def sanitize_episode_slug(slug: str) -> str:
    """Sanitize a topic slug to lowercase snake_case [a-z0-9_]+."""
    if not slug:
        return "topic"
    s = str(slug).strip().lower()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = s.strip('_')
    if not s:
        return "topic"
    return s[:45].rstrip('_')


def get_next_episode_id(market: str = "EN", slug: str = "", offset: int = 0) -> str:
    """Generate next market-isolated sequential episode task ID (e.g. EN_EP0001_topic).
    Strictly isolated per market (EN, JP, KR, etc.).
    Single Source of Truth is Notion:
      1. Primary: Notion VF Trend Brain DB (4c101989-2400-8334-8016-01d4f463b09f) & Story Library DB (b0301989-2400-836b-bdb5-8131fea17736)
         - If Notion has episodes for this market, counts upwards from max(notion_nums).
         - If Notion is empty for this market (user reset/cleared DB), starts from EP0001.
      2. Active unexpired tasks in /var/vf/pending_tasks (to avoid collision during concurrent runs).
      3. Filesystem /var/vf/episodes (only non-archived, non-dead, active directories).
    Returns: <market>_<EPxxxx>_<name>
    """
    import os, re, json, logging
    _log = logging.getLogger("app.episode_id")
    target_market = str(market or "EN").strip().upper()
    clean_slug = sanitize_episode_slug(slug)

    def _extract_market_ep_nums(text: str, mkt: str) -> list[int]:
        if not text:
            return []
        t_up = text.upper()
        patterns = [
            rf'{mkt}_EP(\d+)',
            rf'{mkt}-EP(\d+)',
            rf'EP_{mkt}_(\d+)',
            rf'EP-{mkt}-(\d+)',
            rf'{mkt}-.*-EP(\d+)',
            rf'{mkt}_.*_EP(\d+)',
        ]
        found = []
        for p in patterns:
            for m in re.finditer(p, t_up):
                try:
                    n = int(m.group(1))
                    if 0 <= n < 10000:
                        found.append(n)
                except ValueError:
                    pass
        return found

    notion_nums = []
    # 1. Primary Source of Truth: Notion VF Trend Brain DB & Story Library DB
    try:
        import scripts.ag_notion_bridge as bridge

        def _get_prop_txt(prop: dict) -> str:
            if not prop:
                return ""
            ptype = prop.get("type")
            if ptype == "title":
                return "".join(x.get("plain_text", "") for x in prop.get("title", []))
            if ptype == "rich_text":
                return "".join(x.get("plain_text", "") for x in prop.get("rich_text", []))
            if ptype == "select":
                sel = prop.get("select")
                return sel.get("name", "") if sel else ""
            return ""

        # Check Trend Brain DB
        tb_res = bridge.query_db("4c101989-2400-8334-8016-01d4f463b09f")
        for r in tb_res.get("results", []):
            props = r.get("properties", {})
            mkt_prop = _get_prop_txt(props.get("Market", {}))
            tid_prop = _get_prop_txt(props.get("Task ID", {}))
            eid_prop = _get_prop_txt(props.get("Episode ID", {}))
            kw_prop = _get_prop_txt(props.get("Keyword", {}))
            for txt in [tid_prop, eid_prop, kw_prop]:
                for num in _extract_market_ep_nums(txt, target_market):
                    notion_nums.append(num)

        # Check Story Library DB
        sl_res = bridge.query_db("b0301989-2400-836b-bdb5-8131fea17736")
        for r in sl_res.get("results", []):
            props = r.get("properties", {})
            name_prop = _get_prop_txt(props.get("Name", {}))
            tid_prop = _get_prop_txt(props.get("Task ID", {}))
            eid_prop = _get_prop_txt(props.get("Episode ID", {}))
            for txt in [tid_prop, eid_prop, name_prop]:
                for num in _extract_market_ep_nums(txt, target_market):
                    notion_nums.append(num)
    except Exception as e:
        _log.warning("[episode_id] Notion SoT scan notice: %s", e)

    # Check active pending tasks in /var/vf/pending_tasks
    pending_nums = []
    pending_dir = "/var/vf/pending_tasks"
    if os.path.exists(pending_dir):
        try:
            for f in os.listdir(pending_dir):

                if not f.endswith(".json"):
                    continue
                p = os.path.join(pending_dir, f)
                try:
                    with open(p, "r", encoding="utf-8") as jf:
                        data = json.load(jf)
                    row_m = str(data.get("market", "")).strip().upper()
                    row_eid = str(data.get("episode_id", "") or data.get("task_id", ""))
                    if row_m == target_market or row_eid.startswith(f"{target_market}_EP"):
                        for num in _extract_market_ep_nums(row_eid + " " + f, target_market):
                            pending_nums.append(num)
                except Exception:
                    for num in _extract_market_ep_nums(f, target_market):
                        pending_nums.append(num)
        except Exception as e:
            _log.warning("[episode_id] pending_tasks scan notice: %s", e)

    # Determine next number:
    all_valid_nums = [0]
    if notion_nums:
        all_valid_nums.extend(notion_nums)
    if pending_nums:
        all_valid_nums.extend(pending_nums)

    # Fallback: if both Notion and pending are empty, only check active non-archived dirs
    if len(all_valid_nums) == 1:
        ep_dir = "/var/vf/episodes"
        if os.path.exists(ep_dir):
            try:
                for f in os.listdir(ep_dir):
                    if f.startswith("_") or "archive" in f.lower() or "dead" in f.lower() or "test" in f.lower():
                        continue
                    for num in _extract_market_ep_nums(f, target_market):
                        all_valid_nums.append(num)
            except Exception:
                pass

    max_num = max(all_valid_nums)
    next_num = max_num + 1 + offset
    task_id = f"{target_market}_EP{next_num:04d}_{clean_slug}"
    _log.info("[episode_id] Generated Task ID %s (market=%s, max_num=%d, next_num=%d, offset=%d, notion_count=%d)",
              task_id, target_market, max_num, next_num, offset, len(notion_nums))
    return task_id
