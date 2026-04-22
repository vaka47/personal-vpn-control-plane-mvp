from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class DevicePkiMaterial:
    ca_cert: Path
    server_cert: Path
    client_cert: Path
    client_key: Path
    client_p12: Path
    p12_password: str


class OpenSslError(RuntimeError):
    pass


def _run(args: List[str], cwd: Path) -> None:
    result = subprocess.run(args, cwd=str(cwd), text=True, capture_output=True)
    if result.returncode != 0:
        raise OpenSslError(
            "OpenSSL command failed:\n"
            + " ".join(args)
            + "\nSTDOUT:\n"
            + result.stdout
            + "\nSTDERR:\n"
            + result.stderr
        )


class DevPki:
    """Generates local development certificates through OpenSSL.

    This is not a production CA. It exists so the MVP can generate real
    PKCS#12/PFX artifacts before a live VPN server is rented.
    """

    def __init__(self, base_dir: Path, openssl_bin: str = "openssl"):
        self.base_dir = Path(base_dir).resolve()
        self.openssl_bin = openssl_bin
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def ensure_root_ca(self) -> tuple[Path, Path]:
        key = self.base_dir / "root-ca.key"
        cert = self.base_dir / "root-ca.crt"
        if key.exists() and cert.exists():
            return key, cert

        _run(
            [
                self.openssl_bin,
                "req",
                "-x509",
                "-newkey",
                "rsa:4096",
                "-sha256",
                "-days",
                "3650",
                "-nodes",
                "-subj",
                "/CN=Personal VPN Dev Root CA",
                "-keyout",
                str(key),
                "-out",
                str(cert),
            ],
            self.base_dir,
        )
        return key, cert

    def issue_device(
        self,
        *,
        server_fqdn: str,
        identity: str,
        p12_password: str,
    ) -> DevicePkiMaterial:
        ca_key, ca_cert = self.ensure_root_ca()
        device_dir = self.base_dir / identity
        device_dir.mkdir(parents=True, exist_ok=True)

        server_key = device_dir / "server.key"
        server_csr = device_dir / "server.csr"
        server_cert = device_dir / "server.crt"
        client_key = device_dir / "client.key"
        client_csr = device_dir / "client.csr"
        client_cert = device_dir / "client.crt"
        client_p12 = device_dir / "client.p12"

        san_file = device_dir / "server.ext"
        san_file.write_text(
            "\n".join(
                [
                    "subjectAltName = DNS:" + server_fqdn,
                    "extendedKeyUsage = serverAuth",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        client_ext = device_dir / "client.ext"
        client_ext.write_text("extendedKeyUsage = clientAuth\n", encoding="utf-8")

        if not server_cert.exists():
            _run(
                [
                    self.openssl_bin,
                    "req",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-subj",
                    f"/CN={server_fqdn}",
                    "-keyout",
                    str(server_key),
                    "-out",
                    str(server_csr),
                ],
                self.base_dir,
            )
            _run(
                [
                    self.openssl_bin,
                    "x509",
                    "-req",
                    "-in",
                    str(server_csr),
                    "-CA",
                    str(ca_cert),
                    "-CAkey",
                    str(ca_key),
                    "-CAcreateserial",
                    "-out",
                    str(server_cert),
                    "-days",
                    "825",
                    "-sha256",
                    "-extfile",
                    str(san_file),
                ],
                self.base_dir,
            )

        if not client_cert.exists():
            _run(
                [
                    self.openssl_bin,
                    "req",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-subj",
                    f"/CN={identity}",
                    "-keyout",
                    str(client_key),
                    "-out",
                    str(client_csr),
                ],
                self.base_dir,
            )
            _run(
                [
                    self.openssl_bin,
                    "x509",
                    "-req",
                    "-in",
                    str(client_csr),
                    "-CA",
                    str(ca_cert),
                    "-CAkey",
                    str(ca_key),
                    "-CAcreateserial",
                    "-out",
                    str(client_cert),
                    "-days",
                    "825",
                    "-sha256",
                    "-extfile",
                    str(client_ext),
                ],
                self.base_dir,
            )

        _run(
            [
                self.openssl_bin,
                "pkcs12",
                "-export",
                "-legacy",
                "-inkey",
                str(client_key),
                "-in",
                str(client_cert),
                "-certfile",
                str(ca_cert),
                "-name",
                identity,
                "-passout",
                f"pass:{p12_password}",
                "-out",
                str(client_p12),
            ],
            self.base_dir,
        )

        return DevicePkiMaterial(
            ca_cert=ca_cert,
            server_cert=server_cert,
            client_cert=client_cert,
            client_key=client_key,
            client_p12=client_p12,
            p12_password=p12_password,
        )

    def certificate_serial(self, cert_path: Path) -> str:
        result = subprocess.run(
            [self.openssl_bin, "x509", "-in", str(cert_path), "-noout", "-serial"],
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            raise OpenSslError(result.stderr)
        return result.stdout.strip().replace("serial=", "")

    def certificate_fingerprint(self, cert_path: Path) -> str:
        result = subprocess.run(
            [
                self.openssl_bin,
                "x509",
                "-in",
                str(cert_path),
                "-noout",
                "-fingerprint",
                "-sha256",
            ],
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            raise OpenSslError(result.stderr)
        return result.stdout.strip().replace("sha256 Fingerprint=", "")
