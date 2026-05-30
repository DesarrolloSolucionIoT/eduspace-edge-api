"""Unit tests for UTC timestamp normalization (US1, FR-012)."""
from __future__ import annotations

from datetime import datetime, timezone

from src.iot_ingestion.application.normalize import to_utc


class _FixedClock:
    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant


def test_offset_timestamp_converted_to_utc() -> None:
    result = to_utc("2026-05-30T14:03:22-05:00", _FixedClock(datetime.now(timezone.utc)))
    assert result == datetime(2026, 5, 30, 19, 3, 22, tzinfo=timezone.utc)
    assert result.tzinfo == timezone.utc


def test_naive_timestamp_treated_as_utc() -> None:
    result = to_utc("2026-05-30T19:03:22", _FixedClock(datetime.now(timezone.utc)))
    assert result == datetime(2026, 5, 30, 19, 3, 22, tzinfo=timezone.utc)


def test_missing_timestamp_uses_clock() -> None:
    fixed = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert to_utc(None, _FixedClock(fixed)) == fixed


def test_zulu_timestamp_is_utc() -> None:
    result = to_utc("2026-05-30T19:03:22Z", _FixedClock(datetime.now(timezone.utc)))
    assert result == datetime(2026, 5, 30, 19, 3, 22, tzinfo=timezone.utc)
