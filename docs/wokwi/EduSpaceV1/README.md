# EduSpace V1 — Wokwi ↔ Edge API

This Wokwi project posts real DHT22 + PIR readings to the EduSpace edge API and drives the
RGB LED from the API's authoritative `alert_led_state` response (not a local decision).

## What the firmware does

1. Connects to the Wokwi virtual WiFi (`Wokwi-GUEST`).
2. Every 5 s reads temperature, humidity, and occupancy.
3. `POST`s to `/api/v1/iot-monitoring/sensor-readings` with header `X-API-Key`.
4. Parses the `201` response and sets the LED: **red = alert (1)**, **green = normal (0)**,
   **blue = transmitting**, **magenta = API unreachable**.

The payload matches the OpenAPI contract:

```json
{ "device_id": "esp32-aula-101", "temperature": 23.4, "humidity": 48.2, "occupancy": true }
```

`recorded_at` is intentionally omitted — the edge service stamps server UTC time.

## 1. Start the edge API on your machine

```powershell
$env:EDUSPACE_ENV = "development"   # seeds the test device esp32-aula-101 / test-api-key-edu
flask --app src.app run --host 0.0.0.0
```

Use `--host 0.0.0.0` so the tunnel/gateway can reach Flask. It listens on port `5000`.

## 2. Let the simulated ESP32 reach your server

A simulated ESP32 **cannot reach `localhost` directly**. Pick the path that matches how you run
the simulation, then set the matching constants at the top of `sketch.ino`.

### A) Free wokwi.com web simulator → use a Cloudflare quick tunnel (required)

The free web simulator has no access to your machine, but it *does* have outbound internet.
Expose Flask publicly with a tunnel and point the firmware at it.

> ⚠️ **Use cloudflared, not ngrok.** Verified 2026-06: Wokwi's public gateway can open TLS
> to most hosts (`example.com` OK) but ngrok's edge refuses its connections — every request
> fails with `HTTP -1 connection refused` even though the same URL works from a browser.
> Cloudflare quick tunnels work fine.

```powershell
winget install Cloudflare.cloudflared    # once
cloudflared tunnel --url http://localhost:5000
# banner prints e.g. https://random-words-here.trycloudflare.com
```

Then in `sketch.ino` (in the Wokwi **browser editor** — editing the local file alone does
nothing for the web sim):

```cpp
const bool  USE_TLS  = true;
const char* API_HOST = "random-words-here.trycloudflare.com";  // no https://
const int   API_PORT = 443;
```

The trycloudflare subdomain rotates on every cloudflared restart — update `API_HOST` each
session. The sketch prints a `[TLS test] <host>:443 ... OK/FAILED` line at boot so a stale
host is obvious immediately.

Smoke-test the tunnel before running the sim:

```powershell
$body = @{ device_id="esp32-aula-101"; temperature=24; humidity=40; occupancy=$false } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri "https://random-words-here.trycloudflare.com/api/v1/iot-monitoring/sensor-readings" `
  -Headers @{ "X-API-Key"="test-api-key-edu" } `
  -ContentType "application/json" -Body $body
# expect: alert_led_state / reading_id / recorded_at
```

### B) Wokwi VS Code extension, or wokwi.com + Wokwi Club → Private Gateway

`host.wokwi.internal` routes to your machine through the Wokwi Private IoT Gateway. This is
**bundled in the VS Code extension**; on wokwi.com it needs a paid **Wokwi Club** plan plus the
local `wokwigw` app. Then:

```cpp
const bool  USE_TLS  = false;
const char* API_HOST = "host.wokwi.internal";
const int   API_PORT = 5000;
```

## 3. Run and observe

- Serial monitor prints each reading, the `POST` status, and the parsed
  `reading_id` / `alert_led_state` / `recorded_at`.
- Raise the DHT22 temperature/humidity in the simulation above the zone thresholds → the API
  returns `alert_led_state: 1` and the LED turns **red**.
- Stop Flask → the LED flashes **magenta** (the device still runs; the API is just unreachable).

## Config (top of `sketch.ino`)

| Constant     | Web sim (cloudflared tunnel)     | VS Code / Club gateway   | Notes                       |
|--------------|----------------------------------|--------------------------|-----------------------------|
| `USE_TLS`    | `true`                           | `false`                  | https tunnel vs plain http  |
| `API_HOST`   | `*.trycloudflare.com` (no scheme)| `host.wokwi.internal`    | ngrok does NOT work (see A) |
| `API_PORT`   | `443`                            | `5000`                   |                             |
| `DEVICE_ID`  | `esp32-aula-101`                 | `esp32-aula-101`         | Auto-seeded dev test device |
| `API_KEY`    | `test-api-key-edu`               | `test-api-key-edu`       | Sent as `X-API-Key`         |
