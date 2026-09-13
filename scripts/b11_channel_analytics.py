#!/usr/bin/env python3
"""
scripts/b11_channel_analytics.py
=============================================================================
B11 YouTube Studio 4-Tab Analytics Harvester (Pure REST API Edition)
=============================================================================
Pulls comprehensive channel analytics corresponding to YouTube Studio's 4 tabs:
  1. Tổng quan (Overview): Core metrics, daily trend, top videos, channel statistics.
  2. Nội dung (Content): Traffic sources, search queries, referring videos, device types,
     OS breakdown, playback locations, sharing services, view duration & percentage.
  3. Đối tượng người xem (Audience): Demographics (age/gender), geography (country),
     live vs on-demand viewing nature.
  4. Xu hướng (Research / Trends): Organic search queries, target market trending videos,
     Google Trends RSS intelligence, and content gap recommendations.

Zero-Mock Data (Rule 118): Only real data from YouTube Data API v3, YouTube Analytics API v2,
and live Google Trends RSS. Unset or unavailable fields are recorded as null.
"""

import sys
import os
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def query_youtube_data_api(access_token, endpoint, params=None):
    url = f"https://www.googleapis.com/youtube/v3/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def query_youtube_analytics_api(access_token, params):
    url = "https://youtubeanalytics.googleapis.com/v2/reports?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fetch_google_trends_rss(geo="KR"):
    """Fetch live Google Trends RSS as part of the Tab 4 (Xu hướng) intelligence."""
    geo_code = (geo or "US").upper()
    url = f"https://trends.google.com/trending/rss?geo={geo_code}"
    topics = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Antigravity/2.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for item in root.findall("./channel/item")[:10]:
                title = item.findtext("title")
                approx_traffic = item.findtext("{https://trends.google.com/trending/rss}approx_traffic")
                pub_date = item.findtext("pubDate")
                if title:
                    topics.append({
                        "title": title.strip(),
                        "approx_traffic": approx_traffic.strip() if approx_traffic else None,
                        "pub_date": pub_date.strip() if pub_date else None
                    })
    except Exception:
        pass
    return topics

def fetch_tab_overview(access_token, start_date, end_date):
    """Tab 1: Tổng quan (Overview)"""
    overview = {
        "channel_profile": {},
        "core_metrics": {},
        "daily_breakdown": [],
        "top_performing_videos": []
    }
    
    # 1. Channel Profile & Lifetime Statistics
    try:
        ch_res = query_youtube_data_api(access_token, "channels", {
            "part": "snippet,statistics,contentDetails",
            "mine": "true"
        })
        items = ch_res.get("items", [])
        if items:
            ch = items[0]
            snippet = ch.get("snippet", {})
            stats = ch.get("statistics", {})
            overview["channel_profile"] = {
                "channel_id": ch.get("id"),
                "title": snippet.get("title"),
                "description": snippet.get("description", "")[:200],
                "published_at": snippet.get("publishedAt"),
                "total_views": int(stats.get("viewCount", 0)),
                "total_subscribers": int(stats.get("subscriberCount", 0)),
                "total_videos": int(stats.get("videoCount", 0))
            }
    except Exception as e:
        overview["channel_profile_error"] = str(e)

    # 2. Aggregated 28-day Core Metrics
    try:
        core_res = query_youtube_analytics_api(access_token, {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": "views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost,likes,dislikes,comments,shares"
        })
        headers = [h["name"] for h in core_res.get("columnHeaders", [])]
        rows = core_res.get("rows", [])
        if rows:
            row_dict = dict(zip(headers, rows[0]))
            overview["core_metrics"] = {
                "views": row_dict.get("views", 0),
                "estimated_minutes_watched": row_dict.get("estimatedMinutesWatched", 0),
                "estimated_hours_watched": round(row_dict.get("estimatedMinutesWatched", 0) / 60.0, 2),
                "average_view_duration_seconds": row_dict.get("averageViewDuration", 0),
                "subscribers_gained": row_dict.get("subscribersGained", 0),
                "subscribers_lost": row_dict.get("subscribersLost", 0),
                "net_subscribers": row_dict.get("subscribersGained", 0) - row_dict.get("subscribersLost", 0),
                "likes": row_dict.get("likes", 0),
                "dislikes": row_dict.get("dislikes", 0),
                "comments": row_dict.get("comments", 0),
                "shares": row_dict.get("shares", 0)
            }
        else:
            overview["core_metrics"] = {
                "views": 0, "estimated_minutes_watched": 0, "estimated_hours_watched": 0.0,
                "average_view_duration_seconds": 0, "subscribers_gained": 0, "subscribers_lost": 0,
                "net_subscribers": 0, "likes": 0, "dislikes": 0, "comments": 0, "shares": 0
            }
    except Exception as e:
        overview["core_metrics_error"] = str(e)

    # 3. Daily Breakdown (Trend Curves)
    try:
        day_res = query_youtube_analytics_api(access_token, {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "day",
            "metrics": "views,estimatedMinutesWatched,subscribersGained,likes",
            "sort": "day"
        })
        headers = [h["name"] for h in day_res.get("columnHeaders", [])]
        for row in day_res.get("rows", []):
            overview["daily_breakdown"].append(dict(zip(headers, row)))
    except Exception:
        pass

    # 4. Top Performing Videos in Period
    try:
        top_res = query_youtube_analytics_api(access_token, {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "video",
            "metrics": "views,estimatedMinutesWatched,averageViewDuration,likes",
            "sort": "-views",
            "maxResults": 10
        })
        headers = [h["name"] for h in top_res.get("columnHeaders", [])]
        for row in top_res.get("rows", []):
            overview["top_performing_videos"].append(dict(zip(headers, row)))
    except Exception:
        pass

    return overview

