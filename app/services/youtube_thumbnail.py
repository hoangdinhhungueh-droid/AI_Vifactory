# -*- coding: utf-8 -*-
"""
YouTube thumbnail upload helper. Added 23/08/2026 to support the new
automated B10 flow (Rule 119): auto-set a custom thumbnail image via the
YouTube Data API v3 `thumbnails.set` endpoint, when a matching image asset
exists for the episode. Additive module -- does not modify youtube_upload.py.

NOTE: `thumbnails().set()` requires the uploading channel to have custom
thumbnails enabled (phone-verified YouTube account). If the call fails for
that reason, this function fails soft (logs + returns None) so it never
blocks the B10 upload/Gate 2 flow.
"""
from __future__ import annotations

import os
import logging

from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from app.services.youtube_upload import _build_client, _load_env

logger = logging.getLogger("vf.youtube_thumbnail")


def set_thumbnail(video_id: str, thumbnail_path: str, market: str = None):
    """Upload and set a custom thumbnail for an already-uploaded video.

    Returns the YouTube API response dict on success, or None if skipped/failed
    (non-blocking by design -- see module docstring).
    """
    if not video_id:
        logger.warning("[thumbnail] missing video_id, skip")
        return None
    if not thumbnail_path or not os.path.exists(thumbnail_path):
        logger.info("[thumbnail] no thumbnail asset at %s, skip (pipeline has no dedicated thumbnail generator yet)", thumbnail_path)
        return None

    _load_env()
    try:
        youtube = _build_client(market=market)
        media = MediaFileUpload(thumbnail_path, mimetype="image/png")
        response = youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
        logger.info("[thumbnail] set OK for video_id=%s (%s)", video_id, thumbnail_path)
        return response
    except HttpError as e:
        logger.warning("[thumbnail] YouTube API rejected thumbnail set for %s: %s (channel may need phone verification for custom thumbnails)", video_id, e)
        return None
    except Exception as e:
        logger.warning("[thumbnail] unexpected error setting thumbnail for %s: %s", video_id, e)
        return None
