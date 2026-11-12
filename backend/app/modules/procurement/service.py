"""Procurement rules: supplier verification, dual-controlled bank details,
purchase requests, quotation comparison, approval and purchase orders."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.modules.tenders.models import Tender
from app.platform.approvals import service as approvals
from app.platform.approvals.models import ApprovalRequest
from app.platform.audit import service as audit
from app.platform.authz.deps import Principal
from app.platform.files.models import StoredFile
from app.platform.identity.models import User
from app.platform.references import next_reference
from app.platform.security import crypto

from . import schemas
from .models import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequest,
    PurchaseRequestLine,
    Supplier,
    SupplierBankAccount,
    SupplierQuote,
    SupplierQuoteLine,
)

CENT = Decimal("0.01")
BANK_SUBJECT = "supplier_bank_change"
PR_SUBJECT = "purchase_request"


class ProcurementRuleError(AppError):
    status_code = 422
    code = "validation_error"


def now() -> datetime:
    return datetime.now(UTC)


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _names(db: Session, ids: set[uuid.UUID | None]) -> dict[uuid.UUID, str]:
    wanted = {i for i in ids if i}
    if not wanted:
        return {}
    return dict(
        db.execute(select(User.id, User.display_name).where(User.id.in_(wanted))).tuples().all()
    )


def _ref(db: Session, ids: set[uuid.UUID | None]) -> dict[uuid.UUID, schemas.UserRef]:
    return {k: schemas.UserRef(id=k, display_name=v) for k, v in _names(db, ids).items()}


def _audit(
    db: Session, action: str, actor: uuid.UUID, kind: str, target: Any, **details: Any
) -> None:
    audit.record(
        db,
        action=f"procurement.{action}",
        actor_id=actor,
        target_type=kind,
        target_id=target,
        details=details,
    )


# --- Suppliers ---------------------------------------------------------------


def get_supplier(db: Session, supplier_id: uuid.UUID) -> Supplier:
    row = db.get(Supplier, supplier_id)
    if row is None:
        raise NotFoundError("Supplier not found.")
    return row


def suppliers_out(db: Session, rows: list[Supplier]) -> list[schemas.SupplierOut]:
    if not rows:
        return []
    ids = [r.id for r in rows]
    bank = db.execute(
        select(SupplierBankAccount.supplier_id, SupplierBankAccount.status).where(
            SupplierBankAccount.supplier_id.in_(ids),
            SupplierBankAccount.status.in_(("active", "pending")),
        )
    ).all()
    active = {s for s, st in bank if st == "active"}
    pending = {s for s, st in bank if st == "pending"}
    users = _ref(db, {r.verified_by for r in rows})
    return [
        schemas.SupplierOut(
            id=r.id,
            reference=r.reference,
            name=r.name,
            country_code=r.country_code,
            city=r.city,
            categories=r.categories,
            contact_name=r.contact_name,
            email=r.email,
            phone=r.phone,
            registration_number=r.registration_number,
            tax_number=r.tax_number,
            status=r.status,
            verified_by=users.get(r.verified_by) if r.verified_by else None,
            verified_at=r.verified_at,
            verification_note=r.verification_note,
            notes=r.notes,
            created_at=r.created_at,
            has_active_bank_account=r.id in active,
            pending_bank_change=r.id in pending,
        )
        for r in rows
    ]


def list_suppliers(
    db: Session, *, q: str | None, status: str | None, page: int, size: int
) -> schemas.Page[schemas.SupplierOut]:
    stmt: Select[Any] = select(Supplier)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Supplier.name).like(like),
                func.lower(Supplier.reference).like(like),
                func.lower(func.coalesce(Supplier.categories, "")).like(like),
                func.lower(func.coalesce(Supplier.city, "")).like(like),
            )
        )
    if status:
        stmt = stmt.where(Supplier.status == status)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(func.lower(Supplier.name), Supplier.id)
            .offset((page - 1) * size)
            .limit(size)
        ).scalars()
    )
    return schemas.Page[schemas.SupplierOut](
        items=suppliers_out(db, rows), total=total, page=page, size=size
    )


def create_supplier(db: Session, body: schemas.SupplierIn, actor: uuid.UUID) -> Supplier:
    dup = db.execute(
        select(Supplier.reference).where(func.lower(Supplier.name) == body.name.lower())
    ).scalar_one_or_none()
    if dup:
        raise ConflictError(f"A supplier with this name already exists ({dup}).")
    row = Supplier(reference=next_reference(db, "SUP"), created_by=actor, **body.model_dump())
    db.add(row)
    db.flush()
    _audit(db, "supplier.created", actor, "supplier", row.id, reference=row.reference)
    return row


def update_supplier(
    db: Session, row: Supplier, body: schemas.SupplierPatch, actor: uuid.UUID
) -> Supplier:
    changes = body.model_dump(exclude_unset=True)
    if "name" in changes and not changes["name"]:
        raise ProcurementRuleError("Name cannot be empty.")
    changed = {k: v for k, v in changes.items() if getattr(row, k) != v}
    for key, value in changed.items():
        setattr(row, key, value)
    if changed:
        _audit(db, "supplier.updated", actor, "supplier", row.id, fields=sorted(changed))
    return row


def set_verification(
    db: Session, row: Supplier, body: schemas.VerificationIn, actor: uuid.UUID
) -> Supplier:
    row.status = body.status
    row.verification_note = body.note
    row.verified_by = actor if body.status == "verified" else None
    row.verified_at = now() if body.status == "verified" else None
    _audit(db, f"supplier.{body.status}", actor, "supplier", row.id)
    return row


def bank_accounts(
    db: Session, supplier: Supplier, principal: Principal
) -> tuple[list[schemas.BankAccountMasked | schemas.BankAccountFull], bool]:
    rows = list(
        db.execute(
            select(SupplierBankAccount)
            .where(SupplierBankAccount.supplier_id == supplier.id)
            .order_by(SupplierBankAccount.created_at.desc())
        ).scalars()
    )
    full = principal.has("procurement.supplier_bank.view")
    names = _names(db, {r.requested_by for r in rows})
    out: list[schemas.BankAccountMasked | schemas.BankAccountFull] = []
    for r in rows:
        base = {
            "id": r.id,
            "bank_name": r.bank_name,
            "account_last4": r.account_last4,
            "currency": r.currency,
            "status": r.status,
            "reason": r.reason,
            "requested_by": names.get(r.requested_by, ""),
            "created_at": r.created_at,
        }
        if full:
            out.append(
                schemas.BankAccountFull(
                    **base,
                    account_name=crypto.decrypt(r.account_name_encrypted),
                    account_number=crypto.decrypt(r.account_number_encrypted),
                    branch=crypto.decrypt(r.branch_encrypted) if r.branch_encrypted else None,
                    swift=crypto.decrypt(r.swift_encrypted) if r.swift_encrypted else None,
                )
            )
        else:
            out.append(schemas.BankAccountMasked(**base))
    if full and rows:
        _audit(db, "supplier_bank.viewed", principal.user.id, "supplier", supplier.id)
        db.commit()
    return out, full


def request_bank_change(
    db: Session, supplier: Supplier, body: schemas.BankChangeIn, principal: Principal
) -> SupplierBankAccount:
    pending = db.execute(
        select(SupplierBankAccount.id).where(
            SupplierBankAccount.supplier_id == supplier.id, SupplierBankAccount.status == "pending"
        )
    ).first()
    if pending:
        raise ConflictError("A bank-detail change is already waiting for approval.")
    number = body.account_number.replace(" ", "")
    account = SupplierBankAccount(
        supplier_id=supplier.id,
        bank_name=body.bank_name,
        account_name_encrypted=crypto.encrypt(body.account_name),
        account_number_encrypted=crypto.encrypt(number),
        branch_encrypted=crypto.encrypt(body.branch) if body.branch else None,
        swift_encrypted=crypto.encrypt(body.swift) if body.swift else None,
        account_last4=number[-4:],
        currency=body.currency,
        status="pending",
        requested_by=principal.user.id,
        reason=body.reason,
    )
    db.add(account)
    db.flush()
    req = approvals.create_request(
        db,
        principal=principal,
        subject_type=BANK_SUBJECT,
        subject_id=str(account.id),
        permission_required="procurement.supplier_bank.approve_change",
        summary=f"Change bank details for {supplier.reference} {supplier.name} "
        f"(account ending {account.account_last4})",
        # Masked only: approvals are listed to deciders; full details sit on the supplier page.
        payload={"supplier": supplier.reference, "bank": body.bank_name, "ending": number[-4:]},
    )
    account.approval_id = req.id
    _audit(
        db,
        "supplier_bank.change_requested",
        principal.user.id,
        "supplier",
        supplier.id,
        ending=number[-4:],
    )
    audit.raise_alert(
        db,
        kind="supplier_bank_change",
        severity="warning",
        message=f"Bank-detail change requested for supplier {supplier.reference}.",
        subject_user_id=principal.user.id,
    )
    return account


def _apply_bank_decision(db: Session, request: ApprovalRequest) -> None:
    account = db.get(SupplierBankAccount, uuid.UUID(request.subject_id))
    if account is None or account.status != "pending":
        raise ConflictError("This bank-detail change is no longer pending.")
    if request.status == "approved":
        for old in db.execute(
            select(SupplierBankAccount).where(
                SupplierBankAccount.supplier_id == account.supplier_id,
                SupplierBankAccount.status == "active",
            )
        ).scalars():
            old.status = "superseded"
        db.flush()
        account.status = "active"
    else:
        account.status = "rejected"


approvals.register_handler(BANK_SUBJECT, _apply_bank_decision)


# --- Purchase requests and quotations -----------------------------------------


def get_request(db: Session, request_id: uuid.UUID) -> PurchaseRequest:
    row = db.get(PurchaseRequest, request_id)
    if row is None:
        raise NotFoundError("Purchase request not found.")
    return row


def _lines(db: Session, request_id: uuid.UUID) -> list[PurchaseRequestLine]:
    return list(
        db.execute(
            select(PurchaseRequestLine)
            .where(PurchaseRequestLine.request_id == request_id)
            .order_by(PurchaseRequestLine.line_no)
        ).scalars()
    )


def requests_out(db: Session, rows: list[PurchaseRequest]) -> list[schemas.PurchaseRequestOut]:
    if not rows:
        return []
    users = _ref(db, {r.requested_by for r in rows})
    orders = dict(
        db.execute(
            select(PurchaseOrder.request_id, PurchaseOrder.id).where(
                PurchaseOrder.request_id.in_([r.id for r in rows])
            )
        )
        .tuples()
        .all()
    )
    return [
        schemas.PurchaseRequestOut(
            id=r.id,
            reference=r.reference,
            title=r.title,
            justification=r.justification,
            division=r.division,
            needed_by=r.needed_by,
            currency=r.currency,
            status=r.status,
            selected_quote_id=r.selected_quote_id,
            approval_id=r.approval_id,
            tender_id=r.tender_id,
            requested_by=users.get(r.requested_by),
            created_at=r.created_at,
            order_id=orders.get(r.id),
        )
        for r in rows
    ]


def quotes_for(
    db: Session, request: PurchaseRequest, lines: list[PurchaseRequestLine]
) -> list[schemas.QuoteOut]:
    quotes = list(
        db.execute(
            select(SupplierQuote, Supplier.name, Supplier.status)
            .join(Supplier, Supplier.id == SupplierQuote.supplier_id)
            .where(SupplierQuote.request_id == request.id)
            .order_by(SupplierQuote.created_at)
        ).all()
    )
    if not quotes:
        return []
    prices: dict[uuid.UUID, dict[uuid.UUID, Decimal]] = {}
    for ql in db.execute(
        select(SupplierQuoteLine).where(
            SupplierQuoteLine.quote_id.in_([q.id for q, _, _ in quotes])
        )
    ).scalars():
        prices.setdefault(ql.quote_id, {})[ql.request_line_id] = ql.unit_price
    qty = {line.id: line.quantity for line in lines}
    today = date.today()
    out = []
    for q, name, status in quotes:
        p = prices.get(q.id, {})
        total = _money(sum((qty[k] * v for k, v in p.items() if k in qty), Decimal(0)))
        out.append(
            schemas.QuoteOut(
                id=q.id,
                supplier_id=q.supplier_id,
                supplier_name=name,
                supplier_status=status,
                supplier_reference=q.supplier_reference,
                currency=q.currency,
                valid_until=q.valid_until,
                lead_time_days=q.lead_time_days,
                delivery_terms=q.delivery_terms,
                notes=q.notes,
                total=total,
                complete=set(qty) <= set(p),
                expired=bool(q.valid_until and q.valid_until < today),
                prices={str(k): v for k, v in p.items()},
            )
        )
    return out


def request_detail(db: Session, row: PurchaseRequest) -> schemas.PurchaseRequestDetail:
    lines = _lines(db, row.id)
    quotes = quotes_for(db, row, lines)
    eligible = [
        q
        for q in quotes
        if q.complete
        and not q.expired
        and q.currency == row.currency
        and q.supplier_status != "suspended"
    ]
    cheapest = min(eligible, key=lambda q: q.total).id if eligible else None
    others = sum(1 for q in quotes if q.currency != row.currency)
    note = f"Compared in {row.currency} only." + (
        f" {others} quotation(s) in another currency are listed but not ranked:"
        " no exchange rate is assumed."
        if others
        else ""
    )
    return schemas.PurchaseRequestDetail(
        request=requests_out(db, [row])[0],
        lines=[
            schemas.LineOut(
                id=line.id,
                line_no=line.line_no,
                description=line.description,
                quantity=line.quantity,
                unit=line.unit,
            )
            for line in lines
        ],
        quotes=quotes,
        cheapest_complete_quote_id=cheapest,
        comparison_note=note,
    )


def list_requests(
    db: Session, *, status: str | None, q: str | None, page: int, size: int
) -> schemas.Page[schemas.PurchaseRequestOut]:
    stmt: Select[Any] = select(PurchaseRequest)
    if status:
        stmt = stmt.where(PurchaseRequest.status == status)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(PurchaseRequest.title).like(like),
                func.lower(PurchaseRequest.reference).like(like),
            )
        )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(PurchaseRequest.created_at.desc()).offset((page - 1) * size).limit(size)
        ).scalars()
    )
    return schemas.Page[schemas.PurchaseRequestOut](
        items=requests_out(db, rows), total=total, page=page, size=size
    )


def create_request(
    db: Session, body: schemas.PurchaseRequestIn, actor: uuid.UUID
) -> PurchaseRequest:
    if body.tender_id and db.get(Tender, body.tender_id) is None:
        raise ProcurementRuleError("The linked tender does not exist.")
    data = body.model_dump(exclude={"lines"})
    row = PurchaseRequest(reference=next_reference(db, "PR"), requested_by=actor, **data)
    db.add(row)
    db.flush()
    for n, line in enumerate(body.lines, start=1):
        db.add(PurchaseRequestLine(request_id=row.id, line_no=n, **line.model_dump()))
    db.flush()
    _audit(db, "request.created", actor, "purchase_request", row.id, reference=row.reference)
    return row


def add_quote(
    db: Session, request: PurchaseRequest, body: schemas.QuoteIn, actor: uuid.UUID
) -> SupplierQuote:
    if request.status != "draft":
        raise ConflictError("Quotations can only be added while the request is a draft.")
    supplier = get_supplier(db, body.supplier_id)
    if supplier.status == "suspended":
        raise ConflictError("This supplier is suspended.")
    line_ids = {line.id for line in _lines(db, request.id)}
    priced = [line.request_line_id for line in body.lines]
    if len(priced) != len(set(priced)) or not set(priced) <= line_ids:
        raise ProcurementRuleError("Each price must refer to a different line of this request.")
    if body.file_id:
        f = db.get(StoredFile, body.file_id)
        if f is None or f.module != "procurement":
            raise ProcurementRuleError("Attach a document uploaded to the Procurement section.")
    quote = SupplierQuote(
        request_id=request.id, created_by=actor, **body.model_dump(exclude={"lines"})
    )
    db.add(quote)
    db.flush()
    for line in body.lines:
        db.add(SupplierQuoteLine(quote_id=quote.id, **line.model_dump()))
    db.flush()
    _audit(db, "quote.added", actor, "purchase_request", request.id, supplier=supplier.reference)
    return quote


def submit_for_approval(
    db: Session, request: PurchaseRequest, body: schemas.SubmitForApprovalIn, principal: Principal
) -> PurchaseRequest:
    if request.status != "draft":
        raise ConflictError("Only a draft request can be sent for approval.")
    detail = request_detail(db, request)
    quote = next((q for q in detail.quotes if q.id == body.quote_id), None)
    if quote is None:
        raise ProcurementRuleError("Choose one of this request's quotations.")
    if not quote.complete:
        raise ConflictError("The chosen quotation does not price every line.")
    if quote.expired:
        raise ConflictError("The chosen quotation has expired.")
    if quote.supplier_status != "verified":
        raise ConflictError("The supplier must be verified before an order can be approved.")
    if quote.currency != request.currency:
        raise ConflictError("The quotation currency differs from the request currency.")
    reason = None
    if detail.cheapest_complete_quote_id and detail.cheapest_complete_quote_id != quote.id:
        reason = body.note
        if not reason:
            raise ProcurementRuleError("Explain why the cheapest valid quotation was not chosen.")
    req = approvals.create_request(
        db,
        principal=principal,
        subject_type=PR_SUBJECT,
        subject_id=str(request.id),
        permission_required="procurement.order.approve",
        summary=f"Purchase {request.reference}: {request.title} from {quote.supplier_name} "
        f"for {quote.currency} {quote.total:,.2f}",
        payload={
            "reference": request.reference,
            "supplier": quote.supplier_name,
            "currency": quote.currency,
            "total": str(quote.total),
            "quotes_received": len(detail.quotes),
            "not_cheapest_reason": reason,
            "note": body.note,
        },
    )
    request.selected_quote_id = quote.id
    request.approval_id = req.id
    request.status = "awaiting_approval"
    _audit(db, "request.submitted", principal.user.id, "purchase_request", request.id)
    return request


def _apply_request_decision(db: Session, approval: ApprovalRequest) -> None:
    row = db.get(PurchaseRequest, uuid.UUID(approval.subject_id))
    if row is None or row.approval_id != approval.id or row.status != "awaiting_approval":
        raise ConflictError("The purchase request is no longer waiting for this approval.")
    row.status = "approved" if approval.status == "approved" else "draft"


approvals.register_handler(PR_SUBJECT, _apply_request_decision)


def cancel_request(db: Session, row: PurchaseRequest, reason: str, actor: uuid.UUID) -> None:
    if row.status not in ("draft", "approved"):
        raise ConflictError("Only a draft or approved (not yet ordered) request can be cancelled.")
    row.status = "cancelled"
    row.justification = f"{row.justification or ''}\n\nCancelled: {reason}".strip()
    _audit(db, "request.cancelled", actor, "purchase_request", row.id)


# --- Purchase orders -----------------------------------------------------------


def issue_order(
    db: Session, request: PurchaseRequest, body: schemas.IssueOrderIn, actor: uuid.UUID
) -> PurchaseOrder:
    if request.status != "approved" or request.selected_quote_id is None:
        raise ConflictError("An order can be issued only from an approved purchase request.")
    quote = db.get_one(SupplierQuote, request.selected_quote_id)
    supplier = get_supplier(db, quote.supplier_id)
    if supplier.status != "verified":
        raise ConflictError("The supplier is no longer verified.")
    prices = {
        ql.request_line_id: ql.unit_price
        for ql in db.execute(
            select(SupplierQuoteLine).where(SupplierQuoteLine.quote_id == quote.id)
        ).scalars()
    }
    order = PurchaseOrder(
        reference=next_reference(db, "PO"),
        request_id=request.id,
        quote_id=quote.id,
        supplier_id=supplier.id,
        currency=quote.currency,
        total_amount=Decimal(0),
        delivery_address=body.delivery_address,
        expected_delivery=body.expected_delivery,
        issued_by=actor,
    )
    db.add(order)
    db.flush()
    total = Decimal(0)
    for line in _lines(db, request.id):
        line_total = _money(line.quantity * prices[line.id])
        total += line_total
        db.add(
            PurchaseOrderLine(
                order_id=order.id,
                line_no=line.line_no,
                description=line.description,
                quantity=line.quantity,
                unit=line.unit,
                unit_price=prices[line.id],
                line_total=line_total,
            )
        )
    order.total_amount = total
    request.status = "ordered"
    _audit(db, "order.issued", actor, "purchase_order", order.id, reference=order.reference)
    return order


def orders_out(db: Session, rows: list[PurchaseOrder]) -> list[schemas.PurchaseOrderOut]:
    if not rows:
        return []
    ids = [r.id for r in rows]
    lines: dict[uuid.UUID, list[schemas.OrderLineOut]] = {}
    for line in db.execute(
        select(PurchaseOrderLine)
        .where(PurchaseOrderLine.order_id.in_(ids))
        .order_by(PurchaseOrderLine.line_no)
    ).scalars():
        lines.setdefault(line.order_id, []).append(
            schemas.OrderLineOut(
                line_no=line.line_no,
                description=line.description,
                quantity=line.quantity,
                unit=line.unit,
                unit_price=line.unit_price,
                line_total=line.line_total,
                received_quantity=line.received_quantity,
            )
        )
    suppliers = dict(
        db.execute(
            select(Supplier.id, Supplier.name).where(Supplier.id.in_({r.supplier_id for r in rows}))
        )
        .tuples()
        .all()
    )
    refs = dict(
        db.execute(
            select(PurchaseRequest.id, PurchaseRequest.reference).where(
                PurchaseRequest.id.in_({r.request_id for r in rows})
            )
        )
        .tuples()
        .all()
    )
    users = _ref(db, {r.issued_by for r in rows})
    return [
        schemas.PurchaseOrderOut(
            id=r.id,
            reference=r.reference,
            request_id=r.request_id,
            request_reference=refs.get(r.request_id, ""),
            supplier_id=r.supplier_id,
            supplier_name=suppliers.get(r.supplier_id, ""),
            currency=r.currency,
            total_amount=r.total_amount,
            status=r.status,
            delivery_address=r.delivery_address,
            expected_delivery=r.expected_delivery,
            cancel_reason=r.cancel_reason,
            issued_by=users.get(r.issued_by),
            created_at=r.created_at,
            lines=lines.get(r.id, []),
        )
        for r in rows
    ]


def get_order(db: Session, order_id: uuid.UUID) -> PurchaseOrder:
    row = db.get(PurchaseOrder, order_id)
    if row is None:
        raise NotFoundError("Purchase order not found.")
    return row


def cancel_order(db: Session, row: PurchaseOrder, reason: str, actor: uuid.UUID) -> PurchaseOrder:
    if row.status != "issued":
        raise ConflictError("Only an issued order with nothing received can be cancelled.")
    received = db.execute(
        select(func.coalesce(func.sum(PurchaseOrderLine.received_quantity), 0)).where(
            PurchaseOrderLine.order_id == row.id
        )
    ).scalar_one()
    if received:
        raise ConflictError("Goods have been received against this order.")
    row.status = "cancelled"
    row.cancel_reason = reason
    _audit(db, "order.cancelled", actor, "purchase_order", row.id)
    return row
