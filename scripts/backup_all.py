#!/usr/bin/env python3
"""Back up every NAND partition over the network BEFORE changing anything.
Camera serves each partition with `nc -l`; this PC pulls it. Edit CAMIP.
For partitions with bad blocks (here B/mtd5 and D/mtd7) a plain block-device read via `cat`
STOPS at the first bad block, so those use `nanddump --bb=padbad` instead (data+OOB)."""
import serial, socket, time, os, hashlib
CAMIP = "10.0.0.22"; PORT = 9000
# (name, device, use_nanddump) -- adjust to your /proc/mtd
PARTS = [("MAC","mtdblock1",False),("ENV","mtdblock2",False),("KERNEL","mtdblock3",False),
         ("A_rootfs","mtdblock4",False),("C","mtdblock6",False),("KERBAK","mtdblock8",False),
         ("AK","mtdblock9",False),("BK","mtdblock10",False),("CK","mtdblock11",False),
         ("T_UVC","mtdblock12",False),("B","mtd5",True),("D","mtd7",True)]
S = serial.Serial("COM7", 115200, timeout=0.2)   # or drive over telnet instead
def send(c, w=1.5):
    S.reset_input_buffer(); S.write((c+"\r").encode()); time.sleep(w); return S.read(1<<20)
os.makedirs("backup", exist_ok=True)
for name, dev, nd in PARTS:
    send("killall nc nanddump 2>/dev/null", 0.6)
    src = ("nanddump -o --bb=padbad /dev/%s 2>/dev/null" % dev) if nd else ("cat /dev/%s" % dev)
    send("%s | nc -l -p %d &" % (src, PORT), 1.5)
    c = socket.create_connection((CAMIP, PORT), timeout=12); c.settimeout(20)
    h = hashlib.sha256(); n = 0
    with open("backup/%s_%s.bin" % (dev, name), "wb") as f:
        while True:
            try: b = c.recv(65536)
            except socket.timeout: break
            if not b: break
            f.write(b); h.update(b); n += len(b)
    c.close(); print("%-10s %-12s %10d  %s" % (name, dev, n, h.hexdigest()))
