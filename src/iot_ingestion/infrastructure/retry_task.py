"""Background retry of readings still awaiting upstream delivery."""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable

from src.iot_ingestion.application.ports import ReadingStore, UpstreamForwarder
from src.shared.clock import Clock

logger = logging.getLogger(__name__)


def run_retry_once(readings: ReadingStore, forwarder: UpstreamForwarder, clock: Clock) -> int:
    """Forward all currently-unforwarded readings. Returns the count delivered."""
    delivered = 0
    for reading in readings.iter_unforwarded():
        if reading.reading_id is not None and forwarder.forward(reading):
            readings.mark_forwarded(reading.reading_id, clock.now())
            delivered += 1
    return delivered


def start_retry_worker(
    make_readings: Callable[[], ReadingStore],
    forwarder: UpstreamForwarder,
    clock: Clock,
    interval: float,
) -> threading.Thread | None:
    """Start a daemon thread that retries forwarding every ``interval`` seconds.

    Returns None when ``interval`` <= 0 (worker disabled, e.g. in tests).
    """
    if interval <= 0:
        return None
    thread = threading.Thread(
        target=_loop, args=(make_readings, forwarder, clock, interval), daemon=True
    )
    thread.start()
    return thread


def _loop(
    make_readings: Callable[[], ReadingStore],
    forwarder: UpstreamForwarder,
    clock: Clock,
    interval: float,
) -> None:
    while True:
        time.sleep(interval)
        try:
            run_retry_once(make_readings(), forwarder, clock)
        except Exception:  # noqa: BLE001 - worker must keep running
            logger.exception("retry worker iteration failed")
