"""Integration tests for authentication rejection (US2, FR-003/003b)."""
from __future__ import annotations

from src.iot_ingestion.infrastructure.models import SensorReadingModel

ROUTE = "/api/v1/iot-monitoring/sensor-readings"


def _body(device_id: str = "esp32-aula-101") -> dict[str, object]:
    return {"device_id": device_id, "temperature": 22.0, "humidity": 45.0, "occupancy": True}


def _assert_generic_401(response) -> None:  # noqa: ANN001
    assert response.status_code == 401
    payload = response.get_json()
    assert payload == {"code": "AUTH_FAILED", "message": "Authentication failed"}


def test_missing_api_key_rejected(client) -> None:  # noqa: ANN001
    _assert_generic_401(client.post(ROUTE, json=_body()))
    assert SensorReadingModel.select().count() == 0


def test_unknown_device_rejected(client) -> None:  # noqa: ANN001
    response = client.post(ROUTE, json=_body("ghost-device"), headers={"X-API-Key": "whatever"})
    _assert_generic_401(response)
    assert SensorReadingModel.select().count() == 0


def test_wrong_key_rejected(client) -> None:  # noqa: ANN001
    response = client.post(ROUTE, json=_body(), headers={"X-API-Key": "wrong-key"})
    _assert_generic_401(response)
    assert SensorReadingModel.select().count() == 0


def test_all_failures_are_indistinguishable(client) -> None:  # noqa: ANN001
    missing = client.post(ROUTE, json=_body())
    unknown = client.post(ROUTE, json=_body("ghost"), headers={"X-API-Key": "x"})
    wrong = client.post(ROUTE, json=_body(), headers={"X-API-Key": "wrong"})
    assert missing.get_json() == unknown.get_json() == wrong.get_json()
