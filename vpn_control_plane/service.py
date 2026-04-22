from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from .models import (
    AuditEvent,
    CertificateRecord,
    Customer,
    DeviceSlot,
    InviteStatus,
    InviteToken,
    Platform,
    Server,
    SlotStatus,
    new_id,
    now_iso,
    to_dict,
)
from .pki import DevPki
from .profile_generator import ProfileGenerator, ProfileRequest
from .store import JsonStore


class ControlPlaneError(RuntimeError):
    pass


class ControlPlaneService:
    def __init__(
        self,
        store: JsonStore,
        *,
        package_dir: Path = Path("dist/packages"),
        pki_dir: Path = Path("dist/pki"),
    ):
        self.store = store
        self.package_dir = Path(package_dir)
        self.generator = ProfileGenerator(DevPki(Path(pki_dir)))

    def create_customer(self, *, customer_id: str, name: str, contact: str = "") -> Dict[str, Any]:
        state = self.store.load()
        if any(row["id"] == customer_id for row in state["customers"]):
            raise ControlPlaneError(f"Customer already exists: {customer_id}")
        customer = Customer(id=customer_id, name=name, contact=contact)
        state["customers"].append(to_dict(customer))
        state["audit_log"].append(
            to_dict(
                AuditEvent(
                    id=new_id("audit"),
                    actor_type="ADMIN",
                    action="CUSTOMER_CREATED",
                    target_type="customer",
                    target_id=customer.id,
                    payload={"name": name},
                )
            )
        )
        self.store.save(state)
        return to_dict(customer)

    def create_server(
        self,
        *,
        customer_id: str,
        fqdn: str,
        ip: str = "0.0.0.0",
        provider: str = "VDSina",
        region: str = "Amsterdam",
        slot_limit: int = 20,
    ) -> Dict[str, Any]:
        state = self.store.load()
        self._require_customer(state, customer_id)
        if any(row["customer_id"] == customer_id for row in state["servers"]):
            raise ControlPlaneError(f"Server already exists for customer: {customer_id}")

        server = Server(
            id=new_id("srv"),
            customer_id=customer_id,
            fqdn=fqdn,
            provider=provider,
            region=region,
            ip=ip,
        )
        state["servers"].append(to_dict(server))
        for slot_number in range(1, slot_limit + 1):
            slot = DeviceSlot(
                id=new_id("slot"),
                customer_id=customer_id,
                server_id=server.id,
                slot_number=slot_number,
            )
            state["device_slots"].append(to_dict(slot))

        state["audit_log"].append(
            to_dict(
                AuditEvent(
                    id=new_id("audit"),
                    actor_type="ADMIN",
                    action="SERVER_CREATED",
                    target_type="server",
                    target_id=server.id,
                    payload={"fqdn": fqdn, "slot_limit": slot_limit},
                )
            )
        )
        self.store.save(state)
        return to_dict(server)

    def create_invite(self, *, customer_id: str, ttl_hours: int = 24) -> Dict[str, str]:
        state = self.store.load()
        self._require_customer(state, customer_id)
        free_slots = [
            row
            for row in state["device_slots"]
            if row["customer_id"] == customer_id and row["status"] == SlotStatus.FREE.value
        ]
        if not free_slots:
            raise ControlPlaneError("No free device slots")

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
        invite = InviteToken(
            id=new_id("inv"),
            customer_id=customer_id,
            token_hash=self.hash_token(token),
            status=InviteStatus.CREATED.value,
            expires_at=expires_at.replace(microsecond=0).isoformat(),
        )
        state["invite_tokens"].append(to_dict(invite))
        state["audit_log"].append(
            to_dict(
                AuditEvent(
                    id=new_id("audit"),
                    actor_type="CUSTOMER",
                    action="INVITE_CREATED",
                    target_type="invite",
                    target_id=invite.id,
                    payload={"expires_at": invite.expires_at},
                )
            )
        )
        self.store.save(state)
        return {
            "invite_id": invite.id,
            "token": token,
            "expires_at": invite.expires_at,
        }

    def activate_invite(
        self,
        *,
        token: str,
        platform: Platform,
        device_name: str,
        used_by_ip: str = "127.0.0.1",
    ) -> Dict[str, Any]:
        state = self.store.load()
        invite = self._find_invite_by_token(state, token)
        self._assert_invite_can_be_used(invite)

        server = self._server_for_customer(state, invite["customer_id"])
        slot = self._first_free_slot(state, invite["customer_id"])
        identity = ProfileGenerator.identity(invite["customer_id"], slot["slot_number"])
        output_dir = self.package_dir / invite["customer_id"]

        package = self.generator.generate(
            ProfileRequest(
                customer_id=invite["customer_id"],
                slot_number=slot["slot_number"],
                platform=platform,
                server_fqdn=server["fqdn"],
                device_name=device_name,
                output_dir=output_dir,
                identity=identity,
            )
        )

        slot["status"] = SlotStatus.ACTIVE.value
        slot["platform"] = platform.value
        slot["device_name"] = device_name
        slot["identity"] = identity

        invite["status"] = InviteStatus.USED.value
        invite["used_at"] = now_iso()
        invite["used_by_ip"] = used_by_ip
        invite["slot_id"] = slot["id"]

        cert = CertificateRecord(
            id=new_id("cert"),
            slot_id=slot["id"],
            serial=package.serial,
            fingerprint=package.fingerprint,
            common_name=identity,
        )
        state["certificates"].append(to_dict(cert))
        state["audit_log"].append(
            to_dict(
                AuditEvent(
                    id=new_id("audit"),
                    actor_type="SYSTEM",
                    action="INVITE_ACTIVATED",
                    target_type="slot",
                    target_id=slot["id"],
                    payload={
                        "platform": platform.value,
                        "identity": identity,
                        "package": str(package.path),
                    },
                )
            )
        )
        self.store.save(state)

        return {
            "slot_id": slot["id"],
            "slot_number": slot["slot_number"],
            "identity": identity,
            "package_path": str(package.path),
            "serial": package.serial,
            "fingerprint": package.fingerprint,
        }

    def revoke_slot(self, *, slot_id: str, actor_type: str = "CUSTOMER") -> Dict[str, Any]:
        state = self.store.load()
        slot = self._find_by_id(state, "device_slots", slot_id)
        if slot["status"] != SlotStatus.ACTIVE.value:
            raise ControlPlaneError("Only ACTIVE slots can be revoked")
        slot["status"] = SlotStatus.REVOKED.value
        for cert in state["certificates"]:
            if cert["slot_id"] == slot_id and not cert.get("revoked_at"):
                cert["revoked_at"] = now_iso()

        state["audit_log"].append(
            to_dict(
                AuditEvent(
                    id=new_id("audit"),
                    actor_type=actor_type,
                    action="SLOT_REVOKED",
                    target_type="slot",
                    target_id=slot_id,
                    payload={"identity": slot.get("identity")},
                )
            )
        )
        self.store.save(state)
        return slot

    def record_duplicate_attempt(self, *, identity: str, remote_ip: str) -> None:
        state = self.store.load()
        for slot in state["device_slots"]:
            if slot.get("identity") == identity:
                slot["duplicate_attempts"] = int(slot.get("duplicate_attempts", 0)) + 1
                state["audit_log"].append(
                    to_dict(
                        AuditEvent(
                            id=new_id("audit"),
                            actor_type="SYSTEM",
                            action="DUPLICATE_PROFILE_ATTEMPT",
                            target_type="slot",
                            target_id=slot["id"],
                            payload={"identity": identity, "remote_ip": remote_ip},
                        )
                    )
                )
                self.store.save(state)
                return
        raise ControlPlaneError(f"Identity not found: {identity}")

    def list_slots(self, *, customer_id: str) -> List[Dict[str, Any]]:
        state = self.store.load()
        return [
            row
            for row in state["device_slots"]
            if row["customer_id"] == customer_id
        ]

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _require_customer(self, state: Dict[str, Any], customer_id: str) -> Dict[str, Any]:
        customer = next((row for row in state["customers"] if row["id"] == customer_id), None)
        if not customer:
            raise ControlPlaneError(f"Customer not found: {customer_id}")
        return customer

    def _server_for_customer(self, state: Dict[str, Any], customer_id: str) -> Dict[str, Any]:
        server = next((row for row in state["servers"] if row["customer_id"] == customer_id), None)
        if not server:
            raise ControlPlaneError(f"Server not found for customer: {customer_id}")
        return server

    def _first_free_slot(self, state: Dict[str, Any], customer_id: str) -> Dict[str, Any]:
        slots = sorted(
            [
                row
                for row in state["device_slots"]
                if row["customer_id"] == customer_id and row["status"] == SlotStatus.FREE.value
            ],
            key=lambda row: row["slot_number"],
        )
        if not slots:
            raise ControlPlaneError("No free device slots")
        return slots[0]

    def _find_invite_by_token(self, state: Dict[str, Any], token: str) -> Dict[str, Any]:
        token_hash = self.hash_token(token)
        invite = next(
            (row for row in state["invite_tokens"] if row["token_hash"] == token_hash),
            None,
        )
        if not invite:
            raise ControlPlaneError("Invite not found")
        return invite

    def _assert_invite_can_be_used(self, invite: Dict[str, Any]) -> None:
        if invite["status"] != InviteStatus.CREATED.value:
            raise ControlPlaneError(f"Invite is not usable: {invite['status']}")
        expires_at = datetime.fromisoformat(invite["expires_at"])
        if expires_at < datetime.now(timezone.utc):
            invite["status"] = InviteStatus.EXPIRED.value
            raise ControlPlaneError("Invite expired")

    def _find_by_id(self, state: Dict[str, Any], collection: str, row_id: str) -> Dict[str, Any]:
        row = next((item for item in state[collection] if item["id"] == row_id), None)
        if not row:
            raise ControlPlaneError(f"{collection} row not found: {row_id}")
        return row

