# Motorola VM64 — Reverse-Engineering Notes

Living technical record of everything learned while turning a Motorola VM64 (Hubble/Binatone
baby monitor camera) into a fully-local Home Assistant device, keeping stock firmware and
telnet root. Newest findings are added over time. **UART on the camera is unsoldered = there is
no physical recovery, so nothing here gambles the camera's ability to boot, join Wi-Fi, or run
telnetd.**

---

## 1. Device identity & hardware (measured)

| Item | Value |
|---|---|
| SoC | Anyka **AK3918EV300** (`Hardware: CLOUD39EV3_AK3918EV300_MNBD`) |
| CPU | ARM926EJ-S (ARMv5TEJ), single core, ~198 BogoMIPS, **no FPU / no NEON / no NPU** |
| RAM | **26 MB total** (~2.7 MB free + ~7 MB reclaimable cache) — the real resource limit |
| Kernel | Linux **3.4.35** `armv5tejl`, built 2021-05-21 |
| Flash | 128 MB SPI-NOR, dual-bank A/B OTA layout |
| Wi-Fi | Realtek RTL871x (`wlan0`); MAC `F0:C8:14:FF:CF:CF` |
| Camera | H.264, 1080p; mic PCMA/16000 |

### Flash / MTD layout
```
mtd0 spi0.0 128M (whole)   mtd3 KERNEL 1.9M   mtd4 A 5M    mtd5 B 15M   mtd6 C 1.5M
mtd7 D 76M (=/mnt)         mtd8 KERBAK        mtd9 AK 5M   mtd10 BK 15M mtd11 CK 1.5M  mtd12 T_UVC
```

### Mounts (all **yaffs2, read-write** — not squashfs)
| Mount | Dev | Size | Free | Notes |
|---|---|---|---|---|
| `/` | /dev/root | 5.0M | ~40K | rootfs, writable |
| `/usr` | mtdblock5 | 15M | ~148K | writable, nearly full |
| `/etc/usr_config` | mtdblock6 | 1.5M | ~704K | writable config |
| `/mnt` | mtdblock7 | 76M | **~70M free** | yaffs2, persistent — our scratch/persist area |

Everything is writable, which makes modding easy **and dangerous** (corrupting a boot file can
brick access with no UART). Treat `/usr/sbin/*` boot scripts as sacred.

---

## 2. Access

- **Camera telnet root:** `telnet 10.0.0.22`  user `root` pass `babycam123`. No SSH on the camera.
  Helper `camcmd.py` logs in over a raw socket and runs one command (busybox `nc` half-closes and
  hangs after a transfer, so pull-to-file and act in separate calls; busybox `cp` prompts — use
  `cat a > b`).
- **Jarvis box** (Ubuntu, go2rtc + ffmpeg + toolchain) `10.0.0.60`:
  `ssh -i ~/.ssh/hakey acewood@10.0.0.60` (NOPASSWD sudo). All tooling lives here.
- **Home Assistant** `http://10.0.0.165:8123`; RTSP via go2rtc `rtsp://127.0.0.1:8554/kids_bedroom_camera`
  and direct `rtsp://10.0.0.22:6667/blinkhd`.
- Persistence that survives camera reboot must live on `/mnt` (the rest of `/tmp` clears).

---

## 3. Audio subsystem — the main RE effort

### 3.1 Device ownership (why "just play a file" fails)
The stock app **`fepe_simdev`** (plus `fepe_daemon`) is launched by `/usr/sbin/simdev_startup.sh`
and holds the audio devices **exclusively**:
- `/dev/akpcm_cdev0` = playback (speaker)
- `/dev/akpcm_cdev1` = capture (mic, feeds the RTSP audio)

Any second process that opens `/dev/akpcm_cdev0` gets **EPERM**. `fepe_simdev` is also the H.264
**video encoder + RTSP server + mic source**, so it cannot simply be removed — it IS the camera.

### 3.2 Confirmed DEAD ENDS (do not re-waste time)
- **The fifo `FILE_NOTIFY&PLAY_WAVE&NEXT_JOB` → `/tmp/daemon_fifo`** — *does not make sound.*
  Verified with a **cleared** kernel log: firing it produces **zero** playback ioctls and nothing
  in `/mnt/log/simdevlog`. Earlier notes that claimed "~8 s playback confirmed" mis-attributed
  unrelated boot/cloud kernel lines. The fifo PLAY_WAVE path is dead.
- **Factory `ftest tonegen on 1000`** — also silent (and it leaves the AO device sticky). It does
  not drive the speaker on this unit in isolation.
- **Standalone player while `fepe` runs** — EPERM, as above.
- **On-camera motion/sound detection (`hw_md`/`hw_aed`)** — cloud-gated; only enabled when the
  Hubble cloud configures it. Do motion detection on the RTSP stream instead (go2rtc/Frigate).

