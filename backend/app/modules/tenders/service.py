"""Tender rules. Submission is a human action after Director approval; AI never submits."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.modules.crm.models import Customer
from app.platform.approvals import service as approvals
from app.platform.approvals.models import ApprovalRequest
from app.platform.audit import service as audit
from app.platform.authz.deps import Principal
from app.platform.files.models import StoredFile
from app.platform.identity.models import User
from app.platform.references import next_reference

from . import schemas
from .models import ACTIVE, Requirement, Tender

APPROVAL_SUBJECT = "tender_submission"
APPROVAL_PERMISSION = "tenders.submission.approve"
LOCKED = ("awaiting_approval", "approved")  # core details frozen while approval is pending/given
EDITABLE_WHEN_LOCKED = {"notes", "owner_id"}


class TenderRuleError(AppError):
    status_code = 422
    code = "validation_error"


def now() -> datetime:
    return datetime.now(UTC)


def _audit(db: Session, action: str, actor: uuid.UUID, tender: Tender, **details: Any) -> None:
    audit.record(
        db,
        action=f"tenders.{action}",
        actor_id=actor,
        target_type="tender",
        target_id=tender.id,
        details={"reference": tender.reference, **details},
    )


def _check_refs(db: Session, customer_id: uuid.UUID | None, owner_id: uuid.UUID | None) -> None:
    if customer_id is not None and db.get(Customer, customer_id) is None:
        raise TenderRuleError("The linked customer does not exist.")
    if owner_id is not None and db.get(User, owner_id) is None:
        raise TenderRuleError("The selected owner does not exist.")


def get(db: Session, tender_id: uuid.UUID) -> Tender:
    row = db.get(Tender, tender_id)
    if row is None:
        raise NotFoundError("Tender not found.")
    return row


def to_out(db: Session, rows: list[Tender]) -> list[schemas.TenderOut]:
    if not rows:
        return []
    ids = [r.id for r in rows]
    req_counts: dict[uuid.UUID, tuple[int, int]] = {}
    for tender_id, total, open_ in db.execute(
        select(
            Requirement.tender_id,
            func.count(),
            func.count().filter(
                Requirement.mandatory, Requirement.status.in_(("pending", "not_met"))
            ),
        )
        .where(Requirement.tender_id.in_(ids))
        .group_by(Requirement.tender_id)
    ).all():
        req_counts[tender_id] = (total, open_)
    user_ids = {r.owner_id for r in rows} | {r.submitted_by for r in rows}
    users = {
        uid: schemas.UserRef(id=uid, display_name=name)
        for uid, name in db.execute(
            select(User.id, User.display_name).where(User.id.in_({u for u in user_ids if u}))
        ).tuples()
    }
    out = []
    for r in rows:
        total, open_ = req_counts.get(r.id, (0, 0))
        out.append(
            schemas.TenderOut(
                id=r.id,
                reference=r.reference,
                issuer_reference=r.issuer_reference,
                title=r.title,
                issuer_name=r.issuer_name,
                customer_id=r.customer_id,
                kind=r.kind,
                division=r.division,
                country_code=r.country_code,
                source=r.source,
                published_on=r.published_on,
                clarification_deadline=r.clarification_deadline,
                submission_deadline=r.submission_deadline,
                submission_method=r.submission_method,
                bid_security_required=r.bid_security_required,
                estimated_value=r.estimated_value,
                currency=r.currency,
                status=r.status,
                notes=r.notes,
                approval_id=r.approval_id,
                submitted_at=r.submitted_at,
                submitted_by=users.get(r.submitted_by) if r.submitted_by else None,
                award_value=r.award_value,
                outcome_note=r.outcome_note,
                owner=users.get(r.owner_id) if r.owner_id else None,
                created_at=r.created_at,
                updated_at=r.updated_at,
                requirements_total=total,
                requirements_open=open_,
            )
        )
    return out


def detail(db: Session, row: Tender) -> schemas.TenderDetail:
    reqs = db.execute(
        select(Requirement)
        .where(Requirement.tender_id == row.id)
        .order_by(Requirement.kind, Requirement.created_at)
    ).scalars()
    approval = None
    if row.approval_id:
        a = db.get_one(ApprovalRequest, row.approval_id)
        names = dict(
            db.execute(
                select(User.id, User.display_name).where(
                    User.id.in_({a.requested_by, a.decided_by} - {None})
                )
            ).tuples()
        )
        approval = schemas.ApprovalInfo(
            id=a.id,
            status=a.status,
            requested_by=names.get(a.requested_by, ""),
            decided_by=names.get(a.decided_by) if a.decided_by else None,
            decided_at=a.decided_at,
            decision_note=a.decision_note,
        )
    return schemas.TenderDetail(
        tender=to_out(db, [row])[0],
        requirements=[schemas.RequirementOut.model_validate(r) for r in reqs],
        approval=approval,
    )


def list_tenders(
    db: Session,
    *,
    q: str | None,
    status: str | None,
    kind: str | None,
    active_only: bool,
    due_within_days: int | None,
    page: int,
    size: int,
) -> schemas.Page[schemas.TenderOut]:
    stmt: Select[Any] = select(Tender)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Tender.title).like(like),
                func.lower(Tender.reference).like(like),
                func.lower(Tender.issuer_name).like(like),
                func.lower(func.coalesce(Tender.issuer_reference, "")).like(like),
            )
        )
    if status:
        stmt = stmt.where(Tender.status == status)
    elif active_only:
        stmt = stmt.where(Tender.status.in_(ACTIVE))
    if kind:
        stmt = stmt.where(Tender.kind == kind)
    if due_within_days is not None:
        t = now()
        stmt = stmt.where(
            Tender.status.in_(ACTIVE),
            Tender.submission_deadline >= t,
            Tender.submission_deadline < t + timedelta(days=due_within_days),
        )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(Tender.submission_deadline.asc(), Tender.id)
            .offset((page - 1) * size)
            .limit(size)
        ).scalars()
    )
    return schemas.Page[schemas.TenderOut](
        items=to_out(db, rows), total=total, page=page, size=size
    )


def create(db: Session, body: schemas.TenderIn, actor: uuid.UUID) -> Tender:
    _check_refs(db, body.customer_id, body.owner_id)
    row = Tender(reference=next_reference(db, "TND"), created_by=actor, **body.model_dump())
    db.add(row)
    db.flush()
    _audit(db, "created", actor, row, kind=row.kind)
    return row


def update(db: Session, row: Tender, body: schemas.TenderPatch, actor: uuid.UUID) -> Tender:
    changes = body.model_dump(exclude_unset=True)
    if row.status not in ACTIVE:
        raise ConflictError("This tender is closed and can no longer be edited.")
    if row.status in LOCKED and set(changes) - EDITABLE_WHEN_LOCKED:
        raise ConflictError(
            "Details are frozen while the bid is awaiting or holding approval. "
            "Only notes and owner can change."
        )
    for required in ("title", "issuer_name", "kind", "submission_deadline", "submission_method"):
        if required in changes and changes[required] is None:
            raise TenderRuleError(f"{required} cannot be empty.")
    _check_refs(db, changes.get("customer_id"), changes.get("owner_id"))
    deadline = changes.get("submission_deadline", row.submission_deadline)
    clarification = changes.get("clarification_deadline", row.clarification_deadline)
    if clarification and clarification > deadline:
        raise TenderRuleError("The clarification deadline must be before the submission deadline.")
    changed = {k: v for k, v in changes.items() if getattr(row, k) != v}
    for key, value in changed.items():
        setattr(row, key, value)
    if changed:
        _audit(db, "updated", actor, row, fields=sorted(changed))
    return row


def add_requirement(
    db: Session, row: Tender, body: schemas.RequirementIn, actor: uuid.UUID
) -> Requirement:
    if row.status not in ACTIVE or row.status in LOCKED:
        raise ConflictError("Requirements can only change before the bid goes for approval.")
    req = Requirement(tender_id=row.id, updated_by=actor, **body.model_dump())
    db.add(req)
    db.flush()
    _audit(db, "requirement.added", actor, row, requirement=str(req.id))
    return req


def get_requirement(db: Session, requirement_id: uuid.UUID) -> tuple[Requirement, Tender]:
    req = db.get(Requirement, requirement_id)
    if req is None:
        raise NotFoundError("Requirement not found.")
    return req, db.get_one(Tender, req.tender_id)


def update_requirement(
    db: Session, requirement_id: uuid.UUID, body: schemas.RequirementPatch, actor: uuid.UUID
) -> Requirement:
    req, tender = get_requirement(db, requirement_id)
    if tender.status not in ACTIVE or tender.status in LOCKED:
        raise ConflictError("Requirements can only change before the bid goes for approval.")
    changes = body.model_dump(exclude_unset=True)
    if changes.get("file_id"):
        stored = db.get(StoredFile, changes["file_id"])
        if stored is None or stored.module != "tenders":
            raise TenderRuleError("Attach a document uploaded to the Tenders section.")
    for key in ("description", "mandatory", "status"):
        if key in changes and changes[key] is None:
            raise TenderRuleError(f"{key} cannot be empty.")
    for key, value in changes.items():
        setattr(req, key, value)
    req.updated_by = actor
    _audit(
        db, "requirement.updated", actor, tender, requirement=str(req.id), fields=sorted(changes)
    )
    return req


def delete_requirement(db: Session, requirement_id: uuid.UUID, actor: uuid.UUID) -> None:
    req, tender = get_requirement(db, requirement_id)
    if tender.status not in ACTIVE or tender.status in LOCKED:
        raise ConflictError("Requirements can only change before the bid goes for approval.")
    _audit(db, "requirement.removed", actor, tender, description=req.description)
    db.delete(req)


def request_approval(db: Session, row: Tender, principal: Principal, note: str | None) -> Tender:
    if row.status not in ("reviewing", "bidding"):
        raise ConflictError("Only a tender in review or bidding can go for submission approval.")
    if row.submission_deadline <= now():
        raise ConflictError("The submission deadline has passed.")
    open_items = (
        db.execute(
            select(Requirement.description).where(
                Requirement.tender_id == row.id,
                Requirement.mandatory,
                Requirement.status.in_(("pending", "not_met")),
            )
        )
        .scalars()
        .all()
    )
    if open_items:
        raise ConflictError(
            "Every mandatory requirement must be met first.",
            details={"open_requirements": list(open_items)},
        )
    req = approvals.create_request(
        db,
        principal=principal,
        subject_type=APPROVAL_SUBJECT,
        subject_id=str(row.id),
        permission_required=APPROVAL_PERMISSION,
        summary=f"Submit bid {row.reference}: {row.title}",
        payload={
            "reference": row.reference,
            "issuer": row.issuer_name,
            "deadline": row.submission_deadline.isoformat(),
            "note": note,
        },
    )
    row.approval_id = req.id
    row.status = "awaiting_approval"
    _audit(db, "approval.requested", principal.user.id, row)
    return row


def _apply_decision(db: Session, request: ApprovalRequest) -> None:
    """Registered with the approvals service: runs in the decision's transaction."""
    row = db.get(Tender, uuid.UUID(request.subject_id))
    if row is None or row.approval_id != request.id or row.status != "awaiting_approval":
        raise ConflictError("The tender is no longer waiting for this approval.")
    row.status = "approved" if request.status == "approved" else "bidding"


