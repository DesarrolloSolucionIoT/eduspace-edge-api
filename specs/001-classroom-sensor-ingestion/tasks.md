---
description: "Task list for Classroom Sensor Ingestion & Local Alerting"
---

# Tasks: Classroom Sensor Ingestion & Local Alerting

**Input**: Design documents from `/specs/001-classroom-sensor-ingestion/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are INCLUDED and are written FIRST (must fail before implementation).
This is mandated by Constitution Principle II (Test-First, NON-NEGOTIABLE): unit tests precede
production code, and integration tests run against a real SQLite database.

**Organization**: Tasks are grouped by user story (from spec.md) so each story is an
independently testable increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US4 (user story phases only)
- Exact file paths are included in each task

## Path Conventions

Single project, organized by bounded context under `src/` with tests under `tests/`
(see plan.md → Project Structure).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and tooling.

- [X] T001 Create the project directory tree per plan.md (`src/`, `src/shared/`, `src/device_auth/{domain,application,infrastructure,interfaces}/`, `src/iot_ingestion/{domain,application,infrastructure,interfaces}/`, `tests/{unit,integration,contract}/`) with `__init__.py` files
- [X] T002 Create `requirements.txt` pinning Flask, Peewee, python-dateutil, requests, and pytest
- [X] T003 [P] Configure pytest and type checking in `pyproject.toml` (test discovery under `tests/`, mypy strict-ish settings to enforce mandatory type hints)
- [X] T004 [P] Create `src/config.py` exposing typed settings from env: `EDUSPACE_DB_PATH`, `EDUSPACE_WEB_API_URL`, `EDUSPACE_FORWARD_TIMEOUT`, `EDUSPACE_ENV`
- [X] T005 [P] Create `tests/conftest.py` and `tests/integration/conftest.py` providing a temp-file SQLite fixture and a Flask test-client fixture (real DB, not in-memory)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Cross-cutting infrastructure required by ALL user stories: database handle,
structured errors, UTC clock, shared threshold types, and the stateless authentication
mechanism (every request passes through it).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 Create `src/db.py`: a Peewee `SqliteDatabase` bound to the configured **file** path plus `init_db()` that creates tables idempotently
- [X] T007 [P] Create `src/shared/clock.py`: an injectable UTC `Clock` protocol and a system implementation returning timezone-aware UTC `datetime`
- [X] T008 [P] Create `src/shared/errors.py`: domain error types and machine-readable codes (`AUTH_FAILED`, `VALIDATION_ERROR`) plus a helper that builds `{code, message}` payloads
- [X] T009 [P] Create `src/shared/zone_thresholds.py`: `ZoneThresholds` value object (`temp_min/max`, `humidity_min/max`, all optional) — shared kernel so neither context imports the other's domain
- [X] T010 [P] Create `src/shared/threshold_config.py`: `resolve_thresholds(zone_id) -> ZoneThresholds` loading per-zone bounds from configuration (empty zone → no bounds)
- [X] T011 [P] Create `src/device_auth/infrastructure/password_hasher.py`: salted hashing (`hash_key`) and constant-time `verify_key` — never stores/returns plaintext
- [X] T012 Create `src/device_auth/infrastructure/models.py`: Peewee `DeviceModel` mapping the `devices` table (`device_id` PK, `api_key_hash`, `zone_id`, `created_at`)
- [X] T013 [P] Create `src/device_auth/domain/device.py`: pure `Device` entity with `verify_key(presented_key, hasher)` (no Peewee/Flask imports)
- [X] T014 Create `src/device_auth/infrastructure/device_repository.py`: `DeviceRepository` (`get_by_id`, `add`, `exists`) mapping `DeviceModel` ↔ `Device` (depends on T012, T013)
- [X] T015 Create `src/device_auth/application/authenticator.py`: validate `X-API-Key` against body `device_id` via repository + hasher, resolve `ZoneThresholds` by the device's `zone_id`, and return an auth context (device + thresholds); raises a generic auth error on any failure (depends on T009, T010, T011, T014)
- [X] T016 Create `src/device_auth/interfaces/middleware.py`: Flask middleware that runs the authenticator on every inbound request and attaches the auth context (device + thresholds) to the request (depends on T015)
- [X] T017 Create `src/app.py`: Flask app factory that wires `before_request` bootstrap (`init_db()`), registers the auth middleware, and provides the blueprint/route registration seam (depends on T006, T016)

**Checkpoint**: App boots, initializes a durable SQLite file, and authenticates valid devices.

---

## Phase 3: User Story 1 - Submit a reading and receive a local alert decision (Priority: P1) 🎯 MVP

**Goal**: An authenticated device submits a valid reading and immediately receives the locally
computed `alert_led_state`; the reading is persisted with a UTC-normalized timestamp.

**Independent Test**: With a device present (inserted via fixture), POST a well-formed reading
exceeding the zone thresholds → `201` with `alert_led_state: 1`; POST one within bounds →
`alert_led_state: 0`. No cloud connection required.

### Tests for User Story 1 (write first; must fail) ⚠️

- [X] T018 [P] [US1] Unit test `alert_policy` in `tests/unit/iot_ingestion/test_alert_policy.py`: breach (upper/lower temp & humidity) → 1, within bounds → 0, no thresholds → 0, occupancy never affects result
- [X] T019 [P] [US1] Unit test UTC normalization in `tests/unit/iot_ingestion/test_normalize.py`: offset/zoned ISO 8601 → UTC; naive → UTC; missing `recorded_at` → injected clock UTC
- [X] T020 [P] [US1] Integration test happy path in `tests/integration/test_ingestion_endpoint.py` (real SQLite): valid reading → `201 {reading_id, alert_led_state, recorded_at(UTC)}` and a persisted row

### Implementation for User Story 1

- [X] T021 [P] [US1] Create `src/iot_ingestion/domain/sensor_reading.py`: pure `SensorReading` entity (`temperature`, `humidity`, `occupancy`, `recorded_at` UTC)
- [X] T022 [P] [US1] Create `src/iot_ingestion/domain/alert_policy.py`: pure `evaluate(reading, thresholds) -> int` returning 0/1 (occupancy ignored)
- [X] T023 [P] [US1] Create `src/iot_ingestion/application/normalize.py`: `to_utc(value, clock)` using python-dateutil for parsing/normalization
- [X] T024 [P] [US1] Create `src/iot_ingestion/infrastructure/models.py`: Peewee `SensorReadingModel` mapping `sensor_readings` (incl. autoincrement `id`, `alert_led_state`, `forwarded_at` nullable)
- [X] T025 [US1] Create `src/iot_ingestion/application/ports.py`: `ReadingRepository` and `UpstreamForwarder` protocols (DI seams)
- [X] T026 [US1] Create `src/iot_ingestion/infrastructure/reading_repository.py`: `add(reading) -> reading_id` and helpers, mapping model ↔ entity (depends on T024, T025)
- [X] T027 [US1] Create `src/iot_ingestion/application/ingest_reading.py`: orchestrate normalize → evaluate `alert_led_state` → persist → return result; forwarding is a no-op stub at this stage (depends on T021–T026)
- [X] T028 [US1] Create `src/iot_ingestion/interfaces/routes.py`: `POST /api/v1/iot-monitoring/sensor-readings` reading the auth context, invoking the use case, and returning `201`; register the blueprint in `src/app.py` (depends on T027, T017)

**Checkpoint**: MVP — a valid device gets a correct, cloud-independent alert decision and the reading is durably stored.

---

## Phase 4: User Story 2 - Reject unauthorized or invalid requests (Priority: P2)

**Goal**: Requests without valid credentials get a single generic `401`; readings with missing
or out-of-range values get a `400`. Rejected requests persist nothing and forward nothing.

**Independent Test**: Submit with no credentials, unknown device, and wrong key → each returns
the same generic `401`. Submit valid credentials but bad body (missing/out-of-range) → `400`.
Confirm no rows are written in any case.

### Tests for User Story 2 (write first; must fail) ⚠️

- [X] T029 [P] [US2] Unit test request validator in `tests/unit/iot_ingestion/test_request_validator.py`: missing fields, wrong types, temperature/humidity out of range → validation error
- [X] T030 [P] [US2] Integration test auth failures in `tests/integration/test_auth_failures.py`: missing key, unknown `device_id`, wrong key → identical generic `401 {code: AUTH_FAILED}`; nothing persisted
- [X] T031 [P] [US2] Integration test validation errors in `tests/integration/test_validation_errors.py`: bad body → `400 {code: VALIDATION_ERROR}`; nothing persisted

### Implementation for User Story 2

- [X] T032 [P] [US2] Create `src/iot_ingestion/application/validation.py`: `validate_reading_request(body)` enforcing required fields, types, and ranges (temp −40..85 °C, humidity 0..100 %), raising structured validation errors
- [X] T033 [US2] Register Flask error handlers in `src/app.py` mapping validation errors → `400` and auth errors → `401`, each rendering `{code, message}` via `src/shared/errors.py`
- [X] T034 [US2] Harden `src/device_auth/interfaces/middleware.py`: return one generic `401` for missing/unknown/invalid credentials while logging the specific reason server-side (FR-003b)
- [X] T035 [US2] Update `src/iot_ingestion/interfaces/routes.py` to run `validate_reading_request` before any persistence so rejected requests write nothing (depends on T032)

**Checkpoint**: Security and input gates enforced; US1 still passes.

---

## Phase 5: User Story 3 - Persist locally and forward to the cloud with offline buffering (Priority: P3)

**Goal**: Accepted readings are forwarded asynchronously (best-effort) with the stable
`reading_id` for dedup; on failure they remain in SQLite (`forwarded_at IS NULL`) and a
background task retries until success. The device response never depends on the cloud.

**Independent Test**: With upstream reachable → row gets `forwarded_at` set. With upstream
unreachable → device still gets `201`, row stays `forwarded_at NULL`. Restore upstream → retry
forwards buffered rows and stamps `forwarded_at`, with no duplicate delivery.

### Tests for User Story 3 (write first; must fail) ⚠️

- [X] T036 [P] [US3] Unit test upstream forwarder in `tests/unit/iot_ingestion/test_upstream_forwarder.py`: timeout/connection errors are caught and reported as failure (never propagate to caller); payload includes `reading_id`
- [X] T037 [P] [US3] Integration test offline buffering in `tests/integration/test_offline_buffering.py`: upstream unreachable → `201` and `forwarded_at IS NULL`
- [X] T038 [P] [US3] Integration test retry in `tests/integration/test_retry_forwarding.py`: buffered rows forwarded on next run, `forwarded_at` set, same `reading_id` reused (dedup), no duplicate sends

### Implementation for User Story 3

- [X] T039 [P] [US3] Create `src/iot_ingestion/infrastructure/upstream_forwarder.py`: `requests`-based client posting to `EDUSPACE_WEB_API_URL` with configurable timeout, sending `reading_id`; returns success/failure without raising
- [X] T040 [US3] Update `src/iot_ingestion/application/ingest_reading.py` to forward best-effort after persistence: on success set `forwarded_at`; on failure log and leave `NULL`; never alter the device response (depends on T039)
- [X] T041 [US3] Add `mark_forwarded(reading_id, ts)` and `iter_unforwarded()` to `src/iot_ingestion/infrastructure/reading_repository.py`
- [X] T042 [US3] Create `src/iot_ingestion/infrastructure/retry_task.py`: periodically re-forward rows where `forwarded_at IS NULL` and stamp `forwarded_at` on success (depends on T039, T041)
- [X] T043 [US3] Wire the retry task to start with the app in `src/app.py` (depends on T042)

**Checkpoint**: Zero data loss across outages; forwarding failures never reach the device.

---

## Phase 6: User Story 4 - Auto-provisioned test device for local development (Priority: P4)

**Goal**: On startup in development mode, the service idempotently seeds a default test device
(`esp32-aula-101` / `test-api-key-edu`) so developers can call the API with no manual setup.

**Independent Test**: Fresh dev start → submit a reading with the default credentials → accepted
and evaluated. Restart → the device is not duplicated.

### Tests for User Story 4 (write first; must fail) ⚠️

- [X] T044 [P] [US4] Integration test seeding in `tests/integration/test_seed_test_device.py`: fresh dev start creates the test device and it authenticates; second startup does not duplicate it

### Implementation for User Story 4

- [X] T045 [US4] Create `src/device_auth/application/seed_test_device.py`: idempotent use case that creates the default test device (hashing its key) only when `EDUSPACE_ENV=development` and it is absent
- [X] T046 [US4] Wire seeding into the `before_request` bootstrap in `src/app.py`, gated by development mode and run-once (depends on T045)

**Checkpoint**: Zero-setup local development per quickstart.md.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Contract conformance, documentation, and constitution compliance sweep.

- [X] T047 [P] Contract test in `tests/contract/test_sensor_readings_contract.py`: request/response shapes and status codes match `contracts/sensor-readings.openapi.yaml`
- [X] T048 [P] Validate `quickstart.md` end-to-end against the running service (happy path, 401, 400, offline buffering, restart durability) and confirm unattended operation (FR-016): the service accepts scheduled readings and the background retry task runs with no human intervention
- [X] T049 [P] Constitution compliance sweep: confirm every function ≤ 30 lines, type hints on all signatures, dependencies injected, and all I/O confined to infrastructure
- [X] T050 Finalize `requirements.txt` version pins and a short run/test section in `README.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Stories (Phases 3–6)**: All depend on Foundational completion.
  - US1 (P1) is the MVP and should come first.
  - US2 (P2) builds on US1's route/use case (adds validation + error mapping).
  - US3 (P3) builds on US1's ingest use case (adds forwarding/retry).
  - US4 (P4) depends only on Foundational (device_auth) and the app bootstrap.
