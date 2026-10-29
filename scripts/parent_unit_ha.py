import serial, time, re, json, os, urllib.request

PORT = os.environ.get("PU_PORT", "COM7")
BAUD = int(os.environ.get("PU_BAUD", "115200"))
HA_URL = os.environ.get("HA_URL", "http://10.0.0.165:8123")
TOKEN = open(os.path.join(os.path.expanduser("~"), "pu_ha.token")).read().strip()
LOG = os.path.join(os.path.expanduser("~"), "uart.log")

# battery ADC reference points from boot log
BAT_EMPTY = 810.0   # poweroff threshold
BAT_FULL = 890.0    # ~ level3 region

def post(eid, state, attrs):
    body = json.dumps({"state": state, "attributes": attrs}).encode()
    req = urllib.request.Request(HA_URL + "/api/states/" + eid, data=body, method="POST",
          headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=8).read()
        return True
    except Exception as e:
        return False

st = {"last_lost": 0.0, "last_pkt": 0.0, "bat_raw": None, "boot": 0.0, "reboots": 0}
logf = open(LOG, "ab", buffering=0)

def open_serial():
    s = serial.Serial()
    s.port = PORT; s.baudrate = BAUD; s.timeout = 0.2
    s.dtr = False; s.rts = False
    s.open()
    try: s.setDTR(False); s.setRTS(False)
    except Exception: pass
    return s

ser = open_serial()
print("parent_unit_ha: reading %s@%d -> %s" % (PORT, BAUD, HA_URL), flush=True)
buf = b""
last_push = 0.0

while True:
    try:
        data = ser.read(4096)
    except Exception as e:
        time.sleep(2)
        try: ser = open_serial()
        except Exception: pass
        continue
    now = time.time()
    if data:
        logf.write(data)
        buf += data
        while b"\n" in buf:
            i = buf.index(b"\n"); line = buf[:i].decode("utf-8", "replace"); buf = buf[i+1:]
            low = line.lower()
            if "lostlink" in low or "check frame timeout" in low:
                st["last_lost"] = now
            if "spiboot_ver" in low or "enter normal mode" in low:
                st["boot"] = now; st["reboots"] += 1
            m = re.search(r"current battery level=(\d+)", line)
            if m: st["bat_raw"] = int(m.group(1))
            if re.search(r"\*{3,}\s*\d+\s*\*{3,}", line) or line.strip().startswith("<0,"):
                st["last_pkt"] = now
        if len(buf) > 16384:
            buf = buf[-2048:]
    if now - last_push >= 10:
        last_push = now
        # link: 'lost' if a lost/timeout signal in the last 8s, else 'connected'
        link = "lost" if (now - st["last_lost"] < 8) else ("connected" if st["last_pkt"] else "unknown")
        post("sensor.parent_unit_cam_link", link,
             {"friendly_name": "Parent Unit – Camera Link", "icon": "mdi:cctv"})
        post("sensor.parent_unit_last_update", time.strftime("%Y-%m-%d %H:%M:%S"),
             {"friendly_name": "Parent Unit – Last Update", "icon": "mdi:clock-outline"})
        if st["bat_raw"] is not None:
            pct = max(0, min(100, int((st["bat_raw"] - BAT_EMPTY) / (BAT_FULL - BAT_EMPTY) * 100)))
            post("sensor.parent_unit_battery_raw", st["bat_raw"],
                 {"friendly_name": "Parent Unit – Battery (raw ADC)", "icon": "mdi:battery"})
            post("sensor.parent_unit_battery", pct,
                 {"friendly_name": "Parent Unit – Battery", "unit_of_measurement": "%",
                  "device_class": "battery", "state_class": "measurement"})
