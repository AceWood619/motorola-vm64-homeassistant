# Phase 2 — RF sniff / bridge the camera↔parent 2.4 GHz link

## What we know (from the parent-unit boot log)
- Radio chip: **Beken BK2425** — a 2.4 GHz GFSK transceiver, **register- and air-compatible with the Nordic nRF24L01+** family. CHIP ID=99, RF ver 00.00.04.
- IDs: **Factory ID = 82**, **Product ID = 0x f5b**.
- Address bytes dumped at init (18 bytes):
  `0f 5b 00 02 ff ff ff 0c 08 18 28 38 01 03 ff aa 08 08`
  → the first 5 (`0f 5b 00 02 ff`... likely `0F 5B 00 02 FF` or a subset) are the candidate **pipe address**; note `5b`/`f5b` ties to Product ID 0xf5b.
- **255-channel frequency hopping, adaptive OFF** → fixed pseudo-random hop pattern (not interference-driven). We must find the hop set/sequence.
- Payload example seen on UART: `41 1 ff 3e 2 4f 0 0 0 0 0 0 2 0 ff 0` (16 bytes) → likely the fixed **payload size = 16–32 bytes**.

## Hardware you'll need
- An **ESP32** (you already build these) OR an Arduino.
- An **nRF24L01+** module (cheap) — or ideally a genuine **BK2425** breakout for exact PA/data-rate match. nRF24L01+ is the easy start.
- Wiring (SPI): nRF24 ↔ ESP32: CE, CSN, SCK, MOSI, MISO, 3.3V, GND (+ decoupling cap on the module's 3.3V — these modules are noisy).

## Approach (staged)
1. **Carrier scan** — sweep channels 0–125, log where energy appears while the real camera+parent are powered and linked. That reveals the active hop band/channels. (Starter sketch: `firmware/bk2425_scanner/bk2425_scanner.ino`.)
2. **Lock a pipe** — set address width/length, data rate (try **1 Mbps and 2 Mbps**, and 250 kbps), CRC, and the candidate address above; park on a busy channel and try to receive raw payloads. Confirm against the UART payload pattern.
3. **Map the hop sequence** — with a single radio you'll catch bursts; to follow hopping, either (a) find the PRNG/seed (likely derived from Factory/Product ID), or (b) use multiple radios / an SDR (HackRF/RTL-SDR won't demod GFSK easily but helps map channels).
4. **Bridge to HA** — once we can decode telemetry/audio/video frames, publish to HA (ESPHome custom component or MQTT). Video is the hard part (compressed stream); telemetry + audio first.

## Notes / risks
- nRF24 "promiscuous"/sniffer tricks (shortened address, disabled CRC) help discover unknown addresses — we'll use that to confirm the real pipe address.
- Legal/benign: we only receive our own devices' link. No transmit into the link until we understand it.
- This is a real multi-session RE effort; carrier scan + pipe lock is the concrete first milestone.


---

## REVISED DIRECTION (2026-10-29): emulate the camera, don't sniff it

**Finding:** inspected the camera over telnet/root. It communicates over **WiFi** (Realtek `wlan0`, `wpa_supplicant`, `RTW_*` threads) and still talks to the **Motorola cloud** (`54.186.238.93`). `fepe_simdev` is the app. There is **no proprietary 2.4 GHz / BK2425 transmitter** running on the camera. The parent unit is **BK2425-only, no wifi**. So there is **no camera→parent RF link to sniff** — this VM64 "Connect" camera is a wifi/cloud model and the handheld parent is a separate proprietary-RF unit; they don't natively pair.

**New plan — make an ESP32 + nRF24/BK2425 *be* the camera (TX → parent):**
1. Configure the radio with the parent's expected identity from its boot log: **Factory ID=82, Product ID=0xf5b**, the 18 address bytes, 255-ch hopping, payload ~16 bytes (`41 01 ff 3e 02 4x …`).
2. Reproduce the parent's sync/pairing handshake (the `<0,50,x>` / `****** 1 ******` exchange we see on its UART) so the parent accepts us as "camera 0."
3. Once the parent locks, feed it frames → the parent becomes a **Synapse-branded HA display**: proxied HA camera feed, room status screens, alerts, etc.
4. The parent's UART stays our debug/telemetry channel throughout (Phase 1 already live).

This is more achievable than sniffing (we control the TX) and far more useful — the parent turns into a device we drive instead of a dumb Motorola receiver. Hop-sequence/handshake details come from the parent's UART + the Phase-3 firmware dump.

_Boot splash artwork for the repurposed unit: a 480×272 Synapse splash is drafted (PNG + RGB565) — see Phase 3. Final version committed once approved._
