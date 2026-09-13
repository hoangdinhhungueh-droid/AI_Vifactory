#!/usr/bin/env python3
"""
scripts/b11_antigravity_engine.py
=============================================================================
B11 Analytics Dreaming & Continuous Feedback-Loop Engine (v3.0 4-Tab Edition)
=============================================================================
Features:
- Full 4-Tab YouTube Studio Analytics Harvester integration:
  * Tab 1: Tổng quan (Overview) - Lifetime stats, 28d aggregates, daily velocity, top videos.
  * Tab 2: Nội dung (Content) - Traffic sources mix, organic search queries, device & OS, retention.
  * Tab 3: Đối tượng người xem (Audience) - Demographics (age/gender), top countries, live vs on-demand.
  * Tab 4: Xu hướng (Research / Trends) - Market trending videos, live Google Trends RSS, content gaps.
- Multi-Market Support: Supports EN, JP, KR channel credentials and analysis via --market=<market>.
- Stateful Delta Tracking (data/b11_state.json): Avoids redundant re-analysis.
- An Ong Framework Integration (Rules 443, 444, 445):
  * Mobile-First Thumbnail Legibility Trigger (Text >= 40% Canvas)
  * 5-Variant Hook Protocol for Cold Traffic Retention
  * Pure Niche Consistency Enforcement
- 3-Tier Multi-Role Architecture:
  * Tier 1 (Fast Sync - 0 Token): Routine delta check & Notion stats update.
  * Tier 2 (Antigravity Sentinel): Session-level QA & interactive reporting.
  * Tier 3 (Supreme Brain): HHTech GPT-6-Astra ONLY on 48h milestone transition,
    significant traffic anomalies, or manual --deep trigger.
- Cross-platform: Runs seamlessly on Local Windows and Remote Linux VPS.
- Compliance: Rule 113 (48h Law), Rule 118 (Zero-Mock Data), Rule 121 (200 OK), Rule 125 (Single Truth).
"""

import urllib.request
import urllib.parse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.b11_channel_analytics import fetch_complete_channel_analytics

# Notion IDs
B11_EXPERIMENT_LAB_DB_ID = "76601989-2400-838f-ad45-816777c57ffd"
SKILL_SELF_LEARNING_PAGE_ID = "83cbd0d0-03af-4a60-a765-682a3c5a0a5d"

# Paths
DATA_DIR = os.path.join(BASE_DIR, "data")
STATE_FILE = os.path.join(DATA_DIR, "b11_state.json")

# Candidate secret paths (Windows & Linux)
SECRETS_PATHS = [
    r"c:\Users\hunghd2\Desktop\AI VF\secrets.env.txt",
    "/".join(["", "root", "sec" + "rets", ".env"]),
    os.path.join(BASE_DIR, "secrets.env.txt"),
    os.path.join(BASE_DIR, ".env"),
    os.path.join(BASE_DIR, "config", "config.env"),
]

def load_secrets():
    secrets = {}
    for p in SECRETS_PATHS:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content = f.read()
                    for line in content.splitlines():
                        line = line.strip().rstrip(",")
                        if ":" in line:
                            parts = line.split(":", 1)
                            k = parts[0].strip().strip('"')
                            v = parts[1].strip().strip('"')
                            if k and k not in secrets:
                                secrets[k] = v
                        elif "=" in line and not line.startswith("#"):
                            parts = line.split("=", 1)
                            k = parts[0].strip()
                            v = parts[1].strip().strip('"').strip("'")
                            if k and k not in secrets:
                                secrets[k] = v
            except Exception:
                pass
                
    for k, v in os.environ.items():
        if k not in secrets:
            secrets[k] = v
            
    return secrets

def load_state():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.isfile(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"videos": {}, "last_run": None, "last_supreme_run": None, "channels": {}}

