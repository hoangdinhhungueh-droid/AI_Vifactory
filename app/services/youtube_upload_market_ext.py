import os
import sys
import json
import time
from loguru import logger
from dotenv import load_dotenv

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from app.services import publish_ledger
from app.services.youtube_upload import TOKEN_URI, SCOPES, _resolve_privacy

def _load_env():
    load_dotenv('/root/video_factory/.env')
"""Multi-market patch for youtube_upload.py.

Adds _build_client_for_market(market) and upload_from_payload_market(market, ...)
while keeping ALL existing functions 100% intact and backward-compatible.

Added by [AG] 21/08/2026 -- JP/KR distribution expansion.

Env key convention:
  EN (existing, unchanged): YT_OAUTH_CLIENT_ID / _SECRET / _REFRESH_TOKEN
  JP (new): YT_OAUTH_CLIENT_ID_JP / _SECRET_JP / _REFRESH_TOKEN_JP
  KR (new): YT_OAUTH_CLIENT_ID_KR / _SECRET_KR / _REFRESH_TOKEN_KR
"""

# --------------------------------------------------------------------------
# [AG] MULTI-MARKET EXTENSION -- added 21/08/2026
# --------------------------------------------------------------------------


def _build_client_for_market(market="en"):
    """Build YouTube API client using market-specific credentials.

    Falls back gracefully:
      - JP/KR: tries YT_OAUTH_{KEY}_JP/_KR first, then shared YT_OAUTH_{KEY}
      - EN: uses legacy keys (same as _build_client())
    """
    m = (market or "en").lower().strip()
    su = m.upper()

    if m == "en":
        refresh = os.environ["YT_OAUTH_REFRESH_TOKEN"]
        cid = os.environ["YT_OAUTH_CLIENT_ID"]
        csec = os.environ["YT_OAUTH_CLIENT_SECRET"]
    else:
        refresh = os.environ.get(f"YT_OAUTH_REFRESH_TOKEN_{su}")
        if not refresh:
            raise KeyError(
                f"YT_OAUTH_REFRESH_TOKEN_{su} not set. "
                f"Run scripts/yt_oauth_setup_market.py generate {m} first."
            )
        cid = (os.environ.get(f"YT_OAUTH_CLIENT_ID_{su}")
               or os.environ.get("YT_OAUTH_CLIENT_ID"))
        csec = (os.environ.get(f"YT_OAUTH_CLIENT_SECRET_{su}")
                or os.environ.get("YT_OAUTH_CLIENT_SECRET"))
        if not cid or not csec:
            raise KeyError(f"YT_OAUTH_CLIENT_ID/SECRET for market={su} not set.")

    creds = Credentials(
        token=None,
        refresh_token=refresh,
        token_uri=TOKEN_URI,
        client_id=cid,
        client_secret=csec,
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload_from_payload_market(market, episode_dir,
                               payload_file="youtube_upload_payload.json",
                               privacy_status=None):
    """Market-aware upload: selects correct OAuth credentials for market (en/jp/kr).

    Same 5-step safety gate flow as upload_from_payload().
    Drops into existing upload_video() after building market-specific client.
    Added 21/08/2026 for JP/KR distribution expansion.
    """
    _load_env()
    m = (market or "en").lower().strip()

    with open(os.path.join(episode_dir, payload_file)) as f:
        payload = json.load(f)

    # C-03: Check dedup before upload
    task_id = payload.get("task_id", os.path.basename(episode_dir))
    if publish_ledger.check_already_uploaded(task_id):
        logger.warning("[C-03] Task %s already uploaded, blocking duplicate", task_id)
        return {"upload_blocked": True, "reason": "already_uploaded", "task_id": task_id}

    platform = "youtube"

    # --- Safety Gate ---
    try:
        from app.services.security import safety_gate
        sg = safety_gate.run_safety_gate(episode_dir, payload, platform)
        if not sg.passed:
            logger.error("[S8][%s] Safety gate BLOCK: %s", m.upper(), "; ".join(sg.blocks))
            return {"upload_blocked": True, "reason": "safety_gate", "detail": sg.to_dict()}
        if sg.warns:
            logger.warning("[S8][%s] Safety gate WARN: %s", m.upper(), "; ".join(sg.warns))
    except Exception as e:
        logger.warning("[S8][%s] Safety gate error (non-blocking): %s", m.upper(), e)

    # --- Platform validator ---
    try:
        from app.services import platform_validator
        vr = platform_validator.validate_upload(episode_dir, platform)
        if not vr.passed:
            errs = "; ".join(v.message for v in vr.violations if v.severity == "error")
            logger.error("[S8][%s] Platform validator FAIL: %s", m.upper(), errs)
            return {"upload_blocked": True, "reason": "platform_validator", "violations": vr.to_dict()}
    except Exception as e:
        logger.warning("[S8][%s] Platform validator error (non-blocking): %s", m.upper(), e)

    # --- Rate controller ---
    try:
        from app.services import rate_risk_controller
        rc = rate_risk_controller.can_upload(platform)
        if not rc.allowed:
            logger.warning("[S8][%s] Rate controller BLOCK: %s", m.upper(), rc.reason)
            return {"upload_blocked": True, "reason": "rate_risk_controller", "detail": rc.to_dict()}
    except Exception as e:
        logger.warning("[S8][%s] Rate controller error (non-blocking): %s", m.upper(), e)

    # --- Build market-specific client and upload ---
    target = payload.get("export", {}).get("target_file", "final_169.mp4")
    video_path = os.path.join(episode_dir, target)
    if not os.path.exists(video_path):
        raise FileNotFoundError(video_path)

    youtube_client = _build_client_for_market(m)
    resolved_privacy = _resolve_privacy(privacy_status)

    body = {
        "snippet": {
            "title": payload["title"][:100],
            "description": payload.get("description", ""),
            "tags": payload.get("tags") or [],
            "categoryId": payload.get("category_id", "22"),
        },
        "status": {
            "privacyStatus": resolved_privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(video_path, chunksize=4 * 1024 * 1024,
                            resumable=True, mimetype="video/mp4")
    request = youtube_client.videos().insert(part="snippet,status", body=body,
                                             media_body=media)
    response = None
    retries = 0
    while response is None:
        try:
            status_obj, response = request.next_chunk()
            if status_obj:
                print("UPLOAD_PROGRESS", int(status_obj.progress() * 100))
        except HttpError as e:
            if (getattr(e, "resp", None) is not None
                    and e.resp.status in (500, 502, 503, 504) and retries < 5):
                retries += 1
                time.sleep(2 ** retries)
                continue
            raise

    # --- Post-upload: record ---
    try:
        from app.services import rate_risk_controller
        vid = response.get("id") if isinstance(response, dict) else None
        rate_risk_controller.record_upload(platform, vid or "")
    except Exception:
        pass

    try:
        vid = response.get("id") if isinstance(response, dict) else None
        if vid:
            publish_ledger.record_upload(
                vid, payload.get("title", ""), episode_dir, resolved_privacy
            )
    except Exception:
        pass

    return response
