"""Perpetual inventory accounting: posting settings, stock journals, return and damage movements.

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-13

Additive: one new table and two check constraints widened to allow new
values. No data is changed. Downgrade restores the narrower constraints and
therefore fails, by design, if stock journals or return/damage movements
exist (they must not be silently lost).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MOVES = "inv_stock_movements"
JOURNALS = "fin_journal_entries"
KINDS_OLD = "'opening', 'receipt', 'dispatch', 'adjustment', 'transfer_in', 'transfer_out'"
SOURCES_OLD = "'manual', 'invoice', 'receipt', 'credit_note', 'bill', 'payment', 'reversal'"


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


def _swap(table: str, name: str, condition: str) -> None:
    full = op.f(f"ck_{table}_{name}")
    op.drop_constraint(full, table, type_="check")
    op.create_check_constraint(full, table, condition)


def upgrade() -> None:
    _swap(MOVES, "kind_valid", f"kind IN ({KINDS_OLD}, 'return_in', 'damage')")
    _swap(JOURNALS, "source_valid", f"source_type IN ({SOURCES_OLD}, 'stock')")

    t = "fin_stock_posting"
    op.create_table(
        t,
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "valuation_method", sa.String(20), server_default="weighted_average", nullable=False
        ),
        sa.Column("inventory_account_id", sa.Uuid()),
        sa.Column("grni_account_id", sa.Uuid()),
        sa.Column("cogs_account_id", sa.Uuid()),
        sa.Column("adjustment_account_id", sa.Uuid()),
        sa.Column("opening_account_id", sa.Uuid()),
        sa.Column("reviewed_by_name", sa.String(200)),
        sa.Column("reviewed_on", sa.Date()),
        sa.Column("updated_by", sa.Uuid()),
        _now("updated_at"),
        _ck(t, "single_row", "id = 1"),
        _ck(t, "method_valid", "valuation_method IN ('weighted_average')"),
        _ck(
            t,
            "enabled_requires_setup",
            "NOT enabled OR (inventory_account_id IS NOT NULL AND grni_account_id IS NOT NULL "
            "AND cogs_account_id IS NOT NULL AND adjustment_account_id IS NOT NULL "
            "AND opening_account_id IS NOT NULL AND reviewed_by_name IS NOT NULL "
            "AND reviewed_on IS NOT NULL)",
        ),
        *(
            _fk(t, column, "fin_accounts.id")
            for column in (
                "inventory_account_id",
                "grni_account_id",
                "cogs_account_id",
                "adjustment_account_id",
                "opening_account_id",
            )
        ),
        _fk(t, "updated_by", "auth_users.id"),
        _pk(t),
    )


def downgrade() -> None:
    op.drop_table("fin_stock_posting")
    _swap(JOURNALS, "source_valid", f"source_type IN ({SOURCES_OLD})")
    _swap(MOVES, "kind_valid", f"kind IN ({KINDS_OLD})")
