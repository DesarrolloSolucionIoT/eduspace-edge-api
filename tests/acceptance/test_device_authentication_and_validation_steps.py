"""Step bindings for device_authentication_and_validation.feature (US2)."""
from __future__ import annotations

from pytest_bdd import parsers, scenarios, then, when

from tests.acceptance.conftest import ROUTE, VALID_KEY, ScenarioContext, _body

scenarios("features/device_authentication_and_validation.feature")


@when("the device submits a valid reading without the X-API-Key header")
def submit_without_key(client, context: ScenarioContext) -> None:  # noqa: ANN001
    context.response = client.post(ROUTE, json=_body(22.5, 45.0, True))


@when(parsers.parse('the device submits a valid reading using the API key "{api_key}"'))
def submit_with_key(client, context: ScenarioContext, api_key: str) -> None:  # noqa: ANN001
    context.response = client.post(
        ROUTE, json=_body(22.5, 45.0, True), headers={"X-API-Key": api_key}
    )


@when(parsers.parse('the device submits a reading without the "{field}" field'))
def submit_missing_field(client, context: ScenarioContext, field: str) -> None:  # noqa: ANN001
    body = _body(22.5, 45.0, True)
    del body[field]
    context.response = client.post(ROUTE, json=body, headers={"X-API-Key": VALID_KEY})


@then(parsers.parse('the error code is "{code}"'))
def assert_error_code(context: ScenarioContext, code: str) -> None:
    assert context.response.get_json()["code"] == code
