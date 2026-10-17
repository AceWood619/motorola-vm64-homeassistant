# Coord note for SynapseOS (copy into AceWood619/SynapseOS coord/ board)

**New HA device available: Kids Bedroom Camera (Motorola VM64 / Anyka AK3918EV300)**

- HA camera entity: `camera.kids_bedroom` ("Kids Bedroom Camera"), area `kids_room`.
- Local stream (no cloud): `rtsp://<cam-ip>:6667/blinkhd` — H.264 video + PCMA mic.
- Lives on stock firmware (rooted, on Wi-Fi, reboot-proof). Parent monitor still works.
- Surface it in the Synapse "Remote" room-channel card for the kids room (video tile + mic).
- Sensors coming to the SAME HA device via MQTT discovery (identifiers `vm64_kids_cam`):
  temperature, and motion/sound binary_sensors. Bind them in Synapse as they appear.
- 2-way talkback (speaker) is under investigation; mic is already live.
