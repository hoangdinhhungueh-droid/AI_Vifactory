# app/services/trend_sources_v5.py - FREE non-fiction trend source adapters (S1 RE-POINT v5, 25/06).
# Cluster (1) of Phase 1 build per design subpage "S1 Trend Engine Re-Point 2026".
#   Goal: replace fiction story_scope candidate sourcing with REAL external demand
#   signals for the 4 non-fiction themes (business / history / true_crime / psychology)
#   across EN (US/GB/AU/CA/NZ) + JP + KR. ALL sources are FREE / 0-key:
#     - Wikimedia Pageviews REST  : pageview_spike (recent-7d vs prior-90d baseline)
#     - Apple Podcasts RSS charts : chart_presence (genre rank)
#     - Google News theme RSS     : localized demand corroboration (cross_source)
#   Naver DataLab (KR) is cluster (2) - needs NAVER_CLIENT_ID/SECRET (NOT in this file).
#
# IMPORTANT: this module is ADDITIVE and NOT yet wired into the live pipeline
#   (trend_discovery.discover_candidates). It exposes pure adapters + a combiner so
#   cluster (3) scoring-v5 can consume it after Brain-DB schema sign-off. Zero risk to
#   the running weekly cron. Smoke test: python -m app.services.trend_sources_v5 US,JP
#
# Anti-bias (design 4.6): candidates come ONLY from these external signals - NO internal
#   seed list and NO reference to previously-scored keywords. Downstream scoring requires
#   cross_source >= 2 independent corroboration before a candidate is trusted, which is
#   what breaks the old self-seeding -> keyword-repeat feedback loop.

import re
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Wikimedia API policy requires a descriptive User-Agent. No API key needed anywhere here.
_UA = {"User-Agent": "video-factory-trend/5.0 (+https://vifactory.com; admin@vifactory.com)"}

THEMES = ("business", "history", "true_crime", "psychology", "scam_fraud_gambling")

# EN markets share en.wikipedia + English queries; JP/KR localized.
WIKI_PROJECT = {
    "US": "en.wikipedia", "GB": "en.wikipedia", "AU": "en.wikipedia",
    "CA": "en.wikipedia", "NZ": "en.wikipedia",
    "JP": "ja.wikipedia", "KR": "ko.wikipedia",
}
APPLE_COUNTRY = {
    "US": "us", "GB": "gb", "AU": "au", "CA": "ca", "NZ": "nz",
    "JP": "jp", "KR": "kr",
}
# Apple Podcasts genre ids (documented heuristic proxies per theme; not an exact 1:1).
APPLE_GENRE = {"true_crime": 1488, "business": 1321, "history": 1462, "psychology": 1304}

