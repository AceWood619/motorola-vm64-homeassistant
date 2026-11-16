#!/usr/bin/env python3
# camcmd.py "<camera shell cmd>" [seconds_to_wait]
# Raw-socket telnet helper: logs into the VM64 camera as root and runs a single command.
# Runs on the always-on LAN host ("Jarvis" box).
# Config (env): VM64_CAM_HOST (camera IP), VM64_CAM_USER (default root),
#               VM64_CAM_PASS (the password you set with `passwd root`; required).
import os, socket, sys, time
HOST=os.environ.get("VM64_CAM_HOST", "vm64-camera.local"); PORT=23
USER=os.environ.get("VM64_CAM_USER", "root").encode()
PW=os.environ.get("VM64_CAM_PASS", "").encode()
def recv_until(s, subs, timeout=8):
    s.settimeout(0.6); buf=b""; t0=time.time()
    while time.time()-t0<timeout:
        try:
            d=s.recv(4096)
            if not d: break
            buf+=d
            for sub in subs:
                if sub in buf: return buf
        except socket.timeout:
            pass
    return buf
def main():
    if not PW:
        sys.exit("camcmd.py: set VM64_CAM_PASS (and VM64_CAM_HOST) in the environment")
    cmd=sys.argv[1] if len(sys.argv)>1 else "pwd"
    wait=float(sys.argv[2]) if len(sys.argv)>2 else 3.0
    s=socket.create_connection((HOST,PORT),timeout=8)
    recv_until(s,[b"login:",b"ogin:"],10)
    s.sendall(USER+b"\n"); time.sleep(0.4)
    recv_until(s,[b"assword:",b"Password:"],6)
    s.sendall(PW+b"\n"); time.sleep(0.6)
    recv_until(s,[b"#",b"$"],6)
    s.sendall(cmd.encode()+b"\n")
    time.sleep(wait)
    out=recv_until(s,[b"NEVER_MATCH_SENTINEL"],wait)
    try: s.sendall(b"exit\n")
    except: pass
    s.close()
    sys.stdout.write(out.decode("latin1"))
if __name__=="__main__": main()
