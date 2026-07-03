"""Shared step definitions for the BDD acceptance suite (pytest-bdd).

The Gherkin sources live in ``tests/acceptance/features``; each ``test_*_steps.py``
module binds one .feature file. Steps common to every feature are defined here.
"""
from __future__ import annotations

from typing import Any

import pytest
import requests
from pytest_bdd import given, parsers, then, when

from src.iot_ingestion.infrastructure import upstream_forwarder as fwd_mod

ROUTE = "/api/v1/iot-monitoring/sensor-readings"
VALID_KEY = "test-api-key-edu"
DEVICE_ID = "esp32-aula-101"


class ScenarioContext:
    """Mutable bag carrying the HTTP response and forwarded payloads across steps."""

    def __init__(self) -> None:
        self.response: Any = None
        self.forwarded_payloads: list[dict[str, Any]] = []
        self.delivered_count: int = 0


@pytest.fixture
def context() -> ScenarioContext:
    return ScenarioContext()


def _body(temperature: float, humidity: float, occupancy: bool) -> dict[str, Any]:
    return {
        "device_id": DEVICE_ID,
        "temperature": temperature,
        "humidity": humidity,
        "occupancy": occupancy,
    }


@given("the Edge API is running with the development test device provisioned")
def edge_api_running(client) -> None:  # noqa: ANN001 - Flask test client fixture
    """The app fixture boots in development mode, which seeds the test device."""


@given("the cloud backend is unreachable")
def backend_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    def _down(*_args: Any, **_kwargs: Any) -> None:
        raise requests.ConnectionError("upstream unreachable")

    monkeypatch.setattr(fwd_mod.requests, "post", _down)


@given(
    parsers.parse(
        "the device submits a reading with temperature {temperature:g}, "
        "humidity {humidity:g} and occupancy {occupancy:w}"
    )
)
@when(
    parsers.parse(
        "the device submits a reading with temperature {temperature:g}, "
        "humidity {humidity:g} and occupancy {occupancy:w}"
    )
)
def submit_reading(
    client, context: ScenarioContext, temperature: float, humidity: float, occupancy: str  # noqa: ANN001
) -> None:
    body = _body(temperature, humidity, occupancy == "true")
    context.response = client.post(ROUTE, json=body, headers={"X-API-Key": VALID_KEY})


@then(parsers.parse("the response status is {status:d}"))
def assert_status(context: ScenarioContext, status: int) -> None:
    assert context.response.status_code == status