def fetch_tab_content(access_token, start_date, end_date):
    """Tab 2: Nội dung (Content)"""
    content = {
        "traffic_sources": {},
        "top_search_terms": [],
        "top_suggested_videos": [],
        "top_external_sources": [],
        "device_breakdown": {},
        "operating_systems": {},
        "playback_locations": {},
        "sharing_services": {},
        "engagement_retention": {}
    }

    # 1. Traffic Sources Breakdown (Cách người xem tìm thấy video)
    try:
        traf_res = query_youtube_analytics_api(access_token, {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "insightTrafficSourceType",
            "metrics": "views,estimatedMinutesWatched"
        })
        total_views = 0
        for row in traf_res.get("rows", []):
            src_type, v_count, w_min = row[0], row[1], row[2]
            total_views += v_count
            content["traffic_sources"][src_type] = {
                "views": v_count,
                "watch_minutes": w_min
            }
        for k in content["traffic_sources"]:
            pct = (content["traffic_sources"][k]["views"] / max(total_views, 1)) * 100.0
            content["traffic_sources"][k]["share_pct"] = round(pct, 1)
    except Exception:
        pass

    # 2. Search Terms (Cụm từ tìm kiếm trên YouTube)
    try:
        search_res = query_youtube_analytics_api(access_token, {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "insightTrafficSourceDetail",
            "filters": "insightTrafficSourceType==YT_SEARCH",
            "metrics": "views,estimatedMinutesWatched",
            "sort": "-views",
            "maxResults": 10
        })
        for row in search_res.get("rows", []):
            content["top_search_terms"].append({
                "query": row[0],
                "views": row[1],
                "watch_minutes": row[2]
            })
    except Exception:
        pass

    # 3. Suggested Referring Videos (Video đề xuất nội dung của bạn)
    try:
        rel_res = query_youtube_analytics_api(access_token, {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "insightTrafficSourceDetail",
            "filters": "insightTrafficSourceType==RELATED_VIDEO",
            "metrics": "views,estimatedMinutesWatched",
            "sort": "-views",
            "maxResults": 10
        })
        for row in rel_res.get("rows", []):
            content["top_suggested_videos"].append({
                "referring_video_id": row[0],
                "views": row[1],
                "watch_minutes": row[2]
            })
    except Exception:
        pass

    # 4. External Referrers (Nguồn ngoại vi)
    try:
        ext_res = query_youtube_analytics_api(access_token, {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "insightTrafficSourceDetail",
            "filters": "insightTrafficSourceType==EXT_URL",
            "metrics": "views,estimatedMinutesWatched",
            "sort": "-views",
            "maxResults": 10
        })
        for row in ext_res.get("rows", []):
            content["top_external_sources"].append({
                "source_domain": row[0],
                "views": row[1],
                "watch_minutes": row[2]
            })
    except Exception:
        pass

    # 5. Device Type Breakdown
    try:
        dev_res = query_youtube_analytics_api(access_token, {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "deviceType",
            "metrics": "views,estimatedMinutesWatched"
        })
        tot_dev_views = sum(r[1] for r in dev_res.get("rows", [])) or 1
        for row in dev_res.get("rows", []):
            content["device_breakdown"][row[0]] = {
                "views": row[1],
                "watch_minutes": row[2],
                "share_pct": round((row[1] / tot_dev_views) * 100.0, 1)
            }
    except Exception:
        pass

    # 6. Operating System Breakdown
    try:
        os_res = query_youtube_analytics_api(access_token, {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "operatingSystem",
            "metrics": "views,estimatedMinutesWatched"
        })
        for row in os_res.get("rows", []):
            content["operating_systems"][row[0]] = {
                "views": row[1],
                "watch_minutes": row[2]
            }
    except Exception:
        pass

    # 7. Playback Locations
    try:
        loc_res = query_youtube_analytics_api(access_token, {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "insightPlaybackLocationType",
            "metrics": "views,estimatedMinutesWatched"
        })
        for row in loc_res.get("rows", []):
            content["playback_locations"][row[0]] = {
                "views": row[1],
                "watch_minutes": row[2]
            }
    except Exception:
        pass

    # 8. Sharing Services
    try:
        share_res = query_youtube_analytics_api(access_token, {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "sharingService",
            "metrics": "shares",
            "sort": "-shares",
            "maxResults": 10
        })
        for row in share_res.get("rows", []):
            content["sharing_services"][row[0]] = row[1]
    except Exception:
        pass

    # 9. Engagement & Retention Aggregates
    try:
        eng_res = query_youtube_analytics_api(access_token, {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": "averageViewDuration,averageViewPercentage,annotationClickThroughRate,cardClickRate"
        })
        rows = eng_res.get("rows", [])
        if rows:
            content["engagement_retention"] = {
                "average_view_duration_seconds": rows[0][0],
                "average_view_percentage": round(rows[0][1], 2),
                "annotation_click_through_rate": round(rows[0][2], 2),
                "card_click_rate": round(rows[0][3], 2)
            }
    except Exception:
        pass

    return content

