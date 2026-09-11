"""app/services/market_scheduler.py — WEEKLY STAGGERED MARKET PRODUCTION SCHEDULER
Standardized Architecture (06/09/2026):
  Prevents VPS resource exhaustion and infrastructure crashes by ensuring
  exactly 1 video is produced and published per day across target markets:
    - Monday (Thứ Hai)    & Thursday (Thứ Năm)  ➔ EN (English)
    - Tuesday (Thứ Ba)    & Friday (Thứ Sáu)    ➔ KR (Korean)
    - Wednesday (Thứ Tư)  & Saturday (Thứ Bảy)  ➔ JP (Japanese)
    - Sunday (Chủ Nhật)                         ➔ OFF (System Maintenance & B11 Dreaming)

MANDATORY TIMEZONE ANCHOR:
  All schedule evaluations strictly anchor to Vietnam Time (Asia/Ho_Chi_Minh / UTC+7).
  This prevents off-by-one calendar bugs on UTC VPS servers (e.g., 23:00 UTC = 06:00 AM VN next day).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

try:
    from zoneinfo import ZoneInfo
    VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:
    VN_TZ = timezone(timedelta(hours=7))

logger = logging.getLogger("market_scheduler")

# Python date.weekday(): 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
WEEKLY_MARKET_SCHEDULE: Dict[int, Optional[str]] = {
    0: "EN",  # Thứ Hai (Monday)
    1: "KR",  # Thứ Ba (Tuesday)
    2: "JP",  # Thứ Tư (Wednesday)
    3: "EN",  # Thứ Năm (Thursday)
    4: "KR",  # Thứ Sáu (Friday)
    5: "JP",  # Thứ Bảy (Saturday)
    6: None,  # Chủ Nhật (Sunday) - OFF / Maintenance
}

DAY_NAMES_VI: Dict[int, str] = {
    0: "Thứ Hai",
    1: "Thứ Ba",
    2: "Thứ Tư",
    3: "Thứ Năm",
    4: "Thứ Sáu",
    5: "Thứ Bảy",
    6: "Chủ Nhật",
}

DAY_NAMES_EN: Dict[int, str] = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def get_vn_now() -> datetime:
    """Return current timestamp aware in Vietnam Timezone (UTC+7)."""
    return datetime.now(VN_TZ)


def to_vn_datetime(dt: Optional[datetime] = None) -> datetime:
    """Normalize any datetime (naive or aware) to Vietnam Timezone (UTC+7).
    If dt is None, returns get_vn_now().
    """
    if dt is None:
        return get_vn_now()
    if dt.tzinfo is None:
        # Naive datetime: treat as local VN time
        return dt.replace(tzinfo=VN_TZ)
    # Aware datetime: convert to VN timezone
    return dt.astimezone(VN_TZ)


def get_scheduled_market_for_date(dt: Optional[datetime] = None) -> Optional[str]:
    """Determine which market is scheduled for production on the given date (VN Time).
    Returns 'EN', 'KR', 'JP', or None (if Sunday / OFF day).
    """
    dt_vn = to_vn_datetime(dt)
    weekday = dt_vn.weekday()
    return WEEKLY_MARKET_SCHEDULE.get(weekday)


def is_production_day(dt: Optional[datetime] = None) -> bool:
    """Return True if the date is a designated video production day (Mon-Sat),
    False if Sunday (designated rest & maintenance day).
    """
    return get_scheduled_market_for_date(dt) is not None


def get_market_schedule_info(dt: Optional[datetime] = None) -> Dict[str, Any]:
    """Return structured operational metadata for today's market schedule."""
    dt_vn = to_vn_datetime(dt)
    weekday = dt_vn.weekday()
    scheduled_market = WEEKLY_MARKET_SCHEDULE.get(weekday)
    return {
        "timestamp_vn": dt_vn.isoformat(),
        "date_vn": dt_vn.strftime("%Y-%m-%d"),
        "time_vn": dt_vn.strftime("%H:%M:%S"),
        "weekday": weekday,
        "day_vi": DAY_NAMES_VI.get(weekday, "Không xác định"),
        "day_en": DAY_NAMES_EN.get(weekday, "Unknown"),
        "scheduled_market": scheduled_market,
        "is_production_day": scheduled_market is not None,
        "description": (
            f"{DAY_NAMES_VI.get(weekday)} ({DAY_NAMES_EN.get(weekday)}) ➔ "
            f"Kênh {scheduled_market} (1 video duy nhất)"
            if scheduled_market
            else f"{DAY_NAMES_VI.get(weekday)} ({DAY_NAMES_EN.get(weekday)}) ➔ Nghỉ sản xuất & Bảo dưỡng định kỳ"
        ),
    }


