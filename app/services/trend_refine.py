# app/services/trend_refine.py
# Deep scrape refinement: generic trending categories -> specific subjects (07/08/2026).
#
# NHOM 2 (Keyword Specificity): After raw pool (Nhom 1) identifies generic
# trending categories, search Google via BrightData/Serper to find SPECIFIC
# subjects. Then validate each subject using FREE signals. Output: refined pool
# with specific subjects + virality scores for Notion AI story-ability gate.
#
# QUOTA: BrightData 5K/month (primary), Serper 2.5K one-time (fallback).
# COST: 100% free (within free tiers only).
# SCORING: specificity(0.25) + google_ac(0.20) + youtube_ac(0.20) +
#          wiki_spike(0.15) + seed_match(0.10) + freshness(0.10)

import os, re, json, logging, urllib.parse
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Locale mapping for BrightData/Serper (lowercase gl/hl)
LOCALE = {
    "US": ("us", "en"), "GB": ("gb", "en"), "AU": ("au", "en"),
    "CA": ("ca", "en"), "NZ": ("nz", "en"),
    "JP": ("jp", "ja"), "KR": ("kr", "ko"),
}

WIKI_PROJECT = {"US": "en.wikipedia", "JP": "ja.wikipedia", "KR": "ko.wikipedia"}

GENERIC_WORDS = {
    "2026", "2025", "2024", "best", "top", "biggest", "most", "list",
    "documentary", "explained", "what happened", "story", "video",
    "youtube", "reddit", "wikipedia", "examples", "cases",
    "companies", "people", "famous", "history of",
    "corporate", "the corporate", "company", "the company", "business",
    "corporation", "firm", "organization", "corporate failures",
    "corporate failure", "corporate scandal", "corporate scandals",
    "まとめ", "解説", "一覧", "ランキング",
    "정리", "해설", "목록", "순위",
    "category:", "カテゴリ:", "분류:",
    "未解決", "実際にあった", "日本であった", "殺人・強盗等",
    "残虐度別", "刑法犯による", "世界大量",
    "심리 조작의", "심리조작의", "심리 조작", "심리조작",
}

SUBJECT_PATTERNS = [
    r"^(.+?)\s+scandal",
    r"^(.+?)\s+collapse",
    r"^(.+?)\s+fraud",
    r"^(.+?)\s+bankruptcy",
    r"^(.+?)\s+ponzi",
    r"^(.+?)\s+empire",
    r"what happened to\s+(.+?)(?:[,\.\?]|$)",
    r"the rise and fall of\s+(.+?)(?:[,\.\?]|$)",
    r"(.+?):\s+the\s+",
]

SUBJECT_PATTERNS_JP = [
    r"^(.+?)\s*事件",
    r"^(.+?)\s*スキャンダル",
    r"^(.+?)\s*詐欺",
    r"^(.+?)\s*破綻",
    r"^(.+?)\s*殺人",
    r"^(.+?)\s*の真相",
    r"^(.+?)\s*とは",
    r"^(.+?)\s*の謎",
]

SUBJECT_PATTERNS_KR = [
    r"^(.+?)\s*사건",
    r"^(.+?)\s*스캔들",
    r"^(.+?)\s*사기",
    r"^(.+?)\s*파산",
    r"^(.+?)\s*살인",
    r"^(.+?)\s*진실",
    r"^(.+?)\s*비밀",
    r"^(.+?)\s*미스터리",
]

SUBJECT_PATTERNS_BY_MARKET = {
    "US": SUBJECT_PATTERNS,
    "JP": SUBJECT_PATTERNS_JP,
    "KR": SUBJECT_PATTERNS_KR,
}


def _get_seeds_flat(market=None):
    try:
        from app.services.trend_sources_v5 import SEED_TITLES
        flat = []
        for titles in SEED_TITLES.values():
            flat.extend(titles)
        if market in ("JP", None):
            try:
                from app.services.trend_sources_v5 import SEED_TITLES_JP
                for titles in SEED_TITLES_JP.values():
                    flat.extend(titles)
            except Exception:
                pass
        if market in ("KR", None):
            try:
                from app.services.trend_sources_v5 import SEED_TITLES_KR
                for titles in SEED_TITLES_KR.values():
                    flat.extend(titles)
            except Exception:
                pass
        return flat
    except Exception:
        return []


def _is_generic(term, market="US"):
    t = term.lower().strip()
    for w in GENERIC_WORDS:
        if w in t:
            return True
    min_len = 2 if market in ("JP", "KR") else 3
    if len(t) < min_len or len(t) > 60:
        return True
    return False


