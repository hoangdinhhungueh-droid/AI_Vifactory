"""YouTube privacy-status SWITCH (videos.update) for AI Video Factory (Multi-Market).

Flips privacyStatus on an EXISTING already-uploaded video id across EN, JP, KR.
Credentials loaded from /root/secrets/.env at runtime.
"""
import os
import sys
import json
import argparse

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
VALID = ("private", "unlisted", "public")


def _load_env(path=None):
    path = path or os.path.join("/root", "secrets", ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip(chr(34)).strip(chr(39))
            if k and k not in os.environ:
                os.environ[k] = v


def _build_client(market="en"):
    _load_env()
    m = (market or "en").lower().strip()
    su = m.upper()

    if m == "en":
        refresh = os.environ.get("YT_OAUTH_REFRESH_TOKEN", "")
        cid = os.environ.get("YT_OAUTH_CLIENT_ID", "")
        csec = os.environ.get("YT_OAUTH_CLIENT_SECRET", "")
    else:
        refresh = os.environ.get(f"{su}_YT_OAUTH_REFRESH_TOKEN") or os.environ.get(f"YT_OAUTH_REFRESH_TOKEN_{su}", "")
        cid = os.environ.get(f"{su}_YT_OAUTH_CLIENT_ID") or os.environ.get("YT_OAUTH_CLIENT_ID", "")
        csec = os.environ.get(f"{su}_YT_OAUTH_CLIENT_SECRET") or os.environ.get("YT_OAUTH_CLIENT_SECRET", "")

    if not refresh:
        raise KeyError(f"Refresh token for market={su} not found in /root/secrets/.env")

    creds = Credentials(
        token=None,
        refresh_token=refresh,
        token_uri=TOKEN_URI,
        client_id=cid,
        client_secret=csec,
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def main():
    parser = argparse.ArgumentParser(description="Switch YouTube video privacy status.")
    parser.add_argument("video_id", help="YouTube video ID")
    parser.add_argument("privacy", choices=VALID, help="Target privacy status")
    parser.add_argument("--market", "-m", default="en", help="Market channel (en, jp, kr)")
    parser.add_argument("--yes", action="store_true", help="Execute change (otherwise DRY-RUN)")
    args = parser.parse_args()

    yt = _build_client(args.market)
    resp = yt.videos().list(part="snippet,status", id=args.video_id).execute()
    items = resp.get("items", [])
    if not items:
        print(f"ERROR: Video {args.video_id} not found on market={args.market.upper()} channel.")
        sys.exit(1)

    v = items[0]
    curr_status = v["status"]["privacyStatus"]
    title = v["snippet"]["title"]
    print(f"Channel Market: {args.market.upper()}")
    print(f"Video ID      : {args.video_id}")
    print(f"Title         : {title}")
    print(f"Current Status: {curr_status}")
    print(f"Target Status : {args.privacy}")

    if not args.yes:
        print("\n[DRY-RUN] No changes made. Pass --yes to apply.")
        return

    update_body = {
        "id": args.video_id,
        "status": {
            "privacyStatus": args.privacy,
            "selfDeclaredMadeForKids": v["status"].get("selfDeclaredMadeForKids", False),
        }
    }
    up_resp = yt.videos().update(part="status", body=update_body).execute()
    new_status = up_resp["status"]["privacyStatus"]
    print(f"\n[APPLIED] Successfully updated privacyStatus: {curr_status} -> {new_status}")


if __name__ == "__main__":
    main()
