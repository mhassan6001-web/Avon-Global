"""Identity tables: users, roles, permissions, sessions, MFA, tokens, login events."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Department(TimestampMixin, Base):
    __tablename__ = "org_departments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class Role(TimestampMixin, Base):
    __tablename__ = "auth_roles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    mfa_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class Permission(TimestampMixin, Base):
    __tablename__ = "auth_permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class RolePermission(Base):
    __tablename__ = "auth_role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_permissions.id", ondelete="CASCADE"), primary_key=True
    )


class User(TimestampMixin, Base):
    __tablename__ = "auth_users"
    __table_args__ = (
        CheckConstraint("status IN ('invited', 'active', 'suspended')", name="status_valid"),
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_roles.id"), nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_departments.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="invited")
    password_hash: Mapped[str | None] = mapped_column(Text)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_dev_account: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")


class PermissionOverride(TimestampMixin, Base):
    __tablename__ = "auth_permission_overrides"
    __table_args__ = (
        UniqueConstraint("user_id", "permission_id", name="uq_auth_permission_overrides_user_perm"),
        CheckConstraint("effect IN ('grant', 'deny')", name="effect_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_permissions.id"), nullable=False
    )
    effect: Mapped[str] = mapped_column(String(8), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    granted_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        CheckConstraint(
            "state IN ('mfa_pending', 'mfa_enrolment_required', 'active')", name="state_valid"
        ),
        Index("ix_auth_sessions_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    csrf_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    step_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(400))


class UserMfa(TimestampMixin, Base):
    __tablename__ = "auth_user_mfa"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_users.id", ondelete="CASCADE"), primary_key=True
    )
    secret_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_step: Mapped[int | None] = mapped_column(BigInteger)
    recovery_code_hashes: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )


class OneTimeToken(Base):
    """Invitation and password-reset links. Only the SHA-256 hash is stored."""

    __tablename__ = "auth_one_time_tokens"
    __table_args__ = (
        CheckConstraint("purpose IN ('invitation', 'password_reset')", name="purpose_valid"),
        Index("ix_auth_one_time_tokens_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LoginEvent(Base):
    __tablename__ = "auth_login_events"
    __table_args__ = (
        Index("ix_auth_login_events_user_id", "user_id"),
        Index("ix_auth_login_events_occurred_at", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("auth_users.id", ondelete="SET NULL")
    )
    email_attempted: Mapped[str] = mapped_column(String(320), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(400))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
