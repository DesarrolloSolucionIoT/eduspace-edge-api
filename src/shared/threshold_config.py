"""Configuration-sourced per-zone thresholds, keyed by zone identifier."""
from __future__ import annotations

from src.shared.zone_thresholds import ZoneThresholds

# Per-zone configuration for this iteration. In a deployment this would be loaded
# from a config file or environment; an unknown zone resolves to no bounds.
_ZONE_THRESHOLDS: dict[str, ZoneThresholds] = {
    "aula-101": ZoneThresholds(
        temp_min=18.0, temp_max=27.0, humidity_min=30.0, humidity_max=60.0
    ),
}


def resolve_thresholds(zone_id: str) -> ZoneThresholds:
    """Return the thresholds configured for a zone, or empty bounds if none."""
    return _ZONE_THRESHOLDS.get(zone_id, ZoneThresholds())
