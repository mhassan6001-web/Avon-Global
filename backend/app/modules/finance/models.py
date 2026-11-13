"""Finance (Stage 7): chart of accounts, periods, exchange rates, tax codes,
double-entry journals, invoices, receipts, credit notes, supplier bills,
payments and bank-statement lines.

Integrity rules enforced by the database (migration 0007), not only by code:
- a posted journal entry and its lines can never be updated or deleted,
  except that a posted entry may be marked ``reversed`` once;
- an entry can only become ``posted`` if its functional debits equal its
  functional credits and are greater than zero;
- each journal line is either a debit or a credit, never both or neither.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

CURRENCY_CHECK = "currency IN ('MWK', 'USD', 'ZAR', 'ZMW')"
ACCOUNT_TYPES = ("asset", "liability", "equity", "income", "expense")
SUBTYPES = (
    "bank",
    "receivable",
    "payable",
    "tax",
    "inventory",
    "fixed_asset",
    "other_asset",
    "other_liability",
    "equity",
    "retained_earnings",
    "revenue",
    "cost_of_sales",
    "expense",
    "fx_gain_loss",
)
MONEY = Numeric(18, 2)
RATE = Numeric(18, 6)


class Account(TimestampMixin, Base):
    __tablename__ = "fin_accounts"
    __table_args__ = (
        CheckConstraint(
            "type IN ('asset', 'liability', 'equity', 'income', 'expense')", name="type_valid"
        ),
        CheckConstraint("currency IS NULL OR " + CURRENCY_CHECK, name="currency_valid"),
        CheckConstraint("code ~ '^[0-9A-Z.\\-]{2,20}$'", name="code_format"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    subtype: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(3))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class Period(TimestampMixin, Base):
    __tablename__ = "fin_periods"
    __table_args__ = (
        CheckConstraint("start_date <= end_date", name="dates_ordered"),
        CheckConstraint("status IN ('open', 'closed')", name="status_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(8), nullable=False, server_default="open")
    closed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExchangeRate(Base):
    """Functional-currency units per 1 unit of ``currency`` on ``rate_date``.
    Rates are history: they are added, never edited or deleted."""

    __tablename__ = "fin_exchange_rates"
    __table_args__ = (
        CheckConstraint(CURRENCY_CHECK, name="currency_valid"),
        CheckConstraint("rate > 0", name="rate_positive"),
        UniqueConstraint("currency", "rate_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    rate: Mapped[Decimal] = mapped_column(RATE, nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class TaxCode(TimestampMixin, Base):
    """Configured by Finance and reviewed by the accountant. No rate is built in."""

    __tablename__ = "fin_tax_codes"
    __table_args__ = (
        CheckConstraint("rate_pct >= 0 AND rate_pct <= 100", name="rate_range"),
        CheckConstraint("kind IN ('output', 'input')", name="kind_valid"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from", name="dates_ordered"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    rate_pct: Mapped[Decimal] = mapped_column(Numeric(7, 3), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fin_accounts.id"), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class Settings(TimestampMixin, Base):
    """Control accounts used by automatic postings (single row, id = 1)."""

    __tablename__ = "fin_settings"
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receivable_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_accounts.id"))
    payable_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_accounts.id"))
    fx_gain_loss_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_accounts.id"))
    accountant_reviewed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))


class Counter(Base):
    """Gap-free document numbering: one row per series and year, locked FOR UPDATE."""

    __tablename__ = "fin_counters"

    key: Mapped[str] = mapped_column(String(30), primary_key=True)
    next_value: Mapped[int] = mapped_column(Integer, nullable=False)


class JournalEntry(TimestampMixin, Base):
    __tablename__ = "fin_journal_entries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'awaiting_approval', 'posted', 'reversed', 'rejected')",
            name="status_valid",
        ),
        CheckConstraint(
            "source_type IN ('manual', 'invoice', 'receipt', 'credit_note', 'bill', 'payment', "
            "'reversal', 'stock')",
            name="source_valid",
        ),
        CheckConstraint(
            "status NOT IN ('posted', 'reversed') "
            "OR (number IS NOT NULL AND posted_at IS NOT NULL)",
            name="posted_has_number",
        ),
        Index("ix_fin_journal_entries_date", "entry_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    number: Mapped[str | None] = mapped_column(String(24), unique=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fin_periods.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    source_type: Mapped[str] = mapped_column(String(12), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    approval_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sys_approval_requests.id"))
    reverses_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_journal_entries.id"))
    reversed_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class JournalLine(Base):
    __tablename__ = "fin_journal_lines"
    __table_args__ = (
        CheckConstraint(CURRENCY_CHECK, name="currency_valid"),
        CheckConstraint("amount >= 0 AND debit >= 0 AND credit >= 0", name="non_negative"),
        CheckConstraint("(debit = 0) <> (credit = 0)", name="debit_xor_credit"),
        CheckConstraint("fx_rate > 0", name="rate_positive"),
        CheckConstraint(
            "party_type IS NULL OR party_type IN ('customer', 'supplier')", name="party_valid"
        ),
        UniqueConstraint("entry_id", "line_no"),
        Index("ix_fin_journal_lines_account", "account_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fin_journal_entries.id"), nullable=False, index=True
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fin_accounts.id"), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)  # transaction currency
    fx_rate: Mapped[Decimal] = mapped_column(RATE, nullable=False)
    debit: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    credit: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    party_type: Mapped[str | None] = mapped_column(String(10))
    party_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class Invoice(TimestampMixin, Base):
    __tablename__ = "fin_invoices"
    __table_args__ = (
        CheckConstraint(CURRENCY_CHECK, name="currency_valid"),
        CheckConstraint(
            "status IN ('draft', 'issued', 'partially_paid', 'paid', 'credited')",
            name="status_valid",
        ),
        CheckConstraint("due_date >= issue_date", name="due_after_issue"),
        CheckConstraint(
            "amount_paid >= 0 AND amount_credited >= 0 AND amount_paid + amount_credited <= total",
            name="settlement_within_total",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    number: Mapped[str | None] = mapped_column(String(24), unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crm_customers.id"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fx_rate: Mapped[Decimal | None] = mapped_column(RATE)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="draft")
    subtotal: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    tax_total: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    total: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    amount_paid: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    amount_credited: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text)
    journal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_journal_entries.id"))
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("crm_opportunities.id"))
    issued_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class InvoiceLine(Base):
    __tablename__ = "fin_invoice_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0 AND unit_price >= 0", name="amounts_valid"),
        UniqueConstraint("invoice_id", "line_no"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fin_invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fin_accounts.id"), nullable=False)
    tax_code_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_tax_codes.id"))
    net: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    tax: Mapped[Decimal] = mapped_column(MONEY, nullable=False)


class Receipt(TimestampMixin, Base):
    __tablename__ = "fin_receipts"
    __table_args__ = (
        CheckConstraint(CURRENCY_CHECK, name="currency_valid"),
        CheckConstraint("amount > 0", name="amount_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    number: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crm_customers.id"), nullable=False)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fx_rate: Mapped[Decimal] = mapped_column(RATE, nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fin_accounts.id"), nullable=False
    )
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120))
    journal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fin_journal_entries.id"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class ReceiptAllocation(Base):
    __tablename__ = "fin_receipt_allocations"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fin_receipts.id"), nullable=False, index=True
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fin_invoices.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)


class CreditNote(TimestampMixin, Base):
    __tablename__ = "fin_credit_notes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('awaiting_approval', 'posted', 'rejected')", name="status_valid"
        ),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("status <> 'posted' OR number IS NOT NULL", name="posted_has_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    number: Mapped[str | None] = mapped_column(String(24), unique=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fin_invoices.id"), nullable=False)
    credit_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)  # gross, invoice currency
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="awaiting_approval"
    )
    approval_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sys_approval_requests.id"))
    journal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_journal_entries.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class Bill(TimestampMixin, Base):
    __tablename__ = "fin_bills"
    __table_args__ = (
        CheckConstraint(CURRENCY_CHECK, name="currency_valid"),
        CheckConstraint(
            "status IN ('draft', 'posted', 'partially_paid', 'paid')", name="status_valid"
        ),
        CheckConstraint("due_date >= bill_date", name="due_after_bill"),
        CheckConstraint("amount_paid >= 0 AND amount_paid <= total", name="paid_within_total"),
        UniqueConstraint("supplier_id", "supplier_invoice_ref"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    number: Mapped[str | None] = mapped_column(String(24), unique=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prc_suppliers.id"), nullable=False)
    supplier_invoice_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    purchase_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prc_purchase_orders.id")
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fx_rate: Mapped[Decimal | None] = mapped_column(RATE)
    bill_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="draft")
    subtotal: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    tax_total: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    total: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    amount_paid: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    journal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_journal_entries.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class BillLine(Base):
    __tablename__ = "fin_bill_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0 AND unit_price >= 0", name="amounts_valid"),
        UniqueConstraint("bill_id", "line_no"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fin_bills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fin_accounts.id"), nullable=False)
    tax_code_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_tax_codes.id"))
    net: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    tax: Mapped[Decimal] = mapped_column(MONEY, nullable=False)


class Payment(TimestampMixin, Base):
    """An outgoing supplier payment. Prepared by Finance, approved by a different
    person, then recorded as paid. The system never moves money itself."""

    __tablename__ = "fin_payments"
    __table_args__ = (
        CheckConstraint(CURRENCY_CHECK, name="currency_valid"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            "status IN ('awaiting_approval', 'posted', 'rejected')", name="status_valid"
        ),
        CheckConstraint("status <> 'posted' OR number IS NOT NULL", name="posted_has_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    number: Mapped[str | None] = mapped_column(String(24), unique=True)
    bill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fin_bills.id"), nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prc_suppliers.id"), nullable=False)
    supplier_bank_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prc_supplier_bank_accounts.id")
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fx_rate: Mapped[Decimal] = mapped_column(RATE, nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fin_accounts.id"), nullable=False
    )
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="awaiting_approval"
    )
    approval_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sys_approval_requests.id"))
    journal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_journal_entries.id"))
    prepared_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class BankStatementLine(TimestampMixin, Base):
    """A line from the bank's statement, matched to a posted journal line."""

    __tablename__ = "fin_bank_statement_lines"
    __table_args__ = (CheckConstraint("amount <> 0", name="amount_non_zero"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fin_accounts.id"), nullable=False, index=True
    )
    statement_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120))
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)  # + money in, - money out
    matched_line_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fin_journal_lines.id"), unique=True
    )
    matched_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class StockPosting(Base):
    """Perpetual inventory accounting settings (one row).

    While ``enabled`` is off, stock movements update quantities and cost only.
    When on, every movement also posts a balanced journal in the same
    transaction. It can be switched on only after the accounts are mapped and
    the reviewing accountant is recorded.
    """

    __tablename__ = "fin_stock_posting"
    __table_args__ = (
        CheckConstraint("id = 1", name="single_row"),
        CheckConstraint("valuation_method IN ('weighted_average')", name="method_valid"),
        CheckConstraint(
            "NOT enabled OR (inventory_account_id IS NOT NULL AND grni_account_id IS NOT NULL "
            "AND cogs_account_id IS NOT NULL AND adjustment_account_id IS NOT NULL "
            "AND opening_account_id IS NOT NULL AND reviewed_by_name IS NOT NULL "
            "AND reviewed_on IS NOT NULL)",
            name="enabled_requires_setup",
        ),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    valuation_method: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="weighted_average"
    )
    inventory_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_accounts.id"))
    grni_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_accounts.id"))
    cogs_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_accounts.id"))
    adjustment_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_accounts.id"))
    opening_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fin_accounts.id"))
    reviewed_by_name: Mapped[str | None] = mapped_column(String(200))
    reviewed_on: Mapped[date | None] = mapped_column(Date)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
