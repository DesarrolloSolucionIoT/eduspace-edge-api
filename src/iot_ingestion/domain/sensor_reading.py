"""Pure SensorReading domain entity."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SensorReading:
    """A single measurement event, with its timestamp normalized to UTC.

    ``reading_id`` and ``alert_led_state`` are populated as the reading moves through
    persistence and evaluation; they are None on a freshly parsed reading.
    """

    device_id: str
    temperature: float
    humidity: float
    occupancy: bool
    recorded_at: datetime
    zone_id: str = ""
    alert_led_state: int | None = None
    reading_id: int | None = None
