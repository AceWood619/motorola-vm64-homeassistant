# UART & pinout (Motorola VM64 Connect BU — Lux65 board)

## Adapter
- Any USB‑TTL adapter (CP2102 / CH340 / FTDI) set to **3.3 V logic**.
- Connect **only GND, camera‑TX→adapter‑RX, camera‑RX→adapter‑TX**. **Do not connect VCC/3V3/5V** — the camera is self‑powered off its own 5 V.

## Finding the pads
The debug UART on this board is a short pad row near the SoC / speaker pads. There is no silkscreen
`TX/RX`. Method that avoids guessing:
1. Beep continuity from a candidate pad to the **−** leg of the 330 µF cap to find **GND**.
2. Wire GND, connect the adapter's **RX** as a probe, open a serial terminal at **115200 8N1**.
3. Power the camera; the pad that streams readable boot text is **camera‑TX** → adapter RX.
4. Find **camera‑RX** by moving the adapter's **TX** to the remaining candidate and pressing keys —
   when `y` during boot drops you into test mode, you've got it.

> ⚠️ The solder pads are tiny and the wires are fragile. Once you have wireless root (telnet/ssh),
> treat UART as emergency‑only and stop stressing the joints.

## Boot banner (for reference)
```
Cloud39Ev300 spinandboot V1.2.03
...
Anyka Linux Kernel Version: 1.1.12 / Linux 3.4.35
Machine: CLOUD39EV3_AK3918EV300_MNBD
...
----- Press 'y' or 'Y' to enter test mode -----
--> You had entered to test mode...
[root@anyka ~]$      <-- root, no password
```

## Do NOT touch
The shielded can with `SWCLK`/`SWDIO` pads is the **nRF52810** that runs the 2.4 GHz FHSS link to the
parent handheld monitor. Leave it alone or you lose the parent unit.
