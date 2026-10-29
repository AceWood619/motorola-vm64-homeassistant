# Motorola VM64 — Parent Unit (handheld monitor) teardown & hack

_Started 2026-10-29. Same system as the camera, so it lives in this repo (folder/doc, not a separate repo)._

## Board identification
- Silkscreen: **`Lux65 PU MAIN V1.3`**, dated **`2020.01.07`** ("PU" = Parent Unit).
- Platform: "Lux65" — same baby-monitor family as the camera (Anyka AK3918EV300). Parent unit is almost certainly an **Anyka-family SoC** too (matched RX/display side).
- Major parts visible:
  - **Main SoC** — BGA under a black thermal pad (markings hidden), center of board, next to the RF shield.
  - **24.000 MHz** crystal by the SoC (`24.000` silk on the can).
  - **8-pin SOIC** top-right of the SoC — almost certainly the **SPI NOR flash** holding firmware (dumpable with a CH341A + SOIC-8 clip).
  - **2.4 GHz RF** section under the shield can (proprietary FHSS link to the camera, not Wi-Fi).
  - **LCD** on an orange FPC ribbon; **speaker**; **Lenovo Li-ion battery** (phone-style pack, just the battery brand).
  - Caps marked `H2 220 10V`.

## The gift: a fully labeled debug pad row (left-center of the board)
Gold test pads, clearly silkscreened:

| Pad | Meaning |
|-----|---------|
| **VCC** | main supply rail |
| **SW** | switch / boot-mode select (TBD) |
| **TX** | **UART transmit (SoC → us)** |
| **RX** | **UART receive (us → SoC)** |
| **DM** | **USB D−** |
| **DP** | **USB D+** |
| **1.2V** | core rail test point |
| **3.3V** | IO rail test point → **confirms 3.3 V logic** |
| **Power in** | power input |
| **GND** | ground (also a GND pad lower-left) |
| **BAT+** | battery positive |

This means two ways in, no UART-hunting required (unlike the camera):
1. **UART serial console** via TX / RX / GND — primary path to a boot log + shell.
2. **USB** via DP / DM (+ VCC/GND) — secondary; may enumerate (serial/ADB/mass-storage) depending on SoC USB role.

## Plan (mirrors the camera hack)
1. **UART first.** 3.3 V USB-TTL adapter. Cross TX/RX, share GND, power the board normally. Open terminal, try **115200 8N1** (Anyka default), then 57600. Capture full boot log.
2. From the boot log: ID the SoC + bootloader (U-Boot/Anyka loader) + kernel; get a root shell (camera auto-dropped to root — PU may too, or need a boot interrupt / login).
3. Optional: **dump the SPI flash** (CH341A + SOIC-8 clip) for offline firmware analysis / safe backup before any change.
4. Then design HA integration (decode/ tap the RF link, use as a second speaker/display node, or bridge its audio — scope TBD after we see the firmware).

## Safety (standing orders)
- **3.3 V logic ONLY** — a 5 V adapter will kill the SoC. Set the adapter jumper to 3.3 V and verify.
- Connect **GND first**. Don't bridge adjacent pads (TX/RX/DM/DP sit close).
- Don't connect the adapter's VCC **and** battery/Power-in at the same time (avoid back-powering) — power the board from its own battery/supply and bring over **only GND + TX + RX**.
- This is the spare we're willing to risk; keep notes here as we go.

## Status
- 2026-10-29: Board opened and photographed; pad row identified. Next: solder UART, capture boot log.


---

## FINDINGS — UART boot captured 2026-10-29 (see PARENT-UNIT-bootlog.txt)
- **SoC = Anyka AK3750**, running **bare-metal RTOS** (Anyka DrvLib 1.0.13, tasks D_UART0/D_VTIMR/D_AD/D_DA; "spiboot V1.3.01" → decompress BIOS → jump 0x30000000). **Not Linux** — so, unlike the camera, there is **no root shell / telnet / busybox to obtain**. The camera (AK3918EV300) was Linux; the parent unit is a cheaper RTOS display/receiver chip. "Kinda the same" = same vendor (Anyka), different class of chip.
- UART @115200 is a **debug print (output only)** — no command parser (tested `?`, `help`, Enter → nothing).
- **RF link = Beken BK2425** 2.4 GHz GFSK (nRF24-class). From boot: CHIP ID=99, RF ver 00.00.04, **Factory ID=82, Product ID=0xf5b**, 18 address bytes, **255-channel frequency hopping** (adaptive off). This is the proprietary camera↔parent wireless link.
- SPI NOR flash id=0x0016400b holds the firmware (dumpable with CH341A + SOIC-8 clip).
- LCD 480×272 (id 0x5180); on-board mic + speaker. No local camera (decodes the RF video only).

### So what CAN we do for HA (realistic paths)
1. **UART telemetry → HA sensors (quick win).** The debug stream already reports link up/down ("cam 0 lostlink"), battery level, and per-packet state. Parse it on Jarvis (or an ESP) and publish `sensor.parent_unit_battery`, `binary_sensor.parent_cam_link`, etc. to HA. Low effort, uses the wire already connected.
2. **RF protocol sniff/bridge (the deep, fun hack).** We now have the BK2425 params (IDs + hopping). A cheap nRF24L01+/BK2425 module on an ESP32 could attempt to sniff/join the camera↔parent link and bridge audio/video/telemetry to HA fully cloud-free. Big RF-reversing effort, but Mason has ESPHome/esptools.
3. **Firmware dump + RE (deepest).** CH341A-dump the SPI flash → reverse the AK3750 image + BK2425 protocol for a from-scratch HA-native receiver.
4. **Audio tap** of the decoded speaker output (analog) — possible but least clean.

Recommended order: **#1 now** (immediate HA value), then **#2** as the headline project.
