"""spotify_upload.py - Spotify for Creators distribution adapter (Phase 3).

IMPORTANT: Spotify has NO public upload API for podcasts/video shows. The only
programmatic path is an RSS feed that Spotify for Creators ingests (audio:
MP3/M4A/WAV; video: MP4/MOV/MPG). So this adapter does NOT call an upload API;
instead it generates a standards-compliant RSS <item> and maintains a feed
manifest, leaving feed hosting + one-time portal connection as the manual step.

Reads seo_payloads.json['spotify'] and the episode audio (default narration.mp3),
appends/updates the RSS item in spotify_feed.xml, and writes spotify_manifest.json
+ spotify_rss_item.xml. Media URL is built from VF_PUBLIC_MEDIA_BASE.

Usage: PYTHONPATH=/root/video_factory python3 scripts/spotify_upload.py <episode_dir> [audio_file]
"""
import json
import os
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape


def _public_media_url(episode_dir, media_file):
    base = os.getenv("VF_PUBLIC_MEDIA_BASE")
    if not base:
        return None
    eid = os.path.basename(os.path.normpath(episode_dir))
    return base.rstrip("/") + "/" + eid + "/" + media_file


def build_rss_item(payload, *, media_url, guid, pub_dt=None, duration_s=None,
                   mime="audio/mpeg"):
    """Pure: build a Spotify-compatible RSS <item> string. No network."""
    pub_dt = pub_dt or datetime.now(timezone.utc)
    title = escape(payload.get("title") or "Episode")
    desc = escape(payload.get("description") or "")
    enclosure = ("    <enclosure url=\"%s\" type=\"%s\" length=\"0\"/>\n" % (
        escape(media_url), mime)) if media_url else ""
    dur = ("    <itunes:duration>%d</itunes:duration>\n" % int(duration_s)) if duration_s else ""
    return (
        "  <item>\n"
        "    <title>" + title + "</title>\n"
        "    <description>" + desc + "</description>\n"
        "    <itunes:summary>" + desc + "</itunes:summary>\n"
        "    <guid isPermaLink=\"false\">" + escape(guid) + "</guid>\n"
        "    <pubDate>" + format_datetime(pub_dt) + "</pubDate>\n"
        + enclosure + dur +
        "    <itunes:explicit>false</itunes:explicit>\n"
        "  </item>\n"
    )


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    episode_dir = argv[0] if argv else "/var/vf/episodes/betrayal-revenge-quiet-2026-ep001"
    audio_file = argv[1] if len(argv) > 1 else "narration.mp3"
    eid = os.path.basename(os.path.normpath(episode_dir))
    with open(os.path.join(episode_dir, "seo_payloads.json")) as f:
        payloads = json.load(f)
    payload = payloads.get("spotify") or {}
    media_url = _public_media_url(episode_dir, audio_file)
    item_xml = build_rss_item(payload, media_url=media_url, guid=eid)
    with open(os.path.join(episode_dir, "spotify_rss_item.xml"), "w") as f:
        f.write(item_xml)
    manifest = {
        "adapter": "spotify", "mode": "RSS",
        "note": "Spotify has no upload API. Host spotify_feed.xml publicly and "
                "connect it once in Spotify for Creators; new items are auto-ingested.",
        "episode_id": eid, "category": payload.get("category", "Fiction / Story"),
        "media_url": media_url, "audio_file": audio_file,
        "feed_public_required": not bool(media_url),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(os.path.join(episode_dir, "spotify_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    print("--- RSS ITEM ---")
    print(item_xml)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
