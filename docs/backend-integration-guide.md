# Backend Integration Guide — Receiving Edge Readings in `eduspace-platform`

How to implement, **inside the [`eduspace-platform`](https://github.com/DesarrolloSolucionIoT/eduspace-platform)
.NET backend**, the endpoint that receives sensor readings forwarded by the **EduSpace Edge API**.
The skeletons below follow the repository's existing Clean-Architecture + DDD conventions (verified
against `SpacesAndResourceManagement`), so the new code drops in alongside the other bounded contexts.

> **Stacks at a glance.** Edge = Python 3 / Flask / SQLite (this repo). Backend = .NET 8 / ASP.NET
> Core / EF Core 8 / MySQL (`eduspace-platform`). They talk over a single HTTP `POST`.

---

## 1. What the Edge API is and why it exists

The **EduSpace Edge API** runs *on the edge* — physically near the classrooms (a Raspberry Pi or
local gateway), not in the cloud. ESP32 devices in each classroom (`aula`) post temperature,
humidity, and occupancy readings to it. Its responsibilities:

1. **Ingest & validate** readings over HTTP, authenticating each device by an `X-API-Key`.
2. **Decide the alert LED state locally.** For every reading it computes `alert_led_state`
   (`1` = breach, `0` = normal) *on the edge* from per-zone thresholds, **without contacting the
   cloud** — so the classroom alert light keeps working during an internet outage.
3. **Persist locally, then forward to the cloud.** Each reading is written to local SQLite first,
   then forwarded asynchronously to this backend. If the backend is unreachable the reading is
   **buffered** locally and retried by a background worker until it succeeds.

### Why this matters for the backend

- **The device never waits for the cloud.** The edge returns `201` to the device as soon as the
  reading is stored locally; forwarding is a best-effort side effect. Backend latency/uptime do
  **not** affect classroom devices.
- **The backend is the system of record / analytics layer**, not the real-time control path. It
  stores readings for dashboards, history, and reporting.
- **Readings arrive out of order and in bursts.** After an outage the edge replays its buffer
  oldest-first, so you may receive older readings minutes or hours late. Design for it (§9).

### Data flow

```
┌──────────────┐  POST reading   ┌─────────────────────┐  POST forward    ┌────────────────────────┐
│ ESP32 device  │ ───────────────▶│   EduSpace Edge API  │ ────────────────▶│  eduspace-platform      │
│ (classroom)   │  X-API-Key      │  Flask + SQLite      │ best-effort+retry│  IoTMonitoring context  │
└──────────────┘ ◀─────────────── └─────────────────────┘                  │  (THIS guide)           │
                  201 + alert_led_state      │ buffers in SQLite when       └────────────────────────┘
                  (computed locally)         │ backend down; retries every N s
```

---

## 2. The integration point — exactly what the edge sends you

From the edge's [`UpstreamForwarder.forward`](../src/iot_ingestion/infrastructure/upstream_forwarder.py):

- **Method:** `POST`
- **URL:** the **full** value of the edge's `EDUSPACE_WEB_API_URL` env var, posted **as-is** (the
  edge does not append a path). The operator configures the complete URL of your endpoint there.
- **Headers:** `Content-Type: application/json`, plus **`X-Edge-Key: <secret>`** when the edge is
  configured with `EDUSPACE_FORWARD_AUTH` (empty by default → header omitted) — see §8.
- **Timeout:** the edge waits `EDUSPACE_FORWARD_TIMEOUT` seconds (default **5s**). Respond well
  inside it or the edge treats it as a failure and retries later.
- **Success = `2xx` only.** Any non-`2xx`, a timeout, or a connection error → the reading stays
  buffered and is retried. **Your response body is ignored** by the edge.

### 2.1 Request payload you must accept

```json
{
  "reading_id": 42,
  "device_id": "esp32-aula-101",
  "temperature": 31.5,
  "humidity": 70.0,
  "occupancy": true,
  "alert_led_state": 1,
  "recorded_at": "2026-06-06T14:30:00+00:00"
}
```

