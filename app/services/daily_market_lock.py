"""
app/services/daily_market_lock.py — DAILY MARKET PRODUCTION LOCK & QUOTA GUARD
Mandate:
  1. Prevents duplicate scraping and duplicate episode production for the same market on the same day.
  2. Anchored strictly to Vietnam Timezone (Asia/Ho_Chi_Minh, UTC+7).
  3. Two-tier state:
     - IN_PROGRESS: Guard with TTL (default 6h) to avoid race conditions.
     - COMPLETED: Hard lock for the remainder of the Vietnam calendar day.
  4. Authoritative check across:
     - Lock file: <STATE_DIR>/b1_daily_lock/{MARKET}_{YYYY-MM-DD}.json
     - Permanent History Registry (topic_history_registry)
     - Episode directories with completed run_manifest.json
  5. Cross-platform safe: Windows & Linux compatible.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

VN_TZ = timezone(timedelta(hours=7))
DEFAULT_TTL_SECONDS = 21600  # 6 hours


def resolve_state_dir(custom_dir: Optional[str] = None) -> Path:
    """Resolve directory used for lock files and volatile state."""
    if custom_dir:
        p = Path(custom_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    env_dir = os.getenv("AVF_STATE_DIR") or os.getenv("VF_LOCK_DIR")
    if env_dir:
        p = Path(env_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # Default VPS location vs Local workspace fallback
    vps_lock = Path("/var/vf/locks")
    if vps_lock.exists() or os.name != "nt":
        try:
            vps_lock.mkdir(parents=True, exist_ok=True)
            return vps_lock
        except (PermissionError, OSError):
            pass

    # Local fallback
    project_root = Path(__file__).resolve().parent.parent.parent
    local_locks = project_root / "locks"
    local_locks.mkdir(parents=True, exist_ok=True)
    return local_locks


def vn_now(now: Optional[datetime] = None) -> datetime:
    """Return timezone-aware datetime in Vietnam time (UTC+7)."""
    if now is not None:
        if now.tzinfo is None:
            return now.replace(tzinfo=VN_TZ)
        return now.astimezone(VN_TZ)
    return datetime.now(timezone.utc).astimezone(VN_TZ)


def vn_today(now: Optional[datetime] = None) -> str:
    """Return date string YYYY-MM-DD anchored in Vietnam timezone."""
    return vn_now(now).strftime("%Y-%m-%d")


def _get_lock_file_path(market: str, state_dir: Optional[str] = None, now: Optional[datetime] = None) -> Path:
    base = resolve_state_dir(state_dir)
    lock_subdir = base / "b1_daily_lock"
    lock_subdir.mkdir(parents=True, exist_ok=True)
    m_up = (market or "EN").upper()
    date_str = vn_today(now)
    return lock_subdir / f"{m_up}_{date_str}.json"


def _atomic_write_json(path: Path, data: dict) -> bool:
    """Write dictionary to JSON file atomically via temp file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f".tmp_{os.getpid()}_{int(datetime.now(timezone.utc).timestamp())}")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        return True
    except Exception as e:
        logger.error(f"[daily_market_lock] Failed to write {path}: {e}")
        return False


