<!-- SPECKIT START -->
## Active Feature: Classroom Sensor Ingestion & Local Alerting (`001-classroom-sensor-ingestion`)

Implementation plan: [specs/001-classroom-sensor-ingestion/plan.md](specs/001-classroom-sensor-ingestion/plan.md)

- **Stack**: Python 3.13, Flask, Peewee + SQLite (local file), python-dateutil, requests; pytest for tests. Deps in `requirements.txt`.
- **Architecture**: two bounded contexts — `device_auth` (stateless `X-API-Key` validation, salted-hash key storage, dev test-device seeding) and `iot_ingestion` (validation, UTC normalization, local alert evaluation, persistence, async upstream forwarding + background retry). Each context split into domain/application/infrastructure/interfaces per the constitution.
- **Endpoint**: `POST /api/v1/iot-monitoring/sensor-readings` → `201 {reading_id, alert_led_state, recorded_at}`; `400` validation, `401` generic auth.
- **Key rules**: domain never imports infrastructure/interfaces; cross-context only via application layer; `alert_led_state` computed locally (no upstream dependency); readings buffered in SQLite (`forwarded_at IS NULL`) when upstream is down — forwarding failures never produce a 5xx to the device.
- Design artifacts: [research.md](specs/001-classroom-sensor-ingestion/research.md), [data-model.md](specs/001-classroom-sensor-ingestion/data-model.md), [contracts/](specs/001-classroom-sensor-ingestion/contracts/), [quickstart.md](specs/001-classroom-sensor-ingestion/quickstart.md). Governing principles: [.specify/memory/constitution.md](.specify/memory/constitution.md).
<!-- SPECKIT END -->