# hl/gl for localized Google News RSS (same shape as trend_discovery._gnews).
GNEWS_LOCALE = {
    "US": ("en-US", "US"), "GB": ("en-GB", "GB"), "AU": ("en-AU", "AU"),
    "CA": ("en-CA", "CA"), "NZ": ("en-NZ", "NZ"),
    "JP": ("ja", "JP"), "KR": ("ko", "KR"),
}
# Non-fiction theme queries (replace the OLD fiction family-betrayal query).
THEME_QUERIES = {
    "en": {
        "business": "company collapse OR bankruptcy OR corporate scandal OR rise and fall",
        "history": "what happened to OR historical mystery OR declassified OR forgotten history",
        "true_crime": "true crime case OR cold case OR fraud trial OR investigation",
        "psychology": "psychology of OR human behavior OR cognitive bias OR why people", "scam_fraud_gambling": "scam OR fraud OR Ponzi scheme OR gambling addiction OR investment fraud",
    },
    "ja": {
        "business": "\u4f01\u696d \u7834\u7dbb OR \u4e0d\u6b63 OR \u7d4c\u55b6\u7834\u7dbb OR \u7c89\u98fe",
        "history": "\u6b74\u5386 \u8b0e OR \u305d\u306e\u5f8c OR \u672a\u89e3\u6c7a OR \u6a5f\u5bc6\u89e3\u9664",
        "true_crime": "\u4e8b\u4ef6 OR \u8a50\u6b3a \u4e8b\u4ef6 OR \u672a\u89e3\u6c7a\u4e8b\u4ef6 OR \u88c1\u5224",
        "psychology": "\u5fc3\u7406\u5b66 OR \u4eba\u9593 \u884c\u52d5 OR \u8a8d\u77e5\u30d0\u30a4\u30a2\u30b9 OR \u306a\u305c\u4eba\u306f", "scam_fraud_gambling": "\u8a50\u6b3a OR \u6295\u8cc7\u8a50\u6b3a OR \u30cd\u30ba\u30df\u8b1b OR \u30ae\u30e3\u30f3\u30d6\u30eb\u4f9d\u5b58",
    },
    "ko": {
        "business": "\uae30\uc5c5 \ubd95\uad34 OR \ud30c\uc0b0 OR \ud68c\uac04 \ubd80\uc815 OR \uc0ac\uae30",
        "history": "\uc5ed\uc0ac \ubbf8\uc2a4\ud1a0\ub9ac OR \uadf8 \ud6c4 OR \ubc94\ud574\uacb0 OR \uae30\ubc00 \ud574\uc81c",
        "true_crime": "\uc0ac\uac74 OR \uc0ac\uae30 \uc0ac\uac74 OR \ubc94\uc81c \uc0ac\uac74 OR \uc7ac\ud310",
        "psychology": "\uc2ec\ub9ac\ud559 OR \uc778\uac04 \ud589\ub3d9 OR \uc778\uc9c0 \ud3b8\ud5a5 OR \uc0ac\ub78c\ub4e4\uc740 \uc65c", "scam_fraud_gambling": "\uc0ac\uae30 OR \ud1a0\uc790 \uc0ac\uae30 OR \ud1f0\uc9c0 \uc0ac\uae30 OR \ub458\ubbf1 \uc911\ub3c5",
    },
}


def _lang_for(market):
    return WIKI_PROJECT.get(market, "en.wikipedia").split(".")[0]  # en / ja / ko


def _slug(term):
    t = (term or "").strip().lower()
    if re.search(r"[^\x00-\x7f]", t):  # non-ASCII (JP/KR) -> keep normalized text
        return re.sub(r"\s+", " ", t).strip()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def _httpx():
    try:
        import httpx
        return httpx
    except Exception as e:
        logger.warning("[v5src] httpx unavailable: %s", e)
        return None


# ---------------------------------------------------------------- Wikimedia Pageviews
def wiki_top_articles(project, day=None, limit=40, timeout=15.0):
    """Top viewed articles for a project on a UTC day (default 2 days ago so the dump
    is published). Returns [{article, views}]. Free, no key."""
    httpx = _httpx()
    if httpx is None:
        return []
    d = day or (datetime.now(timezone.utc) - timedelta(days=2))
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
           + project + "/all-access/" + d.strftime("%Y/%m/%d"))
    try:
        r = httpx.get(url, headers=_UA, timeout=timeout, follow_redirects=True)
        if r.status_code != 200:
            logger.warning("[v5src] wiki top %s http %s", project, r.status_code)
            return []
        items = (((r.json().get("items") or [{}])[0]).get("articles") or [])
        out = []
        for it in items:
            art = str(it.get("article", "")).replace("_", " ").strip()
            if not art or art == "Main Page" or art.startswith("Special:"):
                continue
            out.append({"article": art, "views": int(it.get("views", 0))})
            if len(out) >= limit:
                break
        return out
    except Exception as e:
        logger.warning("[v5src] wiki top failed %s: %s", project, e)
        return []


def wiki_article_spike(project, article, timeout=15.0):
    """pageview_spike 0..1 = recent-7d avg vs prior-90d baseline for one article.
    Returns {spike, recent_avg, base_avg} or None."""
    httpx = _httpx()
    if httpx is None:
        return None
    from urllib.parse import quote
    import math
    end = datetime.now(timezone.utc) - timedelta(days=1)
    start = end - timedelta(days=97)
    art = quote(article.replace(" ", "_"), safe="")
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
           + project + "/all-access/all-agents/" + art + "/daily/"
           + start.strftime("%Y%m%d") + "/" + end.strftime("%Y%m%d"))
    try:
        r = httpx.get(url, headers=_UA, timeout=timeout, follow_redirects=True)
        if r.status_code != 200:
            return None
        views = [int(x.get("views", 0)) for x in (r.json().get("items") or [])]
        if len(views) < 14:
            return None
        recent = views[-7:]
        base = views[:-7]
        recent_avg = sum(recent) / max(1, len(recent))
        base_avg = sum(base) / max(1, len(base))
        if base_avg <= 0:
            spike = 1.0 if recent_avg > 0 else 0.0
        else:
            ratio = recent_avg / base_avg
            spike = max(0.0, min(1.0, math.log2(max(ratio, 0.25)) / 2.0))  # 2x~0.5, >=4x->1
        level = max(0.0, min(1.0, (math.log10(recent_avg + 1.0) - 2.0) / 3.0))
        return {"spike": round(spike, 4), "recent_avg": round(recent_avg, 1),
                "base_avg": round(base_avg, 1), "level": round(level, 4)}
    except Exception as e:
        logger.warning("[v5src] wiki spike failed %s/%s: %s", project, article, e)
        return None


