from __future__ import annotations

import base64
import json
import plistlib
import secrets
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import uuid4

from .models import Platform
from .pki import DevPki


@dataclass(frozen=True)
class ProfileRequest:
    customer_id: str
    slot_number: int
    platform: Platform
    server_fqdn: str
    device_name: str
    output_dir: Path
    server_name: str = "Personal VPN"
    identity: Optional[str] = None


@dataclass(frozen=True)
class GeneratedPackage:
    platform: Platform
    identity: str
    path: Path
    ca_cert: Path
    client_p12: Path
    serial: str
    fingerprint: str


class ProfileGenerator:
    def __init__(self, pki: DevPki):
        self.pki = pki

    def generate(self, request: ProfileRequest) -> GeneratedPackage:
        identity = request.identity or self.identity(
            request.customer_id, request.slot_number
        )
        p12_password = secrets.token_urlsafe(18)
        material = self.pki.issue_device(
            server_fqdn=request.server_fqdn,
            identity=identity,
            p12_password=p12_password,
        )

        request.output_dir.mkdir(parents=True, exist_ok=True)
        if request.platform == Platform.APPLE:
            path = self._build_apple_mobileconfig(request, identity, material.client_p12, material.ca_cert, p12_password)
        elif request.platform == Platform.ANDROID:
            path = self._build_android_sswan(request, identity, material.client_p12, material.ca_cert, p12_password)
        elif request.platform == Platform.WINDOWS:
            path = self._build_windows_package(request, identity, material.client_p12, material.ca_cert, p12_password)
        else:
            raise ValueError(f"Unsupported platform: {request.platform}")

        return GeneratedPackage(
            platform=request.platform,
            identity=identity,
            path=path,
            ca_cert=material.ca_cert,
            client_p12=material.client_p12,
            serial=self.pki.certificate_serial(material.client_cert),
            fingerprint=self.pki.certificate_fingerprint(material.client_cert),
        )

    @staticmethod
    def identity(customer_id: str, slot_number: int) -> str:
        safe_customer = "".join(
            ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in customer_id
        )
        return f"{safe_customer}-d{slot_number:02d}"

    def _build_apple_mobileconfig(
        self,
        request: ProfileRequest,
        identity: str,
        p12_path: Path,
        ca_path: Path,
        p12_password: str,
    ) -> Path:
        vpn_uuid = str(uuid4()).upper()
        p12_uuid = str(uuid4()).upper()
        ca_uuid = str(uuid4()).upper()
        profile_uuid = str(uuid4()).upper()
        display_name = f"{request.server_name} {request.slot_number:02d}"

        vpn_payload = {
            "PayloadType": "com.apple.vpn.managed",
            "PayloadVersion": 1,
            "PayloadIdentifier": f"vpn.personal.{identity}.ikev2",
            "PayloadUUID": vpn_uuid,
            "PayloadDisplayName": display_name,
            "UserDefinedName": display_name,
            "VPNType": "IKEv2",
            "IKEv2": {
                "RemoteAddress": request.server_fqdn,
                "RemoteIdentifier": request.server_fqdn,
                "LocalIdentifier": identity,
                "AuthenticationMethod": "Certificate",
                "PayloadCertificateUUID": p12_uuid,
                "DeadPeerDetectionRate": "Medium",
                "DisableMOBIKE": 0,
                "DisableRedirect": 0,
                "EnableCertificateRevocationCheck": 1,
                "IKESecurityAssociationParameters": {
                    "EncryptionAlgorithm": "AES-256-GCM",
                    "IntegrityAlgorithm": "SHA2-256",
                    "DiffieHellmanGroup": 19,
                    "LifeTimeInMinutes": 1440,
                },
                "ChildSecurityAssociationParameters": {
                    "EncryptionAlgorithm": "AES-256-GCM",
                    "IntegrityAlgorithm": "SHA2-256",
                    "DiffieHellmanGroup": 19,
                    "LifeTimeInMinutes": 1440,
                },
            },
            "OnDemandEnabled": 1,
            "OnDemandRules": [{"Action": "Connect"}],
        }

        p12_payload = {
            "PayloadType": "com.apple.security.pkcs12",
            "PayloadVersion": 1,
            "PayloadIdentifier": f"vpn.personal.{identity}.identity",
            "PayloadUUID": p12_uuid,
            "PayloadDisplayName": f"{identity} identity",
            "Password": p12_password,
            "PayloadContent": p12_path.read_bytes(),
        }

        ca_payload = {
            "PayloadType": "com.apple.security.root",
            "PayloadVersion": 1,
            "PayloadIdentifier": f"vpn.personal.{identity}.ca",
            "PayloadUUID": ca_uuid,
            "PayloadDisplayName": "Personal VPN Root CA",
            "PayloadContent": ca_path.read_bytes(),
        }

        profile = {
            "PayloadType": "Configuration",
            "PayloadVersion": 1,
            "PayloadIdentifier": f"vpn.personal.{identity}",
            "PayloadUUID": profile_uuid,
            "PayloadDisplayName": display_name,
            "PayloadDescription": "Personal VPN profile generated for one device slot.",
            "PayloadOrganization": "Personal VPN",
            "PayloadRemovalDisallowed": False,
            "PayloadContent": [ca_payload, p12_payload, vpn_payload],
        }

        output = request.output_dir / f"{identity}.mobileconfig"
        with output.open("wb") as file:
            plistlib.dump(profile, file, sort_keys=False)
        return output

    def _build_android_sswan(
        self,
        request: ProfileRequest,
        identity: str,
        p12_path: Path,
        ca_path: Path,
        p12_password: str,
    ) -> Path:
        profile = {
            "uuid": str(uuid4()),
            "name": f"{request.server_name} {request.slot_number:02d}",
            "type": "ikev2-cert",
            "remote": {
                "addr": request.server_fqdn,
                "id": request.server_fqdn,
            },
            "local": {
                "id": identity,
                "cert": "client.p12",
            },
            "certificates": [
                {
                    "name": "root-ca.crt",
                    "type": "ca",
                    "data": base64.b64encode(ca_path.read_bytes()).decode("ascii"),
                },
                {
                    "name": "client.p12",
                    "type": "pkcs12",
                    "password": p12_password,
                    "data": base64.b64encode(p12_path.read_bytes()).decode("ascii"),
                },
            ],
            "metadata": {
                "customer_id": request.customer_id,
                "slot_number": request.slot_number,
                "device_name": request.device_name,
                "warning": "One profile is intended for one device slot only.",
            },
        }
        output = request.output_dir / f"{identity}.sswan"
        output.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        return output

    def _build_windows_package(
        self,
        request: ProfileRequest,
        identity: str,
        p12_path: Path,
        ca_path: Path,
        p12_password: str,
    ) -> Path:
        vpn_name = f"{request.server_name} {request.slot_number:02d}"
        install_ps1 = f"""$ErrorActionPreference = "Stop"

$VpnName = "{vpn_name}"
$ServerAddress = "{request.server_fqdn}"
$PfxPassword = ConvertTo-SecureString -String "{p12_password}" -AsPlainText -Force

Write-Host "Importing root CA..."
Import-Certificate -FilePath "$PSScriptRoot\\root-ca.cer" -CertStoreLocation Cert:\\LocalMachine\\Root | Out-Null

Write-Host "Importing client certificate..."
Import-PfxCertificate -FilePath "$PSScriptRoot\\client.pfx" -CertStoreLocation Cert:\\LocalMachine\\My -Password $PfxPassword | Out-Null

Write-Host "Creating VPN profile..."
Remove-VpnConnection -Name $VpnName -Force -ErrorAction SilentlyContinue
Add-VpnConnection -Name $VpnName -ServerAddress $ServerAddress -TunnelType Ikev2 -AuthenticationMethod MachineCertificate -EncryptionLevel Required -RememberCredential -SplitTunneling $false -Force

Write-Host "Done. Open Windows VPN settings and connect: $VpnName"
"""
        readme = f"""Personal VPN Windows package

Device identity: {identity}
Server: {request.server_fqdn}
Device name: {request.device_name}

Install:
1. Run PowerShell as Administrator.
2. Execute:
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
   .\\install.ps1
3. Open Windows VPN settings and connect.

One profile is intended for one device slot only.
"""

        output = request.output_dir / f"{identity}-windows.zip"
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(p12_path, "client.pfx")
            archive.write(ca_path, "root-ca.cer")
            archive.writestr("install.ps1", install_ps1)
            archive.writestr("README.txt", readme)
        return output

