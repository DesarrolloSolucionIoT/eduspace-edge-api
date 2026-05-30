"""Peewee model mapping the ``sensor_readings`` table."""
from __future__ import annotations

from peewee import (
    AutoField,
    CharField,
    DateTimeField,
    FloatField,
    IntegerField,
    Model,
)

from src.db import database


class SensorReadingModel(Model):
    """A persisted sensor reading; ``forwarded_at`` is NULL until delivered upstream."""

    id = AutoField()
    device_id = CharField(index=True)  # logical FK to devices.device_id
    temperature = FloatField()
    humidity = FloatField()
    occupancy = IntegerField()  # stored as 0/1
    alert_led_state = IntegerField()  # 0/1
    recorded_at = DateTimeField()
    forwarded_at = DateTimeField(null=True)

    class Meta:
        database = database
        table_name = "sensor_readings"
