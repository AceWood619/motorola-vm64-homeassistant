# Feasibility summary: OpenIPC/Thingino on AK3918EV300 — NO (as of Oct 2026)

**Verdict: stay on stock firmware + add RTSP. Do not flash.**

- OpenIPC lists the AK3918EV300 as "no board to develop on" — no build for any Anyka chip;
  the Anyka toolchain download 404s (OpenIPC firmware issue #1541). Thingino is Ingenic-only.
- No open MIS2003 DVP sensor driver and no 8189fs Wi-Fi driver for Anyka → a self-built
  image boots with **no video and no Wi-Fi**.
- `spinandboot V1.2.03` is not U-Boot and has **no documented unbrick path**.
- Parent-unit link almost certainly breaks (video comes from the Anyka SoC → nRF52810).
- Proven alternative: stock firmware already exposes `rtsp://<ip>:6667/blinkhd`
  (same `/blinkhd` endpoint as sibling Hubble/Motorola cams).

Key sources: openipc.org/cameras/vendors/anyka • OpenIPC firmware #1541, #1970 •
ipctool #217/#134/#228 • elektroda.com/news/news4155743.html (piotr_go GNCC GC2) •
github.com/Nemobi/ak3918ev300v18 • github.com/Erliz/hubble-sniffer