# ---------------------------------------------------------------- Apple Podcasts charts
def apple_chart(market, theme, limit=25, timeout=15.0):
    """Top podcasts for a theme genre in a country (free iTunes RSS). Returns
    [{name, rank}] -> chart_presence signal."""
    httpx = _httpx()
    if httpx is None:
        return []
    country = APPLE_COUNTRY.get(market)
    genre = APPLE_GENRE.get(theme)
    if not country or not genre:
        return []
    url = ("https://itunes.apple.com/" + country + "/rss/toppodcasts/limit="
           + str(limit) + "/genre=" + str(genre) + "/json")
    try:
        r = httpx.get(url, headers=_UA, timeout=timeout, follow_redirects=True)
        if r.status_code != 200:
            logger.warning("[v5src] apple %s/%s http %s", country, theme, r.status_code)
            return []
        entries = (((r.json().get("feed") or {}).get("entry")) or [])
        out = []
        for rank, e in enumerate(entries, 1):
            nm = (((e.get("im:name") or {}).get("label")) or "").strip()
            if nm:
                out.append({"name": nm, "rank": rank})
        return out
    except Exception as e:
        logger.warning("[v5src] apple failed %s/%s: %s", country, theme, e)
        return []


# ---------------------------------------------------------------- Google News theme RSS
def gnews_url(query, hl, gl):
    from urllib.parse import quote_plus
    return ("https://news.google.com/rss/search?q=" + quote_plus(query)
            + "&hl=" + hl + "&gl=" + gl + "&ceid=" + gl + ":" + hl.split("-")[0])


def gnews_theme_titles(market, theme, timeout=15.0, max_titles=20):
    httpx = _httpx()
    if httpx is None:
        return []
    hl, gl = GNEWS_LOCALE.get(market, ("en-US", "US"))
    q = (THEME_QUERIES.get(_lang_for(market)) or THEME_QUERIES["en"]).get(theme)
    if not q:
        return []
    try:
        r = httpx.get(gnews_url(q, hl, gl), headers=_UA, timeout=timeout, follow_redirects=True)
        if r.status_code != 200 or not r.text:
            return []
        titles = []
        for b in re.findall(r"<item\b[^>]*>(.*?)</item>", r.text, re.S):
            m = re.search(r"<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", b, re.S)
            if m and m.group(1).strip():
                titles.append(re.sub(r"<[^>]+>", "", m.group(1)).strip())
            if len(titles) >= max_titles:
                break
        return titles
    except Exception as e:
        logger.warning("[v5src] gnews failed %s/%s: %s", market, theme, e)
        return []


# ---------------------------------------------------------------- Combiner (cluster 1)
THEME_CATEGORIES = {
    "business": ["Defunct companies", "Corporate scandals", "Business executives"],
    "history": ["Former empires", "Ancient peoples", "Historical figures"],
    "true_crime": ["Serial killers", "Fraudsters", "Unsolved murders"],
    "psychology": ["Cognitive biases", "Psychological concepts", "Mental disorders"], "scam_fraud_gambling": ["Confidence tricks", "Fraud", "Gambling"],
}


