"""Unit tests for the requests-based upstream forwarder (US3)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
import requests

from src.iot_ingestion.domain.sensor_reading import SensorReading
from src.iot_ingestion.infrastructure import upstream_forwarder as fwd_mod
from src.iot_ingestion.infrastructure.upstream_forwarder import UpstreamForwarder


def _reading() -> SensorReading:
    return SensorReading(
        device_id="d1",
        temperature=22.0,
        humidity=45.0,
        occupancy=True,
        recorded_at=datetime(2026, 5, 30, 19, 0, tzinfo=timezone.utc),
        alert_led_state=1,
        reading_id=7,
    )


class _Resp:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_timeout_is_caught_and_reported_as_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise requests.Timeout("slow upstream")

    monkeypatch.setattr(fwd_mod.requests, "post", _boom)
    assert UpstreamForwarder("http://up/ingest", 1.0).forward(_reading()) is False


def test_connection_error_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise requests.ConnectionError("down")

    monkeypatch.setattr(fwd_mod.requests, "post", _boom)
    assert UpstreamForwarder("http://up/ingest", 1.0).forward(_reading()) is False


def test_success_returns_true_and_sends_reading_id(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def _ok(url: str, json: dict[str, Any], timeout: float) -> _Resp:  # noqa: A002
        captured["json"] = json
        return _Resp(202)

    monkeypatch.setattr(fwd_mod.requests, "post", _ok)
    assert UpstreamForwarder("http://up/ingest", 1.0).forward(_reading()) is True
    assert captured["json"]["reading_id"] == 7


def test_empty_base_url_is_noop_failure() -> None:
    assert UpstreamForwarder("", 1.0).forward(_reading()) is False
