#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/daily_market_lock.py — Production Daily Market Lock Engine (Rule 118, 125, 126).

Enforces Single Daily Production Episode per Market (EN, VN, JA, KO).
Authoritative State Machine:
  - IN_PROGRESS: Exclusively acquired before any live crawl or LLM viability evaluations.
                 Guarantees atomic mutual exclusion across racing crons via O_CREAT | O_EXCL.
  - COMPLETED:   Stamped upon successful B3 production commit. Locks out future daily runs.
  - EXHAUSTED_TODAY: Stamped when all daily candidates fail Viability Gate (>= 8.0/10).
  - EXHAUSTED_OFFHOURS: Short-TTL lock for pre-06:00 AM VN runs, expiring at 06:00 AM VN.
  - CORRUPT_FAIL_CLOSED: Persistent fail-closed seal on unparseable/corrupt lock files.
  - COMMITTED_PENDING_RENDER: Distinct state for registry-committed topics awaiting render.

Holder verification (PID + UUID Token) is strictly required for mutations:
never unlink or overwrite a lock the caller does not own (Boss Item 14).
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core.atomic_io import atomic_write_json, cleanup_corrupt_quarantines
from core.paths import resolve_episodes_dir, resolve_state_dir

logger = logging.getLogger(__name__)

VN_TZ = timezone(timedelta(hours=7))
DEFAULT_TTL_SECONDS = 14400  # 4 hours
MIN_PRODUCTION_HOUR_VN = 6    # 06:00 AM VN minimum production hour


def _validate_market(market: Any) -> str:
    """Validate and normalize market identifier; reject non-string, empty, or whitespace."""
    if not market or not isinstance(market, str) or not market.strip():
        raise ValueError(f"Market identifier must be a non-empty string, got: {market!r}")
    return market.strip().upper()


def vn_now(override: Optional[datetime] = None) -> datetime:
    """Return current datetime anchored to Asia/Ho_Chi_Minh (UTC+7)."""
    if override is not None:
        if override.tzinfo is None:
            return override.replace(tzinfo=VN_TZ)
        return override.astimezone(VN_TZ)
    return datetime.now(VN_TZ)


def vn_today(now: Optional[datetime] = None) -> str:
    """Return current date string YYYY-MM-DD in Asia/Ho_Chi_Minh timezone."""
    return vn_now(now).strftime("%Y-%m-%d")


def _get_lock_file_path(market: str, state_dir: Optional[str] = None, now: Optional[datetime] = None) -> Path:
    base_dir = Path(state_dir) if state_dir else resolve_state_dir()
    locks_dir = base_dir / "b1_daily_lock"
    m_up = _validate_market(market)
    date_str = vn_today(now)
    return locks_dir / f"{m_up}_{date_str}.json"


def _emit_operator_corrupt_alert(lock_path: Path, error_msg: str, market: str, date_str: str) -> None:
    alert_text = (
        f"🚨 <b>[FAIL-CLOSED LOCK INTEGRITY ALERT - RULE 118]</b>\n"
        f"Phát hiện file lock bị hỏng/rỗng tại: <code>{lock_path}</code>\n"
        f"Thị trường: <b>{market}</b> | Ngày VN: <b>{date_str}</b>\n"
        f"Lỗi: <code>{error_msg}</code>\n"
        f"🛑 <b>Hành động:</b> Đã kích hoạt chốt chặn Fail-Closed, từ chối cào tự động để bảo vệ hệ thống.\n"
        f"🔧 <b>Quy trình khôi phục:</b> Xóa file lock hỏng bằng tay hoặc chạy pipeline với cờ <code>--force</code> (hoặc <code>B1_FORCE_CRAWL=1</code>)."
    )
    logger.critical(alert_text)
    try:
        from app.services.telegram_buttons import send_telegram_broadcast
        send_telegram_broadcast(alert_text)
    except Exception as e:
        logger.error(f"[daily_market_lock] Failed to emit operator corrupt alert to Telegram: {type(e).__name__}: {e}")