def clean_temporary_files(max_age_hours: int = 24) -> Dict[str, int]:
    """Clean obsolete scratch and temporary files from /tmp and /var/vf/locks."""
    stats = {"cleaned_tmp_files": 0, "cleaned_stale_locks": 0, "errors": 0}
    now = time.time()
    max_age_sec = max_age_hours * 3600

    # 1. Clean /tmp temporary files related to video_factory
    tmp_dir = "/tmp"
    if os.path.exists(tmp_dir):
        for fname in os.listdir(tmp_dir):
            if fname.startswith(("vf_", "tmp_vf_", "pytest-", "chrome_bits_")):
                fpath = os.path.join(tmp_dir, fname)
                try:
                    mtime = os.path.getmtime(fpath)
                    if now - mtime > max_age_sec:
                        if os.path.isdir(fpath):
                            shutil.rmtree(fpath, ignore_errors=True)
                        else:
                            os.remove(fpath)
                        stats["cleaned_tmp_files"] += 1
                except Exception as e:
                    logger.debug(f"Could not clean tmp file {fpath}: {e}")
                    stats["errors"] += 1

    # 2. Clean stale locks in /var/vf/locks
    locks_dir = "/var/vf/locks"
    if os.path.exists(locks_dir):
        for fname in os.listdir(locks_dir):
            if fname.endswith(".lock"):
                fpath = os.path.join(locks_dir, fname)
                try:
                    mtime = os.path.getmtime(fpath)
                    if now - mtime > max_age_sec:
                        os.remove(fpath)
                        stats["cleaned_stale_locks"] += 1
                except Exception as e:
                    logger.debug(f"Could not clean lock {fpath}: {e}")
                    stats["errors"] += 1

    return stats


def run_sunday_maintenance() -> Dict[str, Any]:
    """Execute maintenance cycle for Sunday:
    1. System temporary file and lock cleanup.
    2. Weekly B11 Analytics Routine Synthesis.
    3. Telegram summary report.
    """
    logger.info("Starting Sunday System Maintenance & B11 Dreaming cycle...")
    results: Dict[str, Any] = {
        "timestamp_vn": get_vn_now().isoformat(),
        "cleanup": clean_temporary_files(max_age_hours=24),
        "b11_status": "skipped",
        "b11_stdout": "",
    }

    # Run B11 Analytics Routine if engine exists
    b11_script = "/root/video_factory/scripts/b11_engine.py"
    python_bin = sys.executable or "/root/video_factory/venv/bin/python3"
    if os.path.exists(b11_script):
        try:
            cmd = [python_bin, b11_script, "--routine"]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            results["b11_status"] = "success" if proc.returncode == 0 else "failed"
            results["b11_stdout"] = proc.stdout[-500:] if proc.stdout else ""
            if proc.stderr:
                logger.warning(f"B11 routine stderr: {proc.stderr[:300]}")
        except Exception as e:
            results["b11_status"] = f"error: {e}"
            logger.error(f"Failed to execute B11 routine during Sunday maintenance: {e}")

    # Send Telegram notification
    try:
        from app.services.telegram_buttons import send_telegram_broadcast
        msg = (
            "🧹 <b>[VF SYSTEM MAINTENANCE - CHỦ NHẬT]</b>\n"
            "• <i>Trạng thái</i>: Nghỉ sản xuất video định kỳ để bảo vệ hạ tầng VPS.\n"
            f"• <i>Dọn rác /tmp & Locks</i>: {results['cleanup']['cleaned_tmp_files']} files tmp, {results['cleanup']['cleaned_stale_locks']} stale locks.\n"
            f"• <i>B11 Analytics Routine</i>: {results['b11_status'].upper()}\n"
            "• <i>Lịch tuần mới</i>: Sáng mai (Thứ Hai 06:00 VN) sẽ sản xuất kênh <b>EN</b>."
        )
        msg_id = send_telegram_broadcast(msg)
        results["telegram_sent"] = bool(msg_id)
    except Exception as te:
        logger.warning(f"Telegram notification for maintenance failed: {te}")
        results["telegram_sent"] = False

    logger.info("Sunday maintenance completed successfully.")
    return results
