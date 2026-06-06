"""Use case: persist a reading, evaluate the alert locally, forward best-effort."""
from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import datetime

from src.iot_ingestion.application.normalize import to_utc
from src.iot_ingestion.application.ports import ReadingStore, UpstreamForwarder
from src.iot_ingestion.domain.alert_policy import evaluate
from src.iot_ingestion.domain.sensor_reading import SensorReading
from src.shared.clock import Clock
from src.shared.zone_thresholds import ZoneThresholds

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestCommand:
    """Validated inputs for ingesting one reading."""

    device_id: str
    zone_id: str
    temperature: float
    humidity: float
    occupancy: bool
    recorded_at: str | None
    thresholds: ZoneThresholds


@dataclass(frozen=True)
class IngestResult:
    """Outcome returned to the device."""

    reading_id: int
    alert_led_state: int
    recorded_at: datetime


class IngestReading:
    """Orchestrates normalize -> evaluate -> persist -> best-effort forward."""

    def __init__(
        self, readings: ReadingStore, forwarder: UpstreamForwarder, clock: Clock
    ) -> None:
        self._readings = readings
        self._forwarder = forwarder
        self._clock = clock

    def execute(self, command: IngestCommand) -> IngestResult:
        """Process one reading and return the local alert decision."""
        recorded_at = to_utc(command.recorded_at, self._clock)
        alert = evaluate(command.temperature, command.humidity, command.thresholds)
        reading = SensorReading(
            device_id=command.device_id,
            zone_id=command.zone_id,
            temperature=command.temperature,
            humidity=command.humidity,
            occupancy=command.occupancy,
            recorded_at=recorded_at,
            alert_led_state=alert,
        )
        reading_id = self._readings.add(reading)
        self._try_forward(replace(reading, reading_id=reading_id))
        return IngestResult(reading_id=reading_id, alert_led_state=alert, recorded_at=recorded_at)

    def _try_forward(self, reading: SensorReading) -> None:
        """Forward best-effort; failures are logged and left for background retry."""
        assert reading.reading_id is not None
        try:
            if self._forwarder.forward(reading):
                self._readings.mark_forwarded(reading.reading_id, self._clock.now())
        except Exception:  # noqa: BLE001 - forwarding must never break the response
            logger.exception("forwarding raised for reading %s", reading.reading_id)
