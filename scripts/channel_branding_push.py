"""Push channel description + keywords to brandingSettings.channel (2.4 of Moc 2).

Reads current brandingSettings.channel via channels().list(mine=True), merges in
the new description/keywords (preserving all other existing branding fields),
and writes back via channels().update. Prints before/after for the Decisions Log.
"""
import os
import json

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

NEW_DESCRIPTION = (
    "Untold Stories brings you cinematic deep-dives into the moments that shaped "
    "our world \u2014 the rise and fall of business empires, the turning points of "
    "modern history, gripping true-crime investigations, and the hidden workings "
    "of the human mind.\n\n"
    "New long-form stories every day, with shorts to start the journey. Subscribe "
    "and discover what really happened."
)
NEW_KEYWORDS = (
    "untold stories, true stories, business rise and fall, modern history, "
    "true crime, psychology explained, documentary, deep dive, history explained, "
    "case files"
)


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


def _build_client():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_OAUTH_REFRESH_TOKEN"],
        token_uri=TOKEN_URI,
        client_id=os.environ["YT_OAUTH_CLIENT_ID"],
        client_secret=os.environ["YT_OAUTH_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def main():
    _load_env()
    yt = _build_client()

    resp = yt.channels().list(part="brandingSettings", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        print(json.dumps({"error": "NO_CHANNEL_FOUND", "raw": resp}, indent=2))
        return
    ch = items[0]
    channel_id = ch["id"]
    branding = ch.get("brandingSettings", {})
    b_channel = branding.get("channel", {})

    before = {
        "description": b_channel.get("description"),
        "keywords": b_channel.get("keywords"),
    }

    b_channel["description"] = NEW_DESCRIPTION
    b_channel["keywords"] = NEW_KEYWORDS
    branding["channel"] = b_channel

    body = {
        "id": channel_id,
        "brandingSettings": branding,
    }

    update_resp = yt.channels().update(part="brandingSettings", body=body).execute()
    after_branding = update_resp.get("brandingSettings", {}).get("channel", {})

    out = {
        "channelId": channel_id,
        "before": before,
        "after": {
            "description": after_branding.get("description"),
            "keywords": after_branding.get("keywords"),
        },
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
