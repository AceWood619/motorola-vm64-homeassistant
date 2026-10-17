# Make Wi-Fi + root permanent & reboot-proof (no UART needed after this)

Run these once from the root shell. All changes live on the yaffs2 rootfs and survive reboot.

```sh
# 1) your Wi-Fi for the wpa_supplicant wrapper
printf 'ctrl_interface=/tmp/wpa_supplicant\nupdate_config=1\nnetwork={\nssid="YOUR_SSID"\nscan_ssid=1\nkey_mgmt=WPA-PSK\npsk="YOUR_WIFI_PASS"\n}\n' > /etc/my_wifi.conf

# 2) wrap wpa_supplicant so the stock app joins YOUR network
[ -f /usr/bin/wpa_supplicant.real ] || mv /usr/bin/wpa_supplicant /usr/bin/wpa_supplicant.real
# copy wifi_wrapper.sh to /usr/bin/wpa_supplicant (see that file), then:
chmod +x /usr/bin/wpa_supplicant

# 3) network + telnet watchdog, started at boot
cp ha_netwatch.sh /usr/sbin/ha_netwatch.sh && chmod +x /usr/sbin/ha_netwatch.sh
grep -q ha_netwatch /etc/init.d/rcS || echo '/usr/sbin/ha_netwatch.sh &' >> /etc/init.d/rcS

# 4) set a root password so telnet is authenticated
passwd root
```

After a reboot the camera auto-joins your Wi-Fi, grabs DHCP, starts `telnetd`, and the stock app
serves the RTSP stream — all unattended. Get in with `telnet <cam-ip>` (root / your password).

**Tip:** add a DHCP reservation on your router for the camera's MAC so its IP never changes
(Home Assistant's Generic Camera stores the IP in the stream URL).
