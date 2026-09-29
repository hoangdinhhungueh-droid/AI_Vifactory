# -*- coding: utf-8 -*-
"""
Smart Multi-Market Cross-Channel Promotion Engine (cross_channel_promoter.py).
Part of AI Video Factory Pipeline (Step B10 YouTube Post-Upload Stage).

Implements Phương án A (White-Hat Smart Cross-Channel Ecosystem):
  1. Tầng 1 (Cross-Playlists): Tự động thêm video mới vào Playlist chủ đề quốc tế
     của các kênh đối tác (EN ⇄ JP ⇄ KR) thông qua YouTube Data API v3 chính thống.
  2. Tầng 2 (Multi-Language Description Bridge): Tự động chèn liên kết mạng lưới kênh
     quốc tế chính thức vào phần chân trang của YouTube Description.
  3. Tầng 3 (Featured Channels Showcase): Tự động cấu hình mục "Official Global Network"
     (Channel Section type=multipleChannels) trên tab Trang chủ của các kênh.

Compliance & Anti-Bot Protection:
  - 100% sử dụng Google OAuth 2.0 & YouTube Data API v3 (google-api-python-client).
  - TUYỆT ĐỐI KHÔNG dùng headless browser, bot view chéo, bot click farm (Zero Fake Engagement).
  - Ngăn ngừa hiện tượng Audience Poisoning: Không ép view chéo thô bạo giữa các ngôn ngữ;
    chỉ phân phối qua Playlist chủ đề quốc tế và Featured Channels minh bạch.
"""
from __future__ import annotations

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("vf.cross_channel_promoter")

SUPPORTED_MARKETS = ["EN", "JP", "KR"]

# Cấu hình Playlist quốc tế trên từng kênh đối tác
PARTNER_PLAYLIST_SPECS: Dict[str, Dict[str, str]] = {
    "EN": {
        "title": "Global Investigative Docudramas (Worldwide Cases)",
        "description": (
            "Curated investigative docudramas and systemic case studies produced by our "
            "international research network across English, Japanese, and Korean desks."
        ),
        "tags": ["investigative documentary", "global cases", "docudrama", "unfiltered facts"],
    },
    "JP": {
        "title": "世界を揺るがした調査報道・未解決ドキュメンタリー (Global Cases)",
        "description": (
            "日米韓の共同取材ネットワークが解き明かす、世界の金融スキャンダル・"
            "未解決事件・構造的汚職の深層記録。"
        ),
        "tags": ["調査報道", "未解決事件", "ドキュメンタリー", "世界事件"],
    },
    "KR": {
        "title": "글로벌 심층 탐사 다큐멘터리 (Global Investigations)",
        "description": (
            "한·미·일 글로벌 취재 네트워크가 추적하는 세계적인 금융 스캔들과 은폐된 사건의 진실."
        ),
        "tags": ["탐사다큐", "글로벌이슈", "심층취재", "사건기록"],
    },
}

# Thông tin định danh kênh (Handle / Channel ID) có thể override qua ENV
DEFAULT_CHANNEL_PROFILES: Dict[str, Dict[str, str]] = {
    "EN": {
        "name": "AI Video Factory (Global EN)",
        "handle": "@AIVideoFactory_EN",
        "url": "https://www.youtube.com/@AIVideoFactory_EN",
        "env_channel_id": "EN_YT_CHANNEL_ID",
    },
    "JP": {
        "name": "AI Video Factory (日本語版)",
        "handle": "@AIVideoFactory_JP",
        "url": "https://www.youtube.com/@AIVideoFactory_JP",
        "env_channel_id": "JP_YT_CHANNEL_ID",
    },
    "KR": {
        "name": "AI Video Factory (한국어판)",
        "handle": "@AIVideoFactory_KR",
        "url": "https://www.youtube.com/@AIVideoFactory_KR",
        "env_channel_id": "KR_YT_CHANNEL_ID",
    },
}


