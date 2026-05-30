"""Integration tests for development test-device seeding (US4, FR-014)."""
from __future__ import annotations

from pathlib import Path

from src.app import create_app
from src.config import Settings
from src.device_auth.application.seed_test_device import DEFAULT_DEVICE_ID
from src.device_auth.infrastructure.models import DeviceModel

ROUTE = "/api/v1/iot-monitoring/sensor-readings"
HEADERS = {"X-API-Key": "test-api-key-edu"}
BODY = {"device_id": DEFAULT_DEVICE_ID, "temperature": 22.0, "humidity": 45.0, "occupancy": True}


def _trigger(app) -> None:  # noqa: ANN001 - force the before_request bootstrap to run
    app.test_client().get("/api/v1/iot-monitoring/sensor-readings")


def test_fresh_dev_start_seeds_and_authenticates(client) -> None:  # noqa: ANN001
    response = client.post(ROUTE, json=BODY, headers=HEADERS)
    assert response.status_code == 201
    assert DeviceModel.select().where(DeviceModel.device_id == DEFAULT_DEVICE_ID).count() == 1


def test_restart_does_not_duplicate(settings: Settings) -> None:
    _trigger(create_app(settings))  # first start seeds
    _trigger(create_app(settings))  # "restart" against the same db file
    assert DeviceModel.select().where(DeviceModel.device_id == DEFAULT_DEVICE_ID).count() == 1


def test_production_mode_does_not_seed(tmp_path: Path) -> None:
    prod = Settings(
        db_path=str(tmp_path / "prod.db"),
        web_api_url="",
        forward_timeout=1.0,
        env="production",
        retry_interval=0.0,
    )
    _trigger(create_app(prod))
    assert DeviceModel.select().where(DeviceModel.device_id == DEFAULT_DEVICE_ID).count() == 0
