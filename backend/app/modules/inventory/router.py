"""Inventory API (``/api/v1/inventory``). Logistics' section; the Director sees all."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select

from app.modules.procurement.models import PurchaseOrder, PurchaseOrderLine, Supplier
from app.platform.authz.deps import DbSession, Principal, require

from . import schemas
from . import service as inv
from .models import GoodsReceipt, Product, Warehouse

router = APIRouter(prefix="/inventory", tags=["inventory"])

View = Depends(require("inventory.records.view"))
Edit = Depends(require("inventory.records.edit"))


@router.get("/summary", response_model=schemas.InventorySummary)
def summary(db: DbSession, _: Principal = View) -> schemas.InventorySummary:
    return inv.summary(db)


@router.get("/products", response_model=list[schemas.ProductOut])
def list_products(
    db: DbSession,
    _: Principal = View,
    q: str | None = Query(default=None, max_length=100),
    below_reorder: bool = False,
    include_inactive: bool = False,
) -> list[schemas.ProductOut]:
    stmt = select(Product).order_by(Product.sku)
    if not include_inactive:
        stmt = stmt.where(Product.is_active)
    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Product.sku).like(like),
                func.lower(Product.name).like(like),
                func.lower(func.coalesce(Product.category, "")).like(like),
            )
        )
    out = inv.products_out(db, list(db.execute(stmt.limit(500)).scalars()))
    return [p for p in out if p.below_reorder] if below_reorder else out


@router.post("/products", response_model=schemas.ProductOut, status_code=201)
def create_product(
    body: schemas.ProductIn, db: DbSession, principal: Principal = Edit
) -> schemas.ProductOut:
    row = inv.create_product(db, body, principal.user.id)
    db.commit()
    return inv.products_out(db, [row])[0]


@router.patch("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: uuid.UUID, body: schemas.ProductPatch, db: DbSession, principal: Principal = Edit
) -> schemas.ProductOut:
    row = inv.update_product(db, inv.get_product(db, product_id), body, principal.user.id)
    db.commit()
    return inv.products_out(db, [row])[0]


@router.get("/warehouses", response_model=list[schemas.WarehouseOut])
def list_warehouses(db: DbSession, _: Principal = View) -> list[schemas.WarehouseOut]:
    rows = db.execute(select(Warehouse).order_by(Warehouse.code)).scalars()
    return [schemas.WarehouseOut.model_validate(w) for w in rows]


@router.post("/warehouses", response_model=schemas.WarehouseOut, status_code=201)
def create_warehouse(
    body: schemas.WarehouseIn, db: DbSession, principal: Principal = Edit
) -> schemas.WarehouseOut:
    row = inv.create_warehouse(db, body, principal.user.id)
    db.commit()
    return schemas.WarehouseOut.model_validate(row)


@router.get("/levels", response_model=list[schemas.LevelOut])
def stock_levels(
    db: DbSession, _: Principal = View, product_id: uuid.UUID | None = None
) -> list[schemas.LevelOut]:
    return inv.levels(db, product_id)


@router.get("/movements", response_model=list[schemas.MovementOut])
def list_movements(
    db: DbSession,
    _: Principal = View,
    product_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[schemas.MovementOut]:
    return inv.movements(db, product_id, limit)


@router.post("/adjustments", response_model=schemas.MovementOut, status_code=201)
def adjust(
    body: schemas.AdjustmentIn, db: DbSession, principal: Principal = Edit
) -> schemas.MovementOut:
    movement = inv.adjust(db, body, principal.user.id)
    db.commit()
    return next(m for m in inv.movements(db, movement.product_id, 5) if m.id == movement.id)


@router.post("/transfers", response_model=list[schemas.LevelOut])
def transfer(
    body: schemas.TransferIn, db: DbSession, principal: Principal = Edit
) -> list[schemas.LevelOut]:
    inv.transfer(db, body, principal.user.id)
    db.commit()
    return inv.levels(db, body.product_id)


def _grn_out(db: DbSession, grn: GoodsReceipt) -> schemas.GoodsReceiptOut:
    order = db.get_one(PurchaseOrder, grn.purchase_order_id)
    return schemas.GoodsReceiptOut(
        id=grn.id,
        number=grn.number,
        purchase_order_id=order.id,
        purchase_order_reference=order.reference,
        warehouse_id=grn.warehouse_id,
        received_on=grn.received_on,
        fx_rate=grn.fx_rate,
        delivery_note_ref=grn.delivery_note_ref,
        order_status=order.status,
        created_at=grn.created_at,
    )


@router.get("/goods-receipts", response_model=list[schemas.GoodsReceiptOut])
def list_goods_receipts(db: DbSession, _: Principal = View) -> list[schemas.GoodsReceiptOut]:
    rows = db.execute(select(GoodsReceipt).order_by(GoodsReceipt.created_at.desc()).limit(200))
    return [_grn_out(db, g) for g in rows.scalars()]


@router.post("/goods-receipts", response_model=schemas.GoodsReceiptOut, status_code=201)
def receive_goods(
    body: schemas.GoodsReceiptIn, db: DbSession, principal: Principal = Edit
) -> schemas.GoodsReceiptOut:
    grn = inv.receive_goods(db, body, principal.user.id)
    db.commit()
    return _grn_out(db, grn)


@router.get("/open-orders")
def open_orders(db: DbSession, _: Principal = View) -> list[dict[str, object]]:
    """Purchase orders that still have goods to receive (no prices: Logistics sees quantities)."""
    orders = db.execute(
        select(PurchaseOrder, Supplier.name)
        .join(Supplier, Supplier.id == PurchaseOrder.supplier_id)
        .where(PurchaseOrder.status.in_(("issued", "partially_received")))
        .order_by(PurchaseOrder.created_at)
    ).all()
    out: list[dict[str, object]] = []
    for order, supplier in orders:
        lines = db.execute(
            select(PurchaseOrderLine)
            .where(PurchaseOrderLine.order_id == order.id)
            .order_by(PurchaseOrderLine.line_no)
        ).scalars()
        out.append(
            {
                "id": str(order.id),
                "reference": order.reference,
                "supplier": supplier,
                "lines": [
                    {
                        "line_no": line.line_no,
                        "description": line.description,
                        "unit": line.unit,
                        "ordered": str(line.quantity),
                        "received": str(line.received_quantity),
                    }
                    for line in lines
                ],
            }
        )
    return out