# app/services/trend_gate_ai.py - "Notion AI is the crawl brain" architecture (26/07/2026).
#
# WHY: combining SerpApi + Google Trends + evergreen + wiki spikes inside Python was
# fragile - a hardcoded rank cap let the evergreen lane evict 100% of the real-time
# SerpApi lane (verified live 26/07: 11 SerpApi calls spent, 0 SerpApi rows stored).
# NEW SPLIT OF RESPONSIBILITY:
#   VPS  (this module) = dumb COLLECTOR. Fetches every lane's RAW signals, keeps the
#                        lane label + metrics, writes NOTHING to the keyword library.
#   Notion AI          = the reasoning + curation GATE. Reads the raw pool, dedupes /
#                        cross-checks virality / applies theme-safety-IP-anti-repeat
#                        judgement, then commits ONLY approved keywords back here.
# ALREADY_PATCHED_1108B (11/08/2026): PG trend_keyword_cache writer REMOVED from
# trend-commit — Notion Trend Brain DB is the ONLY keyword store (no VPS smart cache).
# trend-commit mirrors approved keywords straight to Notion (source="notion_ai_gate*").
# RAW pool writes NOTHING to Trend Brain — only post-virality-scoring subjects are upserted.
#
# UPDATE (06/08/2026 decision - see Decisions Log): SerpApi's 250/month free quota was
# being burned at ~45-48 calls/single raw-pool run (5 themes x 3 seeds x 3 markets in
# legacy_sources + 1 gtrends_daily call/market here). Fix = (1) legacy_sources's
# SerpApi seed fan-out cut to 1 seed/theme, (2) gtrends_daily now reads the FREE Google
# Trends "Trending Now" RSS feed instead of spending a SerpApi call, (3) two new
# zero-cost lanes (youtube_autocomplete, google_autocomplete) add real "what people
# search on Google/YouTube" signal from the free public autocomplete endpoints - this
# directly answers the original ask (score candidates by both Google AND YouTube
# search interest) without spending any quota, (4) GATE_DAILY_CAP/MIN both default to
# 3/market/day now (was 5/3) so the gate only needs to reason down to exactly 3
# ready-to-video keywords per market, and the raw LANE_MIN pool sizes were trimmed
# since a smaller, cross-confirmed pool is more useful than a huge noisy one. All new
# lanes are FREE / unofficial endpoints - see trend_free_signals.py header for caveats.
#
# UPDATE (12/08/2026 decision - see Decisions Log): EN raw-pool market expansion.
# "EN" is now ONE logical market spanning 6 core English-speaking sub-geos (US, GB,
# DE, AU, CA, NZ) - Bonus tier CH/NO/NL/IE/DK and all of Eastern Europe are explicitly
# EXCLUDED (noise-reduction, user directive). Candidate/commit caps (GATE_DAILY_MIN/
# CAP) stay keyed by market="EN" and are UNCHANGED (3/day total, NOT x6) - only raw
# pool breadth grows. SerpApi lane now runs WEEKLY (Monday only, Asia/Ho_Chi_Minh) to
# stay inside the 250/month free quota with the wider fan-out. Free-lane per-geo calls
# (gtrends_daily / youtube_autocomplete / google_autocomplete) are spaced with a small
# sleep between geos to reduce rate-limit risk on Google's unofficial endpoints.
import os

# --- PATCH: FORCED IPV4 FOR NOTION API ---
import socket
_old_getaddrinfo = socket.getaddrinfo
def _new_getaddrinfo(*args, **kwargs):
    res = _old_getaddrinfo(*args, **kwargs)
    return [r for r in res if r[0] == socket.AF_INET]
socket.getaddrinfo = _new_getaddrinfo
# ----------------------------------------
import re
import json
import time
import logging
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel


logger = logging.getLogger(__name__)
router = APIRouter()

RAW_POOL_DIR = "/root/video_factory/db"
DEFAULT_MARKETS = [m.strip().upper() for m in
                   os.getenv("DISCOVERY_V5_MARKETS", "EN,JP,KR").split(",") if m.strip()]
SERP_GEO = {"US": "US", "JP": "JP", "KR": "KR", "GB": "GB", "AU": "AU", "CA": "CA",
            "DE": "DE", "NZ": "NZ"}