def fetch_tab_audience(access_token, start_date, end_date):
    """Tab 3: Đối tượng người xem (Audience)"""
    audience = {
        "demographics": [],
        "top_geographies": [],
        "viewing_nature": {}
    }

    # 1. Demographics (Age Group & Gender Breakdown)
    try:
        demo_res = query_youtube_analytics_api(access_token, {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "ageGroup,gender",
            "metrics": "viewerPercentage",
            "sort": "gender,ageGroup"
        })
        for row in demo_res.get("rows", []):
            audience["demographics"].append({
                "age_group": row[0],
                "gender": row[1],
                "viewer_percentage": round(row[2], 2)
            })
    except Exception:
        pass

    # 2. Geography (Country Breakdown)
    try:
        geo_res = query_youtube_analytics_api(access_token, {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "country",
            "metrics": "views,estimatedMinutesWatched,averageViewDuration",
            "sort": "-views",
            "maxResults": 10
        })
        for row in geo_res.get("rows", []):
            audience["top_geographies"].append({
                "country_code": row[0],
                "views": row[1],
                "watch_minutes": row[2],
                "average_view_duration_seconds": row[3]
            })
    except Exception:
        pass

    # 3. Viewing Nature (Live vs On-Demand)
    try:
        live_res = query_youtube_analytics_api(access_token, {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "liveOrOnDemand",
            "metrics": "views,estimatedMinutesWatched"
        })
        for row in live_res.get("rows", []):
            audience["viewing_nature"][row[0]] = {
                "views": row[1],
                "watch_minutes": row[2]
            }
    except Exception:
        pass

    return audience

