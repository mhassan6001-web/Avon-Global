"""Approval queue (``/api/v1/approvals``): requests the signed-in user may decide."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.core.errors import NotFoundError
from app.platform.approvals import service as approvals
from app.platform.approvals.models import ApprovalRequest
from app.platform.authz.deps import CurrentPrincipal, DbSession, Principal, require, require_step_up
from app.platform.identity.models import User

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalOut(BaseModel):
    id: uuid.UUID
    subject_type: str
    subject_id: str
    permission_required: str
    summary: str
    payload: dict[str, Any]
    status: str
    requested_by: str
    requested_by_id: uuid.UUID
    created_at: datetime
    decided_by: str | None
    decided_at: datetime | None
    decision_note: str | None
    can_decide: bool
    blocked_reason: str | None = None


class DecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approve: bool
    note: str | None = Field(default=None, max_length=2000)


def _out(
    db: DbSession, rows: list[ApprovalRequest], principal: CurrentPrincipal
) -> list[ApprovalOut]:
    ids = {r.requested_by for r in rows} | {r.decided_by for r in rows if r.decided_by}
    names = (
        dict(db.execute(select(User.id, User.display_name).where(User.id.in_(ids))).tuples().all())
        if ids
        else {}
    )
    # A pending request nobody else can decide is blocked, and says so.
    has_other: dict[tuple[str, uuid.UUID], bool] = {}

    def blocked(r: ApprovalRequest) -> str | None:
        if r.status != "pending":
            return None
        key = (r.permission_required, r.requested_by)
        if key not in has_other:
            has_other[key] = approvals.other_approver_exists(db, *key)
        return None if has_other[key] else approvals.NO_SECOND_APPROVER

    return [
        ApprovalOut(
            id=r.id,
            subject_type=r.subject_type,
            subject_id=r.subject_id,
            permission_required=r.permission_required,
            summary=r.summary,
            payload=r.payload,
            status=r.status,
            requested_by=names.get(r.requested_by, ""),
            requested_by_id=r.requested_by,
            created_at=r.created_at,
            decided_by=names.get(r.decided_by) if r.decided_by else None,
            decided_at=r.decided_at,
            decision_note=r.decision_note,
            can_decide=r.status == "pending"
            and r.requested_by != principal.user.id
            and principal.has(r.permission_required),
            blocked_reason=blocked(r),
        )
        for r in rows
    ]


@router.get("", response_model=list[ApprovalOut])
def list_approvals(
    principal: CurrentPrincipal,
    db: DbSession,
    view: Literal["to_decide", "mine", "decided"] = "to_decide",
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ApprovalOut]:
    """``to_decide``: pending requests this user may decide (never their own).
    ``mine``: requests this user raised. ``decided``: decided requests they may see."""
    stmt = select(ApprovalRequest)
    if view == "to_decide":
        stmt = stmt.where(
            ApprovalRequest.status == "pending",
            ApprovalRequest.requested_by != principal.user.id,
            ApprovalRequest.permission_required.in_(principal.permissions),
        ).order_by(ApprovalRequest.created_at.asc())
    elif view == "mine":
        stmt = stmt.where(ApprovalRequest.requested_by == principal.user.id).order_by(
            ApprovalRequest.created_at.desc()
        )
    else:
        stmt = stmt.where(
            ApprovalRequest.status != "pending",
            ApprovalRequest.permission_required.in_(principal.permissions),
        ).order_by(ApprovalRequest.decided_at.desc())
    rows = list(db.execute(stmt.limit(limit)).scalars())
    return _out(db, rows, principal)


@router.post(
    "/{approval_id}/decide",
    response_model=ApprovalOut,
    dependencies=[Depends(require_step_up)],
)
def decide(
    approval_id: uuid.UUID, body: DecisionIn, principal: CurrentPrincipal, db: DbSession
) -> ApprovalOut:
    request = db.get(ApprovalRequest, approval_id)
    if request is None:
        raise NotFoundError("Approval request not found.")
    approvals.decide(db, principal=principal, request=request, approve=body.approve, note=body.note)
    db.commit()
    return _out(db, [request], principal)[0]


class RuleOut(BaseModel):
    key: str
    label: str
    permission: str
    configurable: bool
    note: str
    enabled: bool
    threshold: Decimal | None
    functional_currency: str
    second_approver_exists: bool


class RuleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    threshold: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)


def _rules_out(db: DbSession, principal: Principal) -> list[RuleOut]:
    from app.modules.finance.posting import functional_currency

    currency = functional_currency(db)
    out = []
    for spec in approvals.RULES:
        enabled, threshold = approvals.get_rule(db, spec.key) if spec.configurable else (True, None)
        out.append(
            RuleOut(
                key=spec.key,
                label=spec.label,
                permission=spec.permission,
                configurable=spec.configurable,
                note=spec.note,
                enabled=enabled,
                threshold=threshold,
                functional_currency=currency,
                second_approver_exists=approvals.other_approver_exists(
                    db, spec.permission, principal.user.id
                ),
            )
        )
    return out


@router.get("/rules", response_model=list[RuleOut])
def list_rules(
    db: DbSession, principal: Principal = Depends(require("admin.permissions.manage"))
) -> list[RuleOut]:
    """Approval limits and whether a second approver exists for each control."""
    return _rules_out(db, principal)


@router.put("/rules/{key}", response_model=list[RuleOut], dependencies=[Depends(require_step_up)])
def put_rule(
    key: str,
    body: RuleIn,
    db: DbSession,
    principal: Principal = Depends(require("admin.permissions.manage")),
) -> list[RuleOut]:
    approvals.set_rule(db, key, body.enabled, body.threshold, principal)
    db.commit()
    return _rules_out(db, principal)
