"""CRM: customers, contacts, opportunities, activities and reference sequences.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-12

Additive only. Downgrade drops only the objects created here.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id() -> sa.Column:  # type: ignore[type-arg]
    return sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def _ts() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def _user_fk(table: str, column: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], ["auth_users.id"], name=op.f(f"fk_{table}_{column}_auth_users")
    )


def upgrade() -> None:
    op.execute("CREATE SEQUENCE crm_customer_ref_seq START 1")
    op.execute("CREATE SEQUENCE crm_opportunity_ref_seq START 1")

    op.create_table(
        "crm_customers",
        _id(),
        sa.Column("reference", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(20), server_default="organisation", nullable=False),
        sa.Column("status", sa.String(16), server_default="prospect", nullable=False),
        sa.Column("country_code", sa.String(2), server_default="MW", nullable=False),
        sa.Column("city", sa.String(120)),
        sa.Column("industry", sa.String(120)),
        sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(40)),
        sa.Column("notes", sa.Text()),
        sa.Column("owner_id", sa.Uuid()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *_ts(),
        sa.CheckConstraint(
            "status IN ('prospect', 'active', 'inactive', 'archived')",
            name=op.f("ck_crm_customers_status_valid"),
        ),
        sa.CheckConstraint(
            "kind IN ('organisation', 'government', 'ngo', 'individual')",
            name=op.f("ck_crm_customers_kind_valid"),
        ),
        sa.CheckConstraint(
            "country_code ~ '^[A-Z]{2}$'", name=op.f("ck_crm_customers_country_code_format")
        ),
        _user_fk("crm_customers", "owner_id"),
        _user_fk("crm_customers", "created_by"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crm_customers")),
        sa.UniqueConstraint("reference", name=op.f("uq_crm_customers_reference")),
    )
    op.create_index("ix_crm_customers_name_lower", "crm_customers", [sa.text("lower(name)")])

    op.create_table(
        "crm_contacts",
        _id(),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("job_title", sa.String(120)),
        sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(40)),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["crm_customers.id"],
            name=op.f("fk_crm_contacts_customer_id_crm_customers"),
            ondelete="CASCADE",
        ),
        _user_fk("crm_contacts", "created_by"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crm_contacts")),
    )
    op.create_index(op.f("ix_crm_contacts_customer_id"), "crm_contacts", ["customer_id"])

    op.create_table(
        "crm_opportunities",
        _id(),
        sa.Column("reference", sa.String(20), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("division", sa.String(40), nullable=False),
        sa.Column("stage", sa.String(16), server_default="lead", nullable=False),
        sa.Column("value_amount", sa.Numeric(18, 2)),
        sa.Column("currency", sa.String(3), server_default="MWK", nullable=False),
        sa.Column("probability", sa.SmallInteger(), server_default="10", nullable=False),
        sa.Column("expected_close", sa.Date()),
        sa.Column("lost_reason", sa.Text()),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("owner_id", sa.Uuid()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *_ts(),
        sa.CheckConstraint(
            "stage IN ('lead', 'qualified', 'proposal', 'negotiation', 'won', 'lost')",
            name=op.f("ck_crm_opportunities_stage_valid"),
        ),
        sa.CheckConstraint(
            "currency IN ('MWK', 'USD', 'ZAR', 'ZMW')",
            name=op.f("ck_crm_opportunities_currency_valid"),
        ),
        sa.CheckConstraint(
            "division IN ('general_supplies', 'technologies', 'industrial_construction', "
            "'medical_pharmaceuticals', 'international_trade', 'logistics_distribution')",
            name=op.f("ck_crm_opportunities_division_valid"),
        ),
        sa.CheckConstraint(
            "value_amount IS NULL OR value_amount >= 0",
            name=op.f("ck_crm_opportunities_value_non_negative"),
        ),
        sa.CheckConstraint(
            "probability BETWEEN 0 AND 100", name=op.f("ck_crm_opportunities_probability_range")
        ),
        sa.CheckConstraint(
            "stage <> 'lost' OR lost_reason IS NOT NULL",
            name=op.f("ck_crm_opportunities_lost_requires_reason"),
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["crm_customers.id"],
            name=op.f("fk_crm_opportunities_customer_id_crm_customers"),
        ),
        _user_fk("crm_opportunities", "owner_id"),
        _user_fk("crm_opportunities", "created_by"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crm_opportunities")),
        sa.UniqueConstraint("reference", name=op.f("uq_crm_opportunities_reference")),
    )
    op.create_index(op.f("ix_crm_opportunities_customer_id"), "crm_opportunities", ["customer_id"])

    op.create_table(
        "crm_activities",
        _id(),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid()),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("assigned_to", sa.Uuid()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        sa.CheckConstraint(
            "kind IN ('meeting', 'call', 'email', 'note', 'follow_up')",
            name=op.f("ck_crm_activities_kind_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["crm_customers.id"],
            name=op.f("fk_crm_activities_customer_id_crm_customers"),
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["crm_opportunities.id"],
            name=op.f("fk_crm_activities_opportunity_id_crm_opportunities"),
        ),
        _user_fk("crm_activities", "assigned_to"),
        _user_fk("crm_activities", "created_by"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crm_activities")),
    )
    op.create_index(op.f("ix_crm_activities_customer_id"), "crm_activities", ["customer_id"])
    op.create_index(
        "ix_crm_activities_open_due",
        "crm_activities",
        ["due_at"],
        postgresql_where=sa.text("completed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("crm_activities")
    op.drop_table("crm_opportunities")
    op.drop_table("crm_contacts")
    op.drop_table("crm_customers")
    op.execute("DROP SEQUENCE crm_opportunity_ref_seq")
    op.execute("DROP SEQUENCE crm_customer_ref_seq")
