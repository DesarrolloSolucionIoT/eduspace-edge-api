"""requests-based upstream forwarder; best-effort, never raises."""
from __future__ import annotations

import logging

import requests

from src.iot_ingestion.domain.sensor_reading import SensorReading

logger = logging.getLogger(__name__)

# Header carrying the shared secret that lets the cloud Web API authenticate this edge node.
EDGE_AUTH_HEADER = "X-Edge-Key"


class UpstreamForwarder:
    """Posts readings to the EduSpace cloud Web API with a configurable timeout.

    When ``auth_token`` is non-empty it is sent as the ``X-Edge-Key`` header so the
    upstream can authenticate the edge; an empty token sends no auth header.
    """

    def __init__(self, base_url: str, timeout: float, auth_token: str = "") -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._auth_token = auth_token

    def forward(self, reading: SensorReading) -> bool:
        """Attempt delivery; return True on 2xx, False on any failure."""
        if not self._base_url:
            return False
        try:
            response = requests.post(
                self._base_url,
                json=self._payload(reading),
                timeout=self._timeout,
                headers=self._headers(),
            )
            return 200 <= response.status_code < 300
        except requests.RequestException as exc:
            logger.warning("upstream forward failed for reading %s: %s", reading.reading_id, exc)
            return False

    def _headers(self) -> dict[str, str]:
        """Auth headers for the upstream request (empty when no token is configured)."""
        if not self._auth_token:
            return {}
        return {EDGE_AUTH_HEADER: self._auth_token}

    @staticmethod
    def _payload(reading: SensorReading) -> dict[str, object]:
        return {
            "reading_id": reading.reading_id,
            "device_id": reading.device_id,
            "temperature": reading.temperature,
            "humidity": reading.humidity,
            "occupancy": reading.occupancy,
            "alert_led_state": reading.alert_led_state,
            "recorded_at": reading.recorded_at.isoformat(),
        }
