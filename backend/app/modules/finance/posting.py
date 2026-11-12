"""Double-entry posting engine.

Every automatic and manual posting goes through :func:`post_entry`, which
converts each line to the functional currency, checks the entry balances,
assigns a gap-free number and marks it posted. The database re-checks the
balance and refuses any later change to a posted entry (migration 0007).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError
from app.modules.organisation.models import OrganisationProfile

from .models import Account, ExchangeRate, JournalEntry, JournalLine, Period

CENT = Decimal("0.01")
# Largest automatic rounding adjustment allowed when converting several
# foreign-currency lines; anything larger is an error, never absorbed.
MAX_ROUNDING = Decimal("0.05")


class FinanceRuleError(AppError):
    status_code = 422
    code = "finance_rule"


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def now() -> datetime:
    return datetime.now(UTC)


def functional_currency(db: Session) -> str:
    value = db.execute(select(OrganisationProfile.functional_currency).limit(1)).scalar()
    return value or "MWK"


def next_number(db: Session, series: str, on: date) -> str:
    """Gap-free number for ``series`` in the year of ``on`` (row locked until commit)."""
    key = f"{series}-{on.year}"
    db.execute(
        text(
            "INSERT INTO fin_counters (key, next_value) VALUES (:k, 1) ON CONFLICT (key) DO NOTHING"
        ),
        {"k": key},
    )
    value = db.execute(
        text("SELECT next_value FROM fin_counters WHERE key = :k FOR UPDATE"), {"k": key}
    ).scalar_one()
    db.execute(
        text("UPDATE fin_counters SET next_value = next_value + 1 WHERE key = :k"), {"k": key}
    )
    return f"{series}-{on.year}-{int(value):05d}"


def rate_for(db: Session, currency: str, on: date, explicit: Decimal | None = None) -> Decimal:
    """Functional units per 1 unit of ``currency`` on ``on``.

    The functional currency is always 1. Otherwise an explicit rate wins;
    failing that, the latest recorded rate on or before the date. A missing
    rate is an error: no rate is ever assumed.
    """
    if currency == functional_currency(db):
        return Decimal(1)
    if explicit is not None:
        if explicit <= 0:
            raise FinanceRuleError("The exchange rate must be greater than zero.")
        return explicit
    rate = db.execute(
        select(ExchangeRate.rate)
        .where(ExchangeRate.currency == currency, ExchangeRate.rate_date <= on)
        .order_by(ExchangeRate.rate_date.desc())
        .limit(1)
    ).scalar()
    if rate is None:
        raise FinanceRuleError(
            f"No {currency} exchange rate is recorded on or before {on.isoformat()}. "
            "Add one in Finance settings first."
        )
    return Decimal(rate)


def open_period(db: Session, on: date) -> Period:
    period = db.execute(
        select(Period).where(Period.start_date <= on, Period.end_date >= on)
    ).scalar_one_or_none()
    if period is None:
        raise FinanceRuleError(f"No financial period covers {on.isoformat()}. Create it first.")
    if period.status != "open":
        raise ConflictError(f"The period {period.name} is closed. Nothing can be posted into it.")
    return period


@dataclass(frozen=True)
class Line:
    account_id: uuid.UUID
    side: Literal["debit", "credit"]
    amount: Decimal  # transaction currency
    currency: str
    fx_rate: Decimal
    description: str | None = None
    party_type: str | None = None
    party_id: uuid.UUID | None = None
    functional: Decimal | None = None  # override (e.g. clearing AR at the invoice rate)


def _check_accounts(db: Session, lines: list[Line]) -> None:
    ids = {line.account_id for line in lines}
    found = {a.id: a for a in db.execute(select(Account).where(Account.id.in_(ids))).scalars()}
    for line in lines:
        account = found.get(line.account_id)
        if account is None:
            raise FinanceRuleError("A line uses an account that does not exist.")
        if not account.is_active:
            raise FinanceRuleError(f"Account {account.code} is inactive.")
        if account.currency and account.currency != line.currency:
            raise FinanceRuleError(
                f"Account {account.code} only accepts {account.currency} transactions."
            )


def prepare_lines(lines: list[Line]) -> list[tuple[Line, Decimal]]:
    """Convert to functional currency and absorb sub-cent conversion rounding.

    Returns (line, functional amount). Raises if the entry does not balance.
    """
    if len(lines) < 2:
        raise FinanceRuleError("A journal entry needs at least two lines.")
    out: list[tuple[Line, Decimal]] = []
    for line in lines:
        if line.amount <= 0:
            raise FinanceRuleError("Every journal line must have a positive amount.")
        functional = (
            line.functional if line.functional is not None else money(line.amount * line.fx_rate)
        )
        if functional <= 0:
            raise FinanceRuleError("A line converts to zero in the functional currency.")
        out.append((line, functional))
    debit = sum((f for line, f in out if line.side == "debit"), Decimal(0))
    credit = sum((f for line, f in out if line.side == "credit"), Decimal(0))
    diff = debit - credit
    if diff == 0:
        return out
    foreign = any(line.fx_rate != 1 and line.functional is None for line, _ in out)
    if not foreign or abs(diff) > MAX_ROUNDING:
        raise FinanceRuleError(f"The entry does not balance: debits {debit} and credits {credit}.")
    # Put the rounding difference on the largest line of the lighter side.
    side = "credit" if diff > 0 else "debit"
    index = max(
        (i for i, (line, _) in enumerate(out) if line.side == side), key=lambda i: out[i][1]
    )
    line, functional = out[index]
    out[index] = (line, functional + abs(diff))
    return out


def post_entry(
    db: Session,
    *,
    entry_date: date,
    description: str,
    source_type: str,
    source_id: uuid.UUID | None,
    lines: list[Line],
    actor: uuid.UUID,
    posted_by: uuid.UUID | None = None,
    approval_id: uuid.UUID | None = None,
    reverses_id: uuid.UUID | None = None,
) -> JournalEntry:
    period = open_period(db, entry_date)
    _check_accounts(db, lines)
    prepared = prepare_lines(lines)
    entry = JournalEntry(
        entry_date=entry_date,
        period_id=period.id,
        description=description[:300],
        source_type=source_type,
        source_id=source_id,
        status="draft",
        approval_id=approval_id,
        reverses_id=reverses_id,
        created_by=actor,
    )
    db.add(entry)
    db.flush()
    write_lines(db, entry, prepared)
    finalise(db, entry, posted_by or actor)
    return entry


def write_lines(db: Session, entry: JournalEntry, prepared: list[tuple[Line, Decimal]]) -> None:
    for n, (line, functional) in enumerate(prepared, start=1):
        db.add(
            JournalLine(
                entry_id=entry.id,
                line_no=n,
                account_id=line.account_id,
                description=line.description,
                currency=line.currency,
                amount=money(line.amount),
                fx_rate=line.fx_rate,
                debit=functional if line.side == "debit" else Decimal(0),
                credit=functional if line.side == "credit" else Decimal(0),
                party_type=line.party_type,
                party_id=line.party_id,
            )
        )
    db.flush()


def finalise(db: Session, entry: JournalEntry, posted_by: uuid.UUID) -> None:
    """Number and post an entry whose lines are written (DB re-checks the balance)."""
    open_period(db, entry.entry_date)
    entry.number = next_number(db, "JE", entry.entry_date)
    entry.status = "posted"
    entry.posted_at = now()
    entry.posted_by = posted_by
    db.flush()


def reverse_entry(
    db: Session, entry: JournalEntry, on: date, actor: uuid.UUID, reason: str
) -> JournalEntry:
    if entry.status != "posted":
        raise ConflictError("Only a posted entry that has not been reversed can be reversed.")
    if on < entry.entry_date:
        raise FinanceRuleError("A reversal cannot be dated before the original entry.")
    original = list(
        db.execute(
            select(JournalLine)
            .where(JournalLine.entry_id == entry.id)
            .order_by(JournalLine.line_no)
        ).scalars()
    )
    lines = [
        Line(
            account_id=line.account_id,
            side="credit" if line.debit > 0 else "debit",
            amount=line.amount,
            currency=line.currency,
            fx_rate=line.fx_rate,
            description=line.description,
            party_type=line.party_type,
            party_id=line.party_id,
            functional=line.debit if line.debit > 0 else line.credit,
        )
        for line in original
    ]
    reversal = post_entry(
        db,
        entry_date=on,
        description=f"Reversal of {entry.number}: {reason}",
        source_type="reversal",
        source_id=entry.id,
        lines=lines,
        actor=actor,
        reverses_id=entry.id,
    )
    entry.status = "reversed"
    entry.reversed_by_id = reversal.id
    db.flush()
    return reversal
