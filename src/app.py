"""Flask application factory and bootstrap (composition root)."""
from __future__ import annotations

from flask import Flask, Response, jsonify

from src.config import Settings, load_settings
from src.db import init_db
from src.device_auth.application.authenticator import Authenticator
from src.device_auth.application.seed_test_device import seed_test_device
from src.device_auth.infrastructure.device_repository import DeviceRepository
from src.device_auth.infrastructure.password_hasher import Pbkdf2Hasher
from src.device_auth.interfaces.middleware import register_auth_middleware
from src.iot_ingestion.infrastructure.reading_repository import ReadingRepository
from src.iot_ingestion.infrastructure.retry_task import start_retry_worker
from src.iot_ingestion.infrastructure.upstream_forwarder import UpstreamForwarder
from src.iot_ingestion.interfaces.routes import build_ingestion_blueprint
from src.shared.clock import SystemClock
from src.shared.errors import AppError, error_payload
from src.device_auth.application.authenticator import ThresholdResolver


def create_app(settings: Settings | None = None) -> Flask:
    """Build and wire the Flask application."""
    settings = settings or load_settings()
    app = Flask(__name__)
    app.config["SETTINGS"] = settings

    init_db(settings.db_path)
    hasher = Pbkdf2Hasher()
    devices = DeviceRepository()
    authenticator = Authenticator(devices, hasher, _resolve_thresholds())

    _register_bootstrap(app, settings, devices, hasher)
    register_auth_middleware(app, authenticator)
    _register_error_handlers(app)
    app.register_blueprint(build_ingestion_blueprint(settings))
    _start_worker(settings)
    return app


def _resolve_thresholds() -> ThresholdResolver:
    from src.shared.threshold_config import resolve_thresholds

    return resolve_thresholds


def _register_bootstrap(
    app: Flask, settings: Settings, devices: DeviceRepository, hasher: Pbkdf2Hasher
) -> None:
    """Initialize the DB and seed the dev test device once, on the first request."""
    state = {"done": False}

    @app.before_request
    def _bootstrap() -> None:
        if state["done"]:
            return
        init_db(settings.db_path)
        if settings.is_development:
            seed_test_device(devices, hasher)
        state["done"] = True

    # Register bootstrap before the auth middleware so the seeded device exists.


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def _handle_app_error(error: AppError) -> tuple[Response, int]:
        return jsonify(error_payload(error)), error.http_status


def _start_worker(settings: Settings) -> None:
    start_retry_worker(
        make_readings=ReadingRepository,
        forwarder=UpstreamForwarder(
            settings.web_api_url, settings.forward_timeout, settings.forward_auth
        ),
        clock=SystemClock(),
        interval=settings.retry_interval,
    )