# hl/gl for the free Google/YouTube autocomplete + Trends RSS lanes (06/08/2026).
AC_HL_GL = {"US": ("en", "US"), "JP": ("ja", "JP"), "KR": ("ko", "KR"),
            "GB": ("en", "GB"), "AU": ("en", "AU"), "CA": ("en", "CA"),
            "DE": ("de", "DE"), "NZ": ("en", "NZ")}

# EN raw-pool expansion (12/08/2026 decision - see Decisions Log): "EN" is ONE
# logical market containing 6 core English-speaking sub-geos. Candidate/commit
# caps stay keyed by market="EN" (GATE_DAILY_MIN/CAP unchanged, NOT multiplied by
# geo count) - only the RAW pool breadth increases. Bonus tier (CH/NO/NL/IE/DK)
# and Eastern Europe are explicitly EXCLUDED to reduce noise (user directive).
EN_SUB_GEOS = ["US", "GB", "DE", "AU", "CA", "NZ"]

# Spacing between per-geo calls on the free (unofficial) Google/YouTube endpoints
# so a 6x geo fan-out doesn't trip rate limits (12/08/2026 decision).
EN_GEO_SLEEP_SECONDS = float(os.getenv("TREND_GATE_EN_GEO_SLEEP", "1.5"))

AUTOCOMPLETE_SEEDS = {
    "business": "business rise and fall collapse",
    "modern_history": "modern history systemic investigation",
    "true_crime": "true crime case non graphic",
    "psychology": "psychology of manipulation",
    "tech_geopolitics": "tech geopolitical supply chain battle",
}

# 5 Canonical Content Pillars per Market (Native-First)
AUTOCOMPLETE_SEEDS_BY_MARKET = {
    "JP": {
        "business": "企業 衰退 崩壊 スキャンダル",
        "modern_history": "現代史 事件 調査",
        "true_crime": "未解決事件 捜査 ドキュメンタリー",
        "psychology": "心理操作 洗脳 行動経済学",
        "tech_geopolitics": "半導体戦争 技術覇権 地政学",
    },
    "KR": {
        "business": "기업 흥망성쇠 몰락 스캔들",
        "modern_history": "현대사 사건 탐사",
        "true_crime": "실화 범죄 수사 다큐",
        "psychology": "심리 조작 가스라이팅 행동심리",
        "tech_geopolitics": "반도체 전쟁 기술 패권 공급망",
    },
}


def _autocomplete_seeds_for(market):
    """Return the theme->seed dict for this market: native-language seeds for JP/KR
    (06/08/2026 fix), English fallback for every other market."""
    return AUTOCOMPLETE_SEEDS_BY_MARKET.get((market or "US").upper(), AUTOCOMPLETE_SEEDS)


# Minimum RAW volume per lane (UPDATED 06/08/2026: trimmed down - a smaller,
# cross-confirmed pool beats a huge noisy one now that the daily commit target is
# a fixed 3/market. 26/07/2026 originally set these much higher when the target
# commit range was 8-12/market/day).
LANE_MIN = {
    "serpapi": int(os.getenv("TREND_GATE_MIN_SERPAPI", "12")),
    "gtrends_daily": int(os.getenv("TREND_GATE_MIN_GTRENDS", "15")),
    "wiki_spike": int(os.getenv("TREND_GATE_MIN_WIKI", "15")),
    "evergreen": int(os.getenv("TREND_GATE_MIN_EVERGREEN", "15")),
    "youtube_autocomplete": int(os.getenv("TREND_GATE_MIN_YT_AC", "15")),
    "google_autocomplete": int(os.getenv("TREND_GATE_MIN_GOOGLE_AC", "15")),
}
# Hard daily commit cap per market (UPDATED 06/08/2026 decision: exactly 3
# ready-to-video keywords/market/day, down from the 26/07 8-12 range - see
# Decisions Log 06/08/2026).
GATE_DAILY_CAP = int(os.getenv("TREND_GATE_DAILY_CAP", "3"))
GATE_DAILY_MIN = int(os.getenv("TREND_GATE_DAILY_MIN", "3"))

# Rule D6 (Decisions Log): Minimum virality score gate for B1 Trend Gate
MIN_VIRALITY_SCORE = 0.70  # 65% normalized (Rule D6: virality threshold, adjusted 31/08 for better pass rate)


def _commits_path(day):
    return os.path.join(RAW_POOL_DIR, "trend_gate_commits_%s.json" % day)


def _committed_today(day):
    """How many keywords the gate already committed per market today."""
    counts = {}
    try:
        with open(_commits_path(day)) as f:
            for line in f:

                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                for it in (rec.get("items") or []):
                    mk = (it.get("market") or "US").upper()
                    counts[mk] = counts.get(mk, 0) + 1
    except Exception:
        pass
    return counts


