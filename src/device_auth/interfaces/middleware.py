"""Flask middleware enforcing device authentication on every inbound request."""
from __future__ import annotations

from flask import Flask, g, request

from src.device_auth.application.authenticator import Authenticator


def register_auth_middleware(app: Flask, authenticator: Authenticator) -> None:
    """Attach a before_request hook that authenticates and exposes the context."""

    @app.before_request
    def _authenticate() -> None:
        if request.method == "OPTIONS":
            return
        device_id = _device_id_from_request()
        api_key = request.headers.get("X-API-Key")
        g.auth = authenticator.authenticate(device_id, api_key)


def _device_id_from_request() -> str | None:
    """Extract device_id from the JSON body, tolerating malformed/absent bodies."""
    body = request.get_json(silent=True)
    if isinstance(body, dict) and isinstance(body.get("device_id"), str):
        return body["device_id"]
    return None
