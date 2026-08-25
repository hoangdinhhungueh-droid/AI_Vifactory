"""Read-only snapshot of YouTube channel (Multi-Market: EN, JP, KR).

Safe / non-destructive: only calls channels().list (GET).
"""
import os
import sys
import json
import argparse

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


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
    parser = argparse.ArgumentParser(description="Snapshot YouTube channel info.")
    parser.add_argument("--market", "-m", default="en", help="Market channel to snapshot (en, jp, kr)")
    args = parser.parse_args()

    yt = _build_client(args.market)
    resp = yt.channels().list(
        part="snippet,brandingSettings,status,statistics,contentDetails",
        mine=True,
    ).execute()
    items = resp.get("items", [])
    if not items:
        print(json.dumps({"error": "NO_CHANNEL_FOUND", "raw": resp}, indent=2))
        return
    ch = items[0]
    snippet = ch.get("snippet", {})
    branding = ch.get("brandingSettings", {})
    b_channel = branding.get("channel", {})
    b_image = branding.get("image", {})
    status = ch.get("status", {})
    stats = ch.get("statistics", {})
    out = {
        "market": args.market.upper(),
        "channelId": ch.get("id"),
        "title": snippet.get("title"),
        "customUrl_handle": snippet.get("customUrl"),
        "country": snippet.get("country"),
        "description_snippet": snippet.get("description"),
        "description_branding": b_channel.get("description"),
        "keywords_branding": b_channel.get("keywords"),
        "unsubscribedTrailer": b_channel.get("unsubscribedTrailer"),
        "defaultLanguage": b_channel.get("defaultLanguage") or snippet.get("defaultLanguage"),
        "country_branding": b_channel.get("country"),
        "bannerExternalUrl": b_image.get("bannerExternalUrl"),
        "thumbnails_default": (snippet.get("thumbnails") or {}).get("default", {}).get("url"),
        "thumbnails_high": (snippet.get("thumbnails") or {}).get("high", {}).get("url"),
        "privacyStatus": status.get("privacyStatus"),
        "isLinked": status.get("isLinked"),
        "madeForKids": status.get("madeForKids"),
        "subscriberCount": stats.get("subscriberCount"),
        "videoCount": stats.get("videoCount"),
        "viewCount": stats.get("viewCount"),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