def _quarantine_and_seal_corrupt_lock(
    lock_path: Path,
    error_msg: str,
    market: str,
    date_str: str,
    now: Optional[datetime] = None,
) -> Path:
    """Quarantines unreadable lock file to *.corrupt.<epoch>, cleans up old quarantines,
    and writes persistent CORRUPT_FAIL_CLOSED marker so subsequent ticks stay fail-closed (Boss Item 16).
    """
    ts = int(time.time())
    corrupt_path = lock_path.with_name(f"{lock_path.name}.corrupt.{ts}")
    try:
        os.replace(str(lock_path), str(corrupt_path))
    except OSError as q_err:
        logger.warning(f"[daily_market_lock] Error quarantining corrupt lock {lock_path} to {corrupt_path}: {q_err}")
    cleanup_corrupt_quarantines(lock_path.parent)

    marker_payload = {
        "market": market,
        "vn_date": date_str,
        "status": "CORRUPT_FAIL_CLOSED",
        "quarantined_to": corrupt_path.name,
        "quarantined_at_utc": vn_now(now).astimezone(timezone.utc).isoformat(),
        "error": str(error_msg),
    }
    try:
        atomic_write_json(lock_path, marker_payload)
    except Exception as w_err:
        logger.error(f"[daily_market_lock] Failed to write CORRUPT_FAIL_CLOSED marker: {w_err}")

    _emit_operator_corrupt_alert(lock_path, error_msg, market, date_str)
    return corrupt_path