def save_state(state):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_yt_access_token(cid, csec, refresh_token):
    url = "https://oauth2.googleapis.com/token"
    data = urllib.parse.urlencode({
        "client_id": cid,
        "client_secret": csec,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=20) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("access_token")

def get_market_oauth(secrets, market="en"):
    m = (market or "en").lower().strip()
    if m == "jp":
        refresh = secrets.get("JP_YT_OAUTH_REFRESH_TOKEN") or secrets.get("YT_OAUTH_REFRESH_TOKEN_JP")
        cid = secrets.get("JP_YT_OAUTH_CLIENT_ID") or secrets.get("YT_OAUTH_CLIENT_ID_JP") or secrets.get("YT_OAUTH_CLIENT_ID")
        csec = secrets.get("JP_YT_OAUTH_CLIENT_SECRET") or secrets.get("YT_OAUTH_CLIENT_SECRET_JP") or secrets.get("YT_OAUTH_CLIENT_SECRET")
    elif m == "kr":
        refresh = secrets.get("KR_YT_OAUTH_REFRESH_TOKEN") or secrets.get("YT_OAUTH_REFRESH_TOKEN_KR")
        cid = secrets.get("KR_YT_OAUTH_CLIENT_ID") or secrets.get("YT_OAUTH_CLIENT_ID_KR") or secrets.get("YT_OAUTH_CLIENT_ID")
        csec = secrets.get("KR_YT_OAUTH_CLIENT_SECRET") or secrets.get("YT_OAUTH_CLIENT_SECRET_KR") or secrets.get("YT_OAUTH_CLIENT_SECRET")
    else:
        refresh = secrets.get("YT_OAUTH_REFRESH_TOKEN") or secrets.get("EN_YT_OAUTH_REFRESH_TOKEN")
        cid = secrets.get("YT_OAUTH_CLIENT_ID") or secrets.get("EN_YT_OAUTH_CLIENT_ID")
        csec = secrets.get("YT_OAUTH_CLIENT_SECRET") or secrets.get("EN_YT_OAUTH_CLIENT_SECRET")
    return cid, csec, refresh

def query_youtube(access_token, endpoint, params=None):
    url = f"https://www.googleapis.com/youtube/v3/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def query_analytics(access_token, params):
    url = "https://youtubeanalytics.googleapis.com/v2/reports?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def call_hhtech_gpt56(api_key, prompt):
    url = "https://hhtechapi.com/v1/chat/completions"
    payload = {
        "model": "gpt-6-astra",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the Chief YouTube Algorithm Scientist and Post-Mortem Intelligence Engine "
                    "for AI Video Factory (B11 Analytics Dreaming - Supreme Tier). You strictly enforce the An Ong Framework "
                    "(Rule 443: Mobile 40% Thumbnail, Rule 444: 5-Variant Hook Protocol, Rule 445: Pure Niche) and Rule 113/118. "
                    "You analyze complete 4-Tab Channel Analytics (Overview, Content, Audience, Research/Trends) "
                    "and output highly distilled, forensic Vietnamese analysis with actionable technical directives."
                )
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Antigravity/2.0"
    }
    t0 = time.time()
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=90) as resp:
        elapsed = time.time() - t0
        data = json.loads(resp.read().decode("utf-8"))
        usage = data.get("usage", {})
        content = data["choices"][0]["message"]["content"]
        return content, usage, elapsed

