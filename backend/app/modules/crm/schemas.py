"""CRM request and response models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CustomerStatus = Literal["prospect", "active", "inactive", "archived"]
CustomerKind = Literal["organisation", "government", "ngo", "individual"]
Division = Literal[
    "general_supplies",
    "technologies",
    "industrial_construction",
    "medical_pharmaceuticals",
    "international_trade",
    "logistics_distribution",
]
Stage = Literal["lead", "qualified", "proposal", "negotiation", "won", "lost"]
ActivityKind = Literal["meeting", "call", "email", "note", "follow_up"]
Currency = Literal["MWK", "USD", "ZAR", "ZMW"]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CustomerIn(_In):
    name: str = Field(min_length=2, max_length=200)
    kind: CustomerKind = "organisation"
    status: Literal["prospect", "active", "inactive"] = "prospect"
    country_code: str = Field(default="MW", pattern="^[A-Z]{2}$")
    city: str | None = Field(default=None, max_length=120)
    industry: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str | None = Field(default=None, max_length=40, pattern=r"^[0-9+()\-\s]{5,40}$")
    notes: str | None = Field(default=None, max_length=5000)
    owner_id: uuid.UUID | None = None

    _strip = field_validator("city", "industry", "email", "phone", "notes", mode="before")(
        lambda v: _clean(v) if isinstance(v, str) else v
    )


class CustomerPatch(_In):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    kind: CustomerKind | None = None
    status: Literal["prospect", "active", "inactive"] | None = None
    country_code: str | None = Field(default=None, pattern="^[A-Z]{2}$")
    city: str | None = Field(default=None, max_length=120)
    industry: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str | None = Field(default=None, max_length=40, pattern=r"^[0-9+()\-\s]{5,40}$")
    notes: str | None = Field(default=None, max_length=5000)
    owner_id: uuid.UUID | None = None


class UserRef(BaseModel):
    id: uuid.UUID
    display_name: str


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    name: str
    kind: str
    status: str
    country_code: str
    city: str | None
    industry: str | None
    email: str | None
    phone: str | None
    notes: str | None
    owner: UserRef | None = None
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    open_opportunities: int = 0


class ContactIn(_In):
    name: str = Field(min_length=2, max_length=200)
    job_title: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str | None = Field(default=None, max_length=40, pattern=r"^[0-9+()\-\s]{5,40}$")
    is_primary: bool = False


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    name: str
    job_title: str | None
    email: str | None
    phone: str | None
    is_primary: bool


class OpportunityIn(_In):
    customer_id: uuid.UUID
    title: str = Field(min_length=2, max_length=200)
    division: Division
    stage: Literal["lead", "qualified", "proposal", "negotiation"] = "lead"
    value_amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    currency: Currency = "MWK"
    probability: int = Field(default=10, ge=0, le=100)
    expected_close: date | None = None
    owner_id: uuid.UUID | None = None


class OpportunityPatch(_In):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    division: Division | None = None
    stage: Stage | None = None
    value_amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    currency: Currency | None = None
    probability: int | None = Field(default=None, ge=0, le=100)
    expected_close: date | None = None
    lost_reason: str | None = Field(default=None, max_length=2000)
    owner_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _lost_reason(self) -> OpportunityPatch:
        if self.stage == "lost" and not (self.lost_reason and self.lost_reason.strip()):
            raise ValueError("A reason is required when marking an opportunity as lost.")
        return self


class OpportunityOut(BaseModel):
    id: uuid.UUID
    reference: str
    customer_id: uuid.UUID
    customer_name: str
    title: str
    division: str
    stage: str
    value_amount: Decimal | None
    currency: str
    probability: int
    expected_close: date | None
    lost_reason: str | None
    closed_at: datetime | None
    owner: UserRef | None
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class ActivityIn(_In):
    customer_id: uuid.UUID
    opportunity_id: uuid.UUID | None = None
    kind: ActivityKind
    subject: str = Field(min_length=2, max_length=200)
    body: str | None = Field(default=None, max_length=10000)
    occurred_at: datetime | None = None
    due_at: datetime | None = None
    assigned_to: uuid.UUID | None = None

    @model_validator(mode="after")
    def _follow_up_due(self) -> ActivityIn:
        if self.kind == "follow_up" and self.due_at is None:
            raise ValueError("A follow-up needs a due date.")
        return self


class ActivityOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str
    opportunity_id: uuid.UUID | None
    kind: str
    subject: str
    body: str | None
    occurred_at: datetime | None
    due_at: datetime | None
    completed_at: datetime | None
    assigned_to: UserRef | None
    created_by: UserRef | None
    created_at: datetime


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int


class CustomerDetail(BaseModel):
    customer: CustomerOut
    contacts: list[ContactOut]
    opportunities: list[OpportunityOut]
    activities: list[ActivityOut]


class StageSummary(BaseModel):
    stage: str
    count: int
    value_by_currency: dict[str, Decimal]


class CrmSummary(BaseModel):
    """``has_records`` False means "No data yet"; zero counts mean "none in range"."""

    has_records: bool
    customers_by_status: dict[str, int]
    pipeline: list[StageSummary]
    follow_ups_overdue: int
    follow_ups_due_7_days: int
