# VM64 Camera Talkback Player

## Purpose

A small native player for the Motorola VM64 / Anyka AK3918EV300 camera speaker. It accepts **raw PCM**, not a WAV container:

- 8,000 Hz sample rate
- mono input
- signed 16-bit little-endian samples
- player duplicates each mono sample into the stereo output buffer expected by the vendor AO demo
- DAC volume is 0–6; the Home Assistant bridge uses volume 2

The player uses the vendor `ak_ao` audio-output API, signals end-of-stream, waits briefly for the driver to finish, then disables the speaker and closes the handle. It does not use the camera's undocumented `ftest` tone generator.

## Build

The build is reproducible when the Anyka SDK and cross-toolchain are present under `/tmp/vm64-talkback-research`:

- `toolchain/arm-anykav200-crosstool/`
- `ak3918ev300v18/platform/libplat/`

The toolchain runs in a 32-bit Debian container because the legacy compiler needs 32-bit host libraries. Run:

```sh
docker build -t vm64-anyka-toolchain:local -f scripts/talkback-toolchain.Dockerfile .
scripts/build_talkback_player.sh
```

The build uses the SDK's AO/common/thread/IPCSRV static libraries and the SDK audio-filter shared library. Vendor headers and libraries are not copied into this repository.

## Home Assistant integration design

- The camera microphone's RTSP source is registered in go2rtc as `kids_bedroom_camera`.
- Dashboard camera cards use the go2rtc stream page with `media=video,audio`; the underlying RTSP stream was verified to expose H.264 video and PCMA audio.
- The dispatcher target is `kids_camera`, intentionally **not** a primary sink and not part of whole-house targets.
- Camera talkback is limited to 20 seconds and uses low DAC volume 2.
- The dedicated Home Assistant intercom option is **Kids room camera**. Its request uses `override_quiet: false`, so the existing baby-asleep guard is respected.

## Verification and safety status

- Cross-compilation succeeded for 32-bit ARM.
- The player was installed on the camera at `/usr/bin/vm64_talkback`.
- Running it without arguments returned usage text; the binary and loader work without opening the speaker.
- The dispatcher was tested with a harmless two-byte transfer; no sound was played.
- Home Assistant configuration validation passed; the dispatcher service is active after restart.
- Home Assistant exposes the `rest_command.vm64_camera_talkback` service and the `Kids room camera` intercom option.
- The live RTSP stream was verified to provide H.264 video and PCMA/16000 mono audio; dashboard camera cards use `media=video,audio`.
- Live audits found no missing or unavailable entity references across the three reviewed dashboards.
- **A live speaker test has not been performed** to avoid unexpected sound in the baby's room. Test only when the monitor is not in use. Do not use `ftest` tone-generation commands.
