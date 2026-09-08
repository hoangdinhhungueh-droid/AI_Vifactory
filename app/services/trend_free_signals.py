import time
import logging
import requests

logger = logging.getLogger(__name__)

_TRENDING_RSS_URL = "https://trends.google.com/trending/rss"
_SUGGEST_URL = "https://suggestqueries.google.com/complete/search"

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


def google_news_topic_rss(topic="BUSINESS", hl="en", gl="US", timeout=12.0):
    """Free Google News Section/Topic RSS feed (e.g. BUSINESS, TECHNOLOGY).
    100% resilient, zero rate-limits, zero token cost.
    Provides live breaking headlines from the past 24-48h.
    """
    key = ("google_news_topic_rss", topic, hl, gl)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        url = f"https://news.google.com/rss/headlines/section/topic/{topic}"
        params = {"hl": hl, "gl": gl, "ceid": f"{gl}:{hl}"}
        r = _get_with_retry(url, params, timeout)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.content)
        out = []
        for item in root.iter("item"):
            raw_title = (item.findtext("title") or "").strip()
            if not raw_title:
                continue
            # Remove publisher suffix e.g. "Headline - Reuters" -> "Headline"
            clean_title = raw_title.rsplit(" - ", 1)[0].strip() if " - " in raw_title else raw_title
            pub_date = (item.findtext("pubDate") or "").strip()
            out.append({
                "term": clean_title,
                "approx_traffic": "google_news_live",
                "news_title": clean_title,
                "published_at": pub_date
            })
        _cache_set(key, out)
        return out
    except Exception as e:
        logger.warning("[free-signals] google_news_topic_rss failed for topic=%r geo=%r: %s", topic, gl, e)
        return []


def gtrends_discover_trending_searches(market="EN", timeout=15.0, geo=None, count=15, **kwargs):
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
    if geo and (not market or market not in ["JP", "KR", "EN"]):
        market = geo.upper()
    if market not in ["JP", "KR", "EN"]:
        return []
    
    # Cache key
    key = ("gtrends_discover", market)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    
    # Seed queries to discover trending searches across investigative & systemic axes
    # KR: Trending, News, Issues, Scandals, Collapse, Crisis, Downfall, Mechanisms
    # JP: Trending, News, Scandals, Collapse, Truth, Bankruptcy, Crisis
    # EN: Trending, News, Scandals, Collapse, Crisis, Investigation, Fraud, Downfall
    seed_queries = {
        "JP": ["トレンド", "ニュース", "話題", "事件", "崩壊", "疑惑", "真相", "なぜ", "問題", "倒産", "危機"],
        "KR": ["트렌드", "뉴스", "화제", "사건", "사태", "논란", "폭망", "의혹", "원인", "실체", "붕괴", "위기", "급락"],
        "EN": ["trending", "news", "scandal", "collapse", "crisis", "investigation", "fraud", "downfall", "exposed"]
    }
    
    seeds = seed_queries.get(market, [])
    if not seeds:
        return []
    
    # Map market to pytrends geo
    geo_map = {"JP": "JP", "KR": "KR", "EN": "US"}
    geo = geo_map.get(market)
    
    # Map market to language
    hl_map = {"JP": "ja", "KR": "ko", "EN": "en"}
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
