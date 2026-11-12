"""Shipments, customs documents and delivery notes with proof of delivery."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.modules.crm.models import Customer
from app.modules.finance.models import Invoice
from app.modules.inventory import service as inv
from app.modules.inventory.models import Product, Warehouse
from app.modules.procurement.models import PurchaseOrder, Supplier
from app.platform.audit import service as audit
from app.platform.files.models import StoredFile
from app.platform.identity.models import User
from app.platform.references import next_reference

from . import schemas
from .models import DeliveryNote, DeliveryNoteLine, Shipment, ShipmentDocument, ShipmentEvent

CLOSED = ("delivered", "cancelled")


class LogisticsRuleError(AppError):
    status_code = 422
    code = "validation_error"


def now() -> datetime:
    return datetime.now(UTC)


def _audit(
    db: Session, action: str, actor: uuid.UUID, kind: str, target: Any, **details: Any
) -> None:
    audit.record(
        db,
        action=f"logistics.{action}",
        actor_id=actor,
        target_type=kind,
        target_id=target,
        details=details,
    )


def _file(db: Session, file_id: uuid.UUID) -> StoredFile:
    f = db.get(StoredFile, file_id)
    if f is None or f.module != "logistics":
        raise LogisticsRuleError("Attach a document uploaded to the Logistics section.")
    return f


def get_shipment(db: Session, shipment_id: uuid.UUID) -> Shipment:
    row = db.get(Shipment, shipment_id)
    if row is None:
        raise NotFoundError("Shipment not found.")
    return row


def shipments_out(db: Session, rows: list[Shipment]) -> list[schemas.ShipmentOut]:
    if not rows:
        return []
    suppliers = dict(
        db.execute(
            select(PurchaseOrder.id, Supplier.name)
            .join(Supplier, Supplier.id == PurchaseOrder.supplier_id)
            .where(PurchaseOrder.id.in_({r.purchase_order_id for r in rows} - {None}))
        )
        .tuples()
        .all()
    )
    customers = dict(
        db.execute(
            select(Customer.id, Customer.name).where(
                Customer.id.in_({r.customer_id for r in rows} - {None})
            )
        )
        .tuples()
        .all()
    )
    today = date.today()
    return [
        schemas.ShipmentOut(
            id=r.id,
            reference=r.reference,
            direction=r.direction,
            mode=r.mode,
            carrier=r.carrier,
            tracking_number=r.tracking_number,
            origin=r.origin,
            destination=r.destination,
            purchase_order_id=r.purchase_order_id,
            customer_id=r.customer_id,
            counterparty=(
                suppliers.get(r.purchase_order_id)
                if r.purchase_order_id
                else customers.get(r.customer_id)
                if r.customer_id
                else None
            ),
            status=r.status,
            etd=r.etd,
            eta=r.eta,
            freight_cost=r.freight_cost,
            freight_currency=r.freight_currency,
            customs_entry_number=r.customs_entry_number,
            notes=r.notes,
            late=bool(r.eta and r.eta < today and r.status not in (*CLOSED, "arrived")),
            created_at=r.created_at,
        )
        for r in rows
    ]


def create_shipment(db: Session, body: schemas.ShipmentIn, actor: uuid.UUID) -> Shipment:
    if body.purchase_order_id and db.get(PurchaseOrder, body.purchase_order_id) is None:
        raise LogisticsRuleError("The purchase order does not exist.")
    if body.customer_id and db.get(Customer, body.customer_id) is None:
        raise LogisticsRuleError("The customer does not exist.")
    row = Shipment(reference=next_reference(db, "SHP"), created_by=actor, **body.model_dump())
    db.add(row)
    db.flush()
    db.add(
        ShipmentEvent(
            shipment_id=row.id,
            status="planned",
            occurred_at=now(),
            recorded_by=actor,
            note="Shipment recorded",
        )
    )
    _audit(db, "shipment.created", actor, "shipment", row.id, reference=row.reference)
    return row


def update_status(db: Session, row: Shipment, body: schemas.StatusIn, actor: uuid.UUID) -> Shipment:
    if row.status in CLOSED:
        raise ConflictError(f"The shipment is {row.status}; its status can no longer change.")
    when = body.occurred_at or now()
    if when > now():
        raise LogisticsRuleError("A status cannot be recorded in the future.")
    if body.status == "cleared" and not (body.customs_entry_number or row.customs_entry_number):
        raise LogisticsRuleError("Record the customs entry number when clearing.")
    if body.customs_entry_number:
        row.customs_entry_number = body.customs_entry_number
    row.status = body.status
    db.add(
        ShipmentEvent(
            shipment_id=row.id,
            status=body.status,
            location=body.location,
            note=body.note,
            occurred_at=when,
            recorded_by=actor,
        )
    )
    _audit(db, f"shipment.{body.status}", actor, "shipment", row.id)
    return row


def add_document(db: Session, row: Shipment, body: schemas.DocumentIn, actor: uuid.UUID) -> None:
    _file(db, body.file_id)
    db.add(ShipmentDocument(shipment_id=row.id, added_by=actor, **body.model_dump()))
    _audit(db, "shipment.document_added", actor, "shipment", row.id, doc_type=body.doc_type)


def shipment_detail(db: Session, row: Shipment) -> schemas.ShipmentDetail:
    events = db.execute(
        select(ShipmentEvent, User.display_name)
        .join(User, User.id == ShipmentEvent.recorded_by)
        .where(ShipmentEvent.shipment_id == row.id)
        .order_by(ShipmentEvent.occurred_at, ShipmentEvent.created_at)
    ).all()
    docs = db.execute(
        select(ShipmentDocument, StoredFile.original_name)
        .join(StoredFile, StoredFile.id == ShipmentDocument.file_id)
        .where(ShipmentDocument.shipment_id == row.id)
        .order_by(ShipmentDocument.created_at)
    ).all()
    return schemas.ShipmentDetail(
        shipment=shipments_out(db, [row])[0],
        events=[
            schemas.EventOut(
                status=e.status,
                location=e.location,
                note=e.note,
                occurred_at=e.occurred_at,
                recorded_by=name,
            )
            for e, name in events
        ],
        documents=[
            schemas.DocumentOut(
                id=d.id,
                doc_type=d.doc_type,
                file_id=d.file_id,
                file_name=fname,
                note=d.note,
                created_at=d.created_at,
            )
            for d, fname in docs
        ],
    )


# --- Delivery notes ------------------------------------------------------------------


def get_note(db: Session, note_id: uuid.UUID) -> DeliveryNote:
    row = db.get(DeliveryNote, note_id)
    if row is None:
        raise NotFoundError("Delivery note not found.")
    return row


def create_note(db: Session, body: schemas.DeliveryNoteIn, actor: uuid.UUID) -> DeliveryNote:
    customer = db.get(Customer, body.customer_id)
    if customer is None or customer.status == "archived":
        raise LogisticsRuleError("Choose an existing customer.")
    inv.get_warehouse(db, body.warehouse_id)
    if body.invoice_id:
        invoice = db.get(Invoice, body.invoice_id)
        if invoice is None or invoice.customer_id != customer.id:
            raise LogisticsRuleError("The invoice belongs to a different customer.")
    if body.shipment_id:
        shipment = get_shipment(db, body.shipment_id)
        if shipment.direction != "outbound":
            raise LogisticsRuleError("Link an outbound shipment.")
    for line in body.lines:
        product = inv.get_product(db, line.product_id)
        if not product.is_active:
            raise LogisticsRuleError(f"Product {product.sku} is inactive.")
    row = DeliveryNote(
        number=next_reference(db, "DN"),
        created_by=actor,
        **body.model_dump(exclude={"lines"}),
    )
    db.add(row)
    db.flush()
    for n, line in enumerate(body.lines, start=1):
        db.add(DeliveryNoteLine(delivery_note_id=row.id, line_no=n, **line.model_dump()))
    db.flush()
    _audit(db, "delivery.created", actor, "delivery_note", row.id, number=row.number)
    return row


def dispatch(db: Session, row: DeliveryNote, actor: uuid.UUID) -> DeliveryNote:
    if row.status != "draft":
        raise ConflictError("Only a draft delivery note can be dispatched.")
    warehouse = inv.get_warehouse(db, row.warehouse_id)
    lines = db.execute(
        select(DeliveryNoteLine).where(DeliveryNoteLine.delivery_note_id == row.id)
    ).scalars()
    for line in lines:
        inv.move_out(
            db,
            product=inv.get_product(db, line.product_id),
            warehouse=warehouse,
            quantity=line.quantity,
            kind="dispatch",
            on=now().date(),
            actor=actor,
            reference=row.number,
            source=("delivery_note", row.id),
        )
    row.status = "dispatched"
    row.dispatched_at = now()
    _audit(db, "delivery.dispatched", actor, "delivery_note", row.id)
    return row


def record_proof(
    db: Session, row: DeliveryNote, body: schemas.ProofIn, actor: uuid.UUID
) -> DeliveryNote:
    if row.status != "dispatched":
        raise ConflictError("Proof of delivery is recorded after dispatch.")
    when = body.delivered_at or now()
    if when > now():
        raise LogisticsRuleError("The delivery time cannot be in the future.")
    if row.dispatched_at and when < row.dispatched_at:
        raise LogisticsRuleError("The delivery time cannot be before dispatch.")
    if body.proof_file_id:
        _file(db, body.proof_file_id)
    row.status = "delivered"
    row.delivered_at = when
    row.received_by_name = body.received_by_name
    row.proof_file_id = body.proof_file_id
    row.proof_note = body.note
    _audit(
        db,
        "delivery.delivered",
        actor,
        "delivery_note",
        row.id,
        has_document=body.proof_file_id is not None,
    )
    return row


def cancel_note(db: Session, row: DeliveryNote, reason: str, actor: uuid.UUID) -> DeliveryNote:
    if row.status != "draft":
        raise ConflictError("Only a draft (not yet dispatched) delivery note can be cancelled.")
    row.status = "cancelled"
    row.proof_note = f"Cancelled: {reason}"
    _audit(db, "delivery.cancelled", actor, "delivery_note", row.id)
    return row


def notes_out(db: Session, rows: list[DeliveryNote]) -> list[schemas.DeliveryNoteOut]:
    if not rows:
        return []
    customers = dict(
        db.execute(
            select(Customer.id, Customer.name).where(Customer.id.in_({r.customer_id for r in rows}))
        )
        .tuples()
        .all()
    )
    warehouses = dict(
        db.execute(
            select(Warehouse.id, Warehouse.code).where(
                Warehouse.id.in_({r.warehouse_id for r in rows})
            )
        )
        .tuples()
        .all()
    )
    lines: dict[uuid.UUID, list[schemas.DeliveryLineOut]] = defaultdict(list)
    for line, sku, name, unit in db.execute(
        select(DeliveryNoteLine, Product.sku, Product.name, Product.unit)
        .join(Product, Product.id == DeliveryNoteLine.product_id)
        .where(DeliveryNoteLine.delivery_note_id.in_([r.id for r in rows]))
        .order_by(DeliveryNoteLine.line_no)
    ).all():
        lines[line.delivery_note_id].append(
            schemas.DeliveryLineOut(
                line_no=line.line_no,
                product_id=line.product_id,
                sku=sku,
                product_name=name,
                unit=unit,
                quantity=line.quantity,
            )
        )
    return [
        schemas.DeliveryNoteOut(
            id=r.id,
            number=r.number,
            customer_id=r.customer_id,
            customer_name=customers.get(r.customer_id, ""),
            warehouse_id=r.warehouse_id,
            warehouse_code=warehouses.get(r.warehouse_id, ""),
            shipment_id=r.shipment_id,
            invoice_id=r.invoice_id,
            delivery_address=r.delivery_address,
            scheduled_for=r.scheduled_for,
            status=r.status,
            dispatched_at=r.dispatched_at,
            delivered_at=r.delivered_at,
            received_by_name=r.received_by_name,
            proof_file_id=r.proof_file_id,
            proof_note=r.proof_note,
            lines=lines.get(r.id, []),
        )
        for r in rows
    ]


def summary(db: Session) -> schemas.LogisticsSummary:
    today = date.today()
    shipments = db.execute(select(Shipment.status, Shipment.eta)).all()
    active = [s for s in shipments if s.status not in CLOSED]
    notes = dict(
        db.execute(select(DeliveryNote.status, func.count()).group_by(DeliveryNote.status))
        .tuples()
        .all()
    )
    return schemas.LogisticsSummary(
        has_records=bool(shipments) or bool(notes),
        active_shipments=len(active),
        late_shipments=sum(1 for s in active if s.eta and s.eta < today and s.status != "arrived"),
        at_customs=sum(1 for s in active if s.status == "at_customs"),
        deliveries_scheduled=notes.get("draft", 0),
        awaiting_proof=notes.get("dispatched", 0),
    )
