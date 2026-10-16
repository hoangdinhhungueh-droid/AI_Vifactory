# app/services/virality_score.py
"""
Virality scoring -- Step 3 in pipeline:
  raw pool (02:00) -> deep scrape (02:10) -> virality scoring (02:15) -> alert -> /trend:gate
Scores refined pool subjects (or evergreen fallback) for virality potential using free signals.

ENHANCED 09/08/2026 (v2):
  - Dual-track scoring: virality_score (trend-relative, UNCHANGED) + abs_score (absolute hotness, ENHANCED)
  - abs_score uses log-scale wiki views + Google AC count + YouTube AC count (3 sources, standalone track)
  - produced_ledger gate: skip subjects already produced (QID-based anti-repeat)
UPGRADED 24/08/2026 (v3 - R1):
  - On-demand Google Trends Rising (Breakout / Đột biến) & Top Queries extraction via pytrends for GT_gate >= 70
  - Injects rising_queries & top_queries into subject scoring payload
  - Cleans technical/HTTP artifacts and filters top 3-5 breakout queries
  - Fast execution & robust seed coverage for JP/KR to prevent timeout and ensure real data pass-through
"""

import os, json, time, logging, math, re
from datetime import datetime, timezone

from core.paths import resolve_raw_pool_dir

logger = logging.getLogger(__name__)
RAW_POOL_DIR = str(resolve_raw_pool_dir())

LOCALE = {"US": ("en", "US"), "EN": ("en", "US"), "JP": ("ja", "JP"), "KR": ("ko", "KR")}
AC_HL_GL = {"US": ("en", "US"), "EN": ("en", "US"), "JP": ("ja", "JP"), "KR": ("ko", "KR"), "GB": ("en", "GB"), "AU": ("en", "AU"), "CA": ("en", "CA"), "DE": ("de", "DE"), "NZ": ("en", "NZ")}
WIKI_PROJECT = {"US": "en", "JP": "ja", "KR": "ko"}
WIKI_LANG = {"US": "en", "JP": "ja", "KR": "ko"}

GENERIC_SUBJECTS = {
    "corporate", "the corporate", "company", "the company", "business",
    "corporation", "firm", "organization", "corporate failures",
    "business scandals", "corporate scandal", "corporate scandals",
}

SEED_TITLES_JP = [
    "孤独死", "認知的不協和", "ライブドア事件", "東芝不正会計事件",
    "地下鉄サリン事件", "松本サリン事件", "過労死", "ひきこもり",
    "振り込め詐欺", "リクルート事件", "オリンパス事件",
]
SEED_TITLES_KR = [
    "도박 중독", "다단계", "보이스피싱", "전세사기",
    "대우그룹", "삼풍백화점", "신창원", "유영철",
    "삼성그룹", "조두순", "외환위기",
]
SEED_TITLES_LOCAL = {"JP": SEED_TITLES_JP, "KR": SEED_TITLES_KR}

TECHNICAL_ARTIFACT_PATTERNS = [
    re.compile(r'https?://\S+', re.I),
    re.compile(r'^(?:404|500|502|503|504|error|null|undefined|nan|none)$', re.I),
    re.compile(r'\b(?:(?:http|status|error|code)\s*(?:404|500|502|503|504)|(?:404|500|502|503|504)\s*(?:error|internal|server\s*error|not\s*found|bad\s*gateway|gateway\s*timeout|service\s*unavailable|timeout))\b', re.I),
    re.compile(r'\b(?:gateway\s*time[- ]?out|request\s*time[- ]?out|connection\s*timed?\s*out|server\s*time[- ]?out|socket\s*time[- ]?out)\b', re.I),
    re.compile(r'\b(?:undefined|null|nan|\[object\s+Object\])\b', re.I),
    re.compile(r'\b(?:syntax\s*error|runtime\s*error|server\s*error|internal\s*error|fatal\s*error|system\s*error|http\s*error|fetch\s*error)\b', re.I),
    re.compile(r'\b(?:stack\s*trace|exception|traceback|connection\s*reset|connection\s*refused)\b', re.I),
    re.compile(r'[{}\[\]<>]'),
]

