# Phase 0 Research: Classroom Sensor Ingestion & Local Alerting

All Technical Context items were supplied concretely by the user; there were no open
`NEEDS CLARIFICATION` markers. The items below record the decisions, the rationale, and the
alternatives considered — including two design questions that the spec raised but the
technical input did not fully pin down (threshold source and 503 mapping).

## 1. Web framework

- **Decision**: Flask.
- **Rationale**: Minimal, well-understood, low overhead for a single-endpoint edge service;
  `before_request` hook cleanly hosts the one-time DB-init + test-device seeding bootstrap and
  per-request auth middleware.
- **Alternatives considered**: FastAPI (more built-in validation/async, but heavier and
  unnecessary for one synchronous endpoint); raw WSGI (too low-level).

## 2. Persistence (ORM + SQLite)

- **Decision**: Peewee ORM over a local SQLite **file**.
- **Rationale**: File-backed SQLite makes buffered readings durable across restarts (FR-008,
  FR-010). Peewee is lightweight and ergonomic for two tables. All Peewee access is confined
  to infrastructure repositories (Principle I & III).
- **Alternatives considered**: In-memory SQLite (rejected — loses buffered readings on
  restart); SQLAlchemy (heavier than needed); raw `sqlite3` (more boilerplate, weaker model
  ergonomics).

## 3. Timestamp normalization to UTC

- **Decision**: Parse the optional `recorded_at` ISO 8601 string with python-dateutil; if
  absent, stamp with the injected UTC clock at ingestion. Convert any timezone-aware value to
  UTC; treat naive timestamps as UTC. Persist as UTC ISO 8601.
- **Rationale**: Satisfies Principle IV (UTC before persistence) and FR-012. python-dateutil
  robustly handles offset and zone-bearing strings.
- **Alternatives considered**: `datetime.fromisoformat` (narrower parsing in older versions);
  rejecting non-UTC input (rejected — devices may send local time/offset).

## 4. Stateless authentication & key storage

- **Decision**: Per-request `X-API-Key` header validated against the body `device_id`. Keys
  are stored only as **salted hashes** (`api_key_hash`); validation hashes the presented key
  and compares. No session state.
- **Rationale**: Principle IV (stateless) and spec clarifications Q4/Q5. A single generic
  401 is returned for missing/unknown/invalid cases to prevent device-identifier enumeration;
  the specific reason is logged server-side.
- **Alternatives considered**: Plaintext key comparison (rejected — leak risk); session
  tokens/JWT (rejected — introduces state, unnecessary for fixed-schedule devices).

## 5. Threshold source (design question raised by spec, not fixed by tech input)

- **Decision**: Per-zone environmental thresholds are provided via **application
  configuration keyed by `zone_id`**, not persisted in SQLite for this iteration. The
  `device_auth` context resolves the authenticated device's `zone_id` and attaches the
  resolved `ZoneThresholds` to the request context; `iot_ingestion` reads thresholds from that
  context only (never from `device_auth`'s domain).
- **Rationale**: The user's schema defines only `devices` and `sensor_readings` tables (no
  threshold table) and states "thresholds are passed in the request context from
  `device_auth`." Config-driven thresholds match that and keep the cross-context dependency at
  the application layer (Principle I). Empty/unknown-zone thresholds yield an inactive alert
  (spec assumption / edge case), never an error.
- **Alternatives considered**: A `zones` table in SQLite (more flexible, deferred — out of
  scope for the two-table schema given); hard-coded global thresholds (rejected — spec
  requires per-zone configuration).

## 6. Alert evaluation (local, synchronous)

- **Decision**: A pure `alert_policy` function returns `1` if temperature or humidity breaches
  the zone's configured bound (upper or lower), else `0`. Occupancy is recorded but never
  affects the decision (spec clarification Q1). Computed in-process with no I/O.
- **Rationale**: Principle IV (local, upstream-independent) and FR-005/FR-006. Pure function
  is trivially unit-testable.
- **Alternatives considered**: Threshold evaluation in the route handler (rejected — leaks
  domain logic into the interface layer).

## 7. Upstream forwarding & retry

- **Decision**: After persisting, attempt a synchronous-from-the-handler best-effort forward
  via a `requests` client with a configurable timeout to `EDUSPACE_WEB_API_URL`, carrying the
  reading's stable `id` for dedup (FR-011a). On success, set `forwarded_at`; on any failure,
  log it and leave `forwarded_at = NULL`. A background retry task periodically re-forwards
  readings where `forwarded_at IS NULL`. Forwarding failure NEVER changes the device response.
- **Rationale**: Principle IV (buffering) and V (failures logged + queued, never 5xx to
  device); FR-009, FR-010, FR-011.
- **Alternatives considered**: Fully synchronous forward blocking the response (rejected —
  violates "never wait on cloud"); external message queue (rejected — over-engineered for the
  edge; SQLite buffer suffices).

## 8. HTTP error mapping (including the 503 question)

- **Decision**: 400 for validation errors (missing/malformed/out-of-range fields), 401
  (single generic code) for all authentication failures. **503 is not emitted on this
  endpoint** because forwarding is asynchronous — upstream unavailability does not block or
  fail the device request. 503 remains reserved by the constitution for any future
  synchronous upstream dependency on a request path.
- **Rationale**: Reconciles Constitution Principle V (which lists 503 for upstream
  unavailability) with the design's asynchronous forwarding (which intentionally shields the
  device from upstream state). Documented explicitly to avoid a false "missing 503" finding.
- **Alternatives considered**: Returning 503 when upstream is down at request time (rejected —
  would violate "device never waits on cloud" and FR-011's "never 5xx for forwarding").

## 9. Application bootstrap

- **Decision**: Flask app factory; a `before_request` hook initializes the SQLite database
  (creates tables if absent) and seeds the dev test device (`esp32-aula-101` /
  `test-api-key-edu`) exactly once when running in development mode, idempotently.
- **Rationale**: Matches user input and FR-014; idempotent seeding avoids duplicates on
  restart. Seeding is gated to the development context so production is unaffected.
- **Alternatives considered**: Seeding at import time (rejected — harder to control per
  environment and in tests).

## 10. Dependencies

- **Decision**: `Flask`, `Peewee`, `python-dateutil`, `requests`, plus `pytest` for tests, all
  declared in `requirements.txt`.
- **Rationale**: Exactly the stack specified; no extras pulled into business logic
  (dependencies injected per Principle III).
