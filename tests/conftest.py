"""Shared pytest fixtures: temp-file SQLite settings, app, and test client."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from src.app import create_app
from src.config import Settings


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    """A development Settings instance backed by a temp SQLite file (not in-memory)."""
    monkeypatch.setenv("EDUSPACE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("EDUSPACE_ENV", "development")
    monkeypatch.setenv("EDUSPACE_WEB_API_URL", "http://upstream.test/ingest")
    monkeypatch.setenv("EDUSPACE_FORWARD_TIMEOUT", "1")
    monkeypatch.setenv("EDUSPACE_RETRY_INTERVAL", "0")  # disable background worker in tests
    from src.config import load_settings

    return load_settings()


@pytest.fixture
def app(settings: Settings) -> Iterator[Flask]:
    """A configured Flask app with a freshly initialized database."""
    application = create_app(settings)
    yield application


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """A Flask test client for the configured app."""
    return app.test_client()