def _clean_related(term):
    t = term.strip()
    for w in ["explained", "documentary", "what happened", "story",
              "2026", "2025", "cases", "examples", "history",
              "video", "youtube", "reddit"]:
        t = re.sub(r"\s+" + re.escape(w) + r"$", "", t, flags=re.IGNORECASE)
    return t.strip()


ENGLISH_STOP = {"the", "a", "an", "of", "and", "or", "in", "on", "at", "to", "for", "is", "was", "are"}

def _is_specific(subject, market="US", seeds_flat=None):
    s = subject.strip()
    if not s:
        return False
    if seeds_flat:
        for st in seeds_flat:
            if st.lower() == s.lower():
                return True
    if market in ("JP", "KR"):
        return len(s) >= 2
    words = [w for w in s.split() if w.lower() not in ENGLISH_STOP]
    if len(words) < 2:
        return False
    return True

def _clean_related_jp(term):
    t = term.strip()
    for w in ["とは", "の真相", "解説", "まとめ", "wiki", "wikipedia"]:
        t = re.sub(re.escape(w) + r"$", "", t)
    return t.strip()

def _clean_related_kr(term):
    t = term.strip()
    for w in ["이란", "진실", "해설", "요약", "wiki", "wikipedia"]:
        t = re.sub(re.escape(w) + r"$", "", t)
    return t.strip()

def _clean_related_for_market(term, market="US"):
    if market == "JP":
        return _clean_related_jp(term)
    elif market == "KR":
        return _clean_related_kr(term)
    return _clean_related(term)

def _is_echo(subject, generic_term, market="US"):
    s = subject.strip().lower()
    g = (generic_term or "").strip().lower()
    if not g or not s:
        return False
    if g in s or s in g:
        return True
    if market == "KR":
        g_nospace = g.replace(" ", "")
        s_nospace = s.replace(" ", "")
        if g_nospace in s_nospace:
            return True
    return False

def _extract_term(item):
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("term", "") or item.get("title", "")
    return ""


# --- BrightData search ---

def brightdata_search(query, gl="us", hl="en", timeout=20.0):
    key = os.getenv("BRIGHTDATA_API_KEY")
    zone = os.getenv("BRIGHTDATA_SERP_ZONE")
    if not key or not zone:
        logger.warning("[trend-refine] BrightData key/zone missing")
        return None
    try:
        from app.services import bd_serp_budget
        if not bd_serp_budget.bd_can_spend(1):
            logger.info("[trend-refine] BrightData budget exhausted")
            return None
    except Exception:
        pass
    search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&brd_json=1&gl={gl}&hl={hl}"
    try:
        import httpx
        transport = httpx.HTTPTransport(local_address="0.0.0.0")
        with httpx.Client(transport=transport, timeout=timeout) as client:
            resp = client.post(
                "https://api.brightdata.com/request",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"zone": zone, "url": search_url, "format": "raw"},
            )
        if resp.status_code != 200:
            logger.warning("[trend-refine] BrightData HTTP %s", resp.status_code)
            return None
        try:
            from app.services import bd_serp_budget
            bd_serp_budget.bd_record(1)
        except Exception:
            pass
        try:
            return resp.json()
        except Exception:
            logger.warning("[trend-refine] BrightData response not JSON")
            return None
    except Exception as e:
        logger.warning("[trend-refine] BrightData search failed: %s", e)
        return None


# --- Serper search ---

def serper_search(query, gl="us", hl="en", timeout=15.0):
    key = os.getenv("SERPER_API_KEY")
    if not key:
        logger.warning("[trend-refine] Serper key missing")
        return None
    try:
        from app.services import bd_serp_budget
        if not bd_serp_budget.serper_can_spend(1):
            logger.info("[trend-refine] Serper budget exhausted")
            return None
    except Exception:
        pass
    try:
        import httpx
        transport = httpx.HTTPTransport(local_address="0.0.0.0")
        with httpx.Client(transport=transport, timeout=timeout) as client:
            resp = client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
                json={"q": query, "gl": gl, "hl": hl},
            )
        if resp.status_code != 200:
            logger.warning("[trend-refine] Serper HTTP %s", resp.status_code)
            return None
        try:
            from app.services import bd_serp_budget
            bd_serp_budget.serper_record(1)
        except Exception:
            pass
        try:
            return resp.json()
        except Exception:
            logger.warning("[trend-refine] Serper response not JSON")
            return None
    except Exception as e:
        logger.warning("[trend-refine] Serper search failed: %s", e)
        return None


# --- Deep search (BrightData primary, Serper fallback) ---

def deep_search(query, gl="us", hl="en"):
    data = brightdata_search(query, gl, hl)
    if data and (data.get("organic") or data.get("related_searches")):
        return {"source": "brightdata", "data": data}
    data = serper_search(query, gl, hl)
    if data and (data.get("organic") or data.get("relatedSearches")):
        return {"source": "serper", "data": data}
    return None


