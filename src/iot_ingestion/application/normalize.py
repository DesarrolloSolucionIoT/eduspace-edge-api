"""UTC normalization of device-supplied timestamps."""
from __future__ import annotations

from datetime import datetime, timezone

from dateutil import parser as date_parser

from src.shared.clock import Clock


def to_utc(value: str | None, clock: Clock) -> datetime:
    """Normalize an ISO 8601 string to UTC; default to clock.now() when absent.

    Naive timestamps are treated as UTC; offset/zoned timestamps are converted.
    Assumes ``value`` is already validated as parseable when present.
    """
    if not value:
        return clock.now()
    parsed = date_parser.isoparse(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