def _get_cache_path() -> Path:
    candidates = [
        Path("/var/vf/data/cross_playlists_cache.json"),
        Path(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cross_playlists_cache.json")),
    ]
    for c in candidates:
        if c.parent.exists():
            return c
    return candidates[-1]


def _get_ledger_path() -> Path:
    candidates = [
        Path("/var/vf/data/cross_promotion_ledger.json"),
        Path(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cross_promotion_ledger.json")),
    ]
    for c in candidates:
        if c.parent.exists():
            return c
    return candidates[-1]


def _load_cache() -> Dict[str, Any]:
    cp = _get_cache_path()
    if cp.exists():
        try:
            return json.loads(cp.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("[cross_channel_promoter] Failed reading cache: %s", e)
    return {}


def _save_cache(data: Dict[str, Any]) -> None:
    cp = _get_cache_path()
    try:
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("[cross_channel_promoter] Failed saving cache: %s", e)


def _load_ledger() -> List[Dict[str, Any]]:
    lp = _get_ledger_path()
    if lp.exists():
        try:
            res = json.loads(lp.read_text(encoding="utf-8"))
            if isinstance(res, list):
                return res
        except Exception:
            pass
    return []


def _record_ledger_entry(entry: Dict[str, Any]) -> None:
    lp = _get_ledger_path()
    try:
        lp.parent.mkdir(parents=True, exist_ok=True)
        ledger = _load_ledger()
        ledger.append(entry)
        lp.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("[cross_channel_promoter] Failed writing ledger: %s", e)


def get_channel_profile(market: str) -> Dict[str, str]:
    """Retrieve public metadata profile for a given market channel."""
    m = market.upper().strip()
    profile = dict(DEFAULT_CHANNEL_PROFILES.get(m, DEFAULT_CHANNEL_PROFILES["EN"]))
    env_id_key = profile.get("env_channel_id", "")
    ch_id = os.environ.get(env_id_key, "")
    if ch_id:
        profile["channel_id"] = ch_id
        profile["url"] = f"https://www.youtube.com/channel/{ch_id}"
    return profile


def build_description_bridge(source_market: str) -> str:
    """Tầng 2: Multi-Language Description Bridge.
    Builds a non-spammy, authoritative sister-channel footer for YouTube video descriptions.
    """
    m = (source_market or "EN").upper().strip()
    partner_markets = [pm for pm in SUPPORTED_MARKETS if pm != m]

    lines = [
        "────────────────────────────────────────",
    ]

    if m == "JP":
        lines.append("🌐 公式グローバルネットワーク (Official Global Network):")
        for pm in partner_markets:
            prof = get_channel_profile(pm)
            label = "English Edition" if pm == "EN" else "韓国語版 (Korean Edition)"
            lines.append(f"• {label}: {prof['url']}")
    elif m == "KR":
        lines.append("🌐 공식 글로벌 취재 네트워크 (Official Global Network):")
        for pm in partner_markets:
            prof = get_channel_profile(pm)
            label = "English Edition" if pm == "EN" else "일본어판 (Japanese Edition)"
            lines.append(f"• {label}: {prof['url']}")
    else:  # EN or other
        lines.append("🌐 Official Global Investigation Network:")
        for pm in partner_markets:
            prof = get_channel_profile(pm)
            label = "Japanese Edition (日本語版)" if pm == "JP" else "Korean Edition (한국어판)"
            lines.append(f"• {label}: {prof['url']}")

    lines.append("────────────────────────────────────────")
    return "\n".join(lines)


def get_or_create_partner_playlist(partner_market: str, youtube_client=None) -> Dict[str, Any]:
    """Tầng 1 Helper: Locate or create the curated cross-promotion playlist on the partner channel."""
    pm = partner_market.upper().strip()
    spec = PARTNER_PLAYLIST_SPECS.get(pm, PARTNER_PLAYLIST_SPECS["EN"])
    target_title = spec["title"]

    cache = _load_cache()
    cached_id = cache.get(pm, {}).get("playlist_id")

    if youtube_client is None:
        try:
            from app.services.youtube_upload import _build_client
            youtube_client = _build_client(market=pm)
        except Exception as e:
            logger.warning("[cross_channel_promoter] Cannot build client for partner %s: %s", pm, e)
            return {"status": "client_error", "market": pm, "error": str(e), "playlist_id": cached_id}

    # 1. Verify cached playlist ID if present
    if cached_id:
        try:
            chk = youtube_client.playlists().list(part="id,snippet", id=cached_id).execute()
            if chk.get("items"):
                return {"status": "cached", "market": pm, "playlist_id": cached_id, "title": target_title}
        except Exception as e:
            logger.info("[cross_channel_promoter] Cached playlist %s no longer valid on %s: %s", cached_id, pm, e)

    # 2. Search existing playlists on the channel
    try:
        req = youtube_client.playlists().list(part="id,snippet", mine=True, maxResults=50)
        resp = req.execute()
        for item in resp.get("items", []):
            snippet = item.get("snippet", {})
            if snippet.get("title", "").strip().lower() == target_title.strip().lower():
                found_id = item["id"]
                cache.setdefault(pm, {})["playlist_id"] = found_id
                cache[pm]["title"] = target_title
                cache[pm]["updated_at"] = datetime.now(timezone.utc).isoformat()
                _save_cache(cache)
                return {"status": "found_existing", "market": pm, "playlist_id": found_id, "title": target_title}
    except Exception as e:
        logger.warning("[cross_channel_promoter] Error listing playlists on %s: %s", pm, e)

    # 3. Create the playlist if not found
    try:
        body = {
            "snippet": {
                "title": target_title,
                "description": spec["description"],
                "tags": spec.get("tags", []),
            },
            "status": {
                "privacyStatus": "public",
            },
        }
        create_req = youtube_client.playlists().insert(part="snippet,status", body=body)
        created = create_req.execute()
        new_id = created.get("id")
        cache.setdefault(pm, {})["playlist_id"] = new_id
        cache[pm]["title"] = target_title
        cache[pm]["created_at"] = datetime.now(timezone.utc).isoformat()
        _save_cache(cache)
        logger.info("[cross_channel_promoter] Created new cross-promotion playlist '%s' on %s: %s", target_title, pm, new_id)
        return {"status": "created", "market": pm, "playlist_id": new_id, "title": target_title}
    except Exception as e:
        logger.error("[cross_channel_promoter] Failed creating playlist on %s: %s", pm, e)
        return {"status": "create_error", "market": pm, "error": str(e), "playlist_id": None}


def add_video_to_partner_playlist(
    video_id: str,
    partner_market: str,
    playlist_id: Optional[str] = None,
    youtube_client=None,
) -> Dict[str, Any]:
    """Tầng 1 Core: Adds a newly uploaded video into a partner channel's playlist."""
    pm = partner_market.upper().strip()
    if not playlist_id:
        p_info = get_or_create_partner_playlist(pm, youtube_client=youtube_client)
        playlist_id = p_info.get("playlist_id")

    if not playlist_id:
        return {"status": "skipped_no_playlist", "partner_market": pm, "video_id": video_id}

    if youtube_client is None:
        try:
            from app.services.youtube_upload import _build_client
            youtube_client = _build_client(market=pm)
        except Exception as e:
            return {"status": "auth_error", "partner_market": pm, "video_id": video_id, "error": str(e)}

    # Check if already present in playlist
    try:
        list_req = youtube_client.playlistItems().list(
            part="id,snippet",
            playlistId=playlist_id,
            videoId=video_id,
            maxResults=1,
        )
        list_resp = list_req.execute()
        if list_resp.get("items"):
            return {
                "status": "already_present",
                "partner_market": pm,
                "playlist_id": playlist_id,
                "video_id": video_id,
                "playlist_item_id": list_resp["items"][0]["id"],
            }
    except Exception as e:
        logger.debug("[cross_channel_promoter] Pre-check list error: %s", e)

    # Insert into playlist
    try:
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id,
                },
            }
        }
        insert_req = youtube_client.playlistItems().insert(part="snippet", body=body)
        insert_resp = insert_req.execute()
        item_id = insert_resp.get("id")
        logger.info("[cross_channel_promoter] Successfully added video %s to playlist %s on %s", video_id, playlist_id, pm)
        return {
            "status": "added_success",
            "partner_market": pm,
            "playlist_id": playlist_id,
            "video_id": video_id,
            "playlist_item_id": item_id,
        }
    except Exception as e:
        logger.warning("[cross_channel_promoter] Failed adding video %s to %s playlist %s: %s", video_id, pm, playlist_id, e)
        return {
            "status": "insert_error",
            "partner_market": pm,
            "playlist_id": playlist_id,
            "video_id": video_id,
            "error": str(e),
        }


