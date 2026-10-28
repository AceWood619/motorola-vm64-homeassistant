#!/usr/bin/env python3
# cam_say_server.py -- optional HTTP front-end on Jarvis (systemd service cam-say, port 8790)
# so anything on the LAN can make the kids-room camera speak: GET/POST /say?text=... -> cam_say.sh
# (The primary HA path is cam_poll.py watching input_text.kids_camera_say; this HTTP endpoint is
#  handy for curl / rest_command / testing.)
import http.server, subprocess, urllib.parse, os, json
HOME = os.path.expanduser("~")
class H(http.server.BaseHTTPRequestHandler):
    def _say(self, text):
        text = (text or "").strip()[:500]
        if not text:
            self.send_response(400); self.end_headers(); self.wfile.write(b"no text"); return
        subprocess.Popen(["bash", HOME + "/cam_say.sh", text])
        self.send_response(200); self.send_header("Content-Type", "text/plain"); self.end_headers()
        self.wfile.write(b"OK: " + text.encode())
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/say":
            q = urllib.parse.parse_qs(u.query); self._say((q.get("text") or [""])[0])
        elif u.path == "/health":
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        else:
            self.send_response(404); self.end_headers()
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(n).decode("utf-8", "ignore") if n else ""
        text = ""
        if "json" in self.headers.get("Content-Type", ""):
            try: text = json.loads(body).get("text", "")
            except Exception: text = ""
        else:
            q = urllib.parse.parse_qs(body); text = (q.get("text") or [""])[0]
        if not text:
            q2 = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            text = (q2.get("text") or [""])[0]
        self._say(text)
    def log_message(self, *a): pass
if __name__ == "__main__":
    http.server.HTTPServer(("0.0.0.0", 8790), H).serve_forever()
