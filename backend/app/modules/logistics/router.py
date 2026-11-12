"""Logistics API (``/api/v1/logistics``). Logistics' section; the Director sees all."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.modules.crm.models import Customer
from app.platform.authz.deps import DbSession, Principal, require

from . import schemas
from . import service as lgx
from .models import DeliveryNote, Shipment

router = APIRouter(prefix="/logistics", tags=["logistics"])

View = Depends(require("logistics.records.view"))
Edit = Depends(require("logistics.records.edit"))


@router.get("/summary", response_model=schemas.LogisticsSummary)
def summary(db: DbSession, _: Principal = View) -> schemas.LogisticsSummary:
    return lgx.summary(db)


@router.get("/shipments", response_model=list[schemas.ShipmentOut])
def list_shipments(
    db: DbSession,
    _: Principal = View,
    status: str | None = Query(default=None, max_length=12),
    direction: str | None = Query(default=None, pattern="^(inbound|outbound)$"),
    active_only: bool = False,
) -> list[schemas.ShipmentOut]:
    stmt = select(Shipment).order_by(Shipment.eta.asc().nulls_last(), Shipment.created_at.desc())
    if status:
        stmt = stmt.where(Shipment.status == status)
    elif active_only:
        stmt = stmt.where(Shipment.status.not_in(lgx.CLOSED))
    if direction:
        stmt = stmt.where(Shipment.direction == direction)
    return lgx.shipments_out(db, list(db.execute(stmt.limit(500)).scalars()))


@router.post("/shipments", response_model=schemas.ShipmentDetail, status_code=201)
def create_shipment(
    body: schemas.ShipmentIn, db: DbSession, principal: Principal = Edit
) -> schemas.ShipmentDetail:
    row = lgx.create_shipment(db, body, principal.user.id)
    db.commit()
    return lgx.shipment_detail(db, row)


@router.get("/shipments/{shipment_id}", response_model=schemas.ShipmentDetail)
def get_shipment(
    shipment_id: uuid.UUID, db: DbSession, _: Principal = View
) -> schemas.ShipmentDetail:
    return lgx.shipment_detail(db, lgx.get_shipment(db, shipment_id))


@router.post("/shipments/{shipment_id}/status", response_model=schemas.ShipmentDetail)
def update_status(
    shipment_id: uuid.UUID, body: schemas.StatusIn, db: DbSession, principal: Principal = Edit
) -> schemas.ShipmentDetail:
    row = lgx.update_status(db, lgx.get_shipment(db, shipment_id), body, principal.user.id)
    db.commit()
    return lgx.shipment_detail(db, row)


@router.post("/shipments/{shipment_id}/documents", response_model=schemas.ShipmentDetail)
def add_document(
    shipment_id: uuid.UUID, body: schemas.DocumentIn, db: DbSession, principal: Principal = Edit
) -> schemas.ShipmentDetail:
    row = lgx.get_shipment(db, shipment_id)
    lgx.add_document(db, row, body, principal.user.id)
    db.commit()
    return lgx.shipment_detail(db, row)


@router.get("/delivery-notes", response_model=list[schemas.DeliveryNoteOut])
def list_notes(
    db: DbSession, _: Principal = View, status: str | None = Query(default=None, max_length=12)
) -> list[schemas.DeliveryNoteOut]:
    stmt = select(DeliveryNote).order_by(DeliveryNote.created_at.desc()).limit(500)
    if status:
        stmt = stmt.where(DeliveryNote.status == status)
    return lgx.notes_out(db, list(db.execute(stmt).scalars()))


@router.post("/delivery-notes", response_model=schemas.DeliveryNoteOut, status_code=201)
def create_note(
    body: schemas.DeliveryNoteIn, db: DbSession, principal: Principal = Edit
) -> schemas.DeliveryNoteOut:
    row = lgx.create_note(db, body, principal.user.id)
    db.commit()
    return lgx.notes_out(db, [row])[0]


@router.post("/delivery-notes/{note_id}/dispatch", response_model=schemas.DeliveryNoteOut)
def dispatch(
    note_id: uuid.UUID, db: DbSession, principal: Principal = Edit
) -> schemas.DeliveryNoteOut:
    row = lgx.dispatch(db, lgx.get_note(db, note_id), principal.user.id)
    db.commit()
    return lgx.notes_out(db, [row])[0]


@router.post("/delivery-notes/{note_id}/proof", response_model=schemas.DeliveryNoteOut)
def record_proof(
    note_id: uuid.UUID, body: schemas.ProofIn, db: DbSession, principal: Principal = Edit
) -> schemas.DeliveryNoteOut:
    row = lgx.record_proof(db, lgx.get_note(db, note_id), body, principal.user.id)
    db.commit()
    return lgx.notes_out(db, [row])[0]


@router.post("/delivery-notes/{note_id}/cancel", response_model=schemas.DeliveryNoteOut)
def cancel(
    note_id: uuid.UUID, body: schemas.CancelIn, db: DbSession, principal: Principal = Edit
) -> schemas.DeliveryNoteOut:
    row = lgx.cancel_note(db, lgx.get_note(db, note_id), body.reason, principal.user.id)
    db.commit()
    return lgx.notes_out(db, [row])[0]


@router.get("/customers")
def customers(db: DbSession, _: Principal = View) -> list[dict[str, str]]:
    """Names and references only, so Logistics can address deliveries without CRM access."""
    rows = db.execute(
        select(Customer.id, Customer.name, Customer.reference)
        .where(Customer.status != "archived")
        .order_by(Customer.name)
    ).all()
    return [{"id": str(i), "name": n, "reference": r} for i, n, r in rows]
