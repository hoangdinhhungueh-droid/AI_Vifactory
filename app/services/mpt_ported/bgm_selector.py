"""MPT-G4-3 - BGM selector from music_library CC0 catalog."""
import asyncio, os, random
from pathlib import Path
from typing import Optional

BGM_CATALOG_DIR = os.getenv("BGM_DIR", "/root/video_factory/assets/bgm")
BGM_GENRES = ["epic", "calm", "happy", "sad", "dramatic", "peaceful", "energetic", "mystery"]

MOOD_TO_GENRE = {
    "epic":       "epic",
    "dramatic":   "dramatic",
    "tense":      "dramatic",
    "calm":       "calm",
    "peaceful":   "peaceful",
    "relaxing":   "peaceful",
    "happy":      "happy",
    "cheerful":   "happy",
    "sad":        "sad",
    "melancholy": "sad",
    "energetic":  "energetic",
    "upbeat":     "energetic",
    "mystery":    "mystery",
    "suspense":   "mystery",
}


def _get_genre(mood: str) -> str:
    return MOOD_TO_GENRE.get(mood.lower(), "epic")


async def _select_from_db(mood: str, duration_s: float, episode_id: Optional[str]) -> Optional[dict]:
    """Query music_library Postgres for a matching CC0 track."""
    try:
        import asyncpg
        db_url = os.getenv("DATABASE_URL", "")
        if not db_url:
            return None
        conn = await asyncpg.connect(db_url)
        genre = _get_genre(mood)
        row = await conn.fetchrow(
            "SELECT filename, genre, license_type, license_url "
            "FROM music_library WHERE acr_status=$1 AND genre=$2 "
            "ORDER BY RANDOM() LIMIT 1",
            "clean", genre
        )
        await conn.close()
        if row:
            fpath = str(Path(BGM_CATALOG_DIR) / row["filename"])
            return {
                "path": fpath,
                "filename": row["filename"],
                "license_url": row["license_url"] or "CC0",
                "genre": row["genre"],
            }
    except Exception as e:
        print(f"[bgm_selector] DB query failed: {e}")
    return None


def _select_from_filesystem(mood: str) -> Optional[dict]:
    """Fallback: pick random file from assets/bgm/ matching genre prefix."""
    genre = _get_genre(mood)
    catalog = Path(BGM_CATALOG_DIR)
    if not catalog.exists():
        return None
    candidates = list(catalog.glob(f"*{genre}*.mp3")) or list(catalog.glob("*.mp3"))
    if not candidates:
        return None
    chosen = random.choice(candidates)
    return {
        "path": str(chosen),
        "filename": chosen.name,
        "license_url": "CC0",
        "genre": genre,
    }


async def select_bgm(
    mood: str,
    duration_s: float,
    episode_id: Optional[str] = None,
) -> dict:
    """Returns dict: path, filename, license_url, genre. DB first, filesystem fallback."""
    result = await _select_from_db(mood, duration_s, episode_id)
    if not result:
        result = _select_from_filesystem(mood)
    if not result:
        raise RuntimeError(f"[bgm_selector] No BGM found for mood='{mood}'")
    return result
