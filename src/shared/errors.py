"""Structured application errors with machine-readable codes and HTTP mapping."""
from __future__ import annotations


class AppError(Exception):
    """Base error carrying a machine-readable code and an HTTP status."""

    code: str = "ERROR"
    http_status: int = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AuthError(AppError):
    """Authentication failure (generic, non-enumerable). Maps to HTTP 401."""

    code = "AUTH_FAILED"
    http_status = 401

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message)


class ValidationError(AppError):
    """Request validation failure. Maps to HTTP 400."""

    code = "VALIDATION_ERROR"
    http_status = 400


def error_payload(error: AppError) -> dict[str, str]:
    """Render an error as the device-facing {code, message} body."""
    return {"code": error.code, "message": error.message}
