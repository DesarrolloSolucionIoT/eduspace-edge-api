# Implementation Plan: Classroom Sensor Ingestion & Local Alerting

**Branch**: `001-classroom-sensor-ingestion` | **Date**: 2026-05-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-classroom-sensor-ingestion/spec.md`

## Summary

An unattended IoT edge service that ingests periodic classroom sensor readings (temperature,
humidity, occupancy) from authenticated devices, computes an alert-LED decision **locally**
against per-zone thresholds, persists every accepted reading to a local SQLite file, and
forwards readings asynchronously to the EduSpace cloud Web API — buffering them in SQLite
(`forwarded_at = NULL`) for background retry when the upstream is unreachable.

Technical approach: Python 3.13 + Flask exposing a single versioned endpoint
`POST /api/v1/iot-monitoring/sensor-readings`. Two bounded contexts — `device_auth`
(stateless `X-API-Key` validation, salted-hash key storage, dev test-device seeding) and
`iot_ingestion` (validation, UTC normalization via python-dateutil, local alert evaluation,
persistence, and upstream forwarding via `requests`). Peewee ORM over a local SQLite database
file provides durable, restart-surviving storage.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: Flask (HTTP), Peewee (ORM), python-dateutil (timestamp
normalization), requests (upstream forwarding). All pinned in `requirements.txt`.

**Storage**: SQLite via a local database **file** (not in-memory) so readings survive process
restarts. Two tables: `devices` and `sensor_readings`.

**Testing**: pytest. Unit tests for domain/application logic (mocked collaborators);
integration tests against a **real SQLite** database (per Constitution Principle II).

**Target Platform**: Linux/edge host running an unattended Python process (also runnable on
the developer's Windows machine for local development).

**Project Type**: Single web service (single project layout, organized by bounded context).

**Performance Goals**: Device-perceived response is effectively instant (alert decision
computed locally; no upstream round-trip on the request path). Target < 100 ms p95 for the
ingestion endpoint excluding asynchronous forwarding.

**Constraints**: Offline-capable (must accept and buffer readings when upstream is down);
stateless authentication (no session state); UTC-normalized persistence; functions ≤ 30
lines; type hints mandatory; dependencies injected.

**Scale/Scope**: Low message volume per device (fixed-schedule readings, e.g., one every
few seconds-to-minutes per classroom device); tens-to-hundreds of devices per edge node.
Single endpoint, two bounded contexts.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against EduSpace Edge API Constitution v1.0.0.

| Principle | Gate | Status |
|-----------|------|--------|
| I. Layered DDD | Two bounded contexts (`device_auth`, `iot_ingestion`), each split into domain/application/infrastructure/interfaces. Domain imports neither infrastructure nor interfaces. `iot_ingestion` consumes `device_auth` only through an application-layer contract (resolved device + zone thresholds attached to request context) — never its domain directly. | ✅ PASS |
| II. Test-First (NON-NEGOTIABLE) | Plan mandates failing unit tests first; happy path, auth failure, validation error, and upstream-forwarding failure covered. Integration tests use real SQLite. | ✅ PASS (enforced in tasks) |
| III. Disciplined Code Quality | Type hints on all signatures; functions ≤ 30 lines; small single-purpose modules; dependencies injected (repositories, upstream client, clock, hasher); all I/O (SQLite writes, HTTP calls) confined to infrastructure. | ✅ PASS |
| IV. IoT Edge Resilience | `recorded_at` normalized to UTC before persistence (python-dateutil); per-request `X-API-Key` validation with no session state; readings buffered in SQLite when upstream down; `alert_led_state` computed locally with zero upstream dependency. | ✅ PASS |
| V. Structured Error Handling | Every error carries a machine-readable code + human-readable message; 400 for validation, 401 (generic) for auth. Forwarding is asynchronous, so upstream unavailability never produces a 5xx to the device — failures are logged and left in SQLite (`forwarded_at = NULL`) for retry. 503 is reserved for any future synchronous upstream dependency on the request path; none exists here, so it is never emitted. | ✅ PASS |

**Initial Constitution Check: PASS** — no violations; Complexity Tracking not required.

**Post-Design Constitution Check (after Phase 1): PASS** — the data model, contract, and
quickstart preserve layer boundaries, stateless auth, UTC normalization, local alerting, and
asynchronous-forwarding error semantics. No new violations introduced. See
[research.md](research.md) for the threshold-source and 503-mapping decisions.

## Project Structure

### Documentation (this feature)

```text
specs/001-classroom-sensor-ingestion/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── sensor-readings.openapi.yaml
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/
├── app.py                          # Flask app factory; before_request bootstrap (db init + seed)
├── config.py                       # Settings from env (DB path, EDUSPACE_WEB_API_URL, timeout, dev mode)
├── shared/
│   ├── errors.py                   # Error codes + structured error response helper
│   └── clock.py                    # UTC clock abstraction (injectable)
├── device_auth/
│   ├── domain/
│   │   └── device.py               # Device entity + credential verification logic (pure)
│   ├── application/
│   │   ├── authenticator.py        # Validates X-API-Key against device_id; resolves zone thresholds
│   │   └── seed_test_device.py     # Dev-only seeding use case (idempotent)
│   ├── infrastructure/
│   │   ├── models.py               # Peewee DeviceModel (devices table)
│   │   ├── device_repository.py    # DeviceRepository (Peewee-backed)
│   │   └── password_hasher.py      # Salted hashing of API keys
│   └── interfaces/
│       └── middleware.py           # Flask middleware enforcing auth on inbound requests
├── iot_ingestion/
│   ├── domain/
│   │   ├── sensor_reading.py       # SensorReading entity (temperature, humidity, occupancy, recorded_at)
│   │   ├── zone_thresholds.py      # ZoneThresholds value object
│   │   └── alert_policy.py         # Pure alert_led_state evaluation (0/1)
│   ├── application/
│   │   ├── ingest_reading.py       # Orchestrates persist → evaluate → forward
│   │   └── ports.py                # Repository + UpstreamForwarder protocols (DI seams)
│   ├── infrastructure/
│   │   ├── models.py               # Peewee SensorReadingModel (sensor_readings table)
│   │   ├── reading_repository.py   # ReadingRepository (Peewee-backed)
│   │   ├── upstream_forwarder.py   # requests-based Web API client (configurable timeout)
│   │   └── retry_task.py           # Background retry of readings with forwarded_at IS NULL
│   └── interfaces/
│       └── routes.py               # POST /api/v1/iot-monitoring/sensor-readings
└── db.py                           # Peewee database handle + init_db()

tests/
├── unit/
│   ├── device_auth/                # Device verification, authenticator, hasher (mocked repo)
│   └── iot_ingestion/              # alert_policy, UTC normalization, ingest orchestration (mocked ports)
├── integration/                    # Real SQLite: auth flow, ingestion, buffering/retry, seeding
│   ├── conftest.py                 # Temp SQLite file fixture
│   ├── test_ingestion_endpoint.py
│   ├── test_auth_failures.py
│   ├── test_offline_buffering.py
│   └── test_seed_test_device.py
└── contract/
    └── test_sensor_readings_contract.py  # Request/response shape vs OpenAPI

requirements.txt
```

**Structure Decision**: Single-project layout organized **by bounded context** under `src/`,
with each context internally split into the four constitutional layers
(domain → application → infrastructure → interfaces). This makes the layer-import rule and the
cross-context-via-application rule statically obvious. Tests mirror the contexts and separate
unit (mocked) from integration (real SQLite) per Principle II.

## Complexity Tracking

> No constitutional violations to justify — Initial and Post-Design Constitution Checks both
> PASS. This section intentionally left empty.
