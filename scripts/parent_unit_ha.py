import serial, time, re, json, os, urllib.request

PORT = os.environ.get("PU_PORT", "COM7")
BAUD = int(os.environ.get("PU_BAUD", "115200"))
HA_URL = os.environ.get("HA_URL", "http://10.0.0.165:8123")
TOKEN = open(os.path.join(os.path.expanduser("~"), "pu_ha.token")).read().strip()
LOG = os.path.join(os.path.expanduser("~"), "uart.log")
LOG_CAP = 10 * 1024 * 1024  # rotate at 10MB

BAT_EMPTY = 810.0
BAT_FULL = 890.0

def post(eid, state, attrs):
    body = json.dumps({"state": state, "attributes": attrs}).encode()
    req = urllib.request.Request(HA_URL + "/api/states/" + eid, data=body, method="POST",
          headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=8).read(); return True
    except Exception:
        return False

def is_spam(line):
    s = line.strip()
    if s == "": return True
    if s in ("check frame timeout!", "*** req info=0 ***", "*** cam 0 lostlink icon ***", "*** diff=0 ***"):
        return True
    noise = sum(1 for c in s if c in "sMw<>0123456789, ")
    return len(s) >= 8 and noise / len(s) > 0.82

st = {"last_lost": 0.0, "last_pkt": 0.0, "bat_raw": None, "reboots": 0,
      "last_link_state": "", "last_pkt_hex": "", "boot_ts": ""}

def open_log():
    try:
        if os.path.exists(LOG) and os.path.getsize(LOG) > LOG_CAP:
            bak = LOG + ".1"
            if os.path.exists(bak): os.remove(bak)
            os.rename(LOG, bak)
    except Exception:
        pass
    return open(LOG, "a", buffering=1, encoding="utf-8", errors="replace")

logf = open_log()

def logline(line):
    global logf
    try:
        logf.write(time.strftime("%H:%M:%S ") + line + "\n")
        if logf.tell() > LOG_CAP:
            logf.close(); logf = open_log()
    except Exception:
        pass

def open_serial():
    s = serial.Serial(); s.port = PORT; s.baudrate = BAUD; s.timeout = 0.2
    s.dtr = False; s.rts = False; s.open()
    try: s.setDTR(False); s.setRTS(False)
    except Exception: pass
    return s

ser = open_serial()
buf = b""; last_push = 0.0

while True:
    try:
        data = ser.read(4096)
    except Exception:
        time.sleep(2)
        try: ser = open_serial()
        except Exception: pass
        continue
    now = time.time()
    if data:
        buf += data
        while b"\n" in buf:
            i = buf.index(b"\n"); line = buf[:i].decode("utf-8", "replace").rstrip("\r"); buf = buf[i+1:]
            low = line.lower()
            if "lostlink" in low or "check frame timeout" in low:
                st["last_lost"] = now
            if "spiboot_ver" in low:
                st["reboots"] += 1; st["boot_ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
            m = re.search(r"battery level=(\d+)", line)
            if m: st["bat_raw"] = int(m.group(1))
            ls = re.search(r"<(\d+,\d+,\d+)>", line)
            if ls: st["last_link_state"] = ls.group(1)
            if re.search(r"\*{3,}\s*\d+\s*\*{3,}", line):
                st["last_pkt"] = now
            hx = re.match(r"^\s*([0-9a-fA-F]{1,2}(?: [0-9a-fA-F]{1,2}){6,})\s*$", line)
            if hx:
                st["last_pkt_hex"] = hx.group(1).strip(); st["last_pkt"] = now
            if not is_spam(line):
                logline(line)
        if len(buf) > 16384: buf = buf[-2048:]
    if now - last_push >= 10:
        last_push = now
        link = "lost" if (now - st["last_lost"] < 8) else ("connected" if st["last_pkt"] else "searching")
        post("sensor.parent_unit_cam_link", link, {
            "friendly_name": "Parent Unit – Camera Link", "icon": "mdi:cctv",
            "link_state": st["last_link_state"], "reboots_seen": st["reboots"],
            "last_rf_packet": st["last_pkt_hex"], "last_boot": st["boot_ts"]})
        post("sensor.parent_unit_last_update", time.strftime("%Y-%m-%d %H:%M:%S"),
             {"friendly_name": "Parent Unit – Last Update", "icon": "mdi:clock-outline"})
        if st["bat_raw"] is not None:
            pct = max(0, min(100, int((st["bat_raw"] - BAT_EMPTY) / (BAT_FULL - BAT_EMPTY) * 100)))
            post("sensor.parent_unit_battery_raw", st["bat_raw"],
                 {"friendly_name": "Parent Unit – Battery (raw ADC)", "icon": "mdi:battery"})
            post("sensor.parent_unit_battery", pct,
                 {"friendly_name": "Parent Unit – Battery", "unit_of_measurement": "%",
                  "device_class": "battery", "state_class": "measurement"})
