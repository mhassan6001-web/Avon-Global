"""Inventory and logistics: products, warehouses, stock levels, an append-only
stock ledger, goods-received notes, shipments with events and documents,
delivery notes with proof of delivery.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-12

Additive only. Downgrade drops only the objects created here.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

QTY = sa.Numeric(18, 3)
COST = sa.Numeric(18, 4)
SEQUENCES = ("inv_grn_ref_seq", "lgx_shipment_ref_seq", "lgx_delivery_ref_seq")


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


def _created_at() -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


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


APPEND_ONLY_SQL = """
CREATE FUNCTION inv_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION '% is append-only; record a correcting entry instead', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER inv_stock_movements_append_only BEFORE UPDATE OR DELETE ON inv_stock_movements
    FOR EACH ROW EXECUTE FUNCTION inv_append_only();
CREATE TRIGGER lgx_shipment_events_append_only BEFORE UPDATE OR DELETE ON lgx_shipment_events
    FOR EACH ROW EXECUTE FUNCTION inv_append_only();
"""


def upgrade() -> None:
    for seq in SEQUENCES:
        op.execute(f"CREATE SEQUENCE {seq} START 1")

    t = "inv_products"
    op.create_table(
        t,
        _id(),
        sa.Column("sku", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("unit", sa.String(20), server_default="each", nullable=False),
        sa.Column("category", sa.String(120)),
        sa.Column("division", sa.String(40)),
        sa.Column("reorder_level", QTY, server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "reorder_non_negative", "reorder_level >= 0"),
        _ck(t, "sku_format", "sku ~ '^[A-Z0-9][A-Z0-9._\\-]{1,39}$'"),
        _fk(t, "created_by", "auth_users.id"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("sku", name=op.f(f"uq_{t}_sku")),
    )

    t = "inv_warehouses"
    op.create_table(
        t,
        _id(),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("location", sa.String(300)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _fk(t, "created_by", "auth_users.id"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("code", name=op.f(f"uq_{t}_code")),
    )

    t = "inv_stock_levels"
    op.create_table(
        t,
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", QTY, server_default="0", nullable=False),
        sa.Column("average_cost", COST, server_default="0", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        _ck(t, "no_negative_stock", "quantity >= 0"),
        _ck(t, "cost_non_negative", "average_cost >= 0"),
        _fk(t, "product_id", "inv_products.id"),
        _fk(t, "warehouse_id", "inv_warehouses.id"),
        sa.PrimaryKeyConstraint("product_id", "warehouse_id", name=op.f(f"pk_{t}")),
    )

    t = "inv_stock_movements"
    op.create_table(
        t,
        _id(),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("movement_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(14), nullable=False),
        sa.Column("quantity", QTY, nullable=False),
        sa.Column("unit_cost", COST, nullable=False),
        sa.Column("reference", sa.String(60)),
        sa.Column("reason", sa.Text()),
        sa.Column("source_type", sa.String(20)),
        sa.Column("source_id", sa.Uuid()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        _created_at(),
        _ck(
            t,
            "kind_valid",
            "kind IN ('opening', 'receipt', 'dispatch', 'adjustment', 'transfer_in', "
            "'transfer_out')",
        ),
        _ck(t, "quantity_non_zero", "quantity <> 0"),
        _ck(t, "cost_non_negative", "unit_cost >= 0"),
        _fk(t, "product_id", "inv_products.id"),
        _fk(t, "warehouse_id", "inv_warehouses.id"),
        _fk(t, "created_by", "auth_users.id"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
    )
    op.create_index("ix_inv_stock_movements_product_date", t, ["product_id", "movement_date"])

    t = "inv_goods_receipts"
    op.create_table(
        t,
        _id(),
        sa.Column("number", sa.String(24), nullable=False),
        sa.Column("purchase_order_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("received_on", sa.Date(), nullable=False),
        sa.Column("fx_rate", sa.Numeric(18, 6), nullable=False),
        sa.Column("delivery_note_ref", sa.String(120)),
        sa.Column("notes", sa.Text()),
        sa.Column("received_by", sa.Uuid(), nullable=False),
        _created_at(),
        _fk(t, "purchase_order_id", "prc_purchase_orders.id"),
        _fk(t, "warehouse_id", "inv_warehouses.id"),
        _fk(t, "received_by", "auth_users.id"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("number", name=op.f(f"uq_{t}_number")),
    )
    op.create_index(op.f(f"ix_{t}_purchase_order_id"), t, ["purchase_order_id"])

    t = "lgx_shipments"
    op.create_table(
        t,
        _id(),
        sa.Column("reference", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("mode", sa.String(12), nullable=False),
        sa.Column("carrier", sa.String(200)),
        sa.Column("tracking_number", sa.String(120)),
        sa.Column("origin", sa.String(200), nullable=False),
        sa.Column("destination", sa.String(200), nullable=False),
        sa.Column("purchase_order_id", sa.Uuid()),
        sa.Column("customer_id", sa.Uuid()),
        sa.Column("status", sa.String(12), server_default="planned", nullable=False),
        sa.Column("etd", sa.Date()),
        sa.Column("eta", sa.Date()),
        sa.Column("freight_cost", sa.Numeric(18, 2)),
        sa.Column("freight_currency", sa.String(3)),
        sa.Column("customs_entry_number", sa.String(120)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "direction_valid", "direction IN ('inbound', 'outbound')"),
        _ck(t, "mode_valid", "mode IN ('road', 'air', 'sea', 'rail', 'courier', 'multimodal')"),
        _ck(
            t,
            "status_valid",
            "status IN ('planned', 'in_transit', 'at_customs', 'cleared', 'arrived', "
            "'delivered', 'cancelled')",
        ),
        _ck(
            t,
            "currency_valid",
            "freight_currency IS NULL OR freight_currency IN ('MWK', 'USD', 'ZAR', 'ZMW')",
        ),
        _ck(t, "cost_non_negative", "freight_cost IS NULL OR freight_cost >= 0"),
        _ck(t, "eta_after_etd", "eta IS NULL OR etd IS NULL OR eta >= etd"),
        _fk(t, "purchase_order_id", "prc_purchase_orders.id"),
        _fk(t, "customer_id", "crm_customers.id"),
        _fk(t, "created_by", "auth_users.id"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("reference", name=op.f(f"uq_{t}_reference")),
    )

    t = "lgx_shipment_events"
    op.create_table(
        t,
        _id(),
        sa.Column("shipment_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("location", sa.String(200)),
        sa.Column("note", sa.Text()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        _created_at(),
        _fk(t, "shipment_id", "lgx_shipments.id"),
        _fk(t, "recorded_by", "auth_users.id"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
    )
    op.create_index(op.f(f"ix_{t}_shipment_id"), t, ["shipment_id"])

    t = "lgx_shipment_documents"
    op.create_table(
        t,
        _id(),
        sa.Column("shipment_id", sa.Uuid(), nullable=False),
        sa.Column("doc_type", sa.String(30), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("note", sa.String(300)),
        sa.Column("added_by", sa.Uuid(), nullable=False),
        _created_at(),
        _ck(
            t,
            "doc_type_valid",
            "doc_type IN ('bill_of_lading', 'airway_bill', 'commercial_invoice', "
            "'packing_list', 'certificate_of_origin', 'customs_declaration', "
            "'import_permit', 'insurance', 'other')",
        ),
        _fk(t, "shipment_id", "lgx_shipments.id"),
        _fk(t, "file_id", "sys_files.id"),
        _fk(t, "added_by", "auth_users.id"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
    )
    op.create_index(op.f(f"ix_{t}_shipment_id"), t, ["shipment_id"])

    t = "lgx_delivery_notes"
    op.create_table(
        t,
        _id(),
        sa.Column("number", sa.String(24), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("shipment_id", sa.Uuid()),
        sa.Column("invoice_id", sa.Uuid()),
        sa.Column("delivery_address", sa.Text(), nullable=False),
        sa.Column("scheduled_for", sa.Date()),
        sa.Column("status", sa.String(12), server_default="draft", nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("received_by_name", sa.String(200)),
        sa.Column("proof_file_id", sa.Uuid()),
        sa.Column("proof_note", sa.Text()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_ts(),
        _ck(t, "status_valid", "status IN ('draft', 'dispatched', 'delivered', 'cancelled')"),
        _ck(
            t,
            "delivered_has_proof",
            "status <> 'delivered' OR (received_by_name IS NOT NULL AND delivered_at IS NOT NULL)",
        ),
        _fk(t, "customer_id", "crm_customers.id"),
        _fk(t, "warehouse_id", "inv_warehouses.id"),
        _fk(t, "shipment_id", "lgx_shipments.id"),
        _fk(t, "invoice_id", "fin_invoices.id"),
        _fk(t, "proof_file_id", "sys_files.id"),
        _fk(t, "created_by", "auth_users.id"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("number", name=op.f(f"uq_{t}_number")),
    )

    t = "lgx_delivery_note_lines"
    op.create_table(
        t,
        _id(),
        sa.Column("delivery_note_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", QTY, nullable=False),
        _ck(t, "quantity_positive", "quantity > 0"),
        _fk(t, "delivery_note_id", "lgx_delivery_notes.id", "CASCADE"),
        _fk(t, "product_id", "inv_products.id"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{t}")),
        sa.UniqueConstraint("delivery_note_id", "line_no", name=op.f(f"uq_{t}_delivery_note_id")),
    )
    op.create_index(op.f(f"ix_{t}_delivery_note_id"), t, ["delivery_note_id"])

    op.execute(APPEND_ONLY_SQL)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS lgx_shipment_events_append_only ON lgx_shipment_events; "
        "DROP TRIGGER IF EXISTS inv_stock_movements_append_only ON inv_stock_movements; "
        "DROP FUNCTION IF EXISTS inv_append_only();"
    )
    for table in (
        "lgx_delivery_note_lines",
        "lgx_delivery_notes",
        "lgx_shipment_documents",
        "lgx_shipment_events",
        "lgx_shipments",
        "inv_goods_receipts",
        "inv_stock_movements",
        "inv_stock_levels",
        "inv_warehouses",
        "inv_products",
    ):
        op.drop_table(table)
    for seq in reversed(SEQUENCES):
        op.execute(f"DROP SEQUENCE {seq}")