def _notify_raw_ready(data):
    """Telegram ping after the automated VPS crawl: raw pool ready for the gate."""
    try:
        from app.services.telegram_buttons import send_telegram_broadcast as _send_telegram
    except Exception:
        return
    lines = ["\U0001f4e5 RAW POOL %s da san sang (VPS cao tu dong, CHUA ghi thu vien)."
             % str(data.get("generated_at") or "")[:10]]
    for mk, blk in (data.get("by_market") or {}).items():
        c = (blk or {}).get("_counts") or {}
        lines.append("%s: %s | tong %d" % (
            mk, " ".join("%s=%d" % (k, v) for k, v in c.items()), sum(c.values())))
        # UPDATED 06/08/2026: use _lane_status (EMPTY / thin(x/y) / ok) instead of a
        # raw zero-check, so under-target ("thin") unofficial free lanes get flagged
        # too, not just fully-dead ones - these endpoints can get silently rate-limited.
        lane_status = (blk or {}).get("_lane_status") or {}
        flagged = ["%s:%s" % (k, v) for k, v in lane_status.items() if v != "ok"]
        if flagged:
            lines.append("  \u26a0\ufe0f lane can kiem tra (khong 'ok'): " + ", ".join(flagged))
        cc = ((blk or {}).get("_context") or {}).get("cross_confirmed_google_youtube") or []
        if cc:
            lines.append("  \U0001f525 Google+YouTube CUNG xac nhan (%d): %s"
                         % (len(cc), ", ".join(cc[:8])))
    lines.append("\U0001f9e0 Mo Notion AI va go: 'chay gate trend hom nay' -> AI suy luan "
                 "tren toan bo raw, chot dung %d tu khoa/market vao thu vien + chon 1 "
                 "key lam video hom nay." % GATE_DAILY_CAP)
    try:
        _send_telegram(chr(10).join(lines))
    except Exception:
        pass


def _slug(term):
    return re.sub(r"[^\w]+", "-", (term or "").strip().lower()).strip("-")


def _norm_for_match(term):
    return re.sub(r"[^\w]+", " ", (term or "").strip().lower()).strip()


def _cross_confirm_google_youtube(block):
    """AND-combination signal (06/08/2026 decision): flag terms that show up on BOTH
    a Google-side lane (serpapi / gtrends_daily / google_autocomplete) AND the
    youtube_autocomplete lane, so the gate can prioritise keywords demonstrably
    searched on both platforms - directly answers the original ask ('nguoi dung
    search gi nhieu tren 2 nen tang nay se de len de xuat khi mo youtube ra')."""
    google_terms = set()
    for lane in ("serpapi", "gtrends_daily", "google_autocomplete"):
        for row in (block.get(lane) or []):
            t = _norm_for_match(row.get("term"))
            if t:
                google_terms.add(t)
    youtube_terms = set()
    for row in (block.get("youtube_autocomplete") or []):
        t = _norm_for_match(row.get("term"))
        if t:
            youtube_terms.add(t)
    confirmed = set()
    for gt in google_terms:
        for yt in youtube_terms:
            if gt == yt or (gt and gt in yt) or (yt and yt in gt):
                confirmed.add(gt)
                break
    return sorted(confirmed)


def _raw_pool_path(day):
    return os.path.join(RAW_POOL_DIR, "trend_raw_pool_%s.json" % day)


# ---------------------------------------------------------------- lane collectors
def _serpapi_weekly_gate_open():
    """SerpApi now runs WEEKLY (Monday only, Asia/Ho_Chi_Minh) instead of daily
    (12/08/2026 decision) to stay inside the 250/month free quota once the EN
    pool fans out to 6 geos. TREND_GATE_FORCE_SERPAPI=1 overrides for manual runs."""
    if os.getenv("TREND_GATE_FORCE_SERPAPI", "0") == "1":
        return True
    try:
        from zoneinfo import ZoneInfo
        now_vn = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    except Exception:
        now_vn = datetime.now(timezone.utc)
    return now_vn.weekday() == 0  # Monday


def _lane_serpapi(market, pool):
    """Legacy serpapi lane retired; canonical trend ingestion handled by B1."""
    return []



def _lane_gtrends_daily(market, limit=None):
    """FREE Google Trends 'Trending Now' RSS feed (06/08/2026 decision - see
    trend_free_signals.py). UPDATE (12/08/2026): EN fans out across 6 sub-geos
    with inter-geo sleep spacing (rate-limit safety), tagging sub_regions_detected;
    dedupes terms cross-geo instead of multiplying pool size."""
    limit = int(limit or LANE_MIN["gtrends_daily"])
    if os.getenv("TREND_GATE_GTRENDS_DAILY", "1") != "1":
        return []
    try:
        from app.services.trend_free_signals import gtrends_daily_rss
    except Exception as e:
        logger.warning("[gate-ai] gtrends-daily lane import failed %s: %s", market, e)
        return []
    geos = EN_SUB_GEOS if market == "EN" else [SERP_GEO.get((market or "US").upper(), "US")]
    by_term = {}
    for i, geo in enumerate(geos):
        try:
            rows = gtrends_daily_rss(geo=geo) or []
        except Exception as e:
            logger.warning("[gate-ai] gtrends-daily lane failed %s/%s: %s", market, geo, e)
            rows = []
        for x in rows[:limit]:
            term = str(x.get("term") or "").strip()
            if not term:
                continue
            key = term.lower()
            if key in by_term:
                if geo not in by_term[key]["sub_regions_detected"]:
                    by_term[key]["sub_regions_detected"].append(geo)
            else:
                by_term[key] = {"term": term, "lane": "gtrends_daily",
                                "approx_traffic": x.get("approx_traffic"),
                                "news_title": x.get("news_title"),
                                "signal": "google_trends_rss_free",
                                "sub_regions_detected": [geo]}
        if i < len(geos) - 1:
            time.sleep(EN_GEO_SLEEP_SECONDS)
    return list(by_term.values())


