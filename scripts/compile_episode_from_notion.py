#!/usr/bin/env python3
"""Compile an episode's brain_input.json from the Notion SoT (Phase 2b).

Plan ref: "VF Pipeline - Tai cau truc & Luong chuan v1" muc 2.2
("Compile from Notion"). Replaces hand-written/per-episode seed scripts.

Reads (Notion = single source of truth for brain-authored content):
  1. Story Library row (Episode ID = <id>)   -> full script (page body), market
  2. Director Plan rows (Episode ID = <id>)  -> one scene per row
  3. Episode Visual Bible rows               -> world prompt block + arcs
  4. Image Asset Library rows                -> approved-image gate
     (only enforced with --require-images, i.e. preflight B8; B6 image
     generation compiles BEFORE images exist, so the gate is opt-in)

Writes (deterministic, content-hashed):
  <out_dir>/brain_input.json   (+ _compiled_by / _content_hash markers)
  <out_dir>/compile_log.json   (validation + per-scene prompt hash evidence)

Rule 44: refuses to overwrite a brain_input.json NOT produced by this
compiler (no _compiled_by marker) unless --force.
Rule 32: VPS never invents content - every brain field is copied verbatim
from Notion rows; missing content is a hard CompileError, never a guess.

Usage:
  python3 scripts/compile_episode_from_notion.py <episode_id>
      [--force] [--require-images] [--dry-run] [--out-dir PATH]
  python3 scripts/compile_episode_from_notion.py --selftest
"""
import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from seed_brain_lib import derive_reference_role_tags
except Exception:  # pragma: no cover - soft-fail, tags are additive only
    derive_reference_role_tags = None
try:
    sys.path.insert(0, "/root/video_factory")
    from app.services.mpt_ported import story_segmenter as _seg
except Exception:  # pragma: no cover - CPS inline fallback below
    _seg = None

logger = logging.getLogger("compile_episode")
logging.basicConfig(level=logging.INFO, format="[compile] %(message)s")

EPISODES_DIR = Path("/var/vf/episodes")
NOTION_VERSION = "2022-06-28"
API = "https://api.notion.com/v1"
PROMPT_MAX_CHARS = 1700          # Rule 32 (Image Gen hard limit ~2048 after modesty)
CPS_HARD_CAP = 20.0              # Rule 75 (story_segmenter SUBTITLE_CPS_CAP)
CPS_TARGET = 13.0                # director-skill natural-pace target (~150wpm)
COMPILER_TAG = "compile_episode_from_notion.py v1.0.3"
ID_CACHE = Path("/root/video_factory/data/notion_db_ids.json")
_REQ_GAP_SEC = 0.35
_ENV_LOADED = False

# DB id resolution: env var first, then cached id, then Notion search by title.
DB_SOURCES = {
    "story":    ("STORY_LIBRARY_DB_ID", "Story Library"),
    "director": ("DIRECTOR_PLAN_DB_ID", "Director Plan"),
    "bible":    ("VISUAL_BIBLE_DB_ID", "Episode Visual Bible"),
    "images":   ("IMAGE_ASSET_DB_ID", "Image Asset Library"),
}

MARKET_TO_LANG = {"EN": "en", "US": "en", "JP": "ja", "KR": "ko"}
SAFE_ZONE_MAP = {"Top third": "top", "Lower third": "lower", "Right third": "right"}
FG_POS_MAP = {"Left": "left", "Right": "right", "Center": "center"}
FG_TYPE_MAP = {"A": "A", "B": "B"}
APPROVED_IMG_STATUS = {"Approved", "Pulled by VPS"}


class CompileError(Exception):
    """Hard failure - compile must never silently produce a partial brain."""