def wiki_category_members(project, category, limit=12, timeout=15.0):
    httpx = _httpx()
    if httpx is None:
        return []
    host = project + ".org"
    url = ("https://" + host + "/w/api.php?action=query&list=categorymembers"
           "&cmtitle=Category:" + category.replace(" ", "_")
           + "&cmtype=page&cmlimit=" + str(limit) + "&format=json")
    try:
        r = httpx.get(url, headers=_UA, timeout=timeout, follow_redirects=True)
        if r.status_code != 200:
            return []
        members = (((r.json().get("query") or {}).get("categorymembers")) or [])
        out = []
        for m in members:
            t = str(m.get("title", "")).strip()
            if t and ":" not in t:
                out.append(t)
        return out
    except Exception as e:
        logger.warning("[v5src] category failed %s/%s: %s", project, category, e)
        return []


# Curated marquee "attraction floor" per theme - high-pageview evergreen topics that
# carry timeless pull even when not trending. Exact Wikipedia article titles so QID /
# pageview resolution stays valid. Downstream ranks the whole pool by sustained-interest
# level, so weak stubs sink and these classics surface.
SEED_TITLES = {
    "business": ["Enron scandal", "Theranos", "Lehman Brothers", "FTX", "WeWork",
                 "Bernard Madoff", "Wirecard", "Blockbuster LLC", "Eastman Kodak", "Nokia"],
    "history": ["Roman Empire", "Ottoman Empire", "Byzantine Empire", "Mongol Empire",
                "Ancient Egypt", "British Empire", "Library of Alexandria",
                "Fall of Constantinople", "Pompeii", "Genghis Khan"],
    "true_crime": ["Ted Bundy", "Jeffrey Dahmer", "Zodiac Killer", "Jack the Ripper",
                   "H. H. Holmes", "Golden State Killer", "D. B. Cooper", "Black Dahlia",
                   "John Wayne Gacy", "Dennis Rader"],
    "psychology": ["Stanford prison experiment", "Milgram experiment",
                   "Stanford marshmallow experiment", "Cognitive dissonance",
                   "Maslow's hierarchy of needs", "Classical conditioning",
                   "Stockholm syndrome", "Confirmation bias", "Bystander effect",
                   "Cognitive bias"], "scam_fraud_gambling": ["Ponzi scheme", "Pyramid scheme", "Bernie Madoff", "Advance-fee scam", "Lottery scam", "Match fixing", "Problem gambling", "Confidence trick", "Pig butchering scam", "Cryptocurrency and crime"],
}

SEED_TITLES_JP = {
    "business": ["オリンパス事件", "東芝不正会計事件", "ライブドア事件", "レーマン・ショック", "ワールドコム", "エンロン", "カネボウ", "山一証券"],
    "history": ["戦国時代 (日本)", "関ヶ原の戦い", "明治維新", "源平合戦", "邪马台国", "太平記", "承久の乱", "応仁の乱"],
    "true_crime": ["オウム真理教", "地下鉄サリン事件", "松本サリン事件", "北九州監禁殺人事件", "和歌山毒物カレー事件", "三芃銀行人質事件", "宮崎事件", "福島悪魔っ子"],
    "psychology": ["引きこもり", "過労死", "孤独死", "認知的不協和", "マシュマロ実験", "アスペルガー症候群", "スタンフォード監獄実験", "ミルグラムの実験"],
    "scam_fraud_gambling": ["振り込め詐欺", "オレオレ詐欺", "闇金融", "特殊詐欺", "投資詐欺", "ヤミ金", "マルチ商法", "靈感商法"],
}

SEED_TITLES_KR = {
    "business": ["삼성그룹", "대우그룹", "SK그룹", "현대그룹", "대한항공 떥족 회항", "남양유업", "STX", "동양그룹"],
    "history": ["임진웜란", "광주민주화운동", "한국전쟁", "일제강점기", "고려", "조선", "병자호란", "을미사변"],
    "true_crime": ["화성 연쇄살인사건", "유영철", "N번방 사건", "지존파", "김대한", "유명철"],
    "psychology": ["교육열", "헬조선", "삼포세대", "인지부조화", "스톡홀증 후군", "방관자 효과", "마시멜로 실험", "밀그램 실험"],
    "scam_fraud_gambling": ["보이스피싱", "전세사기", "다단계 판매", "신용카드 사기", "도박 중독", "폰지 사기", "피라미드 사기", "투자 사기"],
}

SEED_TITLES_BY_MARKET = {
    "US": SEED_TITLES,
    "JP": SEED_TITLES_JP,
    "KR": SEED_TITLES_KR,
}


