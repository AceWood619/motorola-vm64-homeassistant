#!/bin/bash
# cam_play.sh <file_or_url> -- play an arbitrary audio file/URL on the kids-room camera speaker.
# Runs on Jarvis. Caps at 120s so a huge/bad file can't black out the video feed indefinitely
# (fepe is stopped during playback). Same engine as cam_say (16kHz content, player rate arg 8000).
SRC="$1"
TMP=/tmp/cam_play_src
case "$SRC" in
  http://*|https://*) curl -s -m 30 -L -o "$TMP" "$SRC" || exit 1; IN="$TMP";;
  *) IN="$SRC";;
esac
[ -s "$IN" ] || { echo "no input: $SRC"; exit 1; }
ffmpeg -y -hide_banner -loglevel error -t 120 -i "$IN" -af "dynaudnorm=f=150:g=12" -ar 16000 -ac 1 -c:a pcm_s16le -map_metadata -1 -flags +bitexact -fflags +bitexact /tmp/cam_tts.wav 2>/dev/null || ffmpeg -y -hide_banner -loglevel error -t 120 -i "$IN" -ar 16000 -ac 1 -c:a pcm_s16le /tmp/cam_tts.wav
bash ~/stage_file.sh /tmp/cam_tts.wav /tmp/talkback.wav >/dev/null 2>&1
python3 ~/camcmd.py "setsid sh -c \"stop_simdev.sh >/dev/null 2>&1; sleep 1; /mnt/vm64_play3 /tmp/talkback.wav 8000 1 >/tmp/p3.log 2>&1; setsid /usr/sbin/simdev_startup.sh >/tmp/x 2>&1 </dev/null &\" >/dev/null 2>&1 & echo DISPATCHED" 8
echo "PLAYED: $SRC"
