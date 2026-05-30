# Feature Specification: Classroom Sensor Ingestion & Local Alerting

**Feature Branch**: `001-classroom-sensor-ingestion`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "Build an IoT edge service for the EduSpace platform that sits between embedded classroom sensor devices and a cloud backend. It accepts periodic sensor readings (temperature, humidity, occupancy) from registered/authorized devices, evaluates environmental thresholds locally to tell the device whether its alert indicator should be active, persists readings locally for resilience, and forwards them asynchronously to the cloud — buffering when the cloud is unreachable. Devices authenticate with a device identifier and secret API key; a default test device is auto-provisioned for local development. The service runs unattended with a stable, versioned API contract."

## Clarifications

### Session 2026-05-30

- Q: Does occupancy state affect the alert decision, or is it contextual-only? → A: Contextual-only — occupancy is recorded with each reading but does not affect the alert decision; only temperature/humidity thresholds drive it.
- Q: How is a reading uniquely identified so the cloud can deduplicate across retries? → A: The service assigns each accepted reading a stable unique ID at ingestion and includes it on every forward attempt; the cloud deduplicates by that ID.
- Q: What is the local buffer retention policy during a cloud outage? → A: Unbounded — retain all unforwarded readings until delivery succeeds; never drop (prioritize zero data loss).
- Q: How are device API keys stored at rest in the local registry? → A: Store only a salted hash of the API key and validate by hashing the presented key and comparing; never store plaintext.
- Q: Do authentication-failure responses distinguish missing vs unknown-device vs wrong-key? → A: No — return one generic auth-failure code/message to the device for all three cases, but log the specific reason server-side for diagnostics.
- Q: Should the device be able to distinguish a cloud-unavailability error? → A: No — forwarding is asynchronous, so cloud-unavailability is never surfaced to the device; device-facing errors are only authentication (401) and validation (400). 503 is reserved by the constitution for synchronous upstream paths and is not emitted here.
- Q: Are per-zone thresholds persisted or configuration-sourced? → A: Configuration-sourced, keyed by zone identifier (no zone table in this iteration); each Device records its zone identifier. A persisted zone store is a future additive change.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Submit a reading and receive a local alert decision (Priority: P1)

A registered classroom device sends a periodic reading containing temperature, relative
humidity, and occupancy state. The service immediately evaluates the reading against the
environmental thresholds configured for that device's classroom zone and responds telling
the device whether its alert indicator (warning LED) should be active or inactive.

**Why this priority**: This is the core real-time value of the edge service. The device
cannot decide whether to warn occupants without this response, and the response must be
available even when the cloud is down. Without it there is no product.

**Independent Test**: Send a well-formed reading from an authorized device with values that
exceed the zone thresholds; confirm the response indicates the alert indicator should be
active. Send another within thresholds; confirm it indicates inactive. No cloud connection
is required for either.

**Acceptance Scenarios**:

1. **Given** an authorized device whose zone has a temperature ceiling, **When** it submits
   a reading above that ceiling, **Then** the service responds that the alert indicator
   should be active.
2. **Given** an authorized device whose zone thresholds are all satisfied, **When** it
   submits a reading within bounds, **Then** the service responds that the alert indicator
   should be inactive.
3. **Given** the cloud backend is unreachable, **When** an authorized device submits a valid
   reading, **Then** the service still returns a correct alert-indicator decision without
   delay caused by the cloud.
4. **Given** a reading whose timestamp is expressed in a non-UTC form, **When** it is
   accepted, **Then** the stored reading's time is normalized to UTC.

---

### User Story 2 - Reject unauthorized or invalid requests (Priority: P2)

The service must accept data only from devices that are registered and present valid
credentials (a device identifier plus a secret API key). Any request lacking valid
credentials is rejected and no data is stored or forwarded.

**Why this priority**: Trust in the data and protection of the platform depend on every
request being authenticated. It gates US1 in production, but US1's evaluation logic can be
demonstrated independently with the auto-provisioned test device.

**Independent Test**: Submit an otherwise valid reading with (a) no credentials, (b) an
unknown device identifier, and (c) a known identifier with a wrong key; confirm each is
rejected with an authentication error and that nothing is persisted or forwarded.

**Acceptance Scenarios**:

1. **Given** a request with no device identifier or no API key, **When** it is received,
   **Then** the service rejects it as an authentication failure and stores nothing.
2. **Given** a request whose device identifier is not registered, **When** it is received,
   **Then** the service rejects it as an authentication failure.
3. **Given** a request whose device identifier is registered but whose API key does not
   match, **When** it is received, **Then** the service rejects it as an authentication
   failure.
4. **Given** a reading that passes authentication but is missing required values or contains
   out-of-range values, **When** it is received, **Then** the service rejects it as a
   validation error and stores nothing.

---

### User Story 3 - Persist locally and forward to the cloud with offline buffering (Priority: P3)

Every accepted reading is persisted locally and then forwarded to the cloud backend
asynchronously. If the cloud is unreachable, the reading remains buffered locally and is
forwarded automatically once the cloud becomes reachable again. No reading is lost and the
device is never made to wait on the cloud.

