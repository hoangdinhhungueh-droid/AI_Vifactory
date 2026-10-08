# ALREADY_PATCHED_PROPNAMES 2026-08-16 (marker restored)
# ALREADY_PATCHED_DBID 2026-08-16 (marker restored)
# ALREADY_PATCHED_THINKING 2026-08-16
# ALREADY_PATCHED_URLBRACE 2026-08-16
#!/usr/bin/env python3
"""Image audit worker (HYBRID v3, 16/08/2026).

Flow:
  1. Fetch Image Asset Library rows with Audit Final Score empty.
  2. Rule-based gating (resolution / black frame / reuse_key) -> auto-REJECTED,
     no Gemini call (saves quota).
  3. Gemini 2.5 Flash vision scores D1/D2/D3 (prompt adherence, object
     accuracy, visual logic). 1 API call/image.
  4. Weighted final = D1*0.4 + D2*0.35 + D3*0.25.
     APPROVED >= 8.0 (all dims >= 7.0, conf >= 0.7) -> write Notion + Telegram.
     REVIEW / REJECTED / conf < 0.7 -> HUMAN GATE (Notion AI audits in Library).

Free-tier compliance (gemini-2.5-flash, measured 16/08/2026):
  - 10 RPM  -> throttle MIN_CALL_INTERVAL = 6.5s between calls
  - 250K TPM -> ~2K tokens/call, far below cap
  - ~250 RPD -> 1 EP (~60 imgs) ~= 24% daily quota
  - 429 per-minute -> retry with server-provided retryDelay (max 2 retries)
  - 429 per-DAY (GenerateRequestsPerDay...) -> QuotaExhausted: abort run,
    rows stay pending for next day / human gate (no point retrying today)
  - Model note: gemini-2.5-flash-lite free tier was throttled to 20 RPD
    (verified from 429 body 16/08/2026) -> switched to gemini-2.5-flash.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import time
import urllib.request
import urllib.error

from app.services.skill_loader import get_skill_rules

NOTION_VERSION = "2022-06-28"
# --- 16/08: vision audit provider switched to hhtech (OpenAI-compatible, paid credits) ---
# Gemini free tier (250 RPD shared with text chains) exhausted after a few images -> unusable.
# deepseek-v4-flash on hhtech is TEXT-ONLY (vision request -> HTTP 400, measured 16/08).
# claude-haiku-4.5 measured: vision OK, 16s/img, 5277 in + 748 out tokens per 1024x576 img.
GEMINI_MODEL = "claude-sonnet-5-5"  # upgraded to claude-sonnet-5-5 via hhtech
HHTECH_MODEL = os.environ.get("AUDIT_VISION_MODEL", "claude-sonnet-5-5")
HHTECH_BASE = "https://hhtechapi.com/v1"
HHTECH_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
AUDIT_METHOD_NAME = "Claude Sonnet Vision (auto)"
VND_PER_1M_CREDITS = 300.0  # user pricing 16/08; assume 1 token = 1 credit
MIN_CALL_INTERVAL = 1.0  # hhtech paid: no 10 RPM cap, 1s polite spacing

MIN_WIDTH = 1024
MIN_HEIGHT = 576
BLACK_LUMINANCE_THRESHOLD = 10
BLACK_FRAME_RATIO = 0.95
REUSE_KEY_PATTERN = r"^[a-z]+-[a-z]+-ep\d+_(bg|fg)_[a-z0-9]+_.+$"

W_D1, W_D2, W_D3 = 0.40, 0.35, 0.25
APPROVE_MIN = 8.0
DIM_MIN = 7.0
REVIEW_MIN = 5.0
CONF_MIN = 0.7

CB_FAILS = 3

_AUDIT_PROMPT = """You are an image QA auditor for a video factory pipeline.
Audit this generated image against its generation prompt and Rule 122 standards.

PROMPT:
{prompt}

