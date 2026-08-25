"""zernio_upload.py - Distribution adapter via Zernio unified social API (Phase 3).

Zernio (https://zernio.com, base https://zernio.com/api/v1, Bearer API key) posts
one JSON payload to multiple platforms. We use the 2 free connected accounts:
  slot 1 = TikTok            (main funnel)
  slot 2 = Facebook Page     (Meta; connecting the FB Page also lets us mirror
                              to the linked Instagram account for FREE -> no
                              separate Instagram slot is needed)

Reads seo_payloads.json (produced by app/services/seo_metadata.py) and composes
one Zernio create-post request per connected target. Media must be a publicly
reachable URL (set VF_PUBLIC_MEDIA_BASE, e.g. an R2/CDN base); without it the
request is composed with media=null for manual attachment.

NO network unless ZERNIO_API_KEY is set. Default = DRY-RUN: it writes
zernio_request.json into the episode dir so the exact payload can be inspected
before any OAuth/account is connected.

Usage: PYTHONPATH=/root/video_factory python3 scripts/zernio_upload.py <episode_dir>
"""
import json
import os
import sys
from datetime import datetime, timezone

ZERNIO_BASE = os.getenv("ZERNIO_API_BASE", "https://zernio.com/api/v1")

# (seo_payloads.json key, Zernio platform name, account-id env var)
TARGETS = [
    ("tiktok", "tiktok", "ZERNIO_TIKTOK_ACCOUNT_ID"),
    ("facebook_reels", "facebook", "ZERNIO_FACEBOOK_ACCOUNT_ID"),
    ("instagram_reels", "instagram", "ZERNIO_INSTAGRAM_ACCOUNT_ID"),
]


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


def build_post_request(payload, *, platform, account_id, video_url=None,
                       schedule_at=None):
    """Pure: compose a Zernio create-post body from one seo payload. No network."""
    caption = payload.get("description") or payload.get("title") or ""
    hashtags = payload.get("hashtags") or []
    body = {
        "platform": platform,
        "accountId": account_id,
        "content": caption,
        "media": ([{"type": "video", "url": video_url}] if video_url else []),
        "firstComment": (" ".join(hashtags) or None),
        "scheduledAt": schedule_at,
        "meta": {
            "ai_disclosure": bool(payload.get("ai_disclosure")),
            "made_for_kids": False,
            "loop_ending_required": payload.get("loop_ending_required", False),
            "cta_burn_in_last_5s": payload.get("cta_burn_in_last_5s", False),
        },
    }
    return {k: v for k, v in body.items() if v is not None}


def _public_media_url(episode_dir, target_file="final_916.mp4"):
    base = os.getenv("VF_PUBLIC_MEDIA_BASE")
    if not base:
        return None
    eid = os.path.basename(os.path.normpath(episode_dir))
    return base.rstrip("/") + "/" + eid + "/" + target_file


def compose_all(episode_dir):
    """Build every Zernio request for the connected targets. No network."""
    with open(os.path.join(episode_dir, "seo_payloads.json")) as f:
        payloads = json.load(f)
    video_url = _public_media_url(episode_dir)
    requests, skipped = [], []
    for seo_key, platform, env_var in TARGETS:
        payload = payloads.get(seo_key)
        if not payload:
            skipped.append({"platform": platform, "reason": "no seo payload " + seo_key})
            continue
        account_id = os.getenv(env_var)
        if not account_id:
            skipped.append({"platform": platform,
                            "reason": "account not connected (" + env_var + " unset)"})
            continue
        requests.append({"platform": platform, "endpoint": ZERNIO_BASE + "/posts",
                         "body": build_post_request(payload, platform=platform,
                                                    account_id=account_id,
                                                    video_url=video_url)})
    return requests, skipped, video_url


def _execute(req, api_key):
    import httpx
    headers = {"Authorization": "Bearer " + api_key,
               "Content-Type": "application/json"}
    r = httpx.post(req["endpoint"], headers=headers, json=req["body"], timeout=120.0)
    return {"platform": req["platform"], "status_code": r.status_code,
            "response": (r.json() if r.headers.get("content-type", "").startswith(
                "application/json") else r.text[:500])}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    episode_dir = argv[0] if argv else "/var/vf/episodes/betrayal-revenge-quiet-2026-ep001"
    _load_env()
    api_key = os.getenv("ZERNIO_API_KEY")
    requests, skipped, video_url = compose_all(episode_dir)
    out = {"adapter": "zernio", "base": ZERNIO_BASE,
           "video_url": video_url,
           "generated_at": datetime.now(timezone.utc).isoformat(),
           "requests": requests, "skipped": skipped}
    if not api_key:
        out["mode"] = "DRY_RUN"
        out["note"] = "ZERNIO_API_KEY unset -> composed only, nothing posted."
    else:
        out["mode"] = "EXECUTED"
        results = []
        for req in requests:
            try:
                results.append(_execute(req, api_key))
            except Exception as e:
                results.append({"platform": req["platform"], "error": str(e)})
        out["results"] = results
    with open(os.path.join(episode_dir, "zernio_request.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
