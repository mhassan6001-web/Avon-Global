"""Financial reports computed from posted journal lines only.

Posted and later-reversed entries both count: a reversal is itself a posted
entry, so the pair nets to zero. Drafts, pending and rejected entries never
count. Nothing here estimates or forecasts.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.modules.crm.models import Customer, Opportunity
from app.modules.procurement.models import Supplier

from . import posting, schemas
from .models import (
    Account,
    BankStatementLine,
    Bill,
    Invoice,
    InvoiceLine,
    JournalEntry,
    JournalLine,
    Receipt,
)

POSTED = ("posted", "reversed")


def _balances(
    db: Session, *, date_from: date | None = None, date_to: date
) -> list[tuple[Account, Decimal, Decimal]]:
    stmt = (
        select(
            Account,
            func.coalesce(func.sum(JournalLine.debit), 0),
            func.coalesce(func.sum(JournalLine.credit), 0),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(JournalEntry.status.in_(POSTED), JournalEntry.entry_date <= date_to)
        .group_by(Account.id)
        .order_by(Account.code)
    )
    if date_from:
        stmt = stmt.where(JournalEntry.entry_date >= date_from)
    return [(a, Decimal(d), Decimal(c)) for a, d, c in db.execute(stmt).all()]


def _row(account: Account, debit: Decimal, credit: Decimal) -> schemas.ReportRow:
    natural_debit = account.type in ("asset", "expense")
    return schemas.ReportRow(
        account_id=account.id,
        code=account.code,
        name=account.name,
        type=account.type,
        subtype=account.subtype,
        debit=debit,
        credit=credit,
        balance=(debit - credit) if natural_debit else (credit - debit),
    )


def trial_balance(db: Session, as_of: date) -> schemas.TrialBalance:
    rows = [_row(a, d, c) for a, d, c in _balances(db, date_to=as_of)]
    total_debit = sum((r.debit for r in rows), Decimal(0))
    total_credit = sum((r.credit for r in rows), Decimal(0))
    return schemas.TrialBalance(
        as_of=as_of,
        functional_currency=posting.functional_currency(db),
        rows=rows,
        total_debit=total_debit,
        total_credit=total_credit,
        balanced=total_debit == total_credit,
    )


def profit_and_loss(db: Session, date_from: date, date_to: date) -> schemas.ProfitAndLoss:
    rows = [_row(a, d, c) for a, d, c in _balances(db, date_from=date_from, date_to=date_to)]
    income = [r for r in rows if r.type == "income"]
    expenses = [r for r in rows if r.type == "expense"]
    total_income = sum((r.balance for r in income), Decimal(0))
    total_expenses = sum((r.balance for r in expenses), Decimal(0))
    return schemas.ProfitAndLoss(
        date_from=date_from,
        date_to=date_to,
        functional_currency=posting.functional_currency(db),
        income=income,
        expenses=expenses,
        total_income=total_income,
        total_expenses=total_expenses,
        net_profit=total_income - total_expenses,
        basis="Accrual basis from posted journals. Not reviewed by an accountant.",
    )


def balance_sheet(db: Session, as_of: date) -> schemas.BalanceSheet:
    rows = [_row(a, d, c) for a, d, c in _balances(db, date_to=as_of)]
    assets = [r for r in rows if r.type == "asset"]
    liabilities = [r for r in rows if r.type == "liability"]
    equity = [r for r in rows if r.type == "equity"]
    earnings = sum((r.balance for r in rows if r.type == "income"), Decimal(0)) - sum(
        (r.balance for r in rows if r.type == "expense"), Decimal(0)
    )
    total_assets = sum((r.balance for r in assets), Decimal(0))
    total_le = (
        sum((r.balance for r in liabilities), Decimal(0))
        + sum((r.balance for r in equity), Decimal(0))
        + earnings
    )
    return schemas.BalanceSheet(
        as_of=as_of,
        functional_currency=posting.functional_currency(db),
        assets=assets,
        liabilities=liabilities,
        equity=equity,
        current_earnings=earnings,
        total_assets=total_assets,
        total_liabilities_and_equity=total_le,
        balanced=total_assets == total_le,
    )


def _bucket(days: int) -> str:
    if days <= 0:
        return "current"
    if days <= 30:
        return "days_1_30"
    if days <= 60:
        return "days_31_60"
    if days <= 90:
        return "days_61_90"
    return "days_over_90"


def ageing(db: Session, kind: str, as_of: date) -> schemas.Ageing:
    """Outstanding documents by days past due, in each document's own currency."""
    totals: dict[tuple[uuid.UUID, str], dict[str, Decimal]] = defaultdict(
        lambda: defaultdict(Decimal)
    )
    names: dict[uuid.UUID, str] = {}
    if kind == "receivable":
        invoices = db.execute(
            select(Invoice, Customer.name)
            .join(Customer, Customer.id == Invoice.customer_id)
            .where(Invoice.status.in_(("issued", "partially_paid")), Invoice.issue_date <= as_of)
        ).all()
        for inv, name in invoices:
            left = inv.total - inv.amount_paid - inv.amount_credited
            if left > 0:
                names[inv.customer_id] = name
                totals[(inv.customer_id, inv.currency)][_bucket((as_of - inv.due_date).days)] += (
                    left
                )
    else:
        bills = db.execute(
            select(Bill, Supplier.name)
            .join(Supplier, Supplier.id == Bill.supplier_id)
            .where(Bill.status.in_(("posted", "partially_paid")), Bill.bill_date <= as_of)
        ).all()
        for bill, name in bills:
            left = bill.total - bill.amount_paid
            if left > 0:
                names[bill.supplier_id] = name
                totals[(bill.supplier_id, bill.currency)][
                    _bucket((as_of - bill.due_date).days)
                ] += left
    rows = [
        schemas.AgeingRow(
            party_id=party,
            party_name=names[party],
            currency=currency,
            current=b["current"],
            days_1_30=b["days_1_30"],
            days_31_60=b["days_31_60"],
            days_61_90=b["days_61_90"],
            days_over_90=b["days_over_90"],
            total=sum(b.values(), Decimal(0)),
        )
        for (party, currency), b in sorted(totals.items(), key=lambda kv: names[kv[0][0]])
    ]
    return schemas.Ageing(kind=kind, as_of=as_of, rows=rows)


