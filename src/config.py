"""Typed application settings sourced from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings for the edge service."""

    db_path: str
    web_api_url: str
    forward_timeout: float
    env: str
    retry_interval: float

    @property
    def is_development(self) -> bool:
        """True when running in a local development/testing context."""
        return self.env.lower() == "development"


def load_settings() -> Settings:
    """Build Settings from the process environment, applying sensible defaults."""
    return Settings(
        db_path=os.environ.get("EDUSPACE_DB_PATH", "eduspace-edge.db"),
        web_api_url=os.environ.get("EDUSPACE_WEB_API_URL", ""),
        forward_timeout=float(os.environ.get("EDUSPACE_FORWARD_TIMEOUT", "5")),
        env=os.environ.get("EDUSPACE_ENV", "production"),
        retry_interval=float(os.environ.get("EDUSPACE_RETRY_INTERVAL", "30")),
    )
