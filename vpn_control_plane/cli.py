from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models import Platform
from .profile_generator import ProfileGenerator, ProfileRequest
from .pki import DevPki
from .server_config import generate_firewall_notes, generate_swanctl_conf
from .service import ControlPlaneError, ControlPlaneService
from .store import JsonStore


DEFAULT_STATE = Path("data/control_plane.json")
DEFAULT_PACKAGES = Path("dist/packages")
DEFAULT_PKI = Path("dist/pki")


def build_service(args: argparse.Namespace) -> ControlPlaneService:
    return ControlPlaneService(
        JsonStore(Path(args.state)),
        package_dir=Path(args.packages),
        pki_dir=Path(args.pki),
    )


def print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_init_demo(args: argparse.Namespace) -> None:
    service = build_service(args)
    try:
        service.create_customer(
            customer_id="demo-customer",
            name="Demo Customer",
            contact="@demo",
        )
    except ControlPlaneError:
        pass
    try:
        service.create_server(
            customer_id="demo-customer",
            fqdn="vpn-demo.example.com",
            ip="203.0.113.10",
        )
    except ControlPlaneError:
        pass
    print_json({"ok": True, "state": str(args.state), "customer_id": "demo-customer"})


def cmd_create_customer(args: argparse.Namespace) -> None:
    service = build_service(args)
    print_json(
        service.create_customer(
            customer_id=args.customer_id,
            name=args.name,
            contact=args.contact,
        )
    )


def cmd_create_server(args: argparse.Namespace) -> None:
    service = build_service(args)
    print_json(
        service.create_server(
            customer_id=args.customer_id,
            fqdn=args.fqdn,
            ip=args.ip,
            provider=args.provider,
            region=args.region,
            slot_limit=args.slot_limit,
        )
    )


def cmd_create_invite(args: argparse.Namespace) -> None:
    service = build_service(args)
    print_json(service.create_invite(customer_id=args.customer_id, ttl_hours=args.ttl_hours))


def cmd_activate_invite(args: argparse.Namespace) -> None:
    service = build_service(args)
    print_json(
        service.activate_invite(
            token=args.token,
            platform=Platform(args.platform),
            device_name=args.device_name,
            used_by_ip=args.used_by_ip,
        )
    )


def cmd_list_slots(args: argparse.Namespace) -> None:
    service = build_service(args)
    print_json(service.list_slots(customer_id=args.customer_id))


def cmd_revoke_slot(args: argparse.Namespace) -> None:
    service = build_service(args)
    print_json(service.revoke_slot(slot_id=args.slot_id))


def cmd_generate_profile(args: argparse.Namespace) -> None:
    generator = ProfileGenerator(DevPki(Path(args.pki)))
    package = generator.generate(
        ProfileRequest(
            customer_id=args.customer_id,
            slot_number=args.slot,
            platform=Platform(args.platform),
            server_fqdn=args.server_fqdn,
            device_name=args.device_name,
            output_dir=Path(args.packages) / args.customer_id,
        )
    )
    print_json(
        {
            "platform": package.platform.value,
            "identity": package.identity,
            "path": str(package.path),
            "serial": package.serial,
            "fingerprint": package.fingerprint,
        }
    )


def cmd_render_server_config(args: argparse.Namespace) -> None:
    conf = generate_swanctl_conf(
        customer_id=args.customer_id,
        server_fqdn=args.server_fqdn,
        vip_pool=args.vip_pool,
        unique_policy=args.unique_policy,
    )
    notes = generate_firewall_notes(vpn_pool=args.vip_pool)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(conf + "\n" + notes, encoding="utf-8")
        print_json({"path": str(output)})
    else:
        print(conf)
        print(notes)


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    parser.add_argument("--packages", default=str(DEFAULT_PACKAGES))
    parser.add_argument("--pki", default=str(DEFAULT_PKI))


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal VPN control-plane MVP")
    add_common(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    init_demo = sub.add_parser("init-demo")
    init_demo.set_defaults(func=cmd_init_demo)

    create_customer = sub.add_parser("create-customer")
    create_customer.add_argument("--customer-id", required=True)
    create_customer.add_argument("--name", required=True)
    create_customer.add_argument("--contact", default="")
    create_customer.set_defaults(func=cmd_create_customer)

    create_server = sub.add_parser("create-server")
    create_server.add_argument("--customer-id", required=True)
    create_server.add_argument("--fqdn", required=True)
    create_server.add_argument("--ip", default="0.0.0.0")
    create_server.add_argument("--provider", default="VDSina")
    create_server.add_argument("--region", default="Amsterdam")
    create_server.add_argument("--slot-limit", type=int, default=20)
    create_server.set_defaults(func=cmd_create_server)

    create_invite = sub.add_parser("create-invite")
    create_invite.add_argument("--customer-id", required=True)
    create_invite.add_argument("--ttl-hours", type=int, default=24)
    create_invite.set_defaults(func=cmd_create_invite)

    activate = sub.add_parser("activate-invite")
    activate.add_argument("--token", required=True)
    activate.add_argument("--platform", choices=[item.value for item in Platform], required=True)
    activate.add_argument("--device-name", required=True)
    activate.add_argument("--used-by-ip", default="127.0.0.1")
    activate.set_defaults(func=cmd_activate_invite)

    slots = sub.add_parser("list-slots")
    slots.add_argument("--customer-id", required=True)
    slots.set_defaults(func=cmd_list_slots)

    revoke = sub.add_parser("revoke-slot")
    revoke.add_argument("--slot-id", required=True)
    revoke.set_defaults(func=cmd_revoke_slot)

    generate = sub.add_parser("generate-profile")
    generate.add_argument("--customer-id", required=True)
    generate.add_argument("--slot", type=int, required=True)
    generate.add_argument("--platform", choices=[item.value for item in Platform], required=True)
    generate.add_argument("--server-fqdn", required=True)
    generate.add_argument("--device-name", required=True)
    generate.set_defaults(func=cmd_generate_profile)

    server_config = sub.add_parser("render-server-config")
    server_config.add_argument("--customer-id", required=True)
    server_config.add_argument("--server-fqdn", required=True)
    server_config.add_argument("--vip-pool", default="10.10.10.0/24")
    server_config.add_argument("--unique-policy", default="keep")
    server_config.add_argument("--output")
    server_config.set_defaults(func=cmd_render_server_config)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

