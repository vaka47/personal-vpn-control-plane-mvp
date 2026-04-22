from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from vpn_control_plane.cli import main as cli_main
from vpn_control_plane.models import Platform, SlotStatus
from vpn_control_plane.profile_generator import ProfileGenerator, ProfileRequest
from vpn_control_plane.pki import DevPki
from vpn_control_plane.server_config import generate_swanctl_conf
from vpn_control_plane.service import ControlPlaneError, ControlPlaneService
from vpn_control_plane.store import JsonStore


class ControlPlaneServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.service = ControlPlaneService(
            JsonStore(root / "state.json"),
            package_dir=root / "packages",
            pki_dir=root / "pki",
        )
        self.service.create_customer(
            customer_id="customer-a",
            name="Customer A",
            contact="@customer",
        )
        self.service.create_server(
            customer_id="customer-a",
            fqdn="vpn-a.example.com",
            ip="203.0.113.11",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_invite_is_one_time(self) -> None:
        invite = self.service.create_invite(customer_id="customer-a")
        first = self.service.activate_invite(
            token=invite["token"],
            platform=Platform.APPLE,
            device_name="iPhone",
        )
        self.assertEqual(first["slot_number"], 1)

        with self.assertRaises(ControlPlaneError):
            self.service.activate_invite(
                token=invite["token"],
                platform=Platform.APPLE,
                device_name="Second iPhone",
            )

    def test_slot_limit_blocks_extra_device(self) -> None:
        for index in range(20):
            invite = self.service.create_invite(customer_id="customer-a")
            self.service.activate_invite(
                token=invite["token"],
                platform=Platform.APPLE,
                device_name=f"Device {index}",
            )

        with self.assertRaises(ControlPlaneError):
            self.service.create_invite(customer_id="customer-a")

    def test_revoke_slot(self) -> None:
        invite = self.service.create_invite(customer_id="customer-a")
        activated = self.service.activate_invite(
            token=invite["token"],
            platform=Platform.ANDROID,
            device_name="Pixel",
        )
        revoked = self.service.revoke_slot(slot_id=activated["slot_id"])
        self.assertEqual(revoked["status"], SlotStatus.REVOKED.value)

    def test_duplicate_attempt_is_logged(self) -> None:
        invite = self.service.create_invite(customer_id="customer-a")
        activated = self.service.activate_invite(
            token=invite["token"],
            platform=Platform.APPLE,
            device_name="Mac",
        )
        self.service.record_duplicate_attempt(
            identity=activated["identity"],
            remote_ip="198.51.100.20",
        )
        slots = self.service.list_slots(customer_id="customer-a")
        active = next(slot for slot in slots if slot["identity"] == activated["identity"])
        self.assertEqual(active["duplicate_attempts"], 1)


class ProfileGeneratorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.generator = ProfileGenerator(DevPki(self.root / "pki"))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_generates_apple_android_and_windows_packages(self) -> None:
        platforms = [Platform.APPLE, Platform.ANDROID, Platform.WINDOWS]
        generated = []
        for index, platform in enumerate(platforms, start=1):
            package = self.generator.generate(
                ProfileRequest(
                    customer_id="customer-a",
                    slot_number=index,
                    platform=platform,
                    server_fqdn="vpn-a.example.com",
                    device_name=f"Device {index}",
                    output_dir=self.root / "packages",
                )
            )
            generated.append(package.path)
            self.assertTrue(package.path.exists())

        self.assertEqual(generated[0].suffix, ".mobileconfig")
        self.assertEqual(generated[1].suffix, ".sswan")
        self.assertEqual(generated[2].suffix, ".zip")

        android = json.loads(generated[1].read_text(encoding="utf-8"))
        self.assertEqual(android["remote"]["addr"], "vpn-a.example.com")
        self.assertEqual(android["type"], "ikev2-cert")

        with zipfile.ZipFile(generated[2]) as archive:
            self.assertIn("client.pfx", archive.namelist())
            self.assertIn("install.ps1", archive.namelist())
            self.assertIn("root-ca.cer", archive.namelist())

    def test_strongswan_config_uses_keep_policy(self) -> None:
        config = generate_swanctl_conf(
            customer_id="customer-a",
            server_fqdn="vpn-a.example.com",
        )
        self.assertIn("unique = keep", config)
        self.assertIn("vpn-a.example.com", config)


if __name__ == "__main__":
    unittest.main()

