"""Company contact and tax identity with print approval; approval rules; quotations.

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-12

Additive only. Downgrade drops only the objects created here.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ORG = "organisation_profile"
ORG_TEXT = (("address_line1", 200), ("address_line2", 200), ("phone", 40), ("email", 200),
            ("tpin", 40), ("vat_number", 40))  # fmt: skip
ORG_FLAGS = ("print_address", "print_phone", "print_email", "print_tpin", "print_vat")


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
    for name, size in ORG_TEXT:
        op.add_column(ORG, sa.Column(name, sa.String(size)))
    for name in ORG_FLAGS:
        op.add_column(
            ORG, sa.Column(name, sa.Boolean(), server_default=sa.text("false"), nullable=False)
        )
    op.create_check_constraint(
        op.f(f"ck_{ORG}_print_requires_value"),
        ORG,
        "(NOT print_address OR address_line1 IS NOT NULL) AND "
        "(NOT print_phone OR phone IS NOT NULL) AND "
        "(NOT print_email OR email IS NOT NULL) AND "
        "(NOT print_tpin OR tpin IS NOT NULL) AND "
        "(NOT print_vat OR vat_number IS NOT NULL)",
    )

    t = "sys_approval_rules"
    op.create_table(
        t,
        sa.Column("key", sa.String(40), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("threshold", sa.Numeric(18, 2)),
        sa.Column("updated_by", sa.Uuid()),
        _now("updated_at"),
        _ck(t, "threshold_non_negative", "threshold IS NULL OR threshold >= 0"),
        _fk(t, "updated_by", "auth_users.id"),
        _pk(t, "key"),
    )

    t = "crm_quotations"
    op.create_table(
        t,
        _id(),
        sa.Column("number", sa.String(20)),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid()),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("currency", sa.String(3), server_default="MWK", nullable=False),
        sa.Column("quote_date", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("tax_total", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("total", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("terms", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("approval_id", sa.Uuid()),
        sa.Column("issued_by", sa.Uuid()),
        sa.Column("issued_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(
            t,
            "status_valid",
            "status IN ('draft', 'awaiting_approval', 'issued', 'accepted', 'declined', "
            "'cancelled')",
        ),
        _ck(t, "currency_valid", "currency IN ('MWK', 'USD', 'ZAR', 'ZMW')"),
        _ck(
            t,
            "issued_has_number",
            "status IN ('draft', 'awaiting_approval', 'cancelled') OR number IS NOT NULL",
        ),
        _fk(t, "customer_id", "crm_customers.id"),
        _fk(t, "opportunity_id", "crm_opportunities.id"),
        _fk(t, "approval_id", "sys_approval_requests.id"),
        _fk(t, "issued_by", "auth_users.id"),
        _fk(t, "created_by", "auth_users.id"),
        _pk(t),
        sa.UniqueConstraint("number", name=op.f(f"uq_{t}_number")),
    )
    op.create_index(op.f(f"ix_{t}_customer_id"), t, ["customer_id"])

    t = "crm_quotation_lines"
    op.create_table(
        t,
        _id(),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.SmallInteger(), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit", sa.String(20), server_default="each", nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("tax_code_id", sa.Uuid()),
        sa.Column("net", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax", sa.Numeric(18, 2), nullable=False),
        _ck(t, "amounts_valid", "quantity > 0 AND unit_price >= 0"),
        _fk(t, "quotation_id", "crm_quotations.id", "CASCADE"),
        _fk(t, "tax_code_id", "fin_tax_codes.id"),
        _pk(t),
    )
    op.create_index("uq_crm_quotation_lines_no", t, ["quotation_id", "line_no"], unique=True)

    # An issued quotation is a record of what was offered: it cannot be rewritten.
    op.execute(
        """
        CREATE FUNCTION crm_quotation_frozen() RETURNS trigger AS $$
        BEGIN
            IF OLD.status NOT IN ('draft', 'awaiting_approval') AND (
                NEW.number IS DISTINCT FROM OLD.number
                OR NEW.customer_id <> OLD.customer_id
                OR NEW.currency <> OLD.currency
                OR NEW.quote_date <> OLD.quote_date
                OR NEW.valid_until <> OLD.valid_until
                OR NEW.title <> OLD.title
                OR NEW.subtotal <> OLD.subtotal
                OR NEW.tax_total <> OLD.tax_total
                OR NEW.total <> OLD.total
                OR NEW.terms IS DISTINCT FROM OLD.terms
            ) THEN
                RAISE EXCEPTION 'an issued quotation cannot be changed';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER crm_quotation_frozen BEFORE UPDATE ON crm_quotations
            FOR EACH ROW EXECUTE FUNCTION crm_quotation_frozen();

        CREATE FUNCTION crm_quotation_lines_frozen() RETURNS trigger AS $$
        DECLARE
            parent_status text;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                SELECT status INTO parent_status FROM crm_quotations WHERE id = OLD.quotation_id;
            ELSE
                SELECT status INTO parent_status FROM crm_quotations WHERE id = NEW.quotation_id;
            END IF;
            IF parent_status IS NOT NULL AND parent_status <> 'draft' THEN
                RAISE EXCEPTION 'quotation lines can change only while the quotation is a draft';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER crm_quotation_lines_frozen BEFORE INSERT OR UPDATE OR DELETE
            ON crm_quotation_lines FOR EACH ROW EXECUTE FUNCTION crm_quotation_lines_frozen();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS crm_quotation_lines_frozen ON crm_quotation_lines; "
        "DROP TRIGGER IF EXISTS crm_quotation_frozen ON crm_quotations; "
        "DROP FUNCTION IF EXISTS crm_quotation_lines_frozen(); "
        "DROP FUNCTION IF EXISTS crm_quotation_frozen();"
    )
    op.drop_table("crm_quotation_lines")
    op.drop_table("crm_quotations")
    op.drop_table("sys_approval_rules")
    op.drop_constraint(op.f(f"ck_{ORG}_print_requires_value"), ORG, type_="check")
    for name in (*ORG_FLAGS, *(n for n, _ in ORG_TEXT)):
        op.drop_column(ORG, name)
