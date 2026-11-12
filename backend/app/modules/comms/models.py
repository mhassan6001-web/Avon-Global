"""Staff communications (Stage 10): conversations, messages with
acknowledgements, tasks with updates, and work reports.

Privacy rule: a conversation is readable only by its members. The Director
is not silently added to conversations; there is no hidden monitoring.
Messages are not edited or deleted (retention policy in docs/policies).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


def _pk() -> Any:
    return mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))


def _now() -> Any:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class Conversation(Base):
    __tablename__ = "com_conversations"
    __table_args__ = (
        CheckConstraint("kind IN ('direct', 'channel', 'announcements')", name="kind_valid"),
        Index(
            "uq_com_one_announcements",
            "kind",
            unique=True,
            postgresql_where=text("kind = 'announcements'"),
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    kind: Mapped[str] = mapped_column(String(14), nullable=False)
    name: Mapped[str | None] = mapped_column(String(120))
    department_code: Mapped[str | None] = mapped_column(String(40))
    direct_key: Mapped[str | None] = mapped_column(String(80), unique=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    created_at: Mapped[datetime] = _now()


class Member(Base):
    __tablename__ = "com_members"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("com_conversations.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), primary_key=True)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    joined_at: Mapped[datetime] = _now()


class Message(Base):
    __tablename__ = "com_messages"
    __table_args__ = (
        Index("ix_com_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = _pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("com_conversations.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    requires_ack: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    ai_generated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sys_files.id"))
    created_at: Mapped[datetime] = _now()


class Acknowledgement(Base):
    __tablename__ = "com_acknowledgements"

    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("com_messages.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), primary_key=True)
    acknowledged_at: Mapped[datetime] = _now()


class Task(TimestampMixin, Base):
    __tablename__ = "com_tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'in_progress', 'blocked', 'done', 'cancelled')", name="status_valid"
        ),
        CheckConstraint("priority IN ('low', 'normal', 'high', 'urgent')", name="priority_valid"),
        Index("ix_com_tasks_assignee_status", "assigned_to", "status"),
    )

    id: Mapped[uuid.UUID] = _pk()
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    assigned_to: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    assigned_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    priority: Mapped[str] = mapped_column(String(8), nullable=False, server_default="normal")
    status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="open")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_generated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )


class TaskUpdate(Base):
    __tablename__ = "com_task_updates"

    id: Mapped[uuid.UUID] = _pk()
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("com_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    status: Mapped[str | None] = mapped_column(String(12))
    note: Mapped[str] = mapped_column(Text, nullable=False)
    file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sys_files.id"))
    created_at: Mapped[datetime] = _now()


class ReportRequest(Base):
    __tablename__ = "com_report_requests"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'submitted', 'cancelled')", name="status_valid"),
    )

    id: Mapped[uuid.UUID] = _pk()
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    requested_from: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_users.id"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(String(300), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="open")
    created_at: Mapped[datetime] = _now()


class Report(Base):
    __tablename__ = "com_reports"
    __table_args__ = (
        CheckConstraint("kind IN ('morning_plan', 'end_of_day', 'requested')", name="kind_valid"),
        UniqueConstraint("author_id", "kind", "report_date", "request_id"),
    )

    id: Mapped[uuid.UUID] = _pk()
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    request_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("com_report_requests.id"))
    file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sys_files.id"))
    created_at: Mapped[datetime] = _now()
