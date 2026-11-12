"""Finance documents: configuration, manual journals, invoices, receipts,
credit notes, supplier bills, payments and bank reconciliation."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.modules.crm.models import Customer, Opportunity
from app.modules.procurement.models import PurchaseOrder, Supplier, SupplierBankAccount
from app.platform.approvals import service as approvals
from app.platform.approvals.models import ApprovalRequest
from app.platform.audit import service as audit
from app.platform.authz.deps import Principal

from . import posting, schemas
from .models import (
    Account,
    BankStatementLine,
    Bill,
    BillLine,
    CreditNote,
    ExchangeRate,
    Invoice,
    InvoiceLine,
    JournalEntry,
    JournalLine,
    Payment,
    Period,
    Receipt,
    ReceiptAllocation,
    Settings,
    TaxCode,
)
from .posting import FinanceRuleError, Line, money

APPROVE = "finance.transaction.approve"
JOURNAL_SUBJECT = "manual_journal"
REVERSAL_SUBJECT = "journal_reversal"
CREDIT_SUBJECT = "credit_note"
PAYMENT_SUBJECT = "supplier_payment"


def _audit(
    db: Session, action: str, actor: uuid.UUID, kind: str, target: Any, **details: Any
) -> None:
    audit.record(
        db,
        action=f"finance.{action}",
        actor_id=actor,
        target_type=kind,
        target_id=target,
        details=details,
    )


# --- Configuration ----------------------------------------------------------------


def settings_row(db: Session) -> Settings:
    row = db.get(Settings, 1)
    if row is None:
        row = Settings(id=1)
        db.add(row)
        db.flush()
    return row


def settings_out(db: Session) -> schemas.SettingsOut:
    s = settings_row(db)
    missing = []
    if not s.receivable_account_id:
        missing.append("receivable (debtors) control account")
    if not s.payable_account_id:
        missing.append("payable (creditors) control account")
    if not s.fx_gain_loss_account_id:
        missing.append("exchange gain/loss account")
    if not db.execute(select(Period.id).where(Period.status == "open").limit(1)).first():
        missing.append("an open financial period")
    return schemas.SettingsOut(
        functional_currency=posting.functional_currency(db),
        receivable_account_id=s.receivable_account_id,
        payable_account_id=s.payable_account_id,
        fx_gain_loss_account_id=s.fx_gain_loss_account_id,
        accountant_reviewed=s.accountant_reviewed,
        ready_for_invoicing=bool(s.receivable_account_id),
        ready_for_bills=bool(s.payable_account_id),
        missing=missing,
    )


def _account(db: Session, account_id: uuid.UUID, *subtypes: str) -> Account:
    account = db.get(Account, account_id)
    if account is None or not account.is_active:
        raise FinanceRuleError("The account does not exist or is inactive.")
    if subtypes and account.subtype not in subtypes:
        raise FinanceRuleError(
            f"Account {account.code} is a {account.subtype} account; "
            f"expected {', '.join(subtypes)}."
        )
    return account


def update_settings(db: Session, body: schemas.SettingsIn, actor: uuid.UUID) -> None:
    s = settings_row(db)
    checks = {
        "receivable_account_id": ("receivable",),
        "payable_account_id": ("payable",),
        "fx_gain_loss_account_id": ("fx_gain_loss",),
    }
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            _account(db, value, *checks[field])
        setattr(s, field, value)
    s.updated_by = actor
    _audit(db, "settings.updated", actor, "fin_settings", 1, fields=sorted(body.model_fields_set))


def create_account(db: Session, body: schemas.AccountIn, actor: uuid.UUID) -> Account:
    if db.execute(select(Account.id).where(Account.code == body.code)).first():
        raise ConflictError(f"Account code {body.code} is already used.")
    row = Account(type=schemas.SUBTYPE_TYPE[body.subtype], created_by=actor, **body.model_dump())
    db.add(row)
    db.flush()
    _audit(db, "account.created", actor, "fin_account", row.id, code=row.code)
    return row


def create_period(db: Session, body: schemas.PeriodIn, actor: uuid.UUID) -> Period:
    overlap = db.execute(
        select(Period.name).where(
            Period.start_date <= body.end_date, Period.end_date >= body.start_date
        )
    ).first()
    if overlap:
        raise ConflictError(f"The dates overlap period {overlap[0]}.")
    row = Period(**body.model_dump())
    db.add(row)
    db.flush()
    _audit(db, "period.created", actor, "fin_period", row.id, name=row.name)
    return row


def close_period(db: Session, period: Period, actor: uuid.UUID) -> Period:
    if period.status == "closed":
        raise ConflictError("This period is already closed.")
    pending = db.execute(
        select(func.count())
        .select_from(JournalEntry)
        .where(
            JournalEntry.period_id == period.id,
            JournalEntry.status.in_(("draft", "awaiting_approval")),
        )
    ).scalar_one()
    if pending:
        raise ConflictError(f"{pending} journal(s) in this period are not posted or rejected yet.")
    period.status = "closed"
    period.closed_by = actor
    period.closed_at = posting.now()
    _audit(db, "period.closed", actor, "fin_period", period.id, name=period.name)
    return period


def add_rate(db: Session, body: schemas.RateIn, actor: uuid.UUID) -> ExchangeRate:
    if body.currency == posting.functional_currency(db):
        raise FinanceRuleError("The functional currency always has a rate of 1.")
    if db.execute(
        select(ExchangeRate.id).where(
            ExchangeRate.currency == body.currency, ExchangeRate.rate_date == body.rate_date
        )
    ).first():
        raise ConflictError("A rate for this currency and date already exists. Rates are history.")
    row = ExchangeRate(created_by=actor, **body.model_dump())
    db.add(row)
    db.flush()
    _audit(db, "rate.added", actor, "fin_rate", row.id, currency=row.currency, rate=row.rate)
    return row


def create_tax_code(db: Session, body: schemas.TaxCodeIn, actor: uuid.UUID) -> TaxCode:
    if db.execute(select(TaxCode.id).where(TaxCode.code == body.code)).first():
        raise ConflictError(f"Tax code {body.code} already exists.")
    _account(db, body.account_id, "tax")
    if body.effective_to and body.effective_to < body.effective_from:
        raise FinanceRuleError("The end date cannot be before the start date.")
    row = TaxCode(created_by=actor, **body.model_dump())
    db.add(row)
    db.flush()
    _audit(db, "tax_code.created", actor, "fin_tax_code", row.id, code=row.code, rate=row.rate_pct)
    return row


def _tax_code(db: Session, tax_code_id: uuid.UUID | None, kind: str, on: date) -> TaxCode | None:
    if tax_code_id is None:
        return None
    code = db.get(TaxCode, tax_code_id)
    if code is None or code.kind != kind:
        raise FinanceRuleError(f"Choose an {kind} tax code.")
    if code.effective_from > on or (code.effective_to and code.effective_to < on):
        raise FinanceRuleError(f"Tax code {code.code} is not in effect on {on.isoformat()}.")
    return code


# --- Journals ---------------------------------------------------------------------


def journals_out(db: Session, entries: list[JournalEntry]) -> list[schemas.JournalOut]:
    if not entries:
        return []
    rows = db.execute(
        select(JournalLine, Account.code, Account.name)
        .join(Account, Account.id == JournalLine.account_id)
        .where(JournalLine.entry_id.in_([e.id for e in entries]))
        .order_by(JournalLine.entry_id, JournalLine.line_no)
    ).all()
    lines: dict[uuid.UUID, list[schemas.JournalLineOut]] = defaultdict(list)
    for line, code, name in rows:
        lines[line.entry_id].append(
            schemas.JournalLineOut(
                line_no=line.line_no,
                account_id=line.account_id,
                account_code=code,
                account_name=name,
                description=line.description,
                currency=line.currency,
                amount=line.amount,
                fx_rate=line.fx_rate,
                debit=line.debit,
                credit=line.credit,
            )
        )
    return [
        schemas.JournalOut(
            id=e.id,
            number=e.number,
            entry_date=e.entry_date,
            description=e.description,
            source_type=e.source_type,
            source_id=e.source_id,
            status=e.status,
            reverses_id=e.reverses_id,
            reversed_by_id=e.reversed_by_id,
            posted_at=e.posted_at,
            lines=lines.get(e.id, []),
        )
        for e in entries
    ]


def prepare_manual_journal(
    db: Session, body: schemas.ManualJournalIn, principal: Principal
) -> JournalEntry:
    """A manual journal is prepared here and posted only after a different person approves."""
    currency = posting.functional_currency(db)
    lines = [
        Line(
            account_id=line.account_id,
            side="debit" if line.debit > 0 else "credit",
            amount=line.debit or line.credit,
            currency=currency,
            fx_rate=Decimal(1),
            description=line.description,
        )
        for line in body.lines
    ]
    period = posting.open_period(db, body.entry_date)
    posting._check_accounts(db, lines)
    prepared = posting.prepare_lines(lines)
    entry = JournalEntry(
        entry_date=body.entry_date,
        period_id=period.id,
        description=body.description,
        source_type="manual",
        status="awaiting_approval",
        created_by=principal.user.id,
    )
    db.add(entry)
    db.flush()
    posting.write_lines(db, entry, prepared)
    total = sum((f for line, f in prepared if line.side == "debit"), Decimal(0))
    req = approvals.create_request(
        db,
        principal=principal,
        subject_type=JOURNAL_SUBJECT,
        subject_id=str(entry.id),
        permission_required=APPROVE,
        summary=f"Post manual journal dated {body.entry_date.isoformat()}: {body.description} "
        f"({currency} {total:,.2f})",
        payload={"total": str(total), "lines": len(prepared)},
    )
    entry.approval_id = req.id
    _audit(db, "journal.prepared", principal.user.id, "fin_journal", entry.id)
    return entry


def _apply_journal_decision(db: Session, request: ApprovalRequest) -> None:
    entry = db.get(JournalEntry, uuid.UUID(request.subject_id))
    if entry is None or entry.status != "awaiting_approval":
        raise ConflictError("This journal is no longer waiting for approval.")
    if request.status == "approved":
        posting.finalise(db, entry, request.decided_by or request.requested_by)
    else:
        entry.status = "rejected"


def request_reversal(
    db: Session, entry: JournalEntry, body: schemas.ReversalIn, principal: Principal
) -> ApprovalRequest:
    if entry.status != "posted":
        raise ConflictError("Only a posted entry that has not been reversed can be reversed.")
    if entry.source_type in ("invoice", "receipt", "bill", "payment", "credit_note"):
        raise ConflictError(
            "Document postings are corrected with a credit note or a new document, "
            "not by reversing the journal."
        )
    if body.entry_date < entry.entry_date:
        raise FinanceRuleError("A reversal cannot be dated before the original entry.")
    posting.open_period(db, body.entry_date)
    return approvals.create_request(
        db,
        principal=principal,
        subject_type=REVERSAL_SUBJECT,
        subject_id=str(entry.id),
        permission_required=APPROVE,
        summary=f"Reverse journal {entry.number}: {body.reason}",
        payload={"entry_date": body.entry_date.isoformat(), "reason": body.reason},
    )


def _apply_reversal_decision(db: Session, request: ApprovalRequest) -> None:
    if request.status != "approved":
        return
    entry = db.get_one(JournalEntry, uuid.UUID(request.subject_id))
    posting.reverse_entry(
        db,
        entry,
        date.fromisoformat(request.payload["entry_date"]),
        request.decided_by or request.requested_by,
        request.payload["reason"],
    )


# --- Invoices ---------------------------------------------------------------------


def _doc_lines(
    db: Session, lines: list[schemas.DocLineIn], kind: str, on: date, allowed: tuple[str, ...]
) -> list[tuple[schemas.DocLineIn, Decimal, Decimal]]:
    out = []
    for line in lines:
        _account(db, line.account_id, *allowed)
        code = _tax_code(db, line.tax_code_id, kind, on)
        net = money(line.quantity * line.unit_price)
        tax = money(net * code.rate_pct / 100) if code else Decimal(0)
        out.append((line, net, tax))
    return out


def get_invoice(db: Session, invoice_id: uuid.UUID) -> Invoice:
    row = db.get(Invoice, invoice_id)
    if row is None:
        raise NotFoundError("Invoice not found.")
    return row


def create_invoice(db: Session, body: schemas.InvoiceIn, actor: uuid.UUID) -> Invoice:
    customer = db.get(Customer, body.customer_id)
    if customer is None or customer.status == "archived":
        raise FinanceRuleError("Choose an existing, non-archived customer.")
    if body.opportunity_id:
        opp = db.get(Opportunity, body.opportunity_id)
        if opp is None or opp.customer_id != customer.id:
            raise FinanceRuleError("The opportunity belongs to a different customer.")
    priced = _doc_lines(db, body.lines, "output", body.issue_date, ("revenue",))
    invoice = Invoice(
        customer_id=customer.id,
        currency=body.currency,
        issue_date=body.issue_date,
        due_date=body.due_date,
        notes=body.notes,
        opportunity_id=body.opportunity_id,
        created_by=actor,
    )
    db.add(invoice)
    db.flush()
    for n, (line, net, tax) in enumerate(priced, start=1):
        db.add(
            InvoiceLine(
                invoice_id=invoice.id,
                line_no=n,
                net=net,
                tax=tax,
                **line.model_dump(),
            )
        )
    invoice.subtotal = sum((net for _, net, _ in priced), Decimal(0))
    invoice.tax_total = sum((tax for _, _, tax in priced), Decimal(0))
    invoice.total = invoice.subtotal + invoice.tax_total
    if invoice.total <= 0:
        raise FinanceRuleError("An invoice total must be greater than zero.")
    db.flush()
    _audit(db, "invoice.drafted", actor, "fin_invoice", invoice.id, total=invoice.total)
    return invoice


def issue_invoice(
    db: Session, invoice: Invoice, body: schemas.IssueIn, actor: uuid.UUID
) -> Invoice:
    if invoice.status != "draft":
        raise ConflictError("Only a draft invoice can be issued.")
    receivable = settings_row(db).receivable_account_id
    if receivable is None:
        raise FinanceRuleError("Set the receivable (debtors) control account first.")
    rate = posting.rate_for(db, invoice.currency, invoice.issue_date, body.fx_rate)
    lines = list(
        db.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == invoice.id)).scalars()
    )
    journal_lines = [
        Line(
            receivable,
            "debit",
            invoice.total,
            invoice.currency,
            rate,
            "Invoice total",
            "customer",
            invoice.customer_id,
        )
    ]
    for line in lines:
        if line.net > 0:
            journal_lines.append(
                Line(line.account_id, "credit", line.net, invoice.currency, rate, line.description)
            )
    taxes: dict[uuid.UUID, Decimal] = defaultdict(Decimal)
    for line in lines:
        if line.tax > 0 and line.tax_code_id:
            taxes[db.get_one(TaxCode, line.tax_code_id).account_id] += line.tax
    for account_id, amount in taxes.items():
        journal_lines.append(
            Line(account_id, "credit", amount, invoice.currency, rate, "Output tax")
        )
    invoice.number = posting.next_number(db, "INV", invoice.issue_date)
    entry = posting.post_entry(
        db,
        entry_date=invoice.issue_date,
        description=f"Invoice {invoice.number}",
        source_type="invoice",
        source_id=invoice.id,
        lines=journal_lines,
        actor=actor,
    )
    invoice.fx_rate = rate
    invoice.status = "issued"
    invoice.journal_id = entry.id
    invoice.issued_by = actor
    invoice.issued_at = posting.now()
    _audit(db, "invoice.issued", actor, "fin_invoice", invoice.id, number=invoice.number)
    return invoice


def _settle_status(total: Decimal, paid: Decimal, credited: Decimal) -> str:
    if paid + credited >= total:
        return "paid" if paid > 0 else "credited"
    return "partially_paid" if paid + credited > 0 else "issued"


def invoices_out(db: Session, rows: list[Invoice]) -> list[schemas.InvoiceOut]:
    if not rows:
        return []
    names = dict(
        db.execute(
            select(Customer.id, Customer.name).where(Customer.id.in_({r.customer_id for r in rows}))
        )
        .tuples()
        .all()
    )
    lines: dict[uuid.UUID, list[schemas.DocLineOut]] = defaultdict(list)
    for line in db.execute(
        select(InvoiceLine)
        .where(InvoiceLine.invoice_id.in_([r.id for r in rows]))
        .order_by(InvoiceLine.line_no)
    ).scalars():
        lines[line.invoice_id].append(
            schemas.DocLineOut(
                line_no=line.line_no,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                account_id=line.account_id,
                tax_code_id=line.tax_code_id,
                net=line.net,
                tax=line.tax,
            )
        )
    return [
        schemas.InvoiceOut(
            id=r.id,
            number=r.number,
            customer_id=r.customer_id,
            customer_name=names.get(r.customer_id, ""),
            currency=r.currency,
            fx_rate=r.fx_rate,
            issue_date=r.issue_date,
            due_date=r.due_date,
            status=r.status,
            subtotal=r.subtotal,
            tax_total=r.tax_total,
            total=r.total,
            amount_paid=r.amount_paid,
            amount_credited=r.amount_credited,
            outstanding=r.total - r.amount_paid - r.amount_credited
            if r.status != "draft"
            else r.total,
            notes=r.notes,
            journal_id=r.journal_id,
            issued_at=r.issued_at,
            lines=lines.get(r.id, []),
        )
        for r in rows
    ]


# --- Receipts ---------------------------------------------------------------------


def create_receipt(db: Session, body: schemas.ReceiptIn, actor: uuid.UUID) -> Receipt:
    s = settings_row(db)
    if s.receivable_account_id is None:
        raise FinanceRuleError("Set the receivable (debtors) control account first.")
    bank = _account(db, body.bank_account_id, "bank")
    if bank.currency and bank.currency != body.currency:
        raise FinanceRuleError(f"Bank account {bank.code} holds {bank.currency} only.")
    allocated = sum((a.amount for a in body.allocations), Decimal(0))
    if allocated != body.amount:
        raise FinanceRuleError(
            "Allocate the whole receipt to invoices (unallocated money is not supported yet)."
        )
    if len({a.invoice_id for a in body.allocations}) != len(body.allocations):
        raise FinanceRuleError("Allocate to each invoice only once per receipt.")
    rate = posting.rate_for(db, body.currency, body.receipt_date, body.fx_rate)
    receipt_number = posting.next_number(db, "RCT", body.receipt_date)
    lines = [Line(bank.id, "debit", body.amount, body.currency, rate, f"Receipt {receipt_number}")]
    fx_difference = Decimal(0)
    invoices: list[tuple[Invoice, Decimal]] = []
    for alloc in body.allocations:
        inv = db.execute(
            select(Invoice).where(Invoice.id == alloc.invoice_id).with_for_update()
        ).scalar_one_or_none()
        if inv is None or inv.customer_id != body.customer_id:
            raise FinanceRuleError("Each allocation must be to an invoice of this customer.")
        if inv.status not in ("issued", "partially_paid") or inv.fx_rate is None:
            raise FinanceRuleError(f"Invoice {inv.number or 'draft'} is not open for payment.")
        if inv.currency != body.currency:
            raise FinanceRuleError(f"Invoice {inv.number} is in {inv.currency}.")
        outstanding = inv.total - inv.amount_paid - inv.amount_credited
        if alloc.amount > outstanding:
            raise FinanceRuleError(f"Invoice {inv.number} has only {outstanding} outstanding.")
        cleared = money(alloc.amount * inv.fx_rate)  # AR is cleared at the invoice's rate
        fx_difference += money(alloc.amount * rate) - cleared
        lines.append(
            Line(
                s.receivable_account_id,
                "credit",
                alloc.amount,
                body.currency,
                inv.fx_rate,
                f"Settles {inv.number}",
                "customer",
                inv.customer_id,
                functional=cleared,
            )
        )
        invoices.append((inv, alloc.amount))
    # Fix the bank line at the receipt rate and put any exchange difference on the FX account.
    lines[0] = Line(
        bank.id,
        "debit",
        body.amount,
        body.currency,
        rate,
        f"Receipt {receipt_number}",
        functional=money(body.amount * rate),
    )
    if fx_difference:
        if s.fx_gain_loss_account_id is None:
            raise FinanceRuleError("Set the exchange gain/loss account first.")
        lines.append(
            Line(
                s.fx_gain_loss_account_id,
                "credit" if fx_difference > 0 else "debit",
                abs(fx_difference),
                posting.functional_currency(db),
                Decimal(1),
                "Realised exchange difference",
            )
        )
    entry = posting.post_entry(
        db,
        entry_date=body.receipt_date,
        description=f"Receipt {receipt_number}",
        source_type="receipt",
        source_id=None,
        lines=lines,
        actor=actor,
    )
    receipt = Receipt(
        number=receipt_number,
        customer_id=body.customer_id,
        receipt_date=body.receipt_date,
        currency=body.currency,
        fx_rate=rate,
        amount=body.amount,
        bank_account_id=bank.id,
        method=body.method,
        reference=body.reference,
        journal_id=entry.id,
        created_by=actor,
    )
    db.add(receipt)
    db.flush()
    for inv, amount in invoices:
        db.add(ReceiptAllocation(receipt_id=receipt.id, invoice_id=inv.id, amount=amount))
        inv.amount_paid += amount
        inv.status = _settle_status(inv.total, inv.amount_paid, inv.amount_credited)
    db.flush()
    _audit(db, "receipt.recorded", actor, "fin_receipt", receipt.id, number=receipt.number)
    return receipt


def receipts_out(db: Session, rows: list[Receipt]) -> list[schemas.ReceiptOut]:
    if not rows:
        return []
    names = dict(
        db.execute(
            select(Customer.id, Customer.name).where(Customer.id.in_({r.customer_id for r in rows}))
        )
        .tuples()
        .all()
    )
    allocs: dict[uuid.UUID, list[schemas.AllocationIn]] = defaultdict(list)
    for a in db.execute(
        select(ReceiptAllocation).where(ReceiptAllocation.receipt_id.in_([r.id for r in rows]))
    ).scalars():
        allocs[a.receipt_id].append(schemas.AllocationIn(invoice_id=a.invoice_id, amount=a.amount))
    return [
        schemas.ReceiptOut(
            id=r.id,
            number=r.number,
            customer_id=r.customer_id,
            customer_name=names.get(r.customer_id, ""),
            receipt_date=r.receipt_date,
            currency=r.currency,
            fx_rate=r.fx_rate,
            amount=r.amount,
            method=r.method,
            reference=r.reference,
            journal_id=r.journal_id,
            allocations=allocs.get(r.id, []),
        )
        for r in rows
    ]


# --- Credit notes -------------------------------------------------------------------


def request_credit_note(
    db: Session, body: schemas.CreditNoteIn, principal: Principal
) -> CreditNote:
    inv = get_invoice(db, body.invoice_id)
    if inv.status not in ("issued", "partially_paid"):
        raise ConflictError("Only an issued invoice with an outstanding balance can be credited.")
    pending = db.execute(
        select(func.coalesce(func.sum(CreditNote.amount), 0)).where(
            CreditNote.invoice_id == inv.id, CreditNote.status == "awaiting_approval"
        )
    ).scalar_one()
    available = inv.total - inv.amount_paid - inv.amount_credited - Decimal(pending)
    if body.amount > available:
        raise FinanceRuleError(f"At most {available} can be credited on {inv.number}.")
    if body.credit_date < inv.issue_date:
        raise FinanceRuleError("A credit note cannot be dated before its invoice.")
    note = CreditNote(
        invoice_id=inv.id,
        credit_date=body.credit_date,
        amount=body.amount,
        reason=body.reason,
        created_by=principal.user.id,
    )
    db.add(note)
    db.flush()
    req = approvals.create_request(
        db,
        principal=principal,
        subject_type=CREDIT_SUBJECT,
        subject_id=str(note.id),
        permission_required=APPROVE,
        summary=f"Credit note on {inv.number} for {inv.currency} {body.amount:,.2f}: {body.reason}",
        payload={"invoice": inv.number, "amount": str(body.amount), "currency": inv.currency},
    )
    note.approval_id = req.id
    _audit(db, "credit_note.requested", principal.user.id, "fin_invoice", inv.id)
    return note


def _apply_credit_decision(db: Session, request: ApprovalRequest) -> None:
    note = db.get(CreditNote, uuid.UUID(request.subject_id))
    if note is None or note.status != "awaiting_approval":
        raise ConflictError("This credit note is no longer waiting for approval.")
    if request.status != "approved":
        note.status = "rejected"
        return
    inv = db.execute(
        select(Invoice).where(Invoice.id == note.invoice_id).with_for_update()
    ).scalar_one()
    if note.amount > inv.total - inv.amount_paid - inv.amount_credited:
        raise ConflictError(
            "The invoice balance changed; the credit is now larger than what is owed."
        )
    receivable = settings_row(db).receivable_account_id
    assert receivable is not None  # nosec B101 - invoice was issued, so it is configured
    rate = inv.fx_rate or Decimal(1)
    ratio = note.amount / inv.total
    tax_part = money(inv.tax_total * ratio)
    net_part = note.amount - tax_part
    lines = list(db.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == inv.id)).scalars())
    journal: list[Line] = []
    # Spread the net credit over revenue accounts in proportion; remainder on the last.
    by_account: dict[uuid.UUID, Decimal] = defaultdict(Decimal)
    for line in lines:
        by_account[line.account_id] += line.net
    remaining = net_part
    accounts = list(by_account.items())
    for i, (account_id, net) in enumerate(accounts):
        share = remaining if i == len(accounts) - 1 else money(net_part * net / inv.subtotal)
        remaining -= share
        if share > 0:
            journal.append(Line(account_id, "debit", share, inv.currency, rate, "Credit note"))
    if tax_part > 0:
        tax_accounts: dict[uuid.UUID, Decimal] = defaultdict(Decimal)
        for line in lines:
            if line.tax_code_id and line.tax > 0:
                tax_accounts[db.get_one(TaxCode, line.tax_code_id).account_id] += line.tax
        left = tax_part
        items = list(tax_accounts.items())
        for i, (account_id, tax) in enumerate(items):
            share = left if i == len(items) - 1 else money(tax_part * tax / inv.tax_total)
            left -= share
            if share > 0:
                journal.append(
                    Line(account_id, "debit", share, inv.currency, rate, "Output tax reversed")
                )
    journal.append(
        Line(
            receivable,
            "credit",
            note.amount,
            inv.currency,
            rate,
            f"Credit on {inv.number}",
            "customer",
            inv.customer_id,
        )
    )
    note.number = posting.next_number(db, "CN", note.credit_date)
    entry = posting.post_entry(
        db,
        entry_date=note.credit_date,
        description=f"Credit note {note.number} on {inv.number}",
        source_type="credit_note",
        source_id=note.id,
        lines=journal,
        actor=note.created_by,
        posted_by=request.decided_by,
        approval_id=request.id,
    )
    note.status = "posted"
    note.journal_id = entry.id
    inv.amount_credited += note.amount
    inv.status = _settle_status(inv.total, inv.amount_paid, inv.amount_credited)


# --- Supplier bills ------------------------------------------------------------------


def get_bill(db: Session, bill_id: uuid.UUID) -> Bill:
    row = db.get(Bill, bill_id)
    if row is None:
        raise NotFoundError("Bill not found.")
    return row


def create_bill(db: Session, body: schemas.BillIn, actor: uuid.UUID) -> Bill:
    supplier = db.get(Supplier, body.supplier_id)
    if supplier is None:
        raise FinanceRuleError("Choose an existing supplier.")
    if db.execute(
        select(Bill.id).where(
            Bill.supplier_id == supplier.id, Bill.supplier_invoice_ref == body.supplier_invoice_ref
        )
    ).first():
        raise ConflictError("This supplier invoice has already been entered.")
    if body.purchase_order_id:
        po = db.get(PurchaseOrder, body.purchase_order_id)
        if po is None or po.supplier_id != supplier.id or po.status == "cancelled":
            raise FinanceRuleError("The purchase order is not an open order of this supplier.")
    priced = _doc_lines(
        db,
        body.lines,
        "input",
        body.bill_date,
        ("expense", "cost_of_sales", "inventory", "fixed_asset"),
    )
    bill = Bill(
        supplier_id=supplier.id,
        supplier_invoice_ref=body.supplier_invoice_ref,
        purchase_order_id=body.purchase_order_id,
        currency=body.currency,
        bill_date=body.bill_date,
        due_date=body.due_date,
        created_by=actor,
    )
    db.add(bill)
    db.flush()
    for n, (line, net, tax) in enumerate(priced, start=1):
        db.add(BillLine(bill_id=bill.id, line_no=n, net=net, tax=tax, **line.model_dump()))
    bill.subtotal = sum((net for _, net, _ in priced), Decimal(0))
    bill.tax_total = sum((tax for _, _, tax in priced), Decimal(0))
    bill.total = bill.subtotal + bill.tax_total
    if bill.total <= 0:
        raise FinanceRuleError("A bill total must be greater than zero.")
    db.flush()
    _audit(db, "bill.drafted", actor, "fin_bill", bill.id, total=bill.total)
    return bill


def post_bill(db: Session, bill: Bill, body: schemas.IssueIn, actor: uuid.UUID) -> Bill:
    if bill.status != "draft":
        raise ConflictError("Only a draft bill can be posted.")
    payable = settings_row(db).payable_account_id
    if payable is None:
        raise FinanceRuleError("Set the payable (creditors) control account first.")
    rate = posting.rate_for(db, bill.currency, bill.bill_date, body.fx_rate)
    lines = list(db.execute(select(BillLine).where(BillLine.bill_id == bill.id)).scalars())
    journal = [
        Line(line.account_id, "debit", line.net, bill.currency, rate, line.description)
        for line in lines
        if line.net > 0
    ]
    taxes: dict[uuid.UUID, Decimal] = defaultdict(Decimal)
    for line in lines:
        if line.tax > 0 and line.tax_code_id:
            taxes[db.get_one(TaxCode, line.tax_code_id).account_id] += line.tax
    for account_id, amount in taxes.items():
        journal.append(Line(account_id, "debit", amount, bill.currency, rate, "Input tax"))
    journal.append(
        Line(
            payable,
            "credit",
            bill.total,
            bill.currency,
            rate,
            "Bill total",
            "supplier",
            bill.supplier_id,
        )
    )
    bill.number = posting.next_number(db, "BILL", bill.bill_date)
    entry = posting.post_entry(
        db,
        entry_date=bill.bill_date,
        description=f"Supplier bill {bill.number} ({bill.supplier_invoice_ref})",
        source_type="bill",
        source_id=bill.id,
        lines=journal,
        actor=actor,
    )
    bill.fx_rate = rate
    bill.status = "posted"
    bill.journal_id = entry.id
    _audit(db, "bill.posted", actor, "fin_bill", bill.id, number=bill.number)
    return bill


def bills_out(db: Session, rows: list[Bill]) -> list[schemas.BillOut]:
    if not rows:
        return []
    names = dict(
        db.execute(
            select(Supplier.id, Supplier.name).where(Supplier.id.in_({r.supplier_id for r in rows}))
        )
        .tuples()
        .all()
    )
    lines: dict[uuid.UUID, list[schemas.DocLineOut]] = defaultdict(list)
    for line in db.execute(
        select(BillLine)
        .where(BillLine.bill_id.in_([r.id for r in rows]))
        .order_by(BillLine.line_no)
    ).scalars():
        lines[line.bill_id].append(
            schemas.DocLineOut(
                line_no=line.line_no,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                account_id=line.account_id,
                tax_code_id=line.tax_code_id,
                net=line.net,
                tax=line.tax,
            )
        )
    return [
        schemas.BillOut(
            id=r.id,
            number=r.number,
            supplier_id=r.supplier_id,
            supplier_name=names.get(r.supplier_id, ""),
            supplier_invoice_ref=r.supplier_invoice_ref,
            purchase_order_id=r.purchase_order_id,
            currency=r.currency,
            fx_rate=r.fx_rate,
            bill_date=r.bill_date,
            due_date=r.due_date,
            status=r.status,
            subtotal=r.subtotal,
            tax_total=r.tax_total,
            total=r.total,
            amount_paid=r.amount_paid,
            outstanding=r.total - r.amount_paid,
            journal_id=r.journal_id,
            lines=lines.get(r.id, []),
        )
        for r in rows
    ]


# --- Payments ---------------------------------------------------------------------------


def prepare_payment(db: Session, body: schemas.PaymentIn, principal: Principal) -> Payment:
    bill = db.execute(
        select(Bill).where(Bill.id == body.bill_id).with_for_update()
    ).scalar_one_or_none()
    if bill is None or bill.status not in ("posted", "partially_paid"):
        raise FinanceRuleError("Choose a posted bill with an outstanding balance.")
    supplier = db.get_one(Supplier, bill.supplier_id)
    if supplier.status == "suspended":
        raise ConflictError("This supplier is suspended.")
    bank = _account(db, body.bank_account_id, "bank")
    if bank.currency and bank.currency != bill.currency:
        raise FinanceRuleError(f"Bank account {bank.code} holds {bank.currency} only.")
    pending = db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.bill_id == bill.id, Payment.status == "awaiting_approval"
        )
    ).scalar_one()
    available = bill.total - bill.amount_paid - Decimal(pending)
    if body.amount > available:
        raise FinanceRuleError(f"At most {available} can be paid on {bill.number}.")
    payee = None
    if body.method == "bank_transfer":
        payee = db.execute(
            select(SupplierBankAccount).where(
                SupplierBankAccount.supplier_id == supplier.id,
                SupplierBankAccount.status == "active",
            )
        ).scalar_one_or_none()
        if payee is None:
            raise ConflictError("The supplier has no approved bank account on file.")
    rate = posting.rate_for(db, bill.currency, body.payment_date, body.fx_rate)
    payment = Payment(
        bill_id=bill.id,
        supplier_id=supplier.id,
        supplier_bank_account_id=payee.id if payee else None,
        payment_date=body.payment_date,
        currency=bill.currency,
        fx_rate=rate,
        amount=body.amount,
        bank_account_id=bank.id,
        method=body.method,
        reference=body.reference,
        prepared_by=principal.user.id,
    )
    db.add(payment)
    db.flush()
    req = approvals.create_request(
        db,
        principal=principal,
        subject_type=PAYMENT_SUBJECT,
        subject_id=str(payment.id),
        permission_required=APPROVE,
        summary=f"Pay {supplier.name} {bill.currency} {body.amount:,.2f} against {bill.number}"
        + (f" to account ending {payee.account_last4}" if payee else f" by {body.method}"),
        payload={
            "bill": bill.number,
            "supplier": supplier.reference,
            "amount": str(body.amount),
            "currency": bill.currency,
            "payee_ending": payee.account_last4 if payee else None,
        },
    )
    payment.approval_id = req.id
    _audit(db, "payment.prepared", principal.user.id, "fin_payment", payment.id, amount=body.amount)
    return payment


def _apply_payment_decision(db: Session, request: ApprovalRequest) -> None:
    payment = db.get(Payment, uuid.UUID(request.subject_id))
    if payment is None or payment.status != "awaiting_approval":
        raise ConflictError("This payment is no longer waiting for approval.")
    if request.status != "approved":
        payment.status = "rejected"
        return
    bill = db.execute(select(Bill).where(Bill.id == payment.bill_id).with_for_update()).scalar_one()
    if payment.amount > bill.total - bill.amount_paid:
        raise ConflictError(
            "The bill balance changed; this payment is now larger than what is owed."
        )
    if payment.supplier_bank_account_id:
        current = db.get_one(SupplierBankAccount, payment.supplier_bank_account_id)
        if current.status != "active":
            raise ConflictError(
                "The supplier's bank details changed after this payment was prepared."
            )
    s = settings_row(db)
    assert s.payable_account_id is not None  # nosec B101 - bill was posted, so it is configured
    cleared = money(payment.amount * (bill.fx_rate or Decimal(1)))
    paid = money(payment.amount * payment.fx_rate)
    lines = [
        Line(
            s.payable_account_id,
            "debit",
            payment.amount,
            payment.currency,
            bill.fx_rate or Decimal(1),
            f"Settles {bill.number}",
            "supplier",
            bill.supplier_id,
            functional=cleared,
        ),
        Line(
            payment.bank_account_id,
            "credit",
            payment.amount,
            payment.currency,
            payment.fx_rate,
            "Supplier payment",
            functional=paid,
        ),
    ]
    difference = paid - cleared  # paying more in functional terms is a loss
    if difference:
        if s.fx_gain_loss_account_id is None:
            raise FinanceRuleError("Set the exchange gain/loss account first.")
        lines.append(
            Line(
                s.fx_gain_loss_account_id,
                "debit" if difference > 0 else "credit",
                abs(difference),
                posting.functional_currency(db),
                Decimal(1),
                "Realised exchange difference",
            )
        )
    payment.number = posting.next_number(db, "PAY", payment.payment_date)
    entry = posting.post_entry(
        db,
        entry_date=payment.payment_date,
        description=f"Payment {payment.number} for {bill.number}",
        source_type="payment",
        source_id=payment.id,
        lines=lines,
        actor=payment.prepared_by,
        posted_by=request.decided_by,
        approval_id=request.id,
    )
    payment.status = "posted"
    payment.journal_id = entry.id
    bill.amount_paid += payment.amount
    bill.status = "paid" if bill.amount_paid >= bill.total else "partially_paid"


def payments_out(db: Session, rows: list[Payment]) -> list[schemas.PaymentOut]:
    if not rows:
        return []
    bills = dict(
        db.execute(select(Bill.id, Bill.number).where(Bill.id.in_({r.bill_id for r in rows})))
        .tuples()
        .all()
    )
    suppliers = dict(
        db.execute(
            select(Supplier.id, Supplier.name).where(Supplier.id.in_({r.supplier_id for r in rows}))
        )
        .tuples()
        .all()
    )
    endings = dict(
        db.execute(
            select(SupplierBankAccount.id, SupplierBankAccount.account_last4).where(
                SupplierBankAccount.id.in_({r.supplier_bank_account_id for r in rows} - {None})
            )
        )
        .tuples()
        .all()
    )
    return [
        schemas.PaymentOut(
            id=r.id,
            number=r.number,
            bill_id=r.bill_id,
            bill_number=bills.get(r.bill_id),
            supplier_id=r.supplier_id,
            supplier_name=suppliers.get(r.supplier_id, ""),
            payee_account_ending=endings.get(r.supplier_bank_account_id)
            if r.supplier_bank_account_id
            else None,
            payment_date=r.payment_date,
            currency=r.currency,
            fx_rate=r.fx_rate,
            amount=r.amount,
            method=r.method,
            reference=r.reference,
            status=r.status,
            journal_id=r.journal_id,
        )
        for r in rows
    ]


# --- Bank reconciliation -------------------------------------------------------------------


def add_statement_line(
    db: Session, body: schemas.StatementLineIn, actor: uuid.UUID
) -> BankStatementLine:
    _account(db, body.bank_account_id, "bank")
    row = BankStatementLine(created_by=actor, **body.model_dump())
    db.add(row)
    db.flush()
    _audit(db, "statement_line.added", actor, "fin_statement_line", row.id)
    return row


def match_statement_line(
    db: Session, row: BankStatementLine, journal_line_id: uuid.UUID, actor: uuid.UUID
) -> BankStatementLine:
    if row.matched_line_id:
        raise ConflictError("This statement line is already matched.")
    line = db.get(JournalLine, journal_line_id)
    if line is None or line.account_id != row.bank_account_id:
        raise FinanceRuleError("Match to a journal line on the same bank account.")
    entry = db.get_one(JournalEntry, line.entry_id)
    if entry.status not in ("posted", "reversed"):
        raise FinanceRuleError("Only posted journal lines can be matched.")
    account = db.get_one(Account, row.bank_account_id)
    if account.currency and account.currency != posting.functional_currency(db):
        signed = line.amount if line.debit > 0 else -line.amount
    else:
        signed = line.debit - line.credit
    if signed != row.amount:
        raise FinanceRuleError(f"Amounts differ: statement {row.amount}, ledger {signed}.")
    if db.execute(
        select(BankStatementLine.id).where(BankStatementLine.matched_line_id == line.id)
    ).first():
        raise ConflictError("That ledger line is already matched to another statement line.")
    row.matched_line_id = line.id
    row.matched_by = actor
    row.matched_at = posting.now()
    _audit(db, "statement_line.matched", actor, "fin_statement_line", row.id)
    return row


for _subject, _handler in (
    (JOURNAL_SUBJECT, _apply_journal_decision),
    (REVERSAL_SUBJECT, _apply_reversal_decision),
    (CREDIT_SUBJECT, _apply_credit_decision),
    (PAYMENT_SUBJECT, _apply_payment_decision),
):
    approvals.register_handler(_subject, _handler)
