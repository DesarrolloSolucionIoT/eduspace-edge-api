#include <ArduinoJson.h>
#include <DHT.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

// ---------- Pins ----------
#define DHT_PIN 4
#define DHT_TYPE DHT22
#define PIR_PIN 14
#define LED_R 25
#define LED_G 26
#define LED_B 27

// ---------- Local advisory thresholds (serial only; the edge API is
// authoritative) ----------
#define TEMP_WARNING 26.0
#define TEMP_ALERT 30.0
#define HUM_WARNING 70.0
#define HUM_ALERT 85.0

#define INTERVAL_MS 5000

// ---------- WiFi (Wokwi virtual network) ----------
const char *WIFI_SSID = "Wokwi-GUEST";
const char *WIFI_PASS = "";

// ---------- EduSpace Edge API ----------
// Two ways to reach your local Flask server from the simulator:
//
//  A) Wokwi VS Code extension OR wokwi.com + Wokwi Club (Private Gateway):
//        USE_TLS=false, API_HOST="host.wokwi.internal", API_PORT=5000
//
//  B) Free wokwi.com web simulator (no Club): expose Flask with a Cloudflare
//     quick tunnel — `cloudflared tunnel --url http://localhost:5000` — then:
//        USE_TLS=true,  API_HOST="<random>.trycloudflare.com", API_PORT=443
//     The subdomain rotates each cloudflared run; update API_HOST per session.
//     NOTE: ngrok does NOT work — its edge refuses Wokwi's gateway (HTTP -1).
//
// The free web simulator CANNOT reach localhost directly — option B is required
// there.
const bool USE_TLS = true; // true for a public https tunnel
const char *API_HOST = "yamaha-actually-plasma-applicant.trycloudflare.com";
const int API_PORT = 443; // 443 for https, 5000 for the gateway
const char *API_PATH = "/api/v1/iot-monitoring/sensor-readings";

// Auto-seeded development test device (see specs quickstart.md).
const char *DEVICE_ID = "esp32-aula-101";
const char *API_KEY = "test-api-key-edu";

DHT dht(DHT_PIN, DHT_TYPE);
unsigned long lastReading = 0;

void setLED(bool r, bool g, bool b) {
  digitalWrite(LED_R, r ? HIGH : LOW);
  digitalWrite(LED_G, g ? HIGH : LOW);
  digitalWrite(LED_B, b ? HIGH : LOW);
}

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS, 6); // channel 6 = faster connect in Wokwi
  while (WiFi.status() != WL_CONNECTED) {
    setLED(0, 0, 1); // blue = connecting
    delay(150);
    setLED(0, 0, 0);
    delay(150);
    Serial.print(".");
  }
  Serial.print(" connected, IP: ");
  Serial.println(WiFi.localIP());
}

// Sends the reading to the edge API. Returns the alert_led_state (0/1),
// or -1 if the request did not complete with a 201.
int postReading(float temp, float hum, bool occ) {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  // Build the request body per the OpenAPI contract.
  StaticJsonDocument<200> body;
  body["device_id"] = DEVICE_ID;
  body["temperature"] = temp;
  body["humidity"] = hum;
  body["occupancy"] = occ;
  // recorded_at omitted on purpose: the edge service stamps server UTC time.
  String payload;
  serializeJson(body, payload);

  String scheme = USE_TLS ? "https://" : "http://";
  String url = scheme + API_HOST + ":" + API_PORT + API_PATH;

  // A secure client is needed for the https tunnel; a plain client for the
  // gateway.
  WiFiClientSecure tlsClient;
  WiFiClient plainClient;
  if (USE_TLS) {
    tlsClient
        .setInsecure(); // skip cert validation (fine for dev/tunnel testing)
    // NOTE: do not call tlsClient.setTimeout() here — its unit (s vs ms)
    // differs across ESP32 cores and a tiny value kills the connect.
  }

  HTTPClient http;
  http.setConnectTimeout(
      15000); // ms; Wokwi proxies traffic, so connect is slow
  http.setTimeout(15000);
  if (USE_TLS) {
    http.begin(tlsClient, url);
  } else {
    http.begin(plainClient, url);
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);
  http.addHeader("ngrok-skip-browser-warning",
                 "true"); // ignored by non-ngrok hosts

  Serial.print("Free heap : ");
  Serial.println(ESP.getFreeHeap());
  setLED(0, 0, 1); // blue = transmitting
  int status = http.POST(payload);
  String resp = http.getString();
  http.end();

  Serial.print("POST ");
  Serial.print(url);
  Serial.print(" -> HTTP ");
  Serial.println(status);
  Serial.print("Response  : ");
  Serial.println(resp);

  if (status == 201) {
    StaticJsonDocument<256> doc;
    DeserializationError err = deserializeJson(doc, resp);
    if (!err) {
      long readingId = doc["reading_id"] | -1;
      int alert = doc["alert_led_state"] | -1;
      Serial.print("reading_id      : ");
      Serial.println(readingId);
      Serial.print("alert_led_state : ");
      Serial.println(alert);
      Serial.print("recorded_at     : ");
      Serial.println((const char *)(doc["recorded_at"] | ""));
      return alert;
    }
    Serial.print("[ERROR] JSON parse failed: ");
    Serial.println(err.c_str());
  } else if (status == 400) {
    Serial.println("[ERROR] Validation error (400) — check payload fields.");
  } else if (status == 401) {
    Serial.println("[ERROR] Auth failed (401) — check device_id / X-API-Key.");
  } else if (status <= 0) {
    Serial.print("[ERROR] Connection failed: ");
    Serial.println(http.errorToString(status));
  }
  return -1;
}

