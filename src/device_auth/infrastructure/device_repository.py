"""Peewee-backed repository mapping DeviceModel rows to Device entities."""
from __future__ import annotations

from datetime import datetime, timezone

from src.device_auth.domain.device import Device
from src.device_auth.infrastructure.models import DeviceModel


class DeviceRepository:
    """Persistence adapter for registered devices."""

    def get_by_id(self, device_id: str) -> Device | None:
        """Return the device with this id, or None if not registered."""
        row = DeviceModel.get_or_none(DeviceModel.device_id == device_id)
        return self._to_entity(row) if row is not None else None

    def exists(self, device_id: str) -> bool:
        """Return True if a device with this id is registered."""
        return DeviceModel.select().where(DeviceModel.device_id == device_id).exists()

    def add(self, device_id: str, api_key_hash: str, zone_id: str) -> Device:
        """Create and return a new device with a UTC creation timestamp."""
        row = DeviceModel.create(
            device_id=device_id,
            api_key_hash=api_key_hash,
            zone_id=zone_id,
            created_at=datetime.now(timezone.utc),
        )
        return self._to_entity(row)

    @staticmethod
    def _to_entity(row: DeviceModel) -> Device:
        return Device(
            device_id=row.device_id,
            api_key_hash=row.api_key_hash,
            zone_id=row.zone_id,
            created_at=row.created_at,
        )
