# app/services/trend_naver.py - Naver DataLab (KR) search-trend adapter. Cluster (2), S1 RE-POINT v5.
# FREE but key-gated: needs NAVER_CLIENT_ID + NAVER_CLIENT_SECRET in /root/secrets/.env
# (register at developers.naver.com). Defensive: returns [] when keys absent (mirrors the
# has_serpapi_key pattern in trend_signals.py) so the module is import-safe BEFORE keys are
# provisioned. Additive, NOT wired into the live pipeline.

import os
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv("/root/secrets/.env")
except Exception:
    pass

_ENDPOINT = "https://openapi.naver.com/v1/datalab/search"

# KR non-fiction theme search-demand probes (external signal, NOT internal scoring seeds).
NAVER_THEME_KEYWORDS = {
    "business": ["기업 파산", "회계 부정", "경영 위기"],
    "history": ["역사 미스터리", "미해결 사건", "기밀 해제"],
    "true_crime": ["사기 사건", "미제 사건", "재판"],
    "psychology": ["심리학", "인지 편향", "인간 행동"],
}


def has_naver_keys():
    return bool(os.getenv("NAVER_CLIENT_ID") and os.getenv("NAVER_CLIENT_SECRET"))


def _httpx():
    try:
        import httpx
        return httpx
    except Exception as e:
        logger.warning("[naver] httpx unavailable: %s", e)
        return None


def datalab_search(theme, timeout=15.0):
    """Return [{keyword, ratio_recent, ratio_avg, momentum}] for a KR theme via DataLab.
    momentum 0..1 = recent-4wk vs 90d-average ratio. [] if no keys / error."""
    if not has_naver_keys():
        logger.info("[naver] keys absent -> skip (theme=%s)", theme)
        return []
    httpx = _httpx()
    if httpx is None:
        return []
    kws = NAVER_THEME_KEYWORDS.get(theme) or []
    if not kws:
        return []
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=90)
    body = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "timeUnit": "week",
        "keywordGroups": [{"groupName": k, "keywords": [k]} for k in kws[:5]],
    }
    headers = {
        "X-Naver-Client-Id": os.getenv("NAVER_CLIENT_ID", ""),
        "X-Naver-Client-Secret": os.getenv("NAVER_CLIENT_SECRET", ""),
        "Content-Type": "application/json",
    }
    try:
        r = httpx.post(_ENDPOINT, headers=headers, json=body, timeout=timeout)
        if r.status_code != 200:
            logger.warning("[naver] datalab http %s: %s", r.status_code, r.text[:200])
            return []
        out = []
        for grp in (r.json().get("results") or []):
            data = grp.get("data") or []
            if not data:
                continue
            ratios = [float(d.get("ratio", 0)) for d in data]
            avg = sum(ratios) / max(1, len(ratios))
            recent = sum(ratios[-4:]) / max(1, len(ratios[-4:]))
            momentum = 0.0 if avg <= 0 else max(0.0, min(1.0, (recent / avg) / 2.0))
            out.append({"keyword": grp.get("title", ""), "ratio_recent": round(recent, 2),
                        "ratio_avg": round(avg, 2), "momentum": round(momentum, 4)})
        return out
    except Exception as e:
        logger.warning("[naver] datalab failed: %s", e)
        return []


def collect_kr_signals(themes=("business", "history", "true_crime", "psychology")):
    return {th: datalab_search(th) for th in themes}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("has_naver_keys:", has_naver_keys())
    for th, rows in collect_kr_signals().items():
        print(" ", th, "->", len(rows), "keyword groups")
