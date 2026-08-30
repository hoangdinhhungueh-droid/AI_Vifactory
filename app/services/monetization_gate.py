"""monetization_gate.py - Build-first monetization tracker (Phase 3 distribution).

PRINCIPLE (user-locked 21/06/2026): every channel launches in BUILD mode with
monetization OFF. Monetization is enabled automatically ONLY when the platform's
eligibility threshold is met. This module is the single source of truth for those
thresholds and the build -> monetize decision. It does NOT enable anything by
itself (enabling stays a manual portal/OAuth step); it tells the pipeline + the
operator (Telegram) exactly when a channel has crossed the line.

FREE, deterministic, NO network as a library. The optional CLI reads a per-run
stats file and writes monetization_status.json (+ optional Telegram ping).

Thresholds (Q2/2026 sources):
  youtube  - YouTube Partner Program. Vietnam is in the monetized-markets list.
             full  : 1,000 subs AND (4,000 public watch-hours / 12mo
                                      OR 10,000,000 Shorts views / 90d)
             early : 500 subs + 3 public uploads / 90d AND
                     (3,000 watch-hours / 12mo OR 3,000,000 Shorts views / 90d)
  dailymotion - Partner Program: >=1,000 views to unlock monetization; $100 payout.
  facebook    - Content Monetization Program (CMP) beta, payable FROM VIETNAM:
                Professional Mode + >=10,000 followers
                + >=600,000 view-minutes / 60d + original content; $50 payout min.

Distribution-only channels (cannot monetize/withdraw from a Vietnam IP) are
listed in NON_MONETIZABLE and always resolve to mode='distribution_only'.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

# Channels that exist purely as distribution funnels from a Vietnam IP.
NON_MONETIZABLE = {"tiktok", "instagram", "instagram_reels", "spotify"}

THRESHOLDS = {
    "youtube": {
        "full": {"subscribers": 1000, "watch_hours_12mo": 4000,
                 "shorts_views_90d": 10_000_000},
        "early": {"subscribers": 500, "public_uploads_90d": 3,
                  "watch_hours_12mo": 3000, "shorts_views_90d": 3_000_000},
    },
    "dailymotion": {"views_total": 1000, "payout_min_usd": 100},
    "facebook": {"followers": 10000, "view_minutes_60d": 600000,
                 "professional_mode": True, "payout_min_usd": 50},
}


def _norm(channel_type):
    c = (channel_type or "").strip().lower()
    if c in ("facebook_reels", "fb", "meta", "meta_reels"):
        return "facebook"
    if c in ("youtube_shorts", "yt"):
        return "youtube"
    if c in ("dailymotion", "dm"):
        return "dailymotion"
    return c


def evaluate(channel_type, stats):
    """Return a build/monetize verdict for one channel.

    stats: dict of observed metrics. Missing keys count as 0 / False.
    Returns: {channel, monetizable, eligible, mode, missing, thresholds, stats}.
    """
    ch = _norm(channel_type)
    stats = stats or {}

    if ch in NON_MONETIZABLE:
        return {"channel": ch, "monetizable": False, "eligible": False,
                "mode": "distribution_only", "missing": [],
                "thresholds": {}, "stats": stats}

    if ch == "youtube":
        subs = stats.get("subscribers", 0)
        wh = stats.get("watch_hours_12mo", 0)
        sv = stats.get("shorts_views_90d", 0)
        up = stats.get("public_uploads_90d", 0)
        full = THRESHOLDS["youtube"]["full"]
        early = THRESHOLDS["youtube"]["early"]
        full_ok = subs >= full["subscribers"] and (
            wh >= full["watch_hours_12mo"] or sv >= full["shorts_views_90d"])
        early_ok = (subs >= early["subscribers"]
                    and up >= early["public_uploads_90d"]
                    and (wh >= early["watch_hours_12mo"]
                         or sv >= early["shorts_views_90d"]))
        if full_ok:
            mode = "monetize_full"
        elif early_ok:
            mode = "monetize_early"
        else:
            mode = "build"
        missing = []
        if mode == "build":
            if subs < early["subscribers"]:
                missing.append("subscribers %d/%d" % (subs, early["subscribers"]))
            if wh < early["watch_hours_12mo"] and sv < early["shorts_views_90d"]:
                missing.append("watch_hours %d/%d OR shorts_views %d/%d"
                               % (wh, early["watch_hours_12mo"], sv,
                                  early["shorts_views_90d"]))
            if up < early["public_uploads_90d"]:
                missing.append("public_uploads_90d %d/%d"
                               % (up, early["public_uploads_90d"]))
        return {"channel": "youtube", "monetizable": True,
                "eligible": mode != "build", "mode": mode,
                "missing": missing, "thresholds": THRESHOLDS["youtube"],
                "stats": stats}

    if ch == "dailymotion":
        t = THRESHOLDS["dailymotion"]
        views = stats.get("views_total", 0)
        eligible = views >= t["views_total"]
        missing = [] if eligible else ["views_total %d/%d" % (views, t["views_total"])]
        return {"channel": "dailymotion", "monetizable": True,
                "eligible": eligible,
                "mode": "monetize" if eligible else "build",
                "missing": missing, "thresholds": t, "stats": stats}

    if ch == "facebook":
        t = THRESHOLDS["facebook"]
        fol = stats.get("followers", 0)
        vm = stats.get("view_minutes_60d", 0)
        pro = bool(stats.get("professional_mode", False))
        eligible = fol >= t["followers"] and vm >= t["view_minutes_60d"] and pro
        missing = []
        if not eligible:
            if fol < t["followers"]:
                missing.append("followers %d/%d" % (fol, t["followers"]))
            if vm < t["view_minutes_60d"]:
                missing.append("view_minutes_60d %d/%d" % (vm, t["view_minutes_60d"]))
            if not pro:
                missing.append("professional_mode off")
        return {"channel": "facebook", "monetizable": True,
                "eligible": eligible,
                "mode": "monetize" if eligible else "build",
                "missing": missing, "thresholds": t, "stats": stats}

    return {"channel": ch, "monetizable": False, "eligible": False,
            "mode": "unknown", "missing": ["unknown channel '%s'" % ch],
            "thresholds": {}, "stats": stats}


def should_enable_monetization(channel_type, stats):
    return bool(evaluate(channel_type, stats).get("eligible"))


def evaluate_all(stats_by_channel):
    return {c: evaluate(c, s) for c, s in (stats_by_channel or {}).items()}


# ---- optional CLI -----------------------------------------------------------
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


def _telegram(msg):
    """Send message to Telegram via httpx (avoids exposing token in subprocess)."""
    tok = os.getenv("VF_TG_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not tok or not chat or not msg:
        return
    try:
        import httpx
        url = f"https://api.telegram.org/bot{tok}/sendMessage"
        payload = {"chat_id": chat, "text": msg}
        with httpx.Client(timeout=10) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
    except Exception:
        pass


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    stats_file = argv[0] if argv else "monetization_stats.json"
    out_file = argv[1] if len(argv) > 1 else "monetization_status.json"
    if not os.path.exists(stats_file):
        print("missing stats file: " + stats_file, file=sys.stderr)
        return 2
    stats_by_channel = json.loads(open(stats_file).read())
    result = evaluate_all(stats_by_channel)
    out = {"generated_at": datetime.now(timezone.utc).isoformat(),
           "channels": result}
    with open(out_file, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    flipped = [r["channel"] for r in result.values() if r.get("eligible")]
    if flipped:
        _load_env()
        _telegram("\U0001f4b0 MONETIZATION READY: " + ", ".join(flipped)
                  + " crossed threshold -> enable monetization in portal.")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
