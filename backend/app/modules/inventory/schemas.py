"""Inventory request and response models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.crm.schemas import Division

Qty = Decimal


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProductIn(_In):
    sku: str = Field(pattern=r"^[A-Z0-9][A-Z0-9._\-]{1,39}$")
    name: str = Field(min_length=2, max_length=200)
    unit: str = Field(default="each", min_length=1, max_length=20)
    category: str | None = Field(default=None, max_length=120)
    division: Division | None = None
    reorder_level: Decimal = Field(default=Decimal(0), ge=0, max_digits=18, decimal_places=3)
    notes: str | None = Field(default=None, max_length=5000)


class ProductPatch(_In):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    category: str | None = Field(default=None, max_length=120)
    division: Division | None = None
    reorder_level: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=3)
    is_active: bool | None = None
    notes: str | None = Field(default=None, max_length=5000)


class ProductOut(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    unit: str
    category: str | None
    division: str | None
    reorder_level: Decimal
    is_active: bool
    notes: str | None
    on_hand: Decimal
    value: Decimal
    below_reorder: bool


class WarehouseIn(_In):
    code: str = Field(pattern=r"^[A-Z0-9\-]{2,20}$")
    name: str = Field(min_length=2, max_length=200)
    location: str | None = Field(default=None, max_length=300)


class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    location: str | None
    is_active: bool


class LevelOut(BaseModel):
    product_id: uuid.UUID
    sku: str
    product_name: str
    warehouse_id: uuid.UUID
    warehouse_code: str
    quantity: Decimal
    average_cost: Decimal
    value: Decimal


class AdjustmentIn(_In):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: Decimal = Field(max_digits=18, decimal_places=3)  # + found, - lost/damaged
    unit_cost: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=4)
    movement_date: date
    kind: Literal["adjustment", "opening"] = "adjustment"
    reason: str = Field(min_length=3, max_length=2000)


class TransferIn(_In):
    product_id: uuid.UUID
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=3)
    movement_date: date
    reason: str | None = Field(default=None, max_length=2000)


class ReceiveLineIn(_In):
    line_no: int = Field(ge=1)
    product_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=3)


class GoodsReceiptIn(_In):
    purchase_order_id: uuid.UUID
    warehouse_id: uuid.UUID
    received_on: date
    fx_rate: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    delivery_note_ref: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=5000)
    lines: list[ReceiveLineIn] = Field(min_length=1, max_length=200)


class GoodsReceiptOut(BaseModel):
    id: uuid.UUID
    number: str
    purchase_order_id: uuid.UUID
    purchase_order_reference: str
    warehouse_id: uuid.UUID
    received_on: date
    fx_rate: Decimal
    delivery_note_ref: str | None
    order_status: str
    created_at: datetime


class MovementOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    sku: str
    warehouse_code: str
    movement_date: date
    kind: str
    quantity: Decimal
    unit_cost: Decimal
    reference: str | None
    reason: str | None
    created_at: datetime


class InventorySummary(BaseModel):
    has_records: bool
    functional_currency: str
    products: int
    stock_value: Decimal
    below_reorder: int