| Field             | JSON type        | Maps to (C#)        | Notes |
|-------------------|------------------|---------------------|-------|
| `reading_id`      | integer          | `int EdgeReadingId` | The reading's id **on that edge node**. Unique per edge, **not globally unique**. See §7. |
| `device_id`       | string           | `string DeviceId`   | Authenticated device id (e.g. `esp32-aula-101`). |
| `temperature`     | number           | `double Temperature`| °C. Edge already validated to `-40…85`. |
| `humidity`        | number           | `double Humidity`   | %. Edge already validated to `0…100`. |
| `occupancy`       | boolean          | `bool Occupancy`    | Room occupied or not. |
| `alert_led_state` | integer (`0`/`1`)| `int AlertLedState` | Edge's alert decision. **Authoritative — do not recompute.** |
| `recorded_at`     | string ISO 8601  | `DateTimeOffset`    | When the reading was taken, already UTC (`+00:00`). |

> JSON keys are **snake_case**; .NET defaults to camelCase. Bind explicitly with
> `[JsonPropertyName("reading_id")]` on the request resource (shown in §6.2) or configure the
> serializer — otherwise model binding silently leaves fields at their defaults.

---

## 3. Where this lives — a new `IoTMonitoring` bounded context

`eduspace-platform` has no IoT context yet, so add one mirroring `SpacesAndResourceManagement`. Target
file tree (all under `FULLSTACKFURY.EduSpace.API/`):

```
IoTMonitoring/
├── Domain/
│   ├── Model/
│   │   ├── Aggregates/   SensorReading.cs
│   │   ├── Commands/     CreateSensorReadingCommand.cs
│   │   ├── Queries/      GetSensorReadingsByDeviceIdQuery.cs
│   │   └── ValueObjects/ DeviceId.cs        (optional — can be a plain string column)
│   ├── Repositories/     ISensorReadingRepository.cs
│   └── Services/         ISensorReadingCommandService.cs, ISensorReadingQueryService.cs
├── Application/
│   └── Internal/
│       ├── CommandServices/  SensorReadingCommandService.cs
│       └── QueryServices/    SensorReadingQueryService.cs
├── Infrastructure/
│   └── Persistence/EFC/Repositories/  SensorReadingRepository.cs
└── Interfaces/
    └── REST/
        ├── SensorReadingsController.cs
        ├── Resources/    CreateSensorReadingResource.cs, SensorReadingResource.cs
        └── Transform/    CreateSensorReadingCommandFromResourceAssembler.cs,
                          SensorReadingResourceFromEntityAssembler.cs
```

Plus edits to two shared files: `Shared/.../Configuration/AppDbContext.cs` (entity config) and
`Program.cs` (DI registration).

---

## 4. Implementation checklist

- [ ] **Domain** — `SensorReading` aggregate, `CreateSensorReadingCommand`, repository + service interfaces (§5).
- [ ] **Application** — `SensorReadingCommandService` with idempotent create (§5.4, §7).
- [ ] **Infrastructure** — `SensorReadingRepository`, `AppDbContext` config with a **unique index** for idempotency, migration (§6.1).
- [ ] **Interfaces/REST** — controller + resources + assemblers; bind snake_case JSON; map to `2xx` (§6.2–6.4).
- [ ] **Auth** — the edge can't obtain a JWT; add an `X-Edge-Key` API-key header check, **not** `[Authorize]` (§8). *(Edge support is implemented — it sends `X-Edge-Key` when `EDUSPACE_FORWARD_AUTH` is set.)*
- [ ] **DI** — register repository + services in `Program.cs` (§6.5).
- [ ] **Idempotency** — return `2xx` for duplicates; never let a duplicate or a bad row trigger endless retries (§7).
- [ ] **Config & tests** (§10, §11).

---

## 5. Domain layer

### 5.1 Aggregate — `SensorReading.cs`

Follows the repo's aggregate style (EF parameterless ctor + command ctor + validation, mirroring
`Classroom`).

```csharp
using System.ComponentModel.DataAnnotations;
using FULLSTACKFURY.EduSpace.API.IoTMonitoring.Domain.Model.Commands;

namespace FULLSTACKFURY.EduSpace.API.IoTMonitoring.Domain.Model.Aggregates;

public partial class SensorReading
{
    public int Id { get; }                       // backend's own surrogate key
    public string DeviceId { get; private set; }
    public int EdgeReadingId { get; private set; } // the edge's "reading_id" (NOT globally unique)
    public double Temperature { get; private set; }
    public double Humidity { get; private set; }
    public bool Occupancy { get; private set; }
    public int AlertLedState { get; private set; } // 0 or 1, decided by the edge — stored as-is
    public DateTimeOffset RecordedAt { get; private set; } // when measured (UTC, from the edge)

    protected SensorReading() { DeviceId = string.Empty; } // EF Core

    public SensorReading(CreateSensorReadingCommand c)
    {
        DeviceId      = c.DeviceId;
        EdgeReadingId = c.EdgeReadingId;
        Temperature   = c.Temperature;
        Humidity      = c.Humidity;
        Occupancy     = c.Occupancy;
        AlertLedState = c.AlertLedState;
        RecordedAt    = c.RecordedAt;
        Validate();
    }

    private void Validate()
    {
        if (string.IsNullOrWhiteSpace(DeviceId))
            throw new ValidationException("device_id is required.");
        if (Temperature is < -40 or > 85)
            throw new ValidationException("temperature out of range (-40..85).");
        if (Humidity is < 0 or > 100)
            throw new ValidationException("humidity out of range (0..100).");
        if (AlertLedState is not (0 or 1))
            throw new ValidationException("alert_led_state must be 0 or 1.");
    }
}
```