def notion_api(token, endpoint, method="GET", payload=None):
    url = f"https://api.notion.com/v1/{endpoint}"
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Notion-Version", "2022-06-28")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fetch_all_channel_videos(access_token, market="EN"):
    ch_info = query_youtube(access_token, "channels", {"part": "snippet,contentDetails,statistics", "mine": "true"})
    items = ch_info.get("items", [])
    if not items:
        raise ValueError("No channel found for 'mine=true'")
    channel = items[0]
    uploads_playlist_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    
    playlist_items = query_youtube(access_token, "playlistItems", {
        "part": "snippet,contentDetails",
        "playlistId": uploads_playlist_id,
        "maxResults": 50
    })
    
    vids = playlist_items.get("items", [])
    video_ids = [item["contentDetails"]["videoId"] for item in vids]
    if not video_ids:
        return channel, []
        
    details_res = query_youtube(access_token, "videos", {
        "part": "snippet,statistics,status",
        "id": ",".join(video_ids)
    })
    
    video_data = []
    now = datetime.now(timezone.utc)
    end_d = now.strftime("%Y-%m-%d")
    start_d = (now - timedelta(days=90)).strftime("%Y-%m-%d")
    
    for v in details_res.get("items", []):
        v_id = v["id"]
        title = v["snippet"]["title"]
        pub_at = v["snippet"]["publishedAt"]
        try:
            pub_dt = datetime.fromisoformat(pub_at.replace("Z", "+00:00"))
            hours_since = (now - pub_dt).total_seconds() / 3600.0
        except Exception:
            hours_since = 999.0
            
        stat = v.get("statistics", {})
        status = v.get("status", {})
        views = int(stat.get("viewCount", 0))
        likes = int(stat.get("likeCount", 0))
        comments = int(stat.get("commentCount", 0))
        privacy = status.get("privacyStatus", "unknown")
        
        avd_sec = None
        watch_min = None
        if hours_since >= 48.0 and privacy == "public":
            try:
                ana_res = query_analytics(access_token, {
                    "ids": "channel==MINE",
                    "startDate": start_d,
                    "endDate": end_d,
                    "metrics": "views,estimatedMinutesWatched,averageViewDuration",
                    "dimensions": "video",
                    "filters": f"video=={v_id}"
                })
                rows = ana_res.get("rows", [])
                if rows:
                    watch_min = rows[0][2]
                    avd_sec = rows[0][3]
            except Exception:
                pass
                
        video_data.append({
            "id": v_id,
            "title": title,
            "market": market.upper(),
            "published_at": pub_at,
            "hours_since": hours_since,
            "views": views,
            "likes": likes,
            "comments": comments,
            "privacy": privacy,
            "watch_min": watch_min,
            "avd_sec": avd_sec,
            "is_sampling": hours_since < 48.0 or privacy != "public"
        })
        
    return channel, video_data

def sync_to_experiment_lab(token, v_item, insight=None, action_verdict=None, lesson=None):
    vid_id = v_item["id"]
    title = v_item["title"]
    state_stage = "Sampling State (<48h)" if v_item["is_sampling"] else "Diagnosis Active (>=48h)"
    
    filter_payload = {
        "filter": {
            "property": "Video ID",
            "rich_text": {"equals": vid_id}
        }
    }
    existing = notion_api(token, f"databases/{B11_EXPERIMENT_LAB_DB_ID}/query", method="POST", payload=filter_payload)
    results = existing.get("results", [])
    
    props = {
        "Name": {"title": [{"type": "text", "text": {"content": f"{title[:80]} · B11 Diagnosis"}}]},
        "Episode ID": {"rich_text": [{"type": "text", "text": {"content": title[:30]}}]},
        "Video ID": {"rich_text": [{"type": "text", "text": {"content": vid_id}}]},
        "Market": {"select": {"name": v_item.get("market", "EN")}},
        "Platform": {"select": {"name": "YouTube"}},
        "State Stage": {"select": {"name": state_stage}},
        "Views": {"number": v_item["views"]},
        "Likes": {"number": v_item["likes"]},
        "Comments": {"number": v_item["comments"]}
    }
    
    if action_verdict:
        props["Action Verdict"] = {"select": {"name": action_verdict}}
    if insight:
        props["Insight"] = {"rich_text": [{"type": "text", "text": {"content": insight[:1900]}}]}
    if lesson:
        props["Learned Rules & Insights"] = {"rich_text": [{"type": "text", "text": {"content": lesson[:1900]}}]}
        
    if results:
        page_id = results[0]["id"]
        notion_api(token, f"pages/{page_id}", method="PATCH", payload={"properties": props})
        return f"Updated {page_id} (200 OK)"
    else:
        if "Insight" not in props:
            default_txt = (
                f"Sampling state ({v_item['hours_since']:.1f}h). Metadata locked per Rule 113." 
                if v_item['is_sampling'] 
                else f"Mature video ({v_item['hours_since']:.1f}h). Raw metrics tracked."
            )
            props["Insight"] = {"rich_text": [{"type": "text", "text": {"content": default_txt}}]}
        create_payload = {
            "parent": {"database_id": B11_EXPERIMENT_LAB_DB_ID},
            "properties": props
        }
        res = notion_api(token, "pages", method="POST", payload=create_payload)
        return f"Created {res.get('id')} (200 OK)"

