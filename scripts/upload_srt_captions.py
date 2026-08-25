"""Standalone/independent SRT caption upload trigger (Go-Live Moc 3.2).

By design this is a SEPARATE manual step from the main private video
upload -- see app/services/seo_metadata.py `srt_manual_upload` /
`srt_independent_upload` rule (already decided/wired into the SEO
payload before this script existed) and Go-Live Moc 3.2 ("upload_video
private -> upload_srt -> ... -> set_public"). This script is
intentionally NOT auto-called from upload_from_payload(), any pipeline
stage, cron, or Telegram button -- run it by hand (or have Notion AI run
it) after a video has been uploaded and its videoId is known, whenever
you decide captions should be attached.

Usage:
  python3 scripts/upload_srt_captions.py <episode_dir> <video_id> [language] [name]

Reads srt_path from <episode_dir>/youtube_upload_payload.json (field
"srt_path", written by seo_metadata.write_seo_payloads when the platform
rule has srt_manual_upload=True). Falls back to
<episode_dir>/final_169.srt if the payload field is missing/absent.
"""
import json
import os
import sys

sys.path.insert(0, "/root/video_factory")

from app.services.youtube_upload import upload_captions  # noqa: E402


def _resolve_srt_path(episode_dir):
    payload_path = os.path.join(episode_dir, "youtube_upload_payload.json")
    if os.path.exists(payload_path):
        with open(payload_path) as f:
            payload = json.load(f)
        srt_path = payload.get("srt_path")
        if srt_path and os.path.exists(srt_path):
            return srt_path
    fallback = os.path.join(episode_dir, "final_169.srt")
    if os.path.exists(fallback):
        return fallback
    raise FileNotFoundError(
        "No srt_path in payload and no fallback at " + fallback
    )


def main():
    if len(sys.argv) < 3:
        print("Usage: upload_srt_captions.py <episode_dir> <video_id> [language] [name]")
        sys.exit(1)
    episode_dir = sys.argv[1]
    video_id = sys.argv[2]
    language = sys.argv[3] if len(sys.argv) > 3 else "en"
    name = sys.argv[4] if len(sys.argv) > 4 else "English"
    srt_path = _resolve_srt_path(episode_dir)
    resp = upload_captions(video_id, srt_path, language=language, name=name)
    caption_id = resp.get("id") if isinstance(resp, dict) else None
    print("CAPTION_UPLOAD_OK captionId=" + str(caption_id))
    print("SRT_PATH " + srt_path)


if __name__ == "__main__":
    main()
