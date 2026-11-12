"""CRM business rules. Routers stay thin; every change is audited here."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.platform.audit import service as audit
from app.platform.identity.models import User

from . import schemas
from .models import OPEN_STAGES, STAGES, Activity, Contact, Customer, Opportunity


class CrmValidationError(AppError):
    status_code = 422
    code = "validation_error"


def now() -> datetime:
    return datetime.now(UTC)


def _next_reference(db: Session, sequence: str, prefix: str) -> str:
    value = db.execute(text(f"SELECT nextval('{sequence}')")).scalar_one()  # nosec B608 - fixed names
    return f"{prefix}-{int(value):05d}"


def _users(db: Session, ids: set[uuid.UUID | None]) -> dict[uuid.UUID, schemas.UserRef]:
    wanted = {i for i in ids if i}
    if not wanted:
        return {}
    rows = db.execute(select(User.id, User.display_name).where(User.id.in_(wanted))).all()
    return {r.id: schemas.UserRef(id=r.id, display_name=r.display_name) for r in rows}


def _check_user(db: Session, user_id: uuid.UUID | None) -> None:
    if user_id is not None and db.get(User, user_id) is None:
        raise CrmValidationError("The selected owner does not exist.")


# --- Customers --------------------------------------------------------------


def get_customer(db: Session, customer_id: uuid.UUID) -> Customer:
    row = db.get(Customer, customer_id)
    if row is None:
        raise NotFoundError("Customer not found.")
    return row


def customer_out(db: Session, row: Customer, open_count: int | None = None) -> schemas.CustomerOut:
    users = _users(db, {row.owner_id})
    if open_count is None:
        open_count = db.execute(
            select(func.count())
            .select_from(Opportunity)
            .where(Opportunity.customer_id == row.id, Opportunity.stage.in_(OPEN_STAGES))
        ).scalar_one()
    out = schemas.CustomerOut.model_validate(row, from_attributes=True)
    out.owner = users.get(row.owner_id) if row.owner_id else None
    out.open_opportunities = open_count
    return out


def list_customers(
    db: Session,
    *,
    q: str | None,
    status: str | None,
    country: str | None,
    owner_id: uuid.UUID | None,
    include_archived: bool,
    page: int,
    size: int,
) -> schemas.Page[schemas.CustomerOut]:
    stmt: Select[Any] = select(Customer)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Customer.name).like(like),
                func.lower(Customer.reference).like(like),
                func.lower(func.coalesce(Customer.industry, "")).like(like),
                func.lower(func.coalesce(Customer.city, "")).like(like),
            )
        )
    if status:
        stmt = stmt.where(Customer.status == status)
    elif not include_archived:
        stmt = stmt.where(Customer.status != "archived")
    if country:
        stmt = stmt.where(Customer.country_code == country)
    if owner_id:
        stmt = stmt.where(Customer.owner_id == owner_id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(func.lower(Customer.name), Customer.id)
            .offset((page - 1) * size)
            .limit(size)
        ).scalars()
    )
    counts: dict[uuid.UUID, int] = (
        dict(
            db.execute(
                select(Opportunity.customer_id, func.count())
                .where(
                    Opportunity.customer_id.in_([r.id for r in rows]),
                    Opportunity.stage.in_(OPEN_STAGES),
                )
                .group_by(Opportunity.customer_id)
            )
            .tuples()
            .all()
        )
        if rows
        else {}
    )
    users = _users(db, {r.owner_id for r in rows})
    items = []
    for r in rows:
        out = schemas.CustomerOut.model_validate(r, from_attributes=True)
        out.owner = users.get(r.owner_id) if r.owner_id else None
        out.open_opportunities = counts.get(r.id, 0)
        items.append(out)
    return schemas.Page[schemas.CustomerOut](items=items, total=total, page=page, size=size)


def create_customer(db: Session, body: schemas.CustomerIn, actor: uuid.UUID) -> Customer:
    _check_user(db, body.owner_id)
    duplicate = db.execute(
        select(Customer.reference).where(
            func.lower(Customer.name) == body.name.lower(), Customer.status != "archived"
        )
    ).scalar_one_or_none()
    if duplicate:
        raise ConflictError(f"A customer with this name already exists ({duplicate}).")
    row = Customer(
        reference=_next_reference(db, "crm_customer_ref_seq", "CUS"),
        created_by=actor,
        **body.model_dump(),
    )
    db.add(row)
    db.flush()
    audit.record(
        db,
        action="crm.customer.created",
        actor_id=actor,
        target_type="crm_customer",
        target_id=row.id,
        details={"reference": row.reference, "name": row.name},
    )
    return row


def update_customer(
    db: Session, row: Customer, body: schemas.CustomerPatch, actor: uuid.UUID
) -> Customer:
    if row.status == "archived":
        raise ConflictError("Archived customers cannot be edited. Restore it first.")
    changes = body.model_dump(exclude_unset=True)
    if "owner_id" in changes:
        _check_user(db, changes["owner_id"])
    if "name" in changes and changes["name"] is None:
        raise CrmValidationError("Name cannot be empty.")
    changed = {k: v for k, v in changes.items() if getattr(row, k) != v}
    for key, value in changed.items():
        setattr(row, key, value)
    if changed:
        audit.record(
            db,
            action="crm.customer.updated",
            actor_id=actor,
            target_type="crm_customer",
            target_id=row.id,
            details={"fields": sorted(changed)},
        )
    return row


def set_archived(db: Session, row: Customer, archived: bool, actor: uuid.UUID) -> Customer:
    if archived and row.status == "archived":
        return row
    if archived:
        open_count = db.execute(
            select(func.count())
            .select_from(Opportunity)
            .where(Opportunity.customer_id == row.id, Opportunity.stage.in_(OPEN_STAGES))
        ).scalar_one()
        if open_count:
            raise ConflictError("Close or reassign this customer's open opportunities first.")
    row.status = "archived" if archived else "inactive"
    audit.record(
        db,
        action="crm.customer.archived" if archived else "crm.customer.restored",
        actor_id=actor,
        target_type="crm_customer",
        target_id=row.id,
    )
    return row


# --- Contacts ---------------------------------------------------------------


def add_contact(
    db: Session, customer: Customer, body: schemas.ContactIn, actor: uuid.UUID
) -> Contact:
    if body.is_primary:
        for c in db.execute(select(Contact).where(Contact.customer_id == customer.id)).scalars():
            c.is_primary = False
    row = Contact(customer_id=customer.id, created_by=actor, **body.model_dump())
    db.add(row)
    db.flush()
    audit.record(
        db,
        action="crm.contact.created",
        actor_id=actor,
        target_type="crm_contact",
        target_id=row.id,
        details={"customer": customer.reference},
    )
    return row


def update_contact(db: Session, row: Contact, body: schemas.ContactIn, actor: uuid.UUID) -> Contact:
    if body.is_primary and not row.is_primary:
        for c in db.execute(
            select(Contact).where(Contact.customer_id == row.customer_id, Contact.id != row.id)
        ).scalars():
            c.is_primary = False
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    audit.record(
        db,
        action="crm.contact.updated",
        actor_id=actor,
        target_type="crm_contact",
        target_id=row.id,
    )
    return row


def delete_contact(db: Session, row: Contact, actor: uuid.UUID) -> None:
    audit.record(
        db,
        action="crm.contact.deleted",
        actor_id=actor,
        target_type="crm_contact",
        target_id=row.id,
        details={"name": row.name},
    )
    db.delete(row)


# --- Opportunities ----------------------------------------------------------


def opportunities_out(db: Session, rows: list[Opportunity]) -> list[schemas.OpportunityOut]:
    names: dict[uuid.UUID, str] = (
        dict(
            db.execute(
                select(Customer.id, Customer.name).where(
                    Customer.id.in_({r.customer_id for r in rows})
                )
            )
            .tuples()
            .all()
        )
        if rows
        else {}
    )
    users = _users(db, {r.owner_id for r in rows})
    return [
        schemas.OpportunityOut(
            id=r.id,
            reference=r.reference,
            customer_id=r.customer_id,
            customer_name=names.get(r.customer_id, ""),
            title=r.title,
            division=r.division,
            stage=r.stage,
            value_amount=r.value_amount,
            currency=r.currency,
            probability=r.probability,
            expected_close=r.expected_close,
            lost_reason=r.lost_reason,
            closed_at=r.closed_at,
            owner=users.get(r.owner_id) if r.owner_id else None,
            is_demo=r.is_demo,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


def list_opportunities(
    db: Session,
    *,
    q: str | None,
    stage: str | None,
    division: str | None,
    customer_id: uuid.UUID | None,
    open_only: bool,
    page: int,
    size: int,
) -> schemas.Page[schemas.OpportunityOut]:
    stmt: Select[Any] = select(Opportunity).join(Customer, Customer.id == Opportunity.customer_id)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Opportunity.title).like(like),
                func.lower(Opportunity.reference).like(like),
                func.lower(Customer.name).like(like),
            )
        )
    if stage:
        stmt = stmt.where(Opportunity.stage == stage)
    elif open_only:
        stmt = stmt.where(Opportunity.stage.in_(OPEN_STAGES))
    if division:
        stmt = stmt.where(Opportunity.division == division)
    if customer_id:
        stmt = stmt.where(Opportunity.customer_id == customer_id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(
                Opportunity.expected_close.asc().nulls_last(), Opportunity.created_at.desc()
            )
            .offset((page - 1) * size)
            .limit(size)
        ).scalars()
    )
    return schemas.Page[schemas.OpportunityOut](
        items=opportunities_out(db, rows), total=total, page=page, size=size
    )


def get_opportunity(db: Session, opportunity_id: uuid.UUID) -> Opportunity:
    row = db.get(Opportunity, opportunity_id)
    if row is None:
        raise NotFoundError("Opportunity not found.")
    return row


def create_opportunity(db: Session, body: schemas.OpportunityIn, actor: uuid.UUID) -> Opportunity:
    customer = get_customer(db, body.customer_id)
    if customer.status == "archived":
        raise ConflictError("Cannot add an opportunity to an archived customer.")
    _check_user(db, body.owner_id)
    row = Opportunity(
        reference=_next_reference(db, "crm_opportunity_ref_seq", "OPP"),
        created_by=actor,
        **body.model_dump(),
    )
    db.add(row)
    db.flush()
    audit.record(
        db,
        action="crm.opportunity.created",
        actor_id=actor,
        target_type="crm_opportunity",
        target_id=row.id,
        details={"reference": row.reference, "customer": customer.reference, "stage": row.stage},
    )
    return row


def update_opportunity(
    db: Session, row: Opportunity, body: schemas.OpportunityPatch, actor: uuid.UUID
) -> Opportunity:
    changes = body.model_dump(exclude_unset=True)
    if "owner_id" in changes:
        _check_user(db, changes["owner_id"])
    for required in ("title", "division", "stage", "currency", "probability"):
        if required in changes and changes[required] is None:
            raise CrmValidationError(f"{required} cannot be empty.")
    new_stage = changes.get("stage", row.stage)
    if new_stage not in STAGES:
        raise CrmValidationError("Unknown stage.")
    if new_stage != "lost":
        changes["lost_reason"] = None
    if new_stage in ("won", "lost") and row.stage not in ("won", "lost"):
        changes["closed_at"] = now()
        changes["probability"] = 100 if new_stage == "won" else 0
    elif new_stage not in ("won", "lost"):
        changes["closed_at"] = None
    changed = {k: v for k, v in changes.items() if getattr(row, k) != v}
    for key, value in changed.items():
        setattr(row, key, value)
    if changed:
        audit.record(
            db,
            action="crm.opportunity.updated",
            actor_id=actor,
            target_type="crm_opportunity",
            target_id=row.id,
            details={"fields": sorted(changed), "stage": row.stage},
        )
    return row


# --- Activities -------------------------------------------------------------


def activities_out(db: Session, rows: list[Activity]) -> list[schemas.ActivityOut]:
    names: dict[uuid.UUID, str] = (
        dict(
            db.execute(
                select(Customer.id, Customer.name).where(
                    Customer.id.in_({r.customer_id for r in rows})
                )
            )
            .tuples()
            .all()
        )
        if rows
        else {}
    )
    users = _users(db, {r.assigned_to for r in rows} | {r.created_by for r in rows})
    return [
        schemas.ActivityOut(
            id=r.id,
            customer_id=r.customer_id,
            customer_name=names.get(r.customer_id, ""),
            opportunity_id=r.opportunity_id,
            kind=r.kind,
            subject=r.subject,
            body=r.body,
            occurred_at=r.occurred_at,
            due_at=r.due_at,
            completed_at=r.completed_at,
            assigned_to=users.get(r.assigned_to) if r.assigned_to else None,
            created_by=users.get(r.created_by),
            created_at=r.created_at,
        )
        for r in rows
    ]


def create_activity(db: Session, body: schemas.ActivityIn, actor: uuid.UUID) -> Activity:
    customer = get_customer(db, body.customer_id)
    if body.opportunity_id:
        opp = get_opportunity(db, body.opportunity_id)
        if opp.customer_id != customer.id:
            raise CrmValidationError("The opportunity belongs to a different customer.")
    _check_user(db, body.assigned_to)
    data = body.model_dump()
    if data["kind"] != "follow_up" and data["occurred_at"] is None:
        data["occurred_at"] = now()
    row = Activity(created_by=actor, **data)
    if row.kind == "follow_up" and row.assigned_to is None:
        row.assigned_to = actor
    db.add(row)
    db.flush()
    audit.record(
        db,
        action="crm.activity.created",
        actor_id=actor,
        target_type="crm_activity",
        target_id=row.id,
        details={"kind": row.kind, "customer": customer.reference},
    )
    return row


def list_activities(
    db: Session,
    *,
    customer_id: uuid.UUID | None,
    due: str | None,
    assigned_to: uuid.UUID | None,
    limit: int,
) -> list[schemas.ActivityOut]:
    stmt: Select[Any] = select(Activity)
    if customer_id:
        stmt = stmt.where(Activity.customer_id == customer_id)
    if assigned_to:
        stmt = stmt.where(Activity.assigned_to == assigned_to)
    t = now()
    if due == "overdue":
        stmt = stmt.where(Activity.completed_at.is_(None), Activity.due_at < t)
    elif due == "upcoming":
        stmt = stmt.where(
            Activity.completed_at.is_(None),
            Activity.due_at >= t,
            Activity.due_at < t + timedelta(days=7),
        )
    elif due == "open":
        stmt = stmt.where(Activity.completed_at.is_(None), Activity.due_at.is_not(None))
    order = (
        Activity.due_at.asc()
        if due
        else func.coalesce(Activity.occurred_at, Activity.due_at, Activity.created_at).desc()
    )
    rows = list(db.execute(stmt.order_by(order).limit(limit)).scalars())
    return activities_out(db, rows)


def complete_activity(db: Session, activity_id: uuid.UUID, actor: uuid.UUID) -> Activity:
    row = db.get(Activity, activity_id)
    if row is None:
        raise NotFoundError("Activity not found.")
    if row.completed_at is None:
        row.completed_at = now()
        audit.record(
            db,
            action="crm.activity.completed",
            actor_id=actor,
            target_type="crm_activity",
            target_id=row.id,
        )
    return row


# --- Summary ----------------------------------------------------------------


def summary(db: Session) -> schemas.CrmSummary:
    has_records = db.execute(select(func.count()).select_from(Customer)).scalar_one() > 0
    by_status: dict[str, int] = dict(
        db.execute(select(Customer.status, func.count()).group_by(Customer.status)).tuples().all()
    )
    pipeline_rows = db.execute(
        select(
            Opportunity.stage,
            Opportunity.currency,
            func.count(),
            func.coalesce(func.sum(Opportunity.value_amount), 0),
        ).group_by(Opportunity.stage, Opportunity.currency)
    ).all()
    counts: dict[str, int] = defaultdict(int)
    values: dict[str, dict[str, Decimal]] = defaultdict(dict)
    for stage, currency, count, total in pipeline_rows:
        counts[stage] += count
        values[stage][currency] = Decimal(total)
    t = now()
    overdue = db.execute(
        select(func.count())
        .select_from(Activity)
        .where(Activity.completed_at.is_(None), Activity.due_at < t)
    ).scalar_one()
    due_soon = db.execute(
        select(func.count())
        .select_from(Activity)
        .where(
            Activity.completed_at.is_(None),
            Activity.due_at >= t,
            Activity.due_at < t + timedelta(days=7),
        )
    ).scalar_one()
    return schemas.CrmSummary(
        has_records=has_records,
        customers_by_status=by_status,
        pipeline=[
            schemas.StageSummary(
                stage=s, count=counts.get(s, 0), value_by_currency=values.get(s, {})
            )
            for s in STAGES
        ],
        follow_ups_overdue=overdue,
        follow_ups_due_7_days=due_soon,
    )
