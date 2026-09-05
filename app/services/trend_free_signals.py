# app/services/trend_free_signals.py - FREE, NO-KEY signal providers (06/08/2026).
#
# WHY: SerpApi's 250/month free quota was being burned at ~45-48 calls/single raw-pool
# run (see Decisions Log 06/08/2026). These providers add real Google + YouTube
# search-interest signal WITHOUT spending any SerpApi budget, so the gate can
# cross-check "does this term also show up on Google/YouTube autocomplete" before
# a human/Notion-AI commits it, and the daily trending list no longer needs a
# SerpApi call at all.
#
# All three endpoints are public, unauthenticated, zero-cost, but UNOFFICIAL
# (Google can change/rate-limit them without notice) - treat failures as
# "no signal" (return []) rather than raising, same convention as every other
# lane in trend_gate_ai.py / legacy_signals.py.
#
# UPDATE (06/08/2026 live-test fix): youtube_autocomplete originally used
# client=youtube, which returns a JSONP-wrapped body (window.google.ac.h(...)),
# NOT valid JSON - r.json() always raised and the lane silently returned [] every
# time (confirmed live: 0/15 candidates, cross_confirmed_google_youtube always
# empty). Fixed to client=firefox + ds=yt, the correct no-key YouTube-scoped
# endpoint, which returns the same plain-JSON shape as google_autocomplete.
# Also added a small in-process TTL cache + one retry per call so repeated
# same-day gate runs don't hammer Google's unofficial endpoints as hard.
import logging
import time
import requests

logger = logging.getLogger(__name__)

_SUGGEST_URL = "https://suggestqueries.google.com/complete/search"
_TRENDING_RSS_URL = "https://trends.google.com/trending/rss"

_CACHE = {}
_CACHE_TTL_SECONDS = 6 * 3600  # 6h - plenty for the ~1x/day gate cadence, cheap safety net


def _cache_get(key):
    hit = _CACHE.get(key)
    if not hit:
        return None
    ts, val = hit
    if time.time() - ts > _CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return val


def _cache_set(key, val):
    _CACHE[key] = (time.time(), val)


def _get_with_retry(url, params, timeout, retries=1):
    """GET with one retry + short backoff. Raises the last error if every attempt fails
    so callers keep their existing try/except -> [] fallback behaviour."""
    last_exc = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r
            last_exc = Exception("HTTP %s" % r.status_code)
        except Exception as e:
            last_exc = e
        if attempt < retries:
            time.sleep(0.6)
    raise last_exc


def google_autocomplete(seed, hl="en", gl="US", timeout=10.0):
    """Free Google Search autocomplete suggestions for a seed phrase."""
    key = ("google_autocomplete", seed, hl, gl)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        r = _get_with_retry(_SUGGEST_URL,
                            {"client": "firefox", "q": seed, "hl": hl, "gl": gl}, timeout)
        data = r.json()
        out = [str(s).strip() for s in (data[1] or []) if str(s).strip()]
        _cache_set(key, out)
        return out
    except Exception as e:
        logger.warning("[free-signals] google_autocomplete failed for %r: %s", seed, e)
        return []


def youtube_autocomplete(seed, hl="en", gl="US", timeout=10.0):
    """Free YouTube search-box autocomplete suggestions for a seed phrase - real
    signal of what people search FOR ON YOUTUBE, not just Google web search.

    Uses client=firefox&ds=yt (YouTube-scoped suggestion dataset), which returns
    plain JSON. client=youtube returns a JSONP callback body and is NOT usable
    with r.json() - see module header, 06/08/2026 fix."""
    key = ("youtube_autocomplete", seed, hl, gl)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        r = _get_with_retry(_SUGGEST_URL,
                            {"client": "firefox", "ds": "yt", "q": seed, "hl": hl, "gl": gl},
                            timeout)
        data = r.json()
        out = [str(s).strip() for s in (data[1] or []) if str(s).strip()]
        _cache_set(key, out)
        return out
    except Exception as e:
        logger.warning("[free-signals] youtube_autocomplete failed for %r: %s", seed, e)
        return []


