"""CRM API (``/api/v1/crm``). Business Development's section; the Director sees all."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core.errors import NotFoundError
from app.platform.authz.deps import DbSession, Principal, require

from . import schemas
from . import service as crm
from .models import Contact

router = APIRouter(prefix="/crm", tags=["crm"])

View = Depends(require("crm.records.view"))
Edit = Depends(require("crm.records.edit"))


@router.get("/summary", response_model=schemas.CrmSummary)
def get_summary(db: DbSession, _: Principal = View) -> schemas.CrmSummary:
    return crm.summary(db)


@router.get("/customers", response_model=schemas.Page[schemas.CustomerOut])
def list_customers(
    db: DbSession,
    _: Principal = View,
    q: str | None = Query(default=None, max_length=100),
    status: schemas.CustomerStatus | None = None,
    country: str | None = Query(default=None, pattern="^[A-Z]{2}$"),
    owner_id: uuid.UUID | None = None,
    include_archived: bool = False,
    page: int = Query(default=1, ge=1, le=10_000),
    size: int = Query(default=25, ge=1, le=100),
) -> schemas.Page[schemas.CustomerOut]:
    return crm.list_customers(
        db,
        q=q.strip() if q else None,
        status=status,
        country=country,
        owner_id=owner_id,
        include_archived=include_archived,
        page=page,
        size=size,
    )


@router.post("/customers", response_model=schemas.CustomerOut, status_code=201)
def create_customer(
    body: schemas.CustomerIn, db: DbSession, principal: Principal = Edit
) -> schemas.CustomerOut:
    row = crm.create_customer(db, body, principal.user.id)
    db.commit()
    return crm.customer_out(db, row, 0)


@router.get("/customers/{customer_id}", response_model=schemas.CustomerDetail)
def customer_detail(
    customer_id: uuid.UUID, db: DbSession, _: Principal = View
) -> schemas.CustomerDetail:
    row = crm.get_customer(db, customer_id)
    opps = crm.list_opportunities(
        db, q=None, stage=None, division=None, customer_id=row.id, open_only=False, page=1, size=100
    )
    contacts = db.execute(
        select(Contact)
        .where(Contact.customer_id == row.id)
        .order_by(Contact.is_primary.desc(), Contact.name)
    ).scalars()
    return schemas.CustomerDetail(
        customer=crm.customer_out(db, row),
        contacts=[schemas.ContactOut.model_validate(c) for c in contacts],
        opportunities=opps.items,
        activities=crm.list_activities(
            db, customer_id=row.id, due=None, assigned_to=None, limit=100
        ),
    )


@router.patch("/customers/{customer_id}", response_model=schemas.CustomerOut)
def update_customer(
    customer_id: uuid.UUID, body: schemas.CustomerPatch, db: DbSession, principal: Principal = Edit
) -> schemas.CustomerOut:
    row = crm.update_customer(db, crm.get_customer(db, customer_id), body, principal.user.id)
    db.commit()
    return crm.customer_out(db, row)


@router.post("/customers/{customer_id}/archive", response_model=schemas.CustomerOut)
def archive_customer(
    customer_id: uuid.UUID, db: DbSession, principal: Principal = Edit
) -> schemas.CustomerOut:
    row = crm.set_archived(db, crm.get_customer(db, customer_id), True, principal.user.id)
    db.commit()
    return crm.customer_out(db, row)


@router.post("/customers/{customer_id}/restore", response_model=schemas.CustomerOut)
def restore_customer(
    customer_id: uuid.UUID, db: DbSession, principal: Principal = Edit
) -> schemas.CustomerOut:
    row = crm.set_archived(db, crm.get_customer(db, customer_id), False, principal.user.id)
    db.commit()
    return crm.customer_out(db, row)


@router.post(
    "/customers/{customer_id}/contacts", response_model=schemas.ContactOut, status_code=201
)
def add_contact(
    customer_id: uuid.UUID, body: schemas.ContactIn, db: DbSession, principal: Principal = Edit
) -> schemas.ContactOut:
    row = crm.add_contact(db, crm.get_customer(db, customer_id), body, principal.user.id)
    db.commit()
    return schemas.ContactOut.model_validate(row)


def _contact(db: DbSession, contact_id: uuid.UUID) -> Contact:
    row = db.get(Contact, contact_id)
    if row is None:
        raise NotFoundError("Contact not found.")
    return row


@router.put("/contacts/{contact_id}", response_model=schemas.ContactOut)
def update_contact(
    contact_id: uuid.UUID, body: schemas.ContactIn, db: DbSession, principal: Principal = Edit
) -> schemas.ContactOut:
    row = crm.update_contact(db, _contact(db, contact_id), body, principal.user.id)
    db.commit()
    return schemas.ContactOut.model_validate(row)


@router.delete("/contacts/{contact_id}", response_model=schemas.ContactOut)
def delete_contact(
    contact_id: uuid.UUID, db: DbSession, principal: Principal = Edit
) -> schemas.ContactOut:
    row = _contact(db, contact_id)
    out = schemas.ContactOut.model_validate(row)
    crm.delete_contact(db, row, principal.user.id)
    db.commit()
    return out


@router.get("/opportunities", response_model=schemas.Page[schemas.OpportunityOut])
def list_opportunities(
    db: DbSession,
    _: Principal = View,
    q: str | None = Query(default=None, max_length=100),
    stage: schemas.Stage | None = None,
    division: schemas.Division | None = None,
    customer_id: uuid.UUID | None = None,
    open_only: bool = False,
    page: int = Query(default=1, ge=1, le=10_000),
    size: int = Query(default=25, ge=1, le=100),
) -> schemas.Page[schemas.OpportunityOut]:
    return crm.list_opportunities(
        db,
        q=q.strip() if q else None,
        stage=stage,
        division=division,
        customer_id=customer_id,
        open_only=open_only,
        page=page,
        size=size,
    )


@router.post("/opportunities", response_model=schemas.OpportunityOut, status_code=201)
def create_opportunity(
    body: schemas.OpportunityIn, db: DbSession, principal: Principal = Edit
) -> schemas.OpportunityOut:
    row = crm.create_opportunity(db, body, principal.user.id)
    db.commit()
    return crm.opportunities_out(db, [row])[0]


@router.patch("/opportunities/{opportunity_id}", response_model=schemas.OpportunityOut)
def update_opportunity(
    opportunity_id: uuid.UUID,
    body: schemas.OpportunityPatch,
    db: DbSession,
    principal: Principal = Edit,
) -> schemas.OpportunityOut:
    row = crm.update_opportunity(
        db, crm.get_opportunity(db, opportunity_id), body, principal.user.id
    )
    db.commit()
    return crm.opportunities_out(db, [row])[0]


@router.get("/activities", response_model=list[schemas.ActivityOut])
def list_activities(
    db: DbSession,
    principal: Principal = View,
    customer_id: uuid.UUID | None = None,
    due: Literal["overdue", "upcoming", "open"] | None = None,
    mine: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[schemas.ActivityOut]:
    return crm.list_activities(
        db,
        customer_id=customer_id,
        due=due,
        assigned_to=principal.user.id if mine else None,
        limit=limit,
    )


@router.post("/activities", response_model=schemas.ActivityOut, status_code=201)
def create_activity(
    body: schemas.ActivityIn, db: DbSession, principal: Principal = Edit
) -> schemas.ActivityOut:
    row = crm.create_activity(db, body, principal.user.id)
    db.commit()
    return crm.activities_out(db, [row])[0]


@router.post("/activities/{activity_id}/complete", response_model=schemas.ActivityOut)
def complete_activity(
    activity_id: uuid.UUID, db: DbSession, principal: Principal = Edit
) -> schemas.ActivityOut:
    row = crm.complete_activity(db, activity_id, principal.user.id)
    db.commit()
    return crm.activities_out(db, [row])[0]
