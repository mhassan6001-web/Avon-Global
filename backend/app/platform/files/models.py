"""Stored files. Content lives in private storage; this table holds access metadata."""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, ForeignKey, Index, LargeBinary, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class StoredFile(TimestampMixin, Base):
    __tablename__ = "sys_files"
    __table_args__ = (Index("ix_sys_files_owner_id", "owner_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    required_permission: Mapped[str] = mapped_column(String(120), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
