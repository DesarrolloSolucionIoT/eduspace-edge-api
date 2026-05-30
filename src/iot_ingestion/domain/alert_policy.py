"""Pure local alert evaluation. Occupancy is deliberately not a parameter."""
from __future__ import annotations

from src.shared.zone_thresholds import ZoneThresholds


def evaluate(temperature: float, humidity: float, thresholds: ZoneThresholds) -> int:
    """Return 1 if temperature or humidity breaches a configured bound, else 0."""
    if _breaches(temperature, thresholds.temp_min, thresholds.temp_max):
        return 1
    if _breaches(humidity, thresholds.humidity_min, thresholds.humidity_max):
        return 1
    return 0


def _breaches(value: float, low: float | None, high: float | None) -> bool:
    if low is not None and value < low:
        return True
    if high is not None and value > high:
        return True
    return False
