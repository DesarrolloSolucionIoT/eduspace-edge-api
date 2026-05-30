"""Contract tests: responses conform to contracts/sensor-readings.openapi.yaml."""
from __future__ import annotations

from pathlib import Path

CONTRACT = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "001-classroom-sensor-ingestion"
    / "contracts"
    / "sensor-readings.openapi.yaml"
)
ROUTE = "/api/v1/iot-monitoring/sensor-readings"
HEADERS = {"X-API-Key": "test-api-key-edu"}
BODY = {"device_id": "esp32-aula-101", "temperature": 31.5, "humidity": 70.0, "occupancy": True}


def test_contract_file_pins_route_and_fields() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "/sensor-readings" in text
    for field in ("reading_id", "alert_led_state", "recorded_at", "X-API-Key"):
        assert field in text


def test_success_response_matches_schema(client) -> None:  # noqa: ANN001
    response = client.post(ROUTE, json=BODY, headers=HEADERS)
    assert response.status_code == 201
    payload = response.get_json()
    assert set(payload) == {"reading_id", "alert_led_state", "recorded_at"}
    assert isinstance(payload["reading_id"], int)
    assert payload["alert_led_state"] in (0, 1)
    assert payload["recorded_at"].endswith("+00:00")


def test_auth_error_matches_schema(client) -> None:  # noqa: ANN001
    payload = client.post(ROUTE, json=BODY).get_json()
    assert set(payload) == {"code", "message"}
    assert payload["code"] == "AUTH_FAILED"


def test_validation_error_matches_schema(client) -> None:  # noqa: ANN001
    payload = client.post(ROUTE, json={**BODY, "humidity": 999}, headers=HEADERS).get_json()
    assert set(payload) == {"code", "message"}
    assert payload["code"] == "VALIDATION_ERROR"