def is_market_done_today(
    market: str,
    state_dir: Optional[str] = None,
    now: Optional[datetime] = None,
    force: bool = False,
    check_registry: bool = True,
    check_episodes: bool = True,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Check whether the given market has already completed or is currently
    producing today's episode.

    Returns:
        (is_done, reason, details)
        - is_done: True -> B1 MUST SKIP CRAWL
        - reason: identifier ('forced_override', 'lock_completed', 'lock_in_progress',
                            'registry_completed', 'episode_dir_completed', 'not_produced_yet')
        - details: dictionary with topic_id, vn_date, etc.
    """
    if force or os.getenv("B1_FORCE_CRAWL") == "1":
        return False, "forced_override", {"market": market, "forced": True}

    m_up = (market or "EN").upper()
    date_str = vn_today(now)
    lock_path = _get_lock_file_path(m_up, state_dir, now)

    stale_lock_found = False
    stale_data = {}

    # 1. Check lock file
    if lock_path.exists():
        try:
            with open(lock_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    logger.error(f"[daily_market_lock] Lock file {lock_path} is empty (fail-closed)")
                    return True, "corrupt_lock_fail_closed", {"market": m_up, "date": date_str}
                data = json.loads(content)
        except Exception as e:
            logger.error(f"[daily_market_lock] Lock file {lock_path} is corrupt: {e} (fail-closed)")
            return True, "corrupt_lock_fail_closed", {"market": m_up, "date": date_str, "error": str(e)}

        status = data.get("status", "").upper()
        if status == "COMPLETED":
            return True, "lock_completed", data

        if status == "IN_PROGRESS":
            created_at_str = data.get("created_at_utc")
            ttl = int(data.get("ttl_seconds", DEFAULT_TTL_SECONDS))
            if created_at_str:
                try:
                    c_dt = datetime.fromisoformat(created_at_str)
                    if c_dt.tzinfo is None:
                        c_dt = c_dt.replace(tzinfo=timezone.utc)
                    age_seconds = (datetime.now(timezone.utc) - c_dt).total_seconds()
                    if age_seconds < ttl:
                        return True, "lock_in_progress", data
                    else:
                        logger.warning(
                            f"[daily_market_lock] Stale IN_PROGRESS lock for {m_up} on {date_str} "
                            f"(age={int(age_seconds)}s > ttl={ttl}s). Allowing re-run."
                        )
                        stale_lock_found = True
                        stale_data = data
                except Exception as _parse_err:
                    logger.warning(f"[daily_market_lock] Error parsing lock timestamp: {_parse_err}")
                    return True, "lock_in_progress", data

    # 2. Check topic_history_registry if requested
    if check_registry:
        try:
            from app.services.topic_history_registry import load_history
            history = load_history()
            for key, entry in history.items():
                if not isinstance(entry, dict):
                    continue
                ent_mkt = (entry.get("market") or "").upper()
                if ent_mkt != m_up:
                    continue

                task_id = str(entry.get("task_id") or "")
                # Exclude rejected/handled dummy marks
                if task_id in ("REJECTED_OR_HANDLED", "HANDLED", ""):
                    continue

                rec_at = entry.get("recorded_at")
                if rec_at:
                    try:
                        rec_dt = datetime.fromisoformat(rec_at)
                        rec_vn_date = vn_today(rec_dt)
                        if rec_vn_date == date_str:
                            # Auto-heal the lock file to COMPLETED
                            details = {
                                "market": m_up,
                                "vn_date": date_str,
                                "status": "COMPLETED",
                                "topic_id": task_id,
                                "raw_term": entry.get("raw_term", ""),
                                "source": "history_registry_auto_healed",
                                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                            }
                            _atomic_write_json(lock_path, details)
                            return True, "registry_completed", details
                    except Exception:
                        pass
        except Exception as reg_err:
            logger.debug(f"[daily_market_lock] Registry check notice: {reg_err}")

    # 3. Check Episode directories on disk
    if check_episodes:
        episodes_roots = [
            Path("/var/vf/episodes"),
            Path("/root/video_factory/episodes"),
            Path(__file__).resolve().parent.parent.parent / "episodes",
        ]
        for ep_root in episodes_roots:
            if not ep_root.is_dir():
                continue
            try:
                prefix = f"{m_up}_EP"
                for ep_dir in ep_root.iterdir():
                    if not ep_dir.is_dir() or not ep_dir.name.startswith(prefix):
                        continue
                    # Check manifest or directory timestamp
                    manifest_file = ep_dir / "run_manifest.json"
                    if manifest_file.exists():
                        try:
                            m_stat = manifest_file.stat()
                            m_vn_date = vn_today(datetime.fromtimestamp(m_stat.st_mtime, timezone.utc))
                            if m_vn_date == date_str:
                                details = {
                                    "market": m_up,
                                    "vn_date": date_str,
                                    "status": "COMPLETED",
                                    "topic_id": ep_dir.name,
                                    "source": "episode_dir_completed",
                                    "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                                }
                                _atomic_write_json(lock_path, details)
                                return True, "episode_dir_completed", details
                        except Exception:
                            pass
            except Exception as ep_err:
                logger.debug(f"[daily_market_lock] Episode dir check notice: {ep_err}")

    if stale_lock_found:
        return False, "stale_lock", stale_data
    return False, "not_produced_yet", {"market": m_up, "date": date_str}


def acquire_in_progress(
    market: str,
    topic_id: str = "",
    state_dir: Optional[str] = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: Optional[datetime] = None,
) -> bool:
    """Acquire IN_PROGRESS daily lock for market."""
    m_up = (market or "EN").upper()
    date_str = vn_today(now)
    lock_path = _get_lock_file_path(m_up, state_dir, now)

    payload = {
        "market": m_up,
        "vn_date": date_str,
        "status": "IN_PROGRESS",
        "topic_id": topic_id,
        "pid": os.getpid(),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "ttl_seconds": ttl_seconds,
    }
    success = _atomic_write_json(lock_path, payload)
    if success:
        logger.info(f"[daily_market_lock] Acquired IN_PROGRESS lock for {m_up} on {date_str} (topic={topic_id})")
    return success


def mark_completed(
    market: str,
    topic_id: str,
    state_dir: Optional[str] = None,
    now: Optional[datetime] = None,
    extra_metadata: Optional[dict] = None,
) -> bool:
    """Mark daily market production as COMPLETED."""
    m_up = (market or "EN").upper()
    date_str = vn_today(now)
    lock_path = _get_lock_file_path(m_up, state_dir, now)

    payload = {
        "market": m_up,
        "vn_date": date_str,
        "status": "COMPLETED",
        "topic_id": topic_id,
        "pid": os.getpid(),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if extra_metadata:
        payload.update(extra_metadata)

    success = _atomic_write_json(lock_path, payload)
    if success:
        logger.info(f"[daily_market_lock] Marked COMPLETED lock for {m_up} on {date_str} (topic={topic_id})")
    return success


def release_lock(market: str, state_dir: Optional[str] = None, now: Optional[datetime] = None) -> bool:
    """Release or remove daily lock (e.g. after catastrophic early failure)."""
    m_up = (market or "EN").upper()
    lock_path = _get_lock_file_path(m_up, state_dir, now)
    try:
        if lock_path.exists():
            lock_path.unlink()
            logger.info(f"[daily_market_lock] Released lock for {m_up}")
            return True
    except Exception as e:
        logger.warning(f"[daily_market_lock] Failed to remove lock file {lock_path}: {e}")
    return False
