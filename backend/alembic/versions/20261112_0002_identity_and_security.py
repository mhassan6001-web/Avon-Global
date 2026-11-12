"""Identity and security: users, roles, permissions, sessions, MFA, tokens,
login events, audit log (append-only), security alerts, approvals, files.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-12

Creates tables only. Roles, permissions and departments are synchronised
from code at application start (app.platform.authz.sync); no users are created.
Downgrade drops only the tables created here.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_pk() -> sa.Column:  # type: ignore[type-arg]
    return sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def _timestamps() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "org_departments",
        _uuid_pk(),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_org_departments")),
        sa.UniqueConstraint("code", name=op.f("uq_org_departments_code")),
    )
    op.create_table(
        "auth_roles",
        _uuid_pk(),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("mfa_required", sa.Boolean(), server_default="false", nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_roles")),
        sa.UniqueConstraint("code", name=op.f("uq_auth_roles_code")),
    )
    op.create_table(
        "auth_permissions",
        _uuid_pk(),
        sa.Column("code", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("sensitive", sa.Boolean(), server_default="false", nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_permissions")),
        sa.UniqueConstraint("code", name=op.f("uq_auth_permissions_code")),
    )
    op.create_table(
        "auth_role_permissions",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["auth_roles.id"],
            name=op.f("fk_auth_role_permissions_role_id_auth_roles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["auth_permissions.id"],
            name=op.f("fk_auth_role_permissions_permission_id_auth_permissions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name=op.f("pk_auth_role_permissions")),
    )
    op.create_table(
        "auth_users",
        _uuid_pk(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), server_default="invited", nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_dev_account", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('invited', 'active', 'suspended')", name=op.f("ck_auth_users_status_valid")
        ),
        sa.CheckConstraint("email = lower(email)", name=op.f("ck_auth_users_email_lowercase")),
        sa.ForeignKeyConstraint(
            ["role_id"], ["auth_roles.id"], name=op.f("fk_auth_users_role_id_auth_roles")
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["org_departments.id"],
            name=op.f("fk_auth_users_department_id_org_departments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_users")),
        sa.UniqueConstraint("email", name=op.f("uq_auth_users_email")),
    )
    op.create_table(
        "auth_permission_overrides",
        _uuid_pk(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.Column("effect", sa.String(8), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("granted_by", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "effect IN ('grant', 'deny')", name=op.f("ck_auth_permission_overrides_effect_valid")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth_users.id"],
            name=op.f("fk_auth_permission_overrides_user_id_auth_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["auth_permissions.id"],
            name=op.f("fk_auth_permission_overrides_permission_id_auth_permissions"),
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["auth_users.id"],
            name=op.f("fk_auth_permission_overrides_granted_by_auth_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_permission_overrides")),
        sa.UniqueConstraint(
            "user_id", "permission_id", name="uq_auth_permission_overrides_user_perm"
        ),
    )
    op.create_table(
        "auth_sessions",
        _uuid_pk(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("csrf_hash", sa.LargeBinary(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("step_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(400), nullable=True),
        sa.CheckConstraint(
            "state IN ('mfa_pending', 'mfa_enrolment_required', 'active')",
            name=op.f("ck_auth_sessions_state_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth_users.id"],
            name=op.f("fk_auth_sessions_user_id_auth_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_auth_sessions_token_hash")),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_table(
        "auth_user_mfa",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("secret_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_step", sa.BigInteger(), nullable=True),
        sa.Column(
            "recovery_code_hashes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth_users.id"],
            name=op.f("fk_auth_user_mfa_user_id_auth_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_auth_user_mfa")),
    )
    op.create_table(
        "auth_one_time_tokens",
        _uuid_pk(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "purpose IN ('invitation', 'password_reset')",
            name=op.f("ck_auth_one_time_tokens_purpose_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth_users.id"],
            name=op.f("fk_auth_one_time_tokens_user_id_auth_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["auth_users.id"],
            name=op.f("fk_auth_one_time_tokens_created_by_auth_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_one_time_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_auth_one_time_tokens_token_hash")),
    )
    op.create_index("ix_auth_one_time_tokens_user_id", "auth_one_time_tokens", ["user_id"])
    op.create_table(
        "auth_login_events",
        _uuid_pk(),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("email_attempted", sa.String(320), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(400), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth_users.id"],
            name=op.f("fk_auth_login_events_user_id_auth_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_login_events")),
    )
    op.create_index("ix_auth_login_events_user_id", "auth_login_events", ["user_id"])
    op.create_index("ix_auth_login_events_occurred_at", "auth_login_events", ["occurred_at"])

    op.create_table(
        "sys_audit_events",
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_kind", sa.String(32), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=True),
        sa.Column("target_id", sa.String(64), nullable=True),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("prev_hash", sa.LargeBinary(), nullable=False),
        sa.Column("hash", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["auth_users.id"], name=op.f("fk_sys_audit_events_actor_id_auth_users")
        ),
        sa.PrimaryKeyConstraint("seq", name=op.f("pk_sys_audit_events")),
    )
    op.create_index("ix_sys_audit_events_actor_id", "sys_audit_events", ["actor_id"])
    op.create_index("ix_sys_audit_events_target", "sys_audit_events", ["target_type", "target_id"])
    # Append-only: block UPDATE, DELETE and TRUNCATE at the database level.
    op.execute(
        """
        CREATE FUNCTION sys_audit_events_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'sys_audit_events is append-only (% blocked)', TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END
        $$;
        """
    )
    op.execute(
        "CREATE TRIGGER trg_sys_audit_events_no_modify BEFORE UPDATE OR DELETE "
        "ON sys_audit_events FOR EACH ROW EXECUTE FUNCTION sys_audit_events_append_only();"
    )
    op.execute(
        "CREATE TRIGGER trg_sys_audit_events_no_truncate BEFORE TRUNCATE "
        "ON sys_audit_events FOR EACH STATEMENT EXECUTE FUNCTION sys_audit_events_append_only();"
    )

    op.create_table(
        "sys_security_alerts",
        _uuid_pk(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("subject_user_id", sa.Uuid(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["subject_user_id"],
            ["auth_users.id"],
            name=op.f("fk_sys_security_alerts_subject_user_id_auth_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by"],
            ["auth_users.id"],
            name=op.f("fk_sys_security_alerts_acknowledged_by_auth_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sys_security_alerts")),
    )
    op.create_index("ix_sys_security_alerts_created_at", "sys_security_alerts", ["created_at"])

    op.create_table(
        "sys_approval_requests",
        _uuid_pk(),
        sa.Column("subject_type", sa.String(64), nullable=False),
        sa.Column("subject_id", sa.String(64), nullable=False),
        sa.Column("permission_required", sa.String(120), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled')",
            name=op.f("ck_sys_approval_requests_status_valid"),
        ),
        sa.CheckConstraint(
            "decided_by IS NULL OR decided_by <> requested_by",
            name=op.f("ck_sys_approval_requests_no_self_approval"),
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"],
            ["auth_users.id"],
            name=op.f("fk_sys_approval_requests_requested_by_auth_users"),
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"],
            ["auth_users.id"],
            name=op.f("fk_sys_approval_requests_decided_by_auth_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sys_approval_requests")),
    )

    op.create_table(
        "sys_files",
        _uuid_pk(),
        sa.Column("module", sa.String(64), nullable=False),
        sa.Column("required_permission", sa.String(120), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.LargeBinary(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["auth_users.id"], name=op.f("fk_sys_files_owner_id_auth_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sys_files")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_sys_files_storage_key")),
    )
    op.create_index("ix_sys_files_owner_id", "sys_files", ["owner_id"])


def downgrade() -> None:
    op.drop_table("sys_files")
    op.drop_table("sys_approval_requests")
    op.drop_table("sys_security_alerts")
    op.drop_table("sys_audit_events")
    op.execute("DROP FUNCTION IF EXISTS sys_audit_events_append_only()")
    op.drop_table("auth_login_events")
    op.drop_table("auth_one_time_tokens")
    op.drop_table("auth_user_mfa")
    op.drop_table("auth_sessions")
    op.drop_table("auth_permission_overrides")
    op.drop_table("auth_users")
    op.drop_table("auth_role_permissions")
    op.drop_table("auth_permissions")
    op.drop_table("auth_roles")
    op.drop_table("org_departments")
