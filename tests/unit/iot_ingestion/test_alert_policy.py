"""Unit tests for the local alert evaluation policy (US1)."""
from __future__ import annotations

from src.iot_ingestion.domain.alert_policy import evaluate
from src.shared.zone_thresholds import ZoneThresholds

BOUNDS = ZoneThresholds(temp_min=18.0, temp_max=27.0, humidity_min=30.0, humidity_max=60.0)


def test_within_bounds_is_inactive() -> None:
    assert evaluate(22.0, 45.0, BOUNDS) == 0


def test_temperature_above_max_is_active() -> None:
    assert evaluate(30.0, 45.0, BOUNDS) == 1


def test_temperature_below_min_is_active() -> None:
    assert evaluate(10.0, 45.0, BOUNDS) == 1


def test_humidity_above_max_is_active() -> None:
    assert evaluate(22.0, 80.0, BOUNDS) == 1


def test_humidity_below_min_is_active() -> None:
    assert evaluate(22.0, 10.0, BOUNDS) == 1


def test_no_thresholds_is_inactive() -> None:
    assert evaluate(999.0, 999.0, ZoneThresholds()) == 0


def test_occupancy_is_not_a_parameter() -> None:
    # evaluate takes only temperature, humidity, thresholds — occupancy cannot influence it.
    import inspect

    params = list(inspect.signature(evaluate).parameters)
    assert params == ["temperature", "humidity", "thresholds"]
