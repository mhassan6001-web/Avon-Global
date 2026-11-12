"""Synchronise the code catalogue (roles, permissions, departments) into the database.

Idempotent and safe to run on every start; a transaction-scoped advisory lock
prevents concurrent replicas from racing. Role-permission links are replaced
to match the code exactly, so the code remains the single source of truth.
"""

from __future__ import annotations

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.platform.authz.catalogue import DEPARTMENTS, PERMISSIONS, ROLE_PERMISSIONS, ROLES
from app.platform.identity.models import Department, Permission, Role, RolePermission

_SYNC_LOCK_KEY = 0x41564E53  # "AVNS"


def sync_catalogue(db: Session) -> None:
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _SYNC_LOCK_KEY})

    departments = {d.code: d for d in db.execute(select(Department)).scalars()}
    for code, name in DEPARTMENTS:
        if code in departments:
            departments[code].name = name
        else:
            db.add(Department(code=code, name=name))

    roles = {r.code: r for r in db.execute(select(Role)).scalars()}
    for role in ROLES:
        if role.code in roles:
            roles[role.code].name = role.name
            roles[role.code].mfa_required = role.mfa_required
        else:
            db.add(Role(code=role.code, name=role.name, mfa_required=role.mfa_required))

    perms = {p.code: p for p in db.execute(select(Permission)).scalars()}
    for perm in PERMISSIONS:
        if perm.code in perms:
            perms[perm.code].description = perm.description
            perms[perm.code].sensitive = perm.sensitive
        else:
            db.add(
                Permission(code=perm.code, description=perm.description, sensitive=perm.sensitive)
            )
    db.flush()

    role_ids = {r.code: r.id for r in db.execute(select(Role)).scalars()}
    perm_ids = {p.code: p.id for p in db.execute(select(Permission)).scalars()}
    db.execute(delete(RolePermission))
    for role_code, codes in ROLE_PERMISSIONS.items():
        for code in sorted(codes):
            db.add(RolePermission(role_id=role_ids[role_code], permission_id=perm_ids[code]))
    db.commit()