def gtrends_daily_rss(geo="US", timeout=15.0):
    """Free Google Trends 'Trending Now' RSS feed - replaces the SerpApi
    engine=google_trends_trending_now call (was costing 1 SerpApi call/market)."""
    key = ("gtrends_daily_rss", geo)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        r = _get_with_retry(_TRENDING_RSS_URL, {"geo": geo}, timeout)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.content)
        ns = {"ht": "https://trends.google.com/trending/rss"}
        out = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            if not title:
                continue
            traffic = item.findtext("ht:approx_traffic", default="", namespaces=ns)
            news_title = item.findtext("ht:news_item/ht:news_item_title", default="",
                                       namespaces=ns)
            out.append({"term": title, "approx_traffic": (traffic or "").strip(),
                       "news_title": (news_title or "").strip()})
        _cache_set(key, out)
        return out
    except Exception as e:
        logger.warning("[free-signals] gtrends_daily_rss failed for geo=%r: %s", geo, e)
        return []


def gtrends_discover_trending_searches(market, timeout=15.0):
    """
    NEW (02/09/2026): Discover daily trending SEARCH QUERIES in JP/KR via pytrends.
    
    IMPLEMENTATION NOTE: Google broke the trending_searches() API (404 error as of
    02/09/2026), so this uses related_queries() with multiple seed keywords instead.
    Seeds like "トレンド" (trending), "人気" (popular), "ニュース" (news) discover
    what people are actually searching for in relation to hot topics.
    
    Difference from gtrends_daily_rss:
    - RSS feed: "trending topics" from news (broader, editorial picks)
    - This: actual "trending search queries" people TYPE in Google search box
    
    Uses pytrends.related_queries() with market-specific seeds. JP/KR only - EN has
    sufficient coverage from 6-geo fan-out across other lanes.
    
    Returns list of trending search term strings (typically ~20-40 per market after
    deduplication). Free, no API key, official pytrends method.
    """
    if market not in ["JP", "KR"]:
        return []
    
    # Cache key
    key = ("gtrends_discover", market)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    
    # Seed queries to discover trending searches
    # JP: "trending", "popular", "news", "hot topic"
    # KR: "trending", "popular", "news", "hot topic"
    seed_queries = {
        "JP": ["トレンド", "人気", "ニュース", "話題"],
        "KR": ["트렌드", "인기", "뉴스", "화제"]
    }
    
    seeds = seed_queries.get(market, [])
    if not seeds:
        return []
    
    # Map market to pytrends geo
    geo_map = {"JP": "JP", "KR": "KR"}
    geo = geo_map.get(market)
    
    # Map market to language
    hl_map = {"JP": "ja", "KR": "ko"}
    hl = hl_map.get(market, "en")
    
    try:
        from pytrends.request import TrendReq
        
        all_terms = []
        seen = set()
        
        for seed in seeds:
            try:
                # Create pytrends request object
                pytrend = TrendReq(hl=hl, tz=360, timeout=(timeout, timeout))
                
                # Build payload with seed query
                pytrend.build_payload([seed], cat=0, timeframe='now 7-d', geo=geo)
                
                # Get related queries (both rising and top)
                related = pytrend.related_queries()
                
                if seed not in related:
                    continue
                
                # Extract rising queries
                rising_df = related[seed].get('rising')
                if rising_df is not None and not rising_df.empty:
                    for query in rising_df['query'].tolist():
                        query = str(query).strip()
                        if query and query.lower() not in seen:
                            seen.add(query.lower())
                            all_terms.append(query)
                
                # Extract top queries
                top_df = related[seed].get('top')
                if top_df is not None and not top_df.empty:
                    for query in top_df['query'].tolist():
                        query = str(query).strip()
                        if query and query.lower() not in seen:
                            seen.add(query.lower())
                            all_terms.append(query)
                
                # Small sleep between seeds to avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.warning("[free-signals] gtrends_discover seed '%s' failed for %s: %s", 
                             seed, market, e)
                continue
        
        _cache_set(key, all_terms)
        logger.info("[free-signals] gtrends_discover %s: %d terms from %d seeds", 
                   market, len(all_terms), len(seeds))
        return all_terms
        
    except Exception as e:
        logger.warning("[free-signals] gtrends_discover failed for %s: %s", market, e)
        return []
