"""JARVIS persistence: conversations, append-only messages, usage ledger and
proposed actions awaiting the user's confirmation."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


def _pk() -> Any:
    return mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))


def _now() -> Any:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


def _clock() -> Any:
    return mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
    )


class AIConversation(TimestampMixin, Base):
    __tablename__ = "ai_conversations"

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)


class AIMessage(Base):
    """One turn. ``content`` holds provider-neutral blocks so a conversation can
    be replayed to any provider; ``text`` is what the user sees."""

    __tablename__ = "ai_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'tool')", name="role_valid"),
        Index("ix_ai_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = _pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    content: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    # clock_timestamp(), not now(): turns written in one transaction keep their order.
    created_at: Mapped[datetime] = _clock()


class AIUsage(Base):
    __tablename__ = "ai_usage"

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_users.id"), nullable=False, index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_conversations.id", ondelete="SET NULL")
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    outcome: Mapped[str] = mapped_column(String(12), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = _now()


class AIAction(Base):
    """A change JARVIS has prepared. Nothing happens until the user confirms."""

    __tablename__ = "ai_actions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed', 'executed', 'cancelled', 'failed', 'expired')",
            name="status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_users.id"), nullable=False, index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_conversations.id", ondelete="SET NULL")
    )
    tool: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="proposed")
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()


class AIVoiceSettings(Base):
    """Per-user voice choices. Wake word is off until consent is recorded."""

    __tablename__ = "ai_voice_settings"
    __table_args__ = (CheckConstraint("speed BETWEEN 0.80 AND 1.25", name="speed_range"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_users.id", ondelete="CASCADE"), primary_key=True
    )
    voice_id: Mapped[str | None] = mapped_column(String(80))
    speed: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False, server_default="1.00")
    speak_replies: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    wake_word_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    updated_at: Mapped[datetime] = _now()


class AIVoiceConsent(Base):
    """Append-only record of wake-word consent decisions (who, device, when)."""

    __tablename__ = "ai_voice_consents"

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_users.id"), nullable=False, index=True
    )
    device: Mapped[str] = mapped_column(String(120), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = _now()
