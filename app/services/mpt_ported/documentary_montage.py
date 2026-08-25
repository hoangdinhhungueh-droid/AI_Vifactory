"""S5 documentary montage - multi-asset free B-roll for NON-FICTION episodes.

Non-fiction topics (business / history / true crime / psychology / scam) usually
have NO character_pack, so the old S5 stock path fetched a SINGLE clip per scene
(flat, repetitive). This builds a richer DOCUMENTARY MONTAGE: several free assets
per scene (Pexels + Pixabay videos AND photos), with Ken Burns motion applied to
stills so the episode feels like archival documentary footage instead of one
looping clip.

All sources are CC0 / commercial-safe (Pexels, Pixabay). 0 credit, FFmpeg-only
(CPU-native; no GPU, no headless Chrome).

Env toggles:
  S5_DOC_MONTAGE        '1' default -> enable documentary montage in stock mode
  S5_MONTAGE_PER_SCENE  '3' default -> assets fetched per scene
  S5_KENBURNS           '1' default -> animate stills with zoompan
  S5_KENBURNS_SEC       '5' default -> seconds per Ken Burns still-clip
"""
import asyncio
import hashlib
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
MONTAGE_CACHE = "/tmp/vf/montage_cache"
_KB_SIZE = (1080, 1920)  # legacy default (9:16) - kept for callers with no aspect

# FIX 27/07/2026 (Decisions Log): aspect-aware Ken Burns. Hardcoding 9:16 here
# centre-cropped every 16:9 still down to ~28% of its width.
_KB_ASPECT_SIZES = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}


def _kb_size(aspect=None):
    key = (aspect or os.environ.get("VF_KB_ASPECT")
           or os.environ.get("VF_IMAGE_ASPECT") or "16:9").strip()
    return _KB_ASPECT_SIZES.get(key, _KB_SIZE)


def doc_montage_enabled() -> bool:
    return os.environ.get("S5_DOC_MONTAGE", "1") not in ("0", "false", "False", "")


def _per_scene() -> int:
    try:
        return max(1, int(os.environ.get("S5_MONTAGE_PER_SCENE", "3")))
    except ValueError:
        return 3


def _kenburns_enabled() -> bool:
    return os.environ.get("S5_KENBURNS", "1") not in ("0", "false", "False", "")


def _kb_sec() -> float:
    try:
        return max(2.0, float(os.environ.get("S5_KENBURNS_SEC", "5")))
    except ValueError:
        return 5.0


def _ck(*parts) -> str:
    return hashlib.md5(":".join(str(p) for p in parts).encode()).hexdigest()[:16]


async def _pexels(query: str, media_type: str, n: int) -> list:
    """Return up to n asset dicts {url, source, license, media_type} from Pexels."""
    if not PEXELS_API_KEY:
        return []
    endpoint = "videos" if media_type == "video" else "photos"
    url = "https://api.pexels.com/" + endpoint + "/search"
    params = {"query": query, "per_page": max(n * 2, 6), "orientation": "portrait"}
    headers = {"Authorization": PEXELS_API_KEY}
    out = []
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(url, params=params, headers=headers)
            r.raise_for_status()
            data = r.json()
            items = data.get("videos", data.get("photos", []))
            for item in items:
                if media_type == "video":
                    files = item.get("video_files", [])
                    link = next(
                        (f["link"] for f in files
                         if f.get("width", 0) >= 720 and f.get("height", 0) >= 1280),
                        files[0]["link"] if files else None,
                    )
                else:
                    src = item.get("src", {})
                    link = src.get("portrait", src.get("large", src.get("original")))
                if link:
                    out.append({"url": link, "source": "pexels", "license": "CC0",
                                "license_url": "https://www.pexels.com/license/",
                                "media_type": media_type})
                if len(out) >= n:
                    break
        except Exception as e:
            logger.warning("[montage] Pexels %s error for %r: %s", media_type, query, e)
    return out


async def _pixabay(query: str, media_type: str, n: int) -> list:
    if not PIXABAY_API_KEY:
        return []
    base = "https://pixabay.com/api/"
    url = base + "videos/" if media_type == "video" else base
    params = {"key": PIXABAY_API_KEY, "q": query, "per_page": max(n * 2, 6),
              "safesearch": "true"}
    out = []
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(url, params=params)
            r.raise_for_status()
            for item in r.json().get("hits", []):
                if media_type == "video":
                    sizes = item.get("videos", {})
                    link = (sizes.get("large") or sizes.get("medium") or {}).get("url")
                else:
                    link = item.get("largeImageURL") or item.get("webformatURL")
                if link:
                    out.append({"url": link, "source": "pixabay", "license": "CC0",
                                "license_url": "https://pixabay.com/service/license-summary/",
                                "media_type": media_type})
                if len(out) >= n:
                    break
        except Exception as e:
            logger.warning("[montage] Pixabay %s error for %r: %s", media_type, query, e)
    return out


