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
