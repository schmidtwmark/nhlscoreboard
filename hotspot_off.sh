#!/bin/bash
sudo cp /home/pi/nhlscoreboard/dhcpcd.conf.connect /etc/dhcpcd.conf
sudo systemctl stop hostapd
sudo systemctl disable hostapd
sudo systemctl stop dnsmasq
sudo systemctl disable dnsmasq
sudo systemctl daemon-reload
sudo systemctl restart dhcpcd
sudo reboot

