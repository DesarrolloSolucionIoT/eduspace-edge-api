"""Integration fixtures operating against the real (temp-file) SQLite database."""
from __future__ import annotations

import pytest

from src.config import Settings
from src.device_auth.infrastructure.device_repository import DeviceRepository
from src.iot_ingestion.infrastructure.reading_repository import ReadingRepository


@pytest.fixture
def device_repo(app) -> DeviceRepository:  # noqa: ANN001 - app fixture is a Flask app
    """Device repository bound to the test database (tables created by create_app)."""
    return DeviceRepository()


@pytest.fixture
def reading_repo(app) -> ReadingRepository:  # noqa: ANN001
    """Reading repository bound to the test database."""
    return ReadingRepository()


@pytest.fixture
def seeded_device_credentials(settings: Settings) -> tuple[str, str]:
    """The default development test-device credentials seeded on first request."""
    return ("esp32-aula-101", "test-api-key-edu")
