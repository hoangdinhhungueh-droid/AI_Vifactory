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
import re
import json
import logging
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime, timezone

from app.services.trend_free_signals import (
    gtrends_daily_rss,
    youtube_autocomplete,
    google_autocomplete,
    gtrends_discover_trending_searches
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


def perform_direct_platform_recon(term: str, market: str) -> dict:
    """Directly searches the keyword across Google Autocomplete, YouTube Autocomplete, and YouTube Search."""
    m_up = (market or "EN").upper()
    cfg = MARKET_CONFIG.get(m_up, MARKET_CONFIG["EN"])
    hl = cfg["hl"]
    gl = cfg["gl"]
    intent_mods = cfg["intent_modifiers"]

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

    all_rising = []
    seen = set()
    for q in g_sugg + yt_sugg + intent_queries:
        q_str = str(q).strip()
        if q_str and q_str.lower() not in seen:
            seen.add(q_str.lower())
            all_rising.append(q_str)

    viral_videos = []
    api_key = os.environ.get("YT_UPLOAD_API_KEY")
    if api_key:
        try:
            quota = QuotaTracker()
            raw_vids = youtube_search(api_key, term, m_up.lower(), quota)
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
                viral_videos.sort(key=lambda x: x.get("views", 0), reverse=True)
        except Exception as e:
            logger.warning(f"[{m_up}] YouTube search error: {e}")

    return {
        "rising_queries": all_rising[:10],
        "google_suggestions": g_sugg[:5],
        "youtube_suggestions": yt_sugg[:5],
        "viral_videos": viral_videos[:6]
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

    candidates = []
    seen = {}

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
                        "source": "gtrends_rss"
                    }
                    seen[k] = cand_obj
                else:
                    if geo not in seen[k]["geos_present"]:
                        seen[k]["geos_present"].append(geo)
        except Exception as e:
            logger.warning(f"[{m_up}/{geo}] Failed to fetch Daily RSS: {e}")

    # Fallback to Discover Trending Searches if needed
    if len(seen) < 10:
        for geo in geos[:2]:
            try:
                disc_terms = gtrends_discover_trending_searches(geo=geo, count=15, timeout=10.0)
                for t in disc_terms:
                    t = t.strip()
                    if not t:
                        continue
                    k = t.lower()
                    if k not in seen:
                        seen[k] = {
                            "term": t,
                            "primary_geo": geo,
                            "geos_present": [geo],
                            "approx_traffic": "discover_trending",
                            "news_title": "",
                            "source": "gtrends_discover"
                        }
            except Exception as e:
                logger.warning(f"[{m_up}/{geo}] Discover Trending Searches error: {e}")

    candidates = list(seen.values())

    # Multi-geo presence bonus
    def sort_score(cand):
        geo_count = len(cand.get("geos_present", []))
        raw_traffic = str(cand.get("approx_traffic", ""))
        num_m = re.findall(r"(\d+)", raw_traffic.replace(",", ""))
        traffic_val = int(num_m[0]) if num_m else 0
        return (geo_count * 1000) + traffic_val

    candidates.sort(key=sort_score, reverse=True)

    # Deduplicate against permanent topic history registry
    unhandled = []
    for c in candidates:
        term = c["term"]
        if is_topic_already_handled(term, market=m_up):
            logger.info(f"[{m_up}] Skipping previously handled topic: {term}")
            continue
        unhandled.append(c)

    logger.info(f"[{m_up}] Total {len(candidates)} candidates fetched -> {len(unhandled)} unhandled fresh candidates.")
    return unhandled


def commit_trend_task(topic_data: dict) -> str:
    """Save approved topic to /var/vf/pending_tasks/<task_id>.json,
    generate competitor intel card, record to History Registry, and sync to Notion SoT.
    """
    try:
        from app.services.trend_gate_ai import get_next_episode_id
        task_id = get_next_episode_id(topic_data.get("market", "EN"), topic_data.get("task_slug") or topic_data.get("raw_term", "topic"))
    except Exception as _ep_err:
        logger.error(f"[trend_engine] Failed to generate episode ID via trend_gate_ai: {_ep_err}")
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
            "Trend Source": {"multi_select": [{"name": "gtrends_rss"}, {"name": "youtube_recon"}]}
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

    try:
        from app.llm_router import _send_telegram
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
        task_id = html.escape(str(topic_data.get("task_id", "")))
        score = topic_data.get("viability_score", 9.0)

        lines = [
            "🎯 <b>[HUMAN GATE 1] THÔNG BÁO TIẾN ĐỘ CHỦ ĐỀ SẢN XUẤT (GO-LIVE 2026)</b>",
            "<i>(✨ B1 Trend Recon & B1.5 Competitor Gap bởi GPT-6-Astra qua HHTech API)</i>",
            "",
            f"{flag} <b>Market {mkt}:</b> <code>{raw_term}</code> (Viability: {score}/10)",
            f"• <b>Đề tài:</b> {title_vi}",
            f"• <b>Search-Specific Key:</b> <code>{keyword}</code>",
            f"• <b>🔥 Cụm từ tìm kiếm tăng:</b> <code>{rising}</code>",
            f"• <b>Niche Brief:</b> {niche}",
            f"• <b>Khác biệt đối thủ (Blue Ocean Gap):</b> <i>{gap}</i>",
            f"• <b>5-Beat Docudrama:</b> {arcs[:180]}...",
            f"👉 <b>Task ID:</b> <code>{task_id}</code>",
            "--------------------------------------------------",
            "⚙️ <i>Hệ thống đang tự động chuyển tiếp sang <b>B2 Story Engine</b> (Kịch bản điều tra 12–15 phút) & <b>B3 Visual Plan</b>!</i>"
        ]
        msg = chr(10).join(lines)
        _send_telegram(msg)
        logger.info(f"[trend_engine] Sent pure Telegram Gate 1 notification for {task_id}")
    except Exception as e:
        logger.warning(f"[trend_engine] Failed to send Telegram Gate 1 notification: {e}")


def discover_and_produce_market_trend(
    market: str = "EN",
    custom_seed: str = None,
    auto_produce: bool = True,
    max_scan_candidates: int = 6
) -> list[dict]:
    """Execute canonical B1 trend discovery and automated B1.5 -> B2 -> B3 pipeline
    for exactly 1 topic per market per day.
    """
    m_up = (market or "EN").upper()
    print(f"\\n=======================================================")
    print(f"🚀 [TREND ENGINE B1] Scanning Market {m_up} for Daily Production Topic")
    print(f"=======================================================")

    candidates = fetch_live_trending_terms(m_up, custom_seed=custom_seed)
    if not candidates:
        logger.warning(f"[{m_up}] No unhandled candidates found.")
        return []

    produced_topics = []

    for idx, c in enumerate(candidates[:max_scan_candidates], start=1):
        term = c["term"]
        print(f"\\n[{m_up}] Candidate #{idx}/{min(len(candidates), max_scan_candidates)}: '{term}' (Traffic: {c.get('approx_traffic')}, Geos: {c.get('geos_present')})")

        # 1. Direct Platform Recon (Google/YouTube Autocomplete & Viral Videos)
        recon_data = perform_direct_platform_recon(term, m_up)
        rising_queries = recon_data.get("rising_queries", [])
        viral_videos = recon_data.get("viral_videos", [])

        # 2. Ground-truth Wikipedia extract
        factsheet = fetch_ground_truth_factsheet(term, m_up)

        # 3. Viability assessment via HHTech GPT-6-Astra
        viability = assess_keyword_video_viability(
            term=term,
            market=m_up,
            traffic=str(c.get("approx_traffic", "")),
            rising_queries=rising_queries[:6],
            top_videos=viral_videos[:4]
        )
        score = viability.get("viability_score", 0)

        if not viability.get("is_video_viable") or score < 7.0:
            print(f"  ❌ REJECTED: {viability.get('rejection_reason', 'Low viability score (< 7.0)')}")
            continue

        specific_angle = viability.get("specific_viral_angle") or term
        print(f"  ✅ APPROVED! Viability: {score}/10 | Angle: {specific_angle}")

        # 4. Reason Niche Brief & 5-Act Direction
        niche_data = reason_topic_niche(
            subject=term,
            market=m_up,
            virality_score=0.92,
            rising_queries=rising_queries[:8],
            viral_videos=viral_videos[:5]
        )

        t_obj = {
            "market": m_up,
            "raw_term": term,
            "geos_present": c.get("geos_present"),
            "approx_traffic": c.get("approx_traffic"),
            "viability_score": score,
            "specific_viral_angle": specific_angle,
            "visual_feasibility": viability.get("visual_feasibility_score"),
            "conflict_depth": viability.get("conflict_depth_score"),
            "topic_name_vi": niche_data.get("topic_name_vi"),
            "search_specific_keyword": niche_data.get("search_specific_keyword"),
            "task_slug": niche_data.get("task_slug"),
            "niche_angle_brief": niche_data.get("niche_angle_brief"),
            "competitor_differentiation_gap": niche_data.get("competitor_differentiation_gap", ""),
            "story_direction_5_arcs": niche_data.get("story_direction_5_arcs"),
            "rising_queries": rising_queries[:8],
            "breakout_queries": niche_data.get("breakout_queries") or rising_queries[:3],
            "safety_label": niche_data.get("safety_label"),
            "treatment_note": niche_data.get("treatment_note"),
            "factsheet": factsheet,
            "viral_competitor_videos": viral_videos[:5]
        }

        # Commit task to pending tasks, history registry, and Notion Trend Brain
        task_id = commit_trend_task(t_obj)
        t_obj["task_id"] = task_id
        print(f"  💾 Committed Task ID: {task_id}")

        # 5. Inline B1.5 Competitor Recon (Deep Two-Pass Recon & Top Comments)
        print(f"  🎯 [B1.5] Executing Deep Competitor Recon for {task_id}...")
        try:
            recon_keyword = t_obj.get("search_specific_keyword") or term
            recon_card = run_b15(task_id, recon_keyword, t_obj.get("niche_angle_brief", "General"))
            if recon_card:
                gap_val = recon_card.get("competitor_narrative_anatomy", {}).get("fatal_explanatory_vacuum", "")
                if gap_val:
                    t_obj["competitor_differentiation_gap"] = gap_val
                    t_obj["competitor_gap"] = gap_val
                    task_file = os.path.join("/var/vf/pending_tasks", f"{task_id}.json")
                    if os.path.exists(task_file):
                        try:
                            with open(task_file, "w", encoding="utf-8") as tf:
                                json.dump(t_obj, tf, ensure_ascii=False, indent=2)
                        except Exception as _we:
                            logger.warning(f"Could not re-persist task file with competitor gap: {_we}")
                print(f"  ✅ [B1.5] Competitor Intel Card saved successfully with real gap: {gap_val[:60]}...")
        except Exception as re_err:
            logger.warning(f"[{task_id}] Inline B1.5 recon warning: {re_err}")

        # 6. Send Pure Telegram Gate 1 Notification
        send_pure_telegram_gate1_notification(t_obj)

        # 7. Automated Transition to B2 Story Engine & B3 Director Plan
        if auto_produce:
            print(f"  ⚙️ [B2/B3] Auto-producing 12-15 min docudrama & 2-layer director plan for {task_id}...")
            try:
                from scripts.produce_episode_hg1 import run_chain
                run_chain(task_id)
                print(f"  🎉 [SUCCESS] Pipeline completed through B1 -> B1.5 -> B2 -> B3 -> Gate 2 for {task_id}!")
                produced_topics.append(t_obj)
                break  # Exactly 1 completed topic per market per day!
            except Exception as prod_err:
                logger.error(f"[{task_id}] Auto-production failed: {prod_err}. Rotating to next candidate...")
                try:
                    from app.llm_router import _send_telegram
                    _send_telegram(f"⚠️ <b>[Story Gate Fallback]</b> Task <code>{task_id}</code> không đạt chuẩn hoặc lỗi. Đang tự động xoay sang candidate kế tiếp cho thị trường {m_up}...")
                except Exception:
                    pass
                continue
        else:
            produced_topics.append(t_obj)
            break

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
    import sys
    custom_term = None
    target_mkt = "EN"
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        custom_term = sys.argv[1]
    if len(sys.argv) > 2 and not sys.argv[2].startswith("--"):
        target_mkt = sys.argv[2]

    print(f"Executing Trend Engine B1 CLI (term={custom_term}, market={target_mkt})...")
    res = discover_and_produce_market_trend(market=target_mkt, custom_seed=custom_term, auto_produce=True)
    print(f"Finished. Produced {len(res)} topics.")