def collect_evergreen(market="US", themes=THEMES, per_category=8, max_total=80):
    """Evergreen candidate pool = curated marquee SEED_TITLES (quality floor) FIRST,
    then Wikipedia category members. Each item carries its KNOWN theme so downstream
    classify cannot wrongly drop it as off_theme (coverage fix). Final pageview-rank +
    cap happens in run_discovery_v5 (evergreen prioritised, sort by sustained level)."""
    proj = WIKI_PROJECT.get(market, "en.wikipedia")
    seen, out = set(), []
    market_seeds = SEED_TITLES_BY_MARKET.get(market, SEED_TITLES)
    for th in themes:
        for t in (market_seeds.get(th) or []):
            key = t.lower()
            if key not in seen:
                seen.add(key)
                out.append({"t": t, "theme": th})
    for th in themes:
        for cat in (THEME_CATEGORIES.get(th) or []):
            for t in wiki_category_members(proj, cat, limit=per_category):
                key = t.lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append({"t": t, "theme": th})
                if len(out) >= max_total:
                    return out
    return out


def collect_free_signals(markets=("US",), themes=THEMES, spike_topn=8):
    """Gather FREE external signals per market. Returns
    {market: {wiki_spikes:[...], themes:{theme:{apple_chart, gnews_titles}}}}.
    No internal seeds, no prior-score reference (anti-bias design 4.6)."""
    result = {}
    for market in markets:
        proj = WIKI_PROJECT.get(market, "en.wikipedia")
        spikes = []
        for a in wiki_top_articles(proj)[:spike_topn]:
            s = wiki_article_spike(proj, a["article"])
            if s:
                spikes.append({"article": a["article"], "views": a["views"], **s})
        spikes.sort(key=lambda x: x.get("spike", 0), reverse=True)
        per_theme = {th: {"apple_chart": apple_chart(market, th),
                          "gnews_titles": gnews_theme_titles(market, th)}
                     for th in themes}
        result[market] = {"wiki_spikes": spikes, "themes": per_theme}
    return result


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    mkts = sys.argv[1].split(",") if len(sys.argv) > 1 else ["US"]
    data = collect_free_signals(mkts)
    for mk, d in data.items():
        print("== MARKET", mk, "==")
        for s in d["wiki_spikes"][:5]:
            print("   wiki:", s["article"], "| spike", s["spike"], "| views", s["views"])
        for th, td in d["themes"].items():
            print("   theme", th, "| apple", len(td["apple_chart"]),
                  "| gnews", len(td["gnews_titles"]),
                  "| apple_top", [x["name"] for x in td["apple_chart"][:2]])


# --- SerpApi PRIMARY signal source (Gate 1/2 redesign, 22/07) --------------
# Google Trends related_queries RISING via SerpApi is treated as the PRIMARY
# v5 signal (higher-confidence than free Wikimedia/Apple/GNews spikes). It
# shares the shared monthly serp_budget meter with the legacy discover
# engine. Returns [] as soon as that budget is spent (or on any failure) so
# run_discovery_v5 automatically falls back to collect_free_signals /
# collect_evergreen, which keep running in parallel regardless.
SERPAPI_V5_GEO = {"US": "US", "JP": "JP", "KR": "KR", "GB": "GB", "DE": "DE", "AU": "AU", "CA": "CA", "NZ": "NZ"}

# FAN-OUT FIX (06/08/2026 decision - see Decisions Log): the original 5 themes x 3
# seeds x N markets was burning ~45 SerpApi calls per single raw-pool run (48 with
# gtrends_daily), which alone exceeded the sustainable ~8/day average for a 250/month
# free plan. Cut to 1 seed/theme (5 calls/market instead of 15). gtrends_daily no
# longer uses SerpApi at all (moved to the free RSS feed in trend_free_signals.py),
# and 2 new zero-cost lanes (youtube_autocomplete/google_autocomplete, see
# trend_gate_ai.py) now cover part of the discovery breadth the extra seeds used to
# provide, at zero quota cost.
SERPAPI_V5_SEEDS = {
    "business": ["business scandal"],
    "history": ["ancient history mystery"],
    "true_crime": ["true crime case"],
    "psychology": ["psychology of manipulation"],
    "scam_fraud_gambling": ["ponzi scheme"],
}


