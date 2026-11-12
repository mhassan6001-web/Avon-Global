"""Baseline: organisation profile.

Revision ID: 0001
Revises:
Create Date: 2026-11-12

Creates the configurable organisation identity table. No rows are inserted:
the Director enters the legal name and registration details once
authentication exists. Downgrade drops only this table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # gen_random_uuid() is built into PostgreSQL 13+; no extension required.
    op.create_table(
        "organisation_profile",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("trading_name", sa.String(length=200), nullable=False),
        sa.Column("legal_name", sa.String(length=300), nullable=True),
        sa.Column(
            "registration_status",
            sa.String(length=32),
            server_default="not_confirmed",
            nullable=False,
        ),
        sa.Column("registration_number", sa.String(length=100), nullable=True),
        sa.Column("headquarters_city", sa.String(length=120), nullable=True),
        sa.Column("headquarters_country_code", sa.String(length=2), nullable=True),
        sa.Column("functional_currency", sa.String(length=3), server_default="MWK", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "registration_status IN ('not_confirmed', 'pending', 'registered')",
            name=op.f("ck_organisation_profile_registration_status_valid"),
        ),
        sa.CheckConstraint(
            "functional_currency IN ('MWK', 'USD', 'ZAR', 'ZMW')",
            name=op.f("ck_organisation_profile_functional_currency_supported"),
        ),
        sa.CheckConstraint(
            "registration_status <> 'registered' OR registration_number IS NOT NULL",
            name=op.f("ck_organisation_profile_registered_requires_number"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organisation_profile")),
    )


def downgrade() -> None:
    op.drop_table("organisation_profile")
