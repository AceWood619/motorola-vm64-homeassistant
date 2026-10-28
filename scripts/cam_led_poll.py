#!/usr/bin/env python3
# cam_led_poll.py -- watches HA LED helpers and applies them on the camera via ftest.
# Jarvis systemd service cam-led-poll. Controls work alongside the running app (no fepe stop,
# no audio-device conflict; verified). ftest led 1-6 (1/2 red, 3/4/5 RGB, 6 white),
# irled all on/off (IR illuminator / night vision), ircut 0/1 (IR-cut filter).
import subprocess, json, time, urllib.request, os
env = subprocess.run(["sudo","cat","/etc/jarvis/claude.env","/etc/jarvis/ha.env"],capture_output=True,text=True).stdout
kv = dict(l.split("=",1) for l in env.splitlines() if "=" in l and not l.startswith("#"))
TOK = kv.get("HA_TOKEN","").strip().strip('"')
URL = kv.get("JARVIS_HA_URL", kv.get("HA_URL","http://10.0.0.165:8123")).strip().strip('"')
CAM = os.path.expanduser("~") + "/camcmd.py"
def st(ent):
    try:
        req = urllib.request.Request(URL+"/api/states/"+ent, headers={"Authorization":"Bearer "+TOK})
        return json.loads(urllib.request.urlopen(req, timeout=15).read().decode()).get("state","")
    except Exception:
        return None
def cam(cmd):
    subprocess.run(["python3", CAM, cmd, "6"], capture_output=True)
RGB = {"Off":("off","off","off"),"Red":("on","off","off"),"Green":("off","on","off"),
       "Blue":("off","off","on"),"Yellow":("on","on","off"),"Cyan":("off","on","on"),
       "Magenta":("on","off","on"),"White":("on","on","on")}
last = {}
while True:
    try:
        w = st("input_boolean.kids_cam_white_led")
        if w in ("on","off") and w != last.get("w"):
            cam("ftest led 6 %s" % w); last["w"] = w
        nv = st("input_boolean.kids_cam_night_vision")
        if nv in ("on","off") and nv != last.get("nv"):
            cam("ftest irled all %s" % nv); last["nv"] = nv
        rgb = st("input_select.kids_cam_status_led")
        if rgb in RGB and rgb != last.get("rgb"):
            r,g,b = RGB[rgb]
            cam("ftest led 3 %s; ftest led 4 %s; ftest led 5 %s" % (r,g,b)); last["rgb"] = rgb
    except Exception:
        pass
    time.sleep(2)
