# Motorola VM64 Connect (Anyka AK3918EV300) → Home Assistant, no cloud

Get a **local RTSP stream (video + mic)** out of a Motorola VM64 Connect / Hubble-style
baby monitor camera (board **`Lux65 Bu main V1.4`**, SoC **Anyka AK3918EV300 / AK3918EN080 V300**,
SPI‑NAND) and into **Home Assistant** — **without flashing**, keeping the handheld parent
monitor working.

> This repo exists because, as of 2026, **OpenIPC/Thingino do not support the AK3918EV300**
> (no build, no sensor driver, no Wi‑Fi driver, and `spinandboot` has no community unbrick
> path). Flashing it bricks the camera. The stock firmware already has everything we need.

⚠️ **You do this on your own hardware at your own risk.** Back up first (see below).

---

## TL;DR
1. Solder a 3.3 V USB‑TTL adapter to the camera's UART (GND / TX / RX).
2. Catch the boot, press **`y`** at `----- Press 'y' or 'Y' to enter test mode -----` → **root shell** (no password).
3. Back up every NAND partition over the network.
4. Make the camera join your Wi‑Fi (wrap `wpa_supplicant`), start `telnetd`, set a root password → **permanent wireless root**.
5. The stock app already serves **`rtsp://<cam-ip>:6667/blinkhd`** (H.264 + PCMA mic).
6. Add it to Home Assistant as a **Generic Camera** and assign it to a room.

---

## Hardware facts (this board)
| Item | Value |
|---|---|
| Board silkscreen | `Lux65 Bu main V1.4 2019.12.25` |
| SoC | Anyka AK3918EV300 (pkg `AK3918EN080 V300`), ARM926EJ‑S, kernel 3.4.35 |
| Bootloader | `Cloud39Ev300 spinandboot V1.2.03` (NOT U‑Boot) |
| Flash | SPI **NAND** `XT26G01B`, 128 MB, page 2048+64, erase 0x20000 |
| rootfs | yaffs2 on `/dev/mtdblock4`, **rw** |
| Sensor | MIS2003 (DVP) |
| Wi‑Fi | Realtek RTL8189FTV (`8189fs.ko`, SDIO) |
| Parent link | separate Nordic nRF52810 FHSS radio (leave its SWD pads alone) |

## UART
- 3.3 V logic, **115200 8N1**. Wire **GND, camera‑TX, camera‑RX** only (no VCC).
- On this board the UART is a short pad row; probe for the pad that emits readable boot text = camera TX.
- See `docs/uart-and-pinout.md`.

## Root (no password needed)
`/usr/sbin/auto_login.sh` does: `read -t 2 -n 1` → if `y`/`Y` → `/bin/login -f root`.
So: **power‑cycle, spam `y` during boot**, land in `[root@anyka ~]$`. Confirm with `id` → `uid=0(root)`.
(The login prompt's root password is unknown/not needed — the test‑mode hook bypasses it.)

## Back up BEFORE touching anything
Over the network (fast) — on the camera serve each partition, pull from your PC:
```sh
# on camera (per partition N): clean data via block dev
nc -l -p 9000 < /dev/mtdblockN
# bad-block partitions (B/D here): use nanddump so it doesn't stop at bad blocks
nanddump -o --bb=padbad /dev/mtdN | nc -l -p 9000
```
Critical to keep: **MAC, ENV, KERNEL, A (rootfs)**. See `scripts/backup_all.py`.

## Permanent Wi‑Fi + wireless root
The stock app forces a hardcoded factory SSID and ignores config edits. Instead, **wrap
`wpa_supplicant`** so the app's own Wi‑Fi bring‑up connects to *your* network, and run a
watchdog that keeps a DHCP lease + `telnetd`. All on rootfs → survives reboot.
See `scripts/wifi_wrapper.sh`, `scripts/ha_netwatch.sh`, and `scripts/install_persistence.md`.

Set a root password so telnet is authenticated:
```sh
passwd root
```

## The stream
With the app running, `netstat -lntp` shows `fepe_simdev` on **`0.0.0.0:6667`** (RTSP) and
`:60080` (HTTP). The stream:
```
rtsp://<cam-ip>:6667/blinkhd
  video: H.264 1080p
  audio: PCMA/16000 (built-in mic)
```

## Home Assistant
Settings → Devices & Services → **Add Integration → Generic Camera**
- Stream Source: `rtsp://<cam-ip>:6667/blinkhd`
- RTSP transport: **TCP**, still image: blank
- Assign the entity to your room area.

Scripted (REST/WS API) version in `scripts/ha_add_camera.py`.

For the native camera-speaker talkback player and the Home Assistant dispatcher flow, see [`docs/talkback-player.md`](docs/talkback-player.md) and [`docs/home-assistant-talkback-integration.md`](docs/home-assistant-talkback-integration.md).

## Temperature + extra sensors in Home Assistant (no RE needed)
The camera has an NTC temperature sensor read through the Anyka ADC (`/dev/ak_adc`)
with a proprietary formula + a factory offset — the app never logs the value and
there is no sysfs attribute. You do **not** need to reverse any of that: the stock
**factory-test binary already computes it**:
```sh
ftest tempvalue      # -> Actual = 25.1 (raw->C) / Display = 22.1 (offset applied)
ftest tempoffset     # -> the stored temprature_offset (tenths of a degree)
```
`scripts/vm64_bridge.py` runs on an always-on LAN host, polls the camera over
telnet every 2 min, and publishes **one MQTT device** (`vm64_kids_cam`) to Home
Assistant via the `mqtt.publish` service + MQTT discovery — **no broker creds**:
- `sensor` **Temperature** (`ftest tempvalue` -> `Display`)
- `sensor` **Wi-Fi Link Quality** (`/proc/net/wireless`)
- `sensor` **Last Boot** (`/proc/uptime` -> timestamp)
- `binary_sensor` **Online** (connectivity)

Install it as a systemd service (`Restart=always`, `WantedBy=multi-user.target`)
so it survives reboots. The camera's live video stays a Generic Camera entity in
the same HA area (HA can't move a non-MQTT camera entity into the MQTT device).

## What does NOT work / open items
- **Motion / sound events**: the app has motion (`hw_md_*`) and audio-event
  (`hw_aed_*`) detection, but they're only enabled/forwarded via the Hubble cloud.
  Exposing them locally needs more RE of the event callback; a robust alternative
  is motion/sound detection on the RTSP stream (go2rtc/Frigate) in HA.
- **Speaker / 2‑way talkback**: the speaker HW is real (`hw_speaker_set_volume`,
  `ctrl_speaker.c`, and `ftest tonegen` / `ftest audiolpbk`), but a clean inject
  path for talkback still needs app-protocol RE. Mic already works (in the RTSP stream).
- OpenIPC/Thingino: not supported on this SoC — don't.

## Credits / prior art
- piotr_go — GNCC GC2 AK3918EV300 RTSP (Nemobi SDK)
- OpenIPC & ipctool Anyka issues (status/detection)
- Erliz/hubble-sniffer — the `:6667/blinkhd` + `/cgi/jpg/image.cgi` Hubble endpoints

See `docs/research-summary.md` for the full feasibility writeup and sources.