def _lane_youtube_autocomplete(market, limit=None):
    """FREE, no-key, no quota: real YouTube search-box suggestions per theme seed
    (06/08/2026 decision). UPDATE (12/08/2026): EN fans out across 6 sub-geos with
    inter-geo sleep spacing; dedupes terms cross-geo and tags sub_regions_detected."""
    if os.getenv("TREND_GATE_YT_AUTOCOMPLETE", "1") != "1":
        return []
    limit = int(limit or LANE_MIN["youtube_autocomplete"])
    try:
        from app.services.trend_free_signals import youtube_autocomplete
    except Exception as e:
        logger.warning("[gate-ai] youtube_autocomplete import failed: %s", e)
        return []
    geos = EN_SUB_GEOS if market == "EN" else [(market or "US").upper()]
    seeds = _autocomplete_seeds_for(market)
    by_term = {}
    for gi, geo in enumerate(geos):
        hl, gl = AC_HL_GL.get(geo, ("en", "US"))
        for theme, seed in seeds.items():
            try:
                suggestions = youtube_autocomplete(seed, hl=hl, gl=gl) or []
            except Exception as e:
                logger.warning("[gate-ai] youtube_autocomplete lane failed %s/%s/%s: %s",
                               market, geo, theme, e)
                continue
            for term in suggestions:
                key = term.lower()
                if key in by_term:
                    if geo not in by_term[key]["sub_regions_detected"]:
                        by_term[key]["sub_regions_detected"].append(geo)
                    continue
                by_term[key] = {"term": term, "lane": "youtube_autocomplete",
                                "theme_hint": theme, "seed": seed,
                                "signal": "youtube_autocomplete_suggest_free",
                                "sub_regions_detected": [geo]}
                if len(by_term) >= limit and market != "EN":
                    return list(by_term.values())
        if gi < len(geos) - 1:
            time.sleep(EN_GEO_SLEEP_SECONDS)
    return list(by_term.values())


def _lane_google_autocomplete(market, limit=None):
    """FREE, no-key, no quota: real Google Search-box suggestions per theme seed
    (06/08/2026 decision). UPDATE (12/08/2026): EN fans out across 6 sub-geos with
    inter-geo sleep spacing; dedupes terms cross-geo and tags sub_regions_detected."""
    if os.getenv("TREND_GATE_GOOGLE_AUTOCOMPLETE", "1") != "1":
        return []
    limit = int(limit or LANE_MIN["google_autocomplete"])
    try:
        from app.services.trend_free_signals import google_autocomplete
    except Exception as e:
        logger.warning("[gate-ai] google_autocomplete import failed: %s", e)
        return []
    geos = EN_SUB_GEOS if market == "EN" else [(market or "US").upper()]
    seeds = _autocomplete_seeds_for(market)
    by_term = {}
    for gi, geo in enumerate(geos):
        hl, gl = AC_HL_GL.get(geo, ("en", "US"))

        for theme, seed in seeds.items():
            try:
                suggestions = google_autocomplete(seed, hl=hl, gl=gl) or []
            except Exception as e:
                logger.warning("[gate-ai] google_autocomplete lane failed %s/%s/%s: %s",
                               market, geo, theme, e)
                continue
            for term in suggestions:
                key = term.lower()
                if key in by_term:
                    if geo not in by_term[key]["sub_regions_detected"]:
                        by_term[key]["sub_regions_detected"].append(geo)
                    continue
                by_term[key] = {"term": term, "lane": "google_autocomplete",
                                "theme_hint": theme, "seed": seed,
                                "signal": "google_autocomplete_suggest_free",
                                "sub_regions_detected": [geo]}
                if len(by_term) >= limit and market != "EN":
                    return list(by_term.values())
        if gi < len(geos) - 1:
            time.sleep(EN_GEO_SLEEP_SECONDS)
    return list(by_term.values())



