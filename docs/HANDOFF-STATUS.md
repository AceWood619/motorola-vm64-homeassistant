# VM64 Camera → HA — Handoff / Status

_Last updated: 2026-10-29 ~00:35 UTC_

## Standing orders (unchanged)
- Keep telnet root on the camera (root/babycam123). Do NOT pair to Hubble/Motorola app. No cloud firmware updates.
- UART unsoldered = no recovery; no wifi/flash gambles that could brick the camera.
- Parent-unit talkback may be sacrificed for now (flash later via UART).
- Confirm audio by ear/eye. Begin each reply with a [HH:MM AM/PM UTC] marker. Keep this file + GitHub repo updated.

## SSH access to HA box — SOLVED (2026-10-29)
- The HA box (10.0.0.165) runs the **Advanced SSH & Web Terminal** add-on (slug a0d7b954_ssh).
- Root cause it was failing: the add-on's SSH port was set to **22**, already in use on the host → daemon crash-looped ("Bind to port 22 ... Address in use"), so the add-on never listened and no key worked.
- Fix: changed the add-on SSH port to **22222** and started it.
- Login: **user `hassio`, port 22222**, key = `~/.ssh/ha_cam` (pubkey `...R2JNa claude-cam`) on Jarvis. `hassio` has passwordless **sudo** → full root.
- From Jarvis: `ssh -i ~/.ssh/ha_cam -p 22222 hassio@10.0.0.165` (then `sudo` for /homeassistant).
- HA config dir inside the add-on: **/homeassistant** (symlink /config); root-owned 700, so use sudo.
- The "app errors" Mason saw were mainly the **desktop browser being logged out of HA** (stale dashboard → "Could not load Home Assistant"). After login the dashboard loads fine.

## Done this session (2026-10-29)
1. **Never talk through the kids TV** — the only kids-TV ref was the camera-OFFLINE fallback in automation `junior_school_morning` (tts.speak → media_player.kids_room_streaming_stick). Replaced so that branch sets `input_text.kids_camera_say` (routes to the camera; phone notify still fires). 0 kids-TV refs remain. Backup: automations.yaml.bak-tvroute-*. automation.reload=200, no errors.
2. **Black Liquid Glass theme** at `/homeassistant/themes/black_liquid_glass.yaml` (theme-only: near-black base, translucent glass cards, icy-cyan glow, 26px radius; dark+light). YAML valid. reload_themes=200; set as backend default via set_theme=200 (confirms registered).
   - **card-mod is NOT installed**, so this is translucent "dark glass," not true `backdrop-filter` frosted blur. True blur = opt-in later (HACS card-mod, or one global CSS resource — avoid per-card card-mod that broke 288 cards before).
   - Mason's profile is pinned to "Ace Dark"; to SEE it he picks it in Profile → Theme (one tap). Backend default already = Black Liquid Glass (affects backend-selected kiosk views).

## External access (earlier run)
- HA reachable over Tailscale (http://100.97.7.107:8123) — working.
- Temporary public Cloudflare tunnel `cftunnel` still on Jarvis (redundant). Recommend `docker rm -f cftunnel` once Mason confirms.

## Still open / possible next
- True frosted blur (card-mod or CSS-injection) — opt-in.
- Frigate motion/recording + zones (mosquitto MQTT already on Jarvis 10.0.0.60:1883; must use go2rtc restream, never direct camera RTSP which reboot-looped it).
- media_player entity for the camera (DLNA/Snapcast bridge).

## Working features (recap)
Local cloud-free camera speaker (vm64_play3, 16kHz @ arg 8000 for 2× DAC), Piper neural voice, HA dashboard talkback + quick phrases, iPhone Assist voice command ("tell the kids …" → camera), file/URL playback, LED/IR control, morning reminder → camera (never kids TV), GitHub documented.