def is_clean_search_query(q: str) -> bool:
    """Validate that query string is a realistic search phrase and not a technical error/artifact."""
    if not q or not isinstance(q, str):
        return False
    q_clean = q.strip()
    if len(q_clean) < 2 or len(q_clean) > 120:
        return False
    for pat in TECHNICAL_ARTIFACT_PATTERNS:
        if pat.search(q_clean):
            return False
    if not re.search(r'[\w]', q_clean, re.UNICODE):
        return False
    return True

def _parse_growth_value(val) -> tuple[int, str]:
    """Parse growth metric into (sort_priority, display_string).
    Prioritizes 'Breakout' / 'Đột biến', then descending by growth %.
    """
    if val is None or isinstance(val, bool):
        return 0, "+0%"
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("none", "null", "nan", "undefined"):
        return 0, "+0%"
    val_lower = val_str.lower()
    if "breakout" in val_lower or "đột biến" in val_lower or "dot bien" in val_lower:
        return 100_000_000, "Breakout"
    
    cleaned_num = val_str.replace(",", "")
    match = re.search(r'([0-9]+(?:\.[0-9]+)?)', cleaned_num)
    if match:
        try:
            raw_float = float(match.group(1))
            num = int(round(raw_float))
            if num >= 5000:
                return num + 10_000_000, f"+{num}% (Breakout)"
            return num, f"+{num}%"
        except (ValueError, OverflowError) as _parse_err:
            logger.debug(f"[virality_score] Notice invalid float parsing '{match.group(1)}': {_parse_err}")
    return 0, val_str or "+0%"


def extract_clean_breakout_queries(rising_queries: list, max_count: int = 5) -> list[str]:
    """Sort rising queries prioritizing Breakout / Đột biến, then descending by growth %,
    filter out technical artifacts and return Top 3-5 clean search query strings.
    """
    if not rising_queries:
        return []
    
    by_norm = {}
    for item in rising_queries:
        if isinstance(item, dict):
            q = str(item.get("query") or item.get("term") or item.get("keyword") or item.get("name") or item.get("article") or "").strip()
            v = item.get("value") if item.get("value") is not None else (item.get("extracted_value") or "")
        elif isinstance(item, str):
            q = item.strip()
            v = "Breakout"
        else:
            continue
        
        if not is_clean_search_query(q):
            continue
        
        q_norm = q.lower()
        prio, val_display = _parse_growth_value(v)
        if q_norm not in by_norm or prio > by_norm[q_norm]["priority"]:
            by_norm[q_norm] = {"query": q, "value": val_display, "priority": prio}
        
    items = list(by_norm.values())
    items.sort(key=lambda x: x["priority"], reverse=True)
    return [x["query"] for x in items[:max_count]]


extract_clean_rising_queries = extract_clean_breakout_queries

def _is_viable_subject(subject):
    s = subject.lower().strip()
    if not s or len(s) < 3:
        return False
    if s in GENERIC_SUBJECTS:
        return False
    if s.startswith("category:") or s.startswith("カテゴリ:") or s.startswith("분류:"):
        return False
    if len(s) > 60:
        return False
    return True

def _google_ac(seed, hl="en", gl="US"):
    try:
        from app.services.trend_free_signals import google_autocomplete
        return google_autocomplete(seed, hl=hl, gl=gl, timeout=6.0)
    except Exception:
        return []

def _youtube_ac(seed, hl="en", gl="US"):
    try:
        from app.services.trend_free_signals import youtube_autocomplete
        return youtube_autocomplete(seed, hl=hl, gl=gl, timeout=6.0)
    except Exception:
        return []

