"""Dependency-injection seams (Protocols) for the iot_ingestion application layer."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, Protocol

from src.iot_ingestion.domain.sensor_reading import SensorReading


class ReadingStore(Protocol):
    """Persistence operations the use cases depend on."""

    def add(self, reading: SensorReading) -> int:
        """Persist a reading and return its assigned id."""
        ...

    def mark_forwarded(self, reading_id: int, forwarded_at: datetime) -> None:
        """Record that a reading was successfully delivered upstream."""
        ...

    def iter_unforwarded(self) -> Iterable[SensorReading]:
        """Yield readings still awaiting upstream delivery (forwarded_at IS NULL)."""
        ...


class UpstreamForwarder(Protocol):
    """Best-effort upstream delivery; never raises to the caller."""

    def forward(self, reading: SensorReading) -> bool:
        """Attempt delivery; return True on success, False on any failure."""
        ...
