
"""MPT-G3-1 - Stock media fetcher: Pexels + Pixabay + R2 cache.

FIX 2026-06-14: API URLs were corrupted by an f-string brace-escaping bug
(f"https://..." renders the literal '{https://...}' -> invalid URL ->
every request failed -> 0 clips, always falling back to a test clip).
URLs are now built with plain string concatenation so braces can never break
them again. Both Pexels and Pixabay allow commercial use with no required
attribution, which is safe for monetized YouTube content.
"""
import asyncio, hashlib, json, os, time
from pathlib import Path
from typing import Optional
import httpx

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
R2_CACHE_DIR = "/tmp/vf/stock_cache"
RATE_LIMIT_CALLS = 200          # per hour
RATE_LIMIT_WINDOW = 3600

_call_log: list = []            # simple in-process rate tracker


def _cache_key(query: str, media_type: str, idx: int) -> str:
    return hashlib.md5(f"{query}:{media_type}:{idx}".encode()).hexdigest()[:16]


def _check_rate_limit():
    now = time.time()
    global _call_log
    _call_log = [t for t in _call_log if now - t < RATE_LIMIT_WINDOW]
    if len(_call_log) >= RATE_LIMIT_CALLS:
        raise RuntimeError(f"[stock_fetcher] Rate limit: {len(_call_log)} calls in last hour")
    _call_log.append(now)


async def _fetch_pexels(query: str, duration_s: float, media_type: str, lang_code: str) -> Optional[dict]:
    if not PEXELS_API_KEY:
        print("[stock_fetcher] Pexels skipped: PEXELS_API_KEY not set")
        return None
    _check_rate_limit()
    endpoint = "videos" if media_type == "video" else "photos"
    # plain concatenation -> no brace escaping issues
    url = "https://api.pexels.com/" + endpoint + "/search"
    params = {"query": query, "per_page": 10, "orientation": "portrait"}
    headers = {"Authorization": PEXELS_API_KEY}
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(url, params=params, headers=headers)
            r.raise_for_status()
            data = r.json()
            items = data.get("videos", data.get("photos", []))
            if not items:
                print("[stock_fetcher] Pexels: 0 items for query=" + repr(query))
                return None
            item = items[0]
            if media_type == "video":
                files_list = item.get("video_files", [])
                # prefer HD portrait
                link = next(
                    (f["link"] for f in files_list if f.get("width", 0) >= 720 and f.get("height", 0) >= 1280),
                    files_list[0]["link"] if files_list else None
                )
                return {"url": link, "source": "pexels", "license": "CC0",
                        "license_url": "https://www.pexels.com/license/",
                        "duration": item.get("duration", duration_s)}
            else:
                src = item.get("src", {})
                return {"url": src.get("portrait", src.get("original")),
                        "source": "pexels", "license": "CC0",
                        "license_url": "https://www.pexels.com/license/"}
        except Exception as e:
            print("[stock_fetcher] Pexels error: " + repr(e))
            return None


async def _fetch_pixabay(query: str, media_type: str) -> Optional[dict]:
    if not PIXABAY_API_KEY:
        return None
    _check_rate_limit()
    ptype = "video" if media_type == "video" else "photo"
    # plain concatenation -> no brace escaping issues
    base = "https://pixabay.com/api/"
    url = base + "videos/" if ptype == "video" else base
    params = {"key": PIXABAY_API_KEY, "q": query, "per_page": 10,
              "safesearch": "true"}
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(url, params=params)
            r.raise_for_status()
            hits = r.json().get("hits", [])
            if not hits:
                print("[stock_fetcher] Pixabay: 0 hits for query=" + repr(query))
                return None
            item = hits[0]
            if ptype == "video":
                sizes = item.get("videos", {})
                link = (sizes.get("large") or sizes.get("medium") or {}).get("url")
            else:
                link = item.get("largeImageURL") or item.get("webformatURL")
            return {"url": link, "source": "pixabay", "license": "CC0",
                    "license_url": "https://pixabay.com/service/license-summary/"}
        except Exception as e:
            print("[stock_fetcher] Pixabay error: " + repr(e))
            return None


async def _download_to_cache(url: str, cache_key: str, ext: str) -> str:
    """Download URL to R2_CACHE_DIR; return local path."""
    Path(R2_CACHE_DIR).mkdir(parents=True, exist_ok=True)
    local = f"{R2_CACHE_DIR}/{cache_key}.{ext}"
    if Path(local).exists() and Path(local).stat().st_size > 1024:
        return local
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        async with client.stream("GET", url) as r:
            r.raise_for_status()
            with open(local, "wb") as f:
                async for chunk in r.aiter_bytes(65536):
                    f.write(chunk)
    return local


async def fetch_stock_clip(
    query: str,
    duration_s: float = 5.0,
    media_type: str = "video",   # "video" or "photo"
    lang_code: str = "en",
    download: bool = False,
) -> dict:
    """
    Returns dict: url, local_path (if download=True), source, license, license_url.
    Tries Pexels first, then Pixabay.
    """
    # Try Pexels
    result = await _fetch_pexels(query, duration_s, media_type, lang_code)
    # Fallback Pixabay
    if not result:
        result = await _fetch_pixabay(query, media_type)
    if not result:
        raise RuntimeError("[stock_fetcher] No results for query=" + repr(query))

    if download and result.get("url"):
        ext = "mp4" if media_type == "video" else "jpg"
        ck = _cache_key(query, media_type, 0)
        result["local_path"] = await _download_to_cache(result["url"], ck, ext)
    else:
        result["local_path"] = None

    return result
