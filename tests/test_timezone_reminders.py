from datetime import datetime

from app.tools.task_tool import _format_utc_naive_for_user, _has_explicit_date, _normalize_to_utc_naive


def test_normalize_local_india_time_to_utc_storage():
    # 11:00 AM Asia/Kolkata should be stored as 05:30 UTC (naive)
    stored = _normalize_to_utc_naive("2026-04-20 11:00", "Asia/Kolkata")
    assert stored == datetime(2026, 4, 20, 5, 30)


def test_format_utc_storage_back_to_user_local_time():
    display = _format_utc_naive_for_user(datetime(2026, 4, 20, 5, 30), "Asia/Kolkata")
    assert "11:00 AM" in display


def test_has_explicit_date_detection():
    assert _has_explicit_date("2026-04-20 11:00 AM")
    assert _has_explicit_date("tomorrow 11 AM")
    assert not _has_explicit_date("11 AM")