def _lane_gtrends_discover(market, limit=None):
    """
    NEW lane (02/09/2026): Discover trending SEARCH QUERIES in JP/KR markets
    via pytrends.related_queries(). Complements gtrends_daily_rss (which
    gets news-driven "trending topics") by finding what people actually TYPE
    in the Google search box right now.
    
    Only runs for JP/KR markets (EN has sufficient coverage from 6-geo fan-out
    across other lanes). Returns candidates in standard lane format.
    """
    if market not in ["JP", "KR"]:
        return []
    
    limit = int(limit or LANE_MIN.get("gtrends_discover", 10))
    
    if os.getenv("TREND_GATE_GTRENDS_DISCOVER", "1") != "1":
        return []
    
    try:
        from app.services.trend_free_signals import gtrends_discover_trending_searches
    except Exception as e:
        logger.warning("[gate-ai] gtrends-discover lane import failed %s: %s", market, e)
        return []
    
    try:
        terms = gtrends_discover_trending_searches(market) or []
    except Exception as e:
        logger.warning("[gate-ai] gtrends-discover lane failed %s: %s", market, e)
        return []
    
    candidates = []
    for term in terms[:limit]:
        candidates.append({
            "term": term,
            "lane": "gtrends_discover",
            "signal": "pytrends_trending_searches",
            "market": market
        })
    
    logger.info("[gate-ai] gtrends-discover lane %s: %d candidates", market, len(candidates))
    return candidates

def _lane_wiki_spike(market, free_market_block, pool):
    rows = (free_market_block.get("wiki_spikes") or [])[:pool]
    return [{"term": r.get("article"), "lane": "wiki_spike",
             "views": r.get("views"), "spike": r.get("spike"), "level": r.get("level"),
             "theme_hint": r.get("theme_hint"), "signal": "wikimedia_pageview_spike"}
            for r in rows if r.get("article")]


def _lane_evergreen(market, limit=None):
    limit = int(limit or LANE_MIN["evergreen"])
    # Legacy evergreen lane retired; handled by canonical B1 trend engine
    return []
    out = []
    for ev in items[:limit]:
        term = ev.get("t")
        if not term:
            continue
        try:
            sg = wiki_article_spike(proj, term) or {}
        except Exception:
            sg = {}
        out.append({"term": term, "lane": "evergreen", "theme_hint": ev.get("theme"),
                    "views": int(sg.get("recent_avg", 0) or 0),
                    "spike": float(sg.get("spike", 0.0) or 0.0),
                    "level": float(sg.get("level", 0.0) or 0.0),
                    "signal": "curated_library+wiki_level"})
    return out


def collect_raw_pool(markets=None, pool=20, lanes=None):
    """Collect every lane's RAW candidates. No LLM, no scoring, no ranking, no cap,
    no DB write - all judgement is deliberately left to the Notion AI gate."""
    markets = [m.strip().upper() for m in (markets or DEFAULT_MARKETS) if m and m.strip()]

    lanes = lanes or ["serpapi", "gtrends_daily", "wiki_spike", "evergreen",
                       "youtube_autocomplete", "google_autocomplete", "gtrends_discover"]
    # Legacy raw pool free signals retired; canonical pool handled by B1
    free = {}
    out = {"generated_at": datetime.now(timezone.utc).isoformat(),
           "markets": markets, "lanes": lanes, "pool": pool, "by_market": {}}
    for market in markets:
        fm = free.get(market) or {}
        block, counts = {}, {}
        if "serpapi" in lanes:
            block["serpapi"] = _lane_serpapi(market, max(pool, LANE_MIN["serpapi"]))
        if "gtrends_daily" in lanes:
            block["gtrends_daily"] = _lane_gtrends_daily(market)
        if "wiki_spike" in lanes:
            block["wiki_spike"] = _lane_wiki_spike(market, fm,
                                                   max(pool, LANE_MIN["wiki_spike"]))
        if "evergreen" in lanes:
            block["evergreen"] = _lane_evergreen(market)
        if "youtube_autocomplete" in lanes:
            block["youtube_autocomplete"] = _lane_youtube_autocomplete(market)
        if "google_autocomplete" in lanes:
            block["google_autocomplete"] = _lane_google_autocomplete(market)
        if "gtrends_discover" in lanes:
            block["gtrends_discover"] = _lane_gtrends_discover(market)
        for k, v in block.items():
            counts[k] = len(v)
        # Context the gate needs for judgement, without pre-deciding anything.
        block["_context"] = {
            "gnews_titles": [t for td in (fm.get("themes") or {}).values()
                             for t in (td.get("gnews_titles") or [])][:60],
            "apple_chart": [x.get("name") for td in (fm.get("themes") or {}).values()
                            for x in (td.get("apple_chart") or [])][:40],
            "cross_confirmed_google_youtube": _cross_confirm_google_youtube(block),
        }
        block["_counts"] = counts
        # Lane health: never let an empty lane pass silently again.
        status = {}
        for k, v in counts.items():
            need = LANE_MIN.get(k, 0)
            if not v:
                status[k] = "EMPTY"
                logger.warning("[gate-ai] lane %s returned 0 candidates for %s",
                               k, market)
            elif v < need:
                status[k] = "thin(%d/%d)" % (v, need)
                logger.warning("[gate-ai] lane %s thin for %s: %d < %d",
                               k, market, v, need)
            else:
                status[k] = "ok"
        block["_lane_status"] = status
        block["_lane_min"] = dict(LANE_MIN)
        block["_daily_commit_cap"] = [GATE_DAILY_MIN, GATE_DAILY_CAP]
        out["by_market"][market] = block
    try:
        from app.services import serp_budget
        out["serp_budget"] = getattr(serp_budget, "read_budget", lambda: None)()
    except Exception:
        pass
    return out


