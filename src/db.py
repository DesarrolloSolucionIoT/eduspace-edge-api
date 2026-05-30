"""Peewee database handle (proxy) and idempotent initialization."""
from __future__ import annotations

from peewee import DatabaseProxy, SqliteDatabase

database = DatabaseProxy()


def init_db(path: str) -> None:
    """Bind the proxy to a file-backed SQLite database and create tables if absent.

    Safe to call repeatedly; rebinds to ``path`` so distinct databases (e.g. per
    test) are honored.
    """
    if database.obj is not None and not database.is_closed():
        database.close()
    database.initialize(SqliteDatabase(path, pragmas={"foreign_keys": 1}))
    database.connect(reuse_if_open=True)
    from src.device_auth.infrastructure.models import DeviceModel
    from src.iot_ingestion.infrastructure.models import SensorReadingModel

    database.create_tables([DeviceModel, SensorReadingModel])
