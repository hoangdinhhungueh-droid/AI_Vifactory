"""Phase-1 anti-ban PRE-UPLOAD gate (Master Plan page 07).
Runs BEFORE any upload and needs NO OAuth. Enforces the platform-rule layer:
  1. Export profile     - correct aspect file + duration cap via ffprobe
  2. Keyword blacklist  - trademark / unsafe terms in title+description
  3. Duplicate guard    - SHA256(title|platform) and video SHA256 vs upload_log
  4. BGM CC0 compliance - music_library acr_status='clean'; writes license sidecar
  5. AI disclosure      - injects footer + altered_realistic_content_flag
  6. Upload pacing      - max_per_day + min_gap_hours from upload_log
Writes an OAuth-ready upload payload, pushes Telegram + Notion Run Log, and
registers the run in Postgres upload_log.

Usage: PYTHONPATH=/root/video_factory python3 scripts/preflight_upload_gate.py <episode_id> [platform]
  platform in: youtube (default) | youtube_shorts | tiktok | meta_reels
"""
import os, sys, json, re, hashlib, subprocess, asyncio
from datetime import datetime, timezone
from pathlib import Path

for raw in open("/root/secrets/.env"):
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    if line.lower().startswith("export "):
        line = line[7:]
    k, v = line.split("=", 1)
    k = k.strip(); v = v.strip().strip('"').strip("'")
    if v:
        os.environ[k] = v

import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "")
TELEGRAM_BOT_TOKEN = os.getenv("VF_TG_BOT_TOKEN", "") or os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
RUN_LOG_DB_ID = os.getenv("RUN_LOG_DB_ID", "")

EID = sys.argv[1] if len(sys.argv) > 1 else ""
PLATFORM = sys.argv[2] if len(sys.argv) > 2 else "youtube"
if not EID:
    print("missing episode_id", file=sys.stderr); sys.exit(2)

PLATFORM_PROFILE = {
    "youtube":        {"file": "final_169.mp4", "ratio": 16/9, "max_dur": None, "strip_metadata": False},
    "youtube_shorts": {"file": "final_916.mp4", "ratio": 9/16, "max_dur": 60,   "strip_metadata": True},
    "tiktok":         {"file": "final_916.mp4", "ratio": 9/16, "max_dur": 600,  "strip_metadata": True},
    "meta_reels":     {"file": "final_916.mp4", "ratio": 9/16, "max_dur": 90,   "strip_metadata": True},
}
UPLOAD_LIMITS = {
    "youtube":        {"max_per_day": 5, "min_gap_hours": 3},
    "youtube_shorts": {"max_per_day": 5, "min_gap_hours": 3},
    "tiktok":         {"max_per_day": 4, "min_gap_hours": 4},
    "meta_reels":     {"max_per_day": 3, "min_gap_hours": 4},
}
DISCLOSURE = {
    "youtube":        {"description_footer": "\n\n---\nThis content was created with AI assistance.", "altered_realistic_content_flag": True},
    "youtube_shorts": {"description_footer": "\n\n---\nThis content was created with AI assistance.", "altered_realistic_content_flag": True},
    "tiktok":         {"ai_generated_label": True},
    "meta_reels":     {"ai_generated_label": True},
}
MOOD_TO_GENRE = {"dramatic": "dramatic", "tense": "dramatic", "epic": "epic",
                 "calm": "calm", "mystery": "mystery", "peaceful": "peaceful",
                 "sad": "sad", "happy": "happy"}

if PLATFORM not in PLATFORM_PROFILE:
    print("unknown platform " + PLATFORM, file=sys.stderr); sys.exit(2)
prof = PLATFORM_PROFILE[PLATFORM]
limits = UPLOAD_LIMITS[PLATFORM]
disc = DISCLOSURE[PLATFORM]
DIR = Path("/var/vf/episodes") / EID
brain = json.loads((DIR / "brain_input.json").read_text())


def ffprobe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height",
                          "-show_entries", "format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True)
    j = json.loads(out.stdout)
    w = int(j["streams"][0]["width"]); h = int(j["streams"][0]["height"])
    dur = float(j["format"]["duration"])
    return w, h, dur