approvals.register_handler(APPROVAL_SUBJECT, _apply_decision)


def mark_submitted(db: Session, row: Tender, body: schemas.SubmittedIn, actor: uuid.UUID) -> Tender:
    if row.status != "approved":
        raise ConflictError("A bid can be recorded as submitted only after Director approval.")
    when = body.submitted_at or now()
    if when > now() + timedelta(minutes=5):
        raise TenderRuleError("The submission time cannot be in the future.")
    if when > row.submission_deadline:
        raise ConflictError("That time is after the submission deadline.")
    row.status = "submitted"
    row.submitted_at = when
    row.submitted_by = actor
    if body.note:
        row.notes = f"{row.notes}\n\n{body.note}" if row.notes else body.note
    _audit(db, "submitted", actor, row)
    return row


def record_outcome(db: Session, row: Tender, body: schemas.OutcomeIn, actor: uuid.UUID) -> Tender:
    if body.result in ("won", "lost") and row.status != "submitted":
        raise ConflictError("Only a submitted bid can be won or lost.")
    if body.result == "cancelled" and row.status not in (*ACTIVE, "submitted"):
        raise ConflictError("This tender is already closed.")
    if row.status == "awaiting_approval" and row.approval_id:
        pending = db.get_one(ApprovalRequest, row.approval_id)
        if pending.status == "pending":
            pending.status = "cancelled"
    row.status = body.result
    row.award_value = body.award_value
    row.outcome_note = body.note
    _audit(db, f"outcome.{body.result}", actor, row)
    return row