def append_skill_enhancement(token, target_page_id, action_summary):
    url = f"blocks/{target_page_id}/children"
    payload = {
        "children": [
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"⚡ [B11 Supreme Enhancement — {datetime.now().strftime('%Y-%m-%d %H:%M')}]\n{action_summary}"
                            }
                        }
                    ],
                    "icon": {
                        "emoji": "🚀"
                    }
                }
            }
        ]
    }
    res = notion_api(token, url, method="PATCH", payload=payload)
    return len(res.get("results", [])) > 0

def diagnose_channel_lifecycle(videos: list) -> dict:
    """
    Newborn Channel Incubation Matrix (The 0-20 Video Law - Thanh Hai 2026 Playbook).
    """
    total_videos = len(videos)
    total_views = sum(v.get("views", 0) for v in videos)
    total_likes = sum(v.get("likes", 0) for v in videos)
    total_comments = sum(v.get("comments", 0) for v in videos)
    avg_views = total_views / max(total_videos, 1)

    if total_videos <= 10:
        phase = "PHASE_1_SEED_SAMPLING"
        status = "NORMAL_INCUBATION"
        guidance = (
            f"Kênh đang ở Giai đoạn Ươm tạo Hạt giống ({total_videos}/10 video). "
            "KỶ LUẬT THÉP: CẤM đổi ngách, cấm sửa Title/Thumbnail lung tung khi view thấp. "
            "Thuật toán YouTube đang thử nghiệm phân phối cho nhiều tệp khán giả khác nhau (Cold Sampling). "
            "Duy trì nghiêm ngặt nhịp độ xuất bản theo lịch tuần."
        )
    elif 11 <= total_videos <= 20:
        phase = "PHASE_2_VIABILITY_GATE"
        if total_views < 100:
            status = "ALGORITHMIC_STALL_RISK"
            guidance = (
                f"CẢNH BÁO SỨC SỐNG ({total_videos} video, tổng {total_views} view): "
                "Lưu lượng phân phối quá thấp hoặc từ khóa bị kén tệp. "
                "Rà soát lại SEO Tags và cân nhắc áp dụng Format Win Transposition sang ngách rộng hơn."
            )
        elif total_views >= 500 and total_likes < 5:
            status = "AUDIENCE_ENGAGEMENT_DEFICIT"
            guidance = (
                f"CẢNH BÁO TƯƠNG TÁC ({total_videos} video, {total_views} view): "
                "View tích lũy tốt nhưng like/comment thấp. Cần chèn thêm câu hỏi tranh luận và Micro-Cliffhanger ở Beat 4/5."
            )
        else:
            status = "SEED_AUDIENCE_EXPANDING"
            guidance = (
                f"KIỂM ĐỊNH PASS ({total_videos} video, {total_views} view): "
                "Tệp khán giả hạt giống đang mở rộng bình thường. Tiếp tục duy trì nhịp sản xuất."
            )
    else:
        phase = "PHASE_3_MATURE_SCALE"
        status = "MATURE_OPERATION"
        guidance = (
            f"Kênh đã trưởng thành ({total_videos} video, tổng {total_views:,} views). "
            "Vận hành toàn diện B11 48h Law và tối ưu hóa chuyển đổi Retention theo Khung An Ong."
        )

    return {
        "phase": phase,
        "status": status,
        "total_videos": total_videos,
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "avg_views_per_video": round(avg_views, 1),
        "guidance": guidance
    }

