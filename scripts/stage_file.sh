#!/bin/bash
# stage_file.sh <localfile> <camera_abs_path> [port]
# Binary-safe file transfer Jarvis -> camera, md5-verified both ends.
# Serves the file via `nc -l <port>` on Jarvis (set JARVIS_HOST to its LAN IP); the camera pulls it with busybox nc.
# (busybox nc half-closes/hangs after transfer, so the pull is its own camcmd call.)
LF="$1"; RP="$2"; PORT=${3:-9085}
JARVIS_HOST=${JARVIS_HOST:?set JARVIS_HOST to the LAN IP of this host}
SZ=$(wc -c < "$LF")
MD=$(md5sum "$LF" | cut -d" " -f1)
setsid bash -c "timeout 30 nc -l $PORT < \"$LF\" >/dev/null 2>&1" >/dev/null 2>&1 &
sleep 1
python3 ~/camcmd.py "nc $JARVIS_HOST $PORT > $RP; echo PULLED" 8 >/dev/null 2>&1
sleep 1
python3 ~/camcmd.py "echo STAGED=\$(wc -c < $RP) WANT=$SZ; echo RMD5=\$(md5sum $RP 2>/dev/null | cut -d\" \" -f1) LMD5=$MD" 5
