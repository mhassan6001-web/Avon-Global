"""Procurement: suppliers, encrypted bank accounts, purchase requests and lines,
supplier quotations, purchase orders and lines, reference sequences.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-12

Additive only. Downgrade drops only the objects created here.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CURRENCY = "currency IN ('MWK', 'USD', 'ZAR', 'ZMW')"


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


def _fk(
    table: str, column: str, target: str, ondelete: str | None = None
) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column],
        [target],
        name=op.f(f"fk_{table}_{column}_{target.split('.')[0]}"),
        ondelete=ondelete,
    )


def _ck(table: str, name: str, sql: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(sql, name=op.f(f"ck_{table}_{name}"))


def upgrade() -> None:
    for seq in ("prc_supplier_ref_seq", "prc_request_ref_seq", "prc_order_ref_seq"):
        op.execute(f"CREATE SEQUENCE {seq} START 1")

    t = "prc_suppliers"
    op.create_table(
        t,
        _id(),
        sa.Column("reference", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("country_code", sa.String(2), server_default="MW", nullable=False),
        sa.Column("city", sa.String(120)),
        sa.Column("categories", sa.String(300)),
        sa.Column("contact_name", sa.String(200)),
        sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(40)),
        sa.Column("registration_number", sa.String(100)),
        sa.Column("tax_number", sa.String(100)),
        sa.Column("status", sa.String(12), server_default="unverified", nullable=False),
        sa.Column("verified_by", sa.Uuid()),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("verification_note", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "status_valid", "status IN ('unverified', 'verified', 'suspended')"),
        _ck(t, "country_code_format", "country_code ~ '^[A-Z]{2}$'"),
        _fk(t, "verified_by", "auth_users.id"),
        _fk(t, "created_by", "auth_users.id"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("reference", name=op.f(f"uq_{t}_reference")),
    )
    op.create_index("ix_prc_suppliers_name_lower", t, [sa.text("lower(name)")])

    t = "prc_supplier_bank_accounts"
    op.create_table(
        t,
        _id(),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("bank_name", sa.String(200), nullable=False),
        sa.Column("account_name_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("account_number_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("branch_encrypted", sa.LargeBinary()),
        sa.Column("swift_encrypted", sa.LargeBinary()),
        sa.Column("account_last4", sa.String(4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(12), server_default="pending", nullable=False),
        sa.Column("approval_id", sa.Uuid()),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        *_ts(),
        _ck(t, "status_valid", "status IN ('pending', 'active', 'superseded', 'rejected')"),
        _fk(t, "supplier_id", "prc_suppliers.id"),
        _fk(t, "approval_id", "sys_approval_requests.id"),
        _fk(t, "requested_by", "auth_users.id"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
    )
    op.create_index(op.f(f"ix_{t}_supplier_id"), t, ["supplier_id"])
    op.create_index(
        "uq_prc_supplier_bank_one_active",
        t,
        ["supplier_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    t = "prc_purchase_requests"
    op.create_table(
        t,
        _id(),
        sa.Column("reference", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("justification", sa.Text()),
        sa.Column("division", sa.String(40)),
        sa.Column("needed_by", sa.Date()),
        sa.Column("currency", sa.String(3), server_default="MWK", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("selected_quote_id", sa.Uuid()),
        sa.Column("approval_id", sa.Uuid()),
        sa.Column("tender_id", sa.Uuid()),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(
            t,
            "status_valid",
            "status IN ('draft', 'awaiting_approval', 'approved', 'rejected', 'ordered', "
            "'cancelled')",
        ),
        _ck(t, "currency_valid", CURRENCY),
        _fk(t, "approval_id", "sys_approval_requests.id"),
        _fk(t, "tender_id", "tnd_tenders.id"),
        _fk(t, "requested_by", "auth_users.id"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("reference", name=op.f(f"uq_{t}_reference")),
    )

    t = "prc_purchase_request_lines"
    op.create_table(
        t,
        _id(),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit", sa.String(20), server_default="each", nullable=False),
        _ck(t, "quantity_positive", "quantity > 0"),
        _fk(t, "request_id", "prc_purchase_requests.id", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("request_id", "line_no", name=op.f(f"uq_{t}_request_id")),
    )
    op.create_index(op.f(f"ix_{t}_request_id"), t, ["request_id"])

    t = "prc_supplier_quotes"
    op.create_table(
        t,
        _id(),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_reference", sa.String(120)),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("valid_until", sa.Date()),
        sa.Column("lead_time_days", sa.Integer()),
        sa.Column("delivery_terms", sa.String(120)),
        sa.Column("notes", sa.Text()),
        sa.Column("file_id", sa.Uuid()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "currency_valid", CURRENCY),
        _fk(t, "request_id", "prc_purchase_requests.id", "CASCADE"),
        _fk(t, "supplier_id", "prc_suppliers.id"),
        _fk(t, "file_id", "sys_files.id"),
        _fk(t, "created_by", "auth_users.id"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
    )
    op.create_index(op.f(f"ix_{t}_request_id"), t, ["request_id"])

    t = "prc_supplier_quote_lines"
    op.create_table(
        t,
        _id(),
        sa.Column("quote_id", sa.Uuid(), nullable=False),
        sa.Column("request_line_id", sa.Uuid(), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        _ck(t, "price_non_negative", "unit_price >= 0"),
        _fk(t, "quote_id", "prc_supplier_quotes.id", "CASCADE"),
        _fk(t, "request_line_id", "prc_purchase_request_lines.id", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("quote_id", "request_line_id", name=op.f(f"uq_{t}_quote_id")),
    )
    op.create_index(op.f(f"ix_{t}_quote_id"), t, ["quote_id"])

    t = "prc_purchase_orders"
    op.create_table(
        t,
        _id(),
        sa.Column("reference", sa.String(20), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("quote_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(20), server_default="issued", nullable=False),
        sa.Column("delivery_address", sa.Text()),
        sa.Column("expected_delivery", sa.Date()),
        sa.Column("cancel_reason", sa.Text()),
        sa.Column("issued_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(
            t,
            "status_valid",
            "status IN ('issued', 'partially_received', 'received', 'cancelled')",
        ),
        _ck(t, "currency_valid", CURRENCY),
        _ck(t, "total_non_negative", "total_amount >= 0"),
        _fk(t, "request_id", "prc_purchase_requests.id"),
        _fk(t, "quote_id", "prc_supplier_quotes.id"),
        _fk(t, "supplier_id", "prc_suppliers.id"),
        _fk(t, "issued_by", "auth_users.id"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("reference", name=op.f(f"uq_{t}_reference")),
        sa.UniqueConstraint("request_id", name=op.f(f"uq_{t}_request_id")),
    )

    t = "prc_purchase_order_lines"
    op.create_table(
        t,
        _id(),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("received_quantity", sa.Numeric(18, 3), server_default="0", nullable=False),
        _ck(t, "quantity_positive", "quantity > 0"),
        _ck(t, "received_non_negative", "received_quantity >= 0"),
        _ck(t, "received_within_ordered", "received_quantity <= quantity"),
        _fk(t, "order_id", "prc_purchase_orders.id", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("order_id", "line_no", name=op.f(f"uq_{t}_order_id")),
    )
    op.create_index(op.f(f"ix_{t}_order_id"), t, ["order_id"])


def downgrade() -> None:
    for table in (
        "prc_purchase_order_lines",
        "prc_purchase_orders",
        "prc_supplier_quote_lines",
        "prc_supplier_quotes",
        "prc_purchase_request_lines",
        "prc_purchase_requests",
        "prc_supplier_bank_accounts",
        "prc_suppliers",
    ):
        op.drop_table(table)
    for seq in ("prc_order_ref_seq", "prc_request_ref_seq", "prc_supplier_ref_seq"):
        op.execute(f"DROP SEQUENCE {seq}")
