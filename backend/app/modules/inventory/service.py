"""Stock ledger with weighted-average cost. All quantities and costs are Decimal."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.modules.finance import posting
from app.modules.procurement.models import PurchaseOrder, PurchaseOrderLine
from app.platform.audit import service as audit
from app.platform.references import next_reference

from . import schemas
from .models import GoodsReceipt, Product, StockLevel, StockMovement, Warehouse

COST_PLACES = Decimal("0.0001")


class InventoryRuleError(AppError):
    status_code = 422
    code = "validation_error"


def _audit(
    db: Session, action: str, actor: uuid.UUID, kind: str, target: Any, **details: Any
) -> None:
    audit.record(
        db,
        action=f"inventory.{action}",
        actor_id=actor,
        target_type=kind,
        target_id=target,
        details=details,
    )


def get_product(db: Session, product_id: uuid.UUID) -> Product:
    row = db.get(Product, product_id)
    if row is None:
        raise NotFoundError("Product not found.")
    return row


def get_warehouse(db: Session, warehouse_id: uuid.UUID) -> Warehouse:
    row = db.get(Warehouse, warehouse_id)
    if row is None or not row.is_active:
        raise NotFoundError("Warehouse not found.")
    return row


def _lock_level(db: Session, product_id: uuid.UUID, warehouse_id: uuid.UUID) -> StockLevel:
    db.execute(
        text(
            "INSERT INTO inv_stock_levels (product_id, warehouse_id, quantity, average_cost) "
            "VALUES (:p, :w, 0, 0) ON CONFLICT DO NOTHING"
        ),
        {"p": product_id, "w": warehouse_id},
    )
    level = db.execute(
        select(StockLevel)
        .where(StockLevel.product_id == product_id, StockLevel.warehouse_id == warehouse_id)
        .with_for_update()
    ).scalar_one()
    db.refresh(level)
    return level


def move_in(
    db: Session,
    *,
    product: Product,
    warehouse: Warehouse,
    quantity: Decimal,
    unit_cost: Decimal,
    kind: str,
    on: date,
    actor: uuid.UUID,
    reference: str | None = None,
    reason: str | None = None,
    source: tuple[str, uuid.UUID] | None = None,
) -> StockMovement:
    if quantity <= 0:
        raise InventoryRuleError("Quantity received must be greater than zero.")
    if unit_cost < 0:
        raise InventoryRuleError("Unit cost cannot be negative.")
    if not product.is_active:
        raise InventoryRuleError(f"Product {product.sku} is inactive.")
    level = _lock_level(db, product.id, warehouse.id)
    total_qty = level.quantity + quantity
    level.average_cost = (
        (level.quantity * level.average_cost + quantity * unit_cost) / total_qty
    ).quantize(COST_PLACES, rounding=ROUND_HALF_UP)
    level.quantity = total_qty
    level.updated_at = posting.now()
    movement = StockMovement(
        product_id=product.id,
        warehouse_id=warehouse.id,
        movement_date=on,
        kind=kind,
        quantity=quantity,
        unit_cost=unit_cost.quantize(COST_PLACES, rounding=ROUND_HALF_UP),
        reference=reference,
        reason=reason,
        source_type=source[0] if source else None,
        source_id=source[1] if source else None,
        created_by=actor,
    )
    db.add(movement)
    db.flush()
    return movement


def move_out(
    db: Session,
    *,
    product: Product,
    warehouse: Warehouse,
    quantity: Decimal,
    kind: str,
    on: date,
    actor: uuid.UUID,
    reference: str | None = None,
    reason: str | None = None,
    source: tuple[str, uuid.UUID] | None = None,
) -> StockMovement:
    if quantity <= 0:
        raise InventoryRuleError("Quantity must be greater than zero.")
    level = _lock_level(db, product.id, warehouse.id)
    if level.quantity < quantity:
        raise ConflictError(
            f"Only {level.quantity.normalize()} {product.unit} of {product.sku} "
            f"in {warehouse.code}; {quantity.normalize()} requested."
        )
    level.quantity -= quantity
    level.updated_at = posting.now()
    movement = StockMovement(
        product_id=product.id,
        warehouse_id=warehouse.id,
        movement_date=on,
        kind=kind,
        quantity=-quantity,
        unit_cost=level.average_cost,
        reference=reference,
        reason=reason,
        source_type=source[0] if source else None,
        source_id=source[1] if source else None,
        created_by=actor,
    )
    db.add(movement)
    db.flush()
    return movement


def create_product(db: Session, body: schemas.ProductIn, actor: uuid.UUID) -> Product:
    if db.execute(select(Product.id).where(Product.sku == body.sku)).first():
        raise ConflictError(f"SKU {body.sku} already exists.")
    row = Product(created_by=actor, **body.model_dump())
    db.add(row)
    db.flush()
    _audit(db, "product.created", actor, "inv_product", row.id, sku=row.sku)
    return row


def update_product(
    db: Session, row: Product, body: schemas.ProductPatch, actor: uuid.UUID
) -> Product:
    changes = {
        k: v
        for k, v in body.model_dump(exclude_unset=True).items()
        if v is not None or k in ("category", "division", "notes")
    }
    for key, value in changes.items():
        setattr(row, key, value)
    if changes:
        _audit(db, "product.updated", actor, "inv_product", row.id, fields=sorted(changes))
    return row


def create_warehouse(db: Session, body: schemas.WarehouseIn, actor: uuid.UUID) -> Warehouse:
    if db.execute(select(Warehouse.id).where(Warehouse.code == body.code)).first():
        raise ConflictError(f"Warehouse code {body.code} already exists.")
    row = Warehouse(created_by=actor, **body.model_dump())
    db.add(row)
    db.flush()
    _audit(db, "warehouse.created", actor, "inv_warehouse", row.id, code=row.code)
    return row


def products_out(db: Session, rows: list[Product]) -> list[schemas.ProductOut]:
    if not rows:
        return []
    totals = {
        pid: (Decimal(q), Decimal(v))
        for pid, q, v in db.execute(
            select(
                StockLevel.product_id,
                func.coalesce(func.sum(StockLevel.quantity), 0),
                func.coalesce(func.sum(StockLevel.quantity * StockLevel.average_cost), 0),
            )
            .where(StockLevel.product_id.in_([r.id for r in rows]))
            .group_by(StockLevel.product_id)
        ).all()
    }
    out = []
    for r in rows:
        qty, value = totals.get(r.id, (Decimal(0), Decimal(0)))
        out.append(
            schemas.ProductOut(
                id=r.id,
                sku=r.sku,
                name=r.name,
                unit=r.unit,
                category=r.category,
                division=r.division,
                reorder_level=r.reorder_level,
                is_active=r.is_active,
                notes=r.notes,
                on_hand=qty,
                value=posting.money(value),
                below_reorder=r.is_active and r.reorder_level > 0 and qty <= r.reorder_level,
            )
        )
    return out


def adjust(db: Session, body: schemas.AdjustmentIn, actor: uuid.UUID) -> StockMovement:
    product = get_product(db, body.product_id)
    warehouse = get_warehouse(db, body.warehouse_id)
    if body.quantity == 0:
        raise InventoryRuleError("An adjustment cannot be zero.")
    if body.quantity > 0:
        cost = body.unit_cost
        if cost is None:
            level = _lock_level(db, product.id, warehouse.id)
            if level.average_cost == 0 and body.kind == "opening":
                raise InventoryRuleError("Opening stock needs a unit cost.")
            cost = level.average_cost
        movement = move_in(
            db,
            product=product,
            warehouse=warehouse,
            quantity=body.quantity,
            unit_cost=cost,
            kind=body.kind,
            on=body.movement_date,
            actor=actor,
            reason=body.reason,
        )
    else:
        if body.kind == "opening":
            raise InventoryRuleError("Opening stock must be a positive quantity.")
        movement = move_out(
            db,
            product=product,
            warehouse=warehouse,
            quantity=-body.quantity,
            kind="adjustment",
            on=body.movement_date,
            actor=actor,
            reason=body.reason,
        )
    _audit(
        db,
        f"stock.{body.kind}",
        actor,
        "inv_product",
        product.id,
        warehouse=warehouse.code,
        quantity=body.quantity,
        reason=body.reason,
    )
    return movement


def transfer(db: Session, body: schemas.TransferIn, actor: uuid.UUID) -> None:
    if body.from_warehouse_id == body.to_warehouse_id:
        raise InventoryRuleError("Choose two different warehouses.")
    product = get_product(db, body.product_id)
    source = get_warehouse(db, body.from_warehouse_id)
    target = get_warehouse(db, body.to_warehouse_id)
    out = move_out(
        db,
        product=product,
        warehouse=source,
        quantity=body.quantity,
        kind="transfer_out",
        on=body.movement_date,
        actor=actor,
        reference=target.code,
        reason=body.reason,
    )
    move_in(
        db,
        product=product,
        warehouse=target,
        quantity=body.quantity,
        unit_cost=out.unit_cost,
        kind="transfer_in",
        on=body.movement_date,
        actor=actor,
        reference=source.code,
        reason=body.reason,
    )
    _audit(
        db,
        "stock.transfer",
        actor,
        "inv_product",
        product.id,
        source=source.code,
        destination=target.code,
        quantity=body.quantity,
    )


def receive_goods(db: Session, body: schemas.GoodsReceiptIn, actor: uuid.UUID) -> GoodsReceipt:
    order = db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == body.purchase_order_id).with_for_update()
    ).scalar_one_or_none()
    if order is None:
        raise NotFoundError("Purchase order not found.")
    if order.status not in ("issued", "partially_received"):
        raise ConflictError("Goods can only be received against an open purchase order.")
    warehouse = get_warehouse(db, body.warehouse_id)
    rate = posting.rate_for(db, order.currency, body.received_on, body.fx_rate)
    lines = {
        line.line_no: line
        for line in db.execute(
            select(PurchaseOrderLine)
            .where(PurchaseOrderLine.order_id == order.id)
            .with_for_update()
        ).scalars()
    }
    if len({line.line_no for line in body.lines}) != len(body.lines):
        raise InventoryRuleError("Receive each order line only once per note.")
    number = next_reference(db, "GRN")
    grn = GoodsReceipt(
        number=number,
        purchase_order_id=order.id,
        warehouse_id=warehouse.id,
        received_on=body.received_on,
        fx_rate=rate,
        delivery_note_ref=body.delivery_note_ref,
        notes=body.notes,
        received_by=actor,
    )
    db.add(grn)
    db.flush()
    for item in body.lines:
        line = lines.get(item.line_no)
        if line is None:
            raise InventoryRuleError(f"Order {order.reference} has no line {item.line_no}.")
        remaining = line.quantity - line.received_quantity
        if item.quantity > remaining:
            raise ConflictError(
                f"Line {item.line_no}: only {remaining.normalize()} {line.unit} still to receive."
            )
        product = get_product(db, item.product_id)
        move_in(
            db,
            product=product,
            warehouse=warehouse,
            quantity=item.quantity,
            unit_cost=line.unit_price * rate,
            kind="receipt",
            on=body.received_on,
            actor=actor,
            reference=number,
            source=("goods_receipt", grn.id),
        )
        line.received_quantity += item.quantity
    db.flush()
    all_lines = list(lines.values())
    order.status = (
        "received"
        if all(line.received_quantity >= line.quantity for line in all_lines)
        else "partially_received"
    )
    _audit(db, "goods.received", actor, "purchase_order", order.id, grn=number)
    return grn


def levels(db: Session, product_id: uuid.UUID | None = None) -> list[schemas.LevelOut]:
    stmt = (
        select(StockLevel, Product.sku, Product.name, Warehouse.code)
        .join(Product, Product.id == StockLevel.product_id)
        .join(Warehouse, Warehouse.id == StockLevel.warehouse_id)
        .where(StockLevel.quantity != 0)
        .order_by(Product.sku, Warehouse.code)
    )
    if product_id:
        stmt = stmt.where(StockLevel.product_id == product_id)
    return [
        schemas.LevelOut(
            product_id=level.product_id,
            sku=sku,
            product_name=name,
            warehouse_id=level.warehouse_id,
            warehouse_code=code,
            quantity=level.quantity,
            average_cost=level.average_cost,
            value=posting.money(level.quantity * level.average_cost),
        )
        for level, sku, name, code in db.execute(stmt).all()
    ]


def movements(db: Session, product_id: uuid.UUID | None, limit: int) -> list[schemas.MovementOut]:
    stmt = (
        select(StockMovement, Product.sku, Warehouse.code)
        .join(Product, Product.id == StockMovement.product_id)
        .join(Warehouse, Warehouse.id == StockMovement.warehouse_id)
        .order_by(StockMovement.created_at.desc())
        .limit(limit)
    )
    if product_id:
        stmt = stmt.where(StockMovement.product_id == product_id)
    return [
        schemas.MovementOut(
            id=m.id,
            product_id=m.product_id,
            sku=sku,
            warehouse_code=code,
            movement_date=m.movement_date,
            kind=m.kind,
            quantity=m.quantity,
            unit_cost=m.unit_cost,
            reference=m.reference,
            reason=m.reason,
            created_at=m.created_at,
        )
        for m, sku, code in db.execute(stmt).all()
    ]


def summary(db: Session) -> schemas.InventorySummary:
    products = list(db.execute(select(Product).where(Product.is_active)).scalars())
    out = products_out(db, products)
    return schemas.InventorySummary(
        has_records=bool(products),
        functional_currency=posting.functional_currency(db),
        products=len(products),
        stock_value=sum((p.value for p in out), Decimal(0)),
        below_reorder=sum(1 for p in out if p.below_reorder),
    )
