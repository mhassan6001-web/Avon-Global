"""Register of generated documents: one append-only row per generated
version, with a SHA-256 of the exact bytes handed out."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GeneratedDocument(Base):
    __tablename__ = "doc_generated"
    __table_args__ = (
        CheckConstraint("format IN ('pdf', 'docx', 'xlsx')", name="format_valid"),
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