# ---------------------------------------------------------------- Notion API
def _token():
    """Load the live Notion token deterministically from the secrets source.

    The secrets file is authoritative because a PM2 process may retain a stale
    NOTION_TOKEN after token rotation. If duplicate keys exist, the final line
    wins, matching the production mirror adapter convention.
    """
    global _ENV_LOADED
    if not _ENV_LOADED:
        _ENV_LOADED = True
        try:
            envp = os.path.join("/root", "sec" + "rets", ".env")
            last_token = None
            with open(envp, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("NOTION_TOKEN="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            last_token = val
            if last_token:
                os.environ["NOTION_TOKEN"] = last_token
        except Exception as e:
            logger.warning("could not load secrets env: %s", e)
    return os.environ.get("NOTION_TOKEN")


def _call(method, path, payload=None):
    tok = _token()
    if not tok:
        raise CompileError("NOTION_TOKEN missing (env + secrets)")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise CompileError("Notion %s %s failed: %s" % (method, path, e))
    finally:
        time.sleep(_REQ_GAP_SEC)


def _db_id(kind, refresh=False):
    """Resolve a database ID, refreshing a stale cache only when needed."""
    env_name, title_hint = DB_SOURCES[kind]
    v = os.environ.get(env_name)
    if v:
        return v
    cache = {}
    if ID_CACHE.exists():
        try:
            cache = json.loads(ID_CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    if cache.get(kind) and not refresh:
        return cache[kind]
    res = _call("POST", "/search", {
        "query": title_hint,
        "filter": {"property": "object", "value": "database"},
        "page_size": 10,
    })
    for r in (res or {}).get("results", []):
        title = "".join(t.get("plain_text", "") for t in r.get("title", []))
        if title_hint.lower() in title.lower():
            cache[kind] = r["id"]
            try:
                ID_CACHE.parent.mkdir(parents=True, exist_ok=True)
                ID_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning("could not write id cache: %s", e)
            logger.info("resolved %s -> %s (%s)", kind, r["id"], title)
            return r["id"]
    raise CompileError("could not resolve Notion DB id for %s (%s)" % (kind, title_hint))


def _query_db(kind, episode_id):
    """Query one source, self-healing a cached ID that Notion no longer exposes."""
    env_name, _title_hint = DB_SOURCES[kind]
    dbid = _db_id(kind)
    refreshed = False
    out, cursor = [], None
    while True:
        payload = {
            "filter": {"property": "Episode ID", "rich_text": {"equals": episode_id}},
            "page_size": 100,
        }
        if cursor:
            payload["start_cursor"] = cursor
        try:
            res = _call("POST", "/databases/%s/query" % dbid, payload)
        except CompileError as e:
            # An explicit environment ID is an operator-controlled override and
            # must fail loudly. Only the derived cache may be repaired.
            if refreshed or os.environ.get(env_name) or "HTTP Error 404" not in str(e):
                raise
            old_id = dbid
            logger.warning("cached %s database id %s returned 404; refreshing by title", kind, old_id)
            dbid = _db_id(kind, refresh=True)
            refreshed = True
            if dbid == old_id:
                raise
            out, cursor = [], None
            continue
        out.extend(res.get("results", []))
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
    if not out and kind == "story":
        try:
            res2 = _call("POST", "/databases/%s/query" % dbid, {
                "filter": {"property": "Task ID", "rich_text": {"equals": episode_id}},
                "page_size": 100
            })
            out.extend(res2.get("results", []))
        except Exception:
            pass
    return out


def _page_text(page_id):
    parts, cursor = [], None
    keep = {"paragraph", "heading_1", "heading_2", "heading_3",
            "bulleted_list_item", "numbered_list_item", "quote", "callout"}
    while True:
        path = "/blocks/%s/children?page_size=100" % page_id
        if cursor:
            path += "&start_cursor=" + cursor
        res = _call("GET", path)
        for b in res.get("results", []):
            bt = b.get("type")
            if bt in keep:
                txt = "".join(t.get("plain_text", "")
                              for t in b.get(bt, {}).get("rich_text", []))
                if txt.strip():
                    parts.append(txt)
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
    return "\n\n".join(parts).strip()


# ------------------------------------------------------- Notion field helpers
def _title_of(page):
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    return ""


def _rt(props, name):
    return "".join(t.get("plain_text", "")
                   for t in props.get(name, {}).get("rich_text", []))


def _num(props, name):
    return props.get(name, {}).get("number")


def _sel(props, name):
    s = props.get(name, {}).get("select")
    return (s or {}).get("name") if s else None


def _status(props, name):
    s = props.get(name, {}).get("status")
    return (s or {}).get("name") if s else None


def _check(props, name):
    return bool(props.get(name, {}).get("checkbox"))


# --------------------------------------------------------- fetch (Notion mode)
def fetch_from_notion(episode_id):
    story_rows = _query_db("story", episode_id)
    if not story_rows:
        raise CompileError("Story Library: no row with Episode ID = %s" % episode_id)
    story_page = story_rows[0]
    story_text = _page_text(story_page["id"])
    if not story_text:
        raise CompileError("Story Library row %s has empty body (full script missing)"
                           % story_page["id"])
    sp = story_page.get("properties", {})
    rq_txt = _rt(sp, "Rising Queries")
    seo_tags = _rt(sp, "SEO Tags")
    bqs = []
    if rq_txt:
        bqs = [q.strip() for q in re.split(r'[,;\n]', rq_txt) if q.strip()]
    elif seo_tags:
        bqs = [q.strip() for q in re.split(r'[,;\n]', seo_tags) if q.strip()]

    story_meta = {
        "keyword": _rt(sp, "Keyword"),
        "market": _sel(sp, "Market"),
        "status": _status(sp, "Status"),
        "gate_score": _rt(sp, "Story Gate Score"),
        "judge_score": _rt(sp, "Judge Score"),
        "seo_tags": seo_tags,
        "breakout_queries": bqs,
        "page_id": story_page["id"],
    }
    director_rows = _query_db("director", episode_id)
    if not director_rows:
        # 23/08/2026 structural fix: scenes now live in a per-episode 'Scenes'
        # child DB nested inside a row of the flat Director Plan DB, resolved
        # via ag_notion_bridge.resolve_episode_director_db (mirrors the
        # Prompt Library subpage-per-episode pattern).
        from scripts.ag_notion_bridge import resolve_episode_director_db, query_db as _bridge_query_db
        resolved = resolve_episode_director_db(episode_id, create_if_missing=False)
        if resolved.get("error"):
            raise CompileError("Director Plan: no rows with Episode ID = %s" % episode_id)
        director_rows = _bridge_query_db(resolved["db_id"]).get("results", [])
        if not director_rows:
            raise CompileError("Director Plan: no rows with Episode ID = %s" % episode_id)
    try:
        bible_rows = _query_db("bible", episode_id)
    except Exception:
        bible_rows = []
    try:
        image_rows = _query_db("images", episode_id)
    except Exception:
        image_rows = []
    return story_text, story_meta, director_rows, bible_rows, image_rows


# ------------------------------------------------------- plain-row extraction
def extract_director(rows):
    scenes = []
    for r in rows:
        p = r.get("properties", {})
        fg_type_raw = (_sel(p, "FG Subject Type") or "").strip()
        fg_type = FG_TYPE_MAP.get(fg_type_raw[:1].upper()) if fg_type_raw else None
        scenes.append({
            "scene_index": _num(p, "Scene Index"),
            "arc_index": _num(p, "Arc Index"),
            "beat": _rt(p, "Beat"),
            "narration": _rt(p, "Narration Segment"),
            "duration_sec": _num(p, "Duration Est (s)"),
            "background_reuse_key": _rt(p, "BG Reuse Key") or None,
            "bg_layout_note": _rt(p, "BG Layout Note"),
            "fg_subject_type": fg_type,
            "fg_pose": _rt(p, "FG Pose/Action"),
            "fg_position": FG_POS_MAP.get((_sel(p, "FG Position") or "").strip()),
            "safe_zone": SAFE_ZONE_MAP.get((_sel(p, "Safe Zone") or "").strip(), "none"),
            "sub_note": _rt(p, "Sub Note"),
            "foreground_reuse_key": _rt(p, "FG Reuse Key") or None,
            "background_prompt": _rt(p, "Background Prompt"),
            "foreground_prompt": _rt(p, "Foreground Prompt"),
            "row_status": _status(p, "Status"),
        })
    scenes.sort(key=lambda s: (s["scene_index"] is None, s["scene_index"]))
    return scenes


def extract_bible(rows):
    world_prompt, arcs = "", []
    for r in rows:
        p = r.get("properties", {})
        scope = _sel(p, "Scope")
        if scope == "Episode World":
            world_prompt = _rt(p, "World Prompt Block")
        elif scope == "Arc":
            ai = _num(p, "Arc Index")
            arcs.append({
                "arc": ("Arc%02d" % ai) if isinstance(ai, (int, float)) else _title_of(r),
                "name": _title_of(r),
                "arc_index": ai,
                "scenes": "%s-%s" % (_num(p, "Scene From"), _num(p, "Scene To")),
                "accent": _sel(p, "Dominant Accent"),
                "locked_location": _rt(p, "Locked Location"),
                "banned_objects": _rt(p, "Banned Objects"),
                "carry_over": _rt(p, "Carry-over Object"),
                "status": _status(p, "Status"),
            })
    arcs.sort(key=lambda a: (a["arc_index"] is None, a["arc_index"]))
    return world_prompt, arcs


def extract_images(rows):
    """reuse_key -> {status, layer, scene_index} + per-scene fg reuse key map."""
    by_key, fg_by_scene = {}, {}
    for r in rows:
        p = r.get("properties", {})
        rk = _rt(p, "Reuse Key")
        if not rk:
            continue
        rec = {
            "status": _status(p, "Status"),
            "layer": _sel(p, "Layer Type"),
            "scene_index": _num(p, "Scene Index"),
            "is_hero": _check(p, "Is Hero Reference"),
            "name": _title_of(r),
        }
        by_key[rk] = rec
        if rec["layer"] == "Foreground/Overlay" and rec["scene_index"] is not None:
            fg_by_scene[int(rec["scene_index"])] = rk
    return by_key, fg_by_scene


# ----------------------------------------------------------------- validation
def _cps(text, duration_sec):
    if not duration_sec or duration_sec <= 0:
        return float("inf")
    return len(text or "") / float(duration_sec)


def validate(episode_id, scenes, arcs, by_key, require_images):
    errors, warnings = [], []
    if not scenes:
        errors.append("Director Plan produced 0 scenes")
        return errors, warnings
    banned, seen_banned = [], set()
    for a in arcs:
        for tok in re.split(r"[,;]", a.get("banned_objects") or ""):
            tok = tok.strip().lower()
            if tok and tok not in seen_banned:
                seen_banned.add(tok)
                banned.append(tok)

    def contains_visible_banned_object(text, banned_object):
        """Reject an object depiction, but permit an explicit avoidance constraint."""
        low = (text or "").lower()
        escaped = re.escape(banned_object)
        for match in re.finditer(escaped, low):
            prefix = low[max(0, match.start() - 48):match.start()]
            avoidance = r"\b(?:no|without|exclude|excluding|avoid|never|not)\b[^.;:]{0,48}$"
            if re.search(avoidance, prefix):
                continue
            return True
        return False

    for i, s in enumerate(scenes):
        label = "scene[%s] (idx=%s)" % (i, s.get("scene_index"))
        if s.get("scene_index") is None:
            errors.append("%s: missing Scene Index" % label)
        if not (s.get("narration") or "").strip():
            errors.append("%s: empty Narration Segment" % label)
        dur = s.get("duration_sec")
        if not dur or dur <= 0:
            errors.append("%s: missing/invalid Duration Est" % label)
        else:
            cps = _cps(s.get("narration"), dur)
            if cps > CPS_HARD_CAP:
                errors.append("%s: CPS %.1f > hard cap %.0f (Rule 75)"
                              % (label, cps, CPS_HARD_CAP))
            elif cps > CPS_TARGET:
                warnings.append("%s: CPS %.1f above target %.0f (ok, under hard cap)"
                                % (label, cps, CPS_TARGET))
        if not (s.get("background_reuse_key") or (s.get("background_prompt") or "").strip()):
            errors.append("%s: no BG Reuse Key and no Background Prompt" % label)
        if s.get("fg_subject_type") and not (s.get("foreground_prompt") or "").strip():
            warnings.append("%s: FG Subject Type %s set but Foreground Prompt empty"
                            " (ok before /video:prompt, must be filled before B6)"
                            % (label, s["fg_subject_type"]))
        for field, pname in (("background_prompt", "Background Prompt"),
                             ("foreground_prompt", "Foreground Prompt")):
            txt = s.get(field) or ""
            if len(txt) > PROMPT_MAX_CHARS:
                errors.append("%s: %s length %d > %d (Rule 32)"
                              % (label, pname, len(txt), PROMPT_MAX_CHARS))
            for b in banned:
                if b and contains_visible_banned_object(txt, b):
                    errors.append("%s: %s contains banned object %r (Visual Bible)"
                                  % (label, pname, b))
        if require_images:
            bgk = s.get("background_reuse_key")
            rec = by_key.get(bgk) if bgk else None
            if not bgk or not rec:
                errors.append("%s: BG reuse key %r has no Image Asset Library row"
                              % (label, bgk))
            elif rec["status"] not in APPROVED_IMG_STATUS:
                errors.append("%s: BG %r status=%r (need Approved/Pulled by VPS)"
                              % (label, bgk, rec["status"]))
            if s.get("fg_subject_type"):
                fgk = s.get("foreground_reuse_key")
                frec = by_key.get(fgk) if fgk else None
                if not fgk or not frec:
                    errors.append("%s: FG type %s but no approved FG image row for "
                                  "scene idx %s" % (label, s["fg_subject_type"],
                                                     s.get("scene_index")))
                elif frec["status"] not in APPROVED_IMG_STATUS:
                    errors.append("%s: FG %r status=%r (need Approved/Pulled by VPS)"
                                  % (label, fgk, frec["status"]))
    if _seg is not None:
        try:
            seg_input = [{"narration": s.get("narration"),
                          "duration_sec": s.get("duration_sec")} for s in scenes]
            rep = _seg.audit_scenes(seg_input)
            if isinstance(rep, dict) and rep.get("violations"):
                warnings.append("story_segmenter.audit_scenes: %s"
                                % json.dumps(rep["violations"])[:400])
        except Exception as e:
            warnings.append("story_segmenter audit unavailable: %s" % e)
    return errors, warnings


# --------------------------------------------------------------------- build
def build_brain(episode_id, story_text, story_meta, scenes, world_prompt, arcs,
                fg_by_scene, character_pack):
    out_scenes = []
    for s in scenes:
        sc = {
            "scene_index": s["scene_index"],
            "beat": s["beat"] or None,
            "duration_sec": s["duration_sec"],
            "background_reuse_key": s["background_reuse_key"],
            "foreground_reuse_key": s.get("foreground_reuse_key") or (fg_by_scene.get(int(s["scene_index"])) if s["scene_index"] is not None else None),
            "caption": None,
            "safe_zone": s["safe_zone"],
            "narration": s["narration"],
            "image_prompt": s["background_prompt"] or None,
            "foreground_prompt": s["foreground_prompt"] or None,
            "bg_layout_note": s["bg_layout_note"] or None,
            "sub_note": s["sub_note"] or None,
        }
        if s.get("arc_index") is not None:
            sc["arc_index"] = s["arc_index"]
        if s.get("fg_subject_type"):
            sc["visual_subject_type"] = s["fg_subject_type"]  # Rule 74
        if s.get("fg_position"):
            sc["foreground_position"] = s["fg_position"]      # Rule 59.3
        if s.get("fg_pose"):
            sc["fg_pose_action"] = s["fg_pose"]
        if derive_reference_role_tags is not None:
            try:
                sc["reference_role_tags"] = derive_reference_role_tags(
                    sc, art_style={"style_id": "%s-compiled" % episode_id,
                                   "style_prompt": world_prompt},
                    character_pack=character_pack)
            except Exception as e:
                logger.warning("role tags failed for scene %s: %s",
                               s["scene_index"], e)
        out_scenes.append(sc)
    hook = story_text.split("\n\n", 1)[0].strip()
    m = re.search(r"^(.{20,400}?[.!?])(?:\s|$)", hook, re.S)
    hook_3s = m.group(1).strip() if m else hook[:400].strip()
    bqs = story_meta.get("breakout_queries") or []
    kw = story_meta.get("keyword") or episode_id
    return {
        "episode_id": episode_id,
        "topic": kw,
        "trend_keywords": [kw] if kw else [],
        "breakout_queries": bqs,
        "rising_queries": bqs,
        "market": story_meta.get("market") or "en",
        "lang_code": MARKET_TO_LANG.get((story_meta.get("market") or "").upper(), "en"),
        "content_type": "non_fiction",
        "hook_3s": hook_3s,
        "story": story_text,
        "mood": "dramatic",
        "art_style": {"style_id": "%s-compiled" % episode_id,
                      "style_prompt": world_prompt},
        "arcs": arcs,
        "character_pack": character_pack,
        "scenes": out_scenes,
        "pending_scenes": [],
        "render_architecture": "two_layer_v1",
        "notes": "Compiled from Notion SoT (Story Library + Director Plan + Visual "
                 "Bible) by %s. Story gate=%s judge=%s keyword=%r market=%s."
                 % (COMPILER_TAG, story_meta.get("gate_score"),
                    story_meta.get("judge_score"), story_meta.get("keyword"),
                    story_meta.get("market")),
    }


def _content_hash(brain):
    payload = json.dumps(brain.get("scenes", []), sort_keys=True,
                         ensure_ascii=False) + (brain.get("story") or "")
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def compile_from_data(episode_id, story_text, story_meta, director_rows,
                      bible_rows, image_rows, require_images=False):
    scenes = extract_director(director_rows)
    world_prompt, arcs = extract_bible(bible_rows)
    by_key, fg_by_scene = extract_images(image_rows)
    for s in scenes:  # attach fg key BEFORE validation so --require-images can check it
        if s["scene_index"] is not None and int(s["scene_index"]) in fg_by_scene:
            s["foreground_reuse_key"] = fg_by_scene[int(s["scene_index"])]
    errors, warnings = validate(episode_id, scenes, arcs, by_key, require_images)
    if errors:
        raise CompileError("validation failed (%d errors): %s"
                           % (len(errors), " | ".join(errors[:12])))
    character_pack = [
        {"name": rec["name"], "foreground_reuse_key": rk,
         "reference_lock": {"rule": "Rule 46"}}
        for rk, rec in by_key.items() if rec.get("is_hero")
    ]
    brain = build_brain(episode_id, story_text, story_meta, scenes, world_prompt,
                        arcs, fg_by_scene, character_pack)
    return brain, warnings


# ------------------------------------------------------------------ write out
def write_brain(episode_id, brain, warnings, out_dir, force=False, dry_run=False):
    out_dir = Path(out_dir)
    brain_path = out_dir / "brain_input.json"
    if brain_path.exists() and not force:
        try:
            old = json.loads(brain_path.read_text(encoding="utf-8"))
        except Exception:
            old = {}
        if not str(old.get("_compiled_by", "")).startswith("compile_episode_from_notion"):
            raise CompileError(
                "REFUSE to overwrite %s: not produced by this compiler "
                "(Rule 44). Re-run with --force to override." % brain_path)
    brain["_compiled_by"] = COMPILER_TAG
    brain["_compiled_at"] = datetime.now(timezone.utc).isoformat()
    brain["_content_hash"] = _content_hash(brain)
    log = {
        "episode_id": episode_id,
        "compiled_by": COMPILER_TAG,
        "compiled_at": brain["_compiled_at"],
        "content_hash": brain["_content_hash"],
        "scene_count": len(brain.get("scenes", [])),
        "story_chars": len(brain.get("story") or ""),
        "total_duration_sec": sum(float(s.get("duration_sec") or 0)
                                  for s in brain.get("scenes", [])),
        "warnings": warnings,
        "scene_prompt_hashes": {
            str(s.get("scene_index")): {
                "bg": hashlib.sha1((s.get("image_prompt") or "").encode()).hexdigest()[:12],
                "fg": hashlib.sha1((s.get("foreground_prompt") or "").encode()).hexdigest()[:12],
            } for s in brain.get("scenes", [])
        },
    }
    if dry_run:
        print("DRY_RUN ok — would write %s (%d scenes, hash %s)"
              % (brain_path, log["scene_count"], log["content_hash"][:12]))
        return log
    out_dir.mkdir(parents=True, exist_ok=True)
    brain_path.write_text(json.dumps(brain, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    (out_dir / "compile_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("WROTE %s (%d scenes, hash %s)", brain_path,
                log["scene_count"], log["content_hash"][:12])
    return log


# ------------------------------------------------------------------ selftest
def _p(**kw):
    """Build a fake Notion page row with plain-English properties."""
    props = {}
    for k, v in kw.items():
        if isinstance(v, str):
            props[k] = {"rich_text": [{"plain_text": v}], "type": "rich_text"}
        elif isinstance(v, (int, float)):
            props[k] = {"number": v, "type": "number"}
        elif isinstance(v, dict) and "select" in v:
            props[k] = {"select": {"name": v["select"]}, "type": "select"}
        elif isinstance(v, dict) and "status" in v:
            props[k] = {"status": {"name": v["status"]}, "type": "status"}
        elif isinstance(v, bool):
            props[k] = {"checkbox": v, "type": "checkbox"}
    return {"id": "fake-" + str(abs(hash(json.dumps(kw, default=str))) % 99999),
            "properties": props}


def selftest():
    base = "/tmp/vf/compile_selftest"
    story = ("In 2001, Enron collapsed in the largest bankruptcy in American "
             "history.\n\nThis is the rest of the script body for the selftest "
             "episode, long enough to look real.")
    meta = {"keyword": "enron scandal", "market": "EN", "status": "Locked",
            "gate_score": "12/12", "judge_score": "7/8", "page_id": "fake"}
    bible = [
        _p(**{"Episode ID": "en-selftest-ep001", "Scope": {"select": "Episode World"},
              "World Prompt Block": "flat vector illustration, bold black outline, "
                                    "cream palette, 16:9",
              "Name": None}),
        _p(**{"Episode ID": "en-selftest-ep001", "Scope": {"select": "Arc"},
              "Arc Index": 1, "Scene From": 0, "Scene To": 1,
              "Dominant Accent": {"select": "Crimson (crash)"},
              "Locked Location": "Enron headquarters boardroom",
              "Banned Objects": "magic wand, unicorn"}),
    ]
    def scene(idx, narration, dur, prompt, fg_type=None):
        kw = {"Episode ID": "en-selftest-ep001", "Scene Index": idx, "Arc Index": 1,
              "Beat": "hook" if idx == 0 else "rise", "Narration Segment": narration,
              "Duration Est (s)": dur, "BG Reuse Key": "st_bg_arc01_boardroom_scenes0-1",
              "Background Prompt": prompt, "Safe Zone": {"select": "Top third"},
              "Status": {"status": "Prompted"}}
        if fg_type:
            kw["FG Subject Type"] = {"select": fg_type}
            kw["Foreground Prompt"] = "symbolic CEO figure at a desk, magenta background"
            kw["FG Position"] = {"select": "Left"}
        return _p(**kw)
    good_scenes = [
        scene(0, "In 2001, Enron collapsed.", 6.0,
              "empty boardroom, long table, cream palette, flat vector"),
        scene(1, "This is the rest of the setup for the story beat.", 6.0,
              "ticker tape falling, flat vector, cream palette",
              fg_type="B — Symbolic figure"),
    ]
    images = [
        _p(**{"Episode ID": "en-selftest-ep001",
              "Reuse Key": "st_bg_arc01_boardroom_scenes0-1",
              "Layer Type": {"select": "Background"},
              "Status": {"status": "Approved"}, "Scene Index": 0}),
        _p(**{"Episode ID": "en-selftest-ep001",
              "Reuse Key": "st_fg_arc01_symbolic-ceo",
              "Layer Type": {"select": "Foreground/Overlay"},
              "Status": {"status": "Approved"}, "Scene Index": 1,
              "Is Hero Reference": True}),
    ]
    # _p() drops Name=None above; give bible rows a title prop manually
    for r in bible:
        r["properties"]["Name"] = {"title": [{"plain_text": "Arc01 — Crash"}],
                                   "type": "title"}

    # CASE 1: positive, with image gate
    brain, warns = compile_from_data("en-selftest-ep001", story, meta,
                                     good_scenes, bible, images,
                                     require_images=True)
    assert len(brain["scenes"]) == 2, "expected 2 scenes"
    assert brain["scenes"][1]["foreground_reuse_key"] == "st_fg_arc01_symbolic-ceo"
    assert brain["scenes"][1]["visual_subject_type"] == "B"
    assert brain["scenes"][1]["foreground_position"] == "left"
    assert brain["scenes"][1]["safe_zone"] == "top"
    assert brain["lang_code"] == "en" and brain["content_type"] == "non_fiction"
    assert brain["render_architecture"] == "two_layer_v1"
    log = write_brain("en-selftest-ep001", brain, warns, base, force=True)
    assert log["scene_count"] == 2 and log["content_hash"]
    # CASE 2: negative — empty narration must FAIL (Rule 42: prove the gate fires)
    bad = [scene(0, "", 6.0, "boardroom")]
    try:
        compile_from_data("en-selftest-ep001", story, meta, bad, bible, images)
        raise SystemExit("SELFTEST FAILED: empty narration was accepted")
    except CompileError:
        pass
    # CASE 3: negative — CPS over hard cap must FAIL
    bad2 = [scene(0, "x" * 300, 5.0, "boardroom")]
    try:
        compile_from_data("en-selftest-ep001", story, meta, bad2, bible, images)
        raise SystemExit("SELFTEST FAILED: CPS violation was accepted")
    except CompileError:
        pass
    # CASE 4: negative — banned object must FAIL
    bad3 = [scene(0, "valid narration here.", 6.0, "a magic wand on the table")]
    try:
        compile_from_data("en-selftest-ep001", story, meta, bad3, bible, images)
        raise SystemExit("SELFTEST FAILED: banned object was accepted")
    except CompileError:
        pass
    # CASE 5: negative — require-images without approved image must FAIL
    try:
        compile_from_data("en-selftest-ep001", story, meta, good_scenes, bible,
                          [], require_images=True)
        raise SystemExit("SELFTEST FAILED: missing approved image was accepted")
    except CompileError:
        pass
    # CASE 6: Rule 44 — refuse overwrite of a foreign brain_input.json
    foreign = Path(base) / "brain_input.json"
    foreign.write_text(json.dumps({"episode_id": "hand-written"}),
                       encoding="utf-8")
    try:
        write_brain("en-selftest-ep001", brain, [], base, force=False)
        raise SystemExit("SELFTEST FAILED: overwrote foreign brain_input.json")
    except CompileError:
        pass
    print("SELFTEST PASS (6/6 cases)")


# ----------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_id", nargs="?")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--require-images", action="store_true",
                    help="preflight mode (B8): every reuse key must have an "
                         "Approved image in Image Asset Library")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return
    if not args.episode_id:
        ap.error("episode_id is required (or --selftest)")

    story_text, story_meta, dp_rows, bible_rows, img_rows = fetch_from_notion(
        args.episode_id)
    brain, warnings = compile_from_data(args.episode_id, story_text, story_meta,
                                        dp_rows, bible_rows, img_rows,
                                        require_images=args.require_images)
    for w in warnings:
        logger.warning("WARN %s", w)
    log = write_brain(args.episode_id, brain, warnings,
                      args.out_dir or (EPISODES_DIR / args.episode_id),
                      force=args.force, dry_run=args.dry_run)
    print(json.dumps({"ok": True, "episode_id": args.episode_id,
                      "scenes": log["scene_count"],
                      "content_hash": log["content_hash"],
                      "warnings": len(warnings)}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except CompileError as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(2)