# --- Junk filter for SerpApi related-queries (added 26/07/2026) ------------
# WHY: live audit of the rising list found dev-error strings ("http error 502.5
# ancm out-of-process startup failure"), exam questions, game/movie titles and
# shopping intents. Those must never reach the keyword library and the Notion AI
# gate should not waste reasoning budget on them.
import os
import string
import logging

logger = logging.getLogger(__name__)

JUNK_SUB = ["http", "www.", ".com", ".net", ".org", ".gov", "asp.net", "localhost",
            "startup failure", "according to", "which of the following",
            "eligible for exemption", "near me", "for sale"]

JUNK_TOKENS = set(["error", "errors", "iis", "nginx", "apk", "pdf", "download",
                   "login", "coupon", "worksheet", "quiz", "answers", "reddit",
                   "wikipedia", "youtube", "tiktok", "netflix", "imdb", "trailer",
                   "movie", "film", "game", "games", "season", "episode", "cast",
                   "actor", "actress", "lyrics", "template", "price", "cheap",
                   "meme", "roblox", "gta", "walkthrough", "cheats", "salary",
                   "jobs", "job", "stock", "ticker"])


def serp_query_is_junk(q):
    """True when a SerpApi rising query is not usable as a video topic."""
    q = (q or "").strip()
    if len(q) < 4 or len(q) > 70:
        return True
    ql = q.lower()
    for sub in JUNK_SUB:
        if sub in ql:
            return True
    toks = [t.strip(string.punctuation) for t in ql.split()]
    if len(toks) > 7:
        return True
    if JUNK_TOKENS.intersection(toks):
        return True
    if sum(1 for ch in q if ch.isdigit()) >= 4:
        return True
    return False


def serpapi_rising_candidates(market="US", pool=None, timeout=20.0):
    """SerpApi related_queries RISING (Google Trends) - PRIMARY v5 signal.
    Now: junk-filtered, deduped and LOUDLY logged per lane, so a silent empty
    return can never again be mistaken for "SerpApi has no trends today".
    """
    try:
        from app.services import serp_budget
    except Exception:
        logger.warning("[serpapi-v5] serp_budget import failed")
        return []
    pool = int(pool or os.getenv("SERPAPI_V5_POOL", "30"))
    window = os.getenv("SERPAPI_V5_WINDOW", "now 7-d")
    geo = SERPAPI_V5_GEO.get((market or "US").upper(), "US")
    out, seen, junk, calls, empty_seeds = [], set(), 0, 0, []
    for theme, seeds in SERPAPI_V5_SEEDS.items():
        for seed in seeds:
            try:
                params = {"engine": "google_trends", "q": seed,
                          "data_type": "RELATED_QUERIES", "date": window, "geo": geo}
                r = serp_budget.serp_get(params, timeout=timeout)
                calls += 1
                if r is None:
                    logger.warning("[serpapi-v5] %s STOPPED after %d calls (no key or "
                                   "budget/http block) kept=%d", market, calls, len(out))
                    return out
                if r.status_code != 200:
                    logger.warning("[serpapi-v5] %s seed=%s http=%s", market, seed,
                                   r.status_code)
                    continue
                rq = (r.json().get("related_queries") or {})
                rising = rq.get("rising") or []
                if not rising:
                    empty_seeds.append(seed)
                for x in rising:
                    q = str(x.get("query", "")).strip()
                    if not q:
                        continue
                    key = q.lower()
                    if key in seen:
                        continue
                    if serp_query_is_junk(q):
                        junk += 1
                        continue
                    seen.add(key)
                    out.append({"article": q, "views": 0, "spike": 1.0, "level": 1.0,
                                "theme_hint": theme, "lane": "serpapi", "seed": seed,
                                "rise": x.get("value") or x.get("extracted_value")})
            except Exception as e:
                logger.warning("[serpapi-v5] %s seed=%s failed: %s", market, seed, e)
                continue
            if len(out) >= pool:
                logger.info("[serpapi-v5] %s POOL_FULL kept=%d junk=%d calls=%d",
                            market, len(out), junk, calls)
                return out
    logger.info("[serpapi-v5] %s DONE kept=%d junk=%d calls=%d empty_seeds=%d",
                market, len(out), junk, calls, len(empty_seeds))
    return out
