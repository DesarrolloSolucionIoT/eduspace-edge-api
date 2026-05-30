"""Unit tests for request validation (US2, FR-004)."""
from __future__ import annotations

import pytest

from src.iot_ingestion.application.validation import validate_reading_request
from src.shared.errors import ValidationError


def _valid() -> dict[str, object]:
    return {"device_id": "d1", "temperature": 22.0, "humidity": 45.0, "occupancy": True}


def test_valid_body_passes() -> None:
    result = validate_reading_request(_valid())
    assert result.temperature == 22.0
    assert result.humidity == 45.0
    assert result.occupancy is True
    assert result.recorded_at is None


def test_optional_timestamp_preserved() -> None:
    result = validate_reading_request({**_valid(), "recorded_at": "2026-05-30T19:03:22Z"})
    assert result.recorded_at == "2026-05-30T19:03:22Z"


@pytest.mark.parametrize("field", ["temperature", "humidity", "occupancy"])
def test_missing_required_field_rejected(field: str) -> None:
    body = _valid()
    del body[field]
    with pytest.raises(ValidationError):
        validate_reading_request(body)


def test_non_dict_body_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_reading_request("not-a-dict")


def test_temperature_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_reading_request({**_valid(), "temperature": 200.0})


def test_humidity_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_reading_request({**_valid(), "humidity": 150.0})


def test_boolean_is_not_a_number() -> None:
    with pytest.raises(ValidationError):
        validate_reading_request({**_valid(), "temperature": True})


def test_occupancy_must_be_boolean() -> None:
    with pytest.raises(ValidationError):
        validate_reading_request({**_valid(), "occupancy": "yes"})


def test_malformed_timestamp_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_reading_request({**_valid(), "recorded_at": "not-a-date"})
