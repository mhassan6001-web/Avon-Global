"""Logistics (Stage 8): shipments with a status timeline and customs
documents, and outbound delivery notes with proof of delivery."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

SHIPMENT_STATUSES = (
    "planned",
    "in_transit",
    "at_customs",
    "cleared",
    "arrived",
    "delivered",
    "cancelled",
)


class Shipment(TimestampMixin, Base):
    __tablename__ = "lgx_shipments"
    __table_args__ = (
        CheckConstraint("direction IN ('inbound', 'outbound')", name="direction_valid"),
        CheckConstraint(
            "mode IN ('road', 'air', 'sea', 'rail', 'courier', 'multimodal')", name="mode_valid"
        ),
        CheckConstraint(
            "status IN ('planned', 'in_transit', 'at_customs', 'cleared', 'arrived', "
            "'delivered', 'cancelled')",
            name="status_valid",
        ),
        CheckConstraint(
            "freight_currency IS NULL OR freight_currency IN ('MWK', 'USD', 'ZAR', 'ZMW')",
            name="currency_valid",
        ),
        CheckConstraint("freight_cost IS NULL OR freight_cost >= 0", name="cost_non_negative"),
        CheckConstraint("eta IS NULL OR etd IS NULL OR eta >= etd", name="eta_after_etd"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    mode: Mapped[str] = mapped_column(String(12), nullable=False)
    carrier: Mapped[str | None] = mapped_column(String(200))
    tracking_number: Mapped[str | None] = mapped_column(String(120))
    origin: Mapped[str] = mapped_column(String(200), nullable=False)
    destination: Mapped[str] = mapped_column(String(200), nullable=False)
    purchase_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prc_purchase_orders.id")
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("crm_customers.id"))
    status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="planned")
    etd: Mapped[date | None] = mapped_column(Date)
    eta: Mapped[date | None] = mapped_column(Date)
    freight_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    freight_currency: Mapped[str | None] = mapped_column(String(3))
    customs_entry_number: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class ShipmentEvent(Base):
    __tablename__ = "lgx_shipment_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    shipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lgx_shipments.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ShipmentDocument(Base):
    __tablename__ = "lgx_shipment_documents"
    __table_args__ = (
        CheckConstraint(
            "doc_type IN ('bill_of_lading', 'airway_bill', 'commercial_invoice', "
            "'packing_list', 'certificate_of_origin', 'customs_declaration', "
            "'import_permit', 'insurance', 'other')",
            name="doc_type_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    shipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lgx_shipments.id"), nullable=False, index=True
    )
    doc_type: Mapped[str] = mapped_column(String(30), nullable=False)
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sys_files.id"), nullable=False)
    note: Mapped[str | None] = mapped_column(String(300))
    added_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class DeliveryNote(TimestampMixin, Base):
    __tablename__ = "lgx_delivery_notes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'dispatched', 'delivered', 'cancelled')", name="status_valid"
        ),
        CheckConstraint(
            "status <> 'delivered' OR (received_by_name IS NOT NULL AND delivered_at IS NOT NULL)",
            name="delivered_has_proof",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    number: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crm_customers.id"), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inv_warehouses.id"), nullable=False)
    shipment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("lgx_shipments.id"))
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_invoices.id"))
    delivery_address: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_for: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="draft")
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_by_name: Mapped[str | None] = mapped_column(String(200))
    proof_file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sys_files.id"))
    proof_note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class DeliveryNoteLine(Base):
    __tablename__ = "lgx_delivery_note_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        UniqueConstraint("delivery_note_id", "line_no"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    delivery_note_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lgx_delivery_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inv_products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
