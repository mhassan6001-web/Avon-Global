"""Perpetual inventory accounting (Stage 18).

Every stock movement can post a balanced journal in the same database
transaction, valued at the movement's own unit cost (weighted average):

| Movement            | Debit            | Credit           |
|---------------------|------------------|------------------|
| opening             | Inventory        | Opening balance  |
| receipt (goods in)  | Inventory        | Goods received not invoiced |
| dispatch (delivery) | Cost of sales    | Inventory        |
| return_in           | Inventory        | Cost of sales    |
| adjustment (+)      | Inventory        | Stock adjustments|
| adjustment (-), damage | Stock adjustments | Inventory     |
| transfer in / out   | none (same inventory account)       |

Posting is OFF until the accounts are mapped and the reviewing accountant is
recorded. The valuation method must be approved by a qualified accountant
before it is switched on.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.platform.audit import service as audit

from . import posting
from .models import Account, JournalEntry, JournalLine, StockPosting

ACCOUNT_FIELDS = (
    "inventory_account_id",
    "grni_account_id",
    "cogs_account_id",
    "adjustment_account_id",
    "opening_account_id",
)
NOT_POSTED = ("transfer_in", "transfer_out")


class StockPostingIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    enabled: bool = False
    inventory_account_id: uuid.UUID | None = None
    grni_account_id: uuid.UUID | None = None
    cogs_account_id: uuid.UUID | None = None
    adjustment_account_id: uuid.UUID | None = None
    opening_account_id: uuid.UUID | None = None
    reviewed_by_name: str | None = Field(default=None, min_length=3, max_length=200)
    reviewed_on: date | None = None


class StockPostingOut(StockPostingIn):
    valuation_method: str = "weighted_average"


class StockReconciliation(BaseModel):
    as_of: date
    posting_enabled: bool
    functional_currency: str
    stock_value: Decimal  # from the stock movement ledger
    ledger_balance: Decimal | None  # inventory account in the general ledger
    difference: Decimal | None
    movements_not_posted: int  # value-bearing movements with no journal
    reconciled: bool


def get_config(db: Session) -> StockPosting | None:
    return db.get(StockPosting, 1)


def config_out(db: Session) -> StockPostingOut:
    row = get_config(db)
    if row is None:
        return StockPostingOut()
    return StockPostingOut.model_validate(row, from_attributes=True)


def save_config(db: Session, body: StockPostingIn, actor: uuid.UUID) -> StockPostingOut:
    ids = [getattr(body, f) for f in ACCOUNT_FIELDS]
    chosen = [i for i in ids if i is not None]
    accounts = {
        a.id: a for a in db.execute(select(Account).where(Account.id.in_(chosen))).scalars()
    }
    for field in ACCOUNT_FIELDS:
        account_id = getattr(body, field)
        if account_id is None:
            continue
        account = accounts.get(account_id)
        if account is None or not account.is_active:
            raise posting.FinanceRuleError("Choose active accounts from the chart of accounts.")
    inventory = accounts.get(body.inventory_account_id) if body.inventory_account_id else None
    if inventory is not None and inventory.type != "asset":
        raise posting.FinanceRuleError("The inventory account must be an asset account.")
    cogs = accounts.get(body.cogs_account_id) if body.cogs_account_id else None
    if cogs is not None and cogs.type != "expense":
        raise posting.FinanceRuleError("The cost of sales account must be an expense account.")
    if body.enabled:
        if len(chosen) != len(ACCOUNT_FIELDS):
            raise posting.FinanceRuleError("Map all five accounts before switching posting on.")
        if not body.reviewed_by_name or not body.reviewed_on:
            raise posting.FinanceRuleError(
                "Record the accountant who approved the valuation method, and the date, "
                "before switching posting on."
            )
    row = get_config(db)
    before = config_out(db).model_dump(mode="json")
    if row is None:
        row = StockPosting(id=1)
        db.add(row)
    for name, value in body.model_dump().items():
        setattr(row, name, value)
    row.updated_by, row.updated_at = actor, posting.now()
    db.flush()
    audit.record(
        db,
        action="finance.stock_posting.changed",
        actor_id=actor,
        target_type="fin_stock_posting",
        target_id="1",
        details={"before": before, "after": body.model_dump(mode="json")},
    )
    return config_out(db)


def post_movement(db: Session, movement: Any, actor: uuid.UUID) -> JournalEntry | None:
    """Post the journal for one stock movement, if posting is switched on.

    Raises (and so refuses the movement) when the period is closed: stock and
    ledger must never drift apart.
    """
    cfg = get_config(db)
    if cfg is None or not cfg.enabled or movement.kind in NOT_POSTED:
        return None
    value = posting.money(abs(movement.quantity) * movement.unit_cost)
    if value == 0:
        return None
    inventory = cfg.inventory_account_id
    incoming = movement.quantity > 0
    other = {
        "opening": cfg.opening_account_id,
        "receipt": cfg.grni_account_id,
        "dispatch": cfg.cogs_account_id,
        "return_in": cfg.cogs_account_id,
        "adjustment": cfg.adjustment_account_id,
        "damage": cfg.adjustment_account_id,
    }[movement.kind]
    if inventory is None or other is None:  # the database constraint prevents this
        raise posting.FinanceRuleError("Stock posting accounts are not fully mapped.")
    debit, credit = (inventory, other) if incoming else (other, inventory)
    currency = posting.functional_currency(db)
    text_ = f"Stock {movement.kind.replace('_', ' ')}" + (
        f": {movement.reference}" if movement.reference else ""
    )
    return posting.post_entry(
        db,
        entry_date=movement.movement_date,
        description=text_,
        source_type="stock",
        source_id=movement.id,
        lines=[
            posting.Line(debit, "debit", value, currency, Decimal(1), text_),
            posting.Line(credit, "credit", value, currency, Decimal(1), text_),
        ],
        actor=actor,
    )


def reconciliation(db: Session, as_of: date) -> StockReconciliation:
    """Stock ledger value against the inventory account, as of a date."""
    from app.modules.inventory.models import StockMovement

    cfg = get_config(db)
    stock_value = posting.money(
        Decimal(
            db.execute(
                select(
                    func.coalesce(func.sum(StockMovement.quantity * StockMovement.unit_cost), 0)
                ).where(StockMovement.movement_date <= as_of)
            ).scalar_one()
        )
    )
    posted_ids = select(JournalEntry.source_id).where(JournalEntry.source_type == "stock")
    not_posted = db.execute(
        select(func.count())
        .select_from(StockMovement)
        .where(
            StockMovement.movement_date <= as_of,
            StockMovement.kind.not_in(NOT_POSTED),
            StockMovement.quantity * StockMovement.unit_cost != 0,
            StockMovement.id.not_in(posted_ids),
        )
    ).scalar_one()
    ledger: Decimal | None = None
    if cfg is not None and cfg.inventory_account_id is not None:
        debit, credit = db.execute(
            select(
                func.coalesce(func.sum(JournalLine.debit), 0),
                func.coalesce(func.sum(JournalLine.credit), 0),
            )
            .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
            .where(
                JournalLine.account_id == cfg.inventory_account_id,
                JournalEntry.status.in_(("posted", "reversed")),
                JournalEntry.entry_date <= as_of,
            )
        ).one()
        ledger = posting.money(Decimal(debit) - Decimal(credit))
    difference = None if ledger is None else stock_value - ledger
    return StockReconciliation(
        as_of=as_of,
        posting_enabled=bool(cfg and cfg.enabled),
        functional_currency=posting.functional_currency(db),
        stock_value=stock_value,
        ledger_balance=ledger,
        difference=difference,
        movements_not_posted=not_posted,
        reconciled=difference == 0 and not_posted == 0,
    )
