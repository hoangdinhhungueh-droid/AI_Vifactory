#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/upload_preview_chunk.py
Uploads Chunk 1 preview of EN_EP0004_amazon_ad_lawsuit to YouTube Unlisted.
"""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.youtube_upload import upload_video

EPISODE_ID = "EN_EP0004_amazon_ad_lawsuit"
EP_DIR = Path(f"/var/vf/episodes/{EPISODE_ID}")
VIDEO_PATH = str(EP_DIR / "preview_chunk_01_act_i.mp4")
THUMBNAIL_PATH = str(EP_DIR / "thumbnail_a.png")

def main():
    if not os.path.exists(VIDEO_PATH):
        print(f"Error: {VIDEO_PATH} does not exist!", file=sys.stderr)
        sys.exit(1)

    title = "[PREVIEW CHUNK 1] Amazon $20B Ad Lawsuit: VOX Docudrama Act I"
    description = (
        "Preview of Act I (00:00 - 02:37) for Episode EN_EP0004_amazon_ad_lawsuit.\n\n"
        "Style: VOX / Netflix Investigative Docudrama (Object-Driven Evidence)\n"
        "- 100% Tangible Forensic Evidence Artifacts (FTC Court Docket, $20B Audit Invoice)\n"
        "- Zero cartoon human bodies\n"
        "- Dimmed volumetric lighting + punchy white sticker cutout drop-shadow\n"
        "- Word-level karaoke subtitles & clean speaker tags\n\n"
        "#AmazonLawsuit #FTC #Docudrama #VOXStyle"
    )
    tags = ["Amazon", "FTC", "VOX Docudrama", "Preview", "Lawsuit"]

    print(f"🚀 Uploading {VIDEO_PATH} ({os.path.getsize(VIDEO_PATH)/(1024*1024):.1f} MB) to YouTube Unlisted...")
    try:
        vid_id = upload_video(
            video_path=VIDEO_PATH,
            title=title,
            description=description,
            tags=tags,
            privacy_status="unlisted",
            market="en",
            thumbnail_path=THUMBNAIL_PATH if os.path.exists(THUMBNAIL_PATH) else None
        )
        url = f"https://youtu.be/{vid_id}"
        print(f"✅ UPLOAD SUCCESSFUL!")
        print(f"📺 Watch URL: {url}")
        print(f"VIDEO_ID={vid_id}")
    except Exception as e:
        print(f"❌ Upload failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
