from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class Platform(str, Enum):
    APPLE = "apple"
    ANDROID = "android"
    WINDOWS = "windows"


class CustomerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"


class ServerStatus(str, Enum):
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"
    SUSPENDED = "SUSPENDED"


class SlotStatus(str, Enum):
    FREE = "FREE"
    RESERVED = "RESERVED"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class InviteStatus(str, Enum):
    CREATED = "CREATED"
    USED = "USED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


@dataclass
class Customer:
    id: str
    name: str
    contact: str = ""
    status: str = CustomerStatus.ACTIVE.value
    created_at: str = field(default_factory=now_iso)


@dataclass
class Server:
    id: str
    customer_id: str
    fqdn: str
    provider: str = "VDSina"
    region: str = "Amsterdam"
    ip: str = "0.0.0.0"
    status: str = ServerStatus.ACTIVE.value
    created_at: str = field(default_factory=now_iso)


@dataclass
class DeviceSlot:
    id: str
    customer_id: str
    server_id: str
    slot_number: int
    status: str = SlotStatus.FREE.value
    platform: Optional[str] = None
    device_name: Optional[str] = None
    identity: Optional[str] = None
    last_seen_at: Optional[str] = None
    last_ip: Optional[str] = None
    bytes_in: int = 0
    bytes_out: int = 0
    duplicate_attempts: int = 0


@dataclass
class InviteToken:
    id: str
    customer_id: str
    token_hash: str
    status: str
    expires_at: str
    created_at: str = field(default_factory=now_iso)
    used_at: Optional[str] = None
    used_by_ip: Optional[str] = None
    slot_id: Optional[str] = None


@dataclass
class CertificateRecord:
    id: str
    slot_id: str
    serial: str
    fingerprint: str
    common_name: str
    issued_at: str = field(default_factory=now_iso)
    revoked_at: Optional[str] = None


@dataclass
class AuditEvent:
    id: str
    actor_type: str
    action: str
    target_type: str
    target_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)


def empty_state() -> Dict[str, List[Dict[str, Any]]]:
    return {
        "customers": [],
        "servers": [],
        "device_slots": [],
        "invite_tokens": [],
        "certificates": [],
        "audit_log": [],
    }


def to_dict(obj: Any) -> Dict[str, Any]:
    return asdict(obj)

