"""Peewee model mapping the ``devices`` table."""
from __future__ import annotations

from peewee import CharField, DateTimeField, Model

from src.db import database


class DeviceModel(Model):
    """Registered classroom monitoring device."""

    device_id = CharField(primary_key=True)
    api_key_hash = CharField()
    zone_id = CharField()
    created_at = DateTimeField()

    class Meta:
        database = database
        table_name = "devices"
