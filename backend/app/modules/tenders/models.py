"""Tender register, requirement checklists and outcomes (Stage 5)."""

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
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

KINDS = ("rfq", "rfp", "eoi", "itb", "other")
METHODS = ("portal", "email", "physical", "other")
STATUSES = (
    "identified",
    "reviewing",
    "bidding",
    "awaiting_approval",
    "approved",
    "submitted",
    "won",
    "lost",
    "no_bid",
    "cancelled",
)
ACTIVE = ("identified", "reviewing", "bidding", "awaiting_approval", "approved")
REQUIREMENT_KINDS = ("eligibility", "document", "technical", "financial")
REQUIREMENT_STATUSES = ("pending", "met", "not_met", "not_applicable")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Tender(TimestampMixin, Base):
    __tablename__ = "tnd_tenders"
    __table_args__ = (
        CheckConstraint(_in("kind", KINDS), name="kind_valid"),
        CheckConstraint(_in("status", STATUSES), name="status_valid"),
        CheckConstraint(_in("submission_method", METHODS), name="method_valid"),
        CheckConstraint("currency IN ('MWK', 'USD', 'ZAR', 'ZMW')", name="currency_valid"),
        CheckConstraint(
            "estimated_value IS NULL OR estimated_value >= 0", name="estimate_non_negative"
        ),
        CheckConstraint("award_value IS NULL OR award_value >= 0", name="award_non_negative"),
        CheckConstraint("country_code ~ '^[A-Z]{2}$'", name="country_code_format"),
        CheckConstraint(
            "status NOT IN ('no_bid', 'lost', 'cancelled') OR outcome_note IS NOT NULL",
            name="closure_needs_note",
        ),
        Index("ix_tnd_tenders_deadline", "submission_deadline"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    issuer_reference: Mapped[str | None] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    issuer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("crm_customers.id"))
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    division: Mapped[str | None] = mapped_column(String(40))
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, server_default="MW")
    source: Mapped[str | None] = mapped_column(String(300))
    published_on: Mapped[date | None] = mapped_column(Date)
    clarification_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submission_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submission_method: Mapped[str] = mapped_column(String(10), nullable=False)
    bid_security_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="MWK")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="identified")
    notes: Mapped[str | None] = mapped_column(Text)
    approval_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sys_approval_requests.id"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    award_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    outcome_note: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class Requirement(TimestampMixin, Base):
    """Eligibility criteria and submission documents for one tender."""

    __tablename__ = "tnd_requirements"
    __table_args__ = (
        CheckConstraint(_in("kind", REQUIREMENT_KINDS), name="kind_valid"),
        CheckConstraint(_in("status", REQUIREMENT_STATUSES), name="status_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    tender_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tnd_tenders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sys_files.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
