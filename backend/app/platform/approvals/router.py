"""Approval queue (``/api/v1/approvals``): requests the signed-in user may decide."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.core.errors import NotFoundError
from app.platform.approvals import service as approvals
from app.platform.approvals.models import ApprovalRequest
from app.platform.authz.deps import CurrentPrincipal, DbSession, require_step_up
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
