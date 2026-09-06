"""tests/test_market_scheduler.py — UNIT TESTS FOR WEEKLY MARKET STAGGER SCHEDULER
Verifies:
  1. Strict Vietnam Timezone (UTC+7) normalization.
  2. 7-day schedule mapping:
     - Mon & Thu -> EN
     - Tue & Fri -> KR
     - Wed & Sat -> JP
     - Sun -> None (Rest & Maintenance)
  3. Boundary conditions across UTC midnight and VPS 23:00 UTC cron trigger.
  4. System maintenance helper functions.
"""

import pytest
from datetime import datetime, timezone, timedelta

from app.services.market_scheduler import (
    get_vn_now,
    to_vn_datetime,
    get_scheduled_market_for_date,
    is_production_day,
    get_market_schedule_info,
    clean_temporary_files,
    WEEKLY_MARKET_SCHEDULE,
    DAY_NAMES_VI,
)


def test_vietnam_timezone_offset():
    """Verify get_vn_now() produces aware datetime with +07:00 offset."""
    now_vn = get_vn_now()
    assert now_vn.tzinfo is not None, "Timestamp must be timezone-aware"
    offset = now_vn.utcoffset()
    assert offset == timedelta(hours=7), f"Expected UTC+7, got {offset}"


def test_full_week_schedule_mapping():
    """Verify all 7 days match the user's required schedule exactly:
    EN: 2, 5 | KR: 3, 6 | JP: 4, 7 | CN: Nghỉ.
    """
    # 2026-09-07 is Monday (Thứ Hai)
    mon = datetime(2026, 9, 7, 6, 0, 0)
    expected_markets = {
        0: "EN",  # Thứ 2
        1: "KR",  # Thứ 3
        2: "JP",  # Thứ 4
        3: "EN",  # Thứ 5
        4: "KR",  # Thứ 6
        5: "JP",  # Thứ 7
        6: None,  # Chủ Nhật
    }

    for day_offset, expected_mkt in expected_markets.items():
        dt = mon + timedelta(days=day_offset)
        mkt = get_scheduled_market_for_date(dt)
        assert mkt == expected_mkt, (
            f"Failed on day {dt.strftime('%A')} ({DAY_NAMES_VI[dt.weekday()]}): "
            f"expected {expected_mkt}, got {mkt}"
        )
        prod = is_production_day(dt)
        assert prod == (expected_mkt is not None), f"is_production_day incorrect for {dt}"


def test_utc_boundary_cron_trigger():
    """Critical VPS Cron boundary test:
    Crontab fires at 23:00 UTC.
    Sunday 23:00 UTC MUST resolve to Monday 06:00 VN -> EN (NOT Sunday OFF!).
    Saturday 23:00 UTC MUST resolve to Sunday 06:00 VN -> None / OFF.
    """
    # Sunday 2026-09-06 at 23:00:00 UTC
    sun_night_utc = datetime(2026, 9, 6, 23, 0, 0, tzinfo=timezone.utc)
    mkt = get_scheduled_market_for_date(sun_night_utc)
    assert mkt == "EN", f"Cron boundary 23:00 UTC Sunday failed: expected EN, got {mkt}"

    # Saturday 2026-09-12 at 23:00:00 UTC -> Sunday 06:00 VN -> OFF
    sat_night_utc = datetime(2026, 9, 12, 23, 0, 0, tzinfo=timezone.utc)
    mkt_sun = get_scheduled_market_for_date(sat_night_utc)
    assert mkt_sun is None, f"Cron boundary 23:00 UTC Saturday failed: expected None, got {mkt_sun}"
    assert is_production_day(sat_night_utc) is False


def test_market_schedule_info_metadata():
    """Verify info dictionary contains required audit fields."""
    thu_dt = datetime(2026, 9, 10, 10, 30, 0)  # Thursday
    info = get_market_schedule_info(thu_dt)
    assert info["weekday"] == 3
    assert info["day_vi"] == "Thứ Năm"
    assert info["scheduled_market"] == "EN"
    assert info["is_production_day"] is True
    assert "EN" in info["description"]


def test_clean_temporary_files_safe():
    """Verify clean_temporary_files runs without exception."""
    res = clean_temporary_files(max_age_hours=24)
    assert isinstance(res, dict)
    assert "cleaned_tmp_files" in res
    assert "cleaned_stale_locks" in res
    assert "errors" in res
