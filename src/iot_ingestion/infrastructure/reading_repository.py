"""Peewee-backed repository for sensor readings."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from dateutil import parser as date_parser

from src.iot_ingestion.domain.sensor_reading import SensorReading
from src.iot_ingestion.infrastructure.models import SensorReadingModel


class ReadingRepository:
    """Persistence adapter for sensor readings."""

    def add(self, reading: SensorReading) -> int:
        """Insert a reading and return its assigned id."""
        row = SensorReadingModel.create(
            device_id=reading.device_id,
            temperature=reading.temperature,
            humidity=reading.humidity,
            occupancy=int(reading.occupancy),
            alert_led_state=reading.alert_led_state,
            recorded_at=_to_naive_utc(reading.recorded_at),
            forwarded_at=None,
        )
        return int(row.id)

    def mark_forwarded(self, reading_id: int, forwarded_at: datetime) -> None:
        """Stamp a reading as delivered upstream."""
        SensorReadingModel.update(forwarded_at=forwarded_at).where(
            SensorReadingModel.id == reading_id
        ).execute()

    def iter_unforwarded(self) -> Iterable[SensorReading]:
        """Return readings whose forwarded_at is NULL, oldest first."""
        rows = (
            SensorReadingModel.select()
            .where(SensorReadingModel.forwarded_at.is_null())
            .order_by(SensorReadingModel.id)
        )
        return [self._to_entity(row) for row in rows]

    @staticmethod
    def _to_entity(row: SensorReadingModel) -> SensorReading:
        return SensorReading(
            device_id=row.device_id,
            temperature=row.temperature,
            humidity=row.humidity,
            occupancy=bool(row.occupancy),
            recorded_at=_to_aware_utc(row.recorded_at),
            alert_led_state=row.alert_led_state,
            reading_id=int(row.id),
        )


def _to_naive_utc(value: datetime) -> datetime:
    """Drop tz info for storage; the column is always understood as UTC."""
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


def _to_aware_utc(value: datetime | str) -> datetime:
    """Re-attach UTC when reading back (Peewee may yield a naive datetime or string)."""
    parsed = date_parser.isoparse(value) if isinstance(value, str) else value
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
