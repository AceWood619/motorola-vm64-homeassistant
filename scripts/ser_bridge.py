import sys, threading, serial, time, re, os

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM7"
BAUD = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
LOG = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.expanduser("~"), "uart.log")

ser = serial.Serial()
ser.port = PORT; ser.baudrate = BAUD; ser.timeout = 0.1
ser.dtr = False; ser.rts = False
ser.open()
try:
    ser.setDTR(False); ser.setRTS(False)
except Exception:
    pass

logf = open(LOG, "ab", buffering=0)
sys.stdout.write("OPENED %s @ %d (8N1) log=%s\n" % (PORT, BAUD, LOG)); sys.stdout.flush()

# ---- spam filter: the app floods the console with these ----
NOISE_PHRASES = ["check frame timeout!", "*** req info=0 ***",
                 "*** cam 0 lostlink icon ***", "*** diff=0 ***"]
def is_noise(line):
    s = line.strip()
    if s == "":
        return True
    for p in NOISE_PHRASES:
        if p in s and len(s) < len(p) + 6:
            return True
    # lines that are mostly the status chars s / M / w / > / < / digits / spaces
    noise = sum(1 for c in s if c in "sMw<>0123456789, ")
    if len(s) >= 8 and noise / len(s) > 0.82:
        return True
    return False

buf = bytearray()
def reader():
    global buf
    while True:
        try:
            data = ser.read(4096)
            if not data:
                continue
            logf.write(data)  # full raw log, always
            buf.extend(data)
            while b"\n" in buf:
                i = buf.index(b"\n")
                raw = bytes(buf[:i]); del buf[:i+1]
                try:
                    line = raw.decode("utf-8", "replace").rstrip("\r")
                except Exception:
                    line = repr(raw)
                if not is_noise(line):
                    sys.stdout.write(line + "\n"); sys.stdout.flush()
        except Exception as e:
            sys.stdout.write("\n[READ_ERR %r]\n" % e); sys.stdout.flush(); break

threading.Thread(target=reader, daemon=True).start()

for line in sys.stdin:
    cmd = line.rstrip("\r\n")
    try:
        if cmd == "::ENTER::":
            ser.write(b"\r")
        elif cmd == "::BREAK::":
            ser.send_break(0.4)
        elif cmd == "::SPAM::":
            t = time.time()
            while time.time() - t < 3.0:
                ser.write(b"\r"); ser.flush(); time.sleep(0.02)
        elif cmd == "::CTRLC::":
            ser.write(b"\x03")
        elif cmd.startswith("::RAW:") and cmd.endswith("::"):
            ser.write(bytes.fromhex(cmd[6:-2]))
        else:
            ser.write((cmd + "\r\n").encode("utf-8", "ignore"))
        ser.flush()
    except Exception as e:
        sys.stdout.write("\n[WRITE_ERR %r]\n" % e); sys.stdout.flush()
