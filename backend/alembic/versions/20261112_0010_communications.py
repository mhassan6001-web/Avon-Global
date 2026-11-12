"""Staff communications: conversations, members, messages (append-only),
acknowledgements, tasks with updates, report requests and reports.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-12

Additive only. Downgrade drops only the objects created here.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
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
    t = "com_conversations"
    op.create_table(
        t,
        _id(),
        sa.Column("kind", sa.String(14), nullable=False),
        sa.Column("name", sa.String(120)),
        sa.Column("department_code", sa.String(40)),
        sa.Column("direct_key", sa.String(80)),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        _now(),
        _ck(t, "kind_valid", "kind IN ('direct', 'channel', 'announcements')"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
        sa.UniqueConstraint("direct_key", name=op.f(f"uq_{t}_direct_key")),
    )
    op.create_index(
        "uq_com_one_announcements",
        t,
        ["kind"],
        unique=True,
        postgresql_where=sa.text("kind = 'announcements'"),
    )

    t = "com_members"
    op.create_table(
        t,
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True)),
        _now("joined_at"),
        _fk(t, "conversation_id", "com_conversations.id", "CASCADE"),
        _fk(t, "user_id", "auth_users.id"),
        _pk(t, "conversation_id", "user_id"),
    )

    t = "com_messages"
    op.create_table(
        t,
        _id(),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("sender_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("requires_ack", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("ai_generated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("file_id", sa.Uuid()),
        _now(),
        _fk(t, "conversation_id", "com_conversations.id", "CASCADE"),
        _fk(t, "sender_id", "auth_users.id"),
        _fk(t, "file_id", "sys_files.id"),
        _pk(t),
    )
    op.create_index("ix_com_messages_conversation_created", t, ["conversation_id", "created_at"])

    t = "com_acknowledgements"
    op.create_table(
        t,
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        _now("acknowledged_at"),
        _fk(t, "message_id", "com_messages.id", "CASCADE"),
        _fk(t, "user_id", "auth_users.id"),
        _pk(t, "message_id", "user_id"),
    )

    t = "com_tasks"
    op.create_table(
        t,
        _id(),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("assigned_to", sa.Uuid(), nullable=False),
        sa.Column("assigned_by", sa.Uuid(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("priority", sa.String(8), server_default="normal", nullable=False),
        sa.Column("status", sa.String(12), server_default="open", nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("ai_generated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *_ts(),
        _ck(t, "status_valid", "status IN ('open', 'in_progress', 'blocked', 'done', 'cancelled')"),
        _ck(t, "priority_valid", "priority IN ('low', 'normal', 'high', 'urgent')"),
        _fk(t, "assigned_to", "auth_users.id"),
        _fk(t, "assigned_by", "auth_users.id"),
        _pk(t),
    )
    op.create_index("ix_com_tasks_assignee_status", t, ["assigned_to", "status"])

    t = "com_task_updates"
    op.create_table(
        t,
        _id(),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(12)),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("file_id", sa.Uuid()),
        _now(),
        _fk(t, "task_id", "com_tasks.id", "CASCADE"),
        _fk(t, "author_id", "auth_users.id"),
        _fk(t, "file_id", "sys_files.id"),
        _pk(t),
    )
    op.create_index(op.f(f"ix_{t}_task_id"), t, ["task_id"])

    t = "com_report_requests"
    op.create_table(
        t,
        _id(),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("requested_from", sa.Uuid(), nullable=False),
        sa.Column("topic", sa.String(300), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(10), server_default="open", nullable=False),
        _now(),
        _ck(t, "status_valid", "status IN ('open', 'submitted', 'cancelled')"),
        _fk(t, "requested_by", "auth_users.id"),
        _fk(t, "requested_from", "auth_users.id"),
        _pk(t),
    )
    op.create_index(op.f(f"ix_{t}_requested_from"), t, ["requested_from"])

    t = "com_reports"
    op.create_table(
        t,
        _id(),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("request_id", sa.Uuid()),
        sa.Column("file_id", sa.Uuid()),
        _now(),
        _ck(t, "kind_valid", "kind IN ('morning_plan', 'end_of_day', 'requested')"),
        _fk(t, "author_id", "auth_users.id"),
        _fk(t, "request_id", "com_report_requests.id"),
        _fk(t, "file_id", "sys_files.id"),
        _pk(t),
        sa.UniqueConstraint(
            "author_id", "kind", "report_date", "request_id", name=op.f(f"uq_{t}_author_id")
        ),
    )

    op.execute(
        """
        CREATE FUNCTION com_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '% is kept as sent; it cannot be edited or deleted', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER com_messages_append_only BEFORE UPDATE OR DELETE ON com_messages
            FOR EACH ROW EXECUTE FUNCTION com_append_only();
        CREATE TRIGGER com_reports_append_only BEFORE UPDATE OR DELETE ON com_reports
            FOR EACH ROW EXECUTE FUNCTION com_append_only();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS com_reports_append_only ON com_reports; "
        "DROP TRIGGER IF EXISTS com_messages_append_only ON com_messages; "
        "DROP FUNCTION IF EXISTS com_append_only();"
    )
    for table in (
        "com_reports",
        "com_report_requests",
        "com_task_updates",
        "com_tasks",
        "com_acknowledgements",
        "com_messages",
        "com_members",
        "com_conversations",
    ):
        op.drop_table(table)
