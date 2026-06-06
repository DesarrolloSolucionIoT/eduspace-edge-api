"""HTTP interface: POST /api/v1/iot-monitoring/sensor-readings."""
from __future__ import annotations

from flask import Blueprint, Response, g, jsonify, request

from src.config import Settings
from src.iot_ingestion.application.ingest_reading import IngestCommand, IngestReading
from src.iot_ingestion.application.validation import validate_reading_request
from src.iot_ingestion.infrastructure.reading_repository import ReadingRepository
from src.iot_ingestion.infrastructure.upstream_forwarder import UpstreamForwarder
from src.shared.clock import SystemClock

ROUTE = "/api/v1/iot-monitoring/sensor-readings"


def build_ingestion_blueprint(settings: Settings) -> Blueprint:
    """Build the ingestion blueprint wired with concrete infrastructure."""
    blueprint = Blueprint("ingestion", __name__)

    @blueprint.post(ROUTE)
    def submit_reading() -> tuple[Response, int]:
        validated = validate_reading_request(request.get_json(silent=True))
        command = IngestCommand(
            device_id=g.auth.device.device_id,
            zone_id=g.auth.device.zone_id,
            temperature=validated.temperature,
            humidity=validated.humidity,
            occupancy=validated.occupancy,
            recorded_at=validated.recorded_at,
            thresholds=g.auth.thresholds,
        )
        result = _build_use_case(settings).execute(command)
        body = {
            "reading_id": result.reading_id,
            "alert_led_state": result.alert_led_state,
            "recorded_at": result.recorded_at.isoformat(),
        }
        return jsonify(body), 201

    return blueprint


def _build_use_case(settings: Settings) -> IngestReading:
    forwarder = UpstreamForwarder(settings.web_api_url, settings.forward_timeout)
    return IngestReading(ReadingRepository(), forwarder, SystemClock())
