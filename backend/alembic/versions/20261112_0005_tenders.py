"""Tenders: register, requirement checklist, approval link and outcomes.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-12

Additive only. Downgrade drops only the objects created here.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = (
    "'identified', 'reviewing', 'bidding', 'awaiting_approval', 'approved', "
    "'submitted', 'won', 'lost', 'no_bid', 'cancelled'"
)


def _ts() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def _fk(table: str, column: str, target: str) -> sa.ForeignKeyConstraint:
    ref_table = target.split(".")[0]
    return sa.ForeignKeyConstraint(
        [column], [target], name=op.f(f"fk_{table}_{column}_{ref_table}")
    )


def upgrade() -> None:
    op.execute("CREATE SEQUENCE tnd_tender_ref_seq START 1")
    op.create_table(
        "tnd_tenders",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("reference", sa.String(20), nullable=False),
        sa.Column("issuer_reference", sa.String(120)),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("issuer_name", sa.String(200), nullable=False),
        sa.Column("customer_id", sa.Uuid()),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("division", sa.String(40)),
        sa.Column("country_code", sa.String(2), server_default="MW", nullable=False),
        sa.Column("source", sa.String(300)),
        sa.Column("published_on", sa.Date()),
        sa.Column("clarification_deadline", sa.DateTime(timezone=True)),
        sa.Column("submission_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submission_method", sa.String(10), nullable=False),
        sa.Column(
            "bid_security_required", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("estimated_value", sa.Numeric(18, 2)),
        sa.Column("currency", sa.String(3), server_default="MWK", nullable=False),
        sa.Column("status", sa.String(20), server_default="identified", nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("approval_id", sa.Uuid()),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("submitted_by", sa.Uuid()),
        sa.Column("award_value", sa.Numeric(18, 2)),
        sa.Column("outcome_note", sa.Text()),
        sa.Column("owner_id", sa.Uuid()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        sa.CheckConstraint(
            "kind IN ('rfq', 'rfp', 'eoi', 'itb', 'other')", name=op.f("ck_tnd_tenders_kind_valid")
        ),
        sa.CheckConstraint(f"status IN ({STATUSES})", name=op.f("ck_tnd_tenders_status_valid")),
        sa.CheckConstraint(
            "submission_method IN ('portal', 'email', 'physical', 'other')",
            name=op.f("ck_tnd_tenders_method_valid"),
        ),
        sa.CheckConstraint(
            "currency IN ('MWK', 'USD', 'ZAR', 'ZMW')", name=op.f("ck_tnd_tenders_currency_valid")
        ),
        sa.CheckConstraint(
            "estimated_value IS NULL OR estimated_value >= 0",
            name=op.f("ck_tnd_tenders_estimate_non_negative"),
        ),
        sa.CheckConstraint(
            "award_value IS NULL OR award_value >= 0",
            name=op.f("ck_tnd_tenders_award_non_negative"),
        ),
        sa.CheckConstraint(
            "country_code ~ '^[A-Z]{2}$'", name=op.f("ck_tnd_tenders_country_code_format")
        ),
        sa.CheckConstraint(
            "status NOT IN ('no_bid', 'lost', 'cancelled') OR outcome_note IS NOT NULL",
            name=op.f("ck_tnd_tenders_closure_needs_note"),
        ),
        _fk("tnd_tenders", "customer_id", "crm_customers.id"),
        _fk("tnd_tenders", "approval_id", "sys_approval_requests.id"),
        _fk("tnd_tenders", "submitted_by", "auth_users.id"),
        _fk("tnd_tenders", "owner_id", "auth_users.id"),
        _fk("tnd_tenders", "created_by", "auth_users.id"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tnd_tenders")),
        sa.UniqueConstraint("reference", name=op.f("uq_tnd_tenders_reference")),
    )
    op.create_index("ix_tnd_tenders_deadline", "tnd_tenders", ["submission_deadline"])

    op.create_table(
        "tnd_requirements",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tender_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("mandatory", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("file_id", sa.Uuid()),
        sa.Column("notes", sa.Text()),
        sa.Column("updated_by", sa.Uuid()),
        *_ts(),
        sa.CheckConstraint(
            "kind IN ('eligibility', 'document', 'technical', 'financial')",
            name=op.f("ck_tnd_requirements_kind_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'met', 'not_met', 'not_applicable')",
            name=op.f("ck_tnd_requirements_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["tender_id"],
            ["tnd_tenders.id"],
            name=op.f("fk_tnd_requirements_tender_id_tnd_tenders"),
            ondelete="CASCADE",
        ),
        _fk("tnd_requirements", "file_id", "sys_files.id"),
        _fk("tnd_requirements", "updated_by", "auth_users.id"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tnd_requirements")),
    )
    op.create_index(op.f("ix_tnd_requirements_tender_id"), "tnd_requirements", ["tender_id"])


def downgrade() -> None:
    op.drop_table("tnd_requirements")
    op.drop_table("tnd_tenders")
    op.execute("DROP SEQUENCE tnd_tender_ref_seq")
