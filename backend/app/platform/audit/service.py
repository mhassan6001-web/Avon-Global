"""Audit recording and hash-chain verification.

Every event stores ``hash = SHA-256(prev_hash || canonical(event))``. Inserts
are serialised with a transaction-scoped advisory lock so the chain has a
single order. The table itself rejects UPDATE/DELETE/TRUNCATE (migration 0002).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.request_context import get_request_id
from app.platform.audit.models import AuditEvent, SecurityAlert

GENESIS = b"\x00" * 32
_AUDIT_LOCK_KEY = 0x41564E41  # "AVNA"
_SENSITIVE_KEYS = ("password", "secret", "token", "code", "bank", "account_number", "salary")


def redact(details: Mapping[str, Any]) -> dict[str, Any]:
    """Drop values of sensitive-looking keys; coerce values to JSON-stable types."""
    out: dict[str, Any] = {}
    for key, value in details.items():
        if any(marker in key.lower() for marker in _SENSITIVE_KEYS):
            out[key] = "[REDACTED]"
        elif isinstance(value, Mapping):
            out[key] = redact(value)
        elif isinstance(value, (str, int, bool)) or value is None:
            out[key] = value
        elif isinstance(value, (list, tuple, set, frozenset)):
            out[key] = sorted(str(v) for v in value)
        else:
            out[key] = str(value)
    return out


def _canonical(event: AuditEvent) -> bytes:
    body = {
        "occurred_at": event.occurred_at.astimezone(UTC).isoformat(),
        "actor_id": str(event.actor_id) if event.actor_id else None,
        "actor_kind": event.actor_kind,
        "action": event.action,
        "target_type": event.target_type,
        "target_id": event.target_id,
        "outcome": event.outcome,
        "details": event.details,
        "request_id": event.request_id,
        "ip": event.ip,
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def compute_hash(prev_hash: bytes, event: AuditEvent) -> bytes:
    return hashlib.sha256(prev_hash + _canonical(event)).digest()


def record(
    db: Session,
    *,
    action: str,
    actor_id: uuid.UUID | None,
    outcome: str = "success",
    actor_kind: str = "user",
    target_type: str | None = None,
    target_id: str | uuid.UUID | None = None,
    details: Mapping[str, Any] | None = None,
    ip: str | None = None,
) -> AuditEvent:
    """Append an audit event in the caller's transaction (committed with it)."""
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _AUDIT_LOCK_KEY})
    last = db.execute(
        select(AuditEvent.hash).order_by(AuditEvent.seq.desc()).limit(1)
    ).scalar_one_or_none()
    event = AuditEvent(
        occurred_at=datetime.now(UTC),
        actor_id=actor_id,
        actor_kind=actor_kind,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        outcome=outcome,
        details=redact(details or {}),
        request_id=get_request_id(),
        ip=ip,
        prev_hash=last or GENESIS,
    )
    event.hash = compute_hash(event.prev_hash, event)
    db.add(event)
    db.flush()
    return event


@dataclass(frozen=True)
class ChainReport:
    ok: bool
    events_checked: int
    first_bad_seq: int | None = None


def verify_chain(db: Session, batch: int = 1000) -> ChainReport:
    prev = GENESIS
    checked = 0
    last_seq = 0
    while True:
        rows = (
            db.execute(
                select(AuditEvent)
                .where(AuditEvent.seq > last_seq)
                .order_by(AuditEvent.seq)
                .limit(batch)
            )
            .scalars()
            .all()
        )
        if not rows:
            return ChainReport(ok=True, events_checked=checked)
        for event in rows:
            if event.prev_hash != prev or compute_hash(prev, event) != event.hash:
                return ChainReport(ok=False, events_checked=checked, first_bad_seq=event.seq)
            prev = event.hash
            checked += 1
            last_seq = event.seq


def raise_alert(
    db: Session,
    *,
    kind: str,
    message: str,
    severity: str = "warning",
    subject_user_id: uuid.UUID | None = None,
) -> SecurityAlert:
    alert = SecurityAlert(
        created_at=datetime.now(UTC),
        kind=kind,
        severity=severity,
        message=message,
        subject_user_id=subject_user_id,
    )
    db.add(alert)
    db.flush()
    return alert
