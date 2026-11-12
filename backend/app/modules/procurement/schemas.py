"""Procurement request and response models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.crm.schemas import Currency, Division, Page, UserRef

__all__ = ["Page", "UserRef"]

EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
PHONE = r"^[0-9+()\-\s]{5,40}$"


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SupplierIn(_In):
    name: str = Field(min_length=2, max_length=200)
    country_code: str = Field(default="MW", pattern="^[A-Z]{2}$")
    city: str | None = Field(default=None, max_length=120)
    categories: str | None = Field(default=None, max_length=300)
    contact_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320, pattern=EMAIL)
    phone: str | None = Field(default=None, max_length=40, pattern=PHONE)
    registration_number: str | None = Field(default=None, max_length=100)
    tax_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=5000)


class SupplierPatch(_In):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    country_code: str | None = Field(default=None, pattern="^[A-Z]{2}$")
    city: str | None = Field(default=None, max_length=120)
    categories: str | None = Field(default=None, max_length=300)
    contact_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320, pattern=EMAIL)
    phone: str | None = Field(default=None, max_length=40, pattern=PHONE)
    registration_number: str | None = Field(default=None, max_length=100)
    tax_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=5000)


class VerificationIn(_In):
    status: Literal["verified", "suspended", "unverified"]
    note: str = Field(min_length=3, max_length=2000)


class BankAccountMasked(BaseModel):
    id: uuid.UUID
    bank_name: str
    account_last4: str
    currency: str
    status: str
    reason: str
    requested_by: str
    created_at: datetime


class BankAccountFull(BankAccountMasked):
    account_name: str
    account_number: str
    branch: str | None
    swift: str | None


class SupplierOut(BaseModel):
    id: uuid.UUID
    reference: str
    name: str
    country_code: str
    city: str | None
    categories: str | None
    contact_name: str | None
    email: str | None
    phone: str | None
    registration_number: str | None
    tax_number: str | None
    status: str
    verified_by: UserRef | None
    verified_at: datetime | None
    verification_note: str | None
    notes: str | None
    created_at: datetime
    has_active_bank_account: bool = False
    pending_bank_change: bool = False


class SupplierDetail(BaseModel):
    supplier: SupplierOut
    bank_accounts: list[BankAccountMasked | BankAccountFull]
    bank_details_visible: bool


class BankChangeIn(_In):
    """Plaintext travels only in this request body and is encrypted before storage."""

    bank_name: str = Field(min_length=2, max_length=200)
    account_name: str = Field(min_length=2, max_length=200)
    account_number: str = Field(min_length=4, max_length=40, pattern=r"^[0-9A-Za-z\- ]{4,40}$")
    branch: str | None = Field(default=None, max_length=120)
    swift: str | None = Field(default=None, pattern=r"^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$")
    currency: Currency = "MWK"
    reason: str = Field(min_length=5, max_length=2000)


class LineIn(_In):
    description: str = Field(min_length=2, max_length=300)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=3)
    unit: str = Field(default="each", min_length=1, max_length=20)


class PurchaseRequestIn(_In):
    title: str = Field(min_length=3, max_length=200)
    justification: str | None = Field(default=None, max_length=5000)
    division: Division | None = None
    needed_by: date | None = None
    currency: Currency = "MWK"
    tender_id: uuid.UUID | None = None
    lines: list[LineIn] = Field(min_length=1, max_length=200)


class LineOut(BaseModel):
    id: uuid.UUID
    line_no: int
    description: str
    quantity: Decimal
    unit: str


class QuoteLineIn(_In):
    request_line_id: uuid.UUID
    unit_price: Decimal = Field(ge=0, max_digits=18, decimal_places=4)


class QuoteIn(_In):
    supplier_id: uuid.UUID
    supplier_reference: str | None = Field(default=None, max_length=120)
    currency: Currency
    valid_until: date | None = None
    lead_time_days: int | None = Field(default=None, ge=0, le=3650)
    delivery_terms: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=5000)
    file_id: uuid.UUID | None = None
    lines: list[QuoteLineIn] = Field(min_length=1)


class QuoteOut(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    supplier_status: str
    supplier_reference: str | None
    currency: str
    valid_until: date | None
    lead_time_days: int | None
    delivery_terms: str | None
    notes: str | None
    total: Decimal
    complete: bool
    expired: bool
    prices: dict[str, Decimal]


class PurchaseRequestOut(BaseModel):
    id: uuid.UUID
    reference: str
    title: str
    justification: str | None
    division: str | None
    needed_by: date | None
    currency: str
    status: str
    selected_quote_id: uuid.UUID | None
    approval_id: uuid.UUID | None
    tender_id: uuid.UUID | None
    requested_by: UserRef | None
    created_at: datetime
    order_id: uuid.UUID | None = None


class PurchaseRequestDetail(BaseModel):
    request: PurchaseRequestOut
    lines: list[LineOut]
    quotes: list[QuoteOut]
    cheapest_complete_quote_id: uuid.UUID | None
    comparison_note: str


class SubmitForApprovalIn(_In):
    quote_id: uuid.UUID
    note: str | None = Field(default=None, max_length=2000)


class IssueOrderIn(_In):
    delivery_address: str | None = Field(default=None, max_length=1000)
    expected_delivery: date | None = None


class OrderLineOut(BaseModel):
    line_no: int
    description: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    line_total: Decimal
    received_quantity: Decimal


class PurchaseOrderOut(BaseModel):
    id: uuid.UUID
    reference: str
    request_id: uuid.UUID
    request_reference: str
    supplier_id: uuid.UUID
    supplier_name: str
    currency: str
    total_amount: Decimal
    status: str
    delivery_address: str | None
    expected_delivery: date | None
    cancel_reason: str | None
    issued_by: UserRef | None
    created_at: datetime
    lines: list[OrderLineOut]


class CancelIn(_In):
    reason: str = Field(min_length=3, max_length=2000)


class LandedCostIn(_In):
    goods_value: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    supplier_currency: Currency
    freight: Decimal = Field(default=Decimal(0), ge=0, max_digits=18, decimal_places=2)
    insurance: Decimal = Field(default=Decimal(0), ge=0, max_digits=18, decimal_places=2)
    exchange_rate: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    exchange_rate_source: str = Field(min_length=2, max_length=200)
    duty_rate_pct: Decimal = Field(ge=0, le=500, max_digits=7, decimal_places=3)
    excise_rate_pct: Decimal = Field(
        default=Decimal(0), ge=0, le=500, max_digits=7, decimal_places=3
    )
    vat_rate_pct: Decimal = Field(ge=0, le=500, max_digits=7, decimal_places=3)
    vat_recoverable: bool = True
    local_charges: Decimal = Field(default=Decimal(0), ge=0, max_digits=18, decimal_places=2)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=3)


class LandedCostOut(BaseModel):
    functional_currency: str
    customs_value: Decimal
    duty: Decimal
    excise: Decimal
    vat: Decimal
    local_charges: Decimal
    landed_cost: Decimal
    unit_cost: Decimal | None
    vat_included_in_cost: bool
    exchange_rate: Decimal
    exchange_rate_source: str
    is_estimate: bool = True
    note: str
