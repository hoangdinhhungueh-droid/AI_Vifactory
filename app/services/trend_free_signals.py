import time
import logging
import requests

logger = logging.getLogger(__name__)

_TRENDING_RSS_URL = "https://trends.google.com/trending/rss"
_SUGGEST_URL = "https://suggestqueries.google.com/complete/search"

from datetime import datetime, timezone

_CACHE = {}


def _current_utc_day():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _cache_get(key):
    day_str = _current_utc_day()
    # Cache key format: (day_str, *original_key)
    full_key = (day_str, key) if isinstance(key, tuple) else (day_str, str(key))
    hit = _CACHE.get(full_key)
    if not hit:
        return None
    return hit


def _cache_set(key, val):
    day_str = _current_utc_day()
    # Clean out any old days from cache memory to maintain strict daily freshness
    stale_keys = [k for k in _CACHE.keys() if k[0] != day_str]
    for sk in stale_keys:
        _CACHE.pop(sk, None)
    full_key = (day_str, key) if isinstance(key, tuple) else (day_str, str(key))
    _CACHE[full_key] = val


def _get_with_retry(url, params, timeout, retries=1):
    """GET with one retry + short backoff. Raises the last error if every attempt fails
    so callers keep their existing try/except -> [] fallback behaviour."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    last_exc = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
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

def fetch_specialized_market_rss(market="JP", timeout=12.0):
    """Fetch high-RPM investigative & business crisis feeds specialized for each market.
    - JP: Yahoo Japan Business RSS + High-forensic business bankruptcy & fraud queries
    - KR: High-forensic business workout, bankruptcy, and embezzlement queries
    - EN: SEC / DOJ corporate crisis & financial scandal queries
    100% live, zero-quota, zero rate limit.
    """
    m_up = (market or "EN").upper()
    key = ("specialized_market_rss", m_up)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    import urllib.parse
    import xml.etree.ElementTree as ET

    feeds = []
    if m_up == "JP":
        q_forensic = urllib.parse.quote("when:48h (倒産 OR 民事再生 OR 破産 OR 不祥事 OR 巨額損失 OR 不正会計)")
        feeds.append({
            "url": f"https://news.google.com/rss/search?q={q_forensic}&hl=ja&gl=JP&ceid=JP:ja",
            "source": "jp_forensic_news"
        })
        feeds.append({
            "url": "https://news.yahoo.co.jp/rss/topics/business.xml",
            "source": "yahoo_jp_business"
        })
    elif m_up == "KR":
        q_forensic = urllib.parse.quote("when:48h (워크아웃 OR 법정관리 OR 부도 OR 횡령 OR 분식회계 OR 배임)")
        feeds.append({
            "url": f"https://news.google.com/rss/search?q={q_forensic}&hl=ko&gl=KR&ceid=KR:ko",
            "source": "kr_forensic_news"
        })
    else:  # EN
        q_forensic = urllib.parse.quote("when:48h (bankrupt OR bankruptcy OR fraud OR \"investigation\" OR \"indictment\" OR lawsuit OR collapse)")
        feeds.append({
            "url": f"https://news.google.com/rss/search?q={q_forensic}&hl=en-US&gl=US&ceid=US:en",
            "source": "en_forensic_news"
        })

    out = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Antigravity/2.0"}

    for feed_info in feeds:
        try:
            r = requests.get(feed_info["url"], headers=headers, timeout=timeout)
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
            for item in root.iter("item"):
                raw_title = (item.findtext("title") or "").strip()
                if not raw_title:
                    continue
                clean_title = raw_title.rsplit(" - ", 1)[0].strip() if " - " in raw_title else raw_title
                pub_date = (item.findtext("pubDate") or "").strip()
                out.append({
                    "term": clean_title,
                    "approx_traffic": "specialized_rss_live",
                    "news_title": clean_title,
                    "published_at": pub_date,
                    "source": feed_info["source"]
                })
        except Exception as e:
            logger.warning("[free-signals] Specialized feed %s failed for %s: %s", feed_info.get("source"), m_up, e)

    _cache_set(key, out)
    return out


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
    
    # Seed queries to discover trending searches across 7 Canonical Pillars:
    # 1. Corporate & Financial Fraud (Sụp đổ/Gian lận)
    # 2. True Crime Non-Graphic & Forensic Case Solving (Án kinh tế/Phá án trắng)
    # 3. Psychology, Cults & Manipulation Traps (Tâm lý thao túng/Bẫy hành vi)
    # 4. Tech Monopolies & Supply Chain Warfare (Bán dẫn/Độc quyền)
    # 5. Testing Scandals & Recalls (Bê bối kiểm định/Thu hồi)
    # 6. Socio-Economic Structural Crisis (Nghịch lý xã hội/Dân số)
    # 7. Hostile Takeovers & Regulatory Loopholes (Thâu tóm/Hố đen pháp lý)
    # 8. Ancient Prehistory & Lost Civilizations (Khảo cổ tiền sử / Văn minh đã mất)
    # 9. Stoic Wisdom & Modern Psychological Survival (Triết học Khắc kỷ / Bản lĩnh tinh thần)
    # 10. Declassified Military Logistics & Geopolitical Chokepoints (Hậu cần quân sự / Điểm nghẽn địa chính trị)
    seed_queries = {
        "JP": [
            "トレンド", "ニュース", "話題", "事件", "崩壊", "疑惑", "真相", "なぜ", "問題", "倒産", "危機",
            "洗脳", "マインドコントロール", "心理操作", "巨額詐欺", "横領", "捜査", "背任",
            "半導体", "不正認証", "リコール", "過労死", "年金崩壊", "敵対的買収",
            # Niche 2: Stoic Wisdom & Contemplative Mindset (JP)
            "ストイック", "禅の教え", "宮本武蔵 独行道", "精神的自立", "人間関係の疲れ", "孤独の力", "メンタル回復", "折れない心"
        ],
        "KR": [
            "트렌드", "뉴스", "화제", "사건", "사태", "논란", "폭망", "의혹", "원인", "실체", "붕괴", "위기", "급락",
            "가스라이팅", "심리 조작", "다단계", "횡령", "배임", "구속", "검찰 조사",
            "반도체 전쟁", "기술 유출", "품질 조작", "리콜", "고독사", "경영권 분쟁",
            # Niche 2: Stoic Wisdom & Psychological Resilience (KR)
            "스토아 철학", "마르쿠스 아우렐리우스", "독행도", "인간관계 번아웃", "멘탈 관리", "고독의 힘", "내면의 평화", "감정 조절"
        ],
        "EN": [
            "trending", "news", "scandal", "collapse", "crisis", "investigation", "fraud", "downfall", "exposed",
            "gaslighting", "mass hysteria", "cult psychology", "manipulation", "money laundering", "indictment", "embezzlement",
            "semiconductor embargo", "tech monopoly", "recall cover-up", "pension collapse", "hostile takeover",
            # Niche 1: Ancient Prehistory & Lost Civilizations (US/EN)
            "ancient mystery", "lost civilization", "archaeological discovery", "prehistoric anomaly", "younger dryas", "megalithic structure", "ancient humans survive",
            # Niche 3: Declassified Military Logistics & Geopolitical Chokepoints (US/EN)
            "military logistics", "declassified strategy", "geopolitical choke point", "straits of malacca", "undersea cables", "supply line collapse", "defense doctrine"
        ]
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
