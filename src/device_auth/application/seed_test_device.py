"""Idempotent seeding of the development test device."""
from __future__ import annotations

from typing import Protocol

from src.device_auth.domain.device import Device

DEFAULT_DEVICE_ID = "esp32-aula-101"
DEFAULT_API_KEY = "test-api-key-edu"
DEFAULT_ZONE_ID = "aula-101"


class DeviceStore(Protocol):
    """Subset of the device repository needed for seeding."""

    def exists(self, device_id: str) -> bool:
        """Return True if the device already exists."""
        ...

    def add(self, device_id: str, api_key_hash: str, zone_id: str) -> Device:
        """Register a new device."""
        ...


class KeyHasher(Protocol):
    """Hashes the plaintext key before storage."""

    def hash_key(self, key: str) -> str:
        """Return the salted hash of ``key``."""
        ...


def seed_test_device(devices: DeviceStore, hasher: KeyHasher) -> bool:
    """Create the default test device if absent. Returns True if it was created."""
    if devices.exists(DEFAULT_DEVICE_ID):
        return False
    devices.add(DEFAULT_DEVICE_ID, hasher.hash_key(DEFAULT_API_KEY), DEFAULT_ZONE_ID)
    return True
