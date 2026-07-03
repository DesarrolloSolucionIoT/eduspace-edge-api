Feature: Classroom sensor reading ingestion with local alert decision
  Related to User Story 1 (US1): as a registered classroom device, I submit a
  periodic reading (temperature, humidity, occupancy) and immediately receive
  the locally computed alert LED state, so the classroom indicator reflects
  environmental conditions even without cloud connectivity.

  Background:
    Given the Edge API is running with the development test device provisioned

  Scenario: A reading within the zone thresholds is accepted with the alert off
    When the device submits a reading with temperature 22.5, humidity 45.0 and occupancy true
    Then the response status is 201
    And the response reports alert_led_state 0
    And the response includes a reading_id and a recorded_at timestamp in UTC

  Scenario: A temperature above the zone maximum turns the alert on
    When the device submits a reading with temperature 31.5, humidity 45.0 and occupancy true
    Then the response status is 201
    And the response reports alert_led_state 1

  Scenario: A humidity above the zone maximum turns the alert on
    When the device submits a reading with temperature 22.5, humidity 70.0 and occupancy false
    Then the response status is 201
    And the response reports alert_led_state 1
