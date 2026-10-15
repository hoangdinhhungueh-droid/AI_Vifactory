"""
app/services/daily_market_lock.py — DAILY MARKET PRODUCTION LOCK & QUOTA GUARD
Mandate:
  1. Prevents duplicate scraping and duplicate episode production for the same market on the same day.
  2. Anchored strictly to Vietnam Timezone (Asia/Ho_Chi_Minh, UTC+7).
  3. Two-tier state:
     - IN_PROGRESS: Exclusively acquired with O_CREAT|O_EXCL and TTL (default 6h).
     - COMPLETED: Hard lock for the remainder of the Vietnam calendar day.
  4. Authoritative check across:
     - Lock file: <STATE_DIR>/b1_daily_lock/{MARKET}_{YYYY-MM-DD}.json
     - Permanent History Registry (topic_history_registry)
     - Episode directories with completed run_manifest.json
  5. Fail-closed on corruption with explicit Operator Alert and recovery documentation.
  6. Cross-platform safe: Windows & Linux compatible.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

VN_TZ = timezone(timedelta(hours=7))
DEFAULT_TTL_SECONDS = 21600  # 6 hours


def _validate_market(market: Any) -> str:
    """Validate and normalize market string; reject None, empty or non-string."""
    if not market or not isinstance(market, str) or not market.strip():
        raise ValueError(f"Market identifier must be a non-empty string, got: {market!r}")
    return market.strip().upper()


from core.paths import resolve_state_dir  # Canonical authority re-exported for backwards compatibility


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
    m_up = _validate_market(market)
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


def _emit_operator_corrupt_alert(lock_path: Path, error_msg: str, market: str, date_str: str) -> None:
    """Emit high-priority alert when corrupt daily lock forces fail-closed exit."""
    alert_text = (
        f"🚨 <b>[OPERATOR ALERT: CORRUPT DAILY LOCK - RULE 118 FAIL-CLOSED]</b>\n"
        f"Market: <code>{market}</code> | Date: <code>{date_str}</code>\n"
        f"Lock file <code>{lock_path}</code> is unreadable/corrupt:\n"
        f"<code>{error_msg[:250]}</code>\n"
        f"🛑 <b>Hành động:</b> Đã kích hoạt chốt chặn Fail-Closed, từ chối cào tự động để bảo vệ hệ thống.\n"
        f"🔧 <b>Quy trình khôi phục:</b> Xóa file lock hỏng bằng tay hoặc chạy pipeline với cờ <code>--force</code> (hoặc <code>B1_FORCE_CRAWL=1</code>)."
    )
    logger.critical(alert_text)
    try:
        from app.services.telegram_buttons import send_telegram_broadcast
        send_telegram_broadcast(alert_text)
    except Exception:
        pass


def cleanup_corrupt_quarantines(directory: Path, max_age_seconds: float = 86400 * 7, max_files: int = 5) -> int:
    """Retention policy for *.corrupt.* quarantine files to prevent unbounded accumulation (Rule 125 & Boss Item 14).

    Prunes files exceeding max_age_seconds or keeping at most the newest max_files.
    Returns count of pruned files.
    """
    if not directory.exists():
        return 0
    corrupt_files = sorted(
        directory.glob("*.corrupt.*"),
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
        reverse=True,
    )
    pruned = 0
    now = time.time()
    for idx, cf in enumerate(corrupt_files):
        try:
            age = now - cf.stat().st_mtime
            if idx >= max_files or age > max_age_seconds:
                cf.unlink(missing_ok=True)
                pruned += 1
        except OSError as cf_err:
            logger.warning(f"[daily_market_lock] Error pruning corrupt quarantine file {cf}: {cf_err}")
    return pruned


def _quarantine_corrupt_lock(lock_path: Path) -> Path:
    """Quarantines unreadable lock file to *.corrupt.<epoch> and prunes stale quarantines."""
    ts = int(time.time())
    corrupt_path = lock_path.with_name(f"{lock_path.name}.corrupt.{ts}")
    try:
        os.replace(str(lock_path), str(corrupt_path))
    except OSError as q_err:
        logger.warning(f"[daily_market_lock] Error quarantining corrupt lock {lock_path} to {corrupt_path}: {q_err}")
    cleanup_corrupt_quarantines(lock_path.parent)
    return corrupt_path


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
                            'registry_completed', 'episode_dir_completed', 'stale_lock', 'not_produced_yet')
        - details: dictionary with topic_id, vn_date, etc.
    """
    m_up = _validate_market(market)

    if force or os.getenv("B1_FORCE_CRAWL") == "1":
        return False, "forced_override", {"market": m_up, "forced": True}

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
                    _quarantine_corrupt_lock(lock_path)
                    _emit_operator_corrupt_alert(lock_path, "File is completely empty (0 bytes)", m_up, date_str)
                    return True, "corrupt_lock_fail_closed", {"market": m_up, "date": date_str}
                data = json.loads(content)
                if not isinstance(data, dict):
                    _quarantine_corrupt_lock(lock_path)
                    _emit_operator_corrupt_alert(lock_path, f"Top-level JSON is not an object: {type(data)}", m_up, date_str)
                    return True, "corrupt_lock_fail_closed", {"market": m_up, "date": date_str}
        except Exception as e:
            _quarantine_corrupt_lock(lock_path)
            _emit_operator_corrupt_alert(lock_path, str(e), m_up, date_str)
            return True, "corrupt_lock_fail_closed", {"market": m_up, "date": date_str, "error": str(e)}

        status = data.get("status", "").upper()
        if status == "COMPLETED":
            return True, "lock_completed", data

        if status in ("EXHAUSTED_TODAY", "EXHAUSTED"):
            return True, "lock_exhausted_today", data

        if status == "IN_PROGRESS":
            created_at_str = data.get("created_at_utc")
            ttl = int(data.get("ttl_seconds", DEFAULT_TTL_SECONDS))
            if created_at_str:
                try:
                    c_dt = datetime.fromisoformat(created_at_str)
                    if c_dt.tzinfo is None:
                        c_dt = c_dt.replace(tzinfo=timezone.utc)
                    age_seconds = (vn_now(now).astimezone(timezone.utc) - c_dt).total_seconds()
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
                if task_id in ("REJECTED_OR_HANDLED", "HANDLED", ""):
                    continue

                rec_at = entry.get("recorded_at")
                if rec_at:
                    try:
                        rec_dt = datetime.fromisoformat(rec_at)
                        rec_vn_date = vn_today(rec_dt)
                        if rec_vn_date == date_str:
                            details = {
                                "market": m_up,
                                "vn_date": date_str,
                                "status": "COMPLETED",
                                "topic_id": task_id,
                                "raw_term": entry.get("raw_term", ""),
                                "source": "history_registry_auto_healed",
                                "completed_at_utc": vn_now(now).astimezone(timezone.utc).isoformat(),
                            }
                            _atomic_write_json(lock_path, details)
                            return True, "registry_completed", details
                    except Exception:
                        pass
        except Exception as reg_err:
            logger.debug(f"[daily_market_lock] Registry check notice: {reg_err}")

    # 3. Check Episode directories on disk
    if check_episodes:
        episodes_roots = []
        if state_dir and (Path(state_dir) / "episodes").is_dir():
            episodes_roots.append(Path(state_dir) / "episodes")
        episodes_roots.extend([
            Path("/var/vf/episodes"),
            Path(__file__).resolve().parent.parent.parent / "episodes",
        ])
        try:
            if os.path.isdir("/root"):
                episodes_roots.append(Path("/root/video_factory/episodes"))
        except (PermissionError, OSError):
            pass

        for ep_root in episodes_roots:
            try:
                if not ep_root.is_dir():
                    continue
                prefix = f"{m_up}_EP"
                for ep_dir in ep_root.iterdir():
                    if not ep_dir.is_dir() or not ep_dir.name.startswith(prefix):
                        continue
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
                                    "completed_at_utc": vn_now(now).astimezone(timezone.utc).isoformat(),
                                }
                                _atomic_write_json(lock_path, details)
                                return True, "episode_dir_completed", details
                        except (PermissionError, OSError):
                            pass
            except (PermissionError, OSError) as ep_err:
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
    """Exclusively acquire IN_PROGRESS daily lock for market using O_CREAT | O_EXCL.
    Guarantees mutual exclusion between competing processes.
    """
    m_up = _validate_market(market)
    date_str = vn_today(now)
    lock_path = _get_lock_file_path(m_up, state_dir, now)

    now_utc = vn_now(now).astimezone(timezone.utc)
    payload = {
        "market": m_up,
        "vn_date": date_str,
        "status": "IN_PROGRESS",
        "topic_id": topic_id,
        "pid": os.getpid(),
        "created_at_utc": now_utc.isoformat(),
        "updated_at_utc": now_utc.isoformat(),
        "ttl_seconds": ttl_seconds,
    }

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Exclusive atomic creation
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info(f"[daily_market_lock] Exclusively acquired IN_PROGRESS lock for {m_up} on {date_str} (topic={topic_id})")
        return True
    except FileExistsError:
        # Lock exists: check if stale
        try:
            with open(lock_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if existing.get("status") == "IN_PROGRESS":
                c_str = existing.get("created_at_utc")
                if c_str:
                    c_dt = datetime.fromisoformat(c_str)
                    if c_dt.tzinfo is None:
                        c_dt = c_dt.replace(tzinfo=timezone.utc)
                    age = (now_utc - c_dt).total_seconds()
                    if age > ttl_seconds:
                        logger.warning(
                            f"[daily_market_lock] Overwriting stale IN_PROGRESS lock for {m_up} "
                            f"(age={int(age)}s > {ttl_seconds}s)"
                        )
                        return _atomic_write_json(lock_path, payload)
        except Exception as ex:
            logger.error(f"[daily_market_lock] Error inspecting existing lock {lock_path}: {ex}")
        return False
    except Exception as e:
        logger.error(f"[daily_market_lock] Unexpected error acquiring lock {lock_path}: {e}")
        return False


def mark_completed(
    market: str,
    topic_id: str,
    state_dir: Optional[str] = None,
    now: Optional[datetime] = None,
    extra_metadata: Optional[dict] = None,
) -> bool:
    """Mark daily market production as COMPLETED."""
    m_up = _validate_market(market)
    date_str = vn_today(now)
    lock_path = _get_lock_file_path(m_up, state_dir, now)

    payload = {
        "market": m_up,
        "vn_date": date_str,
        "status": "COMPLETED",
        "topic_id": topic_id,
        "pid": os.getpid(),
        "completed_at_utc": vn_now(now).astimezone(timezone.utc).isoformat(),
    }
    if extra_metadata:
        payload.update(extra_metadata)

    success = _atomic_write_json(lock_path, payload)
    if success:
        logger.info(f"[daily_market_lock] Marked COMPLETED lock for {m_up} on {date_str} (topic={topic_id})")
    return success


def mark_exhausted_today(
    market: str,
    scan_count: int,
    state_dir: Optional[str] = None,
    now: Optional[datetime] = None,
    extra_metadata: Optional[dict] = None,
) -> bool:
    """Mark daily market production as EXHAUSTED_TODAY.
    When a daily scan evaluates all N candidates without any passing,
    this lock ensures automated cron/scheduler will NOT re-run in loop today,
    while permitting the next day's scheduled market to run normally.
    Manual re-runs can still bypass using --force.
    """
    m_up = _validate_market(market)
    date_str = vn_today(now)
    lock_path = _get_lock_file_path(m_up, state_dir, now)

    payload = {
        "market": m_up,
        "vn_date": date_str,
        "status": "EXHAUSTED_TODAY",
        "scan_count": scan_count,
        "pid": os.getpid(),
        "exhausted_at_utc": vn_now(now).astimezone(timezone.utc).isoformat(),
    }
    if extra_metadata:
        payload.update(extra_metadata)

    success = _atomic_write_json(lock_path, payload)
    if success:
        logger.info(f"[daily_market_lock] Marked EXHAUSTED_TODAY lock for {m_up} on {date_str} (scan_count={scan_count})")
    return success


def release_lock(market: str, state_dir: Optional[str] = None, now: Optional[datetime] = None) -> bool:
    """Release or remove daily lock (e.g. after catastrophic early failure)."""
    m_up = _validate_market(market)
    lock_path = _get_lock_file_path(m_up, state_dir, now)
    try:
        if lock_path.exists():
            lock_path.unlink()
            logger.info(f"[daily_market_lock] Released lock for {m_up}")
            return True
    except Exception as e:
        logger.warning(f"[daily_market_lock] Failed to remove lock file {lock_path}: {e}")
    return False