def no_bid(db: Session, row: Tender, body: schemas.NoBidIn, actor: uuid.UUID) -> Tender:
    if row.status not in ("identified", "reviewing", "bidding"):
        raise ConflictError("A no-bid decision is only possible before approval is requested.")
    row.status = "no_bid"
    row.outcome_note = body.reason
    _audit(db, "no_bid", actor, row)
    return row


def summary(db: Session) -> schemas.TenderSummary:
    by_status = dict(
        db.execute(select(Tender.status, func.count()).group_by(Tender.status)).tuples().all()
    )
    t = now()
    due = db.execute(
        select(func.count())
        .select_from(Tender)
        .where(
            Tender.status.in_(ACTIVE),
            Tender.submission_deadline >= t,
            Tender.submission_deadline < t + timedelta(days=7),
        )
    ).scalar_one()
    overdue = db.execute(
        select(func.count())
        .select_from(Tender)
        .where(Tender.status.in_(ACTIVE), Tender.submission_deadline < t)
    ).scalar_one()
    won = by_status.get("won", 0)
    return schemas.TenderSummary(
        has_records=bool(by_status),
        by_status=by_status,
        active=sum(by_status.get(s, 0) for s in ACTIVE),
        due_within_7_days=due,
        overdue_unsubmitted=overdue,
        decided=won + by_status.get("lost", 0),
        won=won,
    )
