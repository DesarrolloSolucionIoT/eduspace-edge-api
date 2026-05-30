"""Integration tests for offline buffering (US3, FR-010), real SQLite."""
from __future__ import annotations

from typing import Any

import pytest
import requests

from src.iot_ingestion.infrastructure import upstream_forwarder as fwd_mod
from src.iot_ingestion.infrastructure.models import SensorReadingModel

ROUTE = "/api/v1/iot-monitoring/sensor-readings"
HEADERS = {"X-API-Key": "test-api-key-edu"}
BODY = {"device_id": "esp32-aula-101", "temperature": 22.0, "humidity": 45.0, "occupancy": True}


@pytest.fixture
def upstream_down(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise requests.ConnectionError("upstream unreachable")

    monkeypatch.setattr(fwd_mod.requests, "post", _boom)


def test_reading_accepted_when_upstream_down(client, upstream_down) -> None:  # noqa: ANN001
    response = client.post(ROUTE, json=BODY, headers=HEADERS)
    assert response.status_code == 201
    assert response.get_json()["alert_led_state"] == 0


def test_reading_buffered_with_null_forwarded_at(client, upstream_down) -> None:  # noqa: ANN001
    client.post(ROUTE, json=BODY, headers=HEADERS)
    row = SensorReadingModel.select().order_by(SensorReadingModel.id.desc()).first()
    assert row is not None
    assert row.forwarded_at is None
