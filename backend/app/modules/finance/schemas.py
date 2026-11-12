"""Finance request and response models. Money is ``Decimal`` end to end."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.crm.schemas import Currency

AccountType = Literal["asset", "liability", "equity", "income", "expense"]
Subtype = Literal[
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
]
SUBTYPE_TYPE: dict[str, str] = {
    "bank": "asset",
    "receivable": "asset",
    "inventory": "asset",
    "fixed_asset": "asset",
    "other_asset": "asset",
    "payable": "liability",
    "tax": "liability",
    "other_liability": "liability",
    "equity": "equity",
    "retained_earnings": "equity",
    "revenue": "income",
    "fx_gain_loss": "income",
    "cost_of_sales": "expense",
    "expense": "expense",
}
Money = Decimal
Method = Literal["bank_transfer", "cash", "cheque", "mobile_money", "card", "other"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AccountIn(_In):
    code: str = Field(pattern=r"^[0-9A-Z.\-]{2,20}$")
    name: str = Field(min_length=2, max_length=200)
    subtype: Subtype
    currency: Currency | None = None
    description: str | None = Field(default=None, max_length=2000)


class AccountPatch(_In):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    is_active: bool | None = None
    description: str | None = Field(default=None, max_length=2000)


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    type: str
    subtype: str
    currency: str | None
    is_active: bool
    description: str | None


class PeriodIn(_In):
    name: str = Field(min_length=3, max_length=40)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def _order(self) -> PeriodIn:
        if self.end_date < self.start_date:
            raise ValueError("The period must end on or after its start.")
        return self


class PeriodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    status: str
    closed_at: datetime | None


class RateIn(_In):
    currency: Currency
    rate_date: date
    rate: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    source: str = Field(min_length=2, max_length=200)


class RateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    currency: str
    rate_date: date
    rate: Decimal
    source: str
    created_at: datetime


class TaxCodeIn(_In):
    code: str = Field(pattern=r"^[A-Z0-9_\-]{2,20}$")
    name: str = Field(min_length=2, max_length=120)
    kind: Literal["output", "input"]
    rate_pct: Decimal = Field(ge=0, le=100, max_digits=7, decimal_places=3)
    account_id: uuid.UUID
    effective_from: date
    effective_to: date | None = None


class TaxCodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    kind: str
    rate_pct: Decimal
    account_id: uuid.UUID
    effective_from: date
    effective_to: date | None


class SettingsIn(_In):
    receivable_account_id: uuid.UUID | None = None
    payable_account_id: uuid.UUID | None = None
    fx_gain_loss_account_id: uuid.UUID | None = None


class SettingsOut(BaseModel):
    functional_currency: str
    receivable_account_id: uuid.UUID | None
    payable_account_id: uuid.UUID | None
    fx_gain_loss_account_id: uuid.UUID | None
    accountant_reviewed: bool
    ready_for_invoicing: bool
    ready_for_bills: bool
    missing: list[str]


class ManualLineIn(_In):
    account_id: uuid.UUID
    debit: Decimal = Field(default=Decimal(0), ge=0, max_digits=18, decimal_places=2)
    credit: Decimal = Field(default=Decimal(0), ge=0, max_digits=18, decimal_places=2)
    description: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _one_side(self) -> ManualLineIn:
        if (self.debit > 0) == (self.credit > 0):
            raise ValueError("Each line needs either a debit or a credit.")
        return self


class ManualJournalIn(_In):
    entry_date: date
    description: str = Field(min_length=3, max_length=300)
    lines: list[ManualLineIn] = Field(min_length=2, max_length=100)


class JournalLineOut(BaseModel):
    line_no: int
    account_id: uuid.UUID
    account_code: str
    account_name: str
    description: str | None
    currency: str
    amount: Decimal
    fx_rate: Decimal
    debit: Decimal
    credit: Decimal


class JournalOut(BaseModel):
    id: uuid.UUID
    number: str | None
    entry_date: date
    description: str
    source_type: str
    source_id: uuid.UUID | None
    status: str
    reverses_id: uuid.UUID | None
    reversed_by_id: uuid.UUID | None
    posted_at: datetime | None
    lines: list[JournalLineOut]


class ReversalIn(_In):
    entry_date: date
    reason: str = Field(min_length=3, max_length=500)


class DocLineIn(_In):
    description: str = Field(min_length=2, max_length=300)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=3)
    unit_price: Decimal = Field(ge=0, max_digits=18, decimal_places=4)
    account_id: uuid.UUID
    tax_code_id: uuid.UUID | None = None


class InvoiceIn(_In):
    customer_id: uuid.UUID
    currency: Currency = "MWK"
    issue_date: date
    due_date: date
    notes: str | None = Field(default=None, max_length=5000)
    opportunity_id: uuid.UUID | None = None
    lines: list[DocLineIn] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def _dates(self) -> InvoiceIn:
        if self.due_date < self.issue_date:
            raise ValueError("The due date cannot be before the issue date.")
        return self


class IssueIn(_In):
    fx_rate: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)


class DocLineOut(BaseModel):
    line_no: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    account_id: uuid.UUID
    tax_code_id: uuid.UUID | None
    net: Decimal
    tax: Decimal


class InvoiceOut(BaseModel):
    id: uuid.UUID
    number: str | None
    customer_id: uuid.UUID
    customer_name: str
    currency: str
    fx_rate: Decimal | None
    issue_date: date
    due_date: date
    status: str
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    amount_paid: Decimal
    amount_credited: Decimal
    outstanding: Decimal
    notes: str | None
    journal_id: uuid.UUID | None
    issued_at: datetime | None
    lines: list[DocLineOut]


class AllocationIn(_In):
    invoice_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class ReceiptIn(_In):
    customer_id: uuid.UUID
    receipt_date: date
    currency: Currency
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    fx_rate: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    bank_account_id: uuid.UUID
    method: Method
    reference: str | None = Field(default=None, max_length=120)
    allocations: list[AllocationIn] = Field(min_length=1, max_length=100)


class ReceiptOut(BaseModel):
    id: uuid.UUID
    number: str
    customer_id: uuid.UUID
    customer_name: str
    receipt_date: date
    currency: str
    fx_rate: Decimal
    amount: Decimal
    method: str
    reference: str | None
    journal_id: uuid.UUID
    allocations: list[AllocationIn]


class CreditNoteIn(_In):
    invoice_id: uuid.UUID
    credit_date: date
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    reason: str = Field(min_length=5, max_length=2000)


class CreditNoteOut(BaseModel):
    id: uuid.UUID
    number: str | None
    invoice_id: uuid.UUID
    invoice_number: str | None
    credit_date: date
    amount: Decimal
    reason: str
    status: str
    journal_id: uuid.UUID | None


class BillIn(_In):
    supplier_id: uuid.UUID
    supplier_invoice_ref: str = Field(min_length=1, max_length=120)
    purchase_order_id: uuid.UUID | None = None
    currency: Currency = "MWK"
    bill_date: date
    due_date: date
    lines: list[DocLineIn] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def _dates(self) -> BillIn:
        if self.due_date < self.bill_date:
            raise ValueError("The due date cannot be before the bill date.")
        return self


class BillOut(BaseModel):
    id: uuid.UUID
    number: str | None
    supplier_id: uuid.UUID
    supplier_name: str
    supplier_invoice_ref: str
    purchase_order_id: uuid.UUID | None
    currency: str
    fx_rate: Decimal | None
    bill_date: date
    due_date: date
    status: str
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    amount_paid: Decimal
    outstanding: Decimal
    journal_id: uuid.UUID | None
    lines: list[DocLineOut]


class PaymentIn(_In):
    bill_id: uuid.UUID
    payment_date: date
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    fx_rate: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    bank_account_id: uuid.UUID
    method: Method
    reference: str | None = Field(default=None, max_length=120)


class PaymentOut(BaseModel):
    id: uuid.UUID
    number: str | None
    bill_id: uuid.UUID
    bill_number: str | None
    supplier_id: uuid.UUID
    supplier_name: str
    payee_account_ending: str | None
    payment_date: date
    currency: str
    fx_rate: Decimal
    amount: Decimal
    method: str
    reference: str | None
    status: str
    journal_id: uuid.UUID | None


class StatementLineIn(_In):
    bank_account_id: uuid.UUID
    statement_date: date
    description: str = Field(min_length=1, max_length=300)
    reference: str | None = Field(default=None, max_length=120)
    amount: Decimal = Field(max_digits=18, decimal_places=2)

    @model_validator(mode="after")
    def _non_zero(self) -> StatementLineIn:
        if self.amount == 0:
            raise ValueError("A statement line cannot be zero.")
        return self


class StatementLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bank_account_id: uuid.UUID
    statement_date: date
    description: str
    reference: str | None
    amount: Decimal
    matched_line_id: uuid.UUID | None
    matched_at: datetime | None


class MatchIn(_In):
    journal_line_id: uuid.UUID


class ReportRow(BaseModel):
    account_id: uuid.UUID
    code: str
    name: str
    type: str
    subtype: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


class TrialBalance(BaseModel):
    as_of: date
    functional_currency: str
    rows: list[ReportRow]
    total_debit: Decimal
    total_credit: Decimal
    balanced: bool


class ProfitAndLoss(BaseModel):
    date_from: date
    date_to: date
    functional_currency: str
    income: list[ReportRow]
    expenses: list[ReportRow]
    total_income: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    basis: str


class BalanceSheet(BaseModel):
    as_of: date
    functional_currency: str
    assets: list[ReportRow]
    liabilities: list[ReportRow]
    equity: list[ReportRow]
    current_earnings: Decimal
    total_assets: Decimal
    total_liabilities_and_equity: Decimal
    balanced: bool


class AgeingRow(BaseModel):
    party_id: uuid.UUID
    party_name: str
    currency: str
    current: Decimal
    days_1_30: Decimal
    days_31_60: Decimal
    days_61_90: Decimal
    days_over_90: Decimal
    total: Decimal


class Ageing(BaseModel):
    kind: Literal["receivable", "payable"]
    as_of: date
    rows: list[AgeingRow]


class CashbookRow(BaseModel):
    entry_date: date
    number: str | None
    description: str
    money_in: Decimal
    money_out: Decimal
    balance: Decimal
    line_id: uuid.UUID
    reconciled: bool


class Cashbook(BaseModel):
    account_id: uuid.UUID
    account_name: str
    currency: str
    opening_balance: Decimal
    rows: list[CashbookRow]
    closing_balance: Decimal


class MonthFigure(BaseModel):
    month: str
    invoiced: Decimal
    collected: Decimal


class FinanceOverview(BaseModel):
    """Director KPIs from posted records only. ``has_records`` False → "No data yet"."""

    has_records: bool
    functional_currency: str
    cash_position: Decimal
    invoiced_this_month: Decimal
    collected_this_month: Decimal
    debtors_outstanding: Decimal
    creditors_outstanding: Decimal
    months: list[MonthFigure]
    revenue_by_division: dict[str, Decimal]
