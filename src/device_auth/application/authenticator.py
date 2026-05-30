"""Stateless per-request authentication and zone-threshold resolution."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Protocol

from src.device_auth.domain.device import Device, KeyHasher
from src.shared.errors import AuthError
from src.shared.zone_thresholds import ZoneThresholds

logger = logging.getLogger(__name__)

ThresholdResolver = Callable[[str], ZoneThresholds]


class DeviceReader(Protocol):
    """Read-only device lookup the authenticator depends on."""

    def get_by_id(self, device_id: str) -> Device | None:
        """Return the device with this id, or None."""
        ...


@dataclass(frozen=True)
class AuthContext:
    """The authenticated device plus its resolved zone thresholds."""

    device: Device
    thresholds: ZoneThresholds


class Authenticator:
    """Validates X-API-Key against device_id and resolves zone thresholds."""

    def __init__(
        self, devices: DeviceReader, hasher: KeyHasher, resolve_thresholds: ThresholdResolver
    ) -> None:
        self._devices = devices
        self._hasher = hasher
        self._resolve = resolve_thresholds

    def authenticate(self, device_id: str | None, api_key: str | None) -> AuthContext:
        """Return an AuthContext or raise a generic AuthError (reason logged)."""
        if not device_id or not api_key:
            raise self._reject("missing credentials")
        device = self._devices.get_by_id(device_id)
        if device is None:
            raise self._reject(f"unknown device '{device_id}'")
        if not device.verify_key(api_key, self._hasher):
            raise self._reject(f"invalid key for device '{device_id}'")
        return AuthContext(device=device, thresholds=self._resolve(device.zone_id))

    @staticmethod
    def _reject(reason: str) -> AuthError:
        logger.warning("authentication failed: %s", reason)
        return AuthError()