def sync_featured_channels(target_market: str, youtube_client=None) -> Dict[str, Any]:
    """Tầng 3: Featured Sister Channels Showcase.
    Ensures the target market's channel home page features the other sister channels.
    """
    tm = target_market.upper().strip()
    partner_markets = [pm for pm in SUPPORTED_MARKETS if pm != tm]

    partner_channel_ids = []
    for pm in partner_markets:
        prof = get_channel_profile(pm)
        cid = prof.get("channel_id")
        if cid:
            partner_channel_ids.append(cid)

    if not partner_channel_ids:
        return {
            "status": "skipped_no_channel_ids",
            "market": tm,
            "note": "Sister channel IDs not set in environment variables (e.g. EN_YT_CHANNEL_ID).",
        }

    if youtube_client is None:
        try:
            from app.services.youtube_upload import _build_client
            youtube_client = _build_client(market=tm)
        except Exception as e:
            return {"status": "auth_error", "market": tm, "error": str(e)}

    section_title = (
        "公式グローバルネットワーク (Official Network)" if tm == "JP" else
        "공식 글로벌 네트워크 (Official Network)" if tm == "KR" else
        "Official Global Network"
    )

    try:
        # Check existing channel sections
        list_req = youtube_client.channelSections().list(part="id,snippet,contentDetails", mine=True)
        list_resp = list_req.execute()
        for sec in list_resp.get("items", []):
            if sec.get("snippet", {}).get("type") == "multiplechannels":
                return {
                    "status": "already_configured",
                    "market": tm,
                    "section_id": sec.get("id"),
                    "title": sec.get("snippet", {}).get("title"),
                }

        # Create multipleChannels section
        body = {
            "snippet": {
                "type": "multiplechannels",
                "title": section_title,
                "position": 1,
            },
            "contentDetails": {
                "channels": partner_channel_ids,
            },
        }
        create_req = youtube_client.channelSections().insert(part="snippet,contentDetails", body=body)
        res = create_req.execute()
        return {
            "status": "created_success",
            "market": tm,
            "section_id": res.get("id"),
            "featured_channels": partner_channel_ids,
        }
    except Exception as e:
        logger.warning("[cross_channel_promoter] Failed syncing channel sections on %s: %s", tm, e)
        return {"status": "section_error", "market": tm, "error": str(e)}


