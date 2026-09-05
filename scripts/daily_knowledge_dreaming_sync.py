#!/usr/bin/env python3
"""Daily Knowledge Dreaming & YouTube Analytics Sync (daily_knowledge_dreaming_sync.py)
Automated daily synchronization & self-feedback learning loop for VF Pipeline.
Complies with Rule 113 (The 48-Hour Law), Rule 114 (/youtube:growth-engine), and Rule 115 (/analytics:knowledge-dreaming).
Complies with Rule 118 (Zero-Mock Data) -> NO SIMULATED VALUES, DIRECT YOUTUBE API FETCH.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone, timedelta

sys.path.insert(0, '/root/video_factory')
sys.path.insert(0, '/root/video_factory/scripts')

import ag_notion_bridge as br
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('vf.knowledge_dreaming')

EXPERIMENT_LAB_DB_ID = '76601989-2400-838f-ad45-816777c57ffd'

def _load_env(path="/root/secrets/.env"):
    if not os.path.exists(path): return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            k, _, v = line.partition("=")
            if k and k not in os.environ:
                os.environ[k.strip()] = v.strip().strip(chr(34)).strip(chr(39))

def get_yt_clients(market="en"):
    _load_env()
    su = market.upper()
    refresh = os.environ.get(f"{su}_YT_OAUTH_REFRESH_TOKEN") or os.environ.get("YT_OAUTH_REFRESH_TOKEN", "")
    cid = os.environ.get(f"{su}_YT_OAUTH_CLIENT_ID") or os.environ.get("YT_OAUTH_CLIENT_ID", "")
    csec = os.environ.get(f"{su}_YT_OAUTH_CLIENT_SECRET") or os.environ.get("YT_OAUTH_CLIENT_SECRET", "")
    
    if not refresh: return None, None
    creds = Credentials(
        token=None,
        refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cid,
        client_secret=csec,
    )
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    yt_ana = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
    return yt, yt_ana

def fetch_actual_analytics(yt, yt_ana, video_id):
    # Data API (Views, Likes, Comments)
    stats = {'views': None, 'likes': None, 'comments': None, 'ctr': None, 'avd': None, 'status': 'private', 'published_at': None, 'title': ''}
    try:
        resp = yt.videos().list(part="statistics,status,snippet", id=video_id).execute()
        if resp.get("items"):
            item = resp["items"][0]
            s = item.get("statistics", {})
            st = item.get("status", {})
            sn = item.get("snippet", {})
            stats['views'] = int(s.get("viewCount", 0)) if "viewCount" in s else 0
            stats['likes'] = int(s.get("likeCount", 0)) if "likeCount" in s else 0
            stats['comments'] = int(s.get("commentCount", 0)) if "commentCount" in s else 0
            stats['status'] = st.get("privacyStatus", "private")
            stats['published_at'] = sn.get("publishedAt")
            stats['title'] = sn.get("title", "")
    except Exception as e:
        logger.error(f"Error fetching Data API for {video_id}: {e}")
        
    # Analytics API (CTR, AVD)
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
    try:
        # Note: annotationClickThroughRate might require specific permissions or video dimensions, using basic if needed
        ana_resp = yt_ana.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="annotationClickThroughRate,averageViewDuration",
            dimensions="video",
            filters=f"video=={video_id}"
        ).execute()
        rows = ana_resp.get("rows", [])
        if rows:
            # CTR is ratio (e.g. 0.05 -> 5%)
            stats['ctr'] = float(rows[0][1]) * 100.0 if rows[0][1] is not None else None
            stats['avd'] = float(rows[0][2]) if rows[0][2] is not None else None
    except Exception as e:
        logger.warning(f"Analytics API not available or empty for {video_id}: {e}")
        
    return stats

def run_daily_sync():
    logger.info('=== Starting Daily Knowledge Dreaming Sync (Direct YT Fetch) ===')
    yt, yt_ana = get_yt_clients("en")
    if not yt:
        logger.error("No YouTube credentials found. Aborting.")
        return False
        
    # Get latest uploads
    try:
        resp = yt.channels().list(part="contentDetails", mine=True).execute()
        uploads_id = resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        pl = yt.playlistItems().list(part="snippet", playlistId=uploads_id, maxResults=10).execute()
        videos = [item["snippet"]["resourceId"]["videoId"] for item in pl.get("items", [])]
    except Exception as e:
        logger.error(f"Error fetching uploads: {e}")
        return False
        
    logger.info(f'Found {len(videos)} recent videos on YouTube channel.')
    
    for video_id in videos:
        stats = fetch_actual_analytics(yt, yt_ana, video_id)
        status = stats['status']
        title = stats['title']
        published_at_str = stats['published_at']
        if not published_at_str:
            continue
            
        try:
            created_dt = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
        except ValueError:
            created_dt = datetime.now(timezone.utc)
            
        hours_since = (datetime.now(timezone.utc) - created_dt).total_seconds() / 3600.0
        
        logger.info(f'Processing {video_id} (Hours: {hours_since:.1f}h, Status: {status}) - Views: {stats["views"]}')
        
        # 2. Evaluate 48-Hour Law
        if hours_since < 48.0 or status != 'public':
            state_stage = 'Sampling State (<48h)'
            action_verdict = 'Keep Current'
            insight = f'Episode in 48-Hour initial sampling window ({hours_since:.1f}h). YouTube is exploring random cohorts; metadata locked to prevent distribution cycle reset.'
            learned = 'Rule 113 & 115 Compliance: Do not edit packaging during sampling noise period. Title & Thumbnail B are staged in registry.'
            kd_status = 'Collected'
            # Rule 118: Mask stats if still sampling to avoid premature decisions
            v_views = None
            v_ctr = None
            v_avd = None
            v_comments = None
            v_likes = None
        else:
            state_stage = 'Diagnosis Active (>=48h)'
            # We now have real stats (if any)
            if stats['views'] is not None and stats['views'] > 0:
                insight = f"Direct fetch from YT Studio. Views: {stats['views']}"
                learned = "Actual analytics fetched via YouTube API."
            else:
                insight = 'Chưa có đủ dữ liệu Analytics thực tế từ YouTube Studio (Views=0 or None)'
                learned = 'No analytics available to form a diagnosis yet.'
            
            action_verdict = 'Keep Current'
            kd_status = 'Collected'
            
            # Use actual data
            v_views = stats['views']
            v_ctr = stats['ctr']
            v_avd = stats['avd']
            v_comments = stats['comments']
            v_likes = stats['likes']
            
        market = 'EN'
        ep_id = title[:15] + "..." if len(title) > 15 else title
        
        # 3. Update or Insert into Experiment Lab DB
        lab_res = br.query_db(EXPERIMENT_LAB_DB_ID, filter_obj={
            'property': 'Video ID',
            'rich_text': {'equals': video_id}
        })
        
        lab_props = {
            'Name': {'title': [{'type': 'text', 'text': {'content': f'{title} · Diagnosis'}}]},
            'Episode ID': {'rich_text': [{'type': 'text', 'text': {'content': title}}]},
            'Market': {'select': {'name': market}},
            'Video ID': {'rich_text': [{'type': 'text', 'text': {'content': video_id}}]},
            'Platform': {'select': {'name': 'YouTube'}},
            'State Stage': {'select': {'name': state_stage}},
            'Action Verdict': {'select': {'name': action_verdict}},
            'Insight': {'rich_text': [{'type': 'text', 'text': {'content': insight}}]},
            'Learned Rules & Insights': {'rich_text': [{'type': 'text', 'text': {'content': learned}}]},
            'Status': {'status': {'name': kd_status}},
            # Real data
            'Views': {'number': v_views},
            'CTR %': {'number': v_ctr},
            'AVD %': {'number': v_avd},
            'Comments': {'number': v_comments},
            'Likes': {'number': v_likes},
        }
        
        lab_rows = lab_res.get('results', [])
        if lab_rows:
            page_id = lab_rows[0]['id']
            logger.info(f'Updating existing Experiment Lab record: {page_id}')
            up_res = br.update_page_properties(page_id, lab_props)
            if up_res.get("error"): logger.error(f"Notion update error: {up_res}")
        else:
            logger.info(f'Creating new Experiment Lab record for {video_id}')
            cr_res = br.create_page(EXPERIMENT_LAB_DB_ID, lab_props)
            if cr_res.get("error"): logger.error(f"Notion create error: {cr_res}")

    logger.info('=== Daily Knowledge Dreaming Sync Completed Successfully ===')
    return True

if __name__ == '__main__':
    run_daily_sync()