def is_market_done_today(
    market: str,
    state_dir: Optional[str] = None,
    now: Optional[datetime] = None,
    force: bool = False,
    check_registry: bool = True,
    check_episodes: bool = True,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Pure read-only check whether the given market has completed or has active work today.
    DOES NOT perform mutating writes or directory creation (Boss Item 16 & 20).

    Returns:
        (is_done, reason, details)
        - is_done: True -> B1 MUST SKIP CRAWL
        - reason: identifier ('forced_override', 'lock_completed', 'lock_in_progress',
                            'lock_exhausted_today', 'lock_exhausted_offhours',
                            'registry_committed_pending_render', 'episode_dir_completed',
                            'registry_unreadable_fail_closed', 'episode_scan_error_fail_closed',
                            'corrupt_lock_fail_closed', 'stale_lock', 'not_produced_yet')
        - details: dictionary with topic_id, vn_date, etc.
    """
    m_up = _validate_market(market)

    if force or os.getenv("B1_FORCE_CRAWL") == "1":
        return False, "forced_override", {"market": m_up, "forced": True}

    date_str = vn_today(now)
    lock_path = _get_lock_file_path(m_up, state_dir, now)

    stale_lock_found = False
    stale_data = {}

    # 1. Check lock file (pure read-only: fail-closed on corrupt content without mutating disk)
    if lock_path.exists():
        try:
            with open(lock_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    logger.error(f"[daily_market_lock] Lock file is empty: {lock_path} (fail-closed)")
                    return True, "corrupt_lock_fail_closed", {"market": m_up, "date": date_str, "error": "empty file"}
                data = json.loads(content)
                if not isinstance(data, dict):
                    logger.error(f"[daily_market_lock] Lock JSON is not a dict: {lock_path} (fail-closed)")
                    return True, "corrupt_lock_fail_closed", {"market": m_up, "date": date_str, "error": "non-dict root"}
        except Exception as e:
            logger.error(f"[daily_market_lock] Corrupt lock file {lock_path} (fail-closed): {e}")
            return True, "corrupt_lock_fail_closed", {"market": m_up, "date": date_str, "error": str(e)}

        status = data.get("status", "").upper()
        if status == "COMPLETED":
            return True, "lock_completed", data
        elif status in ("EXHAUSTED_TODAY", "EXHAUSTED"):
            return True, "lock_exhausted_today", data
        elif status in ("EXHAUSTED_OFFHOURS", "OFFHOURS_THROTTLED"):
            now_v = vn_now(now)
            if now_v.hour < MIN_PRODUCTION_HOUR_VN:
                return True, "lock_exhausted_offhours", data
            else:
                logger.info(
                    f"[daily_market_lock] EXHAUSTED_OFFHOURS lock expired at 06:00 VN for {m_up}. "
                    f"Permitting scheduled morning production."
                )
                stale_lock_found = True
                stale_data = data
        elif status == "CORRUPT_FAIL_CLOSED":
            return True, "corrupt_lock_fail_closed", data
        elif status == "IN_PROGRESS":
            created_at_str = data.get("created_at_utc")
            ttl = int(data.get("ttl_seconds", DEFAULT_TTL_SECONDS))
            if not created_at_str:
                logger.warning(
                    f"[daily_market_lock] IN_PROGRESS lock missing created_at_utc for {m_up} on {date_str}. Failing closed (Boss Item 16)."
                )
                return True, "lock_in_progress", data

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
        else:
            logger.warning(
                f"[daily_market_lock] Unrecognized lock status '{status}' for {m_up} on {date_str}. Failing closed (Boss Item 16)."
            )
            return True, f"lock_unrecognized_{status.lower()}", data

    # 2. Check topic_history_registry (Pure Read, Fail-Closed on Unexpected Exceptions - Boss Item 15 & 16)
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
                        if rec_dt.tzinfo is None:
                            rec_dt = rec_dt.replace(tzinfo=timezone.utc)
                        rec_vn_date = vn_today(rec_dt)
                        if rec_vn_date == date_str:
                            details = {
                                "market": m_up,
                                "vn_date": date_str,
                                "status": "COMMITTED_PENDING_RENDER",
                                "topic_id": task_id,
                                "raw_term": entry.get("raw_term", ""),
                                "source": "history_registry",
                                "recorded_at": rec_at,
                            }
                            return True, "registry_committed_pending_render", details
                    except (ValueError, TypeError, KeyError) as parse_err:
                        logger.debug(f"[daily_market_lock] Registry date parse notice: {parse_err}")
        except Exception as reg_err:
            logger.error(f"[daily_market_lock] Registry unreadable (fail-closed): {reg_err}")
            return True, "registry_unreadable_fail_closed", {"market": m_up, "error": str(reg_err)}

    # 3. Check Episode directories on disk (Pure Read, No Side-Effect Mkdir - Boss Item 15 & 16)
    if check_episodes:
        episodes_roots = []
        if state_dir:
            custom_ep = Path(state_dir) / "episodes"
            if custom_ep.is_dir() and custom_ep not in episodes_roots:
                episodes_roots.append(custom_ep)

        canon_ep = resolve_episodes_dir(ensure_dir=False)
        if canon_ep.is_dir() and canon_ep not in episodes_roots:
            episodes_roots.append(canon_ep)

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
                            with open(manifest_file, "r", encoding="utf-8") as mf:
                                m_data = json.load(mf)
                            if not isinstance(m_data, dict):
                                continue
                            m_status = str(m_data.get("status", "")).lower()
                            if m_status in ("ok", "done", "completed", "success"):
                                m_ts_str = m_data.get("completed_at") or m_data.get("created_at") or m_data.get("timestamp")
                                if m_ts_str:
                                    try:
                                        m_dt = datetime.fromisoformat(m_ts_str)
                                        m_vn_date = vn_today(m_dt)
                                    except (ValueError, TypeError):
                                        m_vn_date = vn_today(datetime.fromtimestamp(manifest_file.stat().st_mtime, timezone.utc))
                                else:
                                    m_vn_date = vn_today(datetime.fromtimestamp(manifest_file.stat().st_mtime, timezone.utc))

                                if m_vn_date == date_str:
                                    details = {
                                        "market": m_up,
                                        "vn_date": date_str,
                                        "status": "COMPLETED",
                                        "topic_id": ep_dir.name,
                                        "source": "episode_dir_completed",
                                    }
                                    return True, "episode_dir_completed", details
                        except (json.JSONDecodeError, OSError) as mf_err:
                            logger.warning(f"[daily_market_lock] Error inspecting episode manifest {manifest_file}: {mf_err}")
            except (PermissionError, OSError) as ep_err:
                logger.error(f"[daily_market_lock] Episode check unreadable (fail-closed): {ep_err}")
                return True, "episode_scan_error_fail_closed", {"market": m_up, "error": str(ep_err)}

    if stale_lock_found:
        return False, "stale_lock", stale_data
    return False, "not_produced_yet", {"market": m_up, "date": date_str}


def reconcile_daily_lock(
    market: str,
    state_dir: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """Explicit mutating reconciler to stamp a daily lock from registry or completed episodes (Boss Item 16).
    Separated from pure-read `is_market_done_today` to avoid unwanted side effects during status queries.
    """
    m_up = _validate_market(market)
    is_done, reason, details = is_market_done_today(m_up, state_dir=state_dir, now=now)
    if is_done and reason in ("registry_committed_pending_render", "episode_dir_completed"):
        lock_path = _get_lock_file_path(m_up, state_dir, now)
        details_to_write = dict(details)
        details_to_write["reconciled_at_utc"] = vn_now(now).astimezone(timezone.utc).isoformat()
        try:
            atomic_write_json(lock_path, details_to_write)
            logger.info(f"[daily_market_lock] Reconciled daily lock for {m_up}: {reason}")
            return details_to_write
        except Exception as e:
            logger.error(f"[daily_market_lock] Failed to reconcile daily lock for {m_up}: {e}")
    return None


def acquire_in_progress(
    market: str,
    topic_id: str = "",
    state_dir: Optional[str] = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: Optional[datetime] = None,
    owner_pid: Optional[int] = None,
    lock_token: Optional[str] = None,
) -> bool:
    """Exclusively acquire IN_PROGRESS daily lock for market using O_CREAT | O_EXCL.
    Generates unique lock_token and records owner_pid for holder verification (Boss Item 14).
    Guarantees mutual exclusion between competing processes.
    """
    m_up = _validate_market(market)
    date_str = vn_today(now)
    lock_path = _get_lock_file_path(m_up, state_dir, now)

    pid = owner_pid or os.getpid()
    token = lock_token or uuid.uuid4().hex
    now_utc = vn_now(now).astimezone(timezone.utc)

    payload = {
        "market": m_up,
        "vn_date": date_str,
        "status": "IN_PROGRESS",
        "topic_id": topic_id,
        "pid": pid,
        "lock_token": token,
        "created_at_utc": now_utc.isoformat(),
        "updated_at_utc": now_utc.isoformat(),
        "ttl_seconds": ttl_seconds,
    }

    payload_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        try:
            os.write(fd, payload_bytes)
        finally:
            os.close(fd)
        logger.info(f"[daily_market_lock] Exclusively acquired IN_PROGRESS lock for {m_up} on {date_str} (pid={pid}, token={token[:8]})")
        return True
    except FileExistsError:
        # Lock exists: inspect for stale takeover or expired off-hours lock
        try:
            with open(lock_path, "r", encoding="utf-8") as f:
                raw_stale = f.read().strip()
            if not raw_stale:
                try:
                    mtime = lock_path.stat().st_mtime
                    if (time.time() - mtime) < 2.0:
                        time.sleep(0.05)
                        with open(lock_path, "r", encoding="utf-8") as f:
                            raw_stale = f.read().strip()
                except OSError:
                    pass
            if not raw_stale:
                _quarantine_and_seal_corrupt_lock(lock_path, "File is completely empty (0 bytes)", m_up, date_str, now)
                return False
            try:
                existing = json.loads(raw_stale)
            except Exception as j_err:
                try:
                    mtime = lock_path.stat().st_mtime
                    if (time.time() - mtime) < 2.0:
                        time.sleep(0.05)
                        with open(lock_path, "r", encoding="utf-8") as f:
                            raw_stale = f.read().strip()
                        existing = json.loads(raw_stale)
                    else:
                        _quarantine_and_seal_corrupt_lock(lock_path, str(j_err), m_up, date_str, now)
                        return False
                except Exception as j2_err:
                    _quarantine_and_seal_corrupt_lock(lock_path, str(j2_err), m_up, date_str, now)
                    return False

            ex_status = existing.get("status")

            # Check if existing lock is an expired off-hours lock OR stale IN_PROGRESS lock
            is_expired_offhours = (
                ex_status in ("EXHAUSTED_OFFHOURS", "OFFHOURS_THROTTLED")
                and vn_now(now).hour >= MIN_PRODUCTION_HOUR_VN
            )
            is_stale_in_progress = False
            if ex_status == "IN_PROGRESS":
                c_str = existing.get("created_at_utc")
                if c_str:
                    c_dt = datetime.fromisoformat(c_str)
                    if c_dt.tzinfo is None:
                        c_dt = c_dt.replace(tzinfo=timezone.utc)
                    age = (now_utc - c_dt).total_seconds()
                    rec_ttl = int(existing.get("ttl_seconds", ttl_seconds))
                    if age > rec_ttl:
                        from app.services.alert_cooldown import is_pid_alive
                        ex_pid = existing.get("pid")
                        if ex_pid and isinstance(ex_pid, int) and is_pid_alive(ex_pid):
                            is_stale_in_progress = False
                            logger.info(
                                f"[daily_market_lock] IN_PROGRESS lock for {m_up} age={int(age)}s > ttl={rec_ttl}s, "
                                f"but holder PID {ex_pid} is still alive. Refusing stale takeover."
                            )
                        else:
                            is_stale_in_progress = True

            if is_expired_offhours or is_stale_in_progress:
                action_desc = "expired off-hours" if is_expired_offhours else "stale IN_PROGRESS"
                logger.warning(
                    f"[daily_market_lock] Attempting exclusive takeover of {action_desc} lock for {m_up}"
                )
                takeover_lock = lock_path.with_suffix(lock_path.suffix + ".takeover")
                try:
                    fd_takeover = os.open(str(takeover_lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                except FileExistsError:
                    try:
                        t_age = time.time() - takeover_lock.stat().st_mtime
                        if t_age > 10.0:
                            takeover_lock.unlink(missing_ok=True)
                    except OSError:
                        pass
                    logger.debug(f"[daily_market_lock] Lost takeover race to another contender for {m_up}")
                    return False
                except OSError as tok_err:
                    logger.debug(f"[daily_market_lock] Takeover mutex error for {m_up}: {tok_err}")
                    return False

                try:
                    try:
                        with open(lock_path, "r", encoding="utf-8") as rf:
                            current_content = rf.read().strip()
                        current_data = json.loads(current_content)
                    except Exception as recheck_err:
                        logger.warning(f"[daily_market_lock] Error re-reading lock under mutex: {recheck_err}")
                        return False

                    curr_status = current_data.get("status")
                    curr_still_expired = (
                        curr_status in ("EXHAUSTED_OFFHOURS", "OFFHOURS_THROTTLED")
                        and vn_now(now).hour >= MIN_PRODUCTION_HOUR_VN
                    )
                    curr_still_stale = False
                    if curr_status == "IN_PROGRESS":
                        curr_c_str = current_data.get("created_at_utc")
                        if curr_c_str:
                            curr_c_dt = datetime.fromisoformat(curr_c_str)
                            if curr_c_dt.tzinfo is None:
                                curr_c_dt = curr_c_dt.replace(tzinfo=timezone.utc)
                            curr_age = (now_utc - curr_c_dt).total_seconds()
                            curr_rec_ttl = int(current_data.get("ttl_seconds", ttl_seconds))
                            if curr_age > curr_rec_ttl:
                                from app.services.alert_cooldown import is_pid_alive
                                curr_pid = current_data.get("pid")
                                if not (curr_pid and isinstance(curr_pid, int) and is_pid_alive(curr_pid)):
                                    curr_still_stale = True

                    if not (curr_still_expired or curr_still_stale):
                        logger.info(f"[daily_market_lock] Lock {lock_path} no longer stale under mutex, aborting takeover")
                        return False

                    tmp_new = lock_path.with_name(f"{lock_path.name}.tmp_{pid}_{uuid.uuid4().hex}")
                    try:
                        with open(tmp_new, "w", encoding="utf-8") as f_tmp:
                            json.dump(payload, f_tmp, ensure_ascii=False, indent=2)
                            f_tmp.flush()
                            try:
                                os.fsync(f_tmp.fileno())
                            except OSError:
                                pass
                        os.replace(str(tmp_new), str(lock_path))
                        logger.info(f"[daily_market_lock] Won exclusive takeover of {action_desc} lock for {m_up} on {date_str}")
                        return True
                    except OSError as rep_err:
                        logger.error(f"[daily_market_lock] Failed atomic replace during takeover: {rep_err}")
                        return False
                    finally:
                        tmp_new.unlink(missing_ok=True)
                finally:
                    try:
                        os.close(fd_takeover)
                    except OSError:
                        pass
                    takeover_lock.unlink(missing_ok=True)
        except Exception as ex:
            logger.error(f"[daily_market_lock] Error inspecting existing lock {lock_path}: {ex}")
        return False
    except Exception as e:
        logger.error(f"[daily_market_lock] Unexpected error acquiring lock {lock_path}: {e}")
        return False


def get_current_lock_token(market: str, state_dir: Optional[str] = None, now: Optional[datetime] = None) -> Optional[str]:
    """Retrieve the current lock_token from disk for given market today."""
    lock_path = _get_lock_file_path(market, state_dir, now)
    if not lock_path.exists():
        return None
    try:
        with open(lock_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("lock_token")
    except Exception:
        return None


def _verify_lock_ownership(
    lock_path: Path,
    expected_token: Optional[str] = None,
    expected_pid: Optional[int] = None,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Verify lock exists and belongs to expected owner (Boss Item 14)."""
    if not lock_path.exists():
        return False, None
    try:
        with open(lock_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return False, None

        if expected_token is not None:
            actual_token = data.get("lock_token")
            if not actual_token or actual_token != expected_token:
                logger.warning(
                    f"[daily_market_lock] Lock token mismatch on {lock_path}: "
                    f"held by {actual_token[:8] if actual_token else 'NONE'}, requested by {expected_token[:8]}"
                )
                return False, data

        if expected_pid is not None:
            actual_pid = data.get("pid")
            if actual_pid and actual_pid != expected_pid:
                logger.warning(
                    f"[daily_market_lock] Lock PID mismatch on {lock_path}: "
                    f"held by PID {actual_pid}, requested by PID {expected_pid}"
                )
                return False, data

        return True, data
    except Exception as e:
        logger.error(f"[daily_market_lock] Error checking lock ownership on {lock_path}: {e}")
        return False, None


def mark_completed(
    market: str,
    topic_id: str,
    state_dir: Optional[str] = None,
    now: Optional[datetime] = None,
    extra_metadata: Optional[dict] = None,
    lock_token: Optional[str] = None,
    owner_pid: Optional[int] = None,
) -> bool:
    """Mark daily market production as COMPLETED with strict holder verification (Boss Item 14)."""
    m_up = _validate_market(market)
    date_str = vn_today(now)
    lock_path = _get_lock_file_path(m_up, state_dir, now)

    pid = owner_pid or os.getpid()
    if lock_path.exists():
        verified, existing = _verify_lock_ownership(lock_path, expected_token=lock_token, expected_pid=owner_pid)
        if not verified:
            logger.error(f"[daily_market_lock] Refusing mark_completed for {m_up}: caller is not the lock holder")
            return False
        token = lock_token or (existing.get("lock_token") if existing else uuid.uuid4().hex)
    else:
        token = lock_token or uuid.uuid4().hex

    payload = {
        "market": m_up,
        "vn_date": date_str,
        "status": "COMPLETED",
        "topic_id": topic_id,
        "pid": pid,
        "lock_token": token,
        "completed_at_utc": vn_now(now).astimezone(timezone.utc).isoformat(),
    }
    if extra_metadata:
        payload.update(extra_metadata)

    try:
        atomic_write_json(lock_path, payload)
        logger.info(f"[daily_market_lock] Marked COMPLETED lock for {m_up} on {date_str} (topic={topic_id})")
        return True
    except Exception as e:
        logger.error(f"[daily_market_lock] Failed to mark COMPLETED for {m_up}: {e}")
        return False


def mark_exhausted_today(
    market: str,
    scan_count: int,
    state_dir: Optional[str] = None,
    now: Optional[datetime] = None,
    extra_metadata: Optional[dict] = None,
    allow_off_hours: bool = False,
    lock_token: Optional[str] = None,
    owner_pid: Optional[int] = None,
) -> bool:
    """Mark daily market production as EXHAUSTED_TODAY or EXHAUSTED_OFFHOURS.

    Off-Hours Throttle Policy (Boss Item 18 & Rule 118):
    Runs before 06:00 AM VN write a short-TTL EXHAUSTED_OFFHOURS lock expiring at 06:00 AM VN.
    This guarantees repeated off-hours ticks cannot re-crawl and burn quota,
    while permitting the scheduled 06:00 AM VN run to evaluate fresh morning news.
    """
    m_up = _validate_market(market)
    date_str = vn_today(now)
    lock_path = _get_lock_file_path(m_up, state_dir, now)
    now_vn = vn_now(now)
    pid = owner_pid or os.getpid()

    if lock_path.exists():
        verified, existing = _verify_lock_ownership(lock_path, expected_token=lock_token, expected_pid=owner_pid)
        if not verified:
            logger.error(f"[daily_market_lock] Refusing mark_exhausted for {m_up}: caller is not the lock holder")
            return False
        token = lock_token or (existing.get("lock_token") if existing else uuid.uuid4().hex)
    else:
        token = lock_token or uuid.uuid4().hex

    if now_vn.hour < MIN_PRODUCTION_HOUR_VN and not allow_off_hours:
        # Pre-06:00 VN off-hours: write short-TTL throttle lock expiring at 06:00 AM VN
        target_6am_vn = now_vn.replace(hour=MIN_PRODUCTION_HOUR_VN, minute=0, second=0, microsecond=0)
        offhours_ttl = max(60, int((target_6am_vn - now_vn).total_seconds()))
        payload = {
            "market": m_up,
            "vn_date": date_str,
            "status": "EXHAUSTED_OFFHOURS",
            "scan_count": scan_count,
            "pid": pid,
            "lock_token": token,
            "exhausted_at_utc": now_vn.astimezone(timezone.utc).isoformat(),
            "ttl_seconds": offhours_ttl,
            "expires_at_vn": target_6am_vn.isoformat(),
        }
        if extra_metadata:
            payload.update(extra_metadata)
        try:
            atomic_write_json(lock_path, payload)
            logger.info(
                f"[daily_market_lock] Marked EXHAUSTED_OFFHOURS lock for {m_up} on {date_str} "
                f"until 06:00 AM VN (ttl={offhours_ttl}s, scan_count={scan_count})"
            )
            return True
        except Exception as e:
            logger.error(f"[daily_market_lock] Failed to write EXHAUSTED_OFFHOURS for {m_up}: {e}")
            return False

    payload = {
        "market": m_up,
        "vn_date": date_str,
        "status": "EXHAUSTED_TODAY",
        "scan_count": scan_count,
        "pid": pid,
        "lock_token": token,
        "exhausted_at_utc": now_vn.astimezone(timezone.utc).isoformat(),
    }
    if extra_metadata:
        payload.update(extra_metadata)

    try:
        atomic_write_json(lock_path, payload)
        logger.info(f"[daily_market_lock] Marked EXHAUSTED_TODAY lock for {m_up} on {date_str} (scan_count={scan_count})")
        return True
    except Exception as e:
        logger.error(f"[daily_market_lock] Failed to mark EXHAUSTED_TODAY for {m_up}: {e}")
        return False


def release_lock(
    market: str,
    state_dir: Optional[str] = None,
    now: Optional[datetime] = None,
    lock_token: Optional[str] = None,
    owner_pid: Optional[int] = None,
) -> bool:
    """Release or remove daily lock with holder verification (Boss Item 14).
    Never unlinks a lock owned by another process.
    """
    m_up = _validate_market(market)
    lock_path = _get_lock_file_path(m_up, state_dir, now)
    if not lock_path.exists():
        return False

    # Holder verification
    if lock_token is not None or owner_pid is not None:
        verified, _ = _verify_lock_ownership(lock_path, expected_token=lock_token, expected_pid=owner_pid)
        if not verified:
            logger.warning(f"[daily_market_lock] Refusing release_lock for {m_up}: owner verification failed")
            return False

    try:
        lock_path.unlink()
        logger.info(f"[daily_market_lock] Released lock for {m_up} (token={str(lock_token)[:8]})")
        return True
    except OSError as e:
        logger.warning(f"[daily_market_lock] Failed to remove lock file {lock_path}: {e}")
        return False
