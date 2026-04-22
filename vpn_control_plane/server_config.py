from __future__ import annotations


def generate_swanctl_conf(
    *,
    customer_id: str,
    server_fqdn: str,
    vip_pool: str = "10.10.10.0/24",
    dns_servers: str = "1.1.1.1, 8.8.8.8",
    unique_policy: str = "keep",
) -> str:
    """Render a strongSwan swanctl.conf example for this product model."""

    return f"""# strongSwan swanctl.conf for customer {customer_id}
# One identity may have only one active connection.
# unique = keep prevents a copied profile from kicking the original device.

connections {{
  ikev2-pubkey {{
    version = 2
    unique = {unique_policy}
    local_addrs = %any
    pools = vpn-pool
    send_cert = always
    proposals = aes256gcm16-prfsha256-ecp256

    local {{
      auth = pubkey
      certs = server.crt
      id = {server_fqdn}
    }}

    remote {{
      auth = pubkey
      id = %any
    }}

    children {{
      net {{
        local_ts = 0.0.0.0/0
        esp_proposals = aes256gcm16-ecp256
        dpd_action = clear
      }}
    }}
  }}
}}

pools {{
  vpn-pool {{
    addrs = {vip_pool}
    dns = {dns_servers}
  }}
}}
"""


def generate_firewall_notes(vpn_pool: str = "10.10.10.0/24") -> str:
    return f"""Required firewall behavior:

- allow SSH from admin IPs
- allow UDP 500
- allow UDP 4500
- enable IPv4 forwarding
- NAT VPN clients from {vpn_pool} to the public interface
- block all other inbound traffic by default
"""

