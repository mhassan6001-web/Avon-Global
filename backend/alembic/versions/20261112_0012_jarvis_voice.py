"""JARVIS voice: per-user voice settings and append-only wake-word consents.

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-12

Additive only. Downgrade drops only the objects created here.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
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
    t = "ai_voice_settings"
    op.create_table(
        t,
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("voice_id", sa.String(80)),
        sa.Column("speed", sa.Numeric(3, 2), server_default="1.00", nullable=False),
        sa.Column("speak_replies", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "wake_word_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        _now("updated_at"),
        _ck(t, "speed_range", "speed BETWEEN 0.80 AND 1.25"),
        _fk(t, "user_id", "auth_users.id", "CASCADE"),
        _pk(t, "user_id"),
    )

    t = "ai_voice_consents"
    op.create_table(
        t,
        _id(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("device", sa.String(120), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        _now(),
        _fk(t, "user_id", "auth_users.id"),
        _pk(t),
    )
    op.create_index(op.f(f"ix_{t}_user_id"), t, ["user_id"])
    op.execute(
        """
        CREATE FUNCTION ai_voice_consents_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'ai_voice_consents are append-only';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER ai_voice_consents_append_only BEFORE UPDATE OR DELETE
            ON ai_voice_consents FOR EACH ROW EXECUTE FUNCTION ai_voice_consents_append_only();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS ai_voice_consents_append_only ON ai_voice_consents; "
        "DROP FUNCTION IF EXISTS ai_voice_consents_append_only();"
    )
    op.drop_table("ai_voice_consents")
    op.drop_table("ai_voice_settings")