def dispatch_cross_promotion(
    video_id: str,
    market: str,
    episode_id: str = "",
    title: str = "",
) -> Dict[str, Any]:
    """Master Dispatcher for Step B10:
    Triggers Tầng 1 (Cross-Playlists) across all partner channels and records telemetry.
    """
    m = (market or "EN").upper().strip()
    partner_markets = [pm for pm in SUPPORTED_MARKETS if pm != m]

    results = {}
    for pm in partner_markets:
        res = add_video_to_partner_playlist(video_id=video_id, partner_market=pm)
        results[pm] = res

    # Record ledger entry
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "video_id": video_id,
        "source_market": m,
        "episode_id": episode_id,
        "title": title,
        "partner_distributions": results,
    }
    _record_ledger_entry(entry)

    logger.info("[cross_channel_promoter] Cross-promotion dispatched for %s (%s): %s", video_id, m, results)
    return {
        "source_market": m,
        "video_id": video_id,
        "episode_id": episode_id,
        "results": results,
    }


# Backward-compatible alias
distribute_to_all_partner_playlists = dispatch_cross_promotion


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cross Channel Promoter CLI")
    parser.add_argument("--video-id", required=True, help="YouTube Video ID")
    parser.add_argument("--market", default="EN", choices=["EN", "JP", "KR"], help="Source Market")
    parser.add_argument("--episode-id", default="", help="Episode ID")
    parser.add_argument("--title", default="", help="Video Title")
    parser.add_argument("--sync-sections", action="store_true", help="Sync channel sections (Featured Channels)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.sync_sections:
        print(f"Syncing featured channels for {args.market}...")
        sec_res = sync_featured_channels(args.market)
        print(json.dumps(sec_res, indent=2, ensure_ascii=False))

    print(f"Dispatching cross promotion for video {args.video_id} ({args.market})...")
    res = dispatch_cross_promotion(
        video_id=args.video_id,
        market=args.market,
        episode_id=args.episode_id,
        title=args.title,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))
