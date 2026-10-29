# VM64 → Home Assistant — Project Roadmap

Goal: fully own the Motorola VM64 baby-monitor system (camera **and** parent unit) and run it entirely through Home Assistant / Jarvis — local, cloud-free, no Hubble/Motorola app.

## Camera unit (Anyka AK3918EV300, Linux) — DONE / ongoing polish
Root via telnet, local cloud-free speaker (vm64_play3), Piper neural voice, HA talkback + quick phrases, iPhone Assist voice command ("tell the kids…" → camera), file/URL playback, LED/IR control, morning reminder routed to the camera (never the kids TV), Black Liquid Glass dashboard theme. See REVERSE-ENGINEERING.md / HANDOFF-STATUS.md.

## Parent unit (Anyka AK3750, **bare-metal RTOS**, Beken BK2425 RF) — IN PROGRESS
UART boot captured (`PARENT-UNIT-bootlog.txt`): no Linux/shell to root; the value is the RF link spec + live telemetry. Three phases, in order:

### Phase 1 — UART telemetry → HA sensors  ← DOING NOW
Parse the debug UART (already wired, COM7 on Mason's PC) and publish parent-unit state to HA:
- `sensor.parent_unit_cam_link` (connected / lost)
- `sensor.parent_unit_battery_raw` (ADC level at boot)
- `sensor.parent_unit_last_update`
First version runs on the PC pushing via HA REST API; later move to Jarvis or an ESP for always-on, and/or MQTT discovery for permanent entities.

### Phase 2 — RF sniff / bridge (headline hack)
Use the captured BK2425 params (Factory ID=82, Product ID=0xf5b, 255-ch hopping, 18 addr bytes) with an **nRF24L01+/BK2425 module on an ESP32** to join/sniff the camera↔parent 2.4GHz link → bridge audio/video/telemetry to HA fully cloud-free.

### Phase 3 — Firmware dump + RE
CH341A + SOIC-8 clip to dump the SPI NOR (id 0x0016400b), reverse the AK3750 image + BK2425 protocol for a from-scratch HA-native receiver.

## Standing orders
Keep camera telnet root; no Hubble/Motorola pairing; no cloud firmware updates; camera UART unsoldered (no recovery) so no brick-risk gambles on the camera. Parent unit is the spare we can risk. Confirm audio/behavior by ear/eye. Keep this repo + HANDOFF-STATUS.md updated.