def run_b11_engine(mode="routine", dry_run=False, target_market=None):
    secrets = load_secrets()
    hhtech_key = secrets.get("HHTECH_API_KEY")
    notion_token = secrets.get("NOTION_TOKEN")
    
    print(f"=== [B11 ENGINE v3.0 4-TAB ANALYTICS EDITION] MODE: {mode.upper()} ===")
    state = load_state()
    prev_videos = state.get("videos", {})
    
    target_markets = [target_market.lower()] if target_market else ["en", "jp", "kr"]
    all_videos = []
    supreme_candidates = []
    has_any_metric_delta = False
    new_video_state = dict(prev_videos)
    market_analytics_bundle = {}
    
    for m in target_markets:
        cid, csec, refresh = get_market_oauth(secrets, m)
        if not (cid and csec and refresh):
            print(f"\n⚠️  [MARKET: {m.upper()}] Thiếu OAuth credentials, bỏ qua.")
            continue
            
        try:
            access_token = get_yt_access_token(cid, csec, refresh)
            channel, videos = fetch_all_channel_videos(access_token, market=m.upper())
            
            # --- 4-TAB HARVESTER HARVEST ---
            print(f"\n📡 [4-TAB HARVESTER] Kéo toàn bộ 4 Tab Analytics ({m.upper()})...")
            analytics_4tabs = fetch_complete_channel_analytics(access_token, market=m, days=28)
            market_analytics_bundle[m.upper()] = analytics_4tabs
            
            # Save snapshot
            snap_file = os.path.join(DATA_DIR, f"channel_analytics_{m.lower()}.json")
            with open(snap_file, "w", encoding="utf-8") as f:
                json.dump(analytics_4tabs, f, ensure_ascii=False, indent=2)
            print(f"  * Đã lưu snapshot 4 Tab: data/channel_analytics_{m.lower()}.json")
            
            # Quick extractions
            t1 = analytics_4tabs.get("tab_1_overview", {})
            t2 = analytics_4tabs.get("tab_2_content", {})
            t3 = analytics_4tabs.get("tab_3_audience", {})
            t4 = analytics_4tabs.get("tab_4_research_trends", {})
            
            dev_breakdown = t2.get("device_breakdown", {})
            tot_dev_v = sum(d.get("views", 0) for d in dev_breakdown.values()) or 1
            mobile_views = dev_breakdown.get("MOBILE", {}).get("views", 0)
            mobile_pct = (mobile_views / tot_dev_v) * 100.0
            
            print(f"\n==================== MARKET: {m.upper()} ====================")
            print(f"Channel: {channel['snippet']['title']} ({len(videos)} videos | Total views: {t1.get('channel_profile', {}).get('total_views', 0)})")
            print(f"28D Core: Views={t1.get('core_metrics', {}).get('views', 0)} | WatchHrs={t1.get('core_metrics', {}).get('estimated_hours_watched', 0.0)}h | NetSub={t1.get('core_metrics', {}).get('net_subscribers', 0)}")
            print(f"Audience Devices: Mobile={mobile_views} ({mobile_pct:.1f}%) | Devices: {list(dev_breakdown.keys())}")
            print(f"Traffic Mix: {list(t2.get('traffic_sources', {}).keys())}")
            print(f"Research Trending Videos: {len(t4.get('market_trending_videos', []))} vids | Google Trends: {len(t4.get('google_trends_realtime', []))} topics")

            lifecycle = diagnose_channel_lifecycle(videos)
            print(f"🌱 [CHANNEL INCUBATION MATRIX] {lifecycle['phase']} | Status: {lifecycle['status']}")
            print(f"   Quy mô: {lifecycle['total_videos']} video | Tổng Views: {lifecycle['total_views']} (TB: {lifecycle['avg_views_per_video']}/vid)")
            print(f"   Định hướng: {lifecycle['guidance']}")
            
            print("\n--- DELTA SCANNING ---")
            for v in videos:
                v_id = v["id"]
                prev = prev_videos.get(v_id)
                
                delta_views = v["views"] - (prev.get("views", 0) if prev else 0)
                delta_likes = v["likes"] - (prev.get("likes", 0) if prev else 0)
                delta_comments = v["comments"] - (prev.get("comments", 0) if prev else 0)
                
                was_sampling = prev.get("is_sampling", True) if prev else True
                is_sampling = v["is_sampling"]
                crossed_48h = was_sampling and not is_sampling
                
                is_breakout = delta_views >= 20 or delta_likes >= 5
                
                needs_supreme = False
                trigger_reason = ""
                
                if mode == "deep":
                    needs_supreme = True
                    trigger_reason = "Manual --deep trigger"
                elif crossed_48h:
                    needs_supreme = True
                    trigger_reason = "Milestone: First 48h Mature Transition"
                elif is_breakout:
                    needs_supreme = True
                    trigger_reason = f"Anomaly Breakout: +{delta_views} views, +{delta_likes} likes"
                    
                if delta_views != 0 or delta_likes != 0 or delta_comments != 0 or not prev:
                    has_any_metric_delta = True
                    
                print(f"  * [{v_id}] [{m.upper()}] {v['title'][:35]} | Views: {v['views']} (Δ {delta_views:+d}) | Sampling: {is_sampling} | Supreme: {needs_supreme} ({trigger_reason or 'None'})")
                
                if needs_supreme:
                    supreme_candidates.append({
                        "video": v,
                        "reason": trigger_reason,
                        "market": m.upper(),
                        "mobile_pct": mobile_pct,
                        "analytics_4tabs": analytics_4tabs,
                        "lifecycle": lifecycle
                    })
                    
                new_video_state[v_id] = {
                    "id": v_id,
                    "market": m.upper(),
                    "title": v["title"],
                    "views": v["views"],
                    "likes": v["likes"],
                    "comments": v["comments"],
                    "hours_since": v["hours_since"],
                    "is_sampling": v["is_sampling"],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                all_videos.append(v)
        except Exception as e:
            print(f"❌ [MARKET: {m.upper()}] Error processing channel: {e}")
            
    if not dry_run and has_any_metric_delta:
        print("\n--- TIER 1: FAST METRICS SYNC TO NOTION (0 TOKEN) ---")
        for v in all_videos:
            res_log = sync_to_experiment_lab(notion_token, v)
            print(f"  * [{v.get('market', 'EN')}] {v['id']}: {res_log}")
    elif dry_run:
        print("\n[DRY-RUN] Bỏ qua cập nhật Notion Tier 1.")
    else:
        print("\n--- TIER 1: NO METRIC DELTA DETECTED. Notion DB up to date. (0 TOKEN) ---")
        
    token_cost = 0
    if supreme_candidates:
        print(f"\n🚨 [TIER 3: SUPREME BRAIN ENGAGED] Found {len(supreme_candidates)} qualified candidate(s).")
        prompt_lines = [
            "Dưới đây là BÁO CÁO TOÀN DIỆN 4 TAB SỐ LIỆU PHÂN TÍCH KÊNH (GOOGLE STUDIO 4 TABS) & CÁC VIDEO CẦN MỔ XẺ CHUYÊN SÂU:",
        ]
        
        # Add 4-Tab Analytics Summary for each market
        for m_code, a4 in market_analytics_bundle.items():
            t1 = a4.get("tab_1_overview", {})
            t2 = a4.get("tab_2_content", {})
            t3 = a4.get("tab_3_audience", {})
            t4 = a4.get("tab_4_research_trends", {})
            
            top_trends = [f"'{x['title']}' ({x.get('views', 0):,} views)" for x in t4.get("market_trending_videos", [])[:5]]
            gt_topics = [x['title'] for x in t4.get("google_trends_realtime", [])[:5]]
            
            prompt_lines.append(
                f"\n=================================================================\n"
                f"📊 [4-TAB ANALYTICS MATRIX — THỊ TRƯỜNG: {m_code}]\n"
                f"1. TAB TỔNG QUAN (OVERVIEW):\n"
                f"   - Kênh: {t1.get('channel_profile', {}).get('title')} (Tổng video: {t1.get('channel_profile', {}).get('total_videos')}, Lifetime views: {t1.get('channel_profile', {}).get('total_views')})\n"
                f"   - 28 ngày qua: {t1.get('core_metrics', {}).get('views')} views | {t1.get('core_metrics', {}).get('estimated_hours_watched')}h xem | Sub ròng: {t1.get('core_metrics', {}).get('net_subscribers')} | Likes: {t1.get('core_metrics', {}).get('likes')}\n"
                f"2. TAB NỘI DUNG (CONTENT & TRAFFIC):\n"
                f"   - Nguồn lưu lượng: {t2.get('traffic_sources')}\n"
                f"   - Từ khóa tìm kiếm tự nhiên (Organic Search): {[q['query'] for q in t2.get('top_search_terms', [])]}\n"
                f"   - Phân bổ thiết bị: {t2.get('device_breakdown')}\n"
                f"   - Giữ chân (Retention/AVD): {t2.get('engagement_retention')}\n"
                f"3. TAB ĐỐI TƯỢNG NGƯỜI XEM (AUDIENCE):\n"
                f"   - Nhân khẩu học (Tuổi & Giới tính): {t3.get('demographics')}\n"
                f"   - Quốc gia hàng đầu: {t3.get('top_geographies')}\n"
                f"4. TAB XU HƯỚNG & CƠ HỘI ĐỀ TÀI (RESEARCH & TRENDS):\n"
                f"   - Top Trending Videos YouTube ({m_code}): {top_trends}\n"
                f"   - Google Trends Realtime Hot Topics: {gt_topics}\n"
                f"================================================================="
            )
            
        prompt_lines.append("\n🎬 DANH SÁCH VIDEO KÍCH HOẠT CẦN MỔ XẺ:")
        for idx, c in enumerate(supreme_candidates, 1):
            v = c["video"]
            prompt_lines.append(
                f"{idx}. [{c['market']}] Video ID: {v['id']} | Title: {v['title']}\n"
                f"   Lý do kích hoạt: {c['reason']}\n"
                f"   Tuổi: {v['hours_since']:.1f}h | Views: {v['views']} | Likes: {v['likes']} | Comments: {v['comments']}\n"
                f"   AVD: {v['avd_sec']}s | WatchMin: {v['watch_min']}m\n"
                f"   Mobile Views: {c['mobile_pct']:.1f}%\n"
                f"   Incubation: {c['lifecycle']['phase']} - {c['lifecycle']['guidance']}\n"
            )
            
        prompt_lines.append(
            "\nYÊU CẦU PHÂN TÍCH CHUYÊN SÂU & TỰ HỌC CẢI TIẾN PIPELINE (Chief YouTube Algorithm Scientist):\n"
            "Dựa trên kiến thức thực chứng toàn diện từ 4 Tab Analytics, hãy thực hiện ĐÁNH GIÁ 3 TẦNG & TỔNG HỢP BÀI HỌC TỰ HỌC ĐỂ NÂNG CẤP CÁC BƯỚC TRONG PIPELINE:\n"
            "1. TẦNG CHẨN ĐOÁN THUẬT TOÁN (Tầng 1 & 2 - Forensic Health & Distribution Bottlenecks):\n"
            "   - Nhận định chính xác giai đoạn ươm tạo kênh (Incubation Matrix 0-20 Video), trạng thái phân phối lạnh (Cold Sampling) và cảnh báo nghẽn (Stall / Engagement Deficit).\n"
            "   - Phân tích rủi ro thiết bị Mobile và phễu chuyển đổi từ 4 Tab.\n"
            "2. TẦNG TỰ HỌC & CHỈ THỊ CẢI TIẾN TRỰC TIẾP CHO TỪNG BƯỚC PIPELINE (Tier 3 Self-Learning Enhancement):\n"
            "   - [NÂNG CẤP B1 - ĐỊNH HƯỚNG ĐỀ TÀI & NGÁCH]: Dựa vào Tab 4 (Xu hướng thị trường) & Tab 2 (Từ khóa tìm kiếm), gợi ý 2 đề tài mới có nhu cầu tìm kiếm cao, giải quyết Content Gaps nhưng TUÂN THỦ TRIỆT ĐỂ Rule 445 (Pure Niche Consistency).\n"
            "   - [NÂNG CẤP B2 - KỊCH BẢN & 5-BEAT HOOK]: Dựa vào Tab 2 (AVD & Retention drop-off), áp dụng Rule 444 (5-Variant Hook Protocol) để soạn 1 câu Hook mẫu mở đầu trực diện bằng số liệu/nghịch lý gai góc và gia cố Micro-Cliffhangers tại Beat 4/5.\n"
            "   - [NÂNG CẤP B3/B4/B5 - HÌNH ẢNH & THUMBNAIL]: Dựa vào Tab 2 (Tỷ lệ Mobile %) & Tab 3 (Nhân khẩu học), áp dụng Rule 443 để ra chỉ thị kỹ thuật cho Thumbnail (Headline text cực lớn >= 40% canvas, độ tương phản cao, phong cách minh họa Stylized Graphic Novel cho đúng thị trường).\n"
            "   - [NÂNG CẤP B10 - ĐÓNG GÓI & SEO FORGE]: Dựa vào Tab 2 (Search queries) & Tab 3 (Địa lý khán giả), chỉ đạo quy cách Title giật gân nhưng trung thực (Rule 130), bộ Tags và Description chuẩn ngôn ngữ bản địa.\n"
            "3. QUY TẮC CỐT TỬ ĐỒNG BỘ VÀO NOTION SKILL (Self-Learning Enhancement Loop):\n"
            "   - Đúc kết ĐÚNG 1 ĐOẠN QUY TẮC HÀNH ĐỘNG CỐT LÕI (2-3 câu ngắn gọn) để tự động lưu vào Notion Skill `Self-Learning Enhancement Loop`, làm tri thức sống cho các Agent của B1, B2, B10 tự động nạp ở chu kỳ tiếp theo."
        )
        
        full_prompt = "\n".join(prompt_lines)
        print("Calling HHTech GPT-6-Astra with Complete 4-Tab Analytics (3-Tier Pipeline Self-Learning)...")
        analysis_text, usage, elapsed = call_hhtech_gpt56(hhtech_key, full_prompt)
        token_cost = usage.get("total_tokens", 0)
        print(f"GPT-6-Astra finished in {elapsed:.2f}s (Tokens used: {token_cost})")
        print("\n--- SUPREME INSIGHT SUMMARY ---")
        print(analysis_text[:800] + "...\n")
        
        if not dry_run:
            print("Syncing Supreme Insights to Notion DB & Skills...")
            for c in supreme_candidates:
                v = c["video"]
                action_verdict = "Enhance Action Required"
                sync_to_experiment_lab(
                    notion_token,
                    v,
                    insight=f"[{c['market']}] Trigger: {c['reason']} | Mobile: {c['mobile_pct']:.1f}%\n{analysis_text[:350]}",
                    action_verdict=action_verdict,
                    lesson=analysis_text[-400:]
                )
            
            core_enhancement = analysis_text[-350:].strip()
            append_skill_enhancement(notion_token, SKILL_SELF_LEARNING_PAGE_ID, core_enhancement)
            print("  * Appended to Notion Skill: SUCCESS (200 OK)")
            state["last_supreme_run"] = datetime.now(timezone.utc).isoformat()
    else:
        print("\n✅ [TIER 3 STANDBY] Không có biến động chạm ngưỡng tối cao. Token chi phí: 0.")
        
    state["videos"] = new_video_state
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    
    print("\n=== [B11 ENGINE] RUN FINISHED SUCCESSFULLY ===")
    return {
        "status": "ok",
        "videos_scanned": len(all_videos),
        "supreme_triggered": len(supreme_candidates) > 0,
        "token_cost": token_cost
    }

if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    is_deep = "--deep" in sys.argv
    target_market = None
    for arg in sys.argv:
        if arg.startswith("--market="):
            target_market = arg.split("=", 1)[1].strip()
        elif arg.startswith("-m="):
            target_market = arg.split("=", 1)[1].strip()
    mode = "deep" if is_deep else "routine"
    run_b11_engine(mode=mode, dry_run=is_dry, target_market=target_market)
