#!/bin/bash

# This script is called by wg-quick's PostUp and PostDown hooks.

ACTION=$1
WG_IFACE=$2      # The WireGuard interface name (e.g., wg0)
VPN_SUBNET=$3    # The VPN subnet

# Find the primary network interface name dynamically.
# This is the interface used by the default route.
PRIMARY_IFACE=$(ip -4 route ls | grep default | grep -Po '(?<=dev )(\S+)' | head -1)

if [ "$1" == "up" ]; then
    # Add forwarding and NAT rules.
    iptables -A FORWARD -i "${WG_IFACE}" -j ACCEPT
    iptables -t nat -A POSTROUTING -s "${VPN_SUBNET}" -o "${PRIMARY_IFACE}" -j MASQUERADE
elif [ "$1" == "down" ]; then
    # Remove forwarding and NAT rules.
    iptables -D FORWARD -i "${WG_IFACE}" -j ACCEPT
    iptables -t nat -D POSTROUTING -s "${VPN_SUBNET}" -o "${PRIMARY_IFACE}" -j MASQUERADE
fi

exit 0