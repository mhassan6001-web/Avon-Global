"""Documents: register of generated versions (append-only).

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-12

Additive only. Downgrade drops only the objects created here.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
    t = "doc_generated"
    op.create_table(
        t,
        _id(),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("subject", sa.String(80), nullable=False),
        sa.Column("number", sa.String(80), nullable=False),
        sa.Column("format", sa.String(5), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("generated_by", sa.Uuid(), nullable=False),
        _now(),
        _ck(t, "format_valid", "format IN ('pdf', 'docx', 'xlsx')"),
        _fk(t, "generated_by", "auth_users.id"),
        _pk(t),
        sa.UniqueConstraint(
            "kind", "subject", "format", "version", name="uq_doc_generated_version"
        ),
    )
    op.create_index(op.f(f"ix_{t}_subject"), t, ["subject"])
    op.execute(
        """
        CREATE FUNCTION doc_generated_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'doc_generated is append-only';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER doc_generated_append_only BEFORE UPDATE OR DELETE ON doc_generated
            FOR EACH ROW EXECUTE FUNCTION doc_generated_append_only();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS doc_generated_append_only ON doc_generated; "
        "DROP FUNCTION IF EXISTS doc_generated_append_only();"
    )
    op.drop_table("doc_generated")
