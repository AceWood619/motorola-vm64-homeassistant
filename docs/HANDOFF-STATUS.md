# VM64 Camera → HA — Handoff / Status

_Last verified: 2026-10-28 ~19:45 UTC (scheduled routine run)_

## Standing orders (unchanged)
- Keep telnet root on the camera (root/babycam123). Do NOT pair to Hubble/Motorola app. No cloud firmware updates.
- UART is unsoldered = no recovery path, so no wifi/flash gambles that could brick the camera.
- Parent-unit talkback may be sacrificed for now (Mason: "I can flash that one later via UART").
- Only benign changes. Confirm audio by ear/eye. Begin each reply with a [HH:MM AM/PM UTC] marker. Keep this file + GitHub repo updated.

## Verified healthy this run (read-only probe, no changes made)
- **Jarvis** (acewood-MacBookPro11-1, 10.0.0.60 / tailscale 100.126.208.91): up, load ~2.0.
- **Camera** (10.0.0.22): pings up.
- **cam-say / cam-poll / cam-led-poll** systemd services: all `active`.
- **HA** (10.0.0.165:8123 local): HTTP 200.
- **HA via Tailscale** (100.97.7.107:8123, "homeassistant-2"): HTTP 200 — WORKING.
- iPhone (iphone173, 100.89.23.26) active on the tailnet.
- Jarvis docker stack up: mosquitto (MQTT), grafana, influxdb, nodered, esphome, cync-lan, code-server, filebrowser, portainer, searxng, wyoming-openwakeword, mariadb.

## External access
- Mason's intended path is **Tailscale** (http://100.97.7.107:8123). It is reachable now from Jarvis (HTTP 200) and his iPhone is on the tailnet — so Tailscale external access appears to be working again.
- A **temporary public Cloudflare quick-tunnel** container (`cftunnel`) is still running on Jarvis and exposes the whole HA instance (incl. the kids-bedroom camera) on a public URL: https://blind-sporting-oasis-fountain.trycloudflare.com . Restart policy = none; it was (re)created 2026-10-28 18:54 UTC.
  - Since Tailscale works, this public tunnel is **redundant and an unnecessary public exposure**. Recommend tearing it down: `docker rm -f cftunnel` on Jarvis. NOT removed automatically this run (needs Mason's OK — it's an external change he didn't request).

## Still blocked (need Mason / a non-SSH method)
Mason's guidance: do NOT SSH into the HA box and edit config files directly ("you can't just ssh from my pc like u always do and add in the config files"), and he reported errors in the HA app.
1. **"Black Liquid Glass" frosted theme** as a real theme file + global TV-route fix (repoint `rest_command.vm64_camera_talkback` → camera /say). Needs write access to HA `/config`. Current workaround in place: "Apple Dark" built-in theme (dashboard is working).
2. **Frigate motion/recording + zones**: needs MQTT exposed to HA + a suitable host. Note: `mosquitto` is already running on Jarvis (10.0.0.60:1883) — may be usable as the broker. Frigate was previously REMOVED because it reboot-looped the camera (exhausted RTSP connections); any retry must use a go2rtc restream, not direct camera RTSP.

## Open question for Mason
- What are the exact errors the HA app is showing? (needed to pick the right non-SSH path — File Editor / Studio Code Server add-on UI, or he pastes snippets I provide.)
- OK to tear down the redundant public Cloudflare tunnel now that Tailscale works?

## Working features (recap)
Local cloud-free speaker playback (vm64_play3, 16kHz authored @ arg 8000 for the 2× DAC), Piper neural voice, HA dashboard talkback + quick phrases, iPhone Assist voice command ("tell the kids …"), file/URL playback, LED/IR control, morning-reminder routed to camera speaker (never the kids TV), Apple Dark theme, GitHub repo documented.
