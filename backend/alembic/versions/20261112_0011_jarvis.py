"""JARVIS AI core: conversations, append-only messages, usage ledger and
proposed actions.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-12

Additive only. Downgrade drops only the objects created here.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
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
    t = "ai_conversations"
    op.create_table(
        t,
        _id(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        *_ts(),
        _fk(t, "user_id", "auth_users.id"),
        _pk(t),
    )
    op.create_index(op.f(f"ix_{t}_user_id"), t, ["user_id"])

    t = "ai_messages"
    op.create_table(
        t,
        _id(),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("text", sa.Text(), server_default="", nullable=False),
        _now(),
        _ck(t, "role_valid", "role IN ('user', 'assistant', 'tool')"),
        _fk(t, "conversation_id", "ai_conversations.id", "CASCADE"),
        _pk(t),
    )
    op.create_index("ix_ai_messages_conversation_created", t, ["conversation_id", "created_at"])

    t = "ai_usage"
    op.create_table(
        t,
        _id(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid()),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("outcome", sa.String(12), nullable=False),
        sa.Column("request_id", sa.String(64)),
        _now(),
        _fk(t, "user_id", "auth_users.id"),
        _fk(t, "conversation_id", "ai_conversations.id", "SET NULL"),
        _pk(t),
    )
    op.create_index(op.f(f"ix_{t}_user_id"), t, ["user_id"])

    t = "ai_actions"
    op.create_table(
        t,
        _id(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid()),
        sa.Column("tool", sa.String(60), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(10), server_default="proposed", nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("error", sa.Text()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        _now(),
        _ck(
            t,
            "status_valid",
            "status IN ('proposed', 'executed', 'cancelled', 'failed', 'expired')",
        ),
        _fk(t, "user_id", "auth_users.id"),
        _fk(t, "conversation_id", "ai_conversations.id", "SET NULL"),
        _pk(t),
    )
    op.create_index(op.f(f"ix_{t}_user_id"), t, ["user_id"])

    # Messages are a record of what was said and which tools ran: append-only.
    op.execute(
        """
        CREATE FUNCTION ai_messages_append_only() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' AND NOT EXISTS (
                SELECT 1 FROM ai_conversations WHERE id = OLD.conversation_id
            ) THEN
                RETURN OLD;  -- cascade from a deleted conversation
            END IF;
            RAISE EXCEPTION 'ai_messages are append-only';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER ai_messages_append_only BEFORE UPDATE OR DELETE ON ai_messages
            FOR EACH ROW EXECUTE FUNCTION ai_messages_append_only();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS ai_messages_append_only ON ai_messages; "
        "DROP FUNCTION IF EXISTS ai_messages_append_only();"
    )
    for table in ("ai_actions", "ai_usage", "ai_messages", "ai_conversations"):
        op.drop_table(table)