class TrendRawRequest(BaseModel):
    markets: list[str] | None = None
    pool: int | None = None
    lanes: list[str] | None = None
    refresh: bool | None = None  # False/None = reuse today's cached pool if present


@router.post("/api/v1/trend-raw")
def trend_raw(req: TrendRawRequest):
    """Return the RAW multi-lane candidate pool for the Notion AI gate.
    Writes nothing to the keyword library. Caches one pool file per UTC day so the
    gate can re-read it without spending SerpApi quota again."""
    day = datetime.now(timezone.utc).date().isoformat()
    path = _raw_pool_path(day)
    if not req.refresh and os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
            data["cached"] = True
            data["cache_path"] = path
            return data
        except Exception:
            pass
    data = collect_raw_pool(req.markets, pool=int(req.pool or 20), lanes=req.lanes)
    data["cached"] = False
    try:
        with open(path, "w") as f:
            json.dump(data, f)
        data["cache_path"] = path
    except Exception as e:
        logger.warning("[gate-ai] could not cache raw pool: %s", e)
    # ALREADY_PATCHED_1108: RAW POOL Telegram notify DISABLED (11/08/2026 user directive)
    # -> only /api/v1/trend-virality sends the Telegram alert (after scoring).
    return data


class GateItem(BaseModel):
    term: str
    market: str

    lane: str | None = None       # serpapi | gtrends_daily | wiki_spike | evergreen | youtube_autocomplete | google_autocomplete
    theme: str | None = None
    score: float | None = None    # the gate's own composite judgement, 0..1
    reason: str | None = None     # short audit trail of WHY it passed the gate


class TrendCommitRequest(BaseModel):
    items: list[GateItem]
    notify: bool | None = True
    gate_note: str | None = None
    pick_of_day: str | None = None   # the ONE keyword chosen for today video


@router.post("/api/v1/trend-commit")
def trend_commit(req: TrendCommitRequest):
    """Gate commit — writes approved keywords to the Trend Brain DB (Notion, only store).
    ALREADY_PATCHED_1108: PG trend_keyword_cache writer removed 11/08/2026.
    Accepts the Notion AI gate's approved list. source is always notion_ai_gate_<lane>."""
    _today = datetime.now(timezone.utc).date().isoformat()
    _day_counts = _committed_today(_today)
    dropped = []
    grouped, audit = {}, []
    for it in (req.items or []):
        slug = _slug(it.term)
        market = (it.market or "US").upper()
        if not slug:
            continue
        lane = (it.lane or "gate").strip().lower()
        if _day_counts.get(market, 0) >= GATE_DAILY_CAP:
            dropped.append({"slug": slug, "market": market,
                            "why": "vuot tran %d key/market/ngay" % GATE_DAILY_CAP})
            logger.warning("[gate-ai] daily cap %d reached for %s, dropped %s",
                           GATE_DAILY_CAP, market, slug)
            continue
        _day_counts[market] = _day_counts.get(market, 0) + 1
        grouped.setdefault((market, lane), []).append(
            {"slug": slug, "term": it.term.strip(),
             "score": float(it.score if it.score is not None else 0.5)})
        audit.append({"slug": slug, "market": market, "lane": lane,
                      "theme": it.theme, "reason": it.reason})
    saved, by_source = 0, {}
    for (market, lane), items in grouped.items():
        source = "notion_ai_gate_" + lane
        # ALREADY_PATCHED_1108: PG trend_keyword_cache RETIRED — no VPS-side keyword store.
        n = len(items)
        saved += n
        by_source["%s:%s" % (market, source)] = n
        # Mirror committed keys to Trend Brain DB (10/08/2026, user directive)
        try:
            from app.services import trend_brain_mirror as _tbm
            for _it in items:
                _tbm.upsert_scored(_it["term"], market,
                                   {"virality_score": _it.get("score", 0.0)},
                                   source=source, status="committed")
        except Exception as _e:
            logger.warning("[gate-ai] trend-brain mirror failed %s/%s: %s", market, lane, _e)
    day = datetime.now(timezone.utc).date().isoformat()
    try:
        with open(os.path.join(RAW_POOL_DIR, "trend_gate_commits_%s.json" % day), "a") as f:
            f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(),
                                "note": req.gate_note, "saved": saved,
                                "items": audit}) + "\n")
    except Exception as e:
        logger.warning("[gate-ai] could not write commit audit: %s", e)
    pick = (req.pick_of_day or "").strip()
    if pick:
        try:
            with open(os.path.join(RAW_POOL_DIR, "trend_pick_of_day_%s.json" % day), "w") as f:
                json.dump({"day": day, "term": pick, "slug": _slug(pick),
                           "market": ((req.items[0].market or "US").upper()
                                      if req.items else "US"),
                           "note": req.gate_note}, f)
        except Exception as e:
            logger.warning("[gate-ai] could not write pick of day: %s", e)
        # 20/08/2026 (user directive): commit != production. Do NOT record pick_of_day
        # into produced_ledger and do NOT mark Trend Brain "Used" at commit time.
        # The ledger record + "Used" status now happen in story_check, when the story
        # actually exists in Story Library. pick_of_day file above is only a daily marker.
    if req.notify and (saved or pick):
        try:
            from app.services.telegram_buttons import send_telegram_broadcast as _send_telegram
            msg = ["\u2705 GATE (Notion AI): %d tu khoa qua kiem duyet -> thu vien." % saved]
            if by_source:
                msg.append("Nguon: " + ", ".join("%s=%d" % (k, v)
                                                 for k, v in by_source.items()))
            if dropped:
                msg.append("\u26a0\ufe0f Bo %d key vi vuot tran %d/market/ngay."
                           % (len(dropped), GATE_DAILY_CAP))
            if pick:
                msg.append("\U0001f3af KEY CHOT HOM NAY: " + pick)
                msg.append("\u27a1\ufe0f Buoc tiep: mo Notion AI va go: \"sinh story cho "
                           + pick + "\"")
            _send_telegram("\n".join(msg))
        except Exception:
            pass
    return {"status": "ok", "saved": saved, "by_source": by_source,
            "received": len(req.items or []), "day": day,
            "dropped": dropped, "daily_cap": GATE_DAILY_CAP,
            "committed_today": _day_counts, "pick_of_day": pick or None}