**Why this priority**: Resilience and eventual delivery are essential for unattended
operation, but they build on top of accepting and evaluating readings (US1). The device's
immediate experience does not change whether forwarding succeeds now or later.

**Independent Test**: With the cloud reachable, submit readings and confirm they reach the
cloud. Make the cloud unreachable, submit more readings, confirm the device still receives
normal responses and the readings are retained locally; restore the cloud and confirm the
buffered readings are forwarded without duplication.

**Acceptance Scenarios**:

1. **Given** the cloud backend is reachable, **When** an accepted reading is processed,
   **Then** it is persisted locally and forwarded to the cloud.
2. **Given** the cloud backend is unreachable, **When** an accepted reading is processed,
   **Then** the device receives a normal alert-indicator response and the reading is
   retained locally for later forwarding.
3. **Given** readings buffered during an outage, **When** the cloud becomes reachable again,
   **Then** the buffered readings are forwarded automatically.
4. **Given** a forwarding attempt fails, **When** the failure occurs, **Then** it is logged
   and queued for retry and never surfaces as a server error to the device.

---

### User Story 4 - Auto-provisioned test device for local development (Priority: P4)

When the service starts in a local development or testing context, it automatically
provisions a known default test device (identifier and key) so developers can exercise the
API immediately without manual registration.

**Why this priority**: A convenience that accelerates development and testing. It is not
needed for production value delivery, so it is the lowest priority.

**Independent Test**: Start the service fresh in development mode and, without any manual
setup, submit a reading using the documented default test credentials; confirm it is
accepted and evaluated.

**Acceptance Scenarios**:

1. **Given** a fresh local environment, **When** the service starts in development mode,
   **Then** a default test device exists and can authenticate successfully.
2. **Given** the default test device already exists, **When** the service restarts, **Then**
   it is not duplicated.

---

### Edge Cases

- A reading is missing one of the required values (temperature, humidity, or occupancy) →
  rejected as a validation error.
- A reading contains a value outside the physically plausible range (e.g., humidity above
  100%) → rejected as a validation error.
- A device's classroom zone has no thresholds configured → the service applies a documented
  default behavior (treated as no breach / inactive) rather than failing the request.
- The cloud backend is slow or unreachable for an extended period → readings continue to be
  accepted and buffered; the device experience is unaffected.
- Duplicate or replayed readings during retry → forwarding does not create duplicates in the
  cloud beyond a single logical delivery.
- A reading arrives with a device-local timestamp in a different time zone or with clock
  skew → it is normalized to UTC before being stored.
- A version of the API contract that a device does not recognize is requested → the device's
  expected version continues to work (contract is versioned and backward-compatible).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST accept sensor readings containing temperature, relative
  humidity, and a binary occupancy state from classroom monitoring devices.
- **FR-002**: The service MUST authenticate every incoming request using a device identifier
  and a secret API key, with no reliance on prior session state.
- **FR-003**: The service MUST reject any request that omits credentials, presents an
  unregistered device identifier, or presents a key that does not match the registered
  device, treating each as an authentication failure.
- **FR-003a**: The service MUST store device API keys only as salted hashes and MUST validate
  a request by hashing the presented key and comparing; plaintext API keys MUST NOT be
  persisted.
- **FR-003b**: The service MUST return a single generic authentication-failure response (same
  machine-readable code and message) for missing credentials, unknown device identifier, and
  invalid key, so device identifiers cannot be enumerated. The specific failure reason MUST be
  logged server-side for diagnostics.
- **FR-004**: The service MUST validate every authenticated reading and reject readings with
  missing required values or values outside accepted ranges, treating these as validation
  errors distinct from authentication failures.
- **FR-005**: For each valid reading, the service MUST evaluate the temperature and humidity
  values against the environmental thresholds configured for the device's classroom zone and
  determine whether the device's alert indicator should be active or inactive. Occupancy state
  MUST NOT influence this decision.
- **FR-006**: The service MUST compute the alert-indicator decision locally and MUST NOT
  require communication with the cloud backend or any external system to produce it.
- **FR-007**: The service MUST return the alert-indicator decision to the device in the
  immediate response to its reading submission.
- **FR-008**: The service MUST persist every accepted reading locally before considering the
  submission complete.
- **FR-009**: The service MUST forward accepted readings to the cloud backend asynchronously,
  without blocking the device's response on the outcome of forwarding.
- **FR-010**: When the cloud backend is unreachable, the service MUST retain accepted
  readings locally and forward them automatically once the backend becomes reachable again,
  without losing readings. Retention is unbounded: unforwarded readings MUST be kept until
  delivery succeeds and MUST NOT be dropped to reclaim space.
- **FR-011**: The service MUST log forwarding failures and queue them for retry, and MUST
  NOT surface a forwarding failure as a server error to the device.
- **FR-011a**: The service MUST assign each accepted reading a stable unique identifier at
  ingestion and include that identifier on every forwarding attempt, so that the cloud
  backend can deduplicate readings delivered more than once during retries.
