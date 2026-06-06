"""requests-based upstream forwarder; best-effort, never raises."""
from __future__ import annotations

import logging

import requests

from src.iot_ingestion.domain.sensor_reading import SensorReading

logger = logging.getLogger(__name__)


class UpstreamForwarder:
    """Posts readings to the EduSpace cloud Web API with a configurable timeout."""

    def __init__(self, base_url: str, timeout: float) -> None:
        self._base_url = base_url
        self._timeout = timeout

    def forward(self, reading: SensorReading) -> bool:
        """Attempt delivery; return True on 2xx, False on any failure."""
        if not self._base_url:
            return False
        try:
            response = requests.post(
                self._base_url, json=self._payload(reading), timeout=self._timeout
            )
            return 200 <= response.status_code < 300
        except requests.RequestException as exc:
            logger.warning("upstream forward failed for reading %s: %s", reading.reading_id, exc)
            return False

    @staticmethod
    def _payload(reading: SensorReading) -> dict[str, object]:
        return {
            "reading_id": reading.reading_id,
            "device_id": reading.device_id,
            "zone_id": reading.zone_id,
            "temperature": reading.temperature,
            "humidity": reading.humidity,
            "occupancy": reading.occupancy,
            "alert_led_state": reading.alert_led_state,
            "recorded_at": reading.recorded_at.isoformat(),
        }
