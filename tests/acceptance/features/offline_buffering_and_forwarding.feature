Feature: Offline buffering and idempotent forwarding to the cloud backend
  Related to User Story 3 (US3): every accepted reading is persisted locally
  and forwarded to the cloud backend asynchronously; if the backend is
  unreachable the reading stays buffered and is delivered later without
  duplicates, so no telemetry is lost during connectivity outages.

  Background:
    Given the Edge API is running with the development test device provisioned

  Scenario: A reading is accepted and buffered while the backend is unreachable
    Given the cloud backend is unreachable
    When the device submits a reading with temperature 22.0, humidity 45.0 and occupancy true
    Then the response status is 201
    And the reading is stored locally with no forwarded timestamp

  Scenario: A buffered reading is delivered once connectivity is restored
    Given the cloud backend is unreachable
    And the device submits a reading with temperature 31.5, humidity 70.0 and occupancy true
    When the cloud backend becomes reachable again and the retry cycle runs
    Then exactly 1 buffered reading is delivered to the backend
    And the delivered payload carries the original reading_id for idempotent deduplication
    And the reading is marked as forwarded locally