def sha256_file(path):
    hsh = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            hsh.update(chunk)
    return hsh.hexdigest()


def load_blacklist():
    p = Path("/root/video_factory/scripts/blacklist.json")
    if p.exists():
        return json.loads(p.read_text())
    return {"exact": ["marvel", "disney", "terrorist", "self-harm"], "patterns": []}


async def _db_checks(platform, content_hash, video_sha):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        dup = await conn.fetchval(
            "SELECT 1 FROM upload_log WHERE status='uploaded' AND "
            "((content_hash=$1 AND platform=$2) OR (video_sha256=$3 AND $3 IS NOT NULL)) LIMIT 1",
            content_hash, platform, video_sha)
        day_cnt = await conn.fetchval(
            "SELECT count(*) FROM upload_log WHERE platform=$1 AND status='uploaded' "
            "AND created_at >= now() - interval '24 hours'", platform)
        last_ts = await conn.fetchval(
            "SELECT max(created_at) FROM upload_log WHERE platform=$1 AND status='uploaded'", platform)
        return bool(dup), int(day_cnt or 0), last_ts
    finally:
        await conn.close()


async def _bgm_check(mood):
    genre = MOOD_TO_GENRE.get(mood, mood)
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "SELECT filename, genre, license_type, license_url FROM music_library "
            "WHERE acr_status='clean' AND genre=$1 LIMIT 1", genre)
        if not row:
            return False, {}
        return True, {"bgm_filename": row["filename"], "genre": row["genre"],
                      "license_type": row["license_type"], "license_url": row["license_url"],
                      "acr_status": "clean"}
    finally:
        await conn.close()


async def _register(eid, platform, content_hash, video_sha, title, status, meta):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute(
            "INSERT INTO upload_log (episode_id, platform, content_hash, video_sha256, title, status, metadata) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb)",
            eid, platform, content_hash, video_sha, title, status, json.dumps(meta))
    finally:
        await conn.close()


def telegram_send(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = "https://" + "api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    subprocess.run(["curl", "-sS", "-X", "POST", url, "-d", "chat_id=" + TELEGRAM_CHAT_ID,
                    "--data-urlencode", "text=" + msg], capture_output=True, text=True)


def notion_runlog(title, status, logtxt):
    if not NOTION_TOKEN or not RUN_LOG_DB_ID:
        return
    ts = datetime.now(timezone.utc).isoformat()
    payload = {"parent": {"database_id": RUN_LOG_DB_ID}, "properties": {
        "Name": {"title": [{"text": {"content": title}}]},
        "Status": {"select": {"name": status}},
        "Type": {"select": {"name": "audit"}},
        "Service": {"rich_text": [{"text": {"content": "preflight_gate"}}]},
        "Retries": {"number": 0},
        "Fix Cmd": {"rich_text": [{"text": {"content": "preflight_upload_gate"}}]},
        "Log": {"rich_text": [{"text": {"content": logtxt[:1800]}}]},
        "Timestamp": {"date": {"start": ts}},
    }}
    subprocess.run(["curl", "-sS", "-X", "POST", "https://api.notion.com/v1/pages",
                    "-H", "Authorization: Bearer " + NOTION_TOKEN,
                    "-H", "Notion-Version: 2022-06-28",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(payload)], capture_output=True, text=True)


blocks = []
warns = []

title = (brain.get("title") or brain.get("hook_3s", "")).strip()[:95]
story = brain.get("story", "")
desc_body = story.strip().split("\n\n")[0][:400]
description = desc_body + disc.get("description_footer", "")

# 1) export profile
vfile = DIR / prof["file"]
export_info = {"target_file": prof["file"], "target_ratio": round(prof["ratio"], 3)}
video_sha = None
if not vfile.exists():
    blocks.append("export: missing " + prof["file"])
