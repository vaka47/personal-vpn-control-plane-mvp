#!/usr/bin/env bash
set -euo pipefail

python3 -m vpn_control_plane.cli init-demo

TOKEN=$(
  python3 -m vpn_control_plane.cli create-invite --customer-id demo-customer \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])'
)

python3 -m vpn_control_plane.cli activate-invite \
  --token "$TOKEN" \
  --platform apple \
  --device-name "Demo iPhone"

python3 -m vpn_control_plane.cli render-server-config \
  --customer-id demo-customer \
  --server-fqdn vpn-demo.example.com \
  --output dist/server/swanctl.conf

find dist -maxdepth 3 -type f | sort

