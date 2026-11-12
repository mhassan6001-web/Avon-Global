"""Approval requests (separation of duties). Used by business modules from Stage 4."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ApprovalRequest(TimestampMixin, Base):
    __tablename__ = "sys_approval_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled')", name="status_valid"
        ),
        CheckConstraint(
            "decided_by IS NULL OR decided_by <> requested_by", name="no_self_approval"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    subject_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False)
    permission_required: Mapped[str] = mapped_column(String(120), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[str | None] = mapped_column(Text)
