#!/usr/bin/env bash
set -euo pipefail

DRY_RUN="${DRY_RUN:-1}"
VPN_POOL="${VPN_POOL:-10.10.10.0/24}"
PUBLIC_INTERFACE="${PUBLIC_INTERFACE:-eth0}"

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[dry-run] %s\n' "$*"
  else
    "$@"
  fi
}

echo "Personal VPN strongSwan bootstrap"
echo "DRY_RUN=$DRY_RUN VPN_POOL=$VPN_POOL PUBLIC_INTERFACE=$PUBLIC_INTERFACE"

run apt-get update
run apt-get install -y strongswan strongswan-pki swanctl iptables-persistent

run sysctl -w net.ipv4.ip_forward=1
run sysctl -w net.ipv4.conf.all.accept_redirects=0
run sysctl -w net.ipv4.conf.all.send_redirects=0

run iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
run iptables -A INPUT -p tcp --dport 22 -j ACCEPT
run iptables -A INPUT -i lo -j ACCEPT
run iptables -A INPUT -p udp --dport 500 -j ACCEPT
run iptables -A INPUT -p udp --dport 4500 -j ACCEPT
run iptables -t nat -A POSTROUTING -s "$VPN_POOL" -o "$PUBLIC_INTERFACE" -j MASQUERADE
run iptables -A INPUT -j DROP

run systemctl enable strongswan
run systemctl restart strongswan

echo "Bootstrap plan complete."

