import socket
socket.setdefaulttimeout(600)

import os
import json
import time
import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger("vf.youtube_upload")

TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

def _load_env():
    p = "/root/secrets/.env"
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    v = v.strip().strip('"').strip("'")
                    os.environ.setdefault(k, v)

def _resolve_privacy(privacy_status):
    valid = {"private", "unlisted", "public"}
    if privacy_status and privacy_status.lower() in valid:
        return privacy_status.lower()
    return "unlisted"

def _build_client(market=None):
    _load_env()
    m = (market or "en").lower().strip()

    if m == "jp":
        refresh = os.environ.get("JP_YT_OAUTH_REFRESH_TOKEN") or os.environ.get("YT_OAUTH_REFRESH_TOKEN_JP")
        cid = os.environ.get("JP_YT_OAUTH_CLIENT_ID") or os.environ.get("YT_OAUTH_CLIENT_ID_JP") or os.environ.get("YT_OAUTH_CLIENT_ID")
        csec = os.environ.get("JP_YT_OAUTH_CLIENT_SECRET") or os.environ.get("YT_OAUTH_CLIENT_SECRET_JP") or os.environ.get("YT_OAUTH_CLIENT_SECRET")
    elif m == "kr":
        refresh = os.environ.get("KR_YT_OAUTH_REFRESH_TOKEN") or os.environ.get("YT_OAUTH_REFRESH_TOKEN_KR")
        cid = os.environ.get("KR_YT_OAUTH_CLIENT_ID") or os.environ.get("YT_OAUTH_CLIENT_ID_KR") or os.environ.get("YT_OAUTH_CLIENT_ID")
        csec = os.environ.get("KR_YT_OAUTH_CLIENT_SECRET") or os.environ.get("YT_OAUTH_CLIENT_SECRET_KR") or os.environ.get("YT_OAUTH_CLIENT_SECRET")
    else:
        refresh = os.environ.get("YT_OAUTH_REFRESH_TOKEN") or os.environ.get("EN_YT_OAUTH_REFRESH_TOKEN")
        cid = os.environ.get("YT_OAUTH_CLIENT_ID") or os.environ.get("EN_YT_OAUTH_CLIENT_ID")
        csec = os.environ.get("YT_OAUTH_CLIENT_SECRET") or os.environ.get("EN_YT_OAUTH_CLIENT_SECRET")

    if not refresh:
        raise KeyError(f"YouTube OAuth refresh token for market={m.upper()} not found in /root/secrets/.env.")

    creds = Credentials(
        token=None,
        refresh_token=refresh,
        token_uri=TOKEN_URI,
        client_id=cid,
        client_secret=csec,
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)

