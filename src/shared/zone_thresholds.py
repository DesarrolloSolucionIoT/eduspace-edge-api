"""Shared-kernel value object: per-zone environmental thresholds."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ZoneThresholds:
    """Optional upper/lower bounds for temperature and humidity in a classroom zone.

    A ``None`` bound means that direction is not constrained. A zone with no bounds
    configured never reports a breach.
    """

    temp_min: float | None = None
    temp_max: float | None = None
    humidity_min: float | None = None
    humidity_max: float | None = None