else:
    w, h, dur = ffprobe(vfile)
    ratio = w / h
    export_info.update({"w": w, "h": h, "dur_s": round(dur, 1), "ratio": round(ratio, 3),
                        "strip_metadata": prof["strip_metadata"]})
    if abs(ratio - prof["ratio"]) > 0.05:
        blocks.append("export: aspect %dx%d (%.3f) != target %.3f" % (w, h, ratio, prof["ratio"]))
    if prof["max_dur"] and dur > prof["max_dur"] + 0.5:
        blocks.append("export: duration %.1fs > max %ds for %s" % (dur, prof["max_dur"], PLATFORM))
    video_sha = sha256_file(vfile)

# 2) blacklist
bl = load_blacklist()
hay = (title + " " + description).lower()
hits = [t for t in bl.get("exact", []) if t.lower() in hay]
hits += ["re:" + p for p in bl.get("patterns", []) if re.search(p, hay, re.I)]
if hits:
    blocks.append("blacklist: " + ", ".join(hits))

# 3) duplicate + 6) pacing
content_hash = hashlib.sha256((title.lower().strip() + "|" + PLATFORM).encode()).hexdigest()
dup, day_cnt, last_ts = asyncio.run(_db_checks(PLATFORM, content_hash, video_sha))
if dup:
    blocks.append("duplicate: title+platform or video hash already uploaded")
if day_cnt >= limits["max_per_day"]:
    blocks.append("pacing: %d uploads in 24h >= max_per_day %d" % (day_cnt, limits["max_per_day"]))
elif last_ts:
    gap_h = (datetime.now(timezone.utc) - last_ts).total_seconds() / 3600.0
    if gap_h < limits["min_gap_hours"]:
        blocks.append("pacing: last upload %.1fh ago < min_gap %dh" % (gap_h, limits["min_gap_hours"]))

# 4) BGM CC0 compliance + license sidecar
mood = brain.get("bgm_mood", "dramatic")
bgm_ok, bgm_lic = asyncio.run(_bgm_check(mood))
if not bgm_ok:
    blocks.append("bgm: no clean CC0 track for mood '" + str(mood) + "' in music_library")
else:
    lic = dict(bgm_lic); lic["episode_id"] = EID; lic["mood"] = mood
    lic["verified_at"] = datetime.now(timezone.utc).isoformat()
    (DIR / (EID + "_bgm.license.json")).write_text(json.dumps(lic, ensure_ascii=False, indent=2))
    export_info["bgm_license"] = EID + "_bgm.license.json"

passed = len(blocks) == 0
status = "preflight_pass" if passed else "blocked"

# AI-disclosure flags for the OAuth-ready payload
disclosure_out = {kk: vv for kk, vv in disc.items() if kk != "description_footer"}

payload = {
    "episode_id": EID, "platform": PLATFORM, "passed": passed,
    "title": title, "description": description,
    "disclosure": disclosure_out,
    "export": export_info, "video_sha256": video_sha,
    "content_hash": content_hash,
    "blocks": blocks, "warns": warns,
    "generated_at": datetime.now(timezone.utc).isoformat(),
}
(DIR / (PLATFORM + "_upload_payload.json")).write_text(json.dumps(payload, ensure_ascii=False, indent=2))

asyncio.run(_register(EID, PLATFORM, content_hash, video_sha, title, status,
                      {"blocks": blocks, "export": export_info}))

verdict = "PASS" if passed else "BLOCKED"
msg = ("🛡️ PRE-UPLOAD GATE (" + PLATFORM + ")\n"
       "Episode: " + EID + "\n"
       "VERDICT: " + verdict + "\n"
       + ("blocks: " + " | ".join(blocks) if blocks else "all 6 checks passed") + "\n"
       "file: " + str(export_info.get("target_file")) + " "
       + str(export_info.get("w", "?")) + "x" + str(export_info.get("h", "?"))
       + " " + str(export_info.get("dur_s", "?")) + "s")
telegram_send(msg)
notion_runlog("[preflight] " + EID + " / " + PLATFORM,
              "PASS" if passed else "NEEDS_CONFIRM", json.dumps(payload, ensure_ascii=False))

print(json.dumps(payload, ensure_ascii=False, indent=2))
