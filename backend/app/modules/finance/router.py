"""Finance API (``/api/v1/finance``). Finance's section; restricted actions need
approval by a different person (the Director) and are never self-approved."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.errors import NotFoundError
from app.modules.crm.models import Customer
from app.modules.procurement.models import Supplier
from app.platform.audit import service as audit
from app.platform.authz.deps import DbSession, Principal, require, require_step_up

from . import posting, reports, schemas
from . import service as fin
from .models import (
    Account,
    BankStatementLine,
    Bill,
    CreditNote,
    ExchangeRate,
    Invoice,
    JournalEntry,
    Payment,
    Period,
    Receipt,
    TaxCode,
)

router = APIRouter(prefix="/finance", tags=["finance"])

View = Depends(require("finance.records.view"))
Edit = Depends(require("finance.records.edit"))
Ledger = Depends(require("finance.ledger.view"))


def _today() -> date:
    return posting.now().date()


# --- Configuration ---------------------------------------------------------------


@router.get("/settings", response_model=schemas.SettingsOut)
def get_settings(db: DbSession, _: Principal = View) -> schemas.SettingsOut:
    out = fin.settings_out(db)
    db.commit()
    return out


@router.put("/settings", response_model=schemas.SettingsOut)
def put_settings(
    body: schemas.SettingsIn, db: DbSession, principal: Principal = Edit
) -> schemas.SettingsOut:
    fin.update_settings(db, body, principal.user.id)
    db.commit()
    return fin.settings_out(db)


class ReviewIn(BaseModel):
    reviewed: bool
    note: str = Field(min_length=3, max_length=2000)


@router.post(
    "/settings/accountant-review",
    response_model=schemas.SettingsOut,
    dependencies=[Depends(require_step_up)],
)
def accountant_review(
    body: ReviewIn,
    db: DbSession,
    principal: Principal = Depends(require("finance.transaction.approve")),
) -> schemas.SettingsOut:
    """Records that a qualified accountant reviewed tax and statutory settings."""
    s = fin.settings_row(db)
    s.accountant_reviewed = body.reviewed
    audit.record(
        db,
        action="finance.accountant_review",
        actor_id=principal.user.id,
        target_type="fin_settings",
        target_id="1",
        details={"reviewed": body.reviewed, "note": body.note},
    )
    db.commit()
    return fin.settings_out(db)


@router.get("/accounts", response_model=list[schemas.AccountOut])
def list_accounts(
    db: DbSession, _: Principal = View, include_inactive: bool = False
) -> list[schemas.AccountOut]:
    stmt = select(Account).order_by(Account.code)
    if not include_inactive:
        stmt = stmt.where(Account.is_active)
    return [schemas.AccountOut.model_validate(a) for a in db.execute(stmt).scalars()]


@router.post("/accounts", response_model=schemas.AccountOut, status_code=201)
def create_account(
    body: schemas.AccountIn, db: DbSession, principal: Principal = Edit
) -> schemas.AccountOut:
    row = fin.create_account(db, body, principal.user.id)
    db.commit()
    return schemas.AccountOut.model_validate(row)


@router.patch("/accounts/{account_id}", response_model=schemas.AccountOut)
def update_account(
    account_id: uuid.UUID, body: schemas.AccountPatch, db: DbSession, principal: Principal = Edit
) -> schemas.AccountOut:
    row = db.get(Account, account_id)
    if row is None:
        raise NotFoundError("Account not found.")
    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(row, key, value)
    audit.record(
        db,
        action="finance.account.updated",
        actor_id=principal.user.id,
        target_type="fin_account",
        target_id=row.id,
        details={"fields": sorted(body.model_fields_set)},
    )
    db.commit()
    return schemas.AccountOut.model_validate(row)


@router.get("/periods", response_model=list[schemas.PeriodOut])
def list_periods(db: DbSession, _: Principal = View) -> list[schemas.PeriodOut]:
    rows = db.execute(select(Period).order_by(Period.start_date.desc())).scalars()
    return [schemas.PeriodOut.model_validate(p) for p in rows]


@router.post("/periods", response_model=schemas.PeriodOut, status_code=201)
def create_period(
    body: schemas.PeriodIn, db: DbSession, principal: Principal = Edit
) -> schemas.PeriodOut:
    row = fin.create_period(db, body, principal.user.id)
    db.commit()
    return schemas.PeriodOut.model_validate(row)


@router.post(
    "/periods/{period_id}/close",
    response_model=schemas.PeriodOut,
    dependencies=[Depends(require_step_up)],
)
def close_period(
    period_id: uuid.UUID,
    db: DbSession,
    principal: Principal = Depends(require("finance.transaction.approve")),
) -> schemas.PeriodOut:
    period = db.get(Period, period_id)
    if period is None:
        raise NotFoundError("Period not found.")
    fin.close_period(db, period, principal.user.id)
    db.commit()
    return schemas.PeriodOut.model_validate(period)


@router.get("/exchange-rates", response_model=list[schemas.RateOut])
def list_rates(
    db: DbSession, _: Principal = View, currency: str | None = Query(default=None, max_length=3)
) -> list[schemas.RateOut]:
    stmt = select(ExchangeRate).order_by(ExchangeRate.rate_date.desc()).limit(200)
    if currency:
        stmt = stmt.where(ExchangeRate.currency == currency)
    return [schemas.RateOut.model_validate(r) for r in db.execute(stmt).scalars()]


@router.post("/exchange-rates", response_model=schemas.RateOut, status_code=201)
def add_rate(body: schemas.RateIn, db: DbSession, principal: Principal = Edit) -> schemas.RateOut:
    row = fin.add_rate(db, body, principal.user.id)
    db.commit()
    return schemas.RateOut.model_validate(row)


@router.get("/tax-codes", response_model=list[schemas.TaxCodeOut])
def list_tax_codes(db: DbSession, _: Principal = View) -> list[schemas.TaxCodeOut]:
    rows = db.execute(select(TaxCode).order_by(TaxCode.code)).scalars()
    return [schemas.TaxCodeOut.model_validate(t) for t in rows]


@router.post("/tax-codes", response_model=schemas.TaxCodeOut, status_code=201)
def create_tax_code(
    body: schemas.TaxCodeIn, db: DbSession, principal: Principal = Edit
) -> schemas.TaxCodeOut:
    row = fin.create_tax_code(db, body, principal.user.id)
    db.commit()
    return schemas.TaxCodeOut.model_validate(row)


class PartyOut(BaseModel):
    id: uuid.UUID
    name: str
    reference: str


@router.get("/parties", response_model=list[PartyOut])
def list_parties(
    db: DbSession, kind: Literal["customer", "supplier"], _: Principal = View
) -> list[PartyOut]:
    """Names only, so Finance can bill and pay without access to CRM or supplier records."""
    if kind == "customer":
        rows = db.execute(
            select(Customer.id, Customer.name, Customer.reference)
            .where(Customer.status != "archived")
            .order_by(Customer.name)
        ).all()
    else:
        rows = db.execute(
            select(Supplier.id, Supplier.name, Supplier.reference)
            .where(Supplier.status != "suspended")
            .order_by(Supplier.name)
        ).all()
    return [PartyOut(id=i, name=n, reference=r) for i, n, r in rows]


# --- Journals ----------------------------------------------------------------------


@router.get("/journals", response_model=list[schemas.JournalOut])
def list_journals(
    db: DbSession,
    _: Principal = Ledger,
    status: str | None = Query(default=None, max_length=20),
    source_type: str | None = Query(default=None, max_length=12),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[schemas.JournalOut]:
    stmt = select(JournalEntry).order_by(
        JournalEntry.entry_date.desc(), JournalEntry.created_at.desc()
    )
    if status:
        stmt = stmt.where(JournalEntry.status == status)
    if source_type:
        stmt = stmt.where(JournalEntry.source_type == source_type)
    return fin.journals_out(db, list(db.execute(stmt.limit(limit)).scalars()))


@router.post("/journals", response_model=schemas.JournalOut, status_code=201)
def prepare_journal(
    body: schemas.ManualJournalIn, db: DbSession, principal: Principal = Edit
) -> schemas.JournalOut:
    entry = fin.prepare_manual_journal(db, body, principal)
    db.commit()
    return fin.journals_out(db, [entry])[0]


@router.get("/journals/{entry_id}", response_model=schemas.JournalOut)
def get_journal(entry_id: uuid.UUID, db: DbSession, _: Principal = Ledger) -> schemas.JournalOut:
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        raise NotFoundError("Journal not found.")
    return fin.journals_out(db, [entry])[0]


@router.post("/journals/{entry_id}/reverse", response_model=schemas.JournalOut)
def request_reversal(
    entry_id: uuid.UUID, body: schemas.ReversalIn, db: DbSession, principal: Principal = Edit
) -> schemas.JournalOut:
    entry = db.get(JournalEntry, entry_id)
    if entry is None:
        raise NotFoundError("Journal not found.")
    fin.request_reversal(db, entry, body, principal)
    db.commit()
    return fin.journals_out(db, [entry])[0]


# --- Invoices, receipts, credit notes -------------------------------------------------


@router.get("/invoices", response_model=list[schemas.InvoiceOut])
def list_invoices(
    db: DbSession,
    _: Principal = View,
    status: str | None = Query(default=None, max_length=20),
    customer_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[schemas.InvoiceOut]:
    stmt = select(Invoice).order_by(Invoice.issue_date.desc(), Invoice.created_at.desc())
    if status:
        stmt = stmt.where(Invoice.status == status)
    if customer_id:
        stmt = stmt.where(Invoice.customer_id == customer_id)
    return fin.invoices_out(db, list(db.execute(stmt.limit(limit)).scalars()))


@router.post("/invoices", response_model=schemas.InvoiceOut, status_code=201)
def create_invoice(
    body: schemas.InvoiceIn, db: DbSession, principal: Principal = Edit
) -> schemas.InvoiceOut:
    row = fin.create_invoice(db, body, principal.user.id)
    db.commit()
    return fin.invoices_out(db, [row])[0]


@router.get("/invoices/{invoice_id}", response_model=schemas.InvoiceOut)
def get_invoice(invoice_id: uuid.UUID, db: DbSession, _: Principal = View) -> schemas.InvoiceOut:
    return fin.invoices_out(db, [fin.get_invoice(db, invoice_id)])[0]


@router.post("/invoices/{invoice_id}/issue", response_model=schemas.InvoiceOut)
def issue_invoice(
    invoice_id: uuid.UUID, body: schemas.IssueIn, db: DbSession, principal: Principal = Edit
) -> schemas.InvoiceOut:
    row = fin.issue_invoice(db, fin.get_invoice(db, invoice_id), body, principal.user.id)
    db.commit()
    return fin.invoices_out(db, [row])[0]


@router.get("/receipts", response_model=list[schemas.ReceiptOut])
def list_receipts(
    db: DbSession, _: Principal = View, limit: int = Query(default=100, ge=1, le=500)
) -> list[schemas.ReceiptOut]:
    rows = db.execute(
        select(Receipt)
        .order_by(Receipt.receipt_date.desc(), Receipt.created_at.desc())
        .limit(limit)
    ).scalars()
    return fin.receipts_out(db, list(rows))


@router.post("/receipts", response_model=schemas.ReceiptOut, status_code=201)
def create_receipt(
    body: schemas.ReceiptIn, db: DbSession, principal: Principal = Edit
) -> schemas.ReceiptOut:
    row = fin.create_receipt(db, body, principal.user.id)
    db.commit()
    return fin.receipts_out(db, [row])[0]


def _credit_out(db: DbSession, note: CreditNote) -> schemas.CreditNoteOut:
    inv = db.get_one(Invoice, note.invoice_id)
    return schemas.CreditNoteOut(
        id=note.id,
        number=note.number,
        invoice_id=note.invoice_id,
        invoice_number=inv.number,
        credit_date=note.credit_date,
        amount=note.amount,
        reason=note.reason,
        status=note.status,
        journal_id=note.journal_id,
    )


@router.get("/credit-notes", response_model=list[schemas.CreditNoteOut])
def list_credit_notes(db: DbSession, _: Principal = View) -> list[schemas.CreditNoteOut]:
    rows = db.execute(
        select(CreditNote).order_by(CreditNote.created_at.desc()).limit(200)
    ).scalars()
    return [_credit_out(db, n) for n in rows]


@router.post("/credit-notes", response_model=schemas.CreditNoteOut, status_code=201)
def request_credit_note(
    body: schemas.CreditNoteIn, db: DbSession, principal: Principal = Edit
) -> schemas.CreditNoteOut:
    note = fin.request_credit_note(db, body, principal)
    db.commit()
    return _credit_out(db, note)


# --- Supplier bills and payments ------------------------------------------------------


@router.get("/bills", response_model=list[schemas.BillOut])
def list_bills(
    db: DbSession,
    _: Principal = View,
    status: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[schemas.BillOut]:
    stmt = select(Bill).order_by(Bill.bill_date.desc(), Bill.created_at.desc())
    if status:
        stmt = stmt.where(Bill.status == status)
    return fin.bills_out(db, list(db.execute(stmt.limit(limit)).scalars()))


@router.post("/bills", response_model=schemas.BillOut, status_code=201)
def create_bill(
    body: schemas.BillIn, db: DbSession, principal: Principal = Edit
) -> schemas.BillOut:
    row = fin.create_bill(db, body, principal.user.id)
    db.commit()
    return fin.bills_out(db, [row])[0]


@router.post("/bills/{bill_id}/post", response_model=schemas.BillOut)
def post_bill(
    bill_id: uuid.UUID, body: schemas.IssueIn, db: DbSession, principal: Principal = Edit
) -> schemas.BillOut:
    row = fin.post_bill(db, fin.get_bill(db, bill_id), body, principal.user.id)
    db.commit()
    return fin.bills_out(db, [row])[0]


@router.get("/payments", response_model=list[schemas.PaymentOut])
def list_payments(
    db: DbSession, _: Principal = View, limit: int = Query(default=100, ge=1, le=500)
) -> list[schemas.PaymentOut]:
    rows = db.execute(select(Payment).order_by(Payment.created_at.desc()).limit(limit)).scalars()
    return fin.payments_out(db, list(rows))


@router.post("/payments", response_model=schemas.PaymentOut, status_code=201)
def prepare_payment(
    body: schemas.PaymentIn, db: DbSession, principal: Principal = Edit
) -> schemas.PaymentOut:
    row = fin.prepare_payment(db, body, principal)
    db.commit()
    return fin.payments_out(db, [row])[0]


# --- Bank reconciliation ----------------------------------------------------------------


@router.get("/bank-statements", response_model=list[schemas.StatementLineOut])
def list_statement_lines(
    db: DbSession,
    _: Principal = View,
    bank_account_id: uuid.UUID | None = None,
    unmatched_only: bool = False,
) -> list[schemas.StatementLineOut]:
    stmt = select(BankStatementLine).order_by(BankStatementLine.statement_date.desc()).limit(500)
    if bank_account_id:
        stmt = stmt.where(BankStatementLine.bank_account_id == bank_account_id)
    if unmatched_only:
        stmt = stmt.where(BankStatementLine.matched_line_id.is_(None))
    return [schemas.StatementLineOut.model_validate(r) for r in db.execute(stmt).scalars()]


@router.post("/bank-statements", response_model=schemas.StatementLineOut, status_code=201)
def add_statement_line(
    body: schemas.StatementLineIn, db: DbSession, principal: Principal = Edit
) -> schemas.StatementLineOut:
    row = fin.add_statement_line(db, body, principal.user.id)
    db.commit()
    return schemas.StatementLineOut.model_validate(row)


@router.post("/bank-statements/{line_id}/match", response_model=schemas.StatementLineOut)
def match_statement_line(
    line_id: uuid.UUID, body: schemas.MatchIn, db: DbSession, principal: Principal = Edit
) -> schemas.StatementLineOut:
    row = db.get(BankStatementLine, line_id)
    if row is None:
        raise NotFoundError("Statement line not found.")
    fin.match_statement_line(db, row, body.journal_line_id, principal.user.id)
    db.commit()
    return schemas.StatementLineOut.model_validate(row)


# --- Reports -------------------------------------------------------------------------------


@router.get("/reports/trial-balance", response_model=schemas.TrialBalance)
def trial_balance(
    db: DbSession, _: Principal = Ledger, as_of: date | None = None
) -> schemas.TrialBalance:
    return reports.trial_balance(db, as_of or _today())


@router.get("/reports/profit-and-loss", response_model=schemas.ProfitAndLoss)
def profit_and_loss(
    db: DbSession, date_from: date, date_to: date, _: Principal = Ledger
) -> schemas.ProfitAndLoss:
    return reports.profit_and_loss(db, date_from, date_to)


@router.get("/reports/balance-sheet", response_model=schemas.BalanceSheet)
def balance_sheet(
    db: DbSession, _: Principal = Ledger, as_of: date | None = None
) -> schemas.BalanceSheet:
    return reports.balance_sheet(db, as_of or _today())


@router.get("/reports/ageing", response_model=schemas.Ageing)
def ageing(
    db: DbSession,
    kind: Literal["receivable", "payable"],
    _: Principal = View,
    as_of: date | None = None,
) -> schemas.Ageing:
    return reports.ageing(db, kind, as_of or _today())


@router.get("/reports/statement", response_model=schemas.Statement)
def customer_statement(
    db: DbSession,
    customer_id: uuid.UUID,
    _: Principal = View,
    date_from: date | None = None,
    date_to: date | None = None,
) -> schemas.Statement:
    """Customer account statement. Defaults to the current calendar year to date."""
    end = date_to or _today()
    start = date_from or date(end.year, 1, 1)
    if start > end:
        raise posting.FinanceRuleError("The start date is after the end date.")
    return reports.statement(db, customer_id, start, end)


@router.get("/reports/cashbook", response_model=schemas.Cashbook)
def cashbook(
    db: DbSession, account_id: uuid.UUID, date_from: date, date_to: date, _: Principal = Ledger
) -> schemas.Cashbook:
    return reports.cashbook(db, account_id, date_from, date_to)


@router.get("/overview", response_model=schemas.FinanceOverview)
def overview(db: DbSession, _: Principal = Ledger) -> schemas.FinanceOverview:
    return reports.overview(db, _today())