def cashbook(
    db: Session, account_id: uuid.UUID, date_from: date, date_to: date
) -> schemas.Cashbook:
    account = db.get(Account, account_id)
    if account is None or account.subtype != "bank":
        raise NotFoundError("Bank account not found.")
    foreign = bool(account.currency and account.currency != posting.functional_currency(db))
    signed = (
        case((JournalLine.debit > 0, JournalLine.amount), else_=-JournalLine.amount)
        if foreign
        else JournalLine.debit - JournalLine.credit
    )
    opening = db.execute(
        select(func.coalesce(func.sum(signed), 0))
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalLine.account_id == account_id,
            JournalEntry.status.in_(POSTED),
            JournalEntry.entry_date < date_from,
        )
    ).scalar_one()
    matched = set(
        db.execute(
            select(BankStatementLine.matched_line_id).where(
                BankStatementLine.bank_account_id == account_id,
                BankStatementLine.matched_line_id.is_not(None),
            )
        ).scalars()
    )
    rows = db.execute(
        select(JournalLine, JournalEntry)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalLine.account_id == account_id,
            JournalEntry.status.in_(POSTED),
            JournalEntry.entry_date >= date_from,
            JournalEntry.entry_date <= date_to,
        )
        .order_by(JournalEntry.entry_date, JournalEntry.number, JournalLine.line_no)
    ).all()
    balance = Decimal(opening)
    out = []
    for line, entry in rows:
        value = (
            (line.amount if line.debit > 0 else -line.amount)
            if foreign
            else line.debit - line.credit
        )
        balance += value
        out.append(
            schemas.CashbookRow(
                entry_date=entry.entry_date,
                number=entry.number,
                description=line.description or entry.description,
                money_in=value if value > 0 else Decimal(0),
                money_out=-value if value < 0 else Decimal(0),
                balance=balance,
                line_id=line.id,
                reconciled=line.id in matched,
            )
        )
    return schemas.Cashbook(
        account_id=account.id,
        account_name=f"{account.code} {account.name}",
        currency=account.currency or posting.functional_currency(db),
        opening_balance=Decimal(opening),
        rows=out,
        closing_balance=balance,
    )


def _month_start(d: date) -> date:
    return d.replace(day=1)


def overview(db: Session, today: date) -> schemas.FinanceOverview:
    """Director KPIs. Revenue invoiced and cash collected are reported separately."""
    currency = posting.functional_currency(db)
    has_records = (
        db.execute(select(JournalEntry.id).where(JournalEntry.status.in_(POSTED)).limit(1)).first()
        is not None
    )
    cash = db.execute(
        select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0))
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(Account.subtype == "bank", JournalEntry.status.in_(POSTED))
    ).scalar_one()
    debtors = db.execute(
        select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0))
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(Account.subtype == "receivable", JournalEntry.status.in_(POSTED))
    ).scalar_one()
    creditors = db.execute(
        select(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), 0))
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(Account.subtype == "payable", JournalEntry.status.in_(POSTED))
    ).scalar_one()

    first = _month_start(today)
    months: list[date] = []
    cursor = first
    for _ in range(12):
        months.append(cursor)
        cursor = _month_start(cursor - timedelta(days=1))
    months.reverse()
    invoiced: dict[str, Decimal] = defaultdict(Decimal)
    for issue_date, net, rate in db.execute(
        select(Invoice.issue_date, Invoice.subtotal, Invoice.fx_rate).where(
            Invoice.status != "draft", Invoice.issue_date >= months[0]
        )
    ).all():
        invoiced[issue_date.strftime("%Y-%m")] += posting.money(net * (rate or 1))
    collected: dict[str, Decimal] = defaultdict(Decimal)
    for receipt_date, amount, rate in db.execute(
        select(Receipt.receipt_date, Receipt.amount, Receipt.fx_rate).where(
            Receipt.receipt_date >= months[0]
        )
    ).all():
        collected[receipt_date.strftime("%Y-%m")] += posting.money(amount * rate)
    by_division: dict[str, Decimal] = defaultdict(Decimal)
    for division, net, rate in db.execute(
        select(Opportunity.division, InvoiceLine.net, Invoice.fx_rate)
        .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
        .join(Opportunity, Opportunity.id == Invoice.opportunity_id, isouter=True)
        .where(Invoice.status != "draft", Invoice.issue_date >= date(today.year, 1, 1))
    ).all():
        by_division[division or "unassigned"] += posting.money(net * (rate or 1))
    key = today.strftime("%Y-%m")
    return schemas.FinanceOverview(
        has_records=has_records,
        functional_currency=currency,
        cash_position=Decimal(cash),
        invoiced_this_month=invoiced.get(key, Decimal(0)),
        collected_this_month=collected.get(key, Decimal(0)),
        debtors_outstanding=Decimal(debtors),
        creditors_outstanding=Decimal(creditors),
        months=[
            schemas.MonthFigure(
                month=m.strftime("%Y-%m"),
                invoiced=invoiced.get(m.strftime("%Y-%m"), Decimal(0)),
                collected=collected.get(m.strftime("%Y-%m"), Decimal(0)),
            )
            for m in months
        ],
        revenue_by_division=dict(by_division),
    )
