"""Register of generated documents: one append-only row per generated
version, with a SHA-256 of the exact bytes handed out."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GeneratedDocument(Base):
    __tablename__ = "doc_generated"
    __table_args__ = (
        CheckConstraint("format IN ('pdf', 'docx', 'xlsx', 'zip')", name="format_valid"),
        UniqueConstraint("kind", "subject", "format", "version", name="uq_doc_generated_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    subject: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    number: Mapped[str] = mapped_column(String(80), nullable=False)
    format: Mapped[str] = mapped_column(String(5), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class BusinessContract(Base):
    """A contract or service agreement. The clauses are written by the company
    (the system supplies no legal wording). Frozen once marked final."""

    __tablename__ = "doc_contracts"
    __table_args__ = (
        CheckConstraint("kind IN ('supply', 'service')", name="kind_valid"),
        CheckConstraint("party_type IN ('customer', 'supplier')", name="party_valid"),
        CheckConstraint("status IN ('draft', 'final')", name="status_valid"),
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date", name="dates_valid"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    party_type: Mapped[str] = mapped_column(String(10), nullable=False)
    party_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str | None] = mapped_column(String(3))
    value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    clauses: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="draft")
    finalised_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    finalised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
