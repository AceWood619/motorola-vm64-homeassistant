#!/usr/bin/env python3
# VM64 -> Home Assistant MQTT-discovery bridge.
#
# Publishes ONE Home Assistant MQTT device ("vm64_kids_cam") that groups:
#   - Temperature  (read with the stock factory tool: `ftest tempvalue`)
#   - Wi-Fi Link Quality (/proc/net/wireless)
#   - Last Boot    (/proc/uptime -> timestamp)
#   - Online       (connectivity binary_sensor)
#
# No MQTT broker credentials are needed: it calls Home Assistant's
# `mqtt.publish` service over the REST API with a long-lived token, and HA
# forwards the retained discovery + state messages to its own broker.
#
# TEMPERATURE: the Anyka AK3918EV300 reads an NTC on its ADC (/dev/ak_adc)
# and the app applies a proprietary formula + factory offset. You do NOT need
# to reverse that: the stock factory-test binary already does it ->
#     ftest tempvalue
#       Actual  = 25.1      (raw NTC -> Celsius)
#       Display = 22.1      (Actual + temprature_offset/10 ; offset in tenths)
# We publish the "Display" value. `ftest tempoffset` prints the stored offset.
#
# Run it as a systemd service on an always-on LAN host (see install notes).
import socket, time, json, subprocess, urllib.request, datetime, re, sys

CAM = "YOUR_CAM_IP"             # e.g. the camera's DHCP-reserved LAN IP
TELNET_USER = "root"
TELNET_PASS = "YOUR_ROOT_PASS"  # the password you set with `passwd root`
INTERVAL = 120                  # seconds between polls

# How to reach Home Assistant. Either hardcode here, or export HA_URL/HA_TOKEN.
import os
HA_URL = os.environ.get("HA_URL", "http://YOUR_HA_IP:8123")
HA_TOKEN = os.environ.get("HA_TOKEN", "YOUR_LONG_LIVED_TOKEN")

def ha_post(path, body):
    req = urllib.request.Request(HA_URL + path, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + HA_TOKEN, "Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=30).read().decode()

def pub(topic, payload, retain=True):
    p = payload if isinstance(payload, str) else json.dumps(payload)
    return ha_post("/api/services/mqtt/publish", {"topic": topic, "payload": p, "retain": retain, "qos": 0})

DEV = {"identifiers": ["vm64_kids_cam"], "name": "Kids Bedroom Camera", "manufacturer": "Motorola",
       "model": "VM64 Connect (Anyka AK3918EV300)", "sw_version": "stock"}
AV = {"availability_topic": "vm64cam/status", "payload_available": "online", "payload_not_available": "offline"}

def discovery():
    b = "homeassistant"
    cfgs = {
      b + "/sensor/vm64_kids_cam/temp/config": {"name": "Temperature", "unique_id": "vm64_kids_cam_temp",
          "device_class": "temperature", "unit_of_measurement": "°C", "state_class": "measurement",
          "state_topic": "vm64cam/temperature", "device": DEV, **AV},
      b + "/sensor/vm64_kids_cam/wifi/config": {"name": "Wi-Fi Link Quality", "unique_id": "vm64_kids_cam_wifi",
          "state_class": "measurement", "state_topic": "vm64cam/wifi", "entity_category": "diagnostic",
          "icon": "mdi:wifi", "device": DEV, **AV},
      b + "/sensor/vm64_kids_cam/boot/config": {"name": "Last Boot", "unique_id": "vm64_kids_cam_boot",
          "device_class": "timestamp", "state_topic": "vm64cam/boot", "entity_category": "diagnostic",
          "device": DEV, **AV},
      b + "/binary_sensor/vm64_kids_cam/online/config": {"name": "Online", "unique_id": "vm64_kids_cam_online",
          "device_class": "connectivity", "state_topic": "vm64cam/online", "payload_on": "ON", "payload_off": "OFF",
          "device": DEV, **AV},
    }
    for t, c in cfgs.items():
        pub(t, c)

def cam_cmd(cmd, wait=7):
    c = socket.create_connection((CAM, 23), timeout=8)
    c.settimeout(2)
    def drain(t):
        end = time.time() + t
        o = b""
        while time.time() < end:
            try:
                x = c.recv(65536)
                if x:
                    o += x
            except Exception:
                pass
        return o
    drain(1.0)
    c.sendall((TELNET_USER + "\r\n").encode())
    drain(1.0)
    c.sendall((TELNET_PASS + "\r\n").encode())
    drain(1.5)
    c.sendall((cmd + "\r\n").encode())
    out = drain(wait)
    c.close()
    return out.decode("latin1", "replace")

def read_all():
    out = cam_cmd("ftest tempvalue 2>&1; echo W1FI; cat /proc/net/wireless; echo UPT; cat /proc/uptime")
    temp = wifi = up = None
    for ln in out.splitlines():
        s = ln.strip()
        if s.startswith("Display"):
            try:
                temp = float(s.split("=")[1])
            except Exception:
                pass
        if s.startswith("wlan0:"):
            pp = s.replace("wlan0:", "").split()
            try:
                wifi = int(float(pp[1].rstrip(".")))
            except Exception:
                pass
    m = re.search(r"UPT\s+([0-9.]+)", out)
    if m:
        up = float(m.group(1))
    return temp, wifi, up

def main():
    try:
        discovery()
        print("discovery published")
    except Exception as e:
        print("disc err", e)
    while True:
        try:
            temp, wifi, up = read_all()
            if temp is not None or up is not None:
                pub("vm64cam/status", "online")
                pub("vm64cam/online", "ON")
                if temp is not None:
                    pub("vm64cam/temperature", "%.1f" % temp)
                if wifi is not None:
                    pub("vm64cam/wifi", str(wifi))
                if up is not None:
                    boot = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=up)
                    pub("vm64cam/boot", boot.replace(microsecond=0).isoformat())
                print(time.strftime("%H:%M:%S"), "temp", temp, "wifi", wifi, "up", up)
            else:
                pub("vm64cam/status", "offline")
                pub("vm64cam/online", "OFF")
                print("no data from camera")
        except Exception as e:
            try:
                pub("vm64cam/status", "offline")
                pub("vm64cam/online", "OFF")
            except Exception:
                pass
            print("cycle err", e)
        if "--once" in sys.argv:
            break
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
