"""Contracts and service agreements; tender packs in the document register.

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-13

Additive: one new table; the register's format check widened to allow 'zip'.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FORMAT = "ck_doc_generated_format_valid"


def _id() -> sa.Column:  # type: ignore[type-arg]
    return sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def _now(name: str = "created_at") -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(
        name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
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


def _fk(t: str, c: str, target: str, ondelete: str | None = None) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [c], [target], name=op.f(f"fk_{t}_{c}_{target.split('.')[0]}"), ondelete=ondelete
    )


def _ck(t: str, n: str, sql: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(sql, name=op.f(f"ck_{t}_{n}"))


def _pk(t: str, *cols: str) -> sa.PrimaryKeyConstraint:
    return sa.PrimaryKeyConstraint(*(cols or ("id",)), name=op.f(f"pk_{t}"))


def upgrade() -> None:
    op.drop_constraint(op.f(FORMAT), "doc_generated", type_="check")
    op.create_check_constraint(
        op.f(FORMAT), "doc_generated", "format IN ('pdf', 'docx', 'xlsx', 'zip')"
    )

    t = "doc_contracts"
    op.create_table(
        t,
        _id(),
        sa.Column("reference", sa.String(20), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("party_type", sa.String(10), nullable=False),
        sa.Column("party_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("currency", sa.String(3)),
        sa.Column("value", sa.Numeric(18, 2)),
        sa.Column("clauses", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(10), server_default="draft", nullable=False),
        sa.Column("finalised_by", sa.Uuid()),
        sa.Column("finalised_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "kind_valid", "kind IN ('supply', 'service')"),
        _ck(t, "party_valid", "party_type IN ('customer', 'supplier')"),
        _ck(t, "status_valid", "status IN ('draft', 'final')"),
        _ck(t, "dates_valid", "end_date IS NULL OR start_date IS NULL OR end_date >= start_date"),
        _fk(t, "finalised_by", "auth_users.id"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
        sa.UniqueConstraint("reference", name=op.f(f"uq_{t}_reference")),
    )
    op.execute(
        """
        CREATE FUNCTION doc_contracts_final_frozen() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' OR OLD.status = 'final' THEN
                RAISE EXCEPTION 'a final contract cannot be changed, and contracts are never deleted';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER doc_contracts_final_frozen BEFORE UPDATE OR DELETE ON doc_contracts
            FOR EACH ROW EXECUTE FUNCTION doc_contracts_final_frozen();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS doc_contracts_final_frozen ON doc_contracts; "
        "DROP FUNCTION IF EXISTS doc_contracts_final_frozen();"
    )
    op.drop_table("doc_contracts")
    op.drop_constraint(op.f(FORMAT), "doc_generated", type_="check")
    op.create_check_constraint(op.f(FORMAT), "doc_generated", "format IN ('pdf', 'docx', 'xlsx')")