def _wiki_pv(title, project="en", days=30):
    """Get 30-day total+max AND 7-day avg+max in a SINGLE API call (with 429 retry)."""
    import urllib.error
    for attempt in range(2):
        try:
            safe = urllib.parse.quote(title.replace(" ", "_"))
            url = "https://%s.wikipedia.org/w/api.php?action=query&titles=%s&prop=pageviews&pvipdays=%d&format=json" % (project, safe, days)
            req = urllib.request.Request(url, headers={"User-Agent": "VF-Virality/1.0"})
            with urllib.request.urlopen(req, timeout=6.0) as r:
                data = json.loads(r.read())
            for _pid, page in data.get("query", {}).get("pages", {}).items():
                pv = page.get("pageviews", {})
                views = [(k, v) for k, v in pv.items() if v is not None]
                if views:
                    total_30 = sum(v for _, v in views)
                    max_30 = max(v for _, v in views)
                    last_7 = views[-7:]
                    avg_7 = round(sum(v for _, v in last_7) / len(last_7), 1) if last_7 else 0.0
                    max_7 = max(v for _, v in last_7) if last_7 else 0
                    return total_30, max_30, avg_7, max_7
            return 0, 0, 0.0, 0
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 1:
                time.sleep(1.5)
                continue
            return 0, 0, 0.0, 0
        except Exception:
            return 0, 0, 0.0, 0
    return 0, 0, 0.0, 0

def _norm_wiki(total):
    if total <= 0:
        return 0.0
    return min(1.0, math.log10(total + 1) / 6.0)


# --- Google Trends REAL index ---
GT_MIN_RATIO = float(os.getenv("VF_GT_MIN_RATIO", "70"))
GT70_WINDOW = os.getenv("VF_GT70_WINDOW", "7")
GT_MIN_RATIO_DAILY = float(os.getenv("VF_GT_MIN_RATIO_DAILY", "65"))


def _gt_cache_path(day):
    return os.path.join(RAW_POOL_DIR, "gt_cache_%s.json" % day)


def _parse_related_queries_df(rq_dict, subject: str | None = None):
    """Parse pytrends / SerpApi / JSON related_queries into (rising_queries, top_queries)."""
    rising_list = []
    top_list = []
    if not isinstance(rq_dict, dict):
        return rising_list, top_list

    sub_data = None
    if subject:
        sub_data = rq_dict.get(subject)

    if not sub_data or not isinstance(sub_data, (dict, list)):
        if "related_queries" in rq_dict and isinstance(rq_dict["related_queries"], dict):
            sub_data = rq_dict["related_queries"]
        elif "rising" in rq_dict or "top" in rq_dict:
            sub_data = rq_dict
        elif subject:
            for k, v in rq_dict.items():
                if str(k).strip().lower() == str(subject).strip().lower():
                    sub_data = v
                    break
        elif len(rq_dict) == 1:
            first_val = list(rq_dict.values())[0]
            if isinstance(first_val, dict) and ("rising" in first_val or "top" in first_val):
                sub_data = first_val

    if not sub_data or not isinstance(sub_data, dict):
        return rising_list, top_list

    rising_raw = sub_data.get("rising")
    if rising_raw is not None:
        try:
            by_norm_r = {}
            if hasattr(rising_raw, "iterrows"):
                for _, row in rising_raw.iterrows():
                    q = str(row.get("query", "")).strip()
                    val = row.get("value") if row.get("value") is not None else row.get("extracted_value")
                    if q and is_clean_search_query(q):
                        qn = q.lower()
                        prio, val_str = _parse_growth_value(val)
                        if qn not in by_norm_r or prio > by_norm_r[qn]["priority"]:
                            by_norm_r[qn] = {"query": q, "value": val_str, "priority": prio}
            elif isinstance(rising_raw, list):
                for item in rising_raw:
                    if isinstance(item, dict):
                        q = str(item.get("query") or item.get("term") or item.get("keyword") or item.get("name") or "").strip()
                        val = item.get("value") if item.get("value") is not None else (item.get("extracted_value") or item.get("rise") or "")
                    elif isinstance(item, str):
                        q = item.strip()
                        val = "Breakout"
                    else:
                        continue
                    if q and is_clean_search_query(q):
                        qn = q.lower()
                        prio, val_str = _parse_growth_value(val)
                        if qn not in by_norm_r or prio > by_norm_r[qn]["priority"]:
                            by_norm_r[qn] = {"query": q, "value": val_str, "priority": prio}
            elif isinstance(rising_raw, dict):
                for k, v in rising_raw.items():
                    q = str(k).strip()
                    val = v
                    if q and is_clean_search_query(q):
                        qn = q.lower()
                        prio, val_str = _parse_growth_value(val)
                        if qn not in by_norm_r or prio > by_norm_r[qn]["priority"]:
                            by_norm_r[qn] = {"query": q, "value": val_str, "priority": prio}
            temp_rising = list(by_norm_r.values())
            temp_rising.sort(key=lambda x: x["priority"], reverse=True)
            for item in temp_rising:
                rising_list.append({"query": item["query"], "value": item["value"]})
        except Exception as e:
            logger.warning("[virality] Error parsing rising_df for %s: %s", subject, e)

    top_raw = sub_data.get("top")
    if top_raw is not None:
        try:
            seen_t = set()
            if hasattr(top_raw, "iterrows"):
                for _, row in top_raw.iterrows():
                    q = str(row.get("query", "")).strip()
                    val = row.get("value") if row.get("value") is not None else row.get("extracted_value")
                    if q and is_clean_search_query(q):
                        qn = q.lower()
                        if qn not in seen_t:
                            seen_t.add(qn)
                            top_list.append({"query": q, "value": str(val).strip()})
            elif isinstance(top_raw, list):
                for item in top_raw:
                    if isinstance(item, dict):
                        q = str(item.get("query") or item.get("term") or item.get("keyword") or item.get("name") or "").strip()
                        val = item.get("value") if item.get("value") is not None else (item.get("extracted_value") or "")
                    elif isinstance(item, str):
                        q = item.strip()
                        val = "100"
                    else:
                        continue
                    if q and is_clean_search_query(q):
                        qn = q.lower()
                        if qn not in seen_t:
                            seen_t.add(qn)
                            top_list.append({"query": q, "value": str(val).strip()})
            elif isinstance(top_raw, dict):
                for k, v in top_raw.items():
                    q = str(k).strip()
                    val = str(v).strip()
                    if q and is_clean_search_query(q):
                        qn = q.lower()
                        if qn not in seen_t:
                            seen_t.add(qn)
                            top_list.append({"query": q, "value": val})
        except Exception as e:
            logger.warning("[virality] Error parsing top_df for %s: %s", subject, e)

    return rising_list, top_list

