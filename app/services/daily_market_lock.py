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
import sys
import time
import uuid
from contextlib import contextmanager
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
    """Validate and normalize market identifier; normalize JA->JP and KO->KR aliases; reject non-string, empty, or whitespace."""
    if not market or not isinstance(market, str) or not market.strip():
        raise ValueError(f"Market identifier must be a non-empty string, got: {market!r}")
    m = market.strip().upper()
    if m == "JA":
        return "JP"
    if m == "KO":
        return "KR"
    return m


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


get_vn_now = vn_now



def _get_lock_file_path(
    market: str,
    state_dir: Optional[str] = None,
    now: Optional[datetime] = None,
    read_only: bool = False,
) -> Path:
    base_dir = Path(state_dir) if state_dir else resolve_state_dir(read_only=read_only)
    locks_dir = base_dir / "b1_daily_lock"
    m_up = _validate_market(market)
    date_str = vn_today(now)
    return locks_dir / f"{m_up}_{date_str}.json"


def _emit_operator_corrupt_alert(lock_path: Path, error_msg: str, market: str, date_str: str) -> None:
    if market.upper().startswith("TEST_") or os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("VF_TEST_MODE") == "1":
        logger.info(f"[{market}] Suppressed live corrupt lock alert in test environment.")
        return

    lock_name = lock_path.name
    alert_text = (
        f"🚨 <b>[FAIL-CLOSED LOCK INTEGRITY ALERT - RULE 118]</b>\n"
        f"Phát hiện file lock bất thường: <code>{lock_name}</code>\n"
        f"Thị trường: <b>{market}</b> | Ngày VN: <b>{date_str}</b>\n"
        f"Chi tiết: <code>{error_msg}</code>\n"
        f"🛑 <b>Hành động:</b> Đã kích hoạt chốt chặn Fail-Closed, dừng cào tự động để bảo vệ hệ thống.\n"
        f"🔧 <b>Xử lý:</b> Kiểm tra tính toàn vẹn của lock hoặc kích hoạt chế độ tái cào có kiểm soát."
    )
    logger.critical(alert_text)
    try:
        from app.services.telegram_buttons import send_telegram_broadcast
        send_telegram_broadcast(alert_text)
    except Exception as e:
        logger.error(f"[daily_market_lock] Failed to emit operator corrupt alert to Telegram: {type(e).__name__}: {e}")