> `received_at` (when the backend got it) is best handled by the repo's existing
> **`CreatedUpdatedInterceptor`** — add the `IEntityWithCreatedUpdatedDate` interface the other
> aggregates use so `CreatedDate` is stamped automatically. Keep `RecordedAt` separate from it (§9).

### 5.2 Command — `CreateSensorReadingCommand.cs`

```csharp
namespace FULLSTACKFURY.EduSpace.API.IoTMonitoring.Domain.Model.Commands;

public record CreateSensorReadingCommand(
    string DeviceId,
    int EdgeReadingId,
    double Temperature,
    double Humidity,
    bool Occupancy,
    int AlertLedState,
    DateTimeOffset RecordedAt);
```

### 5.3 Repository interface — `ISensorReadingRepository.cs`

```csharp
using FULLSTACKFURY.EduSpace.API.Shared.Domain.Repositories;
using FULLSTACKFURY.EduSpace.API.IoTMonitoring.Domain.Model.Aggregates;

namespace FULLSTACKFURY.EduSpace.API.IoTMonitoring.Domain.Repositories;

public interface ISensorReadingRepository : IBaseRepository<SensorReading>
{
    // Idempotency key: a reading is uniquely identified by its edge + edge-local id.
    Task<bool> ExistsByDeviceIdAndEdgeReadingIdAsync(string deviceId, int edgeReadingId);

    Task<IEnumerable<SensorReading>> FindByDeviceIdAsync(string deviceId);
}
```

### 5.4 Service interfaces — `Domain/Services/`

```csharp
// ISensorReadingCommandService.cs
public interface ISensorReadingCommandService
{
    Task<SensorReading?> Handle(CreateSensorReadingCommand command);
}

// ISensorReadingQueryService.cs
public interface ISensorReadingQueryService
{
    Task<IEnumerable<SensorReading>> Handle(GetSensorReadingsByDeviceIdQuery query);
}
```

---

## 6. Application, Infrastructure & Interfaces

### 6.1 Command service (idempotent) — `Application/Internal/CommandServices/`

Mirrors `ClassroomCommandService` (repository + `IUnitOfWork`, `CompleteAsync`). The
duplicate-check is what makes retries safe.

```csharp
public class SensorReadingCommandService(
    ISensorReadingRepository readingRepository,
    IUnitOfWork unitOfWork) : ISensorReadingCommandService
{
    public async Task<SensorReading?> Handle(CreateSensorReadingCommand command)
    {
        // Idempotency: the edge may re-deliver a reading we already stored.
        if (await readingRepository.ExistsByDeviceIdAndEdgeReadingIdAsync(
                command.DeviceId, command.EdgeReadingId))
            return null; // signal "duplicate" → controller still returns 2xx (§7)

        var reading = new SensorReading(command);
        await readingRepository.AddAsync(reading);
        await unitOfWork.CompleteAsync();
        return reading;
    }
}
```

### 6.2 Repository — `Infrastructure/Persistence/EFC/Repositories/`

```csharp
public class SensorReadingRepository(AppDbContext context)
    : BaseRepository<SensorReading>(context), ISensorReadingRepository
{
    public async Task<bool> ExistsByDeviceIdAndEdgeReadingIdAsync(string deviceId, int edgeReadingId) =>
        await Context.Set<SensorReading>()
            .AnyAsync(r => r.DeviceId == deviceId && r.EdgeReadingId == edgeReadingId);

    public async Task<IEnumerable<SensorReading>> FindByDeviceIdAsync(string deviceId) =>
        await Context.Set<SensorReading>()
            .AsNoTracking()
            .Where(r => r.DeviceId == deviceId)
            .OrderBy(r => r.RecordedAt)
            .ToListAsync();
}
```

