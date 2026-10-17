#!/bin/sh
# /usr/bin/wpa_supplicant  (WRAPPER)
# The stock app hardcodes a factory SSID and ignores config edits. We rename the real
# binary to wpa_supplicant.real and drop this wrapper in its place, so whenever the app
# brings up Wi-Fi it actually joins YOUR network (from /etc/my_wifi.conf).
#
# Install:
#   [ -f /usr/bin/wpa_supplicant.real ] || mv /usr/bin/wpa_supplicant /usr/bin/wpa_supplicant.real
#   cp wifi_wrapper.sh /usr/bin/wpa_supplicant && chmod +x /usr/bin/wpa_supplicant
#
# /etc/my_wifi.conf:
#   ctrl_interface=/tmp/wpa_supplicant
#   update_config=1
#   network={
#     ssid="YOUR_SSID"
#     scan_ssid=1
#     key_mgmt=WPA-PSK
#     psk="YOUR_WIFI_PASS"
#   }
/bin/killall -9 wpa_supplicant.real 2>/dev/null
sleep 1
exec /usr/bin/wpa_supplicant.real -B -iwlan0 -Dwext -c /etc/my_wifi.conf
