"""Multi-market YouTube OAuth setup helper (Notion SoT 100% compliant).

Exact variable naming per Notion SoT:
  JP_YT_OAUTH_CLIENT_ID
  JP_YT_OAUTH_CLIENT_SECRET
  JP_YT_OAUTH_REFRESH_TOKEN
  JP_YT_CHANNEL_ID
  JP_YT_CHANNEL_HANDLE

  KR_YT_OAUTH_CLIENT_ID
  KR_YT_OAUTH_CLIENT_SECRET
  KR_YT_OAUTH_REFRESH_TOKEN
  KR_YT_CHANNEL_ID
  KR_YT_CHANNEL_HANDLE

Flow:
  1. python3 scripts/yt_oauth_setup_market.py exchange jp <code_or_url>
  2. Script exchanges code -> gets refresh_token -> queries YouTube API -> gets channel ID & handle
  3. Script appends exact block to /root/secrets/.env
  4. Script verifies channel status
"""
import os, sys, json, urllib.parse, urllib.request
import datetime

SCOPES = " ".join([
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
])

REDIRECT_URI = "http://localhost:8765"
SECRETS_PATH = "/root/secrets/.env"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _load_env():
    if not os.path.exists(SECRETS_PATH):
        return
    with open(SECRETS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def get_credentials(market):
    _load_env()
    m = market.lower()
    if m == "en":
        cid = os.environ.get("YT_OAUTH_CLIENT_ID", "")
        csec = os.environ.get("YT_OAUTH_CLIENT_SECRET", "")
    else:
        su = m.upper()
        cid = (os.environ.get(f"{su}_YT_OAUTH_CLIENT_ID")
               or os.environ.get(f"YT_OAUTH_CLIENT_ID_{su}")
               or os.environ.get("YT_OAUTH_CLIENT_ID", ""))
        csec = (os.environ.get(f"{su}_YT_OAUTH_CLIENT_SECRET")
                or os.environ.get(f"YT_OAUTH_CLIENT_SECRET_{su}")
                or os.environ.get("YT_OAUTH_CLIENT_SECRET", ""))
    return cid, csec


def extract_code(raw_input):
    raw = raw_input.strip()
    if raw.startswith("http"):
        parsed = urllib.parse.urlparse(raw)
        params = urllib.parse.parse_qs(parsed.query)
        codes = params.get("code", [])
        if codes:
            return codes[0]
        return None
    return raw


def exchange_and_save(market, raw_code_or_url):
    _load_env()
    m = market.lower()
    su = m.upper()
    cid, csec = get_credentials(market)
    if not cid or not csec:
        return False, "Missing client_id or client_secret in env"

    code = extract_code(raw_code_or_url)
    if not code:
        return False, f"Could not extract code from: {raw_code_or_url[:100]}"

    data = urllib.parse.urlencode({
        "code": code,
        "client_id": cid,
        "client_secret": csec,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode("utf-8")

    req = urllib.request.Request(
        TOKEN_URI, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return False, f"Google OAuth HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)

    refresh = tok.get("refresh_token")
    access = tok.get("access_token")
    if not refresh:
        return False, f"No refresh_token returned. Response: {tok}"

    # Query YouTube Channel info
    ch_info = {"id": "", "title": "", "handle": "", "country": ""}
    try:
        yt_url = "https://www.googleapis.com/youtube/v3/channels?part=snippet,status,statistics&mine=true"
        req_yt = urllib.request.Request(yt_url, headers={"Authorization": f"Bearer {access}"})
        with urllib.request.urlopen(req_yt, timeout=20) as r:
            ch_data = json.loads(r.read().decode("utf-8"))
            if ch_data.get("items"):
                it = ch_data["items"][0]
                ch_info["id"] = it.get("id", "")
                ch_info["title"] = it.get("snippet", {}).get("title", "")
                ch_info["handle"] = it.get("snippet", {}).get("customUrl", "")
                ch_info["country"] = it.get("snippet", {}).get("country", "")
    except Exception as e:
        print(f"Warning: could not fetch channel metadata: {e}")

    # Build exact env lines
    prefix = f"{su}_YT" if su in ["JP", "KR"] else "YT"
    new_vars = {
        f"{prefix}_OAUTH_CLIENT_ID": cid,
        f"{prefix}_OAUTH_CLIENT_SECRET": csec,
        f"{prefix}_OAUTH_REFRESH_TOKEN": refresh,
        f"{prefix}_CHANNEL_ID": ch_info["id"],
        f"{prefix}_CHANNEL_HANDLE": ch_info["handle"],
    }

    # Append to secrets
    existing = ""
    if os.path.exists(SECRETS_PATH):
        with open(SECRETS_PATH, "r") as f:
            existing = f.read()

    lines_to_add = []
    for k, v in new_vars.items():
        if (k + "=") not in existing:
            lines_to_add.append(f"{k}={v}")

    if lines_to_add:
        today = datetime.date.today().strftime("%d/%m/%Y")
        block = f"\n# === YouTube OAuth & Channel -- Market: {su} (added by [AG] {today}) ===\n"
        block += "\n".join(lines_to_add) + "\n"
        with open(SECRETS_PATH, "a") as f:
            f.write(block)

    return True, {
        "market": su,
        "channel_title": ch_info["title"],
        "channel_handle": ch_info["handle"],
        "channel_id": ch_info["id"],
        "channel_country": ch_info["country"],
        "keys_saved": list(new_vars.keys()),
    }


def verify_market(market):
    _load_env()
    m = market.lower()
    su = m.upper()
    prefix = f"{su}_YT" if su in ["JP", "KR"] else "YT"

    refresh = os.environ.get(f"{prefix}_OAUTH_REFRESH_TOKEN") or os.environ.get(f"YT_OAUTH_REFRESH_TOKEN_{su}")
    cid = os.environ.get(f"{prefix}_OAUTH_CLIENT_ID") or os.environ.get("YT_OAUTH_CLIENT_ID")
    csec = os.environ.get(f"{prefix}_OAUTH_CLIENT_SECRET") or os.environ.get("YT_OAUTH_CLIENT_SECRET")

    if not refresh:
        return {"market": su, "status": "ERROR", "error": f"{prefix}_OAUTH_REFRESH_TOKEN not found"}

    data = urllib.parse.urlencode({
        "client_id": cid, "client_secret": csec,
        "refresh_token": refresh, "grant_type": "refresh_token",
    }).encode("utf-8")
    req = urllib.request.Request(TOKEN_URI, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            tok = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"market": su, "status": "ERROR", "error": f"Refresh token failed: {e}"}

    access = tok.get("access_token")
    yt_url = "https://www.googleapis.com/youtube/v3/channels?part=snippet,status,statistics&mine=true"
    req2 = urllib.request.Request(yt_url, headers={"Authorization": f"Bearer {access}"})
    try:
        with urllib.request.urlopen(req2, timeout=20) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"market": su, "status": "ERROR", "error": f"YouTube API error: {e}"}

    items = resp.get("items", [])
    if not items:
        return {"market": su, "status": "ERROR", "error": "No channel found"}

    ch = items[0]
    return {
        "market": su,
        "status": "ACTIVE ✅",
        "channelId": ch.get("id"),
        "title": ch.get("snippet", {}).get("title"),
        "customUrl": ch.get("snippet", {}).get("customUrl"),
        "country": ch.get("snippet", {}).get("country"),
        "subscriberCount": ch.get("statistics", {}).get("subscriberCount"),
        "videoCount": ch.get("statistics", {}).get("videoCount"),
    }


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    market = sys.argv[2] if len(sys.argv) > 2 else ""

    if cmd == "exchange":
        raw = sys.argv[3] if len(sys.argv) > 3 else ""
        ok, res = exchange_and_save(market, raw)
        if ok:
            print("[SUCCESS]", json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print("[ERROR]", res)
            sys.exit(1)
    elif cmd == "verify":
        res = verify_market(market)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif cmd == "verify-all":
        for m in ["en", "jp", "kr"]:
            print(f"--- {m.upper()} ---")
            print(json.dumps(verify_market(m), indent=2, ensure_ascii=False))
