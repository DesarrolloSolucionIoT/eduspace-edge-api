Feature: Rejection of unauthorized or invalid ingestion requests
  Related to User Story 2 (US2): the Edge API accepts data only from registered
  devices presenting valid credentials, and rejects malformed or out-of-range
  readings, so that the local buffer and the cloud backend only receive
  trustworthy telemetry.

  Background:
    Given the Edge API is running with the development test device provisioned

  Scenario: A request without an API key is rejected with a generic 401
    When the device submits a valid reading without the X-API-Key header
    Then the response status is 401
    And the error code is "AUTH_FAILED"

  Scenario: A request with a wrong API key is rejected with a generic 401
    When the device submits a valid reading using the API key "wrong-key"
    Then the response status is 401
    And the error code is "AUTH_FAILED"

  Scenario: A reading with humidity out of range is rejected as invalid
    When the device submits a reading with temperature 22.5, humidity 150.0 and occupancy true
    Then the response status is 400
    And the error code is "VALIDATION_ERROR"

  Scenario: A reading missing the temperature field is rejected as invalid
    When the device submits a reading without the "temperature" field
    Then the response status is 400
    And the error code is "VALIDATION_ERROR"
