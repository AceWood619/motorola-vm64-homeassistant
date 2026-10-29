/*
 * bk2425_scanner.ino  —  Phase 2 recon for the VM64 camera<->parent 2.4GHz link.
 * ESP32 + nRF24L01+ (air-compatible with the parent unit's Beken BK2425).
 *
 * STEP 1 (this sketch): carrier scan. Power the REAL camera + parent unit and
 * watch which channels light up — that's the hop band to target next.
 *
 * Wiring (ESP32 <-> nRF24L01+):
 *   CE  -> GPIO4      CSN -> GPIO5
 *   SCK -> GPIO18     MOSI-> GPIO23     MISO-> GPIO19
 *   VCC -> 3.3V (add a 10uF cap across the module's VCC/GND!)   GND -> GND
 *
 * Library: "RF24" by TMRh20 (Arduino Library Manager).
 * Serial @115200. Each line = one full 0..125 channel sweep; char = hits.
 */
#include <SPI.h>
#include <RF24.h>

#define CE_PIN  4
#define CSN_PIN 5
RF24 radio(CE_PIN, CSN_PIN);

const uint8_t CHANNELS = 126;
uint8_t values[CHANNELS];

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\nBK2425/nRF24 carrier scanner. Power camera+parent now.");
  if (!radio.begin()) { Serial.println("RADIO NOT FOUND - check wiring/3.3V"); }
  radio.setAutoAck(false);
  radio.setDataRate(RF24_1MBPS);   // also try RF24_2MBPS and RF24_250KBPS
  radio.setChannel(0);
  Serial.print("ch:   ");
  for (uint8_t i = 0; i < CHANNELS; i += 10) { Serial.print(i/10); Serial.print("         "); }
  Serial.println();
}

void loop() {
  const int reps = 200;
  memset(values, 0, sizeof(values));
  for (int r = 0; r < reps; r++) {
    for (uint8_t ch = 0; ch < CHANNELS; ch++) {
      radio.setChannel(ch);
      radio.startListening();
      delayMicroseconds(130);
      bool carrier = radio.testCarrier() || radio.testRPD();
      radio.stopListening();
      if (carrier && values[ch] < 255) values[ch]++;
    }
  }
  Serial.print("scan: ");
  for (uint8_t ch = 0; ch < CHANNELS; ch++) {
    uint8_t v = values[ch];
    Serial.print(v == 0 ? '.' : (v > 15 ? '#' : "0123456789abcdef"[v]));
  }
  Serial.println();
}
