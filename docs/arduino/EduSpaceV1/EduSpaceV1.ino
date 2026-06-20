/*
 * EduSpace V1 - ESP32 fisico (Arduino IDE) -> Edge API
 * --------------------------------------------------------------
 * Lee DHT22 (temp/humedad) + PIR (ocupacion) y los envia por HTTP
 * al EduSpace Edge API. El LED RGB se maneja con la respuesta
 * autoritativa del API (alert_led_state), NO con una decision local.
 *
 * Pinout (igual al hardware_test.ino que ya funciona):
 *   DHT22 dato -> GPIO32   ( + a 5V/VIN, - a GND )
 *   PIR   OUT  -> GPIO14   ( VCC a 5V/VIN, GND a GND )
 *   LED RGB R  -> GPIO25  (resistencia 220 ohm)
 *   LED RGB G  -> GPIO26  (resistencia 220 ohm)
 *   LED RGB B  -> GPIO27  (resistencia 220 ohm)
 *   LED comun (catodo, pata larga) -> GND
 *
 * Librerias (Library Manager): "DHT sensor library" (Adafruit) +
 * su dependencia "Adafruit Unified Sensor", y "ArduinoJson".
 */
#include <ArduinoJson.h>
#include <DHT.h>
#include <HTTPClient.h>
#include <WiFi.h>

// ---------- Pines (montaje fisico) ----------
#define DHT_PIN 32 // <-- GPIO32 en hardware real (en Wokwi era D4)
#define DHT_TYPE DHT22
#define PIR_PIN 14
#define LED_R 25
#define LED_G 26
#define LED_B 27

// ---------- Umbrales locales solo informativos (serial). ----------
// El edge API es la autoridad sobre el estado del LED.
#define TEMP_WARNING 26.0
#define TEMP_ALERT 30.0
#define HUM_WARNING 70.0
#define HUM_ALERT 85.0

#define INTERVAL_MS 5000

// ---------- WiFi (TU red real; el ESP32 y la PC deben estar en la misma)
// ----------
const char *WIFI_SSID = "iPhone de Luis";
const char *WIFI_PASS = "luis5173";

// ---------- EduSpace Edge API ----------
// Pon la IP LOCAL de la PC donde corre Flask (mira el Paso 3: ipconfig).
// Ej: "192.168.1.45". Flask debe correr con --host 0.0.0.0 en el puerto 5000.
const char *API_HOST = "172.20.10.3";
const int API_PORT = 5000;
const char *API_PATH = "/api/v1/iot-monitoring/sensor-readings";

// Device de desarrollo sembrado por el API (EDUSPACE_ENV=development).
const char *DEVICE_ID = "esp32-aula-101";
const char *API_KEY = "test-api-key-edu";

DHT dht(DHT_PIN, DHT_TYPE);
unsigned long lastReading = 0;

// Catodo comun: HIGH = encendido.
void setLED(bool r, bool g, bool b) {
  digitalWrite(LED_R, r ? HIGH : LOW);
  digitalWrite(LED_G, g ? HIGH : LOW);
  digitalWrite(LED_B, b ? HIGH : LOW);
}

void connectWiFi() {
  Serial.print("Conectando a WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    setLED(0, 0, 1); // azul = conectando
    delay(150);
    setLED(0, 0, 0);
    delay(150);
    Serial.print(".");
  }
  Serial.print(" conectado, IP: ");
  Serial.println(WiFi.localIP());
}

// Envia la lectura al edge API. Devuelve alert_led_state (0/1),
// o -1 si la peticion no termino con un 201.
int postReading(float temp, float hum, bool occ) {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  // Cuerpo segun el contrato OpenAPI. recorded_at se omite a proposito:
  // el edge service estampa la hora UTC del servidor.
  StaticJsonDocument<200> body;
  body["device_id"] = DEVICE_ID;
  body["temperature"] = temp;
  body["humidity"] = hum;
  body["occupancy"] = occ;
  String payload;
  serializeJson(body, payload);

  String url = String("http://") + API_HOST + ":" + API_PORT + API_PATH;

  WiFiClient client;
  HTTPClient http;
  http.setConnectTimeout(8000);
  http.setTimeout(8000);
  http.begin(client, url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);

  setLED(0, 0, 1); // azul = transmitiendo
  int status = http.POST(payload);
  String resp = http.getString();
  http.end();

  Serial.print("POST ");
  Serial.print(url);
  Serial.print(" -> HTTP ");
  Serial.println(status);
  Serial.print("Respuesta : ");
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
    Serial.print("[ERROR] Fallo al parsear JSON: ");
    Serial.println(err.c_str());
  } else if (status == 400) {
    Serial.println("[ERROR] Validacion (400) - revisa los campos del payload.");
  } else if (status == 401) {
    Serial.println("[ERROR] Auth (401) - revisa device_id / X-API-Key.");
  } else if (status <= 0) {
    Serial.print("[ERROR] Conexion fallida: ");
    Serial.println(http.errorToString(status));
    Serial.println(
        "        revisa: IP de la PC, puerto 5000, mismo WiFi, firewall.");
  }
  return -1;
}

void applyServerLED(int alert) {
  if (alert == 1) {
    setLED(1, 0, 0); // rojo = ALERTA (segun edge API)
  } else if (alert == 0) {
    setLED(0, 1, 0); // verde = NORMAL (segun edge API)
  } else {
    setLED(1, 0, 1); // magenta = API inalcanzable
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(LED_R, OUTPUT);
  pinMode(LED_G, OUTPUT);
  pinMode(LED_B, OUTPUT);
  pinMode(PIR_PIN, INPUT);
  dht.begin();

  // Parpadeo blanco de inicializacion.
  for (int i = 0; i < 5; i++) {
    setLED(1, 1, 1);
    delay(200);
    setLED(0, 0, 0);
    delay(200);
  }

  connectWiFi();
  Serial.println("EduSpace IoT - Listo!");
  Serial.println("PIR calentando (~30-60 s la primera vez)...");
  setLED(0, 1, 0); // verde = listo
}

void loop() {
  unsigned long now = millis();
  if (now - lastReading < INTERVAL_MS) {
    return;
  }
  lastReading = now;

  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  bool occ = digitalRead(PIR_PIN) == HIGH;

  if (isnan(temp) || isnan(hum)) {
    Serial.println("[ERROR] Lectura DHT22 fallida (revisa dato en GPIO32, + a "
                   "5V, - a GND).");
    return;
  }

  Serial.println("--- EduSpace IoT Reading ---");
  Serial.print("Temperatura : ");
  Serial.print(temp);
  Serial.println(" C");
  Serial.print("Humedad     : ");
  Serial.print(hum);
  Serial.println(" %");
  Serial.print("Ocupacion   : ");
  Serial.println(occ ? "Ocupado" : "Vacio");

  // Interpretacion local solo informativa (la decision real la toma el API).
  if (temp >= TEMP_ALERT || hum >= HUM_ALERT)
    Serial.println("Hint local  : ALERTA");
  else if (temp >= TEMP_WARNING || hum >= HUM_WARNING)
    Serial.println("Hint local  : WARNING");
  else
    Serial.println("Hint local  : NORMAL");

  int alert = postReading(temp, hum, occ);
  applyServerLED(alert);
  Serial.println("----------------------------");
}