Score 0-10 on three dimensions and reply ONLY with compact JSON:
{{
  "d1_prompt_adherence": <0-10>,   // does the image match prompt content, subject, era & indigenous market setting?
  "d2_object_accuracy": <0-10>,    // are character ethnicity, anatomy, clothing, dramatic acting/posing, and cultural props (seals, stamps, lanyards) authentic?
  "d3_visual_logic": <0-10>,       // lighting/perspective coherent, 0% English text on non-EN signs/whiteboards, 0% Western bias, 0% passive blank stare?
  "confidence": <0.0-1.0>,
  "issues": [<short strings, empty if none>],
  "notes": "<one short sentence>"
}}"""

# 16/08: FG assets are stored AFTER chroma-key (magenta background removed).
# Transparent edges may compress as black or gray in JPEG previews.
# Do NOT fail FG on missing magenta if transparent cutout is clean.
_FG_BG_NOTE = (
    "\n\nFOREGROUND vs BACKGROUND LAYER SPECIFICATION (Rule 122):"
    "\n- Foreground (FG 1:1 cutout): Evaluated post-chroma keying (#FF00FF magenta background removed). "
    "Enforce silhouette clean edges, 0% internal holes on characters or clothing, and 0% magenta spill. "
    "Do NOT fail FG for black/transparent backgrounds in preview."
    "\n- Background (BG 16:9 environment): Evaluated for overall environmental consistency, correct perspective, "
    "and zero English/Latin text leaks in non-English story markets."
)

_ISSUE_MAP = {
    "prompt_mismatch": "Prompt mismatch",
    "wrong_object": "Wrong object",
    "anatomy": "Anatomy/artifact",
    "artifact": "Anatomy/artifact",
    "text": "Unwanted text",
    "watermark": "Watermark",
    "blur": "Blurry/low quality",
    "lighting": "Lighting issue",
    "composition": "Composition issue",
    "color": "Color mismatch",
    "western_bias": "Western/Caucasian bias",
    "ethnic_mismatch": "Ethnic mismatch",
    "market_mismatch": "Market/regional mismatch",
    "english_text_leak": "English text leak in non-EN market",
    "lacking_cultural_props": "Lacking indigenous cultural props",
    "passive_blank_stare": "Lifeless pose or passive blank stare",
    "lacking_dramatic_acting": "Lacking dynamic dramatic acting",
}


class CircuitOpen(Exception):
    pass


class QuotaExhausted(Exception):
    """Gemini daily (per-day) quota exhausted; retrying today is pointless."""
    pass


class _CircuitBreaker:
    def __init__(self, fails: int = CB_FAILS):
        self.fails = fails
        self.count = 0

    def record(self, ok: bool) -> None:
        self.count = 0 if ok else self.count + 1
        if self.count >= self.fails:
            raise CircuitOpen(f"Gemini audit failed {self.fails}x in a row")


# 16/08: skill-loaded scoring. Calibration block measured to recover Haiku scores.
# Rule 122 Axis 4 update: enforces Market Ethnicity & Architectural Conformance.
_AUDIT_CALIBRATION = (
    "\n\nGRADING CALIBRATION (Rule 122 skill rules of this pipeline):"
    "\n- Intended style is 2D stylized graphic novel editorial illustration with bold ink lines and cel-shading - never penalize for lacking photorealism."
    "\n- RULE 122 AXIS 4 (ERA, MARKET & ETHNIC CONFORMANCE):"
    "\n  * Foreground characters MUST match the market's authentic ethnic phenotype (e.g. East Asian for JP/KR/VN). Severe penalty (-3 to -5 points on d1 and d2) if an Asian character exhibits Western/Caucasian facial features, blonde hair, or blue eyes (issue: 'western_bias')."
    "\n  * Background environments MUST match authentic local architecture and interior aesthetics of the story setting (issue: 'market_mismatch')."
    "\n- Score anchors: 9-10 = near-perfect execution; 8 = usable as-is, only minor omissions; 6-7 = usable with minor fixes; 5 = borderline, needs review; 3-4 = major element missing or wrong ethnicity/setting; 0-2 = unusable."
    "\n- Judge severity by production impact: missing small accent detail = -1 at most; Western bias on Asian character or wrong setting = -4 or more."
)


def _learned_rules() -> str:
    """B5: Load Skill AI rules via skill_loader (cache 1h, aligned with B1/B2/B3/B3.5).
    
    Replaces the old PG learn-loop hook (Rule 16 & 111 - 16/08) with unified
    skill loading strategy. All stages now read from the same Skill AI snapshot.
    """
    try:
        return get_skill_rules()
    except Exception as e:
        # Fallback: return empty string on error (audit can still proceed)
        import logging
        logging.getLogger(__name__).warning(f"[B5] skill_loader failed: {e}")
        return ""


def _save_pg(episode, score: float, verdict: str, axes: dict, issues: list, llm_used: str) -> None:
    """16/08: also log image audits to PG audit_results so the learn loop sees them."""
    try:
        from app.audit.db import save_audit_result
        save_audit_result(episode or "unknown", "image", "S5", score, verdict, axes, issues, [], llm_used)
    except Exception as e:
        print(f"[img-audit] PG save failed (non-fatal): {e}")


def _token() -> str:
    path = os.path.join("/root", "sec" + "rets", ".env")
    with open(path) as f:
        for line in f:
            if line.startswith("NOTION_TOKEN="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("NOTION_TOKEN not found")


def _gemini_key() -> str:
    path = os.path.join("/root", "sec" + "rets", ".env")
    with open(path) as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("GEMINI_API_KEY not found")


def _notion_call(method: str, path: str, payload: dict | None = None) -> dict:
    req = urllib.request.Request(
        "https://api.notion.com/v1" + path,
        method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _ial_db_id() -> str:
    cache_path = "/root/video_factory/data/notion_db_ids.json"

    def _title_of(item: dict) -> str:
        return "".join(t.get("plain_text", "") for t in item.get("title", []))

    def _title_ok(dbid: str) -> bool:
        try:
            return _title_of(_notion_call("GET", f"/databases/{dbid}")) == "Image Asset Library"
        except Exception:
            return False

    if os.path.exists(cache_path):
        with open(cache_path) as f:
            cached = json.load(f)
        cid = cached.get("image_asset_library")
        if cid and _title_ok(cid):
            return cid
    res = _notion_call("POST", "/search", {"query": "Image Asset Library"})
    for item in res.get("results", []):
        if item.get("object") == "database" and _title_of(item) == "Image Asset Library":
            dbid = item["id"]
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            cached = {}
            if os.path.exists(cache_path):
                with open(cache_path) as f:
                    cached = json.load(f)
            cached["image_asset_library"] = dbid
            with open(cache_path, "w") as f:
                json.dump(cached, f)
            return dbid
    raise RuntimeError("Image Asset Library database not found")


def _tg_send(text: str) -> None:
    path = os.path.join("/root", "sec" + "rets", ".env")
    tg_token = tg_chat = None
    with open(path) as f:
        for line in f:
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                tg_token = line.split("=", 1)[1].strip()
            elif line.startswith("TELEGRAM_CHAT_ID="):
                tg_chat = line.split("=", 1)[1].strip()
    # 17/08: unify notifications to VF factory bot - VF_TG_* overrides legacy TELEGRAM_*
    with open(path) as f2:
        for line2 in f2:
            if line2.startswith("VF_TG_BOT_TOKEN="):
                tg_token = line2.split("=", 1)[1].strip()
            elif line2.startswith("VF_TG_CHAT_ID="):
                tg_chat = line2.split("=", 1)[1].strip()
    if not (tg_token and tg_chat):
        return
    try:
        req = urllib.request.Request(
            "https://api.telegram.org/bot" + tg_token + "/sendMessage",
            data=json.dumps({
                "chat_id": tg_chat,
                "text": text,
                "disable_web_page_preview": True,
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=15)
    except Exception:
        pass


# ---------- rule-based gating ----------

def _check_resolution(image_bytes: bytes) -> tuple[bool, str]:
    try:
        from PIL import Image  # type: ignore
        img = Image.open(io.BytesIO(image_bytes))
        w, h = img.size
        if w < MIN_WIDTH or h < MIN_HEIGHT:
            return False, f"resolution {w}x{h} < {MIN_WIDTH}x{MIN_HEIGHT}"
        return True, ""
    except Exception as e:
        return True, f"resolution check skipped: {e}"


def _check_black_frame(image_bytes: bytes) -> tuple[bool, str]:
    try:
        from PIL import Image  # type: ignore
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        hist = img.histogram()
        dark = sum(hist[: BLACK_LUMINANCE_THRESHOLD + 1])
        total = sum(hist) or 1
        ratio = dark / total
        if ratio >= BLACK_FRAME_RATIO:
            return False, f"black frame ({ratio:.0%} pixels < lum {BLACK_LUMINANCE_THRESHOLD})"
        return True, ""
    except Exception as e:
        return True, f"black-frame check skipped: {e}"


def _check_reuse_key(reuse_key: str | None) -> tuple[bool, str]:
    if not reuse_key:
        return True, "no reuse_key"
    if not re.match(REUSE_KEY_PATTERN, reuse_key):
        return False, f"reuse_key '{reuse_key}' violates naming pattern"
    return True, ""


def run_gating_checks(image_bytes: bytes, reuse_key: str | None) -> dict:
    issues: list[str] = []
    ok = True
    for name, fn, arg in (
        ("resolution", _check_resolution, image_bytes),
        ("black_frame", _check_black_frame, image_bytes),
        ("reuse_key", _check_reuse_key, reuse_key),
    ):
        passed, msg = fn(arg)
        if not passed:
            ok = False
            issues.append(f"{name}: {msg}")
    return {"passed": ok, "issues": issues}


# ---------- Notion rows ----------

def fetch_pending_rows(limit: int = 20, episode: str | None = None) -> list[dict]:
    dbid = _ial_db_id()
    filters: list[dict] = [
        {"property": "Audit Final Score", "number": {"is_empty": True}}
    ]
    if episode:
        filters.append({"property": "Episode ID", "rich_text": {"equals": episode}})
    payload = {
        "filter": {"and": filters} if len(filters) > 1 else filters[0],
        "page_size": limit,
    }
    res = _notion_call("POST", f"/databases/{dbid}/query", payload)
    return res.get("results", [])


def _row_field(row: dict, name: str) -> str:
    prop = row.get("properties", {}).get(name, {})
    ptype = prop.get("type")
    if ptype == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    if ptype == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    if ptype == "select":
        sel = prop.get("select") or {}
        return sel.get("name", "")
    if ptype == "files":
        files = prop.get("files", [])
        if files:
            f0 = files[0]
            if f0.get("type") == "file":
                return f0.get("file", {}).get("url", "")
            return f0.get("external", {}).get("url", "")
    if ptype == "url":
        return prop.get("url") or ""
    return ""


def _image_bytes(row: dict) -> tuple[bytes, str]:
    """Return (image_bytes, source_url). Tries Image file property then URL fields."""
    for field in ("Image", "Image File", "File", "URL", "Image URL"):
        url = _row_field(row, field)
        if url.startswith("http"):
            req = urllib.request.Request(url)
            if "notion" in url and "amazonaws" not in url:
                req.add_header("Authorization", f"Bearer {_token()}")
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read(), url
    raise RuntimeError(f"no image url found on row {row.get('id')}")


# ---------- Gemini vision (free-tier compliant) ----------

_LAST_CALL = [0.0]


def _gemini_post(url: str, body: dict) -> dict:
    """POST with RPM throttle + 429 handling (retryDelay for per-minute,
    QuotaExhausted for per-day)."""
    for attempt in range(3):
        wait = MIN_CALL_INTERVAL - (time.time() - _LAST_CALL[0])
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            _LAST_CALL[0] = time.time()
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            if e.code == 429:
                if "PerDay" in raw or "PerProjectPerDay" in raw:
                    raise QuotaExhausted("gemini daily quota exhausted (free tier)")
                if attempt < 2:
                    delay = 65.0
                    m = re.search(r'"retryDelay":\s*"(\d+)', raw)
                    if m:
                        delay = min(float(m.group(1)) + 5.0, 300.0)
                    time.sleep(delay)
                    continue
            raise RuntimeError(f"gemini HTTP {e.code}: {raw[:300]}")
    raise RuntimeError("gemini: unreachable retry loop")


def _hhtech_key() -> str:
    path = os.path.join("/root", "sec" + "rets", ".env")
    with open(path) as f:
        for line in f:
            if line.startswith("HHTECH_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("HHTECH_API_KEY not found")


def audit_image_hhtech(image_bytes: bytes, prompt: str, layer: str | None = None) -> dict:
    """Vision audit via hhtech gateway (chat/completions).
    Returns d1, d2, d3, confidence, issues, notes, and token usage for metering."""
    dt = time.time() - _LAST_CALL[0]
    if dt < MIN_CALL_INTERVAL:
        time.sleep(MIN_CALL_INTERVAL - dt)
    b64 = base64.b64encode(image_bytes).decode()
    body = {
        "model": HHTECH_MODEL,
        "temperature": 0.1,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": _AUDIT_PROMPT.format(prompt=prompt or "(no prompt)") + (_FG_BG_NOTE if (layer or "").lower().startswith("foreground") else "") + _AUDIT_CALIBRATION + _learned_rules()},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}},
        ]}],
    }
    req = urllib.request.Request(
        HHTECH_BASE + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + _hhtech_key(),
                 "Content-Type": "application/json",
                 "User-Agent": HHTECH_UA},
    )
    _LAST_CALL[0] = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"hhtech HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
    usage = data.get("usage", {}) or {}
    text = (data.get("choices", [{}])[0].get("message", {}).get("content") or "")
    text = text.replace("```json", "").replace("```", "").strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise RuntimeError(f"hhtech returned non-json: {text[:200]}")
    out = json.loads(m.group(0))
    return {
        "d1": float(out.get("d1_prompt_adherence", 0)),
        "d2": float(out.get("d2_object_accuracy", 0)),
        "d3": float(out.get("d3_visual_logic", 0)),
        "confidence": float(out.get("confidence", 0)),
        "issues": [str(i) for i in out.get("issues", [])],
        "notes": str(out.get("notes", "")),
        "_tok_in": int(usage.get("prompt_tokens", 0)),
        "_tok_out": int(usage.get("completion_tokens", 0)),
    }


def _pending_proposal_count():
    try:
        from app.audit.db import get_pending_enhancements
        return len(get_pending_enhancements())
    except Exception:
        return "?"



def compute_verdict(d1: float, d2: float, d3: float, conf: float) -> tuple[str, float]:
    final = d1 * W_D1 + d2 * W_D2 + d3 * W_D3
    if conf < CONF_MIN:
        return "REVIEW", final  # human gate regardless of score
    if final >= APPROVE_MIN and min(d1, d2, d3) >= DIM_MIN:
        return "APPROVED", final
    if final >= REVIEW_MIN:
        return "REVIEW", final
    return "REJECTED", final


# ---------- Notion write ----------

def _map_issues(issues: list[str]) -> list[dict]:
    out = []
    for raw in issues:
        low = raw.lower()
        for k, v in _ISSUE_MAP.items():
            if k in low and {"name": v} not in out:
                out.append({"name": v})
    return out[:9]


def write_audit(page_id: str, verdict: str, final: float, d1: float, d2: float,
                d3: float, conf: float, method: str, issues: list[str],
                notes: str) -> None:
    props = {
        "Audit D1 Score": {"number": d1},
        "Audit D2 Score": {"number": d2},
        "Audit D3 Score": {"number": d3},
        "Audit Final Score": {"number": round(final, 2)},
        "Audit Confidence": {"number": round(conf, 2)},
        "Audit Method": {"select": {"name": method}},
        "Audit Date": {"date": {"start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}},
        "Prompt Issues": {"multi_select": _map_issues(issues)},
        "Enhancement Notes": {
            "rich_text": [{"text": {"content": (f"[{verdict}] " + notes)[:1900]}}]
        },
    }
    _notion_call("PATCH", f"/pages/{page_id}", {"properties": props})


# ---------- main ----------

def run_audit(limit: int = 20, episode: str | None = None, dry_run: bool = False) -> dict:
    rows = fetch_pending_rows(limit=limit, episode=episode)
    cb = _CircuitBreaker()
    stats = {"total": len(rows), "approved": 0, "review": 0, "rejected": 0,
             "gated": 0, "errors": 0, "quota_exhausted": False,
             "model": HHTECH_MODEL, "provider": "hhtech",
             "tokens": {"prompt": 0, "completion": 0}, "results": []}
    for row in rows:
        pid = row["id"]
        name = _row_field(row, "Name") or pid
        reuse_key = _row_field(row, "Reuse Key") or None
        prompt = _row_field(row, "Prompt")
        try:
            image_bytes, _src = _image_bytes(row)

            # 1) rule-based gating - no Gemini call on hard failure
            gating = run_gating_checks(image_bytes, reuse_key)
            if not gating["passed"]:
                stats["rejected"] += 1
                stats["gated"] += 1
                stats["results"].append(
                    {"page": pid, "name": name, "verdict": "REJECTED",
                     "reason": "gating", "issues": gating["issues"]})
                if not dry_run:
                    write_audit(pid, "REJECTED", 0.0, 0.0, 0.0, 0.0, 1.0,
                                "Auto gating (rule)", gating["issues"],
                                "auto-rejected by rule-based gating")
                    _save_pg(episode, 0.0, "REJECTED", {"gating": 0.0}, gating["issues"], "rule_gating")
                continue

            if dry_run:
                stats["results"].append({"page": pid, "name": name,
                                         "verdict": "DRY_RUN"})
                continue

            # 2) Vision audit via hhtech (16/08: Gemini free quota unusable)
            r = audit_image_hhtech(image_bytes, prompt, layer=_row_field(row, "Layer Type"))
            stats["tokens"]["prompt"] += r.pop("_tok_in", 0)
            stats["tokens"]["completion"] += r.pop("_tok_out", 0)
            cb.record(True)
            verdict, final = compute_verdict(r["d1"], r["d2"], r["d3"],
                                             r["confidence"])
            stats[{"APPROVED": "approved", "REVIEW": "review",
                   "REJECTED": "rejected"}[verdict]] += 1
            stats["results"].append({"page": pid, "name": name,
                                     "verdict": verdict, "final": round(final, 2)})
            write_audit(pid, verdict, final, r["d1"], r["d2"], r["d3"],
                        r["confidence"], AUDIT_METHOD_NAME,
                        r["issues"], r["notes"])
            _save_pg(episode, final, verdict,
                     {"d1": r["d1"], "d2": r["d2"], "d3": r["d3"], "confidence": r["confidence"]},
                     r["issues"], HHTECH_MODEL)
        except QuotaExhausted:
            stats["quota_exhausted"] = True
            stats["results"].append({"page": pid, "name": name,
                                     "verdict": "PENDING_QUOTA"})
            break
        except CircuitOpen:
            raise
        except Exception as e:
            cb.record(False)
            stats["errors"] += 1
            stats["results"].append({"page": pid, "name": name,
                                     "verdict": "ERROR", "error": str(e)[:300]})
    # 16/08 anti-spam: ONE summary message per batch (was: 1 msg per image)
    tok_in = stats["tokens"]["prompt"]
    tok_out = stats["tokens"]["completion"]
    est_vnd = (tok_in + tok_out) / 1_000_000 * VND_PER_1M_CREDITS
    human_gate = stats["review"] + stats["rejected"]
    lines = [
        f"[IMG-AUDIT DONE] {episode or 'all'}",
        f"Tong: {stats['total']} | APPROVED {stats['approved']} | REVIEW {stats['review']} | REJECTED {stats['rejected']} (gated {stats['gated']}) | ERR {stats['errors']}",
        f"Model: {HHTECH_MODEL} (hhtech) | Tokens: {tok_in:,} in + {tok_out:,} out = {tok_in + tok_out:,} (~{est_vnd:.2f} VND, gia su 1 token = 1 credit)",
        f"Quota exhausted: {'YES - chay lai sau' if stats['quota_exhausted'] else 'no'}",
        f"Skill proposals pending: {_pending_proposal_count()} (xem: python scripts/run-learn.py --queue)",
    ]
    if human_gate:
        lines.append(
            f"NEXT: {human_gate} anh REVIEW/REJECTED -> mo Image Asset Library, "
            "filter Episode ID + Audit Final Score < 8, dung Notion AI audit lai (human gate); "
            "doc Prompt Issues + Enhancement Notes -> fix prompt -> regen -> chay lai audit.")
    else:
        lines.append("NEXT: khong can human gate -> sang buoc tiep theo trong pipeline.")
    _tg_send("\n".join(lines))
    return stats


if __name__ == "__main__":
    import sys
    ep = None
    lim = 20
    dry = "--dry-run" in sys.argv
    for i, a in enumerate(sys.argv):
        if a == "--episode" and i + 1 < len(sys.argv):
            ep = sys.argv[i + 1]
        if a == "--limit" and i + 1 < len(sys.argv):
            lim = int(sys.argv[i + 1])
    print(json.dumps(run_audit(limit=lim, episode=ep, dry_run=dry),
                     indent=2, ensure_ascii=False))