def _gtrends_related_queries(subject, market="US", sub_region=None):
    """Fetch on-demand Google Trends related queries (rising + top) for topics with GT >= 70."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_key = ((sub_region or market or "US").upper()) + "|" + subject.strip().lower()

    try:
        from pytrends.request import TrendReq
        hl, gl = AC_HL_GL.get((sub_region or market).upper(), LOCALE.get(market, ("en", "US")))
        hl_full = "%s-%s" % (hl, gl.upper())
        GT_MAX_RETRIES = int(os.getenv("VF_GT_RETRIES", "2"))
        rq_dict = None
        for attempt in range(GT_MAX_RETRIES):
            try:
                pt = TrendReq(hl=hl_full, tz=420, timeout=(6, 12))
                pt.build_payload([subject], cat=0, timeframe="today 1-m", geo=gl, gprop="")
                rq_dict = pt.related_queries()
                break
            except Exception as e:
                msg = str(e)
                if "429" in msg and attempt < GT_MAX_RETRIES - 1:
                    time.sleep(3.0)
                    continue
                break
        if rq_dict:
            rising, top = _parse_related_queries_df(rq_dict, subject)
            try:
                cp = _gt_cache_path(day)
                cache = {}
                if os.path.exists(cp):
                    with open(cp, "r", encoding="utf-8") as f:
                        cache = json.load(f)
                if cache_key in cache and isinstance(cache[cache_key], dict):
                    cache[cache_key]["rising_queries"] = rising
                    cache[cache_key]["top_queries"] = top
                    tmp = cp + ".tmp"
                    with open(tmp, "w", encoding="utf-8") as f:
                        json.dump(cache, f, ensure_ascii=False)
                    os.replace(tmp, cp)
            except Exception as _ce:
                logger.warning("[virality] Failed to update gt_cache with related queries: %s", _ce)
            return rising, top
    except Exception as e:
        logger.warning("[virality] gtrends related_queries failed for '%s' (%s): %s", subject, market, e)

    return [], []


def _gtrends_ratio(subject, market="US", sub_region=None):
    """Fetch the REAL Google Trends index (0-100, the exact number shown on
    trends.google.com) via pytrends. Returns {avg7, avg30, peak, avg7_ratio,
    avg30_ratio, rising_queries, top_queries} or None on failure."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_key = ((sub_region or market or "US").upper()) + "|" + subject.strip().lower()
    cache = {}
    try:
        cp = _gt_cache_path(day)
        if os.path.exists(cp):
            with open(cp, "r", encoding="utf-8") as f:
                cache = json.load(f)
        if cache_key in cache:
            return cache[cache_key]
    except Exception as e:
        logger.warning("[virality] gt cache read failed: %s", e)
        cache = {}
    try:
        import urllib3.util.retry as _retry_mod
        _OrigRetry = _retry_mod.Retry

        class _CompatRetry(_OrigRetry):
            def __init__(self, *a, **kw):
                mw = kw.pop("method_whitelist", None)
                if mw is not None and "allowed_methods" not in kw:
                    kw["allowed_methods"] = mw
                super().__init__(*a, **kw)

        _retry_mod.Retry = _CompatRetry
        import urllib3.util
        urllib3.util.Retry = _CompatRetry
        from pytrends.request import TrendReq

        hl, gl = AC_HL_GL.get((sub_region or market).upper(), LOCALE.get(market, ("en", "US")))
        hl_full = "%s-%s" % (hl, gl.upper())
        GT_MAX_RETRIES = int(os.getenv("VF_GT_RETRIES", "2"))
        df = None
        pt = None
        for attempt in range(GT_MAX_RETRIES):
            try:
                pt = TrendReq(hl=hl_full, tz=420, timeout=(6, 12))
                pt.build_payload([subject], cat=0, timeframe="today 1-m", geo=gl, gprop="")
                df = pt.interest_over_time()
                break
            except Exception as e:
                msg = str(e)
                if "429" in msg and attempt < GT_MAX_RETRIES - 1:
                    time.sleep(3.0)
                    continue
                break
        if df is None or df.empty:
            logger.warning("[virality] gtrends empty for '%s' (%s)", subject, market)
            return None
        if "isPartial" in df.columns:
            df = df[~df["isPartial"]]
        series = [int(v) for v in df[subject].tolist()]
        if not series or max(series) <= 0:
            logger.warning("[virality] gtrends all-zero for '%s' (%s)", subject, market)
            return None
        peak = max(series)
        peak_idx = df[subject].idxmax()
        peak_date = peak_idx.strftime("%Y-%m-%d") if hasattr(peak_idx, "strftime") else str(peak_idx)[:10]
        tail7 = series[-7:]
        avg7 = round(sum(tail7) / len(tail7), 1)
        avg30 = round(sum(series) / len(series), 1)
        avg1 = series[-1]
        avg7_ratio = round(avg7 / peak * 100.0, 1)

        rising_queries = []
        top_queries = []
        if avg7_ratio >= GT_MIN_RATIO and pt is not None:
            try:
                rq_dict = pt.related_queries()
                rising_queries, top_queries = _parse_related_queries_df(rq_dict, subject)
                logger.info("[virality] Extracted %d rising & %d top queries for '%s' (%s)",
                            len(rising_queries), len(top_queries), subject, market)
            except Exception as _rq_err:
                logger.warning("[virality] related_queries extraction failed for '%s': %s", subject, _rq_err)

        result = {
            "avg7": avg7,
            "avg30": avg30,
            "avg1": avg1,
            "peak": peak,
            "peak_date": peak_date,
            "avg7_ratio": avg7_ratio,
            "avg30_ratio": round(avg30 / peak * 100.0, 1),
            "avg1_ratio": round(avg1 / peak * 100.0, 1),
            "rising_queries": rising_queries,
            "top_queries": top_queries,
        }
        try:
            cache[cache_key] = result
            tmp = _gt_cache_path(day) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False)
            os.replace(tmp, _gt_cache_path(day))
        except Exception as e:
            logger.warning("[virality] gt cache write failed: %s", e)
        return result
    except Exception as e:
        logger.warning("[virality] gtrends failed for '%s' (%s): %s", subject, market, e)
        return None


