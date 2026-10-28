#!/usr/bin/env python3
# cam_poll.py -- watches HA input_text.kids_camera_say and speaks it on the kids-room camera.
# Runs on Jarvis as the systemd service cam-poll. Pure HA REST API (the MQTT broker is not
# reachable from Jarvis), so HA -> camera voice works without any HA YAML edits.
import subprocess, json, time, urllib.request, os
env = subprocess.run(["sudo","cat","/etc/jarvis/claude.env","/etc/jarvis/ha.env"],capture_output=True,text=True).stdout
kv = dict(l.split("=",1) for l in env.splitlines() if "=" in l and not l.startswith("#"))
TOK = kv.get("HA_TOKEN","").strip().strip('"')
URL = kv.get("JARVIS_HA_URL", kv.get("HA_URL","http://10.0.0.165:8123")).strip().strip('"')
ENT = "input_text.kids_camera_say"
HOME = os.path.expanduser("~")
def api(method, path, data=None):
    req = urllib.request.Request(URL+path,
          data=(json.dumps(data).encode() if data else None), method=method,
          headers={"Authorization":"Bearer "+TOK, "Content-Type":"application/json"})
    return urllib.request.urlopen(req, timeout=15).read().decode()
last = ""
while True:
    try:
        st = json.loads(api("GET", "/api/states/"+ENT))
        val = (st.get("state") or "").strip()
        if val and val.lower() not in ("unknown", "unavailable") and val != last:
            last = val
            subprocess.Popen(["bash", HOME + "/cam_say.sh", val])
            try:
                api("POST", "/api/services/input_text/set_value", {"entity_id": ENT, "value": ""})
            except Exception:
                pass
            last = ""
    except Exception:
        pass
    time.sleep(2)
