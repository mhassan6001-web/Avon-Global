"""Tender API (``/api/v1/tenders``). Business Development's section; Director approves bids."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.platform.authz.deps import DbSession, Principal, require

from . import schemas
from . import service as tenders

router = APIRouter(prefix="/tenders", tags=["tenders"])

View = Depends(require("tenders.records.view"))
Edit = Depends(require("tenders.records.edit"))


@router.get("/summary", response_model=schemas.TenderSummary)
def get_summary(db: DbSession, _: Principal = View) -> schemas.TenderSummary:
    return tenders.summary(db)


@router.get("", response_model=schemas.Page[schemas.TenderOut])
def list_tenders(
    db: DbSession,
    _: Principal = View,
    q: str | None = Query(default=None, max_length=100),
    status: schemas.Status | None = None,
    kind: schemas.Kind | None = None,
    active_only: bool = False,
    due_within_days: int | None = Query(default=None, ge=1, le=365),
    page: int = Query(default=1, ge=1, le=10_000),
    size: int = Query(default=25, ge=1, le=100),
) -> schemas.Page[schemas.TenderOut]:
    return tenders.list_tenders(
        db,
        q=q.strip() if q else None,
        status=status,
        kind=kind,
        active_only=active_only,
        due_within_days=due_within_days,
        page=page,
        size=size,
    )


@router.post("", response_model=schemas.TenderDetail, status_code=201)
def create_tender(
    body: schemas.TenderIn, db: DbSession, principal: Principal = Edit
) -> schemas.TenderDetail:
    row = tenders.create(db, body, principal.user.id)
    db.commit()
    return tenders.detail(db, row)


@router.get("/{tender_id}", response_model=schemas.TenderDetail)
def get_tender(tender_id: uuid.UUID, db: DbSession, _: Principal = View) -> schemas.TenderDetail:
    return tenders.detail(db, tenders.get(db, tender_id))


@router.patch("/{tender_id}", response_model=schemas.TenderDetail)
def update_tender(
    tender_id: uuid.UUID, body: schemas.TenderPatch, db: DbSession, principal: Principal = Edit
) -> schemas.TenderDetail:
    row = tenders.update(db, tenders.get(db, tender_id), body, principal.user.id)
    db.commit()
    return tenders.detail(db, row)


@router.post("/{tender_id}/requirements", response_model=schemas.RequirementOut, status_code=201)
def add_requirement(
    tender_id: uuid.UUID, body: schemas.RequirementIn, db: DbSession, principal: Principal = Edit
) -> schemas.RequirementOut:
    req = tenders.add_requirement(db, tenders.get(db, tender_id), body, principal.user.id)
    db.commit()
    return schemas.RequirementOut.model_validate(req)


@router.patch("/requirements/{requirement_id}", response_model=schemas.RequirementOut)
def update_requirement(
    requirement_id: uuid.UUID,
    body: schemas.RequirementPatch,
    db: DbSession,
    principal: Principal = Edit,
) -> schemas.RequirementOut:
    req = tenders.update_requirement(db, requirement_id, body, principal.user.id)
    db.commit()
    return schemas.RequirementOut.model_validate(req)


@router.delete("/requirements/{requirement_id}", response_model=schemas.TenderDetail)
def delete_requirement(
    requirement_id: uuid.UUID, db: DbSession, principal: Principal = Edit
) -> schemas.TenderDetail:
    _, row = tenders.get_requirement(db, requirement_id)
    tenders.delete_requirement(db, requirement_id, principal.user.id)
    db.commit()
    return tenders.detail(db, row)


@router.post("/{tender_id}/request-approval", response_model=schemas.TenderDetail)
def request_approval(
    tender_id: uuid.UUID,
    body: schemas.RequestApprovalIn,
    db: DbSession,
    principal: Principal = Edit,
) -> schemas.TenderDetail:
    row = tenders.request_approval(db, tenders.get(db, tender_id), principal, body.note)
    db.commit()
    return tenders.detail(db, row)


@router.post("/{tender_id}/submitted", response_model=schemas.TenderDetail)
def mark_submitted(
    tender_id: uuid.UUID, body: schemas.SubmittedIn, db: DbSession, principal: Principal = Edit
) -> schemas.TenderDetail:
    row = tenders.mark_submitted(db, tenders.get(db, tender_id), body, principal.user.id)
    db.commit()
    return tenders.detail(db, row)


@router.post("/{tender_id}/outcome", response_model=schemas.TenderDetail)
def record_outcome(
    tender_id: uuid.UUID, body: schemas.OutcomeIn, db: DbSession, principal: Principal = Edit
) -> schemas.TenderDetail:
    row = tenders.record_outcome(db, tenders.get(db, tender_id), body, principal.user.id)
    db.commit()
    return tenders.detail(db, row)


@router.post("/{tender_id}/no-bid", response_model=schemas.TenderDetail)
def no_bid(
    tender_id: uuid.UUID, body: schemas.NoBidIn, db: DbSession, principal: Principal = Edit
) -> schemas.TenderDetail:
    row = tenders.no_bid(db, tenders.get(db, tender_id), body, principal.user.id)
    db.commit()
    return tenders.detail(db, row)