def upload_video(video_path, title, description, tags=None,
                 category_id="22", privacy_status=None,
                 made_for_kids=False, market=None, thumbnail_path=None,
                 subtitles_path=None):
    if not os.path.exists(video_path):
        raise FileNotFoundError(video_path)
    _load_env()
    youtube = _build_client(market=market)
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": _resolve_privacy(privacy_status),
            "selfDeclaredMadeForKids": bool(made_for_kids),
            "containsSyntheticMedia": True,
        },
    }
    # 16MB chunks (standard Google recommendation for multi-GB uploads)
    media = MediaFileUpload(video_path, chunksize=16 * 1024 * 1024,
                            resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body,
                                      media_body=media)
    response = None
    retries = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print("UPLOAD_PROGRESS", pct, flush=True)
        except Exception as e:
            if retries < 20:
                retries += 1
                print(f'Upload retry {retries}/20 due to {type(e).__name__}: {e}', flush=True)
                time.sleep(2 ** min(retries, 5))
                continue
            raise
    # 23/08/2026: set the auto-generated thumbnail (produced alongside BG/FG at
    # B4, see prompt_forge.py) right after the video upload -- video +
    # description + thumbnail all go out together in this one B10 call, no
    # separate manual Human Gate 2 thumbnail step.
    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            youtube.thumbnails().set(
                videoId=response["id"],
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            print("THUMBNAIL_SET_OK", thumbnail_path, flush=True)
        except Exception as e:
            print(f"[WARN] thumbnail set failed for {thumbnail_path}: {e}", flush=True)

    # 11/09/2026 (Beat TTS & YouTube AI Dubbing): Upload .srt captions
    if subtitles_path and os.path.exists(subtitles_path):
        try:
            lang_sub = (market or "en").lower()
            if lang_sub == "jp": lang_sub = "ja"
            if lang_sub == "kr": lang_sub = "ko"
            youtube.captions().insert(
                part="snippet",
                body={
                    "snippet": {
                        "videoId": response["id"],
                        "language": lang_sub,
                        "name": f"{lang_sub.upper()} Captions",
                        "isDraft": False
                    }
                },
                media_body=MediaFileUpload(subtitles_path, mimetype="application/x-subrip")
            ).execute()
            print("CAPTIONS_SET_OK", subtitles_path, flush=True)
        except Exception as e:
            print(f"[WARN] captions upload failed for {subtitles_path}: {e}", flush=True)

    return response

def upload_from_payload(episode_dir, payload_file="youtube_upload_payload.json",
                        privacy_status=None, market=None):
    _load_env()
    with open(os.path.join(episode_dir, payload_file)) as f:
        payload = json.load(f)

    if not market:
        market = payload.get("market")
        if not market:
            ep_base = os.path.basename(os.path.normpath(episode_dir)).lower()
            if ep_base.startswith("jp-"):
                market = "jp"
            elif ep_base.startswith("kr-"):
                market = "kr"
            else:
                market = "en"

    # Upload
    target = payload.get("export", {}).get("target_file", "final_169.mp4")
    video_path = os.path.join(episode_dir, target)

    # 23/08/2026: resolve the per-episode auto-generated thumbnail (produced
    # at B4 alongside BG/FG images, key name "thumbnail") so it uploads
    # together with the video + description in this single B10 call.
    thumbnail_path = payload.get("thumbnail_file")
    if thumbnail_path and not os.path.isabs(thumbnail_path):
        thumbnail_path = os.path.join(episode_dir, thumbnail_path)
    if not thumbnail_path or not os.path.exists(thumbnail_path):
        # 23/08/2026 audit fix: check BOTH the episode-dir root AND the images/
        # subfolder, and both "thumbnail" and "thumbnail_final" basenames, so
        # this matches whichever location/name the (not-yet-built) dedicated
        # thumbnail-generation step ends up using -- keeps this consumer in
        # sync with execute_b10_auto_seo_upload_gate2.py's candidate list.
        candidates = []
        for base in ("thumbnail_final", "thumbnail"):
            for ext in ("png", "jpg", "jpeg"):
                candidates.append(os.path.join(episode_dir, f"{base}.{ext}"))
                candidates.append(os.path.join(episode_dir, "images", f"{base}.{ext}"))
        for cand in candidates:
            if os.path.exists(cand):
                thumbnail_path = cand
                break

    subtitles_path = None
    sub_cands = [
        os.path.join(episode_dir, f"subtitles_{market}.srt"),
        os.path.join(episode_dir, "subtitles_ja.srt" if market == "jp" else f"subtitles_{market}.srt"),
        os.path.join(episode_dir, "subtitles.srt"),
    ]
    for cand in sub_cands:
        if os.path.exists(cand) and os.path.getsize(cand) > 50:
            subtitles_path = cand
            break

    resp = upload_video(
        video_path=video_path,
        title=payload["title"],
        description=payload.get("description", ""),
        tags=payload.get("tags") or [],
        privacy_status=privacy_status,
        made_for_kids=False,
        market=market,
        thumbnail_path=thumbnail_path,
        subtitles_path=subtitles_path,
    )
    return resp
