# Phase 3 — Dump & reverse the parent-unit firmware

## The flash chip
Boot log: `SPI FLASH: id=0x0016400b`. Decoding the JEDEC bytes (`0B 40 16`):
- **Manufacturer 0x0B = XTX Technology**
- Memtype 0x40 = 25-series SPI NOR
- **Capacity 0x16 = 4 MB (32 Mbit)**

→ Almost certainly an **XTX XT25F32B** (or 25Q32-compatible) **4 MB 3.3 V SPI NOR**, in the 8-pin SOIC next to the SoC.

## Hardware needed
- **CH341A** USB programmer **+ SOIC-8 (SOP8) test clip**.
- ⚠️ **3.3 V only.** Many cheap CH341A boards drive the SPI lines at ~5 V in 25xx mode — that can stress a 3.3 V flash/SoC. Use a 3.3 V-modded CH341A (common mod) or a 3.3 V-safe programmer.

## Dump procedure
1. **Board powered OFF.** Clip the SOIC-8 onto the flash (pin 1 = the dot/bevel; match clip pin 1).
2. Read it **three times** and compare (consistency = good contact):
   ```
   flashrom -p ch341a_spi -r pu_flash_1.bin
   flashrom -p ch341a_spi -r pu_flash_2.bin
   flashrom -p ch341a_spi -r pu_flash_3.bin
   fc /b pu_flash_1.bin pu_flash_2.bin   (Windows)   # or cmp on Linux
   ```
   If flashrom doesn't auto-ID the XTX part, force a compatible profile:
   `flashrom -p ch341a_spi -c "XT25F32B" -r pu_flash.bin`  (or a `W25Q32`/`GD25Q32` equivalent).
   Expected size: **4194304 bytes (4 MB)**.
3. If reads are inconsistent/garbage, the SoC is back-powering/contending — then either hold the SoC in reset, lift the flash VCC pin, or desolder the flash to dump off-board.

## Reverse-engineering the image (once dumped)
- `binwalk pu_flash.bin` — find the `spiboot` loader, the compressed "BIOS", LCD icon/resource blobs (boot mentioned `total icons=180`), fonts, strings.
- `strings -n 6 pu_flash.bin | less` — look for the BK2425 setup, hop table, Factory/Product ID handling, the "req info"/packet formats we saw on UART.
- Goal: understand the **BK2425 channel/hop + packet protocol** (feeds Phase 2), and whether we can safely patch/rebuild firmware later (reflash = our true "root" of this RTOS device).

## Safety
Keep `pu_flash_*.bin` as the golden backup before ANY write. We only READ until the image is fully understood. The parent unit is the spare we can risk, but a verified backup means we can always restore.


## Phase 3 goal: replace the boot splash with a SYNAPSE logo
The Motorola boot/splash logo is a bitmap in the SPI flash (boot log reports `total icons=180` — the LCD resource region). Panel is **480×272 RGB** (id 0x5180), so the splash is almost certainly a 480×272 image, likely stored as raw **RGB565** or in Anyka's icon/resource container.
Procedure (after we can dump+reflash):
1. Dump `pu_flash.bin` (above) and keep the golden backup.
2. `binwalk`/hex-search for the 480×272 image region (look near the icon table; RGB565 480×272 = 261,120 bytes; or a packed/compressed resource blob).
3. Render a **Synapse** logo at 480×272, convert to the same format/stride, splice it into the image at the exact offset (same byte length).
4. Reflash and verify the golden backup still restores.
Note: keep the replacement image the **same byte size & format** as the original so offsets/tables don't shift. We'll confirm the exact format from the dump.


## Programmer: RP2040 + pico-serprog (no CH341A/clip needed)
Mason has an RP2040 ("RP2040 USB" stick). Built `pico-serprog.uf2` from kukrimate/pico-serprog (delivered in chat). Source-confirmed pins:
`#define SPI_CS 5 / SPI_MISO 4 / SPI_MOSI 3 / SPI_SCK 2`  → **GP5=CS, GP4=MISO, GP3=MOSI, GP2=SCK**.

Wiring (RP2040 → the parent's 8-pin SOIC SPI NOR; see rp2040_flash_wiring.png in chat):
- GP2 → pin 6 CLK   • GP3 → pin 5 DI(MOSI)   • GP4 → pin 2 DO(MISO)   • GP5 → pin 1 CS
- 3V3 → pin 8 VCC   • GND → pin 4 GND        • pins 3 (WP) & 7 (HOLD) left n/c
- Parent unit powered **OFF** during flashing (RP2040's 3V3 powers just the flash). Pin 1 = the dot.

Steps:
1. Hold BOOT on the RP2040, plug into USB, copy `pico-serprog.uf2` to the RPI-RP2 drive.
2. Wire per above to the flash legs.
3. On a Linux host where the RP2040 enumerates (Jarvis easiest, or PC via WSL+usbipd): `sudo apt install flashrom`.
4. Dump 3× and compare (keep the first as the golden backup):
   ```
   flashrom -p serprog:dev=/dev/ttyACM0:115200 -r pu_flash_1.bin
   flashrom -p serprog:dev=/dev/ttyACM0:115200 -r pu_flash_2.bin
   flashrom -p serprog:dev=/dev/ttyACM0:115200 -r pu_flash_3.bin
   cmp pu_flash_1.bin pu_flash_2.bin && cmp pu_flash_2.bin pu_flash_3.bin && echo CONSISTENT
   ```
   (Optional `,spispeed=8M` in the dev string. If the XTX chip isn't auto-detected, run once with no -r to see flashrom's message, then force a 25Q32-compatible with `-c`.)
5. Then: locate the Motorola splash bytes in the dump, splice in the 480×272 Synapse image (same offset/size/format), and `-w pu_flash_synapse.bin` (keep the backup safe).


## DUMP COMPLETE — 2026-10-29 (RP2040 + pico-serprog, pure-Python serprog client)
- Wiring verified: JEDEC ID read 3× = `0B 40 16` (XTX, 25-series, 4 MB) — matches boot log. Powered SoC did NOT contend (consistent reads).
- Dumped 4 MB twice; **byte-identical, md5 `026322c21cd95440955ebd74da2d9764`** → golden backup `pu_flash_1.bin` / `pu_flash_2.bin` on Mason's PC. (Scripts: serprog_flash.py / pu_analyze.py / pu_map.py / pu_find_splash.py on his PC.)
- Structure: header `ANYKAS3C` @0x0 (Anyka); firmware in first ~1.5 MB, rest 0xFF.
- **Images are UNCOMPRESSED** (low-entropy block 0xA8000–0xF0000). Editable in place — no decompress needed.
- 480×272 image descriptors (`E0 01 10 01`) found @~0xAB740 and a 60-byte-stride table @~0x115B80. Splash is a 480×272 image in the 0xA8000 region.
- NEXT: render the region to locate the Motorola splash exactly, build a same-size/format Synapse replacement, splice, and write back with `-w`. (Easier once the dump is accessible to Claude for rendering — connect the folder or transfer.)
