"""Integration tests for the ingestion endpoint happy path (US1), real SQLite."""
from __future__ import annotations

from src.iot_ingestion.infrastructure.models import SensorReadingModel

ROUTE = "/api/v1/iot-monitoring/sensor-readings"
HEADERS = {"X-API-Key": "test-api-key-edu"}


def _reading(**overrides: object) -> dict[str, object]:
    body = {
        "device_id": "esp32-aula-101",
        "temperature": 22.0,
        "humidity": 45.0,
        "occupancy": True,
    }
    body.update(overrides)
    return body


def test_reading_within_bounds_returns_inactive(client) -> None:  # noqa: ANN001
    response = client.post(ROUTE, json=_reading(), headers=HEADERS)
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["alert_led_state"] == 0
    assert payload["reading_id"] >= 1
    assert payload["recorded_at"].endswith("+00:00")


def test_reading_exceeding_threshold_returns_active(client) -> None:  # noqa: ANN001
    response = client.post(ROUTE, json=_reading(temperature=31.5, humidity=70.0), headers=HEADERS)
    assert response.status_code == 201
    assert response.get_json()["alert_led_state"] == 1


def test_reading_is_persisted_with_utc(client) -> None:  # noqa: ANN001
    client.post(ROUTE, json=_reading(recorded_at="2026-05-30T14:03:22-05:00"), headers=HEADERS)
    row = SensorReadingModel.select().order_by(SensorReadingModel.id.desc()).first()
    assert row is not None
    assert row.occupancy == 1
    assert "19:03:22" in str(row.recorded_at)


def test_non_utc_timestamp_normalized_in_response(client) -> None:  # noqa: ANN001
    response = client.post(
        ROUTE, json=_reading(recorded_at="2026-05-30T14:03:22-05:00"), headers=HEADERS
    )
    assert response.get_json()["recorded_at"].startswith("2026-05-30T19:03:22")
