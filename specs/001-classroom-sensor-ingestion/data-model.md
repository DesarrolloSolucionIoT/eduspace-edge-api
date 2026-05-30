# Phase 1 Data Model: Classroom Sensor Ingestion & Local Alerting

Two persisted tables (SQLite, via Peewee) plus one in-memory value object resolved from
configuration. Domain entities are pure (no Peewee imports); Peewee models live in each
context's infrastructure layer and map to/from the domain.

## Table: `devices` (context: device_auth)

| Column         | Type      | Constraints                          | Notes                                              |
|----------------|-----------|--------------------------------------|----------------------------------------------------|
| `device_id`    | TEXT      | PRIMARY KEY                          | Natural identifier sent by the device + body field |
| `api_key_hash` | TEXT      | NOT NULL                             | Salted hash of the secret API key (never plaintext)|
| `zone_id`      | TEXT      | NOT NULL                             | Classroom zone; used to resolve thresholds         |
| `created_at`   | TIMESTAMP | NOT NULL, default UTC now            | UTC                                                |

**Domain entity — `Device`** (pure):
- `device_id: str`, `api_key_hash: str`, `zone_id: str`, `created_at: datetime`
- `verify_key(presented_key: str, hasher: Hasher) -> bool` — compares salted hash; pure given
  an injected hasher.

**Rules**:
- `device_id` is unique (primary key).
- Authentication requires a matching `device_id` **and** a presented `X-API-Key` whose hash
  equals `api_key_hash`. Any mismatch → generic auth failure (FR-003, FR-003a, FR-003b).

## Table: `sensor_readings` (context: iot_ingestion)

| Column            | Type      | Constraints                       | Notes                                                       |
|-------------------|-----------|-----------------------------------|-------------------------------------------------------------|
| `id`              | INTEGER   | PRIMARY KEY AUTOINCREMENT         | Stable unique reading ID; returned as `reading_id`; sent upstream for dedup (FR-011a) |
| `device_id`       | TEXT      | NOT NULL, FK → devices.device_id  | Submitting device                                           |
| `temperature`     | REAL      | NOT NULL                          | Degrees Celsius                                             |
| `humidity`        | REAL      | NOT NULL                          | Relative humidity %                                         |
| `occupancy`       | INTEGER   | NOT NULL (0/1)                    | Boolean; contextual only — never affects alert (Q1)        |
| `alert_led_state` | INTEGER   | NOT NULL (0/1)                    | Locally computed; 1 if any threshold breached              |
| `recorded_at`     | TIMESTAMP | NOT NULL                          | UTC-normalized (FR-012)                                     |
| `forwarded_at`    | TIMESTAMP | NULLABLE                          | NULL = buffered/awaiting forward; set on successful forward |

**Domain entity — `SensorReading`** (pure):
- `temperature: float`, `humidity: float`, `occupancy: bool`, `recorded_at: datetime` (UTC)
- Plus persistence-assigned `id`, `device_id`, `alert_led_state`, `forwarded_at` populated
  through the application/infrastructure layers.

**Validation rules** (400 on failure — FR-004):
- `device_id`: non-empty string, present in body, matches authenticated device.
- `temperature`: float, finite, within plausible range (e.g., −40.0 to 85.0 °C).
- `humidity`: float, finite, 0.0–100.0 %.
- `occupancy`: boolean.
- `recorded_at`: optional; if present, a parseable ISO 8601 timestamp.

**State transitions** (`forwarded_at`):
```
[accepted: forwarded_at = NULL]  --forward succeeds-->  [forwarded: forwarded_at = <UTC ts>]
        ^                                                        
        |---- forward fails: stays NULL, logged, retried by background task ----|
```
Once `forwarded_at` is set it is terminal; the retry task only selects rows where
`forwarded_at IS NULL`.

## Value object — `ZoneThresholds` (in-memory, config-sourced; context: iot_ingestion)

Resolved by `device_auth` from the device's `zone_id` against application configuration and
attached to the request context (see research §5). Not persisted in this iteration.

| Field          | Type            | Notes                                            |
|----------------|-----------------|--------------------------------------------------|
| `temp_min`     | float \| None   | Lower temperature bound (optional)               |
| `temp_max`     | float \| None   | Upper temperature bound (optional)               |
| `humidity_min` | float \| None   | Lower humidity bound (optional)                  |
| `humidity_max` | float \| None   | Upper humidity bound (optional)                  |

**Rules**:
- A breach is any value below a configured `*_min` or above a configured `*_max`.
- A zone with no configured thresholds → no breach → `alert_led_state = 0` (spec assumption).

## Relationships

- `Device 1 ──< sensor_readings` via `device_id` (one device has many readings).
- `Device.zone_id ──> ZoneThresholds` resolved via configuration (not a foreign key).

## Entity → spec traceability

| Spec entity (FR/Key Entities) | This model |
|-------------------------------|------------|
| Device | `devices` table + `Device` entity |
| Classroom Zone (thresholds) | `ZoneThresholds` value object (config-sourced, keyed by `zone_id`) |
| Sensor Reading | `sensor_readings` table + `SensorReading` entity |
| Alert Evaluation Result | `alert_led_state` column + `alert_policy` output |
| Forwarding Queue Entry | `sensor_readings` rows with `forwarded_at IS NULL` |