def _check_produced(subject, market):
    """Check if subject was already produced (QID-based anti-repeat)."""
    try:
        from app.services.produced_ledger import gate as _gate
        lang = WIKI_LANG.get(market, "en")
        result = _gate(subject, market, lang=lang)
        return result.get("blocked", False), result.get("qid")
    except Exception as e:
        logger.warning("[virality] produced_ledger gate failed for '%s': %s", subject, e)
        return False, None


_POLICY_BLACKLIST_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts", "blacklist.json")

CHILD_EXPLOITATION_HARD_PATTERNS = [
    r"아동\s?(성|학대|착취|음란)", r"미성년자\s?(성|피해|착취)",
    r"child\s?(sexual|sex)\s?(abuse|exploitation)", r"child\s?porn", r"minor\s?victim", r"grooming",
    r"小児性", r"児童\s?(虐待|買春|ポルノ|性的)",
]

_policy_blacklist_cache = {"mtime": None, "exact": set(), "patterns": []}


def _load_policy_blacklist():
    try:
        mtime = os.path.getmtime(_POLICY_BLACKLIST_PATH)
        if _policy_blacklist_cache["mtime"] != mtime:
            with open(_POLICY_BLACKLIST_PATH, encoding="utf-8") as f:
                data = json.load(f)
            _policy_blacklist_cache["exact"] = {s.lower() for s in data.get("exact", [])}
            _policy_blacklist_cache["patterns"] = [re.compile(p, re.IGNORECASE) for p in data.get("patterns", [])]
            _policy_blacklist_cache["mtime"] = mtime
    except Exception as e:
        logger.warning("[virality] policy blacklist reload failed: %s", e)
    return _policy_blacklist_cache


