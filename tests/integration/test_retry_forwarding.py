"""Integration tests for background retry forwarding (US3, FR-011/011a)."""
from __future__ import annotations

from typing import Any

import pytest
import requests

from src.config import Settings
from src.iot_ingestion.infrastructure import upstream_forwarder as fwd_mod
from src.iot_ingestion.infrastructure.models import SensorReadingModel
from src.iot_ingestion.infrastructure.reading_repository import ReadingRepository
from src.iot_ingestion.infrastructure.retry_task import run_retry_once
from src.iot_ingestion.infrastructure.upstream_forwarder import UpstreamForwarder
from src.shared.clock import SystemClock

ROUTE = "/api/v1/iot-monitoring/sensor-readings"
HEADERS = {"X-API-Key": "test-api-key-edu"}
BODY = {"device_id": "esp32-aula-101", "temperature": 31.5, "humidity": 70.0, "occupancy": True}


class _Resp:
    status_code = 202


def _forwarder(settings: Settings) -> UpstreamForwarder:
    return UpstreamForwarder(settings.web_api_url, settings.forward_timeout, settings.forward_auth)


def test_buffered_reading_forwarded_on_retry(
    client, settings: Settings, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    # Upstream down during ingestion -> reading buffered.
    monkeypatch.setattr(
        fwd_mod.requests, "post", lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError())
    )
    client.post(ROUTE, json=BODY, headers=HEADERS)
    assert SensorReadingModel.get().forwarded_at is None

    # Upstream restored -> retry forwards and stamps forwarded_at.
    sent: list[dict[str, Any]] = []

    def _ok(url: str, json: dict[str, Any], timeout: float, headers: dict[str, str]) -> _Resp:  # noqa: A002
        sent.append(json)
        return _Resp()

    monkeypatch.setattr(fwd_mod.requests, "post", _ok)
    delivered = run_retry_once(ReadingRepository(), _forwarder(settings), SystemClock())

    assert delivered == 1
    assert SensorReadingModel.get().forwarded_at is not None
    assert len(sent) == 1 and "reading_id" in sent[0]


def test_retry_is_idempotent_no_duplicate_delivery(
    client, settings: Settings, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    sent: list[dict[str, Any]] = []

    def _ok(url: str, json: dict[str, Any], timeout: float, headers: dict[str, str]) -> _Resp:  # noqa: A002
        sent.append(json)
        return _Resp()

    monkeypatch.setattr(fwd_mod.requests, "post", _ok)
    client.post(ROUTE, json=BODY, headers=HEADERS)  # forwarded immediately (1 send)

    # No unforwarded rows remain, so a retry sends nothing more.
    delivered = run_retry_once(ReadingRepository(), _forwarder(settings), SystemClock())
    assert delivered == 0
    assert len(sent) == 1
