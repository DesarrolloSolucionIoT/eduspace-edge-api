/*
 * EduSpace - Prueba de hardware (SIN WiFi ni API)
 * --------------------------------------------------------------
 * Verifica de forma aislada las 3 conexiones del montaje:
 *   - LED RGB (catodo comun): enciende cada color por separado
 *   - DHT22  : imprime temperatura y humedad
 *   - PIR    : imprime si detecta movimiento y enciende el LED rojo
 *
 * Pinout (ESP32 enchufado al protoboard, SOLO lado izquierdo):
 *   DHT22  dato -> GPIO32   ( + alimentado a 5V/VIN, - a GND )
 *   PIR    OUT  -> GPIO14   ( VCC a 5V/VIN, GND a GND )
 *   LED RGB R   -> GPIO25  (por resistencia 220 ohm)
 *   LED RGB G   -> GPIO26  (por resistencia 220 ohm)
 *   LED RGB B   -> GPIO27  (por resistencia 220 ohm)
 *   LED comun (pata larga) -> GND
 *
 * Solo necesita la libreria "DHT sensor library" (Adafruit).
 */
#include <DHT.h>

#define DHT_PIN 32
#define DHT_TYPE DHT22
#define PIR_PIN 14
#define LED_R 25
#define LED_G 26
#define LED_B 27

DHT dht(DHT_PIN, DHT_TYPE);

// Catodo comun: HIGH = encendido.
void setLED(bool r, bool g, bool b) {
  digitalWrite(LED_R, r ? HIGH : LOW);
  digitalWrite(LED_G, g ? HIGH : LOW);
  digitalWrite(LED_B, b ? HIGH : LOW);
}

// Enciende rojo, verde, azul y blanco para verificar cada canal,
// las resistencias, la polaridad y que el comun este a GND.
void ledSelfTest() {
  Serial.println("== Test del LED: ROJO -> VERDE -> AZUL -> BLANCO ==");
  const char *names[] = {"ROJO", "VERDE", "AZUL", "BLANCO"};
  const bool colors[][3] = {{1, 0, 0}, {0, 1, 0}, {0, 0, 1}, {1, 1, 1}};
  for (int i = 0; i < 4; i++) {
    Serial.print("  -> ");
    Serial.println(names[i]);
    setLED(colors[i][0], colors[i][1], colors[i][2]);
    delay(800);
  }
  setLED(0, 0, 0);
}

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(LED_R, OUTPUT);
  pinMode(LED_G, OUTPUT);
  pinMode(LED_B, OUTPUT);
  pinMode(PIR_PIN, INPUT);
  dht.begin();

  Serial.println("\n=== EduSpace - Prueba de hardware ===");
  ledSelfTest();
  Serial.println("PIR calentando (~30-60 s la primera vez)...");
  Serial.println("Lecturas cada 2 s. Pasa la mano frente al PIR -> LED rojo.\n");
}

void loop() {
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  bool motion = digitalRead(PIR_PIN) == HIGH;

  Serial.println("---------------------------------");
  if (isnan(temp) || isnan(hum)) {
    Serial.println("DHT22      : ERROR de lectura");
    Serial.println("             revisa: + a 5V, dato en GPIO32, - a GND");
  } else {
    Serial.print("Temperatura: ");
    Serial.print(temp);
    Serial.println(" C");
    Serial.print("Humedad    : ");
    Serial.print(hum);
    Serial.println(" %");
  }

  Serial.print("PIR        : ");
  Serial.println(motion ? "MOVIMIENTO detectado" : "sin movimiento");

  // El LED refleja el PIR: rojo con movimiento, verde en reposo.
  setLED(motion ? 1 : 0, motion ? 0 : 1, 0);

  delay(2000);
}