- **FR-012**: The service MUST normalize device-supplied timestamps to UTC before persisting
  a reading.
- **FR-013**: Every error response returned to a device MUST include both a machine-readable
  code and a human-readable message, and MUST distinguish authentication failures from
  validation errors. Cloud-unavailability is NOT surfaced to the device on the reading-
  submission path: because forwarding is asynchronous (FR-009, FR-011), an unreachable cloud
  never produces a device-facing error. The machine-readable code reserved for synchronous
  upstream-unavailability conditions (HTTP 503) is defined by the constitution but is not
  emitted by this endpoint.
- **FR-014**: The service MUST automatically provision a known default test device in local
  development/testing contexts, without duplicating it on restart, and MUST NOT rely on that
  device for production operation.
- **FR-015**: The service MUST expose a stable, versioned API contract so that device
  firmware and cloud-side ingestion remain compatible across service updates.
- **FR-016**: The service MUST operate unattended, accepting readings sent on a fixed
  schedule without human intervention.

### Key Entities *(include if feature involves data)*

- **Device**: A registered classroom monitoring unit. Identified by a device identifier and
  authenticated by a secret API key stored only as a salted hash. Associated with exactly one
  classroom zone.
- **Classroom Zone**: A monitored space identified by a zone identifier, with a configured set
  of environmental thresholds (e.g., acceptable temperature and humidity bounds) used to
  evaluate readings from its device(s). In this iteration a zone is a **configuration-sourced**
  concept keyed by zone identifier — not a persisted table; each Device records the zone
  identifier it belongs to.
- **Sensor Reading**: A single measurement event containing temperature, relative humidity,
  binary occupancy state, the submitting device, and a timestamp normalized to UTC. Carries a
  service-assigned stable unique identifier used for forwarding deduplication.
- **Alert Evaluation Result**: The locally computed outcome for a reading, indicating whether
  the device's alert indicator should be active or inactive and which threshold(s), if any,
  were breached.
- **Forwarding Queue Entry**: A persisted record representing a reading awaiting successful
  delivery to the cloud backend, including its retry status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A device receives its alert-indicator decision effectively immediately after
  submitting a reading (perceived as instant), in every case, regardless of cloud backend
  availability.
- **SC-002**: 100% of readings submitted by authorized devices with valid data are persisted
  locally and are not lost, including during cloud outages.
- **SC-003**: 100% of requests lacking valid credentials are rejected, and none of their data
  is persisted or forwarded.
- **SC-004**: After a cloud outage of any duration ends, 100% of readings buffered during the
  outage are forwarded, with no duplicate logical deliveries.
- **SC-005**: The alert-indicator decision is correct for 100% of readings relative to the
  zone's configured thresholds, with no dependency on external systems.
- **SC-006**: A developer can submit a successful reading against a freshly started local
  service using only documented default credentials, with zero manual setup steps.
- **SC-007**: Every error returned to a device carries a distinct machine-readable code and a
  human-readable message, enabling the device to react differently to authentication versus
  validation failures. Cloud-unavailability is never returned as a device-facing error on the
  reading-submission path (readings are buffered and retried), so the device does not need to
  handle it.

## Assumptions

- The alert-indicator decision is driven by temperature and humidity thresholds configured
  per classroom zone; occupancy state is recorded with each reading and does not by itself
  trigger an alert (it is contextual data for the cloud platform).
- "Exceeds threshold" includes breaching either an upper or a lower configured bound for a
  measured value.
- If a classroom zone has no thresholds configured, no breach is reported and the alert
  indicator is inactive for its readings (documented default, not an error).
- Devices submit readings on a fixed schedule; the service does not need to poll or push to
  devices outside the response to a reading submission.
- The cloud backend exposes an ingestion endpoint capable of accepting forwarded readings;
  its availability is intermittent and outside this service's control.
- "Local development/testing context" is distinguished from production by configuration; the
  default test device is provisioned only in that context.
- Backward compatibility of the versioned API contract means a device built against a given
  contract version continues to function after service updates within that version.
- Accepted value ranges for validation are: temperature −40.0 to 85.0 °C (typical sensor
  operating range) and relative humidity 0.0 to 100.0 %. Values outside these ranges, missing
  values, or wrong types are validation errors.
- Per-zone thresholds are configuration-sourced and keyed by zone identifier (no zone table in
  this iteration); moving thresholds into a persisted store is a future, additive change.
- Terminology: the device-facing "alert indicator" / "warning LED" corresponds to the
  `alert_led_state` field in the API contract (1 = active, 0 = inactive).
- Constitution alignment: the constitution reserves HTTP 503 for synchronous upstream-
  unavailability conditions; this feature has no synchronous upstream dependency on the request
  path, so 503 is intentionally never emitted, and forwarding failures never produce a 5xx
  (they are buffered and retried).

## Dependencies

- An external cloud backend ingestion endpoint for forwarded readings (intermittently
  available).
- Per-zone environmental threshold configuration available to the service at evaluation time.
