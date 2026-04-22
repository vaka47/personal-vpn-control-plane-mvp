from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from vpn_control_plane.api_server import build_server


class ApiServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        try:
            self.server = build_server(
                host="127.0.0.1",
                port=0,
                state_path=root / "state.json",
                packages_path=root / "packages",
                pki_path=root / "pki",
                web_root=Path("web_app"),
            )
        except PermissionError:
            self.skipTest("local sandbox does not allow binding test HTTP sockets")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        time.sleep(0.05)

    def tearDown(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()
        self.tmp.cleanup()

    def get_json(self, path: str) -> dict:
        opener = build_opener(ProxyHandler({}))
        with opener.open(self.base_url + path, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_json(self, path: str, payload: dict) -> dict:
        opener = build_opener(ProxyHandler({}))
        request = Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with opener.open(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_dashboard_and_invite_activation(self) -> None:
        health = self.get_json("/api/health")
        self.assertTrue(health["ok"])

        dashboard = self.get_json("/api/dashboard?customer_id=demo-customer")
        self.assertEqual(dashboard["summary"]["free_slots"], 20)

        invite = self.post_json(
            "/api/customers/demo-customer/invites",
            {"ttl_hours": 24},
        )
        self.assertIn("token", invite)

        activation = self.post_json(
            f"/api/invites/{invite['token']}/activate",
            {"platform": "apple", "device_name": "API Test iPhone"},
        )
        self.assertEqual(activation["slot_number"], 1)
        self.assertTrue(activation["package_path"].endswith(".mobileconfig"))

        dashboard = self.get_json("/api/dashboard?customer_id=demo-customer")
        self.assertEqual(dashboard["summary"]["active_slots"], 1)
        self.assertEqual(dashboard["summary"]["free_slots"], 19)

    def test_invite_cannot_be_reused(self) -> None:
        invite = self.post_json(
            "/api/customers/demo-customer/invites",
            {"ttl_hours": 24},
        )
        self.post_json(
            f"/api/invites/{invite['token']}/activate",
            {"platform": "android", "device_name": "Pixel"},
        )

        with self.assertRaises(HTTPError) as context:
            self.post_json(
                f"/api/invites/{invite['token']}/activate",
                {"platform": "android", "device_name": "Second Pixel"},
            )
        self.assertEqual(context.exception.code, 409)


if __name__ == "__main__":
    unittest.main()
