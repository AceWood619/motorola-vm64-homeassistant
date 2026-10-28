#!/bin/bash
# cam_say.sh "text" -- speak on the kids-room camera (local, no cloud, 16kHz; player rate arg 8000).
# Runs on Jarvis. Prefers Piper neural voice (en_GB-alan), falls back to espeak-ng.
# OPTIMIZED: a single telnet session to the camera (background nc pull, then stop fepe/play/restart
# in the same login) -- cut announce time from ~40s to ~15s on a sluggish camera link.
TEXT="$1"
PIPERD=/home/acewood/piper_dist/piper
VOICE=/home/acewood/voices/en_GB-alan-medium.onnx
if [ -x "$PIPERD/piper" ] && [ -f "$VOICE" ]; then
  printf '%s' "$TEXT" | ( cd "$PIPERD" && LD_LIBRARY_PATH=. ./piper -m "$VOICE" -f /tmp/tts_raw.wav 2>/dev/null )
fi
if [ ! -s /tmp/tts_raw.wav ]; then
  espeak-ng -v en-us -s 160 -p 45 -a 200 "$TEXT" -w /tmp/tts_raw.wav 2>/dev/null
fi
ffmpeg -y -hide_banner -loglevel error -i /tmp/tts_raw.wav -af "dynaudnorm=f=150:g=12" -ar 16000 -ac 1 -c:a pcm_s16le -map_metadata -1 -flags +bitexact -fflags +bitexact /tmp/cam_tts.wav 2>/dev/null || ffmpeg -y -hide_banner -loglevel error -i /tmp/tts_raw.wav -ar 16000 -ac 1 -c:a pcm_s16le /tmp/cam_tts.wav
rm -f /tmp/tts_raw.wav
PORT=9085
setsid bash -c "timeout 15 nc -l $PORT < /tmp/cam_tts.wav >/dev/null 2>&1" >/dev/null 2>&1 &
sleep 1
python3 ~/camcmd.py "nc 10.0.0.60 $PORT > /tmp/talkback.wav & NP=\$!; sleep 3; kill \$NP 2>/dev/null; setsid sh -c \"stop_simdev.sh >/dev/null 2>&1; sleep 1; /mnt/vm64_play3 /tmp/talkback.wav 8000 1 >/tmp/p3.log 2>&1; setsid /usr/sbin/simdev_startup.sh >/tmp/x 2>&1 </dev/null &\" >/dev/null 2>&1 & echo DISPATCHED" 7
echo "SAID: $TEXT"