async def _download(url: str, dest: str) -> str:
    Path(MONTAGE_CACHE).mkdir(parents=True, exist_ok=True)
    if Path(dest).exists() and Path(dest).stat().st_size > 1024:
        return dest
    async with httpx.AsyncClient(timeout=90, follow_redirects=True) as client:
        async with client.stream("GET", url) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                async for chunk in r.aiter_bytes(65536):
                    f.write(chunk)
    return dest


async def _kenburns(img_path: str, out_path: str, dur: float,
                    aspect: str = None) -> str:
    """Animate a still into a slow zoom/pan clip (archival documentary feel)."""
    w, h = _kb_size(aspect)
    fps = 30
    frames = int(dur * fps)
    vf = (
        "scale=" + str(w * 2) + ":" + str(h * 2)
        + ":force_original_aspect_ratio=increase,"
        + "crop=" + str(w * 2) + ":" + str(h * 2) + ","
        + "zoompan=z='min(zoom+0.0012,1.25)':d=" + str(frames)
        + ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        + "s=" + str(w) + "x" + str(h) + ":fps=" + str(fps) + ","
        + "format=yuv420p"
    )
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-vf", vf,
           "-t", str(dur), "-c:v", "libx264", "-preset", "fast",
           "-pix_fmt", "yuv420p", "-an", out_path]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError("kenburns failed: " + err.decode()[-200:])
    return out_path


async def build_scene_montage(query: str, lang_code: str, episode_id: str,
                              scene_idx: int, n: int = 0, aspect: str = None) -> list:
    """Fetch several free assets for ONE scene and return ready clip dicts.

    Mix of videos (used directly) + photos (Ken Burns -> mp4). Each returned
    dict has a local `path`/`local_path` so S7 can concat it. Best-effort: any
    asset that fails to download/convert is skipped, never raised.
    """
    n = n or _per_scene()
    aspect = aspect or (os.environ.get("VF_KB_ASPECT")
                        or os.environ.get("VF_IMAGE_ASPECT") or "16:9")
    if not query:
        return []
    # Prefer ~2/3 video, ~1/3 stills (documentary mix).
    n_video = max(1, (n * 2) // 3)
    n_photo = max(0, n - n_video) if _kenburns_enabled() else 0
    n_video = n - n_photo

    vids = await _pexels(query, "video", n_video)
    if len(vids) < n_video:
        vids += await _pixabay(query, "video", n_video - len(vids))
    photos = []
    if n_photo:
        photos = await _pexels(query, "photo", n_photo)
        if len(photos) < n_photo:
            photos += await _pixabay(query, "photo", n_photo - len(photos))

    Path(MONTAGE_CACHE).mkdir(parents=True, exist_ok=True)
    clips = []
    # Videos: download directly.
    for j, a in enumerate(vids):
        try:
            dest = os.path.join(
                MONTAGE_CACHE,
                episode_id + "_m" + str(scene_idx) + "_v" + str(j) + ".mp4")
            await _download(a["url"], dest)
            clips.append({**a, "path": dest, "local_path": dest, "montage": True})
        except Exception as e:
            logger.warning("[montage] video dl failed %r: %s", query, e)
    # Photos: download then Ken Burns -> mp4.
    for j, a in enumerate(photos):
        try:
            img = os.path.join(
                MONTAGE_CACHE,
                episode_id + "_m" + str(scene_idx) + "_p" + str(j) + ".jpg")
            await _download(a["url"], img)
            out = os.path.join(
                MONTAGE_CACHE,
                episode_id + "_m" + str(scene_idx) + "_kb" + str(j) + ".mp4")
            await _kenburns(img, out, _kb_sec())
            clips.append({**a, "path": out, "local_path": out,
                          "kenburns": True, "montage": True})
        except Exception as e:
            logger.warning("[montage] kenburns failed %r: %s", query, e)

    logger.info("[montage] scene %d %r -> %d clips (%d video + %d stills)",
                scene_idx, query[:40], len(clips),
                sum(1 for c in clips if not c.get("kenburns")),
                sum(1 for c in clips if c.get("kenburns")))
    return clips