- **Polish (Phase 7)**: Depends on the user stories being implemented.

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational only.
- **US2 (P2)**: Depends on Foundational + US1 (extends the endpoint).
- **US3 (P3)**: Depends on Foundational + US1 (extends the ingest use case).
- **US4 (P4)**: Depends on Foundational only (independent of US1–US3); can run in parallel with US1 once Foundational is done.

### Within Each User Story

- Tests are written FIRST and must FAIL before implementation (Constitution II).
- Domain (entities, policies) → application (use cases) → infrastructure (repos, clients) → interfaces (routes).

### Parallel Opportunities

- Setup: T003, T004, T005 in parallel.
- Foundational: T007, T008, T009, T010, T011, T013 in parallel (distinct files); T012/T014/T015/T016/T017 are sequential on the auth chain.
- US1 tests T018–T020 in parallel; domain files T021/T022/T023/T024 in parallel.
- US2 tests T029–T031 in parallel.
- US3 tests T036–T038 in parallel.
- US4 can proceed in parallel with US1–US3 after Foundational.

---

## Parallel Example: User Story 1

```bash
# Write the failing tests for US1 together:
Task: "Unit test alert_policy in tests/unit/iot_ingestion/test_alert_policy.py"
Task: "Unit test UTC normalization in tests/unit/iot_ingestion/test_normalize.py"
Task: "Integration test happy path in tests/integration/test_ingestion_endpoint.py"

# Then the independent domain/infra files together:
Task: "Create SensorReading entity in src/iot_ingestion/domain/sensor_reading.py"
Task: "Create alert_policy in src/iot_ingestion/domain/alert_policy.py"
Task: "Create normalize helper in src/iot_ingestion/application/normalize.py"
Task: "Create SensorReadingModel in src/iot_ingestion/infrastructure/models.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (US1).
3. **STOP and VALIDATE**: a valid device receives a correct, cloud-independent alert decision and the reading is durably persisted.

### Incremental Delivery

1. Setup + Foundational → app boots, authenticates, durable DB.
2. US1 → MVP (local alerting + persistence). Demo.
3. US2 → security/input gates (401/400, nothing persisted). Demo.
4. US3 → async forwarding + offline buffering + retry. Demo.
5. US4 → zero-setup dev test device. Demo.
6. Polish → contract test, quickstart validation, constitution sweep.

### Notes

- [P] = different files, no dependency on incomplete tasks.
- Verify each story's tests fail before implementing it.
- Commit after each task or logical group.
- Keep cross-context dependencies at the application layer only; `ZoneThresholds` lives in the shared kernel to avoid cross-context domain imports.
