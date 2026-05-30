"""Injectable UTC clock abstraction."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    """Source of the current time, always timezone-aware UTC."""

    def now(self) -> datetime:
        """Return the current instant as a timezone-aware UTC datetime."""
        ...


class SystemClock:
    """Default Clock backed by the system wall clock in UTC."""

    def now(self) -> datetime:
        """Return the current UTC time."""
        return datetime.now(timezone.utc)