# ===== Trend Refine endpoint (07/08/2026) — Nhom 2: deep scrape =====

class TrendRefineRequest(BaseModel):
    date: str | None = None
    markets: list[str] | None = None
    max_searches_per_market: int = 5


@router.post("/api/v1/trend-refine")
def trend_refine(req: TrendRefineRequest):
    """Legacy trend-refine retired; canonical B1 trend engine handles refinement."""
    return {"status": "deprecated", "message": "trend_refine has been retired. Use canonical B1 trend engine."}



class TrendViralityRequest(BaseModel):
    markets: list[str] | None = ["EN", "JP", "KR"]
    max_candidates: int = 1
    auto_commit: bool = True


@router.post("/api/v1/trend-virality")
def trend_virality(req: TrendViralityRequest):
    """Step 3 / Unified Pipeline: Approach B Direct Recon & Algorithmic Anchor.
    Replaces old theoretical virality scoring with real YouTube & Google Trends data.
    Auto-commits to pending tasks, competitor intel card, permanent history registry, and Notion SoT.
    """
    from app.services.trend_engine_b1 import discover_and_produce_market_trend as discover_approach_b
    from app.services import telegram_buttons as tb
    import asyncio

    logger.info("[trend-virality] Triggered Unified Approach B Pipeline for markets EN, JP, KR...")
    approved_topics = []
    by_market = {}

    for m in ["EN", "JP", "KR"]:
        try:
            topics = discover_approach_b(market=m, max_candidates=1, auto_commit=True)
            if topics:
                approved_topics.extend(topics)
                by_market[m] = topics[0]
        except Exception as e:
            logger.error(f"[trend-virality] Approach B discovery failed for {m}: {e}")

    # Build Gate 1 packs for Telegram
    gate1_packs = {}
    for m, t in by_market.items():
        gate1_packs[m] = {
            'top_subject': t.get('raw_term', ''),
            'virality': t.get('viability_score', 0.9),
            'topic_name_vi': t.get('topic_name_vi', ''),
            'search_specific_keyword': t.get('search_specific_keyword', ''),
            'niche_angle_brief': t.get('niche_angle_brief', ''),
            'story_direction_5_arcs': t.get('story_direction_5_arcs', ''),
            'rising_queries': t.get('rising_queries', []),
            'breakout_queries': t.get('breakout_queries', []),
            'task_id': t.get('task_id', f"{m.lower()}-none")
        }

    # Send Gate 1 interactive Telegram Card
    if tb.is_enabled() and gate1_packs:
        en_p = gate1_packs.get("EN", {'top_subject': 'None', 'virality': 0, 'topic_name_vi': 'None', 'search_specific_keyword': 'None', 'niche_angle_brief': 'No valid EN trend found', 'story_direction_5_arcs': '', 'task_id': 'en-none'})
        jp_p = gate1_packs.get("JP", {'top_subject': 'None', 'virality': 0, 'topic_name_vi': 'None', 'search_specific_keyword': 'None', 'niche_angle_brief': 'No valid JP trend found', 'story_direction_5_arcs': '', 'task_id': 'jp-none'})
        kr_p = gate1_packs.get("KR", {'top_subject': 'None', 'virality': 0, 'topic_name_vi': 'None', 'search_specific_keyword': 'None', 'niche_angle_brief': 'No valid KR trend found', 'story_direction_5_arcs': '', 'task_id': 'kr-none'})
        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(tb.send_gate1_card(en_p, jp_p, kr_p))
                else:
                    loop.run_until_complete(tb.send_gate1_card(en_p, jp_p, kr_p))
            except Exception:
                asyncio.run(tb.send_gate1_card(en_p, jp_p, kr_p))
        except Exception as te:
            logger.warning(f"[trend-virality] Telegram notify error: {te}")

    return {
        "ok": True,
        "pipeline": "approach_b_direct_recon",
        "total_approved": len(approved_topics),
        "approved_topics": approved_topics,
        "by_market": by_market
    }

