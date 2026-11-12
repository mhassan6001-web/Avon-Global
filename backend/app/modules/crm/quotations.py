"""Quotations (Stage 16): priced offers built from validated records.

Draft → (approval, when the limit applies) → issued → accepted / declined.
A quotation gets its gap-free number (``QUO-YYYY-NNNNN``) only when issued,
and is frozen from then on. Tax comes from Finance's configured tax codes;
no rate is built in.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.modules.finance import posting
from app.modules.finance.models import TaxCode
from app.platform.approvals import service as approvals
from app.platform.approvals.models import ApprovalRequest
from app.platform.audit import service as audit
from app.platform.authz.deps import DbSession, Principal, require
from app.platform.identity.models import User

from .models import Customer, Opportunity, Quotation, QuotationLine

router = APIRouter(prefix="/crm/quotations", tags=["crm"])
View = Depends(require("crm.records.view"))
Edit = Depends(require("crm.records.edit"))
APPROVE = "crm.quotation.approve"
SUBJECT = "crm_quotation"
RULE = "crm_quotation"
Currency = Literal["MWK", "USD", "ZAR", "ZMW"]


class QuotationRuleError(AppError):
    status_code = 422
    code = "quotation_rule"


# --- schemas -------------------------------------------------------------------------


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LineIn(_In):
    description: str = Field(min_length=2, max_length=300)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=3)
    unit: str = Field(default="each", min_length=1, max_length=20)
    unit_price: Decimal = Field(ge=0, max_digits=18, decimal_places=4)
    tax_code_id: uuid.UUID | None = None


class QuotationIn(_In):
    customer_id: uuid.UUID
    opportunity_id: uuid.UUID | None = None
    title: str = Field(min_length=2, max_length=200)
    currency: Currency = "MWK"
    quote_date: date
    valid_until: date
    terms: str | None = Field(default=None, max_length=5000)
    notes: str | None = Field(default=None, max_length=5000)
    lines: list[LineIn] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def _dates(self) -> QuotationIn:
        if self.valid_until < self.quote_date:
            raise ValueError("The validity date cannot be before the quotation date.")
        return self


class OutcomeIn(_In):
    status: Literal["accepted", "declined", "cancelled"]
    note: str | None = Field(default=None, max_length=2000)


class LineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    line_no: int
    description: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    tax_code_id: uuid.UUID | None
    net: Decimal
    tax: Decimal


class QuotationOut(BaseModel):
    id: uuid.UUID
    number: str | None
    customer_id: uuid.UUID
    customer_name: str
    opportunity_id: uuid.UUID | None
    title: str
    currency: str
    quote_date: date
    valid_until: date
    status: str
    expired: bool
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    terms: str | None
    notes: str | None
    approval_id: uuid.UUID | None
    issued_by: str | None
    issued_at: datetime | None
    created_by: str
    lines: list[LineOut]


class TaxCodeOption(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    rate_pct: Decimal


# --- service -------------------------------------------------------------------------


def _today() -> date:
    return posting.now().date()


def get(db: Session, quotation_id: uuid.UUID, lock: bool = False) -> Quotation:
    row = db.get(Quotation, quotation_id, with_for_update=lock)
    if row is None:
        raise NotFoundError("Quotation not found.")
    return row


def _lines(db: Session, row: Quotation) -> list[QuotationLine]:
    return list(
        db.execute(
            select(QuotationLine)
            .where(QuotationLine.quotation_id == row.id)
            .order_by(QuotationLine.line_no)
        ).scalars()
    )


def out(db: Session, rows: list[Quotation]) -> list[QuotationOut]:
    if not rows:
        return []
    customers = dict(
        db.execute(
            select(Customer.id, Customer.name).where(Customer.id.in_({r.customer_id for r in rows}))
        )
        .tuples()
        .all()
    )
    user_ids = {r.created_by for r in rows} | {r.issued_by for r in rows if r.issued_by}
    users = dict(
        db.execute(select(User.id, User.display_name).where(User.id.in_(user_ids))).tuples().all()
    )
    today = _today()
    return [
        QuotationOut(
            id=r.id,
            number=r.number,
            customer_id=r.customer_id,
            customer_name=customers.get(r.customer_id, ""),
            opportunity_id=r.opportunity_id,
            title=r.title,
            currency=r.currency,
            quote_date=r.quote_date,
            valid_until=r.valid_until,
            status=r.status,
            expired=r.status == "issued" and r.valid_until < today,
            subtotal=r.subtotal,
            tax_total=r.tax_total,
            total=r.total,
            terms=r.terms,
            notes=r.notes,
            approval_id=r.approval_id,
            issued_by=users.get(r.issued_by) if r.issued_by else None,
            issued_at=r.issued_at,
            created_by=users.get(r.created_by, ""),
            lines=[LineOut.model_validate(x) for x in _lines(db, r)],
        )
        for r in rows
    ]


def _tax_code(db: Session, tax_code_id: uuid.UUID | None, on: date) -> TaxCode | None:
    if tax_code_id is None:
        return None
    code = db.get(TaxCode, tax_code_id)
    if code is None or code.kind != "output":
        raise QuotationRuleError("Choose a sales (output) tax code set up by Finance.")
    if code.effective_from > on or (code.effective_to and code.effective_to < on):
        raise QuotationRuleError(f"Tax code {code.code} is not in effect on {on.isoformat()}.")
    return code


def _apply(db: Session, row: Quotation, body: QuotationIn) -> None:
    customer = db.get(Customer, body.customer_id)
    if customer is None or customer.status == "archived":
        raise QuotationRuleError("Choose an active customer.")
    if body.opportunity_id is not None:
        opp = db.get(Opportunity, body.opportunity_id)
        if opp is None or opp.customer_id != body.customer_id:
            raise QuotationRuleError("That opportunity does not belong to this customer.")
    for name in ("customer_id", "opportunity_id", "title", "currency", "quote_date",
                 "valid_until", "terms", "notes"):  # fmt: skip
        setattr(row, name, getattr(body, name))
    db.flush()
    for old in _lines(db, row):
        db.delete(old)
    db.flush()
    subtotal = tax_total = Decimal(0)
    for i, line in enumerate(body.lines, start=1):
        code = _tax_code(db, line.tax_code_id, body.quote_date)
        net = posting.money(line.quantity * line.unit_price)
        tax = posting.money(net * code.rate_pct / 100) if code else Decimal(0)
        subtotal += net
        tax_total += tax
        db.add(QuotationLine(quotation_id=row.id, line_no=i, net=net, tax=tax, **line.model_dump()))
    row.subtotal, row.tax_total, row.total = subtotal, tax_total, subtotal + tax_total
    db.flush()


def create(db: Session, body: QuotationIn, principal: Principal) -> Quotation:
    row = Quotation(
        customer_id=body.customer_id,
        title=body.title,
        quote_date=body.quote_date,
        valid_until=body.valid_until,
        created_by=principal.user.id,
    )
    db.add(row)
    db.flush()
    _apply(db, row, body)
    audit.record(
        db,
        action="crm.quotation.created",
        actor_id=principal.user.id,
        target_type="crm_quotation",
        target_id=row.id,
        details={"customer_id": str(row.customer_id), "total": str(row.total)},
    )
    return row


def update(db: Session, row: Quotation, body: QuotationIn, principal: Principal) -> Quotation:
    if row.status != "draft":
        raise ConflictError("Only a draft quotation can be changed.")
    _apply(db, row, body)
    audit.record(
        db,
        action="crm.quotation.updated",
        actor_id=principal.user.id,
        target_type="crm_quotation",
        target_id=row.id,
        details={"total": str(row.total)},
    )
    return row


def _functional_total(db: Session, row: Quotation) -> Decimal | None:
    """Total in the functional currency, or ``None`` when no rate is recorded."""
    try:
        return posting.money(row.total * posting.rate_for(db, row.currency, row.quote_date))
    except posting.FinanceRuleError:
        return None


def _issue(db: Session, row: Quotation, issued_by: uuid.UUID) -> None:
    row.number = posting.next_number(db, "QUO", row.quote_date)
    row.status = "issued"
    row.issued_by = issued_by
    row.issued_at = posting.now()
    audit.record(
        db,
        action="crm.quotation.issued",
        actor_id=issued_by,
        target_type="crm_quotation",
        target_id=row.id,
        details={"number": row.number, "total": str(row.total), "currency": row.currency},
    )


def issue(db: Session, row: Quotation, principal: Principal) -> Quotation:
    """Issue directly, or send for approval when the configured limit applies."""
    if row.status != "draft":
        raise ConflictError("Only a draft quotation can be issued.")
    if row.valid_until < _today():
        raise QuotationRuleError("The validity date has passed. Update it before issuing.")
    needs = approvals.needs_approval(db, RULE, _functional_total(db, row))
    if needs and not principal.has(APPROVE):
        req = approvals.create_request(
            db,
            principal=principal,
            subject_type=SUBJECT,
            subject_id=str(row.id),
            permission_required=APPROVE,
            summary=f"Issue quotation “{row.title}” for {row.currency} {row.total:,.2f}",
            payload={"title": row.title, "total": str(row.total), "currency": row.currency},
        )
        row.approval_id = req.id
        row.status = "awaiting_approval"
        return row
    _issue(db, row, principal.user.id)
    return row


def _apply_decision(db: Session, request: ApprovalRequest) -> None:
    row = get(db, uuid.UUID(request.subject_id), lock=True)
    if row.status != "awaiting_approval":
        raise ConflictError("This quotation is no longer waiting for approval.")
    if request.status == "approved":
        _issue(db, row, request.requested_by)
    else:
        row.status = "draft"


approvals.register_handler(SUBJECT, _apply_decision)


def set_outcome(db: Session, row: Quotation, body: OutcomeIn, principal: Principal) -> Quotation:
    allowed = {
        "accepted": ("issued",),
        "declined": ("issued",),
        "cancelled": ("draft", "issued"),
    }[body.status]
    if row.status not in allowed:
        raise ConflictError(
            f"A quotation that is {row.status.replace('_', ' ')} cannot be {body.status}."
        )
    if body.status == "accepted" and row.valid_until < _today():
        raise QuotationRuleError("This quotation has expired. Issue a new one.")
    row.status = body.status
    audit.record(
        db,
        action=f"crm.quotation.{body.status}",
        actor_id=principal.user.id,
        target_type="crm_quotation",
        target_id=row.id,
        details={"number": row.number, "note": body.note},
    )
    return row


# --- API -----------------------------------------------------------------------------


@router.get("/tax-codes", response_model=list[TaxCodeOption])
def tax_codes(db: DbSession, _: Principal = View) -> list[TaxCodeOption]:
    """Sales tax codes in effect today, as configured by Finance (none are built in)."""
    today = _today()
    rows = db.execute(
        select(TaxCode)
        .where(TaxCode.kind == "output", TaxCode.effective_from <= today)
        .order_by(TaxCode.code)
    ).scalars()
    return [
        TaxCodeOption(id=t.id, code=t.code, name=t.name, rate_pct=t.rate_pct)
        for t in rows
        if t.effective_to is None or t.effective_to >= today
    ]


@router.get("", response_model=list[QuotationOut])
def list_quotations(
    db: DbSession,
    _: Principal = View,
    customer_id: uuid.UUID | None = None,
    status: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[QuotationOut]:
    stmt = select(Quotation).order_by(Quotation.created_at.desc()).limit(limit)
    if customer_id:
        stmt = stmt.where(Quotation.customer_id == customer_id)
    if status:
        stmt = stmt.where(Quotation.status == status)
    return out(db, list(db.execute(stmt).scalars()))


@router.post("", response_model=QuotationOut, status_code=201)
def create_quotation(body: QuotationIn, db: DbSession, principal: Principal = Edit) -> QuotationOut:
    row = create(db, body, principal)
    db.commit()
    return out(db, [row])[0]


@router.get("/{quotation_id}", response_model=QuotationOut)
def get_quotation(quotation_id: uuid.UUID, db: DbSession, _: Principal = View) -> QuotationOut:
    return out(db, [get(db, quotation_id)])[0]


@router.put("/{quotation_id}", response_model=QuotationOut)
def update_quotation(
    quotation_id: uuid.UUID, body: QuotationIn, db: DbSession, principal: Principal = Edit
) -> QuotationOut:
    row = update(db, get(db, quotation_id, lock=True), body, principal)
    db.commit()
    return out(db, [row])[0]


@router.post("/{quotation_id}/issue", response_model=QuotationOut)
def issue_quotation(
    quotation_id: uuid.UUID, db: DbSession, principal: Principal = Edit
) -> QuotationOut:
    row = issue(db, get(db, quotation_id, lock=True), principal)
    db.commit()
    return out(db, [row])[0]


@router.post("/{quotation_id}/outcome", response_model=QuotationOut)
def quotation_outcome(
    quotation_id: uuid.UUID, body: OutcomeIn, db: DbSession, principal: Principal = Edit
) -> QuotationOut:
    row = set_outcome(db, get(db, quotation_id, lock=True), body, principal)
    db.commit()
    return out(db, [row])[0]
