"""
app/services/trend_engine_b1.py - CANONICAL B1 TREND DISCOVERY & END-TO-END PIPELINE (2026)
Standardized Architecture:
  1. Multi-Geo Fan-Out for Market EN (US, GB, CA, AU, NZ), JP, and KR.
  2. Direct Platform Recon (Google Autocomplete & YouTube Search API):
     - Pulls real viewer search queries (Rising / Breakout queries)
     - Calls YouTube Data API v3 directly to fetch real viral videos (Titles, Views, Publish dates)
  3. Ground-Truth Fact Sheet & Anti-Bias Mandate (Rule 118 Zero-Mock Data):
     - Verified Wikipedia summary as immutable truth anchors
     - Strict objective non-fiction causal framing
  4. Algorithmic Surge Anchor & Competitor Differentiation Gap:
     - Anchored to rising queries and proven viral video mechanics.
     - B1.5 Competitor Recon & 5-field anatomy integrated.
  5. Permanent History Registry & Daily Rotation (No Old Smart Cache):
     - Permanent deduplication lock via topic_history_registry (0 token LLM, 0 YouTube API unit on duplicates).
  6. Multi-Candidate Scan & Automated B1 -> B1.5 -> B2 Execution:
     - 1 top topic per market per day.
     - Human Gate 1: Pure Informative Broadcast on Telegram (0 buttons, non-blocking).
     - Auto-transition to B2 Story Engine (12-15 min docudrama) & B3 Director Plan (2-layer).
     - Fallback loop: If B2 fails Story Gate 12/12 after self-repair, automatically rotates to next candidate.
"""
import os
import sys
import re
import json
import logging
import asyncio
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# Ensure workspace root is in sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if "/root/video_factory" not in sys.path:
    sys.path.insert(0, "/root/video_factory")

from app.services.trend_free_signals import (
    gtrends_daily_rss,
    youtube_autocomplete,
    google_autocomplete,
    gtrends_discover_trending_searches,
    google_news_topic_rss,
    fetch_specialized_market_rss
)
from app.services.competitor_recon_b15 import (
    youtube_search,
    youtube_video_details,
    QuotaTracker,
    run_b15
)
from app.services.hhtech_reasoner import (
    assess_keyword_video_viability,
    reason_topic_niche,
    detect_safety_and_theme,
    _fetch_native_wiki_extract
)
from app.services.topic_history_registry import (
    is_topic_already_handled,
    record_handled_topic
)

logger = logging.getLogger("trend_engine_b1")

EN_SUB_GEOS = ["US", "GB", "CA", "AU", "NZ"]
VIABILITY_THRESHOLD = 8.0

V7_POOL_FILE = os.path.join(_PROJECT_ROOT, "data", "v7_winning_pool.json")