def _check_policy_blocklist(subject):
    if not subject:
        return False, None
    low = subject.lower()
    for pat in CHILD_EXPLOITATION_HARD_PATTERNS:
        if re.search(pat, subject, re.IGNORECASE):
            return True, "child_exploitation_policy"
    bl = _load_policy_blacklist()
    if low in bl["exact"]:
        return True, "platform_blacklist_exact"
    for pat in bl["patterns"]:
        if pat.search(subject):
            return True, "platform_blacklist_pattern"
    return False, None


_TRENDING_KW = [
    "scandal", "explained", "documentary", "movie", "story", "doku", "trailer",
    "series", "case", "news", "fraud", "bankruptcy", "arrest", "trial", "crash", "collapse",
    "controversy", "lawsuit", "investigation", "crisis", "skandal", "2008", "2001", "2026", "2025",
    "解説", "ドキュ", "事件", "ニュース", "スキャンダル", "詐欺", "倒産",
    "해설", "다큐", "사건", "뉴스", "스캔들", "사기", "파산",
]

def _trending_count(suggestions, subject=""):
    subject_lower = subject.lower().strip()
    count = 0
    for s in suggestions:
        remaining = s.lower()
        if subject_lower:
            remaining = remaining.replace(subject_lower, "")
        if any(kw in remaining for kw in _TRENDING_KW):
            count += 1
    return count


def _score_autocomplete(suggestions, subject):
    if not suggestions:
        return 0.0
    trending_matches = _trending_count(suggestions, subject)
    long_tail_count = sum(1 for s in suggestions if len(s.split()) >= 3)
    trend_score = min(trending_matches / 4.0, 1.0) * 0.6
    long_tail_score = min(long_tail_count / 6.0, 1.0) * 0.4
    return round(trend_score + long_tail_score, 3)

