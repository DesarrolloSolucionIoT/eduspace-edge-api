"""Integration tests for validation rejection (US2, FR-004), real SQLite."""
from __future__ import annotations

from src.iot_ingestion.infrastructure.models import SensorReadingModel

ROUTE = "/api/v1/iot-monitoring/sensor-readings"
HEADERS = {"X-API-Key": "test-api-key-edu"}


def _body(**overrides: object) -> dict[str, object]:
    body = {
        "device_id": "esp32-aula-101",
        "temperature": 22.0,
        "humidity": 45.0,
        "occupancy": True,
    }
    body.update(overrides)
    return body


def test_out_of_range_humidity_returns_400(client) -> None:  # noqa: ANN001
    response = client.post(ROUTE, json=_body(humidity=150.0), headers=HEADERS)
    assert response.status_code == 400
    assert response.get_json()["code"] == "VALIDATION_ERROR"
    assert SensorReadingModel.select().count() == 0


def test_missing_field_returns_400(client) -> None:  # noqa: ANN001
    body = _body()
    del body["temperature"]
    response = client.post(ROUTE, json=body, headers=HEADERS)
    assert response.status_code == 400
    assert SensorReadingModel.select().count() == 0


def test_validation_error_has_code_and_message(client) -> None:  # noqa: ANN001
    response = client.post(ROUTE, json=_body(occupancy="yes"), headers=HEADERS)
    payload = response.get_json()
    assert payload["code"] == "VALIDATION_ERROR"
    assert isinstance(payload["message"], str) and payload["message"]
