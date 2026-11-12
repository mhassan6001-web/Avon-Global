"""Approval requests and separation of duties.

Business modules (from Stage 4) create requests for restricted actions; a
*different* user holding the required permission decides them, after step-up.
The database also enforces ``decided_by <> requested_by``.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, PermissionDeniedError
from app.platform.approvals.models import ApprovalRequest, ApprovalRule
from app.platform.audit import service as audit
from app.platform.authz.catalogue import PERMISSION_CODES
from app.platform.authz.deps import Principal
from app.platform.identity import service as identity

# Business modules register a handler per subject type to apply a decision
# (e.g. a tender becomes "approved for submission"). Handlers run inside the
# same transaction as the decision, so both commit or neither does.
DecisionHandler = Callable[[Session, ApprovalRequest], None]
_HANDLERS: dict[str, DecisionHandler] = {}


def register_handler(subject_type: str, handler: DecisionHandler) -> None:
    _HANDLERS[subject_type] = handler


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
    handler = _HANDLERS.get(request.subject_type)
    if handler is not None:
        handler(db, request)
    return request


# --- Second approver -----------------------------------------------------------------

NO_SECOND_APPROVER = (
    "Blocked: no second authorised approver has been appointed. Nobody may approve "
    "their own request, so this stays pending until another approver exists."
)


def other_approver_exists(db: Session, permission: str, requester: uuid.UUID) -> bool:
    """Is there an active user, other than the requester, who may decide this?"""
    from app.platform.identity.models import User

    users = db.execute(select(User).where(User.status == "active", User.id != requester)).scalars()
    return any(permission in identity.permissions_of(db, user) for user in users)


# --- Configurable approval limits ----------------------------------------------------


@dataclass(frozen=True)
class RuleSpec:
    key: str
    label: str
    permission: str
    configurable: bool
    note: str


# Configurable rules have a row in ``sys_approval_rules``. The others are fixed
# controls, listed so the Director sees the whole picture in one place.
RULES: tuple[RuleSpec, ...] = (
    RuleSpec(
        "crm_quotation",
        "Quotations prepared by staff",
        "crm.quotation.approve",
        True,
        "Approval before a quotation is issued. A user who holds the approval "
        "permission issues their own quotations directly.",
    ),
    RuleSpec("tender_submission", "Tender bid submission", "tenders.submission.approve", False,
             "Always requires approval."),
    RuleSpec("purchase_order", "Purchase orders", "procurement.order.approve", False,
             "Always requires approval."),
    RuleSpec("supplier_bank_change", "Supplier bank detail changes",
             "procurement.supplier_bank.approve_change", False, "Always requires approval."),
    RuleSpec("finance_transaction", "Payments, credit notes, manual journals",
             "finance.transaction.approve", False, "Always requires approval."),
    RuleSpec("payroll_run", "Payroll runs", "hr.payroll.approve", False,
             "Always requires approval."),
)  # fmt: skip
RULE_BY_KEY = {r.key: r for r in RULES}


def get_rule(db: Session, key: str) -> tuple[bool, Decimal | None]:
    """(enabled, threshold) for a configurable rule. Default: every request needs approval."""
    row = db.get(ApprovalRule, key)
    return (True, None) if row is None else (row.enabled, row.threshold)


def needs_approval(db: Session, key: str, amount_functional: Decimal | None) -> bool:
    """``amount_functional`` is ``None`` when it could not be converted: approval is required."""
    enabled, threshold = get_rule(db, key)
    if not enabled:
        return False
    if threshold is None or amount_functional is None:
        return True
    return amount_functional >= threshold


def set_rule(
    db: Session, key: str, enabled: bool, threshold: Decimal | None, principal: Principal
) -> ApprovalRule:
    spec = RULE_BY_KEY.get(key)
    if spec is None or not spec.configurable:
        raise ConflictError("This approval rule is fixed and cannot be changed.")
    row = db.get(ApprovalRule, key)
    before = {"enabled": row.enabled, "threshold": str(row.threshold)} if row else {}
    if row is None:
        row = ApprovalRule(key=key)
        db.add(row)
    row.enabled, row.threshold = enabled, threshold
    row.updated_by, row.updated_at = principal.user.id, identity.now()
    audit.record(
        db,
        action="approval.rule_changed",
        actor_id=principal.user.id,
        target_type="approval_rule",
        target_id=key,
        details={"before": before, "after": {"enabled": enabled, "threshold": str(threshold)}},
    )
    db.flush()
    return row