def score_subject(subject, market="US", sub_region=None):
    """Score a single subject for virality potential (0-1).
    HARD GT GATE (Rule 118, Decisions Log): GT_gate >= 70 strictly required.
    """
    hl, gl = AC_HL_GL.get((sub_region or market).upper(), LOCALE.get(market, ("en", "US")))
    project = WIKI_PROJECT.get(market, "en")
    
    gt = _gtrends_ratio(subject, market, sub_region)
    avg7 = gt.get("avg7", 0) if gt else 0
    peak = gt.get("peak", 0) if gt else 0
    gt_ratio = gt.get("avg7_ratio", 0) if gt else 0
    
    # STRICT USER GATE (05/09/2026):
    # 1. 7-day average Google Trends index >= 70 (avg7 >= 70)
    # 2. 30-day peak Google Trends index == 100 (at least 1 day with peak 100)
    if not gt or avg7 < 70 or peak < 100:
        return {
            "rejected": True,
            "reason": "gt_gate_failed",
            "gt_avg7": avg7,
            "gt_peak": peak,
            "gt_avg7_ratio": gt_ratio,
            "detail": f"avg7={avg7} (min 70), peak={peak} (min 100)"
        }

    gt_70 = True

    rising_queries = gt.get("rising_queries")
    top_queries = gt.get("top_queries")
    if rising_queries is None or top_queries is None:
        rising_queries, top_queries = _gtrends_related_queries(subject, market=market, sub_region=sub_region)
        gt["rising_queries"] = rising_queries
        gt["top_queries"] = top_queries

    breakout_queries = extract_clean_breakout_queries(rising_queries, max_count=5)

    g = _google_ac(subject, hl=hl, gl=gl)
    y = _youtube_ac(subject, hl=hl, gl=gl)
    doc_words = ["documentary", "explained", "doc", "story", "history", "movie", "解説", "ドキュ", "다큐", "설명"]
    doc_terms = [s for s in y if any(w in s.lower() for w in doc_words)]
    total_pv, max_pv, wiki_7d_avg, wiki_7d_max = _wiki_pv(subject, project=project)

    g_score = _score_autocomplete(g, subject)
    y_score = _score_autocomplete(y, subject)
    doc_score = min(len(doc_terms) / 3.0, 1.0)
    wiki_score = _norm_wiki(total_pv)

    signals = [g_score > 0, y_score > 0, doc_score > 0, wiki_score > 0.3]
    cross = sum(signals) / len(signals)

    gt_score = gt_ratio / 100.0
    virality = (
        gt_score * 0.50 +
        g_score * 0.20 +
        y_score * 0.20 +
        doc_score * 0.05 +
        wiki_score * 0.05
    )

    wiki_abs = min(math.log10(wiki_7d_avg + 1) / 3.0, 1.0)
    g_trending = _trending_count(g, subject)
    y_trending = _trending_count(y, subject)
    gac_abs = min(g_trending / 10.0, 1.0)
    yac_abs = min(y_trending / 10.0, 1.0)
    abs_score = round(wiki_abs * 0.4 + gac_abs * 0.3 + yac_abs * 0.3, 3)

    trend_80 = (wiki_7d_avg >= 0.8 * max_pv) if max_pv else False

    return {
        "google_ac": g_score,
        "youtube_ac": y_score,
        "youtube_doc": doc_score,
        "wiki_interest": round(wiki_score, 3),
        "wiki_views_30d": total_pv,
        "wiki_max_day": max_pv,
        "cross_signal": round(cross, 3),
        "virality_score": round(virality, 3),
        "gt_score": round(gt_score, 3),
        "google_suggestions": len(g),
        "youtube_suggestions": len(y),
        "google_trending": g_trending,
        "youtube_trending": y_trending,
        "doc_suggestions": len(doc_terms),
        "wiki_daily_avg_7d": wiki_7d_avg,
        "wiki_daily_max_7d": wiki_7d_max,
        "trend_80": trend_80,
        "gt_avg7_index": gt.get("avg7") if gt else None,
        "gt_peak": gt.get("peak") if gt else None,
        "gt_peak_date": gt.get("peak_date") if gt else None,
        "gt_avg7_ratio": gt.get("avg7_ratio") if gt else None,
        "gt_avg30_ratio": gt.get("avg30_ratio") if gt else None,
        "gt_avg1_index": gt.get("avg1") if gt else None,
        "gt_avg1_ratio": gt.get("avg1_ratio") if gt else None,
        "gt_70": gt_70,
        "rising_queries": rising_queries or [],
        "breakout_queries": breakout_queries or [],
        "top_queries": top_queries or [],
        "abs_score": abs_score,
        "abs_wiki": round(wiki_abs, 3),
        "abs_gac": round(gac_abs, 3),
        "abs_yac": round(yac_abs, 3),
    }

