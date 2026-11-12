"""CRM tables: customers, contacts, opportunities and activities (Stage 4).

Records are never hard-deleted through the API: customers are archived.
``is_demo`` marks clearly labelled development-only demonstration rows.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

CUSTOMER_STATUSES = ("prospect", "active", "inactive", "archived")
CUSTOMER_KINDS = ("organisation", "government", "ngo", "individual")
DIVISIONS = (
    "general_supplies",
    "technologies",
    "industrial_construction",
    "medical_pharmaceuticals",
    "international_trade",
    "logistics_distribution",
)
STAGES = ("lead", "qualified", "proposal", "negotiation", "won", "lost")
OPEN_STAGES = ("lead", "qualified", "proposal", "negotiation")
ACTIVITY_KINDS = ("meeting", "call", "email", "note", "follow_up")
CURRENCIES = ("MWK", "USD", "ZAR", "ZMW")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Customer(TimestampMixin, Base):
    __tablename__ = "crm_customers"
    __table_args__ = (
        CheckConstraint(_in("status", CUSTOMER_STATUSES), name="status_valid"),
        CheckConstraint(_in("kind", CUSTOMER_KINDS), name="kind_valid"),
        CheckConstraint("country_code ~ '^[A-Z]{2}$'", name="country_code_format"),
        Index("ix_crm_customers_name_lower", text("lower(name)")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, server_default="organisation")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="prospect")
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, server_default="MW")
    city: Mapped[str | None] = mapped_column(String(120))
    industry: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


class Contact(TimestampMixin, Base):
    __tablename__ = "crm_contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crm_customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(40))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class Opportunity(TimestampMixin, Base):
    __tablename__ = "crm_opportunities"
    __table_args__ = (
        CheckConstraint(_in("stage", STAGES), name="stage_valid"),
        CheckConstraint(_in("currency", CURRENCIES), name="currency_valid"),
        CheckConstraint(_in("division", DIVISIONS), name="division_valid"),
        CheckConstraint("value_amount IS NULL OR value_amount >= 0", name="value_non_negative"),
        CheckConstraint("probability BETWEEN 0 AND 100", name="probability_range"),
        CheckConstraint("stage <> 'lost' OR lost_reason IS NOT NULL", name="lost_requires_reason"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crm_customers.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    division: Mapped[str] = mapped_column(String(40), nullable=False)
    stage: Mapped[str] = mapped_column(String(16), nullable=False, server_default="lead")
    value_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="MWK")
    probability: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="10")
    expected_close: Mapped[date | None] = mapped_column(Date)
    lost_reason: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


class Activity(TimestampMixin, Base):
    """Meetings, calls, emails, notes and follow-ups (a follow-up has ``due_at``)."""

    __tablename__ = "crm_activities"
    __table_args__ = (
        CheckConstraint(_in("kind", ACTIVITY_KINDS), name="kind_valid"),
        Index(
            "ix_crm_activities_open_due", "due_at", postgresql_where=text("completed_at IS NULL")
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crm_customers.id"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("crm_opportunities.id"))
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


QUOTATION_STATUSES = (
    "draft",
    "awaiting_approval",
    "issued",
    "accepted",
    "declined",
    "cancelled",
)


class Quotation(TimestampMixin, Base):
    """A priced offer to a customer. It gets its number when issued, and its
    lines and amounts cannot change after that (database trigger)."""

    __tablename__ = "crm_quotations"
    __table_args__ = (
        CheckConstraint(_in("status", QUOTATION_STATUSES), name="status_valid"),
        CheckConstraint(_in("currency", CURRENCIES), name="currency_valid"),
        CheckConstraint(
            "status IN ('draft', 'awaiting_approval', 'cancelled') OR number IS NOT NULL",
            name="issued_has_number",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    number: Mapped[str | None] = mapped_column(String(20), unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crm_customers.id"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("crm_opportunities.id"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="MWK")
    quote_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    tax_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    terms: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    approval_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sys_approval_requests.id"))
    issued_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class QuotationLine(Base):
    __tablename__ = "crm_quotation_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0 AND unit_price >= 0", name="amounts_valid"),
        Index("uq_crm_quotation_lines_no", "quotation_id", "line_no", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    quotation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crm_quotations.id", ondelete="CASCADE"), nullable=False
    )
    line_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, server_default="each")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    tax_code_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_tax_codes.id"))
    net: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
