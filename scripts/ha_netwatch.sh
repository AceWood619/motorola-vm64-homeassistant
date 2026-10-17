#!/bin/sh
# /usr/sbin/ha_netwatch.sh  -- keep the camera on YOUR LAN + telnet root available.
# The stock app assigns a factory static IP after associating; we re-grab DHCP and
# make sure telnetd is running. Start it from /etc/init.d/rcS:
#   grep -q ha_netwatch /etc/init.d/rcS || echo '/usr/sbin/ha_netwatch.sh &' >> /etc/init.d/rcS
# Change 10.0.0. to your subnet prefix.
while true; do
  IP=`ifconfig wlan0 2>/dev/null | sed -n 's/.*inet addr:\([0-9.]*\).*/\1/p'`
  case "$IP" in
    10.0.0.*) : ;;                                  # already on our LAN
    *) udhcpc -i wlan0 -t 4 -T 2 -n -q >/dev/null 2>&1 ;;
  esac
  pidof telnetd >/dev/null 2>&1 || /sbin/telnetd -l /bin/login >/dev/null 2>&1
  sleep 20
done