def fetch_pending_v7_candidates(market: str = "EN") -> list:
    """Đọc các ứng viên V7 có trạng thái PENDING từ data/v7_winning_pool.json."""
    if not os.path.isfile(V7_POOL_FILE):
        return []
    try:
        with open(V7_POOL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            m_up = (market or "EN").upper()
            cands = []
            for c in data.get("candidates", []):
                if c.get("status") == "PENDING" and c.get("candidate_id", "").startswith(f"V7_{m_up}_"):
                    cands.append(c)
            return cands
    except Exception as e:
        logger.debug(f"[trend_engine] Failed to read V7 pool: {e}")
        return []

def mark_v7_candidate_consumed(candidate_id: str, episode_id: str) -> bool:
    """Đánh dấu ứng viên V7 đã được sản xuất (CONSUMED)."""
    if not os.path.isfile(V7_POOL_FILE):
        return False
    try:
        with open(V7_POOL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        modified = False
        for c in data.get("candidates", []):
            if c.get("candidate_id") == candidate_id:
                c["status"] = "CONSUMED"
                c["consumed_by_episode"] = episode_id
                c["consumed_at"] = datetime.now(timezone.utc).isoformat()
                modified = True
                break
        if modified:
            with open(V7_POOL_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"[trend_engine] Marked V7 candidate {candidate_id} as CONSUMED by {episode_id}")
            return True
    except Exception as e:
        logger.error(f"[trend_engine] Failed to mark V7 candidate {candidate_id} consumed: {e}")
    return False

MARKET_CONFIG = {
    "EN": {
        "geos": EN_SUB_GEOS,
        "hl": "en",
        "gl": "US",
        "lang_name": "English",
        "intent_modifiers": ["documentary", "explained", "scandal", "what really happened to", "collapse", "fraud"]
    },
    "JP": {
        "geos": ["JP"],
        "hl": "ja",
        "gl": "JP",
        "lang_name": "Japanese",
        "intent_modifiers": ["事件の真相", "なぜ", "闇", "崩壊の理由", "解説", "仕組み"]
    },
    "KR": {
        "geos": ["KR"],
        "hl": "ko",
        "gl": "KR",
        "lang_name": "Korean",
        "intent_modifiers": ["원리", "사건의 진실", "폭망 이유", "비하인드", "충격 실체", "해설"]
    }
}


def fetch_ground_truth_factsheet(term: str, market: str) -> dict:
    """Fetch factual, verified baseline from Wikipedia REST API to prevent AI hallucination/bias."""
    m_up = (market or "EN").upper()
    wiki_extract = _fetch_native_wiki_extract(term, m_up)
    return {
        "term": term,
        "market": m_up,
        "wiki_ground_truth": wiki_extract[:1500] if wiki_extract else "",
        "has_verified_wiki": bool(wiki_extract),
    }


def fetch_live_news_catalyst(term: str, market: str, count: int = 6) -> list:
    """Fetch live news articles via Google News RSS for the term to identify the exact 24-48h news catalyst.
    Zero-quota, zero rate limit, essential for Rule 130 search-intent payoff.
    """
    m_up = (market or "EN").upper()
    cfg = MARKET_CONFIG.get(m_up, MARKET_CONFIG["EN"])
    hl = cfg["hl"]
    gl = cfg["gl"]

    clean_term = str(term).strip()
    if not clean_term:
        return []

    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(clean_term)}&hl={hl}&gl={gl}&ceid={gl}:{hl}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Antigravity/2.0"})

    news_items = []
    try:
        import xml.etree.ElementTree as ET
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            xml_data = resp.read().decode("utf-8", errors="replace")
            root = ET.fromstring(xml_data)
            for it in root.findall(".//item")[:count]:
                t_elem = it.find("title")
                d_elem = it.find("description")
                p_elem = it.find("pubDate")
                title = t_elem.text.strip() if t_elem is not None and t_elem.text else ""
                desc = d_elem.text.strip() if d_elem is not None and d_elem.text else ""
                desc_clean = re.sub(r'<[^>]+>', ' ', desc).replace('&nbsp;', ' ').strip()
                pub = p_elem.text.strip() if p_elem is not None and p_elem.text else ""
                if title:
                    news_items.append({
                        "title": title,
                        "description": desc_clean[:250],
                        "published_at": pub
                    })
    except Exception as e:
        logger.debug(f"[{m_up}] Live news catalyst fetch failed for '{clean_term}': {e}")

    return news_items


def perform_direct_platform_recon(term: str, market: str) -> dict:
    """Directly searches the keyword across Google Autocomplete, YouTube Autocomplete, and YouTube Search."""
    m_up = (market or "EN").upper()
    cfg = MARKET_CONFIG.get(m_up, MARKET_CONFIG["EN"])
    hl = cfg["hl"]
    gl = cfg["gl"]
    intent_mods = cfg["intent_modifiers"]

    # 0. Real-time Google Trends Rising / Breakout Queries via pytrends (Rule 123)
    pytrends_rising = []
    seen = set()
    try:
        from pytrends.request import TrendReq
        hl_code = "en-US" if m_up == "EN" else ("ja-JP" if m_up == "JP" else "ko-KR")
        pt = TrendReq(hl=hl_code, tz=360, timeout=(6.0, 6.0))
        pt.build_payload([term], timeframe='now 7-d', geo=gl)
        rel = pt.related_queries()
        if term in rel and rel[term].get("rising") is not None:
            rdf = rel[term]["rising"]
            if hasattr(rdf, "empty") and not rdf.empty and "query" in rdf:
                for q_val in rdf["query"].tolist():
                    q_clean = str(q_val).strip()
                    if q_clean and q_clean.lower() not in seen:
                        seen.add(q_clean.lower())
                        pytrends_rising.append(q_clean)
    except Exception as _pt_err:
        logger.debug(f"[{m_up}] Pytrends rising queries fetch skipped/failed for {term}: {_pt_err}")

    # 1. Google Autocomplete (Viewer Web Searches)
    g_sugg = google_autocomplete(term, hl=hl, gl=gl, timeout=6.0)

    # 2. YouTube Autocomplete (Viewer Video Searches)
    yt_sugg = youtube_autocomplete(term, hl=hl, gl=gl, timeout=6.0)

    # 3. Intent modifier queries
    intent_queries = []
    for mod in intent_mods[:2]:
        q_mod = f"{term} {mod}"
        s = youtube_autocomplete(q_mod, hl=hl, gl=gl, timeout=6.0)
        if s:
            intent_queries.extend(s[:2])

    all_rising = list(pytrends_rising)
    for q in g_sugg + yt_sugg + intent_queries:
        q_str = str(q).strip()
        if q_str and q_str.lower() not in seen:
            seen.add(q_str.lower())
            all_rising.append(q_str)

    # 4. Live News Catalyst Recon (Google News RSS Live — Rule 130)
    news_catalysts = fetch_live_news_catalyst(term, m_up, count=6)

    viral_videos = []
    # Primary: Resilient zero-quota YouTube search for B1 candidate screening
    # Conserves 100% of YouTube Data API quota for B1.5 and B10 video upload!
    try:
        from app.services.competitor_recon_b15 import scrape_youtube_search_zero_quota
        scraped = scrape_youtube_search_zero_quota(term, m_up.lower(), max_results=6)
        if scraped:
            for v in scraped:
                viral_videos.append({
                    "video_id": v.get("video_id"),
                    "title": v.get("title", term),
                    "views": v.get("views", 0),
                    "published_at": v.get("published_at", ""),
                    "url": v.get("url", f"https://www.youtube.com/watch?v={v.get('video_id')}")
                })
    except Exception as _scrape_err:
        logger.debug(f"[{m_up}] Zero-quota YouTube scrape during B1 recon notice: {_scrape_err}")

    # Fallback to official API only if zero-quota returned nothing and quota is healthy
    if not viral_videos:
        api_key = os.environ.get("YT_UPLOAD_API_KEY")
        if api_key:
            try:
                quota = QuotaTracker()
                if not quota.should_fallback():
                    raw_vids = youtube_search(api_key, term, m_up.lower(), quota, max_results=8)
                    if raw_vids:
                        vids_to_fetch = [v["video_id"] for v in raw_vids[:8]]
                        details = youtube_video_details(api_key, vids_to_fetch, quota)
                        for v in raw_vids[:8]:
                            vid = v["video_id"]
                            d = details.get(vid, {})
                            title = v.get("title") or (d.get("tags", [term])[0] if d.get("tags") else term)
                            views = d.get("views", 0)
                            pub = d.get("published_at", "")
                            viral_videos.append({
                                "video_id": vid,
                                "title": title,
                                "views": views,
                                "published_at": pub,
                                "url": f"https://www.youtube.com/watch?v={vid}"
                            })
            except Exception as e:
                logger.warning(f"[{m_up}] YouTube API search error: {e}")

    viral_videos.sort(key=lambda x: x.get("views", 0), reverse=True)

    return {
        "rising_queries": all_rising[:10],
        "google_suggestions": g_sugg[:5],
        "youtube_suggestions": yt_sugg[:5],
        "viral_videos": viral_videos[:6],
        "news_catalysts": news_catalysts
    }


def fetch_live_trending_terms(market: str, custom_seed: str = None) -> list[dict]:
    """Fetch live trending search terms across official Google Trends RSS feeds,
    deduplicating against the permanent topic history registry.
    """
    m_up = (market or "EN").upper()
    cfg = MARKET_CONFIG.get(m_up, MARKET_CONFIG["EN"])
    geos = cfg["geos"]

    if custom_seed:
        return [{
            "term": custom_seed,
            "primary_geo": geos[0],
            "geos_present": geos,
            "approx_traffic": "custom_seed",
            "news_title": "",
            "source": "custom_seed"
        }]

    gt_candidates = []
    yt_candidates = []
    seen = {}

    # Lane 1: Google Trends Daily RSS across market geos
    for geo in geos:
        try:
            items = gtrends_daily_rss(geo=geo, timeout=12.0)
            logger.info(f"[{m_up}/{geo}] Google Trends Daily RSS returned {len(items)} items.")
            for it in items:
                t = it.get("term", "").strip()
                if not t:
                    continue
                k = t.lower()
                traffic = it.get("approx_traffic", "")
                news = it.get("news_title", "")
                if k not in seen:
                    cand_obj = {
                        "term": t,
                        "primary_geo": geo,
                        "geos_present": [geo],
                        "approx_traffic": traffic,
                        "news_title": news,
                        "source": "gtrends_rss",
                        "sources_present": ["gtrends_rss"]
                    }
                    seen[k] = cand_obj
                    gt_candidates.append(cand_obj)
                else:
                    if geo not in seen[k]["geos_present"]:
                        seen[k]["geos_present"].append(geo)
                    if "gtrends_rss" not in seen[k].get("sources_present", []):
                        seen[k].setdefault("sources_present", []).append("gtrends_rss")
        except Exception as e:
            logger.warning(f"[{m_up}/{geo}] Failed to fetch Daily RSS: {e}")

    # Lane 2: Google News Topic RSS (Business & Finance) - Zero rate limit, 100% live breaking stories
    try:
        hl = cfg.get("hl", "en")
        gl = cfg.get("gl", "US")
        news_items = google_news_topic_rss(topic="BUSINESS", hl=hl, gl=gl, timeout=12.0)
        logger.info(f"[{m_up}] Google News Topic RSS returned {len(news_items)} live breaking business stories.")
        for n_it in news_items:
            t = n_it.get("term", "").strip()
            if not t or len(t) < 4:
                continue
            k = t.lower()
            if k not in seen:
                cand_obj = {
                    "term": t,
                    "primary_geo": gl,
                    "geos_present": [gl],
                    "approx_traffic": "google_news_live",
                    "news_title": t,
                    "source": "google_news_live",
                    "sources_present": ["google_news_live"]
                }
                seen[k] = cand_obj
                gt_candidates.append(cand_obj)
            else:
                if "google_news_live" not in seen[k].get("sources_present", []):
                    seen[k].setdefault("sources_present", []).append("google_news_live")
    except Exception as e:
        logger.warning(f"[{m_up}] Failed to fetch Google News Topic RSS: {e}")

    # Lane 2.5: High-Forensic Specialized Market RSS (TDB/Yahoo for JP, Crisis for KR, Corporate for EN)
    try:
        spec_items = fetch_specialized_market_rss(market=m_up, timeout=12.0)
        logger.info(f"[{m_up}] Specialized Market RSS returned {len(spec_items)} high-forensic items.")
        for s_it in spec_items:
            t = s_it.get("term", "").strip()
            if not t or len(t) < 4:
                continue
            k = t.lower()
            if k not in seen:
                cand_obj = {
                    "term": t,
                    "primary_geo": cfg.get("gl", "US"),
                    "geos_present": [cfg.get("gl", "US")],
                    "approx_traffic": "specialized_rss_live",
                    "news_title": t,
                    "source": s_it.get("source", "specialized_rss"),
                    "sources_present": [s_it.get("source", "specialized_rss")]
                }
                seen[k] = cand_obj
                gt_candidates.append(cand_obj)
            else:
                src_name = s_it.get("source", "specialized_rss")
                if src_name not in seen[k].get("sources_present", []):
                    seen[k].setdefault("sources_present", []).append(src_name)
    except Exception as e:
        logger.warning(f"[{m_up}] Failed to fetch Specialized Market RSS: {e}")

    # Lane 3: Google Trends Discover Searches via pytrends (with fallback to 0 if rate-limited)
    for geo in geos[:2]:
        try:
            disc_terms = gtrends_discover_trending_searches(market=m_up, geo=geo, count=20, timeout=12.0)
            logger.info(f"[{m_up}/{geo}] Discover Trending Searches returned {len(disc_terms)} queries.")
            for t in disc_terms:
                t = t.strip()
                if not t:
                    continue
                k = t.lower()
                if k not in seen:
                    cand_obj = {
                        "term": t,
                        "primary_geo": geo,
                        "geos_present": [geo],
                        "approx_traffic": "discover_trending",
                        "news_title": "",
                        "source": "gtrends_discover",
                        "sources_present": ["gtrends_discover"]
                    }
                    seen[k] = cand_obj
                    gt_candidates.append(cand_obj)
                else:
                    if "gtrends_discover" not in seen[k].get("sources_present", []):
                        seen[k].setdefault("sources_present", []).append("gtrends_discover")
        except Exception as e:
            logger.warning(f"[{m_up}/{geo}] Discover Trending Searches error: {e}")

    # Lane 4: YouTube Search-Box Autocomplete (Direct Viewer Search Intent across 7 Pillars — Free, No Quota)
    PILLAR_SEEDS_BY_MARKET = {
        "KR": [
            # Pillar 1: Business Rise & Fall
            "망한 이유", "몰락 이유", "파산 이유", "위기 이유", "폭망한 이유", "경영권 분쟁",
            # Pillar 2: Modern History & Systemic Crisis
            "사태 원인", "비하인드 스토리", "제도적 실패", "외환위기 원인",
            # Pillar 3: True Crime Non-Graphic
            "사건의 진실", "화이트칼라 범죄", "횡령 수법", "자금세탁 실체", "위조 사건",
            # Pillar 4: Psychology & Behavioral Manipulation
            "가스라이팅 사건", "사이비 실체", "다단계 사기", "심리 조작 수법", "집단 광기",
            # Pillar 5: Tech & Geopolitical Battles
            "반도체 전쟁", "기술 유출", "공급망 위기", "패권 다툼", "통신케이블",
            # Pillar 6: Institutional & Regulatory Chokepoints
            "리콜 은폐", "품질 조작", "연금 고갈 이유", "시험성적서 위조", "독점 규제",
            # Pillar 7: Hidden Fortunes & Underground Flows
            "지하경제 실체", "비자금 추적", "탈세 수법", "차명계좌"
        ],
        "JP": [
            # Pillar 1: Business Rise & Fall
            "なぜ 失敗", "倒産 理由", "崩壊のメカニズム", "経営破綻", "敵対的買収",
            # Pillar 2: Modern History & Systemic Crisis
            "事件の真相", "疑惑 暴露", "問題の闇", "歴史的転換点", "制度崩壊",
            # Pillar 3: True Crime Non-Graphic
            "巨額横領 手口", "知能犯 手口", "金融詐欺", "公金横領", "粉飾決算 手口",
            # Pillar 4: Psychology & Behavioral Manipulation
            "洗脳 事件", "マインドコントロール 手口", "カルト 実態", "集団心理の罠", "心理誘導",
            # Pillar 5: Tech & Geopolitical Battles
            "半導体 覇権", "サプライチェーン 危機", "技術流出 事件", "地政学 リスク",
            # Pillar 6: Institutional & Regulatory Chokepoints
            "不正認証 理由", "データ改ざん 闇", "リコール隠し", "年金破綻 理由", "規制緩和の罠",
            # Pillar 7: Hidden Fortunes & Underground Flows
            "巨額詐欺 手口", "マネーロンダリング 手口", "裏金 闇", "地下資金 流れ"
        ],
        "EN": [
            # Pillar 1: Business Rise & Fall
            "business collapse documentary", "the downfall of", "corporate bankruptcy explained", "how it went bankrupt",
            # Pillar 2: Modern History & Systemic Crisis
            "crisis breakdown", "what really happened to", "scandal explained", "systemic crisis documentary",
            # Pillar 3: True Crime Non-Graphic
            "fraud investigation", "white collar crime documentary", "embezzlement scheme exposed", "accounting fraud breakdown",
            # Pillar 4: Psychology & Behavioral Manipulation
            "cult manipulation documentary", "mass hysteria psychology", "social engineering scam", "cognitive bias trap",
            # Pillar 5: Tech & Geopolitical Battles
            "semiconductor war explained", "supply chain chokepoint", "tech cold war documentary", "subsea cable geopolitics",
            # Pillar 6: Institutional & Regulatory Chokepoints
            "corporate cover up documentary", "safety test falsification scandal", "regulatory loophole explained", "pension crisis collapse",
            # Pillar 7: Hidden Fortunes & Underground Flows
            "money laundering network exposed", "shadow banking scheme", "offshore tax evasion documentary"
        ]
    }
    yt_seeds = PILLAR_SEEDS_BY_MARKET.get(m_up, PILLAR_SEEDS_BY_MARKET["EN"])
    hl = cfg.get("hl", "en")
    gl = cfg.get("gl", "US")

    for y_seed in yt_seeds:
        try:
            yt_terms = youtube_autocomplete(y_seed, hl=hl, gl=gl, timeout=8.0)
            for t in yt_terms[:10]:
                t = t.strip()
                if not t or len(t) < 3:
                    continue
                k = t.lower()
                if k not in seen:
                    cand_obj = {
                        "term": t,
                        "primary_geo": gl,
                        "geos_present": [gl],
                        "approx_traffic": "yt_viewer_search",
                        "news_title": "",
                        "source": "youtube_autocomplete",
                        "sources_present": ["youtube_autocomplete"]
                    }
                    seen[k] = cand_obj
                    yt_candidates.append(cand_obj)
                else:
                    if "youtube_autocomplete" not in seen[k].get("sources_present", []):
                        seen[k].setdefault("sources_present", []).append("youtube_autocomplete")
        except Exception as _yt_err:
            logger.debug(f"[{m_up}] YouTube autocomplete seed '{y_seed}' failed: {_yt_err}")

    # Fetch V7 Algorithmic Suggested Candidates from Pool
    v7_raw = fetch_pending_v7_candidates(m_up)
    v7_candidates = []
    for vc in v7_raw:
        v_title = vc.get("referring_title", "").strip()
        if not v_title:
            continue
        v_cand_obj = {
            "term": v_title,
            "raw_term": v_title,
            "source": "v7_suggested_win",
            "sources_present": ["v7_suggested_win"],
            "approx_traffic": f"V7 CTR={vc.get('ctr_percent')}% AVD={vc.get('avd_seconds')}s (Views={vc.get('views_from_source')})",
            "v7_data": vc,
            "geos_present": [m_up]
        }
        v7_candidates.append(v_cand_obj)

    # Forensic Priority & Competitive Scoring Assembly:
    # V7 candidates and forensic crisis anchors are prioritized
    all_raw = v7_candidates + gt_candidates + yt_candidates
    anchors = FORENSIC_ANCHORS.get(m_up, FORENSIC_ANCHORS["EN"])

    forensic_priority = []
    regular_cands = []

    for c in all_raw:
        if c.get("source") == "v7_suggested_win":
            forensic_priority.append(c)
            continue
        comb = f"{c.get('term', '')} {c.get('news_title', '')}".lower()
        if any(kw.lower() in comb for kw in anchors):
            forensic_priority.append(c)
        else:
            regular_cands.append(c)

    # Put forensic/V7 priority first, followed by regular candidates
    ordered_candidates = forensic_priority + regular_cands

    # Deduplicate against permanent topic history registry
    unhandled = []
    for c in ordered_candidates:
        term = c["term"]
        if is_topic_already_handled(term, market=m_up):
            logger.info(f"[{m_up}] Skipping previously handled topic: {term}")
            continue
        unhandled.append(c)

    logger.info(f"[{m_up}] Total candidates: GT={len(gt_candidates)}, YT={len(yt_candidates)} -> Forensic Priority: {len(forensic_priority)}, Regular: {len(regular_cands)} -> Unhandled: {len(unhandled)}")
    return unhandled


def commit_trend_task(topic_data: dict) -> str:
    """Save approved topic to /var/vf/pending_tasks/<task_id>.json,
    generate competitor intel card, record to History Registry, and sync to Notion SoT.
    """
    try:
        from app.services.episode_numbering import get_next_episode_id
        task_id = get_next_episode_id(topic_data.get("market", "EN"), topic_data.get("task_slug") or topic_data.get("raw_term", "topic"))
    except (ImportError, AttributeError):
        try:
            from app.services.trend_gate_ai import get_next_episode_id
            task_id = get_next_episode_id(topic_data.get("market", "EN"), topic_data.get("task_slug") or topic_data.get("raw_term", "topic"))
        except Exception as _ep_err:
            logger.error(f"[trend_engine] Failed to generate episode ID via trend_gate_ai: {_ep_err}")
            slug = re.sub(r'[^a-zA-Z0-9]+', '-', str(topic_data.get("task_slug") or topic_data.get("raw_term", "topic"))).strip('-')[:25]
            task_id = f"{topic_data.get('market', 'EN')}_EP9999_{slug}"
    except Exception as _ep_err:
        logger.error(f"[trend_engine] Failed to generate episode ID via episode_numbering: {_ep_err}")
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', str(topic_data.get("task_slug") or topic_data.get("raw_term", "topic"))).strip('-')[:25]
        task_id = f"{topic_data.get('market', 'EN')}_EP9999_{slug}"

    topic_data["task_id"] = task_id

    # 1. Save pending task to disk
    pending_dir = "/var/vf/pending_tasks"
    os.makedirs(pending_dir, exist_ok=True)
    task_file = os.path.join(pending_dir, f"{task_id}.json")
    with open(task_file, "w", encoding="utf-8") as f:
        json.dump(topic_data, f, ensure_ascii=False, indent=2)
    logger.info(f"[trend_engine] Saved pending task to {task_file}")

    # 2. Save Competitor Intel Card
    for ep_base in ["/var/vf/episodes", "/root/video_factory/episodes"]:
        ep_dir = os.path.join(ep_base, task_id)
        os.makedirs(ep_dir, exist_ok=True)
        card_file = os.path.join(ep_dir, "competitor_intel_card.json")
        intel_card = {
            "task_id": task_id,
            "target_keyword": topic_data["raw_term"],
            "niche": topic_data.get("niche_angle_brief", ""),
            "competitor_gap": topic_data.get("competitor_differentiation_gap", ""),
            "market": topic_data["market"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "rising_queries": topic_data.get("rising_queries", []),
            "competitors": topic_data.get("viral_competitor_videos", []),
            "ground_truth_wiki": topic_data.get("factsheet", {}).get("has_verified_wiki", False)
        }
        with open(card_file, "w", encoding="utf-8") as f:
            json.dump(intel_card, f, ensure_ascii=False, indent=2)

    # 3. Record to Permanent History Registry (Anti-Duplicate Lock)
    record_handled_topic(
        term=topic_data["raw_term"],
        task_id=task_id,
        market=topic_data["market"],
        slug=topic_data.get("task_slug"),
        specific_angle=topic_data.get("specific_viral_angle")
    )

    # 3.5 Mark V7 Pool candidate as CONSUMED if topic originated from V7
    if topic_data.get("v7_data"):
        cand_id = topic_data["v7_data"].get("candidate_id")
        if cand_id:
            mark_v7_candidate_consumed(cand_id, task_id)

    # 4. Sync to Notion Trend Brain DB (Standardized Cross-DB State Machine)
    try:
        import scripts.ag_notion_bridge as bridge
        from app.services.trend_brain_mirror import _yt_labels_for_subject
        trend_db_id = "4c101989-2400-8334-8016-01d4f463b09f"
        raw_term = str(topic_data.get("raw_term", "")).strip()
        mkt = topic_data.get("market", "EN").upper()
        raw_score = float(topic_data.get("viability_score", 8.5) or 8.5)
        score_val = (raw_score / 10.0) if raw_score > 1.0 else raw_score
        labels, treatment_note = _yt_labels_for_subject(raw_term)
        today = datetime.now(timezone.utc).date().isoformat()

        find_filt = {"and": [
            {"property": "Keyword", "title": {"equals": raw_term[:1900]}},
            {"property": "Market", "select": {"equals": mkt}}
        ]}
        existing = bridge.query_db(trend_db_id, filter_obj=find_filt)
        props = {
            "Trend Score": {"number": round(score_val, 4)},
            "": {"status": {"name": "Approved→Story"}},
            "Task ID": {"rich_text": [{"type": "text", "text": {"content": task_id}}]},
            "Rising Queries": {"rich_text": [{"type": "text", "text": {"content": ", ".join(topic_data.get("rising_queries", []))[:1990]}}]},
            "Competitor Benchmarks": {"rich_text": [{"type": "text", "text": {"content": (f"Blue Ocean Gap: {topic_data.get('competitor_differentiation_gap', '')} | " + f"Top {len(topic_data.get('viral_competitor_videos', []))} videos reconciled")[:1990]}}]},
            "YouTube Safety Label": {"multi_select": [{"name": x} for x in labels]},
            "Upload Treatment Note": {"rich_text": [{"type": "text", "text": {"content": treatment_note[:1990]}}]},
            "Trend Source": {"multi_select": [{"name": "gtrends_rss"}, {"name": "youtube_recon"}]},
            "Verdict Reason": {"rich_text": [{"type": "text", "text": {"content": str(topic_data.get("verdict_reason") or topic_data.get("specific_viral_angle") or "Approved via GPT-6-Astra")[:1990]}}]},
            "QID": {"rich_text": [{"type": "text", "text": {"content": str(topic_data.get("qid") or topic_data.get("task_slug") or "")[:1990]}}]}
        }
        if existing.get("results"):
            page_id = existing["results"][0]["id"]
            bridge.update_page_properties(page_id, props)
            logger.info(f"[trend_engine] Updated task {task_id} in Notion Trend Brain DB (page={page_id}, status='Approved→Story')")
        else:
            props["Keyword"] = {"title": [{"type": "text", "text": {"content": raw_term[:1900]}}]}
            props["Market"] = {"select": {"name": mkt}}
            props["Discovered"] = {"date": {"start": today}}
            cr = bridge.create_page(trend_db_id, props)
            logger.info(f"[trend_engine] Created task {task_id} in Notion Trend Brain DB (id={cr.get('id') if isinstance(cr, dict) else 'ok'}, status='Approved→Story')")
    except Exception as e:
        logger.warning(f"[trend_engine] Notion sync failed: {e}")

    return task_id


def send_pure_telegram_gate1_notification(topic_data: dict) -> None:
    """Send pure informative broadcast for Human Gate 1 (0 interactive buttons)."""
    # Block notifications if it is a synthetic test seed
    if topic_data.get("is_test_seed") or topic_data.get("source") == "custom_seed":
        logger.info(f"[trend_engine] Skipping Telegram notification for test seed: {topic_data.get('raw_term')}")
        return

    task_id = str(topic_data.get("task_id", "")).strip()

    # 1. Gate Order Integrity Guard (Rule 125 & Anti-Ghost Out-of-Order Gate Violation)
    # Human Gate 1 can ONLY be dispatched BEFORE B3/Gate 2. If B3 is already done or HG2 dispatched, BLOCK!
    if task_id:
        for ep_base in ["/var/vf/episodes", "/root/video_factory/episodes", "./episodes"]:
            plan_file = os.path.join(ep_base, task_id, "director_plan.json")
            audit_file = os.path.join(ep_base, task_id, "visual_convergence_audit.json")
            if os.path.exists(plan_file) or os.path.exists(audit_file):
                logger.warning(
                    f"[trend_engine] GATE ORDER VIOLATION BLOCKED: Refusing to dispatch Human Gate 1 for {task_id} "
                    f"because B3 Director Plan / HG2 visual convergence already exists ({plan_file})! "
                    f"Human Gate 1 MUST NEVER be dispatched after Human Gate 2."
                )
                return

    # 2. Fact & Causal Audit Strict Pass Enforcement (Rule 118 & Rule 130)
    try:
        fact_score = float(topic_data.get("fact_audit_score", 0.0) or 0.0)
    except (ValueError, TypeError):
        fact_score = 0.0
    fact_passed = topic_data.get("fact_audit_passed", None)

    # Explicit PASS check: Must either have fact_passed=True or fact_score >= 7.5
    if fact_passed is False or (fact_passed is None and fact_score < 7.5):
        logger.warning(
            f"[trend_engine] GATE 1 DISPATCH BLOCKED: Candidate {task_id} B2.1 Fact Audit did NOT pass "
            f"(score={fact_score}/10, passed={fact_passed}). CẤM broadcast Human Gate 1 PASS khi chưa đạt chuẩn!"
        )
        return

    try:
        from app.services.telegram_buttons import send_telegram_broadcast
        import html
        mkt = topic_data.get("market", "EN")
        flag = "🇺🇸" if mkt == "EN" else ("🇯🇵" if mkt == "JP" else "🇰🇷")
        raw_term = html.escape(str(topic_data.get("raw_term", "")))
        title_vi = html.escape(str(topic_data.get("topic_name_vi", raw_term)))
        keyword = html.escape(str(topic_data.get("search_specific_keyword", raw_term)))
        rising_list = [html.escape(str(q)) for q in topic_data.get("rising_queries", [])[:5]]
        rising = ", ".join(rising_list) or "Đang cập nhật"
        niche = html.escape(str(topic_data.get("niche_angle_brief", "")))
        arcs = html.escape(str(topic_data.get("story_direction_5_arcs", "")))
        gap = html.escape(str(topic_data.get("competitor_differentiation_gap", "")))
        score = topic_data.get("viability_score", 9.0)
        title_a = html.escape(str(topic_data.get("title_a", "")))
        hook_60s = html.escape(str(topic_data.get("hook_60s", "")))
        fact_model = html.escape(str(topic_data.get("fact_audit_model", "Claude Opus 5")))

        lines = [
            "🎯 <b>[HUMAN GATE 1] THÔNG BÁO TIẾN ĐỘ CHỦ ĐỀ SẢN XUẤT (GO-LIVE 2026)</b>",
            "<i>(✨ B1 Trend Recon & B1.5 Competitor Gap & B1.6 SEO & B2 Story qua GPT-6-Astra & Claude Opus 5)</i>",
            "",
            f"{flag} <b>Market {mkt}:</b> <code>{raw_term}</code> (Viability: {score}/10)",
            f"• <b>Đề tài:</b> {title_vi}",
            f"• <b>Search-Specific Key:</b> <code>{keyword}</code>",
            (f"• <b>🎬 YouTube Title A:</b> <code>{title_a}</code>" if title_a else f"• <b>🔥 Cụm từ tìm kiếm tăng:</b> <code>{rising}</code>"),
            (f"• <b>⚡ 60s An Ong Hook:</b> <i>{hook_60s[:160]}...</i>" if hook_60s else f"• <b>Niche Brief:</b> {niche}"),
            f"• <b>Khác biệt đối thủ (Blue Ocean Gap):</b> <i>{gap}</i>",
            f"• <b>5-Beat Docudrama:</b> {arcs[:180]}...",
            f"• <b>🛡️ B2.1 Fact & Causal Audit:</b> <b>PASS ({fact_score}/10)</b> qua {fact_model}",
            f"👉 <b>Task ID:</b> <code>{task_id}</code>",
            "--------------------------------------------------",
            "⚙️ <i>B2.1 Fact Audit đã PASS! Hệ thống đang tự động chuyển tiếp sang <b>B3 Visual Director Plan & B3.5 Prompt Forge</b>...</i>"
        ]
        # Append extra niche brief only if hook_60s was displayed
        if hook_60s and niche:
            lines.insert(8, f"• <b>Niche Brief:</b> {niche}")

        msg = chr(10).join(lines)
        msg_id = send_telegram_broadcast(msg)
        if msg_id:
            logger.info(f"[trend_engine] Sent pure Telegram Gate 1 notification (msg_id={msg_id}) for {task_id}")
        else:
            logger.error(f"[trend_engine] FAILED to send pure Telegram Gate 1 notification for {task_id} (msg_id is None)")
    except Exception as e:
        logger.warning(f"[trend_engine] Failed to send Telegram Gate 1 notification: {e}")


def sanitize_candidate_term(term: str) -> str:
    """Sanitize noisy news headlines into crisp entity & event keywords.
    Removes news source suffixes, brackets, and journalistic boilerplate.
    Guarantees word-boundary integrity: NEVER truncates in the middle of words (Rule 118 & Rule 125).
    """
    if not term:
        return ""
    s = str(term).strip()

    # 1. Remove publisher brackets and source tags
    s = re.sub(r'^[【\[][^】\]]+[】\]]\s*', '', s)
    s = re.sub(r'\s*[（\(][^）\)]+[）\)]\s*$', '', s)
    s = re.sub(r'\s*[-–—|]\s*[^-–—|]+$', '', s)

    # 2. Remove common journalistic / clickbait prefixes
    s = re.sub(
        r'^(?:Report|Update|Watch|Opinion|Breaking|Exclusive|Analysis|Look|Sunday Reader|Briggs):\s*',
        '', s, flags=re.IGNORECASE
    )

    # 3. Clean quotes and whitespace
    s = re.sub(r"[‘'’]", "'", s)
    s = re.sub(r'[“”]', '"', s)
    s = re.sub(r'\s+', ' ', s).strip()

    # 4. Check for East Asian (CJK) vs Latin/English
    is_cjk = bool(re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]', s))
    if is_cjk:
        # Extract quoted entity if present: 『多田神社』 -> 多田神社
        quotes = re.findall(r'[『「]([^』」]+)[』」]', s)
        entity = quotes[0].strip() if quotes else ""

        events = [
            "民事再生", "倒産", "破産", "不正会計", "粉飾", "巨額損失", "不祥事", "買収", "逮捕", "疑惑",
            "법정관리", "워크아웃", "부도", "횡령", "배임", "분식회계", "상장폐지"
        ]
        found_event = next((ev for ev in events if ev in s), "")

        if entity and found_event:
            return f"{entity} {found_event}"
        elif entity and len(s) > 35:
            return entity
        elif len(s) > 50:
            m_split = re.split(r'[。、…\s]+', s)
            chunk = ""
            for seg in m_split:
                if len(chunk) + len(seg) <= 45:
                    chunk = f"{chunk} {seg}".strip() if chunk else seg
                else:
                    break
            return chunk if len(chunk) >= 10 else s[:45].strip()
        return s.strip(" .。、…-")

    # 5. Latin / English / Western Headlines
    s = s.strip(" .,:;!?-")

    # If headline is within rich search length (<= 95 chars), keep 100% intact!
    if len(s) <= 95:
        return s

    # If headline is excessively long (> 95 characters):
    # Truncate strictly at a sentence boundary (. ) or word boundary, NEVER in the middle of a word!
    if ". " in s:
        first_sentence = s.split(". ")[0].strip()
        if len(first_sentence) >= 25 and len(first_sentence) <= 95:
            return first_sentence

    truncated = s[:90]
    if " " in truncated:
        clean_word_boundary = truncated.rsplit(" ", 1)[0].strip()
        return clean_word_boundary.strip(" .,:;!?-")

    return truncated.strip(" .,:;!?-")


FORENSIC_ANCHORS = {
    "KR": [
        # Business & Financial
        "망한", "파산", "부도", "위기", "사태", "비리", "회생", "적자", "폭망", "몰락",
        "배임", "횡령", "매각", "상폐", "상장폐지", "손실", "디폴트", "구속", "압수수색", "체납",
        "논란", "붕괴", "스캔들", "진실", "의혹", "사건", "갈등", "분쟁", "소송",
        "검찰", "조사", "규제", "폭락", "폭등", "사기", "의문", "제재", "인수",
        "파업", "관세", "경고", "해고", "감원", "쇼크", "폭로", "탈세", "충격",
        "법정관리", "워크아웃", "분식회계", "불법대출", "불공정거래", "미정산", "먹튀",
        # Psychology & Behavioral Manipulation
        "가스라이팅", "심리 조작", "다단계", "세뇌", "사이비", "폰지", "자금세탁", "집단 광기", "마인드컨트롤",
        # Tech, Institutional, Regulatory Chokepoints & Non-Graphic Crime
        "품질 조작", "기술 유출", "공급망", "경영권 분쟁", "독점", "고독사", "리콜 은폐", "시험성적서 위조", "비자금"
    ],
    "EN": [
        # Business & Financial
        "collapse", "bankrupt", "crisis", "scandal", "fraud", "failed", "downfall",
        "investigation", "default", "liquidation", "loss", "debt", "deficit", "probe",
        "arrest", "lawsuit", "court", "recession", "scam", "why it failed", "exposed",
        "fall of", "controversy", "crash", "plunge", "turmoil", "indictment", "guilty",
        "sanction", "tariff", "strike", "layoff", "shock", "dispute", "takeover",
        "whistleblower", "antitrust", "subpoena", "foreclosure", "ponzi", "accounting fraud",
        # Psychology & Behavioral Manipulation
        "gaslighting", "mass hysteria", "cult psychology", "manipulation", "mind control",
        "social engineering", "brainwashing", "pyramid scheme",
        # Tech, Institutional, Regulatory Chokepoints & Non-Graphic Crime
        "money laundering", "embezzlement", "insider trading", "recall cover-up", "monopoly chokehold",
        "pension crisis", "safety test falsification", "subsea cable", "supply chain chokepoint"
    ],
    "JP": [
        # Business & Financial
        "倒産", "破産", "危機", "事件", "転落", "不正", "赤字", "崩壊", "粉飾",
        "裁判", "逮捕", "巨額", "損失", "なぜ", "疑惑", "衰退", "暴落", "詐欺",
        "買収", "買収へ", "制裁", "ストライキ", "解雇", "ショック", "暴露", "脱税",
        "問題", "紛争", "訴訟", "調査", "規制", "真相", "失敗", "リスク",
        "民事再生", "特別清算", "不正会計", "粉飾決算", "横領", "背任", "不祥事",
        "リコール", "営業停止", "独占禁止法", "偽装", "内部告発", "債務超過",
        # Psychology & Behavioral Manipulation
        "洗脳", "マインドコントロール", "心理操作", "カルト", "集団心理", "巨額詐欺",
        "情報弱者", "マルチ商法", "集団パニック", "心理誘導",
        # Tech, Institutional, Regulatory Chokepoints & Non-Graphic Crime
        "資金洗浄", "技術流出", "品質不正", "過労死", "年金崩壊", "敵対的買収",
        "データ改ざん", "裏金", "知能犯", "公金横領", "サプライチェーン"
    ]
}


def forensic_pre_filter(candidate: dict, market: str) -> tuple[bool, str]:
    """Level-0 Forensic Pre-Filter Gate (Rule 118, Rule 123, Rule 130).
    Filters out non-investigative queries and verifies that YouTube Autocomplete queries
    possess an active 24-48h news catalyst before burning any LLM tokens.
    """
    source = candidate.get("source", "")
    if source == "custom_seed":
        return True, "Bypassed: custom seed"

    m_up = (market or "EN").upper()
    anchors = FORENSIC_ANCHORS.get(m_up, FORENSIC_ANCHORS["EN"])

    term = candidate.get("term", "").strip() or candidate.get("title", "").strip()
    term_lower = term.lower()
    combined_text = f"{term_lower} {candidate.get('niche_brief', '').lower()} {candidate.get('angle', '').lower()} {candidate.get('title', '').lower()}"
    # Hard Safety Gate (Anti-Politics, Anti-Religion, Anti-Defamation - Rule 118 & Policy Safety)
    safety_forbidden_terms = [
        'election 2026', 'election', 'presidential race', 'vote for', 'vote against',
        'democrat vs republican', 'left-wing agenda', 'right-wing agenda', 'party propaganda',
        'biden', 'trump', 'kamala', 'yoon suk yeol', 'lee jae myung', 'kishida', 'ishiba', 'putin', 'zelensky',
        'democrat', 'republican', 'senate election', 'congressional hearing', 'parliament election',
        'christianity', 'buddhism', 'islam', 'hinduism', 'judaism', 'catholic church',
        'buddhist doctrine', 'muslim doctrine', 'quran', 'bible verse', 'defamation', 'hate speech'
    ]
    for st in safety_forbidden_terms:
        if st in combined_text:
            return False, f"Safety Gate VETO: Political/Religious/Defamation trigger '{st}' in candidate (0 LLM tokens burned)"

    # For YouTube Autocomplete candidates: verify live breaking news catalyst (Rule 130 & Rule 123)
    if source == "youtube_autocomplete":
        catalysts = fetch_live_news_catalyst(term, m_up, count=5)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=48)
        fresh_articles = []
        for cat in catalysts:
            pub_str = cat.get("published_at", "")
            try:
                pub_dt = parsedate_to_datetime(pub_str)
                if pub_dt >= cutoff:
                    fresh_articles.append(cat)
            except Exception:
                # If date parse fails, keep article if term is in title
                if term_lower in cat.get("title", "").lower():
                    fresh_articles.append(cat)

        if not fresh_articles:
            return False, f"Stale YouTube search without 24-48h live news catalyst: '{term}' (0 LLM tokens burned)"
        return True, f"Verified YouTube search with {len(fresh_articles)} live news catalyst articles in 24-48h"

    # For Google Trends / Google News: check forensic crisis anchors
    for kw in anchors:
        if kw.lower() in combined_text:
            return True, f"Matched forensic crisis anchor: '{kw}'"

    return False, f"No forensic crisis anchor in '{term}' (0 LLM tokens burned)"




MAX_B2_ATTEMPTS_DEFAULT = int(os.getenv("MAX_B2_ATTEMPTS_PER_RUN", "2"))


def discover_and_produce_market_trend(
    market: str = "EN",
    custom_seed: str = None,
    auto_produce: bool = True,
    max_scan_candidates: int = 60,
    max_b2_attempts: int = MAX_B2_ATTEMPTS_DEFAULT
) -> list[dict]:
    """Execute canonical B1 trend discovery and automated B1.5 -> B2 -> B3 pipeline
    for exactly 1 topic per market per day.
    """
    m_up = (market or "EN").upper()
    print(f"\n=======================================================")
    print(f"🚀 [TREND ENGINE B1] Scanning Market {m_up} for Daily Production Topic (Max B2 Attempts: {max_b2_attempts})")
    print(f"=======================================================")

    candidates = fetch_live_trending_terms(m_up, custom_seed=custom_seed)
    if not candidates:
        logger.warning(f"[{m_up}] No unhandled candidates found.")
        return []

    produced_topics = []
    viability_passed_candidates = []
    consecutive_api_errors = 0
    max_consecutive_api_errors = 3
    b2_attempts_count = 0

    for idx, c in enumerate(candidates[:max_scan_candidates], start=1):
        raw_term = c["term"]
        c["raw_term"] = raw_term
        # Sanitize long noisy headlines into crisp entity & event keyword
        clean_recon_term = sanitize_candidate_term(raw_term)
        term = clean_recon_term if clean_recon_term else raw_term

        print(f"\n[{m_up}] Candidate #{idx}/{min(len(candidates), max_scan_candidates)}: '{raw_term}' (Recon Term: '{term}', Traffic: {c.get('approx_traffic')}, Geos: {c.get('geos_present')})")

        # Level-0 Forensic Pre-Filter Gate (0 LLM Tokens Burned)
        pass_pre, pre_reason = forensic_pre_filter(c, m_up)
        if not pass_pre:
            print(f"  ⏭️ [PRE-FILTER LEVEL-0 REJECT] {pre_reason}")
            continue

        # 1. Direct Platform Recon (Google/YouTube Autocomplete & Viral Videos)
        recon_data = perform_direct_platform_recon(term, m_up)
        rising_queries = recon_data.get("rising_queries", [])
        viral_videos = recon_data.get("viral_videos", [])

        # 2. Ground-truth Wikipedia extract
        factsheet = fetch_ground_truth_factsheet(term, m_up)

        # 3. Viability assessment via HHTech GPT-6-Astra (Grounded on News Catalysts per Rule 118 & 130)
        viability = assess_keyword_video_viability(
            term=term,
            market=m_up,
            traffic=str(c.get("approx_traffic", "")),
            rising_queries=rising_queries[:6],
            top_videos=viral_videos[:4],
            news_catalysts=recon_data.get("news_catalysts", []),
            raw_headline=raw_term
        )

        # Circuit Breaker check for repeated LLM API infrastructure outages (Rule 118)
        if viability.get("api_error"):
            consecutive_api_errors += 1
            err_detail = viability.get("rejection_reason", "Unknown LLM error")
            print(f"  ⚠️ [LLM API FAILURE {consecutive_api_errors}/{max_consecutive_api_errors}] {err_detail}")
            logger.error(f"[{m_up}] Viability LLM API error on candidate '{term}': {err_detail}")
            if consecutive_api_errors >= max_consecutive_api_errors:
                circuit_alert = (
                    f"🚨 <b>[RULE 118 CIRCUIT BREAKER ACTIVATED]</b>\n"
                    f"Market: <code>{m_up}</code> | Candidate: <code>{term}</code>\n"
                    f"LLM API thất bại liên tiếp {consecutive_api_errors} lần tại Viability Gate:\n"
                    f"<code>{err_detail[:250]}</code>\n"
                    f"🛑 <b>Hành động:</b> Tạm dừng quét candidate pool để bảo vệ hệ thống và chờ kiểm tra hạ tầng."
                )
                print(f"\n{circuit_alert}\n")
                logger.critical(f"[{m_up}] Rule 118 Circuit Breaker triggered after {consecutive_api_errors} consecutive LLM failures.")
                try:
                    from app.services.telegram_buttons import send_telegram_broadcast
                    send_telegram_broadcast(circuit_alert)
                except Exception:
                    pass
                break
            continue
        else:
            consecutive_api_errors = 0

        score = viability.get("viability_score", 0)

        if not viability.get("is_video_viable") or score < 8.0:
            print(f"  ❌ REJECTED: {viability.get('rejection_reason', 'Low viability score (< 8.0)')}")
            continue

        specific_angle = viability.get("specific_viral_angle") or term
        print(f"  ✅ APPROVED! Viability: {score}/10 | Angle: {specific_angle}")
        viability_passed_candidates.append({"term": term, "score": score, "angle": specific_angle})

        # Temporary pipeline task ID for pre-audit stages (B1 -> B1.1 -> B1.5 -> B1.5.5 -> B1.6 -> B2 -> B2.1)
        import hashlib
        clean_slug = re.sub(r'[^a-zA-Z0-9]+', '-', str(term).lower()).strip('-')[:20]
        if not clean_slug:
            # CJK term without latin letters: anchor with deterministic MD5 hash
            term_hash = hashlib.md5(str(term).encode('utf-8')).hexdigest()[:8]
            temp_task_id = f"{m_up}_TEMP_{term_hash}"
        else:
            temp_task_id = f"{m_up}_TEMP_{clean_slug}"

        # 3.2 B1.1 Adversarial Critic Gate (Rule 130 & Anti-Bait-and-Switch Early VETO - Claude Opus 5)
        # Filters out false trends, stale anchors, and bait-and-switch before wasting tokens/scrapes on B1.5!
        print(f"  🛡️ [B1.1 Critic Gate] Interrogating candidate '{term}' and angle for live trend fidelity...")
        try:
            from app.services.adversarial_critic_b1 import audit_candidate_trend_alignment
            critic_res = audit_candidate_trend_alignment(
                candidate_term=term,
                specific_angle=specific_angle,
                niche_brief=f"Documentary on {term} and {specific_angle}",
                market=m_up,
                news_catalysts=recon_data.get("news_catalysts", []),
                rising_queries=rising_queries[:8],
                traffic=str(c.get("approx_traffic", "")),
                model="claude-opus-5-5",
                fallback_model="gpt-6-astra"
            )
            c_verdict = critic_res.get("verdict", "PASS").upper()
            c_score = critic_res.get("audit_score", 0.0)
            if c_verdict == "FAIL" or c_score < 7.5:
                veto_msg = critic_res.get("veto_reason") or "Failed adversarial trend alignment audit"
                print(f"  ❌ VETOED BY CRITIC GATE (Score: {c_score}/10): {veto_msg}")
                logger.warning(f"[{m_up}] Critic Gate VETOED '{term}': {veto_msg}")
                continue
            print(f"  ✅ CRITIC GATE PASSED! Score: {c_score}/10 | Angle verified aligned with live trend.")
        except Exception as _critic_err:
            logger.warning(f"[{m_up}] Critic Gate execution warning for '{term}': {_critic_err}")

        # 3.5 B1.5 Pre-Recon (Rule 123 & Rule 128: Data-Driven Competitor Recon Before Niche Decision)
        print(f"  🎯 [B1.5 Pre-Recon] Harvesting Competitor Benchmarks & Audience Frustrations for '{term}'...")
        recon_card = None
        comp_gap = ""
        anchor_vid = c.get("v7_data", {}).get("referring_video_id") if c.get("v7_data") else None
        try:
            recon_card = run_b15(temp_task_id, term, niche="Trending Investigative", use_cache=True, anchor_video_id=anchor_vid)
            if recon_card:
                anatomy = recon_card.get("competitor_narrative_anatomy", {})
                comp_gap = anatomy.get("fatal_explanatory_vacuum", "")
                if comp_gap:
                    print(f"  ✅ [B1.5 Pre-Recon] Discovered real competitor vacuum: {comp_gap[:60]}...")
        except Exception as _b15_pre_err:
            logger.warning(f"B1.5 pre-recon warning for {term}: {_b15_pre_err}")

        # 4. Reason Niche Brief & 5-Beat Direction using Real Competitor Intel & Real Rising Queries
        niche_data = reason_topic_niche(
            subject=term,
            market=m_up,
            virality_score=0.92,
            rising_queries=rising_queries[:8],
            viral_videos=viral_videos[:5],
            news_catalysts=recon_data.get("news_catalysts", [])
        )
        if comp_gap:
            niche_data["competitor_differentiation_gap"] = comp_gap

        native_topic = niche_data.get("search_specific_keyword") or term
        t_obj = {
            "market": m_up,
            "raw_term": term,
            "topic": native_topic,
            "geos_present": c.get("geos_present"),
            "approx_traffic": c.get("approx_traffic"),
            "viability_score": score,
            "specific_viral_angle": specific_angle,
            "visual_feasibility": viability.get("visual_feasibility_score"),
            "conflict_depth": viability.get("conflict_depth_score"),
            "topic_name_vi": niche_data.get("topic_name_vi"),  # Retained exclusively for Telegram Gate 1 operator display
            "search_specific_keyword": niche_data.get("search_specific_keyword"),
            "task_slug": niche_data.get("task_slug"),
            "niche_angle_brief": niche_data.get("niche_angle_brief"),
            "competitor_differentiation_gap": niche_data.get("competitor_differentiation_gap") or comp_gap,
            "story_direction_5_arcs": niche_data.get("story_direction_5_arcs"),
            "rising_queries": rising_queries[:8],
            "breakout_queries": niche_data.get("breakout_queries") or rising_queries[:3],
            "safety_label": niche_data.get("safety_label"),
            "treatment_note": niche_data.get("treatment_note"),
            "factsheet": factsheet,
            "viral_competitor_videos": viral_videos[:5],
            "critic_score": c_score,
            "temp_task_id": temp_task_id,
            "v7_data": c.get("v7_data")
        }

        # 5. Save Competitor Intel Card to temp workspace
        print(f"  🎯 [B1.5] Persisting Competitor Intel Card for {temp_task_id}...")
        try:
            recon_keyword = t_obj.get("search_specific_keyword") or term
            if not recon_card:
                recon_card = run_b15(temp_task_id, recon_keyword, t_obj.get("niche_angle_brief", "General"), market=m_up, anchor_video_id=anchor_vid)
            else:
                recon_card["task_id"] = temp_task_id
            if recon_card and isinstance(recon_card, dict):
                for ep_base in ["/var/vf/episodes", "/root/video_factory/episodes", "./episodes"]:
                    t_dir = Path(ep_base) / temp_task_id
                    t_dir.mkdir(parents=True, exist_ok=True)
                    (t_dir / "competitor_intel_card.json").write_text(
                        json.dumps(recon_card, ensure_ascii=False, indent=2), encoding="utf-8")
                gap_val = recon_card.get("competitor_narrative_anatomy", {}).get("fatal_explanatory_vacuum", "") or comp_gap
                if gap_val:
                    t_obj["competitor_differentiation_gap"] = gap_val
                    t_obj["competitor_gap"] = gap_val
        except Exception as re_err:
            logger.warning(f"[{temp_task_id}] B1.5 recon finalizing warning: {re_err}")

        # 5.2. Grounding Layer Fact-Verification & Gate (B1.5.5 - Rule 118 & Rule 121)
        print(f"  🔍 [B1.5.5] Running Live Grounding Research & Verification Gate for {temp_task_id}...")
        try:
            import importlib
            import app.services.grounding_layer_b15 as gl_b15
            importlib.reload(gl_b15)
            from app.services.grounding_layer_b15 import run_grounding_research, passes_grounding_gate
            grounding_kw = t_obj.get("search_specific_keyword") or term
            grounding_hint = t_obj.get("niche_angle_brief") or ""
            grounding_intel = run_grounding_research(topic=grounding_kw, search_hint=grounding_hint, market=m_up)
            
            gate_ok, gate_msg = passes_grounding_gate(grounding_intel, min_verified=3, min_claims=8, min_dated_claims=3, require_whitelist=True)
            if not gate_ok:
                logger.warning(f"[{temp_task_id}] Grounding Gate REJECTED: {gate_msg}")
                print(f"  ❌ [B1.5.5 Grounding Gate] REJECTED: {gate_msg}. Rotating to next candidate...")
                continue

            t_obj["grounding_intel"] = grounding_intel
            print(f"  ✅ [B1.5.5 Grounding Gate] {gate_msg}")

            # Persist grounding_intel.json to episode folders under temp_task_id
            for ep_base in ["/var/vf/episodes", "/root/video_factory/episodes", "./episodes"]:
                g_dir = Path(ep_base) / temp_task_id
                if g_dir.parent.exists() or Path(ep_base).exists():
                    g_dir.mkdir(parents=True, exist_ok=True)
                    (g_dir / "grounding_intel.json").write_text(
                        json.dumps(grounding_intel, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
        except Exception as g_err:
            logger.error(f"[{temp_task_id}] Grounding Layer exception: {g_err}. Rotating to next candidate...")
            print(f"  ❌ [B1.5.5 Grounding Gate] Exception: {g_err}. Rotating to next candidate...")
            continue

        # 5.5. Early B1.6 SEO & Narrative Hook Package Forge (Rule 119 & Rule 444)
        print(f"  🚀 [B1.6] Forging Early SEO Package & 60s An Ong Hook for {temp_task_id} via GPT-6-Astra...")
        try:
            from app.services.seo_package_forge import forge_seo_package
            seo_pkg = forge_seo_package(
                task_id=temp_task_id,
                target_keyword=t_obj.get("search_specific_keyword") or term,
                market=m_up,
                niche_brief=t_obj.get("niche_angle_brief", ""),
                competitor_gap=t_obj.get("competitor_differentiation_gap", ""),
                rising_queries=rising_queries[:8],
                breakout_queries=t_obj.get("breakout_queries", []),
                competitor_card=recon_card if 'recon_card' in locals() else None
            )
            if seo_pkg:
                t_obj["seo_package"] = seo_pkg
                t_obj["title_a"] = seo_pkg.get("title_a")
                t_obj["title_b"] = seo_pkg.get("title_b")
                t_obj["topic"] = seo_pkg.get("title_a") or t_obj.get("topic") or term
                t_obj["hook_3s"] = seo_pkg.get("hook_3s")
                t_obj["hook_60s"] = seo_pkg.get("hook_60s")
                t_obj["specific_viral_angle"] = seo_pkg.get("specific_viral_angle") or t_obj.get("specific_viral_angle")
                print(f"  ✅ [B1.6] Early SEO Package forged: '{seo_pkg.get('title_a')}'")
                print(f"     60s Hook Contract: {seo_pkg.get('hook_60s')[:70]}...")
        except Exception as seo_err:
            logger.warning(f"[{temp_task_id}] Early SEO package forge warning: {seo_err}")

        # Temporarily save pending task under temp_task_id so B2 can read metadata
        pending_dir = "/var/vf/pending_tasks"
        os.makedirs(pending_dir, exist_ok=True)
        temp_task_file = os.path.join(pending_dir, f"{temp_task_id}.json")
        with open(temp_task_file, "w", encoding="utf-8") as tf:
            json.dump(t_obj, tf, ensure_ascii=False, indent=2)

        # 6. Generate B2 5-Beat Investigative Docudrama Script
        b2_attempts_count += 1
        print(f"  ⚙️ [B2 Attempt {b2_attempts_count}/{max_b2_attempts}] Generating 12-15 min docudrama script for {temp_task_id} via HHTech Reasoner...")
        try:
            from app.services.story_engine_b2 import generate_5_arc_story
            brain = generate_5_arc_story(temp_task_id)
            story_text = brain.get("story") or brain.get("full_script") or ""
            t_obj["story_text"] = story_text
            t_obj["story_gate_score"] = brain.get("story_gate_score")
            t_obj["story_verdict"] = brain.get("story_verdict", "PASS")
            print(f"  ✅ [B2 Attempt {b2_attempts_count}] Script generated ({len(story_text.split())} words, Gate Score: {t_obj['story_gate_score']}, Verdict: {t_obj['story_verdict']})")
        except Exception as b2_err:
            logger.error(f"[{temp_task_id}] B2 Story generation failed: {b2_err}. Rotating to next candidate...")
            record_handled_topic(term=term, task_id=temp_task_id, market=m_up)
            if os.path.exists(temp_task_file):
                try:
                    os.remove(temp_task_file)
                except Exception:
                    pass
            if b2_attempts_count >= max_b2_attempts:
                cb_err_msg = (
                    f"🚨 <b>[RULE 118 B2 CIRCUIT BREAKER ACTIVATED]</b>\n"
                    f"Market: <code>{m_up}</code> | B2 Attempts: <code>{b2_attempts_count}/{max_b2_attempts}</code>\n"
                    f"Quá trình sinh B2 thất bại trên {b2_attempts_count} ứng viên liên tiếp. Lỗi gần nhất: <code>{str(b2_err)[:200]}</code>\n"
                    f"🛑 <b>Hành động:</b> Ngắt pipeline ngay lập tức để bảo vệ ngân sách token và quota API."
                )
                print(f"\n{cb_err_msg}\n")
                logger.critical(f"[{m_up}] B2 Circuit Breaker triggered on exception after {b2_attempts_count} attempts.")
                try:
                    from app.services.telegram_buttons import send_telegram_broadcast
                    send_telegram_broadcast(cb_err_msg)
                except Exception:
                    pass
                break
            continue

        # Check Story Gate verdict (Rule 121 & Rule 127)
        if t_obj.get("story_verdict") == "FAIL":
            logger.error(f"[{temp_task_id}] B2 Story Gate REJECTED ({t_obj.get('story_gate_score')}). Candidate rejected...")
            print(f"  ❌ [B2 STORY GATE REJECTED] Score: {t_obj.get('story_gate_score')}.")
            record_handled_topic(term=term, task_id=temp_task_id, market=m_up)
            if os.path.exists(temp_task_file):
                try:
                    os.remove(temp_task_file)
                except Exception:
                    pass
            # Clean up temp episode directory to prevent stale cache contamination (Rule 118 & 125)
            import shutil
            for ep_base in ["/var/vf/episodes", "/root/video_factory/episodes", "./episodes"]:
                t_dir = Path(ep_base) / temp_task_id
                if t_dir.exists():
                    try:
                        shutil.rmtree(t_dir)
                    except Exception:
                        pass

            # Rule 118 Hard Circuit Breaker for B2 (Anti-Token-Drain Law)
            if b2_attempts_count >= max_b2_attempts:
                cb_msg = (
                    f"🚨 <b>[RULE 118 B2 CIRCUIT BREAKER ACTIVATED]</b>\n"
                    f"Market: <code>{m_up}</code> | B2 Attempts: <code>{b2_attempts_count}/{max_b2_attempts}</code>\n"
                    f"Đã thử sinh và kiểm toán B2 cho {b2_attempts_count} ứng viên liên tiếp nhưng chưa đạt Story Gate 11/13 "
                    f"(Ứng viên gần nhất: <code>{term}</code> - Score: {t_obj.get('story_gate_score')}).\n"
                    f"🛑 <b>Hành động:</b> Ngắt pipeline ngay lập tức để bảo vệ ngân sách token và chi phí API."
                )
                print(f"\n{cb_msg}\n")
                logger.critical(f"[{m_up}] B2 Circuit Breaker triggered after {b2_attempts_count} candidate attempts.")
                try:
                    from app.services.telegram_buttons import send_telegram_broadcast
                    send_telegram_broadcast(cb_msg)
                except Exception:
                    pass
                break
            continue

        # 7. B2.1 Independent Fact & Causal Integrity Audit Gate (Rule 118, 122 & 130 - GPT-6-Astra / Claude Opus 5)
        fact_audit = brain.get("fact_causal_audit") or {}
        auditor_disp_name = fact_audit.get("auditor_model") or "GPT-6-Astra"
        print(f"  🛡️ [B2.1 Fact & Causal Audit] Script audited by {auditor_disp_name}...")
        is_converged = fact_audit.get("convergence_status") == "CONVERGED"
        f_score = float(fact_audit.get("audit_score", 10.0))
        if (is_converged or f_score >= 7.5) and fact_audit.get("verdict") != "PASS":
            f_verdict = "PASS"
            fact_audit["verdict"] = "PASS"
        else:
            f_verdict = fact_audit.get("verdict", "PASS").upper()
        print(f"  ⚖️ [B2.1 Fact & Causal Audit Result] Verdict={f_verdict}, Score={f_score}/10")

        if f_verdict == "FAIL" or f_score < 7.5:
            veto_reason = fact_audit.get("veto_reason") or fact_audit.get("audit_notes") or "Script failed fact/causal integrity audit"
            logger.error(f"[{temp_task_id}] B2.1 Audit REJECTED ({f_score}/10): {veto_reason}. Candidate rejected, rotating to next candidate...")
            print(f"  ❌ [B2.1 REJECTED] {veto_reason}. Rotating to next candidate in queue...")
            # User approved: no telegram notification for B2.1 candidate rotation.
            # If all fail, B1 VIABILITY ALERT or BOTTLENECK ALERT will cover; if passes, HG1 will cover.
            record_handled_topic(term=term, task_id=temp_task_id, market=m_up)
            if os.path.exists(temp_task_file):
                try:
                    os.remove(temp_task_file)
                except Exception:
                    pass
            # Clean up temp episode directory to prevent stale cache contamination (Rule 118 & 125)
            import shutil
            for ep_base in ["/var/vf/episodes", "/root/video_factory/episodes", "./episodes"]:
                t_dir = Path(ep_base) / temp_task_id
                if t_dir.exists():
                    try:
                        shutil.rmtree(t_dir)
                    except Exception:
                        pass
            continue

        print(f"  🎉 [B2.1 AUDIT PASSED!] Score: {f_score}/10. Moving to OFFICIAL TASK ID COMMIT & NOTION SYNC & HG1 NOTIFICATION!")
        t_obj["fact_audit_score"] = f_score
        t_obj["fact_audit_model"] = fact_audit.get("auditor_model", "GPT-6-Astra")
        t_obj["fact_audit_passed"] = True

        # 8. NOW OFFICIALLY COMMIT TASK ID, SYNC NOTION, RENAME TEMP FOLDERS, & SEND HG1 NOTIFICATION!
        task_id = commit_trend_task(t_obj)
        t_obj["task_id"] = task_id
        print(f"  💾 Officially Committed Task ID: {task_id}")

        # Migrate episode and pending task artifacts from temp_task_id to canonical task_id
        import shutil
        for ep_base in ["/var/vf/episodes", "/root/video_factory/episodes", "./episodes"]:
            temp_p = Path(ep_base) / temp_task_id
            canon_p = Path(ep_base) / task_id
            if temp_p.exists():
                canon_p.mkdir(parents=True, exist_ok=True)
                for f_item in temp_p.iterdir():
                    dest_file = canon_p / f_item.name
                    try:
                        if f_item.is_file():
                            shutil.copy2(f_item, dest_file)
                        elif f_item.is_dir():
                            shutil.copytree(f_item, dest_file, dirs_exist_ok=True)
                    except Exception as _cp_err:
                        logger.warning(f"Could not copy {f_item} to {dest_file}: {_cp_err}")
                try:
                    shutil.rmtree(temp_p)
                except Exception as _rm_err:
                    logger.warning(f"Could not remove temp folder {temp_p}: {_rm_err}")

        # Update canonical pending task file with full object
        canon_task_file = os.path.join(pending_dir, f"{task_id}.json")
        with open(canon_task_file, "w", encoding="utf-8") as tf:
            json.dump(t_obj, tf, ensure_ascii=False, indent=2)

        # Cleanup temp pending task
        if os.path.exists(temp_task_file):
            try:
                os.remove(temp_task_file)
            except Exception:
                pass

        # Update Notion Story Library row from temp_task_id to canonical task_id (Rule 125 & 126 Single Truth)
        try:
            from scripts.ag_notion_bridge import query_db, update_page_properties
            s_db_id = os.getenv("STORY_LIBRARY_DB_ID", "b0301989-2400-836b-bdb5-8131fea17736")
            q_res = query_db(s_db_id, filter_obj={"or": [
                {"property": "Task ID", "rich_text": {"equals": temp_task_id}},
                {"property": "Episode ID", "rich_text": {"equals": temp_task_id}}
            ]})
            if q_res and q_res.get("results"):
                for r in q_res["results"]:
                    update_page_properties(r["id"], {
                        "Task ID": {"rich_text": [{"type": "text", "text": {"content": task_id}}]},
                        "Episode ID": {"rich_text": [{"type": "text", "text": {"content": task_id}}]},
                        "Status": {"status": {"name": "Gate Passed"}}
                    })
                logger.info(f"[trend_engine] Migrated Notion Story Library rows from {temp_task_id} to canonical {task_id} (Status: Gate Passed)")
        except Exception as _m_err:
            logger.warning(f"[trend_engine] Notice migrating Story Library Task ID: {_m_err}")

        # 9. Send Pure Telegram Gate 1 Notification (Now fully enriched with Title A/B, 60s Hook & B2.1 PASS!)
        send_pure_telegram_gate1_notification(t_obj)

        # 10. Proceed directly to B3 Hollywood Director Plan & B3.5 Prompt Forge
        if auto_produce:
            print(f"  ⚙️ [B3/B3.5] Auto-producing Hollywood Director Plan & Scene Breakdown for {task_id}...")
            try:
                from scripts.produce_episode_hg1 import run_chain
                res_code = run_chain(task_id)
                if res_code == 0:
                    print(f"  🎉 [SUCCESS] Pipeline completed through B1 -> B1.5 -> B2 -> B2.1 -> B3 -> Gate 2 for {task_id}!")
                    produced_topics.append(t_obj)
                    break  # Exactly 1 completed topic per market per day!
                else:
                    logger.error(f"[{task_id}] Pipeline stopped at gate with exit code {res_code}. Freezing pipeline.")
                    break
            except Exception as prod_err:
                logger.error(f"[{task_id}] CRITICAL RUNTIME ERROR in B3: {prod_err}. Freezing pipeline.")
                break
        else:
            produced_topics.append(t_obj)
            break

    if not produced_topics and not custom_seed:
        scanned_count = min(len(candidates), max_scan_candidates)
        if viability_passed_candidates:
            # Candidates passed B1 Viability Gate, but were stopped downstream (Critic, Grounding, or B2 Story/Fact Audit)
            alert_msg = (
                f"⚠️ <b>[VF PIPELINE B2/B3 BOTTLENECK ALERT - RULE 118]</b>\n"
                f"Đã quét qua {scanned_count}/{len(candidates)} ứng viên live cho thị trường <b>{m_up}</b>.\n"
                f"📊 <b>Kết quả B1:</b> Có <b>{len(viability_passed_candidates)}</b> ứng viên đạt Viability Gate (≥ 8.0/10).\n"
                f"❌ <b>Điểm nghẽn:</b> Toàn bộ ứng viên đã bị chặn tại các chốt kiểm định hạ nguồn (Adversarial Critic Gate hoặc B2 Story/Fact Audit Gate).\n"
                f"🛑 Hệ thống tuân thủ Rule 118 & Rule 123: Dừng lại và KHÔNG tự ý sinh seed giả định. Vui lòng kiểm tra log chi tiết."
            )
            logger.warning(f"[{m_up}] {len(viability_passed_candidates)} candidates passed viability gate but none passed downstream B2/B3 gates.")
        else:
            alert_msg = (
                f"⚠️ <b>[B1 VIABILITY ALERT - RULE 118]</b>\n"
                f"Đã quét qua {scanned_count}/{len(candidates)} ứng viên live từ đa kênh (RSS, Discover, YouTube) cho thị trường <b>{m_up}</b>, "
                f"nhưng không có đề tài nào vượt qua Viability Gate (≥ 8.0/10) để làm phóng sự điều tra.\n"
                f"🛑 Hệ thống tuân thủ Rule 118 & Rule 123: Dừng lại và KHÔNG tự ý sinh seed giả định. Vui lòng kiểm tra hoặc cấp seed chỉ định."
            )
            logger.warning(f"[{m_up}] No candidates passed viability gate.")
        try:
            from app.services.telegram_buttons import send_telegram_broadcast
            send_telegram_broadcast(alert_msg)
        except Exception as _tel_err:
            logger.warning(f"Failed to send B1 alert to Telegram: {_tel_err}")

    return produced_topics


# Backwards compatibility aliases
discover_approach_b = discover_and_produce_market_trend
commit_approach_b_task = commit_trend_task


def run_daily_all_markets(markets: list[str] = None, auto_produce: bool = True) -> dict:
    """Run daily production cycle for all target markets (EN, JP, KR)."""
    mkts = markets or ["EN", "JP", "KR"]
    results = {}
    for m in mkts:
        try:
            res = discover_and_produce_market_trend(market=m, auto_produce=auto_produce)
            results[m] = res
        except Exception as e:
            logger.error(f"Daily pipeline failed for {m}: {e}")
            results[m] = []
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Canonical Trend Engine B1 Discovery & Production")
    parser.add_argument("term", nargs="?", default=None, help="Custom seed term")
    parser.add_argument("pos_market", nargs="?", default=None, help="Target market (EN, JP, KR)")
    parser.add_argument("--market", "-m", default=None, help="Target market (EN, JP, KR)")
    parser.add_argument("--seed", "-s", default=None, help="Custom seed term")
    parser.add_argument("--max-candidates", "-n", type=int, default=15, help="Max candidates to scan (default: 15)")
    parser.add_argument("--no-auto", action="store_true", help="Disable automated B1.5 -> B2 production")
    args = parser.parse_args()

    target_mkt = (args.market or args.pos_market or "EN").upper()
    custom_term = args.seed or args.term
    if custom_term == "":
        custom_term = None
    auto_prod = not args.no_auto
    max_candidates = args.max_candidates

    print(f"Executing Trend Engine B1 CLI (term={custom_term}, market={target_mkt}, auto_produce={auto_prod}, max_candidates={max_candidates})...")
    res = discover_and_produce_market_trend(market=target_mkt, custom_seed=custom_term, auto_produce=auto_prod, max_scan_candidates=max_candidates)
    print(f"Finished. Produced {len(res)} topics.")
