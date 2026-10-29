# Parent Unit — graphics/resource reverse engineering (from flash dump)

_Working notes, 2026-10-29. Dump: pu_flash_1.bin, md5 026322c21cd95440955ebd74da2d9764 (golden backup)._

## Confirmed
- **Graphics = uncompressed RGB565**, stored as individual icons/images with **solid-color backgrounds** (seen: `0x2222` dark, `0xAAAA` light, green field). Directly editable in place — no compression on the image data.
- Main image/resource region: **`0xA8000 – 0xF0000`** (288 KB, low entropy, "image-like").
- Rendered real graphics successfully: the **"no-camera / lost-signal" box-X status icons + labels** decode cleanly (see decoded_icons.png). Width per icon ~50–100 px; **each icon has its own width** (not a uniform grid), so they must be parsed via the resource table, not a fixed stride.
- Resource/table structures:
  - `~0x171880`: 8-byte entries `[id/char:4][val:4]` (vals 0x800/0x900/0x750… — looks like a font/glyph or resource index).
  - `0x170ff4`: sequential ID list (…0xb4,0xb5,0xb6… = 180,181,182…).
  - `0x171898`: entry with count **180** (matches boot log "total icons=180").
- `0x22222222` background runs mark icon slots around `0xC0000–0xE0000`, spaced ~10 KB.
- **No single full-screen 480×272 "Motorola Nursery" bitmap exists** → the boot splash is **composed** (a logo graphic + font-rendered text over a background). So "replace the logo" = replace the Motorola logo icon/element (+ maybe text), not swap one big image.

## Still to do (the rebuild)
1. Fully decode the resource index (entry layout: id, offset, width, height, bg) → map all ~180 icons to exact (offset, w, h).
2. Render every icon; identify the Motorola-branded element(s) (logo + "nursery" text).
3. Build Synapse replacements at the **exact same offset/width/height/format** (RGB565, same byte length) so nothing shifts.
4. Splice into a copy of the golden dump → `pu_flash_synapse.bin`.
5. Flash with the RP2040 serprog path (`-w`), re-read to byte-verify, then **Mason confirms on the LCD** (the one step Claude can't see).

## Scope note
- **Graphics rebuild: feasible** (format understood, uncompressed, backed up).
- **"Rebuild all functions" (firmware code/behavior): out of safe scope** for now — that's rewriting AK3750 RTOS ARM code (RF/UI/audio), high-risk and low-confidence; not something to flash blind. Revisit only after much deeper code RE.

## HA integration status
Live entities in HA: `sensor.parent_unit_cam_link`, `sensor.parent_unit_battery` (100%), `sensor.parent_unit_battery_raw`, `sensor.parent_unit_last_update`; dashboard card added to the jarvis-hud Home view. Live updates require the parent UART connected to the PC (COM7) running parent_unit_ha.py (auto-starts at logon). Permanent always-on = embedded ESP tap (deferred).
