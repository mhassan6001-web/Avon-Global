"""Administration (module K): users, roles, overrides, audit, login history, alerts.

Director only (department-scoped access decision, 2026-11-12). Every change
requires a recent step-up verification and is written to the audit log.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.platform.audit import service as audit
from app.platform.audit.models import AuditEvent, SecurityAlert
from app.platform.authz.catalogue import (
    DIRECTOR_ONLY,
    PERMISSION_CODES,
    PERMISSIONS,
    ROLE_BY_CODE,
    ROLE_PERMISSIONS,
    ROLES,
)
from app.platform.authz.deps import DbSession, Principal, require, require_step_up
from app.platform.identity import schemas as id_schemas
from app.platform.identity import service as identity
from app.platform.identity.models import LoginEvent, Permission, PermissionOverride, Role, User
from app.platform.identity.router import user_out
from app.platform.identity.schemas import validate_email

router = APIRouter(prefix="/admin", tags=["admin"])

ManageUsers = Depends(require("admin.users.manage"))
ManagePerms = Depends(require("admin.permissions.manage"))
ViewAudit = Depends(require("admin.audit.view"))
ViewLogins = Depends(require("admin.login_history.view"))
StepUp = Depends(require_step_up)


class CreateUserRequest(BaseModel):
    email: str = Field(max_length=320)
    display_name: str = Field(min_length=2, max_length=200)
    role: str

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        return validate_email(value)


class CreatedUserOut(BaseModel):
    user: id_schemas.UserOut
    invitation_url: str
    note: str = "Give this one-time link to the person securely. It is shown only once."


class LinkOut(BaseModel):
    url: str
    expires_note: str


class RoleChange(BaseModel):
    role: str


class OverrideRequest(BaseModel):
    permission: str
    effect: str = Field(pattern="^(grant|deny)$")
    reason: str = Field(min_length=5, max_length=500)


class OverrideOut(BaseModel):
    permission: str
    effect: str
    reason: str
    created_at: datetime


class RoleOut(BaseModel):
    code: str
    name: str
    mfa_required: bool
    permissions: list[str]


class PermissionOut(BaseModel):
    code: str
    description: str
    sensitive: bool
    director_only: bool


class AuditEventOut(BaseModel):
    seq: int
    occurred_at: datetime
    actor_id: uuid.UUID | None
    actor_kind: str
    action: str
    target_type: str | None
    target_id: str | None
    outcome: str
    details: dict[str, Any]
    request_id: str | None


class ChainOut(BaseModel):
    ok: bool
    events_checked: int
    first_bad_seq: int | None


class AlertOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    kind: str
    severity: str
    message: str
    acknowledged_at: datetime | None


def _user(db: DbSession, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


def _not_self(principal: Principal, user: User) -> None:
    if user.id == principal.user.id:
        raise PermissionDeniedError("You cannot change your own account here.")


# ------------------------------------------------------------------ catalogue


@router.get("/roles", response_model=list[RoleOut], dependencies=[ManageUsers])
def roles() -> list[RoleOut]:
    return [
        RoleOut(
            code=r.code,
            name=r.name,
            mfa_required=r.mfa_required,
            permissions=sorted(ROLE_PERMISSIONS[r.code]),
        )
        for r in ROLES
    ]


@router.get("/permissions", response_model=list[PermissionOut], dependencies=[ManageUsers])
def permissions() -> list[PermissionOut]:
    return [
        PermissionOut(
            code=p.code,
            description=p.description,
            sensitive=p.sensitive,
            director_only=p.code in DIRECTOR_ONLY,
        )
        for p in PERMISSIONS
    ]


# ------------------------------------------------------------------ users


@router.get("/users", response_model=list[id_schemas.UserOut], dependencies=[ManageUsers])
def list_users(db: DbSession) -> list[id_schemas.UserOut]:
    users = db.execute(select(User).order_by(User.display_name)).scalars()
    return [user_out(db, u) for u in users]


@router.post("/users", response_model=CreatedUserOut, status_code=201, dependencies=[StepUp])
def create_user(
    body: CreateUserRequest, db: DbSession, principal: Principal = ManageUsers
) -> CreatedUserOut:
    if body.role not in ROLE_BY_CODE:
        raise NotFoundError("Unknown role.")
    if body.role == "director":
        raise PermissionDeniedError(
            "Director accounts are created only with the deployment command (create-director)."
        )
    user = identity.create_user(
        db,
        email=body.email,
        display_name=body.display_name,
        role_code=body.role,
        created_by=principal.user.id,
    )
    url = identity.issue_link(db, user, "invitation", principal.user.id)
    db.commit()
    return CreatedUserOut(user=user_out(db, user), invitation_url=url)


def _set_status(
    db: DbSession, principal: Principal, user_id: uuid.UUID, status: str
) -> id_schemas.UserOut:
    user = _user(db, user_id)
    _not_self(principal, user)
    if user.status == status:
        raise ConflictError(f"User is already {status}.")
    if status == "active" and not user.password_hash:
        raise ConflictError("This user has not accepted their invitation yet.")
    user.status = status
    user.suspended_at = identity.now() if status == "suspended" else None
    user.version += 1
    revoked = identity.revoke_sessions(db, user.id) if status == "suspended" else 0
    audit.record(
        db,
        action=f"admin.user_{'suspended' if status == 'suspended' else 'reactivated'}",
        actor_id=principal.user.id,
        target_type="user",
        target_id=user.id,
        details={"sessions_revoked": revoked},
    )
    db.commit()
    return user_out(db, user)


@router.post("/users/{user_id}/suspend", response_model=id_schemas.UserOut, dependencies=[StepUp])
def suspend(
    user_id: uuid.UUID, db: DbSession, principal: Principal = ManageUsers
) -> id_schemas.UserOut:
    return _set_status(db, principal, user_id, "suspended")


@router.post(
    "/users/{user_id}/reactivate", response_model=id_schemas.UserOut, dependencies=[StepUp]
)
def reactivate(
    user_id: uuid.UUID, db: DbSession, principal: Principal = ManageUsers
) -> id_schemas.UserOut:
    return _set_status(db, principal, user_id, "active")


@router.put("/users/{user_id}/role", response_model=id_schemas.UserOut, dependencies=[StepUp])
def change_role(
    user_id: uuid.UUID, body: RoleChange, db: DbSession, principal: Principal = ManageUsers
) -> id_schemas.UserOut:
    user = _user(db, user_id)
    _not_self(principal, user)
    if body.role not in ROLE_BY_CODE or body.role == "director":
        raise PermissionDeniedError("That role cannot be assigned here.")
    role = db.execute(select(Role).where(Role.code == body.role)).scalar_one()
    from app.platform.identity.models import Department

    dept = db.execute(
        select(Department).where(Department.code == ROLE_BY_CODE[body.role].department_code)
    ).scalar_one()
    old = identity.role_of(db, user).code
    user.role_id, user.department_id = role.id, dept.id
    user.version += 1
    identity.revoke_sessions(db, user.id)
    audit.record(
        db,
        action="admin.user_role_changed",
        actor_id=principal.user.id,
        target_type="user",
        target_id=user.id,
        details={"from": old, "to": body.role},
    )
    db.commit()
    return user_out(db, user)


@router.post("/users/{user_id}/reset-link", response_model=LinkOut, dependencies=[StepUp])
def reset_link(user_id: uuid.UUID, db: DbSession, principal: Principal = ManageUsers) -> LinkOut:
    user = _user(db, user_id)
    _not_self(principal, user)
    purpose = "invitation" if user.status == "invited" else "password_reset"
    url = identity.issue_link(db, user, purpose, principal.user.id)
    audit.record(
        db,
        action=f"admin.{purpose}_link_issued",
        actor_id=principal.user.id,
        target_type="user",
        target_id=user.id,
    )
    db.commit()
    return LinkOut(url=url, expires_note="Single use. Give it to the person securely.")


@router.post(
    "/users/{user_id}/revoke-sessions", response_model=id_schemas.OkOut, dependencies=[StepUp]
)
def revoke_user_sessions(
    user_id: uuid.UUID, db: DbSession, principal: Principal = ManageUsers
) -> id_schemas.OkOut:
    user = _user(db, user_id)
    count = identity.revoke_sessions(db, user.id)
    audit.record(
        db,
        action="admin.sessions_revoked",
        actor_id=principal.user.id,
        target_type="user",
        target_id=user.id,
        details={"count": count},
    )
    db.commit()
    return id_schemas.OkOut()


# ------------------------------------------------------------------ overrides


@router.get(
    "/users/{user_id}/overrides", response_model=list[OverrideOut], dependencies=[ManagePerms]
)
def list_overrides(user_id: uuid.UUID, db: DbSession) -> list[OverrideOut]:
    rows = db.execute(
        select(Permission.code, PermissionOverride)
        .join(Permission, Permission.id == PermissionOverride.permission_id)
        .where(PermissionOverride.user_id == user_id)
    ).all()
    return [
        OverrideOut(permission=code, effect=o.effect, reason=o.reason, created_at=o.created_at)
        for code, o in rows
    ]


@router.post(
    "/users/{user_id}/overrides", response_model=OverrideOut, status_code=201, dependencies=[StepUp]
)
def set_override(
    user_id: uuid.UUID, body: OverrideRequest, db: DbSession, principal: Principal = ManagePerms
) -> OverrideOut:
    user = _user(db, user_id)
    _not_self(principal, user)
    if body.permission not in PERMISSION_CODES:
        raise NotFoundError("Unknown permission.")
    if body.effect == "grant" and body.permission in DIRECTOR_ONLY:
        raise PermissionDeniedError("Director-only permissions cannot be granted to other users.")
    perm = db.execute(select(Permission).where(Permission.code == body.permission)).scalar_one()
    db.execute(
        delete(PermissionOverride).where(
            PermissionOverride.user_id == user.id, PermissionOverride.permission_id == perm.id
        )
    )
    override = PermissionOverride(
        user_id=user.id,
        permission_id=perm.id,
        effect=body.effect,
        reason=body.reason,
        granted_by=principal.user.id,
    )
    db.add(override)
    db.flush()
    audit.record(
        db,
        action="admin.permission_override_set",
        actor_id=principal.user.id,
        target_type="user",
        target_id=user.id,
        details={"permission": body.permission, "effect": body.effect, "reason": body.reason},
    )
    db.commit()
    return OverrideOut(
        permission=body.permission,
        effect=override.effect,
        reason=override.reason,
        created_at=override.created_at,
    )


@router.delete(
    "/users/{user_id}/overrides/{permission}",
    response_model=id_schemas.OkOut,
    dependencies=[StepUp],
)
def remove_override(
    user_id: uuid.UUID, permission: str, db: DbSession, principal: Principal = ManagePerms
) -> id_schemas.OkOut:
    perm = db.execute(select(Permission).where(Permission.code == permission)).scalar_one_or_none()
    if perm is None:
        raise NotFoundError("Unknown permission.")
    deleted = db.execute(
        delete(PermissionOverride).where(
            PermissionOverride.user_id == user_id, PermissionOverride.permission_id == perm.id
        )
    )
    if not deleted.rowcount:  # type: ignore[attr-defined]
        raise NotFoundError("No override for that permission.")
    audit.record(
        db,
        action="admin.permission_override_removed",
        actor_id=principal.user.id,
        target_type="user",
        target_id=user_id,
        details={"permission": permission},
    )
    db.commit()
    return id_schemas.OkOut()


# ------------------------------------------------------------------ audit, logins, alerts


@router.get("/audit", response_model=list[AuditEventOut], dependencies=[ViewAudit])
def audit_events(
    db: DbSession, before_seq: int | None = None, limit: int = 100
) -> list[AuditEventOut]:
    stmt = select(AuditEvent).order_by(AuditEvent.seq.desc()).limit(min(max(limit, 1), 500))
    if before_seq is not None:
        stmt = stmt.where(AuditEvent.seq < before_seq)
    return [
        AuditEventOut.model_validate(e, from_attributes=True) for e in db.execute(stmt).scalars()
    ]


@router.post("/audit/verify", response_model=ChainOut)
def verify_audit(db: DbSession, principal: Principal = ViewAudit) -> ChainOut:
    report = audit.verify_chain(db)
    if not report.ok:
        audit.raise_alert(
            db,
            kind="audit_chain_broken",
            severity="critical",
            message=f"Audit chain verification failed at event {report.first_bad_seq}.",
        )
        db.commit()
    return ChainOut(
        ok=report.ok, events_checked=report.events_checked, first_bad_seq=report.first_bad_seq
    )


@router.get(
    "/login-history", response_model=list[id_schemas.LoginEventOut], dependencies=[ViewLogins]
)
def login_history(db: DbSession, limit: int = 100) -> list[id_schemas.LoginEventOut]:
    rows = db.execute(
        select(LoginEvent).order_by(LoginEvent.occurred_at.desc()).limit(min(max(limit, 1), 500))
    ).scalars()
    return [
        id_schemas.LoginEventOut(
            occurred_at=e.occurred_at,
            email_attempted=e.email_attempted,
            outcome=e.outcome,
            ip=str(e.ip) if e.ip else None,
            user_agent=e.user_agent,
            user_id=e.user_id,
        )
        for e in rows
    ]


@router.get("/security-alerts", response_model=list[AlertOut], dependencies=[ViewAudit])
def security_alerts(db: DbSession) -> list[AlertOut]:
    rows = db.execute(select(SecurityAlert).order_by(SecurityAlert.created_at.desc()).limit(200))
    return [AlertOut.model_validate(a, from_attributes=True) for a in rows.scalars()]
