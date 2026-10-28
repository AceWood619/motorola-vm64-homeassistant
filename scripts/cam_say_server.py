#!/usr/bin/env python3
# cam_say_server.py -- HTTP front-end on Jarvis (systemd cam-say, :8790).
#   GET/POST /say?text=...   -> cam_say.sh  (TTS)
#   GET/POST /play?url=...   -> cam_play.sh (arbitrary audio file/URL)
#   GET /health
import http.server, subprocess, urllib.parse, os, json
HOME = os.path.expanduser("~")
def run(script, arg):
    arg = (arg or "").strip()[:1000]
    if not arg: return False
    subprocess.Popen(["bash", HOME + "/" + script, arg]); return True
class H(http.server.BaseHTTPRequestHandler):
    def _do(self, script, arg):
        if run(script, arg):
            self.send_response(200); self.send_header("Content-Type","text/plain"); self.end_headers()
            self.wfile.write(b"OK: " + arg.encode())
        else:
            self.send_response(400); self.end_headers(); self.wfile.write(b"missing arg")
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        if u.path == "/say":   self._do("cam_say.sh",  (q.get("text") or [""])[0])
        elif u.path == "/play": self._do("cam_play.sh", (q.get("url") or q.get("file") or [""])[0])
        elif u.path == "/health":
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        else:
            self.send_response(404); self.end_headers()
    def do_POST(self):
        n = int(self.headers.get("Content-Length",0) or 0)
        body = self.rfile.read(n).decode("utf-8","ignore") if n else ""
        u = urllib.parse.urlparse(self.path)
        data = {}
        if "json" in self.headers.get("Content-Type",""):
            try: data = json.loads(body)
            except Exception: data = {}
        else:
            data = {k:v[0] for k,v in urllib.parse.parse_qs(body).items()}
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/say":
            self._do("cam_say.sh", data.get("text") or (q.get("text") or [""])[0])
        elif u.path == "/play":
            self._do("cam_play.sh", data.get("url") or data.get("file") or (q.get("url") or [""])[0])
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, *a): pass
if __name__ == "__main__":
    http.server.HTTPServer(("0.0.0.0", 8790), H).serve_forever()
