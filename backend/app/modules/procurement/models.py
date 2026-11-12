"""Procurement: suppliers, bank details (encrypted, dual control), purchase
requests, supplier quotations and purchase orders (Stage 6)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

CURRENCY_CHECK = "currency IN ('MWK', 'USD', 'ZAR', 'ZMW')"
SUPPLIER_STATUSES = ("unverified", "verified", "suspended")
BANK_STATUSES = ("pending", "active", "superseded", "rejected")
PR_STATUSES = ("draft", "awaiting_approval", "approved", "rejected", "ordered", "cancelled")
PO_STATUSES = ("issued", "partially_received", "received", "cancelled")


class Supplier(TimestampMixin, Base):
    __tablename__ = "prc_suppliers"
    __table_args__ = (
        CheckConstraint("status IN ('unverified', 'verified', 'suspended')", name="status_valid"),
        CheckConstraint("country_code ~ '^[A-Z]{2}$'", name="country_code_format"),
        Index("ix_prc_suppliers_name_lower", text("lower(name)")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, server_default="MW")
    city: Mapped[str | None] = mapped_column(String(120))
    categories: Mapped[str | None] = mapped_column(String(300))
    contact_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(40))
    registration_number: Mapped[str | None] = mapped_column(String(100))
    tax_number: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="unverified")
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_note: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class SupplierBankAccount(TimestampMixin, Base):
    """Bank details are encrypted at rest. A new account starts ``pending`` and
    becomes ``active`` only when a different person approves it."""

    __tablename__ = "prc_supplier_bank_accounts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'active', 'superseded', 'rejected')", name="status_valid"
        ),
        Index(
            "uq_prc_supplier_bank_one_active",
            "supplier_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prc_suppliers.id"), nullable=False, index=True
    )
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_name_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    account_number_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    branch_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    swift_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    account_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="pending")
    approval_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sys_approval_requests.id"))
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class PurchaseRequest(TimestampMixin, Base):
    __tablename__ = "prc_purchase_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'awaiting_approval', 'approved', 'rejected', 'ordered', "
            "'cancelled')",
            name="status_valid",
        ),
        CheckConstraint(CURRENCY_CHECK, name="currency_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    justification: Mapped[str | None] = mapped_column(Text)
    division: Mapped[str | None] = mapped_column(String(40))
    needed_by: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="MWK")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    selected_quote_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    approval_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sys_approval_requests.id"))
    tender_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tnd_tenders.id"))
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class PurchaseRequestLine(Base):
    __tablename__ = "prc_purchase_request_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        UniqueConstraint("request_id", "line_no"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prc_purchase_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, server_default="each")


class SupplierQuote(TimestampMixin, Base):
    __tablename__ = "prc_supplier_quotes"
    __table_args__ = (CheckConstraint(CURRENCY_CHECK, name="currency_valid"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prc_purchase_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prc_suppliers.id"), nullable=False)
    supplier_reference: Mapped[str | None] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    delivery_terms: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sys_files.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class SupplierQuoteLine(Base):
    __tablename__ = "prc_supplier_quote_lines"
    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="price_non_negative"),
        UniqueConstraint("quote_id", "request_line_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    quote_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prc_supplier_quotes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prc_purchase_request_lines.id", ondelete="CASCADE"), nullable=False
    )
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)


class PurchaseOrder(TimestampMixin, Base):
    """Issued from an approved purchase request and its selected quotation."""

    __tablename__ = "prc_purchase_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('issued', 'partially_received', 'received', 'cancelled')",
            name="status_valid",
        ),
        CheckConstraint(CURRENCY_CHECK, name="currency_valid"),
        CheckConstraint("total_amount >= 0", name="total_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prc_purchase_requests.id"), nullable=False, unique=True
    )
    quote_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prc_supplier_quotes.id"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prc_suppliers.id"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="issued")
    delivery_address: Mapped[str | None] = mapped_column(Text)
    expected_delivery: Mapped[date | None] = mapped_column(Date)
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    issued_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class PurchaseOrderLine(Base):
    __tablename__ = "prc_purchase_order_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("received_quantity >= 0", name="received_non_negative"),
        CheckConstraint("received_quantity <= quantity", name="received_within_ordered"),
        UniqueConstraint("order_id", "line_no"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prc_purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 3), nullable=False, server_default="0"
    )
