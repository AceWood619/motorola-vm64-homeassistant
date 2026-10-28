#!/bin/bash
# cam_say.sh "text"  -- speak text on the kids-room camera speaker (local, no cloud).
# Runs on the Jarvis box (10.0.0.60). Chain: espeak-ng -> 16kHz mono WAV -> md5-verified
# transfer to camera /tmp/talkback.wav -> stop fepe, play with vm64_play3, restart fepe.
# NOTE on rate: the AK3918 DAC clocks at 2x the set rate, so author at 16kHz but tell the
# player 8000 (half) -> plays back at a correct 16kHz. Loudness = WAV amplitude
# (ak_ao_set_volume SIGFPEs on this chip rev and is intentionally not used).
TEXT="$1"
espeak-ng -v en-us -s 160 -p 45 -a 200 "$TEXT" -w /tmp/tts_raw.wav 2>/dev/null
ffmpeg -y -hide_banner -loglevel error -i /tmp/tts_raw.wav -af "dynaudnorm=f=150:g=12" -ar 16000 -ac 1 -c:a pcm_s16le -map_metadata -1 -flags +bitexact -fflags +bitexact /tmp/cam_tts.wav 2>/dev/null || ffmpeg -y -hide_banner -loglevel error -i /tmp/tts_raw.wav -ar 16000 -ac 1 -c:a pcm_s16le /tmp/cam_tts.wav
bash ~/stage_file.sh /tmp/cam_tts.wav /tmp/talkback.wav >/dev/null 2>&1
python3 ~/camcmd.py "setsid sh -c \"stop_simdev.sh >/dev/null 2>&1; sleep 1; /mnt/vm64_play3 /tmp/talkback.wav 8000 1 >/tmp/p3.log 2>&1; setsid /usr/sbin/simdev_startup.sh >/tmp/x 2>&1 </dev/null &\" >/dev/null 2>&1 & echo DISPATCHED" 6
echo "SAID: $TEXT"
