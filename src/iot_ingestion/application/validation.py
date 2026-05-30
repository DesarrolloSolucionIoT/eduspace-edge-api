"""Request-body validation for sensor readings (raises ValidationError)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dateutil import parser as date_parser

from src.shared.errors import ValidationError

TEMP_MIN, TEMP_MAX = -40.0, 85.0
HUMIDITY_MIN, HUMIDITY_MAX = 0.0, 100.0


@dataclass(frozen=True)
class ValidatedReading:
    """A validated reading body."""

    temperature: float
    humidity: float
    occupancy: bool
    recorded_at: str | None


def validate_reading_request(body: Any) -> ValidatedReading:
    """Validate a parsed JSON body, raising ValidationError on any problem."""
    if not isinstance(body, dict):
        raise ValidationError("Request body must be a JSON object")
    return ValidatedReading(
        temperature=_require_number(body, "temperature", TEMP_MIN, TEMP_MAX),
        humidity=_require_number(body, "humidity", HUMIDITY_MIN, HUMIDITY_MAX),
        occupancy=_require_bool(body, "occupancy"),
        recorded_at=_optional_timestamp(body, "recorded_at"),
    )


def _require_number(body: dict[str, Any], field: str, low: float, high: float) -> float:
    value = body.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{field} is required and must be a number")
    if not low <= float(value) <= high:
        raise ValidationError(f"{field} must be between {low} and {high}")
    return float(value)


def _require_bool(body: dict[str, Any], field: str) -> bool:
    value = body.get(field)
    if not isinstance(value, bool):
        raise ValidationError(f"{field} is required and must be a boolean")
    return value


def _optional_timestamp(body: dict[str, Any], field: str) -> str | None:
    value = body.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be an ISO 8601 string")
    try:
        date_parser.isoparse(value)
    except (ValueError, OverflowError) as exc:
        raise ValidationError(f"{field} must be a valid ISO 8601 timestamp") from exc
    return value