### 6.3 `AppDbContext` entity config + **unique index** (idempotency at the DB level)

Add to `OnModelCreating` in `Shared/.../Configuration/AppDbContext.cs`, alongside the other contexts'
blocks (snake_case is already applied globally by the existing convention):

```csharp
// IoT Monitoring Context
builder.Entity<SensorReading>().HasKey(r => r.Id);
builder.Entity<SensorReading>().Property(r => r.Id).IsRequired().ValueGeneratedOnAdd();
builder.Entity<SensorReading>().Property(r => r.DeviceId).IsRequired().HasMaxLength(64);
builder.Entity<SensorReading>().Property(r => r.EdgeReadingId).IsRequired();
builder.Entity<SensorReading>().Property(r => r.Temperature).IsRequired();
builder.Entity<SensorReading>().Property(r => r.Humidity).IsRequired();
builder.Entity<SensorReading>().Property(r => r.Occupancy).IsRequired();
builder.Entity<SensorReading>().Property(r => r.AlertLedState).IsRequired();
builder.Entity<SensorReading>().Property(r => r.RecordedAt).IsRequired();

// Idempotency: one row per (device, edge reading id). Backs ExistsBy... and blocks duplicates.
builder.Entity<SensorReading>()
    .HasIndex(r => new { r.DeviceId, r.EdgeReadingId })
    .IsUnique();
```

Then generate the migration (it auto-applies on startup, per the repo's existing behavior):

```bash
dotnet ef migrations add AddSensorReadings
```

### 6.4 REST resources + assemblers — `Interfaces/REST/`

```csharp
// Resources/CreateSensorReadingResource.cs  — binds the edge's snake_case body
using System.Text.Json.Serialization;

public record CreateSensorReadingResource(
    [property: JsonPropertyName("reading_id")]       int ReadingId,
    [property: JsonPropertyName("device_id")]        string DeviceId,
    [property: JsonPropertyName("temperature")]      double Temperature,
    [property: JsonPropertyName("humidity")]         double Humidity,
    [property: JsonPropertyName("occupancy")]        bool Occupancy,
    [property: JsonPropertyName("alert_led_state")]  int AlertLedState,
    [property: JsonPropertyName("recorded_at")]      DateTimeOffset RecordedAt);

// Resources/SensorReadingResource.cs  — backend's view of a stored reading
public record SensorReadingResource(
    int Id, string DeviceId, int EdgeReadingId, double Temperature,
    double Humidity, bool Occupancy, int AlertLedState, DateTimeOffset RecordedAt);

// Transform/CreateSensorReadingCommandFromResourceAssembler.cs
public static class CreateSensorReadingCommandFromResourceAssembler
{
    public static CreateSensorReadingCommand ToCommandFromResource(CreateSensorReadingResource r) =>
        new(r.DeviceId, r.ReadingId, r.Temperature, r.Humidity, r.Occupancy, r.AlertLedState, r.RecordedAt);
}

// Transform/SensorReadingResourceFromEntityAssembler.cs
public static class SensorReadingResourceFromEntityAssembler
{
    public static SensorReadingResource ToResourceFromEntity(SensorReading e) =>
        new(e.Id, e.DeviceId, e.EdgeReadingId, e.Temperature, e.Humidity, e.Occupancy, e.AlertLedState, e.RecordedAt);
}
```

### 6.5 Controller — `Interfaces/REST/SensorReadingsController.cs`

Same shape as `ResourceController` (`[ApiController]`, `[Route("api/v1/[...]")]`,
`[Produces(...)]`, `[Tags(...)]`, constructor-injected command + query services) — **except** the
ingestion endpoint is **not** `[Authorize]` (the edge has no JWT; it uses an API key — §8).

```csharp
using System.Net.Mime;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace FULLSTACKFURY.EduSpace.API.IoTMonitoring.Interfaces.REST;

[ApiController]
[Route("api/v1/iot-monitoring/sensor-readings")]
[Produces(MediaTypeNames.Application.Json)]
[Tags("IoT Monitoring")]
public class SensorReadingsController(
    ISensorReadingCommandService commandService,
    ISensorReadingQueryService queryService) : ControllerBase
{
    // Edge → backend. Authenticated by API key (see §8), NOT JWT.
    [AllowAnonymous]
    [ServiceFilter(typeof(EdgeApiKeyFilter))]   // §8
    [HttpPost]
    public async Task<IActionResult> IngestReading([FromBody] CreateSensorReadingResource resource)
    {
        var command = CreateSensorReadingCommandFromResourceAssembler.ToCommandFromResource(resource);
        var reading = await commandService.Handle(command);

        // Duplicate (idempotent replay) → still 2xx so the edge stops retrying (§7).
        if (reading is null) return Ok(new { status = "duplicate" });

        var body = SensorReadingResourceFromEntityAssembler.ToResourceFromEntity(reading);
        return StatusCode(StatusCodes.Status201Created, body);
    }

    // Backend UI → readings. This one IS user-facing, so require JWT.
    [Authorize]
    [HttpGet("by-device/{deviceId}")]
    public async Task<IActionResult> GetByDevice(string deviceId)
    {
        var readings = await queryService.Handle(new GetSensorReadingsByDeviceIdQuery(deviceId));
        return Ok(readings.Select(SensorReadingResourceFromEntityAssembler.ToResourceFromEntity));
    }
}
```

### 6.6 DI registration — `Program.cs`

Add next to the other `AddScoped` blocks:

```csharp
// IoT Monitoring Bounded Context
builder.Services.AddScoped<ISensorReadingRepository, SensorReadingRepository>();
builder.Services.AddScoped<ISensorReadingCommandService, SensorReadingCommandService>();
builder.Services.AddScoped<ISensorReadingQueryService, SensorReadingQueryService>();
builder.Services.AddScoped<EdgeApiKeyFilter>();   // §8
```

---

## 7. Idempotency & the edge's retry behavior (read this twice)

The edge's retry worker can deliver the **same reading more than once** (e.g. your `2xx` was lost in
transit, so the edge believes it failed and retries). You **must** de-duplicate, because
`reading_id` is **only unique within one edge node** — two classrooms both produce `reading_id = 1`.