@contextmanager
def _market_lock_mutex(lock_path: Path, timeout_sec: float = 10.0):
    """File lock mutex to serialize verify-and-mutate operations (takeover, release, mark_completed, mark_exhausted).
    Eliminates TOCTOU races between concurrent takeover and release/completion (Boss Round 12 Item 5).
    """
    mutex_path = lock_path.with_suffix(lock_path.suffix + ".mutex")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = None
    start_t = time.time()
    while True:
        try:
            fd = os.open(str(mutex_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            break
        except FileExistsError:
            try:
                m_age = time.time() - mutex_path.stat().st_mtime
                if m_age > timeout_sec:
                    mutex_path.unlink(missing_ok=True)
            except OSError as _stale_err:
                logger.debug(f"[daily_market_lock] Stale mutex inspection suppressed: {_stale_err}")
            if time.time() - start_t > timeout_sec:
                logger.warning(f"[daily_market_lock] Timed out waiting for mutex on {lock_path} after {timeout_sec}s")
                raise TimeoutError(f"Timed out acquiring mutex for {lock_path}")
            time.sleep(0.02)
        except OSError as e:
            logger.error(f"[daily_market_lock] Mutex acquisition error on {lock_path}: {e}")
            raise e
    try:
        yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError as _close_err:
                logger.debug(f"[daily_market_lock] Mutex fd close notice: {_close_err}")
        mutex_path.unlink(missing_ok=True)


HARD_MAX_IN_PROGRESS_AGE_SECONDS = 28800  # 8 hours hard cap exceeding max TTL (Boss Item 6)

def _get_current_git_sha() -> str:
    """Returns current git commit SHA for production provenance tracking (Boss Item 15).
    Delegates to core.paths.get_current_git_sha per Rule 125 single source of truth.
    """
    from core.paths import get_current_git_sha
    return get_current_git_sha()


def _get_process_start_time(pid: Optional[int] = None) -> float:
    """Returns start time of process for PID identity verification (PID reuse defense).
    Uses /proc/<pid>/stat field 22 (starttime) + /proc/stat btime on Linux (Boss Item 4).
    """
    effective_pid = pid or os.getpid()
    if sys.platform != "win32":
        stat_path = f"/proc/{effective_pid}/stat"
        if os.path.exists(stat_path):
            try:
                with open(stat_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                rparen = content.rfind(")")
                if rparen != -1:
                    fields = content[rparen + 1:].split()
                    if len(fields) > 19:
                        raw_ticks = float(fields[19])
                        clk_tck = 100.0
                        try:
                            clk_tck = float(os.sysconf(os.sysconf_names.get("SC_CLK_TCK", -1)))
                        except (AttributeError, ValueError, OSError):
                            clk_tck = 100.0
                        btime = 0.0
                        try:
                            with open("/proc/stat", "r", encoding="utf-8") as sf:
                                for sline in sf:
                                    if sline.startswith("btime "):
                                        btime = float(sline.split()[1])
                                        break
                        except Exception as _b_err:
                            logger.debug("[daily_market_lock] proc stat btime notice: %s", _b_err)
                        return btime + (raw_ticks / clk_tck)
            except Exception as _e:
                logger.debug("[daily_market_lock] proc stat field 22 notice for PID %s: %s", effective_pid, _e)
    return 0.0


def _is_lock_stale(
    data: Dict[str, Any],
    now_utc: datetime,
    default_ttl: int = DEFAULT_TTL_SECONDS,
    m_up: Optional[str] = None,
    date_str: Optional[str] = None,
    state_dir: Optional[str] = None,
    emit_alert: bool = False,
) -> Tuple[bool, str]:
    """Unified staleness predicate used for BOTH candidate pre-check and under-mutex re-check (Boss Item 4).
    Guarantees consistent decision between pre-mutex and under-mutex re-check.

    Returns:
        (is_stale, reason_description)
    """
    status = (data.get("status") or "").upper()
    if status in ("EXHAUSTED_OFFHOURS", "OFFHOURS_THROTTLED"):
        now_v = vn_now(now_utc)
        if now_v.hour >= MIN_PRODUCTION_HOUR_VN:
            return True, "expired off-hours"
        return False, "active off-hours"

    if status == "IN_PROGRESS":
        c_str = data.get("created_at_utc")
        if not c_str:
            return False, "missing created_at_utc"
        try:
            c_dt = datetime.fromisoformat(c_str)
            if c_dt.tzinfo is None:
                c_dt = c_dt.replace(tzinfo=timezone.utc)
            age = (now_utc - c_dt).total_seconds()
            rec_ttl = int(data.get("ttl_seconds", default_ttl))
            hard_max = max(rec_ttl + 7200, HARD_MAX_IN_PROGRESS_AGE_SECONDS)

            # 1. Hard max-age exceeded: unconditionally stale (PID-reuse defense - Boss Item 4 & 6)
            if age > hard_max:
                logger.warning(
                    f"[daily_market_lock] IN_PROGRESS lock age={int(age)}s exceeds hard_max {hard_max}s. "
                    f"Forcing stale takeover (PID reuse defense)."
                )
                return True, "hard_max_age_exceeded"

            # 2. TTL expiration check with PID aliveness & process start time verification
            if age > rec_ttl:
                from app.services.alert_cooldown import is_pid_alive
                ex_pid = data.get("pid")
                ex_start = float(data.get("process_start_time", 0.0))
                curr_start = _get_process_start_time(ex_pid) if ex_pid else 0.0

                is_same_proc = True
                if ex_start > 0 and curr_start > 0 and abs(curr_start - ex_start) > 2.0:
                    is_same_proc = False

                if ex_pid and isinstance(ex_pid, int) and is_pid_alive(ex_pid) and is_same_proc:
                    if emit_alert and m_up and date_str:
                        logger.warning(
                            f"[daily_market_lock] IN_PROGRESS lock for {m_up} age={int(age)}s > ttl={rec_ttl}s, "
                            f"but holder PID {ex_pid} is alive. Refusing stale takeover."
                        )
                        _emit_operator_stale_holder_alert(m_up, date_str, ex_pid, int(age), rec_ttl, state_dir=state_dir)
                    return False, "holder_alive"
                else:
                    return True, "ttl_expired_holder_dead"
        except Exception as _parse_err:
            logger.debug(f"[daily_market_lock] Staleness check timestamp parse error: {_parse_err}")
            return False, "parse_error"

    return False, "not_stale"


def _resolve_process_name(pid: int) -> str:
    """Resolves process name/cmdline for a given PID for operator triage (Boss Round 14 Item 10)."""
    try:
        if sys.platform != "win32":
            cmdline_path = Path(f"/proc/{pid}/cmdline")
            if cmdline_path.exists():
                cmd = cmdline_path.read_bytes().replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
                if cmd:
                    return cmd[:80]
        import psutil
        p = psutil.Process(pid)
        return " ".join(p.cmdline())[:80] or p.name()
    except Exception as _p_err:
        logger.debug(f"[daily_market_lock] Notice resolving process name for PID {pid}: {_p_err}")
        return "python"


def _emit_operator_stale_holder_alert(market: str, date_str: str, pid: int, age_sec: int, ttl_sec: int, state_dir: Optional[str] = None) -> None:
    """Emits operator alert when acquire_in_progress is refused for a stale-but-'alive' holder (Boss Item 6 & 10)."""
    if market.upper().startswith("TEST_") or os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("VF_TEST_MODE") == "1":
        logger.info(f"[{market}] Suppressed live stale holder alert in test environment.")
        return
    proc_name = _resolve_process_name(pid)
    alert_text = (
        f"⚠️ <b>[STALE LOCK HOLDER ALERT - RULE 118]</b>\n"
        f"Market: <b>{market}</b> | VN Date: <b>{date_str}</b>\n"
        f"Khóa IN_PROGRESS giữ bởi PID <code>{pid}</code> ({proc_name}) đã vượt TTL ({age_sec}s > {ttl_sec}s).\n"
        f"Tiến trình giữ khóa vẫn đang chạy (alive); hệ thống từ chối cướp khóa tự động để bảo toàn khế ước.\n"
        f"🔧 <b>Khắc phục:</b> Kiểm tra tiến trình PID {pid} ({proc_name}) hoặc giải phóng khóa bằng cờ <code>--force</code>."
    )
    logger.warning(alert_text)
    try:
        from app.services.alert_cooldown import should_send_alert
        from app.services.telegram_buttons import send_telegram_broadcast
        decision = should_send_alert("stale_lock_holder", market, state_dir=state_dir)
        if decision.can_send:
            sent = send_telegram_broadcast(alert_text + decision.suffix)
            if not sent:
                logger.warning(
                    f"[daily_market_lock] Telegram broadcast returned falsy for stale holder alert PID {pid} on {market}. "
                    f"FALLBACK ALERT LOGGED: {alert_text}"
                )
    except Exception as e:
        logger.warning(
            f"[daily_market_lock] Failed to broadcast stale holder alert to Telegram: {e}. "
            f"FALLBACK ALERT LOGGED: {alert_text}"
        )


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
    registry_path: Optional[str] = None,
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
    lock_path = _get_lock_file_path(m_up, state_dir, now, read_only=True)

    stale_lock_found = False
    stale_data = {}

    # 1. Check lock file (pure read-only: fail-closed on corrupt content without mutating disk)
    if lock_path.exists():
        content = ""
        try:
            try:
                with open(lock_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
            except OSError as open_err:
                logger.error(f"[daily_market_lock] Unreadable lock file {lock_path} (fail-closed): {open_err}")
                return True, "corrupt_lock_fail_closed", {"market": m_up, "date": date_str, "error": str(open_err)}

            if not content:
                # Concurrent creation grace window
                try:
                    age = time.time() - lock_path.stat().st_mtime
                    if age < 5.0:
                        time.sleep(0.05)
                        try:
                            with open(lock_path, "r", encoding="utf-8") as f:
                                content = f.read().strip()
                        except OSError as retry_err:
                            logger.debug(f"[daily_market_lock] Grace window retry read failed for {lock_path}: {retry_err}")
                except OSError as stat_err:
                    logger.debug(f"[daily_market_lock] Grace window stat failed for {lock_path}: {stat_err}")
            if not content:
                try:
                    age = time.time() - lock_path.stat().st_mtime
                    if age < 5.0:
                        logger.info(f"[daily_market_lock] Lock {lock_path} empty during concurrent write (age < 5s). Treating as lock_in_progress.")
                        return True, "lock_in_progress", {"market": m_up, "date": date_str, "status": "IN_PROGRESS"}
                except OSError as stat_err:
                    logger.debug(f"[daily_market_lock] Grace window empty stat failed for {lock_path}: {stat_err}")
                logger.error(f"[daily_market_lock] Lock file is empty: {lock_path} (fail-closed)")
                return True, "corrupt_lock_fail_closed", {"market": m_up, "date": date_str, "error": "empty file"}

            data = json.loads(content)
            if not isinstance(data, dict):
                logger.error(f"[daily_market_lock] Lock JSON is not a dict: {lock_path} (fail-closed)")
                return True, "corrupt_lock_fail_closed", {"market": m_up, "date": date_str, "error": "non-dict root"}
        except Exception as e:
            try:
                age = time.time() - lock_path.stat().st_mtime
                if age < 5.0 and not content:
                    time.sleep(0.05)
                    try:
                        with open(lock_path, "r", encoding="utf-8") as f:
                            retry_content = f.read().strip()
                        if retry_content:
                            data = json.loads(retry_content)
                            if not isinstance(data, dict):
                                return True, "corrupt_lock_fail_closed", {"market": m_up, "date": date_str, "error": "non-dict root"}
                        else:
                            return True, "lock_in_progress", {"market": m_up, "date": date_str, "status": "IN_PROGRESS"}
                    except json.JSONDecodeError as decode_err:
                        logger.error(f"[daily_market_lock] Corrupt lock file {lock_path} (fail-closed): {decode_err}")
                        return True, "corrupt_lock_fail_closed", {"market": m_up, "date": date_str, "error": str(decode_err)}
                    except Exception as retry_other_err:
                        logger.debug(f"[daily_market_lock] Grace window json retry failed: {retry_other_err}")
                        return True, "lock_in_progress", {"market": m_up, "date": date_str, "status": "IN_PROGRESS"}
                else:
                    logger.error(f"[daily_market_lock] Corrupt lock file {lock_path} (fail-closed): {e}")
                    return True, "corrupt_lock_fail_closed", {"market": m_up, "date": date_str, "error": str(e)}
            except OSError as stat_err:
                logger.error(f"[daily_market_lock] Corrupt lock file {lock_path} stat error (fail-closed): {e} (stat: {stat_err})")
                return True, "corrupt_lock_fail_closed", {"market": m_up, "date": date_str, "error": str(e)}

        status = (data.get("status") or "").upper()
        now_utc = vn_now(now).astimezone(timezone.utc)
        is_stale, stale_reason = _is_lock_stale(
            data,
            now_utc,
            default_ttl=DEFAULT_TTL_SECONDS,
            emit_alert=False,
            m_up=m_up,
            date_str=date_str,
            state_dir=state_dir,
        )
        if is_stale:
            logger.info(
                f"[daily_market_lock] Stale lock found for {m_up} on {date_str} (reason: {stale_reason}). Allowing re-run."
            )
            stale_lock_found = True
            stale_data = data
        else:
            if status == "COMPLETED":
                return True, "lock_completed", data
            elif status in ("EXHAUSTED_TODAY", "EXHAUSTED"):
                return True, "lock_exhausted_today", data
            elif status in ("EXHAUSTED_OFFHOURS", "OFFHOURS_THROTTLED"):
                return True, "lock_exhausted_offhours", data
            elif status == "CORRUPT_FAIL_CLOSED":
                return True, "corrupt_lock_fail_closed", data
            elif status == "IN_PROGRESS":
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
            reg_target = registry_path or (str(Path(state_dir) / "topic_history.json") if state_dir else None)
            history = load_history(registry_path=reg_target)
            for key, entry in history.items():
                if not isinstance(entry, dict):
                    continue
                ent_mkt = (entry.get("market") or "").upper()
                if ent_mkt != m_up:
                    continue

                task_id = str(entry.get("task_id") or "")
                status_val = str(entry.get("status") or "")
                if (
                    task_id in ("REJECTED_OR_HANDLED", "HANDLED", "")
                    or "_TEMP_" in task_id
                    or "DISPOSED" in status_val
                    or "DISPOSED" in task_id
                ):
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
        else:
            canon_ep = resolve_episodes_dir(ensure_dir=False)
            if canon_ep.is_dir() and canon_ep not in episodes_roots:
                episodes_roots.append(canon_ep)

        for ep_root in episodes_roots:
            try:
                if not ep_root.is_dir():
                    continue
                prefixes = (f"{m_up}_EP",)
                if m_up == "JP":
                    prefixes = ("JP_EP", "JA_EP")
                elif m_up == "KR":
                    prefixes = ("KR_EP", "KO_EP")
                for ep_dir in ep_root.iterdir():
                    if not ep_dir.is_dir() or not any(ep_dir.name.startswith(pfx) for pfx in prefixes):
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


def acquire_in_progress(
    market: str,
    topic_id: str = "",
    state_dir: Optional[str] = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: Optional[datetime] = None,
    owner_pid: Optional[int] = None,
    lock_token: Optional[str] = None,
    force: bool = False,
    force_override: bool = False,
) -> bool:
    """Exclusively acquire IN_PROGRESS daily lock for market using atomic creation with content.
    Generates unique lock_token and records owner_pid for holder verification.
    Guarantees mutual exclusion between competing processes.
    When force=True, forcefully acquires the lock under token ownership. Refuses to displace
    COMPLETED, EXHAUSTED_TODAY, or CORRUPT_FAIL_CLOSED unless force_override=True (Boss Round 11 Item 15).
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
        "process_start_time": _get_process_start_time(pid),
    }
    if force:
        payload["forced"] = True
        if lock_path.exists():
            try:
                ex_data = json.loads(lock_path.read_text(encoding="utf-8"))
                ex_status = (ex_data.get("status") or "").upper()
                if ex_status in ("COMPLETED", "EXHAUSTED_TODAY", "CORRUPT_FAIL_CLOSED") and not force_override:
                    logger.warning(
                        f"[daily_market_lock] Refusing force acquisition for {m_up} on {date_str}: "
                        f"lock is in terminal state '{ex_status}' and force_override=False (Boss Round 11 Item 15)"
                    )
                    return False
                payload["displaced_payload"] = ex_data
                payload["displaced_status"] = ex_status
                payload["displaced_token"] = ex_data.get("lock_token")
                payload["displaced_pid"] = ex_data.get("pid")
                logger.warning(
                    f"[daily_market_lock] Force acquisition displaced active lock holder "
                    f"(displaced_status={ex_status}, displaced_pid={ex_data.get('pid')}, displaced_token={str(ex_data.get('lock_token'))[:8]})"
                )
            except Exception as _ex_err:
                logger.debug(f"[daily_market_lock] Notice reading pre-force lock: {_ex_err}")
        atomic_write_json(lock_path, payload)
        logger.info(f"[daily_market_lock] Forcefully acquired IN_PROGRESS lock for {m_up} on {date_str} (pid={pid}, token={token[:8]})")
        return True

    payload_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = lock_path.with_name(f"{lock_path.name}.tmp.{pid}_{token[:8]}_{int(time.time()*1000)}")

    acquired = False
    try:
        with open(tmp_path, "wb") as f_tmp:
            f_tmp.write(payload_bytes)
            f_tmp.flush()
            try:
                os.fsync(f_tmp.fileno())
            except OSError as fsync_err:
                logger.debug(f"[daily_market_lock] fsync skipped on {tmp_path}: {fsync_err}")
        try:
            os.link(str(tmp_path), str(lock_path))
            acquired = True
        except FileExistsError:
            acquired = False
        except (AttributeError, PermissionError, OSError):
            # Fallback on platforms/filesystems without hardlink support
            try:
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                try:
                    os.write(fd, payload_bytes)
                finally:
                    os.close(fd)
                acquired = True
            except FileExistsError:
                acquired = False
    finally:
        tmp_path.unlink(missing_ok=True)

    if acquired:
        logger.info(f"[daily_market_lock] Exclusively acquired IN_PROGRESS lock for {m_up} on {date_str} (pid={pid}, token={token[:8]})")
        return True

    # Lock exists: inspect for stale takeover or expired off-hours lock
    try:
        raw_stale = ""
        try:
            with open(lock_path, "r", encoding="utf-8") as f:
                raw_stale = f.read().strip()
        except OSError as read_err:
            logger.debug(f"[daily_market_lock] Could not read candidate lock file {lock_path}: {read_err}")

        if not raw_stale:
            try:
                mtime = lock_path.stat().st_mtime
                if (time.time() - mtime) < 5.0:
                    time.sleep(0.05)
                    with open(lock_path, "r", encoding="utf-8") as f:
                        raw_stale = f.read().strip()
            except OSError as retry_err:
                logger.debug(f"[daily_market_lock] Retrying read after stat error on {lock_path}: {retry_err}")

        if not raw_stale:
            try:
                mtime = lock_path.stat().st_mtime
                if (time.time() - mtime) < 5.0:
                    logger.info(f"[daily_market_lock] Lock {lock_path} empty during concurrent creation (age < 5s). Treating as held IN_PROGRESS.")
                    return False
            except OSError as stat_err:
                logger.debug(f"[daily_market_lock] Secondary stat check error on {lock_path}: {stat_err}")
            _quarantine_and_seal_corrupt_lock(lock_path, "File is completely empty (0 bytes)", m_up, date_str, now)
            return False

        try:
            existing = json.loads(raw_stale)
        except Exception as j_err:
            try:
                mtime = lock_path.stat().st_mtime
                if (time.time() - mtime) < 5.0:
                    time.sleep(0.05)
                    with open(lock_path, "r", encoding="utf-8") as f:
                        raw_stale = f.read().strip()
                    existing = json.loads(raw_stale)
                else:
                    _quarantine_and_seal_corrupt_lock(lock_path, str(j_err), m_up, date_str, now)
                    return False
            except Exception:
                try:
                    mtime = lock_path.stat().st_mtime
                    if (time.time() - mtime) < 5.0:
                        logger.info(f"[daily_market_lock] Lock {lock_path} unparseable during concurrent creation (age < 5s). Treating as held IN_PROGRESS.")
                        return False
                except OSError as stat_err:
                    logger.debug(f"[daily_market_lock] Stat check error during corrupt quarantine on {lock_path}: {stat_err}")
                _quarantine_and_seal_corrupt_lock(lock_path, str(j_err), m_up, date_str, now)
                return False

        is_stale, stale_reason = _is_lock_stale(
            existing, now_utc, ttl_seconds, m_up=m_up, date_str=date_str, state_dir=state_dir, emit_alert=True
        )

        if is_stale:
            action_desc = stale_reason
            logger.warning(
                f"[daily_market_lock] Attempting exclusive takeover of {action_desc} lock for {m_up}"
            )
            try:
                with _market_lock_mutex(lock_path, timeout_sec=5.0):
                    try:
                        with open(lock_path, "r", encoding="utf-8") as rf:
                            current_content = rf.read().strip()
                        current_data = json.loads(current_content)
                    except Exception as recheck_err:
                        logger.warning(f"[daily_market_lock] Error re-reading lock under mutex: {recheck_err}")
                        return False

                    curr_still_stale, curr_stale_reason = _is_lock_stale(
                        current_data, now_utc, ttl_seconds, m_up=m_up, date_str=date_str, state_dir=state_dir, emit_alert=False
                    )

                    if not curr_still_stale:
                        logger.info(f"[daily_market_lock] Lock {lock_path} no longer stale under mutex ({curr_stale_reason}), aborting takeover")
                        return False

                    tmp_new = lock_path.with_name(f"{lock_path.name}.tmp_{pid}_{uuid.uuid4().hex}")
                    try:
                        with open(tmp_new, "w", encoding="utf-8") as f_tmp:
                            json.dump(payload, f_tmp, ensure_ascii=False, indent=2)
                            f_tmp.flush()
                            try:
                                os.fsync(f_tmp.fileno())
                            except OSError as fsync_err:
                                logger.debug(f"[daily_market_lock] fsync error on tmp_new {tmp_new}: {fsync_err}")
                        os.replace(str(tmp_new), str(lock_path))
                        logger.info(f"[daily_market_lock] Won exclusive takeover of {action_desc} lock for {m_up} on {date_str}")
                        return True
                    except OSError as rep_err:
                        logger.error(f"[daily_market_lock] Failed atomic replace during takeover: {rep_err}")
                        return False
                    finally:
                        tmp_new.unlink(missing_ok=True)
            except (TimeoutError, OSError) as tok_err:
                logger.debug(f"[daily_market_lock] Takeover mutex conflict for {m_up}: {tok_err}")
                return False
    except Exception as ex:
        logger.error(f"[daily_market_lock] Error inspecting existing lock {lock_path}: {ex}")
    return False


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
    force_unverified: bool = False,
) -> bool:
    """Mark daily market production as COMPLETED with strict holder verification (Boss Item 14)."""
    m_up = _validate_market(market)
    date_str = vn_today(now)
    lock_path = _get_lock_file_path(m_up, state_dir, now)

    pid = owner_pid or os.getpid()
    try:
        with _market_lock_mutex(lock_path, timeout_sec=10.0):
            if lock_path.exists():
                if force_unverified:
                    try:
                        prev_text = lock_path.read_text(encoding="utf-8")
                        logger.warning(
                            f"[daily_market_lock] Overwriting existing lock with force_unverified=True for {m_up} on {date_str}. "
                            f"Previous lock content: {prev_text}"
                        )
                    except OSError as _audit_err:
                        logger.debug(f"[daily_market_lock] Notice reading old lock for force audit: {_audit_err}")
                elif lock_token is None and owner_pid is None:
                    logger.error(
                        f"[daily_market_lock] Refusing unverified mark_completed for {m_up}: "
                        f"must provide lock_token, owner_pid, or force_unverified=True to overwrite held lock"
                    )
                    return False
                if not force_unverified:
                    verified, existing = _verify_lock_ownership(lock_path, expected_token=lock_token, expected_pid=owner_pid)
                    if not verified:
                        logger.error(f"[daily_market_lock] Refusing mark_completed for {m_up}: caller is not the lock holder")
                        return False
                    token = lock_token or (existing.get("lock_token") if existing else uuid.uuid4().hex)
                else:
                    token = lock_token or uuid.uuid4().hex
            else:
                if lock_token is not None:
                    logger.error(
                        f"[daily_market_lock] Refusing mark_completed for {m_up}: "
                        f"caller provided lock_token {lock_token[:8]} but lock file {lock_path} no longer exists"
                    )
                    return False
                token = uuid.uuid4().hex

            payload = {
                "market": m_up,
                "vn_date": date_str,
                "status": "COMPLETED",
                "topic_id": topic_id,
                "pid": pid,
                "lock_token": token,
                "completed_at_utc": vn_now(now).astimezone(timezone.utc).isoformat(),
                "git_sha": _get_current_git_sha(),
            }
            if extra_metadata:
                payload.update(extra_metadata)

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
    force_unverified: bool = False,
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
    try:
        with _market_lock_mutex(lock_path, timeout_sec=10.0):
            if lock_path.exists():
                if force_unverified:
                    try:
                        prev_text = lock_path.read_text(encoding="utf-8")
                        logger.warning(
                            f"[daily_market_lock] Overwriting existing lock with force_unverified=True for {m_up} on {date_str}. "
                            f"Previous lock content: {prev_text}"
                        )
                    except OSError as _audit_err:
                        logger.debug(f"[daily_market_lock] Notice reading old lock for force audit: {_audit_err}")
                elif lock_token is None and owner_pid is None:
                    logger.error(
                        f"[daily_market_lock] Refusing unverified mark_exhausted for {m_up}: "
                        f"must provide lock_token, owner_pid, or force_unverified=True to overwrite held lock"
                    )
                    return False
                if not force_unverified:
                    verified, existing = _verify_lock_ownership(lock_path, expected_token=lock_token, expected_pid=owner_pid)
                    if not verified:
                        logger.error(f"[daily_market_lock] Refusing mark_exhausted for {m_up}: caller is not the lock holder")
                        return False
                    token = lock_token or (existing.get("lock_token") if existing else uuid.uuid4().hex)
                else:
                    token = lock_token or uuid.uuid4().hex
            else:
                if lock_token is not None:
                    logger.error(
                        f"[daily_market_lock] Refusing mark_exhausted for {m_up}: "
                        f"caller provided lock_token {lock_token[:8]} but lock file {lock_path} no longer exists"
                    )
                    return False
                token = uuid.uuid4().hex

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
                    "git_sha": _get_current_git_sha(),
                }
                if extra_metadata:
                    payload.update(extra_metadata)
                atomic_write_json(lock_path, payload)
                logger.info(
                    f"[daily_market_lock] Marked EXHAUSTED_OFFHOURS lock for {m_up} on {date_str} "
                    f"until 06:00 AM VN (ttl={offhours_ttl}s, scan_count={scan_count})"
                )
                return True

            payload = {
                "market": m_up,
                "vn_date": date_str,
                "status": "EXHAUSTED_TODAY",
                "scan_count": scan_count,
                "pid": pid,
                "lock_token": token,
                "exhausted_at_utc": now_vn.astimezone(timezone.utc).isoformat(),
                "git_sha": _get_current_git_sha(),
            }
            if extra_metadata:
                payload.update(extra_metadata)

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
    force_unverified: bool = False,
) -> bool:
    """Release or remove daily lock with strict holder verification under mutex (Boss Round 12 Item 5).
    Never unlinks a lock unless verified by lock_token / owner_pid or explicit force_unverified=True.
    """
    m_up = _validate_market(market)
    lock_path = _get_lock_file_path(m_up, state_dir, now)

    try:
        with _market_lock_mutex(lock_path, timeout_sec=10.0):
            if not lock_path.exists():
                return False

            if lock_token is None and owner_pid is None and not force_unverified:
                logger.error(
                    f"[daily_market_lock] Refusing unverified release_lock for {m_up}: "
                    f"must provide lock_token, owner_pid, or force_unverified=True"
                )
                return False

            if not force_unverified:
                verified, _ = _verify_lock_ownership(lock_path, expected_token=lock_token, expected_pid=owner_pid)
                if not verified:
                    logger.warning(f"[daily_market_lock] Refusing release_lock for {m_up}: owner verification failed")
                    return False

            # If lock contains a displaced payload (from forced takeover or custom seed), restore it instead of unlinking!
            # (Boss Round 11 Item 15)
            try:
                cur_data = json.loads(lock_path.read_text(encoding="utf-8"))
            except Exception as _r_err:
                cur_data = {}
                logger.debug("[daily_market_lock] Notice reading lock before release: %s", _r_err)

            displaced = cur_data.get("displaced_payload")
            if displaced and isinstance(displaced, dict):
                atomic_write_json(lock_path, displaced)
                logger.info(
                    f"[daily_market_lock] Restored displaced lock payload (status={displaced.get('status')}) "
                    f"for {m_up} on release instead of unlinking (Boss Round 11 Item 15)."
                )
                return True

            lock_path.unlink()
            logger.info(f"[daily_market_lock] Released lock for {m_up} (token={str(lock_token)[:8]})")
            return True
    except OSError as e:
        logger.warning(f"[daily_market_lock] Failed to remove lock file {lock_path}: {e}")
        return False

