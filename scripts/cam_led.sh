#!/bin/bash
# cam_led.sh -- manual LED/IR control for the VM64 camera (runs ftest over telnet via camcmd).
#   cam_led.sh white on|off
#   cam_led.sh nightvision on|off      (IR illuminator; the app may re-assert auto night vision)
#   cam_led.sh ircut 0|1               (IR-cut filter: 1 in / 0 out)
#   cam_led.sh rgb Off|Red|Green|Blue|Yellow|Cyan|Magenta|White   (status RGB led 3/4/5)
case "$1" in
  white)       python3 ~/camcmd.py "ftest led 6 $2" 5 >/dev/null 2>&1;;
  nightvision) python3 ~/camcmd.py "ftest irled all $2" 5 >/dev/null 2>&1;;
  ircut)       python3 ~/camcmd.py "ftest ircut $2" 5 >/dev/null 2>&1;;
  rgb)
    case "$2" in
      Red) C="on off off";; Green) C="off on off";; Blue) C="off off on";;
      Yellow) C="on on off";; Cyan) C="off on on";; Magenta) C="on off on";;
      White) C="on on on";; *) C="off off off";;
    esac
    set -- $C
    python3 ~/camcmd.py "ftest led 3 $1; ftest led 4 $2; ftest led 5 $3" 6 >/dev/null 2>&1;;
esac
echo "LED: $*"
