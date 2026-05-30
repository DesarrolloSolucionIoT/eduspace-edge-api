# Quickstart: Classroom Sensor Ingestion & Local Alerting

Get the EduSpace edge service running locally and submit your first reading using the
auto-provisioned development test device — zero manual setup.

## Prerequisites

- Python 3.13
- A POSIX or Windows shell

## 1. Install dependencies

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS:        source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` pins: `Flask`, `Peewee`, `python-dateutil`, `requests` (plus `pytest` for
the test suite).

## 2. Configure environment

| Variable               | Purpose                                          | Example                                |
|------------------------|--------------------------------------------------|----------------------------------------|
| `EDUSPACE_WEB_API_URL` | Upstream cloud Web API base URL for forwarding   | `https://api.eduspace.example/ingest`  |
| `EDUSPACE_DB_PATH`     | SQLite file path (durable, not in-memory)        | `./eduspace-edge.db`                    |
| `EDUSPACE_ENV`         | `development` enables test-device seeding        | `development`                          |
| `EDUSPACE_FORWARD_TIMEOUT` | Upstream request timeout (seconds)           | `5`                                    |

```bash
# PowerShell
$env:EDUSPACE_WEB_API_URL = "https://api.eduspace.example/ingest"
$env:EDUSPACE_ENV = "development"
```

## 3. Run the service

```bash
flask --app src.app run
```

On the first request, the `before_request` bootstrap creates the SQLite tables and seeds the
development test device if absent:

- **device_id**: `esp32-aula-101`
- **api_key**: `test-api-key-edu`

## 4. Submit a reading

```bash
curl -X POST http://localhost:5000/api/v1/iot-monitoring/sensor-readings \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-api-key-edu" \
  -d '{
        "device_id": "esp32-aula-101",
        "temperature": 31.5,
        "humidity": 70.0,
        "occupancy": true,
        "recorded_at": "2026-05-30T14:03:22-05:00"
      }'
```

Expected `201`:

```json
{
  "reading_id": 1,
  "alert_led_state": 1,
  "recorded_at": "2026-05-30T19:03:22+00:00"
}
```

(`recorded_at` is normalized to UTC; `alert_led_state` is `1` here assuming the zone's
configured bounds are exceeded.)

## 5. Verify the core guarantees

- **Local alerting works offline**: stop/blackhole the upstream (`EDUSPACE_WEB_API_URL`
  unreachable) and submit again — you still get an immediate `201` with a correct
  `alert_led_state`. The row persists with `forwarded_at = NULL`.
- **Buffering & retry**: restore upstream; the background retry task forwards rows where
  `forwarded_at IS NULL` and stamps `forwarded_at`.
- **Auth failures (401)**: omit `X-API-Key`, or use a wrong key, or an unknown `device_id` —
  each returns the same generic `{"code": "AUTH_FAILED", ...}`.
- **Validation errors (400)**: send `humidity: 150` or omit `temperature` — returns
  `{"code": "VALIDATION_ERROR", ...}` and stores nothing.
- **Durability**: restart the process — previously buffered readings remain in the SQLite
  file.

## 6. Run the tests

```bash
pytest                      # full suite
pytest tests/unit           # pure domain/application (mocked collaborators)
pytest tests/integration    # real SQLite file (per Constitution Principle II)
```

Tests are written **first** and must fail before implementation (Constitution Principle II).
Coverage includes happy path, auth failures, validation errors, and upstream-forwarding
failure/retry.
