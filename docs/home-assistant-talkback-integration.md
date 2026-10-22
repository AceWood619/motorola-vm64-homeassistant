# Home Assistant camera talkback integration

This document describes the local integration pattern without publishing a camera address, dispatcher URL, credentials, or Home Assistant token. Keep those values in the existing local configuration/secrets files; do not commit them to this repository.

## Audio and video

- The camera's stock RTSP stream provides H.264 video and PCMA/16000 mono microphone audio.
- The go2rtc stream alias used by the dashboard is `kids_bedroom_camera`.
- The camera iframe must request both media types, for example with the go2rtc stream page and `media=video,audio`. A video-only request can make the dashboard appear to have lost microphone audio even when the RTSP stream still carries it.
- Browser autoplay policies may keep audio muted until the user interacts with the camera card. Verify the card's mute control before changing the camera stream configuration.

## Talkback route

The intended route is:

1. Home Assistant's intercom selector chooses **Kids room camera**.
2. Home Assistant calls `rest_command.vm64_camera_talkback` on the local dispatcher.
3. The dispatcher routes the request to the dedicated `kids_camera` output target.
4. The target invokes the native `vm64_talkback` player to send raw PCM audio to the camera speaker.

The target is deliberately **not a primary sink** and must not be included in whole-house/broadcast audio groups.

## Safety guardrails

- Keep `override_quiet: false` so the existing baby-asleep/quiet guard is respected.
- Keep the camera target at low DAC volume and a short maximum duration (currently 20 seconds).
- Do not expose the dispatcher endpoint publicly; keep it on the trusted local network.
- Do not put real host/IP values, passwords, API keys, tokens, camera credentials, firmware dumps, or local secrets files in this repository.
- Do not use the camera's undocumented `ftest` tone-generation commands to test the speaker.
- A live speaker test should only be done when the baby monitor is not in use, because it produces audible sound in the room.

## Verification checklist

- [ ] Home Assistant configuration check passes after any YAML change.
- [ ] The dispatcher service is active and the talkback REST command is registered.
- [ ] The intercom selector includes **Kids room camera**.
- [ ] The go2rtc stream reports video and audio tracks.
- [ ] The camera card requests `media=video,audio` and is not muted in the browser.
- [ ] Only after confirming the room is safe to test, verify audible talkback at low volume.