def _normalize(search_result):
    if not search_result:
        return {"organic": [], "related": []}
    data = search_result.get("data", {})
    source = search_result.get("source", "")
    if source == "brightdata":
        return {"organic": data.get("organic", []), "related": data.get("related_searches", [])}
    elif source == "serper":
        return {"organic": data.get("organic", []), "related": data.get("relatedSearches", [])}
    else:
        return {"organic": data.get("organic", []),
                "related": data.get("related_searches", data.get("relatedSearches", []))}


# --- Subject extraction ---

def _extract_from_related(related, seeds_flat, market="US"):
    subjects = []
    for term in related:
        if not isinstance(term, str):
            continue
        cleaned = _clean_related_for_market(term, market)
        if _is_generic(cleaned, market):
            continue
        if not _is_specific(cleaned, market, seeds_flat):
            continue
        if cleaned.startswith("Category:") or cleaned.startswith("カテゴリ:") or cleaned.startswith("분류:"):
            continue
        if _is_echo(cleaned, term, market):
            continue
        seed_match = False
        for st in seeds_flat:
            if st.lower() in cleaned.lower() or cleaned.lower() in st.lower():
                subjects.append({"subject": st, "source": "related+seed", "raw": term})
                seed_match = True
                break
        if not seed_match and len(cleaned.split()) <= 5:
            subjects.append({"subject": cleaned, "source": "related", "raw": term})
    return subjects


def _extract_from_organic(organic, seeds_flat, market="US", generic_term=""):
    subjects = []
    for item in organic:
        title = item.get("title", "") if isinstance(item, dict) else str(item)
        if not title:
            continue
        found = False
        for st in seeds_flat:
            if st.lower() in title.lower():
                subjects.append({"subject": st, "source": "organic+seed", "raw": title})
                found = True
                break
        if found:
            continue
        patterns = SUBJECT_PATTERNS_BY_MARKET.get(market, SUBJECT_PATTERNS)
        for pattern in patterns:
            m = re.search(pattern, title, re.IGNORECASE)
            if m:
                subject = m.group(1).strip()
                if not _is_generic(subject, market) and _is_specific(subject, market, seeds_flat) and 3 <= len(subject) <= (30 if market in ("JP", "KR") else 50):
                    if subject.startswith("Category:") or subject.startswith("カテゴリ:") or subject.startswith("분류:"):
                        continue
                    subjects.append({"subject": subject, "source": "organic+pattern", "raw": title})
                break
    return subjects


# --- Validation (FREE signals) ---

def _validate(subject, market="US"):
    hl = LOCALE.get(market, ("us", "en"))[1]
    gl_upper = market
    result = {
        "subject": subject,
        "google_ac": False,
        "youtube_ac": False,
        "wiki_spike": 0.0,
        "seed_match": False,
    }
    try:
        from app.services.trend_free_signals import google_autocomplete
        suggestions = google_autocomplete(subject, hl=hl, gl=gl_upper)
        if suggestions:
            for s in suggestions:
                if subject.lower() in s.lower():
                    result["google_ac"] = True
                    break
    except Exception:
        pass
    try:
        from app.services.trend_free_signals import youtube_autocomplete
        suggestions = youtube_autocomplete(subject, hl=hl, gl=gl_upper)
        if suggestions:
            for s in suggestions:
                if subject.lower() in s.lower():
                    result["youtube_ac"] = True
                    break
    except Exception:
        pass
    try:
        from app.services.trend_sources_v5 import wiki_article_spike
        project = WIKI_PROJECT.get(market, "en.wikipedia")
        spike_data = wiki_article_spike(project, subject)
        if spike_data:
            result["wiki_spike"] = float(spike_data.get("spike", 0.0) or 0.0)
    except Exception:
        pass
    try:
        seeds = _get_seeds_flat(market)
        if subject in seeds:
            result["seed_match"] = True
    except Exception:
        pass
    return result


# --- Scoring ---

def _score(v):
    s = 0.0
    s += 0.25
    s += 0.20 if v.get("google_ac") else 0.0
    s += 0.20 if v.get("youtube_ac") else 0.0
    s += min(0.15, float(v.get("wiki_spike", 0.0)) * 0.15)
    s += 0.10 if v.get("seed_match") else 0.0
    s += 0.10 if float(v.get("wiki_spike", 0.0)) > 0.1 else 0.0
    return round(s, 3)


# --- Main entry ---

