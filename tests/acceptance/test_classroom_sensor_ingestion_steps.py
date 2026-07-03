"""Step bindings for classroom_sensor_ingestion.feature (US1)."""
from __future__ import annotations

from datetime import datetime, timezone

from pytest_bdd import parsers, scenarios, then

from tests.acceptance.conftest import ScenarioContext

scenarios("features/classroom_sensor_ingestion.feature")


@then(parsers.parse("the response reports alert_led_state {state:d}"))
def assert_alert_state(context: ScenarioContext, state: int) -> None:
    assert context.response.get_json()["alert_led_state"] == state


@then("the response includes a reading_id and a recorded_at timestamp in UTC")
def assert_reading_id_and_utc(context: ScenarioContext) -> None:
    payload = context.response.get_json()
    assert isinstance(payload["reading_id"], int)
    recorded_at = datetime.fromisoformat(payload["recorded_at"])
    assert recorded_at.utcoffset() == timezone.utc.utcoffset(recorded_at)