def score_pool(day=None):
    """Score subjects from refined pool + evergreen fallback with strict GT >= 70 gate."""
    if not day:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    refined_path = os.path.join(RAW_POOL_DIR, "trend_refined_pool_%s.json" % day)
    raw_path = os.path.join(RAW_POOL_DIR, "trend_raw_pool_%s.json" % day)

    refined = {}
    if os.path.exists(refined_path):
        try:
            with open(refined_path) as f:
                refined = json.load(f)
        except (json.JSONDecodeError, OSError) as _read_err:
            logger.debug(f"[virality_score] Notice unreadable refined pool {refined_path}: {_read_err}")

    raw = {}
    if os.path.exists(raw_path):
        try:
            with open(raw_path) as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError) as _read_err:
            logger.debug(f"[virality_score] Notice unreadable raw pool {raw_path}: {_read_err}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "virality_score_v2",
        "day": day,
        "refined_pool": refined_path if os.path.exists(refined_path) else None,
        "by_market": {},
        "summary": {"total_scored": 0, "high_virality": 0, "total_blocked": 0},
    }

    total_scored = 0
    high_virality = 0
    total_blocked = 0

    markets = ["EN", "JP", "KR"]
    for mi, market in enumerate(markets):
        subjects = []

        if market in ("JP", "KR"):
            seeds = SEED_TITLES_LOCAL.get(market, [])
            for seed in seeds:
                subjects.append({"subject": seed, "source": "seed_titles_direct"})

        refined_mkt = refined.get("by_market", {}).get(market, {})
        for s in refined_mkt.get("subjects", []):
            name = s.get("subject", "")
            if name and not any(x.get("subject") == name for x in subjects):
                entry = dict(s)
                entry["subject"] = name
                entry["source"] = "refined"
                subjects.append(entry)

        if not subjects:
            raw_mkt = raw.get("by_market", {}).get(market, {})
            for e in raw_mkt.get("evergreen", [])[:10]:
                name = e.get("term", "") if isinstance(e, dict) else (e if isinstance(e, str) else "")
                if name and not any(x.get("subject") == name for x in subjects):
                    subjects.append({"subject": name, "source": "evergreen_fallback"})

        scored = []
        blocked_list = []
        
        # Prioritize evaluation: evaluate candidates until we find 3 solid candidates passing GT >= 70
        max_eval = min(len(subjects), 15)
        for s in subjects[:max_eval]:
            if len(scored) >= 3:
                break
            name = s.get("subject", "")
            if not name:
                continue

            blocked, qid = _check_produced(name, market)
            if blocked:
                blocked_list.append({"subject": name, "qid": qid, "market": market})
                total_blocked += 1
                continue

            pol_blocked, pol_reason = _check_policy_blocklist(name)
            if pol_blocked:
                blocked_list.append({"subject": name, "market": market, "reason": pol_reason})
                total_blocked += 1
                continue

            sub_regions = s.get("sub_regions_detected", [])
            primary_sub_region = sub_regions[0] if sub_regions else None
            vs = score_subject(name, market=market, sub_region=primary_sub_region)
            if primary_sub_region:
                vs["primary_sub_region"] = primary_sub_region
            if vs.get("rejected"):
                logger.info("[virality] REJECTED '%s' (%s) - reason: %s (GT_gate < 70, ratio=%s)",
                            name, market, vs.get("reason"), vs.get("gt_avg7_ratio"))
                continue
            
            merged = dict(s)
            merged.update(vs)
            scored.append(merged)
            total_scored += 1
            if vs.get("virality_score", 0) >= 0.65:
                high_virality += 1

        scored.sort(key=lambda x: x.get("virality_score", 0), reverse=True)

        top_abs = None
        if scored:
            by_abs = sorted(scored, key=lambda x: x.get("abs_score", 0), reverse=True)
            top_abs = {"subject": by_abs[0]["subject"], "abs_score": by_abs[0].get("abs_score", 0)}

        out["by_market"][market] = {
            "subjects": scored,
            "top_subject": scored[0]["subject"] if scored else None,
            "top_virality": scored[0].get("virality_score", 0) if scored else 0,
            "top_abs": top_abs,
            "blocked": blocked_list,
            "blocked_count": len(blocked_list),
        }

    out["summary"] = {
        "total_scored": total_scored,
        "high_virality": high_virality,
        "total_blocked": total_blocked,
    }

    virality_path = os.path.join(RAW_POOL_DIR, "trend_virality_pool_%s.json" % day)
    try:
        tmp = virality_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        os.replace(tmp, virality_path)
    except Exception as e:
        logger.warning("[virality] Failed to save virality pool: %s", e)

    return out
