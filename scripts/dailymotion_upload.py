"""dailymotion_upload.py - Dailymotion uploader (Phase 3, mandatory monetizable).

Dailymotion REST API (public base https://api.dailymotion.com), OAuth2 Bearer.
Upload workflow:
  1. POST /oauth/token (grant_type=password) -> access_token
  2. GET  /file/upload (Bearer)              -> {upload_url, progress_url}
  3. POST file to upload_url (multipart)      -> {url: <uploaded file url>}
  4. POST /me/videos (Bearer)                 -> create video with that url

Uses the long-form 16:9 metadata from seo_payloads.json['youtube'] (Dailymotion
is a long-form YouTube-like platform), falling back to ['facebook_reels'].
Video defaults to final_169.mp4. Channel keeps monetization in BUILD mode until
monetization_gate says >=1,000 views (see monetization_gate.py).

NO network unless DAILYMOTION_* creds are set. Default = DRY-RUN: writes
dailymotion_request.json with the exact metadata + planned calls.

Required env (when live):
  DAILYMOTION_API_KEY, DAILYMOTION_API_SECRET,
  DAILYMOTION_USERNAME, DAILYMOTION_PASSWORD

Usage: PYTHONPATH=/root/video_factory python3 scripts/dailymotion_upload.py <episode_dir>
"""
import json
import os
import sys
from datetime import datetime, timezone

API_BASE = os.getenv("DAILYMOTION_API_BASE", "https://api.dailymotion.com")
SCOPES = "manage_videos"


def _load_env(path="/root/secrets/.env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip(); v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def build_video_meta(payload):
    """Pure: map an seo payload to Dailymotion /me/videos fields. No network."""
    tags = [h.lstrip("#") for h in (payload.get("hashtags") or [])]
    tags += [t for t in (payload.get("tags") or []) if t not in tags]
    return {
        "title": (payload.get("title") or "")[:255],
        "description": payload.get("description") or "",
        "tags": ",".join(tags[:10]),
        "channel": os.getenv("DAILYMOTION_CHANNEL", "shortfilms"),
        "published": True,
        "is_created_for_kids": False,
        "language": (payload.get("series", {}) or {}).get("market_code", "en"),
    }


def _select_payload(payloads):
    return payloads.get("youtube") or payloads.get("facebook_reels") or {}


def _creds():
    return {
        "api_key": os.getenv("DAILYMOTION_API_KEY"),
        "api_secret": os.getenv("DAILYMOTION_API_SECRET"),
        "username": os.getenv("DAILYMOTION_USERNAME"),
        "password": os.getenv("DAILYMOTION_PASSWORD"),
    }


def _execute(video_path, meta, creds):
    import httpx
    tok = httpx.post(API_BASE + "/oauth/token", data={
        "grant_type": "password", "client_id": creds["api_key"],
        "client_secret": creds["api_secret"], "username": creds["username"],
        "password": creds["password"], "scope": SCOPES}, timeout=60.0)
    tok.raise_for_status()
    access = tok.json()["access_token"]
    h = {"Authorization": "Bearer " + access}
    up = httpx.get(API_BASE + "/file/upload", headers=h, timeout=60.0)
    up.raise_for_status()
    upload_url = up.json()["upload_url"]
    with open(video_path, "rb") as fh:
        post = httpx.post(upload_url, files={"file": fh}, timeout=600.0)
    post.raise_for_status()
    file_url = post.json()["url"]
    body = dict(meta); body["url"] = file_url
    create = httpx.post(API_BASE + "/me/videos", headers=h, data=body, timeout=120.0)
    return {"status_code": create.status_code,
            "response": (create.json() if create.headers.get(
                "content-type", "").startswith("application/json")
                else create.text[:500])}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    episode_dir = argv[0] if argv else "/var/vf/episodes/betrayal-revenge-quiet-2026-ep001"
    target_file = argv[1] if len(argv) > 1 else "final_169.mp4"
    _load_env()
    with open(os.path.join(episode_dir, "seo_payloads.json")) as f:
        payloads = json.load(f)
    meta = build_video_meta(_select_payload(payloads))
    video_path = os.path.join(episode_dir, target_file)
    creds = _creds()
    have_creds = all(creds.values())
    out = {"adapter": "dailymotion", "base": API_BASE,
           "video_path": video_path, "meta": meta,
           "generated_at": datetime.now(timezone.utc).isoformat()}
    if not have_creds:
        out["mode"] = "DRY_RUN"
        out["note"] = "DAILYMOTION_* creds incomplete -> metadata composed, nothing uploaded."
    elif not os.path.exists(video_path):
        out["mode"] = "DRY_RUN"
        out["note"] = "video file missing: " + video_path
    else:
        out["mode"] = "EXECUTED"
        try:
            out["result"] = _execute(video_path, meta, creds)
        except Exception as e:
            out["mode"] = "ERROR"; out["error"] = str(e)
    with open(os.path.join(episode_dir, "dailymotion_request.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