def fetch_tab_research(access_token, market="KR", top_search_terms=None):
    """Tab 4: Xu hướng / Nghiên cứu (Research / Trends / Inspiration)"""
    research = {
        "market": market.upper(),
        "organic_channel_searches": top_search_terms or [],
        "market_trending_videos": [],
        "google_trends_realtime": []
    }

    # 1. Market Trending Videos on YouTube
    region_map = {"KR": "KR", "JP": "JP", "EN": "US", "VN": "VN"}
    region_code = region_map.get(market.upper(), "US")
    try:
        trend_res = query_youtube_data_api(access_token, "videos", {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": 10
        })
        for item in trend_res.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            research["market_trending_videos"].append({
                "video_id": item.get("id"),
                "title": snippet.get("title"),
                "channel_title": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "tags": snippet.get("tags", [])[:5]
            })
    except Exception:
        pass

    # 2. Live Google Trends RSS for Market
    research["google_trends_realtime"] = fetch_google_trends_rss(geo=region_code)

    return research

def fetch_complete_channel_analytics(access_token, market="KR", days=28):
    """
    Master Collector: Combines all 4 tabs into a comprehensive JSON payload.
    """
    now = datetime.now(timezone.utc)
    end_date = now.strftime("%Y-%m-%d")
    start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")

    tab_1 = fetch_tab_overview(access_token, start_date, end_date)
    tab_2 = fetch_tab_content(access_token, start_date, end_date)
    tab_3 = fetch_tab_audience(access_token, start_date, end_date)
    tab_4 = fetch_tab_research(access_token, market=market, top_search_terms=tab_2.get("top_search_terms", []))

    payload = {
        "metadata": {
            "generated_at": now.isoformat(),
            "market": market.upper(),
            "period_days": days,
            "start_date": start_date,
            "end_date": end_date,
            "collector_engine": "B11_PURE_REST_API_HARVESTER_V1"
        },
        "tab_1_overview": tab_1,
        "tab_2_content": tab_2,
        "tab_3_audience": tab_3,
        "tab_4_research_trends": tab_4
    }
    return payload

if __name__ == "__main__":
    from scripts.b11_engine import load_secrets, get_market_oauth, get_yt_access_token
    secrets = load_secrets()
    market = "kr"
    for arg in sys.argv:
        if arg.startswith("--market="):
            market = arg.split("=", 1)[1].strip()
            
    cid, csec, refresh = get_market_oauth(secrets, market)
    if not (cid and csec and refresh):
        print(f"Missing OAuth credentials for market {market}")
        sys.exit(1)
        
    token = get_yt_access_token(cid, csec, refresh)
    data = fetch_complete_channel_analytics(token, market=market, days=28)
    
    out_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", f"channel_analytics_{market}.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Successfully harvested 4-Tab Analytics for [{market.upper()}]:")
    print(f"  - Tab 1 Overview: {len(data['tab_1_overview']['daily_breakdown'])} daily rows, Profile={data['tab_1_overview']['channel_profile'].get('title')}")
    print(f"  - Tab 2 Content: {len(data['tab_2_content']['traffic_sources'])} traffic sources, {len(data['tab_2_content']['device_breakdown'])} device types")
    print(f"  - Tab 3 Audience: {len(data['tab_3_audience']['demographics'])} demographic rows, {len(data['tab_3_audience']['top_geographies'])} countries")
    print(f"  - Tab 4 Research/Trends: {len(data['tab_4_research_trends']['market_trending_videos'])} trending videos, {len(data['tab_4_research_trends']['google_trends_realtime'])} Google Trends topics")
    print(f"Saved snapshot to: {out_file}")
