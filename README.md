# EduSpace Edge API

An IoT edge service that ingests classroom sensor readings, computes an alert-LED decision
**locally**, persists readings to a local SQLite file, and forwards them asynchronously to the
EduSpace cloud — buffering during outages. See
[specs/001-classroom-sensor-ingestion/](specs/001-classroom-sensor-ingestion/) for the spec,
plan, and tasks, and [.specify/memory/constitution.md](.specify/memory/constitution.md) for the
governing principles.

## Architecture

Two bounded contexts, each split into domain / application / infrastructure / interfaces:

- **`device_auth`** — stateless `X-API-Key` validation, salted-hash key storage, dev test-device seeding.
- **`iot_ingestion`** — validation, UTC normalization, local alert evaluation, persistence, async forwarding + background retry.

`ZoneThresholds` lives in `src/shared/` (shared kernel) so the contexts never import each
other's domain.

## Requirements

- Python 3.12+ (plan target: 3.13)

## Install

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1   |  Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration (environment variables)

| Variable                   | Purpose                                      | Default            |
|----------------------------|----------------------------------------------|--------------------|
| `EDUSPACE_DB_PATH`         | SQLite file path (durable, not in-memory)    | `eduspace-edge.db` |
| `EDUSPACE_WEB_API_URL`     | Upstream cloud Web API URL for forwarding    | _(empty)_          |
| `EDUSPACE_FORWARD_TIMEOUT` | Upstream request timeout (seconds)           | `5`                |
| `EDUSPACE_ENV`             | `development` enables test-device seeding    | `production`       |
| `EDUSPACE_RETRY_INTERVAL`  | Background retry interval (seconds; 0=off)   | `30`               |

## Run

```bash
flask --app src.app run
```

In `development`, the first request seeds a test device — **device_id** `esp32-aula-101`,
**api_key** `test-api-key-edu` (zone `aula-101`).

```bash
curl -X POST http://localhost:5000/api/v1/iot-monitoring/sensor-readings \
  -H "Content-Type: application/json" -H "X-API-Key: test-api-key-edu" \
  -d '{"device_id":"esp32-aula-101","temperature":31.5,"humidity":70.0,"occupancy":true}'
# -> 201 {"reading_id":1,"alert_led_state":1,"recorded_at":"...+00:00"}
```

## Test

```bash
pytest                    # full suite
pytest tests/unit         # pure domain/application (mocked collaborators)
pytest tests/integration  # real SQLite file
pytest tests/contract     # response/contract conformance
```
