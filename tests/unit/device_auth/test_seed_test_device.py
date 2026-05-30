"""Unit test for idempotent seeding logic (US4)."""
from __future__ import annotations

from src.device_auth.application.seed_test_device import DEFAULT_DEVICE_ID, seed_test_device


class _FakeStore:
    def __init__(self) -> None:
        self.added: list[str] = []

    def exists(self, device_id: str) -> bool:
        return device_id in self.added

    def add(self, device_id: str, api_key_hash: str, zone_id: str) -> None:
        self.added.append(device_id)


class _FakeHasher:
    def hash_key(self, key: str) -> str:
        return f"hashed:{key}"


def test_seeds_when_absent() -> None:
    store = _FakeStore()
    assert seed_test_device(store, _FakeHasher()) is True
    assert store.added == [DEFAULT_DEVICE_ID]


def test_idempotent_when_present() -> None:
    store = _FakeStore()
    seed_test_device(store, _FakeHasher())
    assert seed_test_device(store, _FakeHasher()) is False
    assert store.added == [DEFAULT_DEVICE_ID]
