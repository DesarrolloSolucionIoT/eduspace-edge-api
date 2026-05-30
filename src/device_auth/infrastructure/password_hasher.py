"""Salted PBKDF2 hashing of device API keys (never stores plaintext)."""
from __future__ import annotations

import hashlib
import hmac
import secrets


class Pbkdf2Hasher:
    """Hashes and verifies API keys using PBKDF2-HMAC-SHA256 with a per-key salt."""

    def __init__(self, iterations: int = 100_000) -> None:
        self._iterations = iterations

    def hash_key(self, key: str) -> str:
        """Return a ``salt$digest`` string for the given key."""
        salt = secrets.token_hex(16)
        return f"{salt}${self._derive(key, salt)}"

    def verify(self, key: str, stored: str) -> bool:
        """Return True if ``key`` matches the stored ``salt$digest`` value."""
        salt, _, digest = stored.partition("$")
        if not salt or not digest:
            return False
        return hmac.compare_digest(self._derive(key, salt), digest)

    def _derive(self, key: str, salt: str) -> str:
        raw = hashlib.pbkdf2_hmac("sha256", key.encode(), salt.encode(), self._iterations)
        return raw.hex()