def refine_raw_pool(raw_pool_data, max_searches_per_market=5):
    """Refine raw pool generic categories into specific subjects.

    Args:
        raw_pool_data: dict from collect_raw_pool() or loaded from JSON
        max_searches_per_market: max Google searches per market (quota guard)

    Returns:
        dict: refined pool with specific subjects + scores per market
    """
    seeds_flat_all = _get_seeds_flat()
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "trend_refine_v1",
        "by_market": {},
    }
    for market, block in (raw_pool_data.get("by_market") or {}).items():
        gl, hl = LOCALE.get(market, ("us", "en"))
        seeds_flat = _get_seeds_flat(market)
        # Step 1: Extract generic terms from raw pool (Nhom 1 output)
        generic_terms = []
        seen_generics = set()
        
        def _add_generic(term, sub_regions):
            if term and not _is_generic(term):
                is_specific = any(st.lower() == term.lower() for st in seeds_flat_all)
                if not is_specific and term not in seen_generics:
                    seen_generics.add(term)
                    generic_terms.append({"term": term, "sub_regions_detected": sub_regions})
                    
        ctx = block.get("_context") or {}
        cross = ctx.get("cross_confirmed_google_youtube") or []
        for item in cross:
            _add_generic(_extract_term(item), [])
            
        for lane_name in ("google_autocomplete", "youtube_autocomplete"):
            lane = block.get(lane_name) or []
            for item in lane[:10]:
                _add_generic(_extract_term(item), [])
                
        gtrends = block.get("gtrends_daily") or []
        for item in gtrends[:5]:
            _add_generic(_extract_term(item), [])
        generic_terms = generic_terms[:max_searches_per_market]
        # Step 1b (proactive seed check, 14/08/2026 decision - see Decisions Log):
        # always test curated SEED_TITLES via 100% free signals (google/youtube
        # autocomplete + wiki spike) so specific-key discovery never depends
        # solely on weak discovery lanes or paid deep-search quota (BrightData/Serper).
        seed_scored = []
        for seed_title in seeds_flat:
            v = _validate(seed_title, market)
            v["source"] = "seed_proactive"
            v["generic_term"] = ""
            v["search_source"] = ""
            v["score"] = _score(v)
            seed_scored.append(v)
        if not generic_terms and not seed_scored:
            out["by_market"][market] = {"generic_terms": [], "subjects": [], "searches": 0}
            continue
        # Step 2: Deep search each generic term
        all_subjects = []
        searches_made = 0
        for g_dict in generic_terms:
            if isinstance(g_dict, str):
                term = g_dict
                sub_regions = []
            else:
                term = g_dict.get("term", "")
                sub_regions = g_dict.get("sub_regions_detected", [])
                
            sr = sub_regions[0] if sub_regions else None
            # Fetch local gl, hl if we have a sub-region
            if sr:
                # Need to use AC_HL_GL but note it returns (hl, gl) in virality and here gl, hl is expected?
                # deep_search(term, gl, hl)
                # Let's just manually map it to be safe
                loc_map = {"US": ("us", "en"), "JP": ("jp", "ja"), "KR": ("kr", "ko"), "GB": ("gb", "en"), "AU": ("au", "en"), "CA": ("ca", "en"), "DE": ("de", "de"), "NZ": ("nz", "en")}
                loc_gl, loc_hl = loc_map.get(sr.upper(), ("us", "en"))
            else:
                loc_gl, loc_hl = gl, hl
                
            search_result = deep_search(term, gl=loc_gl, hl=loc_hl)
            searches_made += 1
            if not search_result:
                continue
            normalized = _normalize(search_result)
            related_subjects = _extract_from_related(normalized["related"], seeds_flat, market)
            organic_subjects = _extract_from_organic(normalized["organic"], seeds_flat, market, term)
            seen = set()
            for s in related_subjects + organic_subjects:
                key = s["subject"].lower()
                if key not in seen:
                    seen.add(key)
                    s["generic_term"] = term
                    s["search_source"] = search_result.get("source", "")
                    s["sub_regions_detected"] = sub_regions # KEEP SUB REGION
                    all_subjects.append(s)
        # Step 3: Validate and score
        scored = []
        for s in all_subjects:
            v = _validate(s["subject"], market)
            v["source"] = s.get("source", "")
            v["generic_term"] = s.get("generic_term", "")
            v["search_source"] = s.get("search_source", "")
            v["score"] = _score(v)
            scored.append(v)
        seen_subjects = {x["subject"].lower() for x in scored}
        for v in seed_scored:
            if v["subject"].lower() not in seen_subjects:
                scored.append(v)
                seen_subjects.add(v["subject"].lower())
        scored.sort(key=lambda x: x["score"], reverse=True)
        out["by_market"][market] = {
            "generic_terms": generic_terms,
            "subjects": scored,
            "searches": searches_made,
        }
    try:
        from app.services import bd_serp_budget
        out["budget"] = bd_serp_budget.read_budget()
    except Exception:
        pass
    return out