void applyServerLED(int alert) {
  if (alert == 1) {
    setLED(1, 0, 0); // red = ALERT (per edge API)
  } else if (alert == 0) {
    setLED(0, 1, 0); // green = NORMAL (per edge API)
  } else {
    // No authoritative answer from the API: flash magenta to signal "offline".
    setLED(1, 0, 1);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_R, OUTPUT);
  pinMode(LED_G, OUTPUT);
  pinMode(LED_B, OUTPUT);
  pinMode(PIR_PIN, INPUT);

  dht.begin();

  // Parpadeo blanco de inicializacion
  for (int i = 0; i < 5; i++) {
    setLED(1, 1, 1);
    delay(200);
    setLED(0, 0, 0);
    delay(200);
  }

  connectWiFi();

  // One-shot TLS self-test: distinguishes "no TLS in sim" from "ngrok issue".
  {
    WiFiClientSecure probe;
    probe.setInsecure();
    Serial.print("[TLS test] example.com:443 ... ");
    Serial.println(probe.connect("example.com", 443) ? "OK" : "FAILED");
    probe.stop();

    WiFiClientSecure probe2;
    probe2.setInsecure();
    Serial.print("[TLS test] ");
    Serial.print(API_HOST);
    Serial.print(":443 ... ");
    Serial.println(probe2.connect(API_HOST, 443) ? "OK" : "FAILED");
    probe2.stop();
  }

  setLED(0, 1, 0); // Verde = listo
  Serial.println("EduSpace IoT - Ready!");
}

void loop() {
  unsigned long now = millis();

  if (now - lastReading >= INTERVAL_MS) {
    lastReading = now;

    float temp = dht.readTemperature();
    float hum = dht.readHumidity();
    bool occ = digitalRead(PIR_PIN) == HIGH;

    if (isnan(temp) || isnan(hum)) {
      Serial.println("[ERROR] DHT22 read failed!");
      return;
    }

    Serial.println("--- EduSpace IoT Reading ---");
    Serial.print("Temperature : ");
    Serial.print(temp);
    Serial.println(" C");
    Serial.print("Humidity    : ");
    Serial.print(hum);
    Serial.println(" %");
    Serial.print("Occupancy   : ");
    Serial.println(occ ? "Occupied" : "Unoccupied");

    // Local advisory interpretation (the edge API makes the real decision).
    if (temp >= TEMP_ALERT || hum >= HUM_ALERT)
      Serial.println("Local hint  : ALERT");
    else if (temp >= TEMP_WARNING || hum >= HUM_WARNING)
      Serial.println("Local hint  : WARNING");
    else
      Serial.println("Local hint  : NORMAL");

    // Send to the edge API and drive the LED from its authoritative response.
    int alert = postReading(temp, hum, occ);
    applyServerLED(alert);

    Serial.println("----------------------------");
  }
}
