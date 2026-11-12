"""Procurement API (``/api/v1/procurement``). Procurement's section; Director approves."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.modules.organisation.models import OrganisationProfile
from app.platform.authz.deps import DbSession, Principal, require

from . import landed_cost, schemas
from . import service as prc
from .models import PurchaseOrder

router = APIRouter(prefix="/procurement", tags=["procurement"])

View = Depends(require("procurement.records.view"))
Edit = Depends(require("procurement.records.edit"))


# --- Suppliers ---------------------------------------------------------------


@router.get("/suppliers", response_model=schemas.Page[schemas.SupplierOut])
def list_suppliers(
    db: DbSession,
    _: Principal = View,
    q: str | None = Query(default=None, max_length=100),
    status: str | None = Query(default=None, pattern="^(unverified|verified|suspended)$"),
    page: int = Query(default=1, ge=1, le=10_000),
    size: int = Query(default=25, ge=1, le=100),
) -> schemas.Page[schemas.SupplierOut]:
    return prc.list_suppliers(db, q=q.strip() if q else None, status=status, page=page, size=size)


@router.post("/suppliers", response_model=schemas.SupplierOut, status_code=201)
def create_supplier(
    body: schemas.SupplierIn, db: DbSession, principal: Principal = Edit
) -> schemas.SupplierOut:
    row = prc.create_supplier(db, body, principal.user.id)
    db.commit()
    return prc.suppliers_out(db, [row])[0]


@router.get("/suppliers/{supplier_id}", response_model=schemas.SupplierDetail)
def supplier_detail(
    supplier_id: uuid.UUID, db: DbSession, principal: Principal = View
) -> schemas.SupplierDetail:
    row = prc.get_supplier(db, supplier_id)
    accounts, full = prc.bank_accounts(db, row, principal)
    return schemas.SupplierDetail(
        supplier=prc.suppliers_out(db, [row])[0], bank_accounts=accounts, bank_details_visible=full
    )


@router.patch("/suppliers/{supplier_id}", response_model=schemas.SupplierOut)
def update_supplier(
    supplier_id: uuid.UUID, body: schemas.SupplierPatch, db: DbSession, principal: Principal = Edit
) -> schemas.SupplierOut:
    row = prc.update_supplier(db, prc.get_supplier(db, supplier_id), body, principal.user.id)
    db.commit()
    return prc.suppliers_out(db, [row])[0]


@router.post("/suppliers/{supplier_id}/verification", response_model=schemas.SupplierOut)
def set_verification(
    supplier_id: uuid.UUID,
    body: schemas.VerificationIn,
    db: DbSession,
    principal: Principal = Edit,
) -> schemas.SupplierOut:
    row = prc.set_verification(db, prc.get_supplier(db, supplier_id), body, principal.user.id)
    db.commit()
    return prc.suppliers_out(db, [row])[0]


@router.post("/suppliers/{supplier_id}/bank-change", response_model=schemas.SupplierOut)
def request_bank_change(
    supplier_id: uuid.UUID,
    body: schemas.BankChangeIn,
    db: DbSession,
    principal: Principal = Depends(require("procurement.supplier_bank.request_change")),
) -> schemas.SupplierOut:
    row = prc.get_supplier(db, supplier_id)
    prc.request_bank_change(db, row, body, principal)
    db.commit()
    return prc.suppliers_out(db, [row])[0]


# --- Purchase requests ---------------------------------------------------------


@router.get("/requests", response_model=schemas.Page[schemas.PurchaseRequestOut])
def list_requests(
    db: DbSession,
    _: Principal = View,
    q: str | None = Query(default=None, max_length=100),
    status: str | None = Query(default=None, max_length=20),
    page: int = Query(default=1, ge=1, le=10_000),
    size: int = Query(default=25, ge=1, le=100),
) -> schemas.Page[schemas.PurchaseRequestOut]:
    return prc.list_requests(db, status=status, q=q.strip() if q else None, page=page, size=size)


@router.post("/requests", response_model=schemas.PurchaseRequestDetail, status_code=201)
def create_request(
    body: schemas.PurchaseRequestIn, db: DbSession, principal: Principal = Edit
) -> schemas.PurchaseRequestDetail:
    row = prc.create_request(db, body, principal.user.id)
    db.commit()
    return prc.request_detail(db, row)


@router.get("/requests/{request_id}", response_model=schemas.PurchaseRequestDetail)
def request_detail(
    request_id: uuid.UUID, db: DbSession, _: Principal = View
) -> schemas.PurchaseRequestDetail:
    return prc.request_detail(db, prc.get_request(db, request_id))


@router.post("/requests/{request_id}/quotes", response_model=schemas.PurchaseRequestDetail)
def add_quote(
    request_id: uuid.UUID, body: schemas.QuoteIn, db: DbSession, principal: Principal = Edit
) -> schemas.PurchaseRequestDetail:
    row = prc.get_request(db, request_id)
    prc.add_quote(db, row, body, principal.user.id)
    db.commit()
    return prc.request_detail(db, row)


@router.post("/requests/{request_id}/submit", response_model=schemas.PurchaseRequestDetail)
def submit_for_approval(
    request_id: uuid.UUID,
    body: schemas.SubmitForApprovalIn,
    db: DbSession,
    principal: Principal = Edit,
) -> schemas.PurchaseRequestDetail:
    row = prc.submit_for_approval(db, prc.get_request(db, request_id), body, principal)
    db.commit()
    return prc.request_detail(db, row)


@router.post("/requests/{request_id}/cancel", response_model=schemas.PurchaseRequestDetail)
def cancel_request(
    request_id: uuid.UUID, body: schemas.CancelIn, db: DbSession, principal: Principal = Edit
) -> schemas.PurchaseRequestDetail:
    row = prc.get_request(db, request_id)
    prc.cancel_request(db, row, body.reason, principal.user.id)
    db.commit()
    return prc.request_detail(db, row)


@router.post("/requests/{request_id}/order", response_model=schemas.PurchaseOrderOut)
def issue_order(
    request_id: uuid.UUID, body: schemas.IssueOrderIn, db: DbSession, principal: Principal = Edit
) -> schemas.PurchaseOrderOut:
    order = prc.issue_order(db, prc.get_request(db, request_id), body, principal.user.id)
    db.commit()
    return prc.orders_out(db, [order])[0]


# --- Purchase orders -------------------------------------------------------------


@router.get("/orders", response_model=list[schemas.PurchaseOrderOut])
def list_orders(
    db: DbSession,
    _: Principal = View,
    status: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[schemas.PurchaseOrderOut]:
    stmt = select(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(PurchaseOrder.status == status)
    return prc.orders_out(db, list(db.execute(stmt).scalars()))


@router.get("/orders/{order_id}", response_model=schemas.PurchaseOrderOut)
def get_order(order_id: uuid.UUID, db: DbSession, _: Principal = View) -> schemas.PurchaseOrderOut:
    return prc.orders_out(db, [prc.get_order(db, order_id)])[0]


@router.post("/orders/{order_id}/cancel", response_model=schemas.PurchaseOrderOut)
def cancel_order(
    order_id: uuid.UUID, body: schemas.CancelIn, db: DbSession, principal: Principal = Edit
) -> schemas.PurchaseOrderOut:
    order = prc.cancel_order(db, prc.get_order(db, order_id), body.reason, principal.user.id)
    db.commit()
    return prc.orders_out(db, [order])[0]


# --- Landed cost -------------------------------------------------------------------


@router.post("/landed-cost", response_model=schemas.LandedCostOut)
def estimate_landed_cost(
    body: schemas.LandedCostIn, db: DbSession, _: Principal = View
) -> schemas.LandedCostOut:
    currency = (
        db.execute(select(OrganisationProfile.functional_currency).limit(1)).scalar() or "MWK"
    )
    result = landed_cost.calculate(
        landed_cost.LandedCostInput(
            goods_value=body.goods_value,
            freight=body.freight,
            insurance=body.insurance,
            exchange_rate=body.exchange_rate,
            duty_rate_pct=body.duty_rate_pct,
            excise_rate_pct=body.excise_rate_pct,
            vat_rate_pct=body.vat_rate_pct,
            vat_recoverable=body.vat_recoverable,
            local_charges=body.local_charges,
            quantity=body.quantity,
        )
    )
    return schemas.LandedCostOut(
        functional_currency=currency,
        customs_value=result.customs_value,
        duty=result.duty,
        excise=result.excise,
        vat=result.vat,
        local_charges=result.local_charges,
        landed_cost=result.landed_cost,
        unit_cost=result.unit_cost,
        vat_included_in_cost=result.vat_included_in_cost,
        exchange_rate=body.exchange_rate,
        exchange_rate_source=body.exchange_rate_source,
        note=(
            "Estimate only. Rates and the exchange rate were entered by you; confirm them "
            "with your clearing agent and the current revenue-authority tariff."
        ),
    )