- **Idempotency key:** `(device_id, edge_reading_id)`. Enforced two ways: the **unique index** (§6.3)
  and the **`ExistsBy...` pre-check** (§6.1). The index is the real guard; the pre-check just avoids
  a noisy exception on the common case.
- **Return `2xx` for duplicates** (§6.5). Returning an error would make the edge retry that reading
  **forever**.

> ⚠️ **The edge retries *any* non-`2xx` indefinitely** and does **not** distinguish permanent (4xx)
> from transient (5xx) failures
> ([`upstream_forwarder.py`](../src/iot_ingestion/infrastructure/upstream_forwarder.py#L28)). So a
> reading you reject with `400`/`401` is re-sent every retry interval and never drains from the edge
> buffer. Therefore:
> - During integration, prefer to **accept-and-quarantine** a questionable payload (store it, return
>   `2xx`) over `400`, so one bad reading can't clog the buffer.
> - True reject-and-drop semantics require a change on the **edge** side. Coordinate before relying on it.

---

## 8. Authentication (edge → backend)

The edge **cannot obtain a JWT** (it's an unattended device gateway, not a logged-in user), so the
ingestion endpoint must **not** use the platform's `[Authorize]` JWT filter. Instead it authenticates
with a shared-secret header: **the edge sends `X-Edge-Key: <secret>` whenever its
`EDUSPACE_FORWARD_AUTH` env var is set** (implemented in
[`upstream_forwarder.py`](../src/iot_ingestion/infrastructure/upstream_forwarder.py)). The backend
must validate that header:

1. **Add a shared-secret header check.** Define an action filter, e.g. `EdgeApiKeyFilter`, that
   compares a request header (`X-Edge-Key`) against a configured secret and returns `401` if it
   doesn't match. Apply it only to the ingestion action (§6.5), keeping the endpoint `[AllowAnonymous]`
   for JWT purposes.

   ```csharp
   public class EdgeApiKeyFilter(IConfiguration config) : IActionFilter
   {
       public void OnActionExecuting(ActionExecutingContext ctx)
       {
           var expected = config["Edge:ApiKey"];
           var provided = ctx.HttpContext.Request.Headers["X-Edge-Key"].FirstOrDefault();
           if (string.IsNullOrEmpty(expected) || provided != expected)
               ctx.Result = new UnauthorizedResult();
       }
       public void OnActionExecuted(ActionExecutedContext ctx) { }
   }
   ```

2. **Agree on the secret on both sides.** Set `EDUSPACE_FORWARD_AUTH` on the **edge** and the
   matching `Edge:ApiKey` on the **backend** to the same value. The header name is fixed as
   `X-Edge-Key` (`EDGE_AUTH_HEADER` in
   [`upstream_forwarder.py`](../src/iot_ingestion/infrastructure/upstream_forwarder.py)).
   > ⚠️ **Don't enable the backend filter before the edge has the secret set.** If the filter is on
   > but the edge's `EDUSPACE_FORWARD_AUTH` is empty, the edge sends no header → `401` → and per §7 it
   > **retries that reading forever**. Roll out the edge secret first, then turn on the filter.

   Network-level hardening (reverse-proxy IP allow-list / VPN / mTLS) is still recommended in addition
   to the shared secret.

> Note: `device_id` arrives in the body but is **not** an auth credential — the edge already
> authenticated the device. Don't treat the body `device_id` as proof of identity.

---

## 9. Data modeling notes

- **Store `RecordedAt` and `received_at` separately.** `RecordedAt` is when the measurement happened
  (from the edge); `received_at`/`CreatedDate` is when the backend ingested it. After an outage these
  diverge a lot — a rising gap is your "an edge just reconnected" signal.
- **Keep `AlertLedState` exactly as received.** The edge owns alerting (per-zone thresholds your
  backend doesn't have). Don't recompute it.
- **Expect out-of-order / bursty inserts.** Order time-series queries by `RecordedAt`, and make any
  "latest reading per device" logic tolerant of late arrivals.

---

## 10. Configuration the two sides must agree on

Set on the **edge** (see [edge README](../README.md)); agree on URL + secret with the backend team:

| Edge env var               | Meaning for the integration                                        |
|----------------------------|--------------------------------------------------------------------|
| `EDUSPACE_WEB_API_URL`     | **Full URL** of your controller, e.g. `https://api.eduspace…/api/v1/iot-monitoring/sensor-readings`. Empty = forwarding off. |
| `EDUSPACE_FORWARD_TIMEOUT` | Seconds the edge waits for your `2xx` (default `5`). Stay under it. |
| `EDUSPACE_RETRY_INTERVAL`  | Seconds between buffer-drain retries (default `30`).               |
| `EDUSPACE_FORWARD_AUTH`    | Secret sent as the `X-Edge-Key` header (§8). Empty = no header. Must match the backend's `Edge:ApiKey`. |

On the **backend**, add `Edge:ApiKey` to configuration (`.env` / `appsettings`) matching that secret.

Example edge launch pointed at a locally-running backend:

```powershell
$env:EDUSPACE_ENV = "development"
$env:EDUSPACE_WEB_API_URL = "http://localhost:5xxx/api/v1/iot-monitoring/sensor-readings"
$env:EDUSPACE_RETRY_INTERVAL = "10"
flask --app src.app run
```

---

## 11. Integration test checklist

- [ ] Edge `EDUSPACE_WEB_API_URL` → backend; submit a reading on the edge → row appears in MySQL with
      matching `RecordedAt` and `AlertLedState`; edge returns `201` to the device.
- [ ] Re-deliver the same `(device_id, reading_id)` → exactly **one** row; backend returns `2xx`
      (`status: duplicate`); unique index holds.
- [ ] Stop the backend, submit 3 readings (each still `201` to the device) → start the backend → after
      one `EDUSPACE_RETRY_INTERVAL` all 3 appear in MySQL.
- [ ] Backend slower than `EDUSPACE_FORWARD_TIMEOUT` → edge buffers and retries; no data loss.
- [ ] (After §8) Wrong/missing `X-Edge-Key` → `401`; confirm behavior and remember the retry-forever
      caveat (§7) before enabling rejection in production.

---

### Appendix — conventions this guide mirrors (from `eduspace-platform`)

Aggregate (EF ctor + command ctor + `Validate()`), `record` commands/queries, `IXRepository :
IBaseRepository<T>` with `ExistsBy…`, `XRepository(AppDbContext) : BaseRepository<T>`, command
services taking the repository + `IUnitOfWork` and calling `CompleteAsync()`, controllers with
`[ApiController]` / `[Route("api/v1/…")]` / `[Produces]` / `[Tags]` + assemblers
(`…CommandFromResourceAssembler`, `…ResourceFromEntityAssembler`), `AppDbContext` with global
snake_case + `CreatedUpdatedInterceptor`, and per-context `AddScoped` blocks in `Program.cs`.
```
