"""Step bindings for offline_buffering_and_forwarding.feature (US3)."""
from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import parsers, scenarios, then, when

from src.config import Settings
from src.iot_ingestion.infrastructure import upstream_forwarder as fwd_mod
from src.iot_ingestion.infrastructure.models import SensorReadingModel
from src.iot_ingestion.infrastructure.reading_repository import ReadingRepository
from src.iot_ingestion.infrastructure.retry_task import run_retry_once
from src.iot_ingestion.infrastructure.upstream_forwarder import UpstreamForwarder
from src.shared.clock import SystemClock

from tests.acceptance.conftest import ScenarioContext

scenarios("features/offline_buffering_and_forwarding.feature")


class _AcceptedResponse:
    status_code = 202


@when("the cloud backend becomes reachable again and the retry cycle runs")
def backend_restored_and_retry(
    context: ScenarioContext, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _ok(url: str, json: dict[str, Any], timeout: float, headers: dict[str, str]) -> _AcceptedResponse:  # noqa: A002
        context.forwarded_payloads.append(json)
        return _AcceptedResponse()

    monkeypatch.setattr(fwd_mod.requests, "post", _ok)
    forwarder = UpstreamForwarder(
        settings.web_api_url, settings.forward_timeout, settings.forward_auth
    )
    context.delivered_count = run_retry_once(ReadingRepository(), forwarder, SystemClock())


@then("the reading is stored locally with no forwarded timestamp")
def assert_buffered(context: ScenarioContext) -> None:
    reading_id = context.response.get_json()["reading_id"]
    row = SensorReadingModel.get_by_id(reading_id)
    assert row.forwarded_at is None


@then(parsers.parse("exactly {count:d} buffered reading is delivered to the backend"))
def assert_delivered_count(context: ScenarioContext, count: int) -> None:
    assert context.delivered_count == count
    assert len(context.forwarded_payloads) == count


@then("the delivered payload carries the original reading_id for idempotent deduplication")
def assert_idempotent_payload(context: ScenarioContext) -> None:
    original_id = context.response.get_json()["reading_id"]
    assert context.forwarded_payloads[0]["reading_id"] == original_id


@then("the reading is marked as forwarded locally")
def assert_marked_forwarded(context: ScenarioContext) -> None:
    reading_id = context.response.get_json()["reading_id"]
    assert SensorReadingModel.get_by_id(reading_id).forwarded_at is not None
