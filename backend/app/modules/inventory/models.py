"""Inventory (Stage 8): products, warehouses, an append-only stock ledger,
per-warehouse levels with weighted-average cost, and goods-received notes.

Stock levels never go negative (database check). Movements are append-only
(trigger in migration 0008): a mistake is corrected by a new adjustment.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

QTY = Numeric(18, 3)
COST = Numeric(18, 4)
MOVEMENT_KINDS = ("opening", "receipt", "dispatch", "adjustment", "transfer_in", "transfer_out")


class Product(TimestampMixin, Base):
    __tablename__ = "inv_products"
    __table_args__ = (
        CheckConstraint("reorder_level >= 0", name="reorder_non_negative"),
        CheckConstraint("sku ~ '^[A-Z0-9][A-Z0-9._\\-]{1,39}$'", name="sku_format"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    sku: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, server_default="each")
    category: Mapped[str | None] = mapped_column(String(120))
    division: Mapped[str | None] = mapped_column(String(40))
    reorder_level: Mapped[Decimal] = mapped_column(QTY, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class Warehouse(TimestampMixin, Base):
    __tablename__ = "inv_warehouses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(300))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class StockLevel(Base):
    __tablename__ = "inv_stock_levels"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="no_negative_stock"),
        CheckConstraint("average_cost >= 0", name="cost_non_negative"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inv_products.id"), primary_key=True)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inv_warehouses.id"), primary_key=True
    )
    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False, server_default="0")
    average_cost: Mapped[Decimal] = mapped_column(COST, nullable=False, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class StockMovement(Base):
    __tablename__ = "inv_stock_movements"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('opening', 'receipt', 'dispatch', 'adjustment', 'transfer_in', "
            "'transfer_out')",
            name="kind_valid",
        ),
        CheckConstraint("quantity <> 0", name="quantity_non_zero"),
        CheckConstraint("unit_cost >= 0", name="cost_non_negative"),
        Index("ix_inv_stock_movements_product_date", "product_id", "movement_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inv_products.id"), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inv_warehouses.id"), nullable=False)
    movement_date: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[str] = mapped_column(String(14), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)  # + in, - out
    unit_cost: Mapped[Decimal] = mapped_column(COST, nullable=False)  # functional currency
    reference: Mapped[str | None] = mapped_column(String(60))
    reason: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str | None] = mapped_column(String(20))
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class GoodsReceipt(Base):
    """A goods-received note (GRN) against a purchase order."""

    __tablename__ = "inv_goods_receipts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    number: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prc_purchase_orders.id"), nullable=False, index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inv_warehouses.id"), nullable=False)
    received_on: Mapped[date] = mapped_column(Date, nullable=False)
    fx_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    delivery_note_ref: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    received_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
