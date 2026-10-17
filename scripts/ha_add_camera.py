#!/usr/bin/env python3
"""Add the VM64 stream to Home Assistant as a Generic Camera, headless, via REST+WS.
Needs a HA long-lived access token. Set HA_URL and HA_TOKEN below (or via env)."""
import asyncio, json, os, urllib.request, urllib.error, websockets

HA_URL   = os.environ.get("HA_URL",   "http://YOUR_HA_IP:8123")
HA_TOKEN = os.environ.get("HA_TOKEN", "YOUR_LONG_LIVED_TOKEN")
STREAM   = os.environ.get("CAM_RTSP", "rtsp://YOUR_CAM_IP:6667/blinkhd")
AREA     = os.environ.get("CAM_AREA", "")   # e.g. "kids_room"; leave blank to skip
NAME     = os.environ.get("CAM_NAME", "Baby Camera")

def rest(method, path, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(HA_URL+path, data=body, method=method,
        headers={"Authorization":"Bearer "+HA_TOKEN, "Content-Type":"application/json"})
    try:    return json.loads(urllib.request.urlopen(req, timeout=40).read().decode())
    except urllib.error.HTTPError as e: return {"_err":e.code, "_body":e.read().decode()[:300]}

def add_camera():
    fi = rest("POST", "/api/config/config_entries/flow",
              {"handler":"generic", "show_advanced_options":True})
    fid = fi["flow_id"]
    rest("POST", "/api/config/config_entries/flow/"+fid,
         {"stream_source":STREAM, "advanced":{"framerate":5, "verify_ssl":False, "rtsp_transport":"tcp"}})
    s = rest("POST", "/api/config/config_entries/flow/"+fid, {"confirmed_ok":True})
    assert s.get("type") == "create_entry", s
    return s["result"]["entry_id"]

async def rename_and_area(entry_id):
    async with websockets.connect(HA_URL.replace("http","ws")+"/api/websocket") as w:
        await w.recv(); await w.send(json.dumps({"type":"auth","access_token":HA_TOKEN})); await w.recv()
        n=[0]
        async def call(m):
            n[0]+=1; m["id"]=n[0]; await w.send(json.dumps(m))
            while True:
                r=json.loads(await w.recv())
                if r.get("id")==n[0]: return r
        er = await call({"type":"config/entity_registry/list"})
        for e in er["result"]:
            if e.get("config_entry_id")==entry_id:
                upd={"type":"config/entity_registry/update","entity_id":e["entity_id"],"name":NAME}
                if AREA: upd["area_id"]=AREA
                await call(upd)
                print("configured", e["entity_id"])

eid = add_camera(); print("entry", eid)
asyncio.run(rename_and_area(eid))