### 3.3 The app's own audio paths (symbols from `fepe_simdev`)
`ctrl_speaker.c` / `speaker.c`: `hw_prepare_speaker`, `hw_speaker_init`, `ctrl_speaker_playfile_start/stop`,
`force_stop_speaker_voice_prompt`, `sim_speaker_play_wave`, `prepare_talkback_env`, `bu_talkback`,
`ak_ao_open/_set_sample_rate/_enable_speaker/_set_volume/_send_frame/_notice_frame_end/_close`.
`hw_prepare_speaker` opens the AO with args `(6,16,1,8000)`. The 4 `HAL_SetGpioLevel` calls near
the talkback code are **IR-cut / night-vision (`ak_vi_switch_mode`)**, NOT a speaker amp — there is
no shell-settable speaker-amp GPIO. Audiobook/voice-prompt/talkback are all **cloud-triggered**;
only parent-unit talkback produced sound (it rides the Motorola relay).

### 3.4 THE WORKING LOCAL SPEAKER METHOD ✅ (cloud-free, confirmed audible)
Owner (Mason) authorised sacrificing parent-unit talkback (parent is UART-reflashable). Method:
**briefly stop fepe, grab the device with our own player, restart fepe.**

1. Player: `vm64_play3` — ARMv5/uClibc binary that `dlopen`s `/usr/lib/libplat_ao.so` (+ its
   hidden deps) and calls the `ak_ao_*` API. Source = `vm64_play.c` with the
   **`ak_ao_set_volume` call removed**.
2. **BUG:** `ak_ao_set_volume()` **SIGFPEs** (divide-by-zero on this chip rev; prints
   `## ChipIdval = 0x20160100` then dies). Never call it. **Loudness is set by the WAV sample
   amplitude instead.**
3. **RATE QUIRK:** the DAC clocks at **2× the rate you set** (mono fed as if stereo). So author
   audio at the *true* rate and pass **half** of it to the player. Working combo for clear speech:
   **content = 16 kHz mono s16le, player rate arg = 8000.** (8 k content / 8 k arg and 16 k / 16 k
   both play ~2× fast = chipmunk.)
