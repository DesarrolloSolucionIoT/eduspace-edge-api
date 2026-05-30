"""Pure Device domain entity (no infrastructure or framework imports)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class KeyHasher(Protocol):
    """Abstraction the domain depends on to verify a presented key."""

    def verify(self, key: str, stored: str) -> bool:
        """Return True if ``key`` matches the ``stored`` hash."""
        ...


@dataclass(frozen=True)
class Device:
    """A registered device, authenticated by a salted-hash API key."""

    device_id: str
    api_key_hash: str
    zone_id: str
    created_at: datetime

    def verify_key(self, presented_key: str, hasher: KeyHasher) -> bool:
        """Verify a presented API key against this device's stored hash."""
        return hasher.verify(presented_key, self.api_key_hash)
