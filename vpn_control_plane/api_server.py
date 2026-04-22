from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .models import Platform
from .service import ControlPlaneError, ControlPlaneService
from .store import JsonStore


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "data" / "control_plane.json"
DEFAULT_PACKAGES = ROOT / "dist" / "packages"
DEFAULT_PKI = ROOT / "dist" / "pki"
DEFAULT_WEB_ROOT = ROOT / "web_app"


def ensure_demo_data(service: ControlPlaneService) -> None:
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


def build_server(
    *,
    host: str,
    port: int,
    state_path: Path,
    packages_path: Path,
    pki_path: Path,
    web_root: Path,
) -> ThreadingHTTPServer:
    service = ControlPlaneService(
        JsonStore(state_path),
        package_dir=packages_path,
        pki_dir=pki_path,
    )
    ensure_demo_data(service)

    class Handler(ApiHandler):
        control_plane = service
        static_root = web_root

    return ThreadingHTTPServer((host, port), Handler)


class ApiHandler(BaseHTTPRequestHandler):
    control_plane: ControlPlaneService
    static_root: Path

    server_version = "PersonalVPNControlPlane/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        try:
            if path == "/api/health":
                self.json_response({"ok": True})
                return
            if path == "/api/demo":
                ensure_demo_data(self.control_plane)
                self.json_response({"ok": True, "customer_id": "demo-customer"})
                return
            if path == "/api/dashboard":
                customer_id = query.get("customer_id", ["demo-customer"])[0]
                self.json_response(
                    self.control_plane.get_customer_dashboard(customer_id=customer_id)
                )
                return
            if path.startswith("/api/invites/"):
                token = unquote(path.removeprefix("/api/invites/"))
                self.json_response(self.control_plane.resolve_invite(token=token))
                return
            self.serve_static(path)
        except ControlPlaneError as exc:
            self.json_response({"error": str(exc)}, status=409)
        except Exception as exc:
            self.json_response({"error": str(exc)}, status=500)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        payload = self.read_json()

        try:
            if path == "/api/demo/reset":
                ensure_demo_data(self.control_plane)
                self.json_response({"ok": True, "customer_id": "demo-customer"})
                return

            if path.startswith("/api/customers/") and path.endswith("/invites"):
                customer_id = path.split("/")[3]
                ttl_hours = int(payload.get("ttl_hours", 24))
                self.json_response(
                    self.control_plane.create_invite(
                        customer_id=customer_id,
                        ttl_hours=ttl_hours,
                    ),
                    status=201,
                )
                return

            if path.startswith("/api/invites/") and path.endswith("/activate"):
                parts = path.split("/")
                token = unquote(parts[3])
                self.json_response(
                    self.control_plane.activate_invite(
                        token=token,
                        platform=Platform(payload["platform"]),
                        device_name=payload["device_name"],
                        used_by_ip=self.client_address[0],
                    ),
                    status=201,
                )
                return

            if path.startswith("/api/slots/") and path.endswith("/revoke"):
                slot_id = path.split("/")[3]
                self.json_response(self.control_plane.revoke_slot(slot_id=slot_id))
                return

            if path == "/api/admin/customers":
                self.json_response(
                    self.control_plane.create_customer(
                        customer_id=payload["id"],
                        name=payload["name"],
                        contact=payload.get("contact", ""),
                    ),
                    status=201,
                )
                return

            if path.startswith("/api/admin/customers/") and path.endswith("/server"):
                customer_id = path.split("/")[4]
                self.json_response(
                    self.control_plane.create_server(
                        customer_id=customer_id,
                        fqdn=payload["fqdn"],
                        ip=payload.get("ip", "0.0.0.0"),
                        provider=payload.get("provider", "VDSina"),
                        region=payload.get("region", "Amsterdam"),
                        slot_limit=int(payload.get("slot_limit", 20)),
                    ),
                    status=201,
                )
                return

            self.json_response({"error": "Route not found"}, status=404)
        except KeyError as exc:
            self.json_response({"error": f"Missing field: {exc}"}, status=400)
        except ControlPlaneError as exc:
            self.json_response({"error": str(exc)}, status=409)
        except Exception as exc:
            self.json_response({"error": str(exc)}, status=500)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def json_response(self, payload: Any, *, status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)

    def serve_static(self, request_path: str) -> None:
        path = unquote(request_path)
        if path == "/":
            path = "/index.html"
        file_path = (self.static_root / path.lstrip("/")).resolve()
        static_root = self.static_root.resolve()
        if not str(file_path).startswith(str(static_root)) or not file_path.exists():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:
        print("%s - - %s" % (self.address_string(), format % args))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run local API and dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    parser.add_argument("--packages", default=str(DEFAULT_PACKAGES))
    parser.add_argument("--pki", default=str(DEFAULT_PKI))
    parser.add_argument("--web-root", default=str(DEFAULT_WEB_ROOT))
    args = parser.parse_args(argv)

    server = build_server(
        host=args.host,
        port=args.port,
        state_path=Path(args.state),
        packages_path=Path(args.packages),
        pki_path=Path(args.pki),
        web_root=Path(args.web_root),
    )
    print(f"Serving dashboard: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