4. Sequence (detached with `setsid` so a dropped telnet can't leave fepe stopped):
   ```sh
   setsid sh -c "stop_simdev.sh; sleep 1; \
     /mnt/vm64_play3 /tmp/talkback.wav 8000 1 >/tmp/p3.log 2>&1; \
     setsid /usr/sbin/simdev_startup.sh >/tmp/x 2>&1 </dev/null &" &
   ```
   Stopping fepe is safe for the camera: Wi-Fi (`wpa_supplicant`/`ha_netwatch.sh`) and `telnetd`
   are independent; fepe has no respawn watchdog; `simdev_startup.sh` relaunches it.
   **Trade-off:** RTSP video + parent talkback drop for ~5–8 s per announcement.
5. Verified end to end: tones (confirmed by ear), then espeak TTS (intelligible; "robotic" is just
   espeak's formant synth — a nicer voice like Piper can be rendered on Jarvis later).

**Future non-disruptive upgrade:** `LD_PRELOAD` a resident helper into `fepe` that reuses its own
`cdev0` handle / `ctrl_speaker_playfile` path, so nothing has to stop and video never drops.

### 3.5 TTS pipeline (on Jarvis)
`cam_say.sh "text"` → `espeak-ng` → `ffmpeg` (dynaudnorm, **-ar 16000**, mono, s16le, minimal WAV,
no LIST chunk) → `stage_file.sh` (md5-verified `nc` transfer) → the stop/play/restart sequence with
player rate arg **8000**.

---

## 4. Cloud / relay

- `simdev_startup.sh` launches fepe with `UIP=54.186.238.93` (Motorola relay).
- Logs show persistent `relay ping-pong timeout` / `RELAY_SERVER ... DISCONNECT` — the cloud relay
  is effectively **dead/unreachable**; the camera is already functioning cloud-free.
- A live blackhole route (`route add -host 54.186.238.93 reject`) silences the retry churn. Not
  persisted across reboots on purpose (the only boot hook also restarts telnetd; a typo there =
  loss of access with no UART). On reboot it reverts to harmless retry-logging.
- **Do NOT pair** with the Hubble/Nursery app and **do not** allow a cloud firmware update
  (would risk telnet root; no UART recovery).

---

## 5. What is / isn't feasible

- **On-device AI (person/object detection on the camera): NOT feasible** — ARMv5, 26 MB RAM, no
  NPU/NEON. Correct approach: run detection on the **RTSP stream** (`rtsp://10.0.0.22:6667/blinkhd`)
  via **Frigate/go2rtc** on Jarvis or the HA box (optionally a Coral USB TPU). Camera just streams.
- **Replacing the video daemon / custom firmware for lower latency: possible but high-risk** — it
  means replacing the proprietary Anyka encode/RTSP pipeline on a no-UART-recovery unit. Prefer
  tuning the existing chain (keyframe interval, RTSP TCP, go2rtc low-latency/WebRTC, HA buffering).
- Temperature already works: `ftest tempvalue` (Actual/Display, offset `-30` tenths) → MQTT to HA.

---

## 6. Tooling (on Jarvis `10.0.0.60`)

| File | Purpose |
|---|---|
| `camcmd.py` | telnet-to-camera single-command helper (root/babycam123) |
| `stage_file.sh <local> <cam_path>` | md5-verified binary transfer (serves via `nc -l 9085`, camera pulls) |
| `cam_say.sh "text"` | espeak-ng → 16 kHz WAV → stage → stop/play/restart (local TTS) |
| `vm64build/vm64_play3(.c)` | the working speaker player (no `ak_ao_set_volume`) |
| `vm64build/arm-anykav200-crosstool/` | gcc 4.8.5 + uClibc 0.9.33 cross toolchain (exact match) |
| `measure.sh` | ffmpeg volumedetect on the go2rtc stream (mic; limited by camera AEC) |

Player is persisted at camera `/mnt/vm64_play3` (survives reboot).

---

## 7. Next steps
- Wire `cam_say` into Home Assistant (shell_command / small HTTP service on Jarvis → rest_command).
- Route all kids-bedroom announcements to the camera speaker (never the bedroom TV); TV-protection.
- Louder output via higher WAV amplitude / limiter (ak_ao_set_volume unusable).
- Motion detection via go2rtc/Frigate on the RTSP stream → HA binary_sensor.
- Optional: Piper TTS on Jarvis for a natural voice; LD_PRELOAD resident player to avoid video drop.

---

## 8. Home Assistant integration (2026-10-28) — DONE

Full chain verified end-to-end (confirmed by the HA entity clearing + fresh audio generated):

**HA dashboard control → camera speech**
1. Helper `input_text.kids_camera_say` (created via the HA WS API `input_text/create`).
2. Jarvis systemd service **`cam-poll`** (`cam_poll.py`) polls that entity every 2 s over the HA
   REST API; on a new value it runs `cam_say.sh` and clears the field. (MQTT broker 1883 is NOT
   reachable from Jarvis, so this poll design avoids needing it — and needs no HA YAML edits.)
3. Jarvis systemd service **`cam-say`** (`cam_say_server.py`, port 8790) is an optional HTTP
   front-end: `GET/POST http://10.0.0.60:8790/say?text=...` → same `cam_say.sh`. Handy for curl /
   `rest_command` / automations.
4. Dashboard (storage dashboard url_path `jarvis-hud`, **Junior** view, "Kids Bedroom Camera"
   section) now has a **"Speak to Kids Room"** entities card wired to `input_text.kids_camera_say`:
   type text, press Enter → camera speaks within ~2 s.

**Neural voice (Piper)**
- `cam_say.sh` now prefers **Piper** (`en_GB-alan-medium`, calm British male) for far more natural
  speech, falling back to espeak-ng if Piper/voice are missing.
- Piper standalone binary at `~/piper_dist/piper/` (needs `LD_LIBRARY_PATH=.`), voice model at
  `~/voices/en_GB-alan-medium.onnx` (+ `.json`). Outputs 22050 Hz → ffmpeg resamples to 16 kHz →
  played at rate-arg 8000 (the 2x-DAC rule).
- (pip install piper-tts failed on this box: Python 3.14 has no onnxruntime wheels + PEP 668; the
  prebuilt binary sidesteps both.)

New scripts in `scripts/`: `cam_poll.py`, `cam_say_server.py` (and `cam_say.sh` updated for Piper).

## 9. Roadmap (owner requests, not yet done)
- **"Black Liquid Glass" theme**: cohesive Apple-glass design/theme across ALL dashboard views.
- **Motion recording + zones (advanced)**: Frigate on `rtsp://10.0.0.22:6667/blinkhd` (on Jarvis or
  HA), event recording, zones, snapshots → HA. Optional Coral TPU for AI person/pet detection.
- **LED / status-LED control via HA**: the factory tool exposes `ftest led`, `ftest irled`,
  `ftest ircut` — RE these and expose as HA switches/lights (IR illuminator, status LED, IR-cut).
- **Non-disruptive playback**: LD_PRELOAD resident player in fepe so announcements don't drop video.
- **Persist cloud blackhole** safely (only if a non-telnet-critical boot hook is available).
