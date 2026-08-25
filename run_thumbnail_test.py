import asyncio
import os
import json
from pathlib import Path
import logging
logging.basicConfig(level=logging.INFO)

from app.services.episode_images import _generate_thumbnail_prompt, _gen_one, _registry_upsert_thumbnail
import app.services.image_gen as _img
from app.services.youtube_upload import _build_client, MediaFileUpload, _load_env

async def main():
    episode_id = "EP001"
    video_id = "bpiAPGfTHPY"
    
    # 1. Fake a brain input or read it
    brain_path = Path(f"/root/video_factory/episodes/{episode_id}/brain_input.json")
    if brain_path.exists():
        with open(brain_path, "r") as f:
            brain = json.load(f)
    else:
        # Fallback fake brain
        brain = {
            "topic": "The mystery of something",
            "hook_3s": "This is a dramatic hook for EP001",
            "story": "Once upon a time in EP001...",
            "art_style": {"style_prompt": "cinematic realism"}
        }

    print("--- 1. Generating thumbnail prompt ---")
    thumb_prompt = _generate_thumbnail_prompt(brain)
    print("Prompt:", thumb_prompt)

    print("--- 2. Generating image via _gen_one ---")
    thumb_img = await _gen_one(thumb_prompt)
    thumb_local = thumb_img.get("local_path")
    if not thumb_local or not os.path.exists(thumb_local):
        print("Failed to generate image local path!")
        return
    print("Local image generated at:", thumb_local)

    from PIL import Image as _PILImage
    out_dir = Path(f"/root/video_factory/episodes/{episode_id}/images")
    out_dir.mkdir(parents=True, exist_ok=True)
    thumb_dest = str(out_dir / "thumbnail.png")
    
    _PILImage.open(thumb_local).convert("RGB").save(thumb_dest, "PNG")
    print("Saved thumbnail to:", thumb_dest)

    print("--- 3. Uploading to R2 and updating Notion DB ---")
    try:
        thumb_r2 = _img._r2_upload(thumb_dest, f"episodes/{episode_id}/thumbnail.png")
        if thumb_r2:
            print("R2 URL:", thumb_r2)
            _registry_upsert_thumbnail(episode_id, thumb_r2)
            print("Notion DB updated.")
        else:
            print("R2 upload failed.")
    except Exception as e:
        print("Notion DB / R2 upload error:", e)

    print("--- 4. Uploading to YouTube ---")
    _load_env()
    youtube = _build_client() # default market
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumb_dest)
        ).execute()
        print(f"THUMBNAIL_SET_OK for video {video_id} using {thumb_dest}")
    except Exception as e:
        print(f"[WARN] thumbnail set failed for {video_id}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
