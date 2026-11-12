"""Approval requests and separation of duties.

Business modules (from Stage 4) create requests for restricted actions; a
*different* user holding the required permission decides them, after step-up.
The database also enforces ``decided_by <> requested_by``.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, PermissionDeniedError
from app.platform.approvals.models import ApprovalRequest
from app.platform.audit import service as audit
from app.platform.authz.catalogue import PERMISSION_CODES
from app.platform.authz.deps import Principal
from app.platform.identity import service as identity


class SelfApprovalError(PermissionDeniedError):
    code = "self_approval_forbidden"
    message = "You cannot approve a request you created."


def ensure_not_self_approval(requested_by: uuid.UUID, decider: uuid.UUID) -> None:
    if requested_by == decider:
        raise SelfApprovalError()


def create_request(
    db: Session,
    *,
    principal: Principal,
    subject_type: str,
    subject_id: str,
    permission_required: str,
    summary: str,
    payload: dict[str, Any] | None = None,
) -> ApprovalRequest:
    if permission_required not in PERMISSION_CODES:
        raise ValueError(f"unknown permission {permission_required!r}")
    req = ApprovalRequest(
        subject_type=subject_type,
        subject_id=subject_id,
        permission_required=permission_required,
        summary=summary,
        payload=payload or {},
        requested_by=principal.user.id,
    )
    db.add(req)
    db.flush()
    audit.record(
        db,
        action="approval.requested",
        actor_id=principal.user.id,
        target_type=subject_type,
        target_id=subject_id,
        details={"approval_id": str(req.id), "permission": permission_required},
    )
    return req


def decide(
    db: Session,
    *,
    principal: Principal,
    request: ApprovalRequest,
    approve: bool,
    note: str | None = None,
) -> ApprovalRequest:
    if request.status != "pending":
        raise ConflictError("This request has already been decided.")
    ensure_not_self_approval(request.requested_by, principal.user.id)
    if not principal.has(request.permission_required):
        raise PermissionDeniedError()
    if not identity.has_recent_step_up(principal.session):
        from app.platform.authz.deps import StepUpRequiredError

        raise StepUpRequiredError()
    request.status = "approved" if approve else "rejected"
    request.decided_by = principal.user.id
    request.decided_at = identity.now()
    request.decision_note = note
    audit.record(
        db,
        action=f"approval.{request.status}",
        actor_id=principal.user.id,
        target_type=request.subject_type,
        target_id=request.subject_id,
        details={"approval_id": str(request.id)},
    )
    db.flush()
    return request
