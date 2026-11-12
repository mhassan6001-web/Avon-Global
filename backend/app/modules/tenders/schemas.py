"""Tender request and response models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.crm.schemas import Currency, Division, Page, UserRef

Kind = Literal["rfq", "rfp", "eoi", "itb", "other"]
Method = Literal["portal", "email", "physical", "other"]
Status = Literal[
    "identified",
    "reviewing",
    "bidding",
    "awaiting_approval",
    "approved",
    "submitted",
    "won",
    "lost",
    "no_bid",
    "cancelled",
]
RequirementKind = Literal["eligibility", "document", "technical", "financial"]
RequirementStatus = Literal["pending", "met", "not_met", "not_applicable"]

__all__ = ["Page", "UserRef"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TenderIn(_In):
    title: str = Field(min_length=3, max_length=300)
    issuer_name: str = Field(min_length=2, max_length=200)
    issuer_reference: str | None = Field(default=None, max_length=120)
    customer_id: uuid.UUID | None = None
    kind: Kind
    division: Division | None = None
    country_code: str = Field(default="MW", pattern="^[A-Z]{2}$")
    source: str | None = Field(default=None, max_length=300)
    published_on: date | None = None
    clarification_deadline: datetime | None = None
    submission_deadline: datetime
    submission_method: Method = "email"
    bid_security_required: bool = False
    estimated_value: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    currency: Currency = "MWK"
    notes: str | None = Field(default=None, max_length=10000)
    owner_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _dates(self) -> TenderIn:
        if self.submission_deadline.tzinfo is None:
            raise ValueError("submission_deadline must include a time zone.")
        if self.clarification_deadline and self.clarification_deadline > self.submission_deadline:
            raise ValueError("The clarification deadline must be before the submission deadline.")
        return self


class TenderPatch(_In):
    title: str | None = Field(default=None, min_length=3, max_length=300)
    issuer_name: str | None = Field(default=None, min_length=2, max_length=200)
    issuer_reference: str | None = Field(default=None, max_length=120)
    customer_id: uuid.UUID | None = None
    kind: Kind | None = None
    division: Division | None = None
    country_code: str | None = Field(default=None, pattern="^[A-Z]{2}$")
    source: str | None = Field(default=None, max_length=300)
    published_on: date | None = None
    clarification_deadline: datetime | None = None
    submission_deadline: datetime | None = None
    submission_method: Method | None = None
    bid_security_required: bool | None = None
    estimated_value: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    currency: Currency | None = None
    status: Literal["identified", "reviewing", "bidding"] | None = None
    notes: str | None = Field(default=None, max_length=10000)
    owner_id: uuid.UUID | None = None


class RequirementIn(_In):
    kind: RequirementKind
    description: str = Field(min_length=3, max_length=500)
    mandatory: bool = True


class RequirementPatch(_In):
    description: str | None = Field(default=None, min_length=3, max_length=500)
    mandatory: bool | None = None
    status: RequirementStatus | None = None
    file_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class RequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tender_id: uuid.UUID
    kind: str
    description: str
    mandatory: bool
    status: str
    file_id: uuid.UUID | None
    notes: str | None


class TenderOut(BaseModel):
    id: uuid.UUID
    reference: str
    issuer_reference: str | None
    title: str
    issuer_name: str
    customer_id: uuid.UUID | None
    kind: str
    division: str | None
    country_code: str
    source: str | None
    published_on: date | None
    clarification_deadline: datetime | None
    submission_deadline: datetime
    submission_method: str
    bid_security_required: bool
    estimated_value: Decimal | None
    currency: str
    status: str
    notes: str | None
    approval_id: uuid.UUID | None
    submitted_at: datetime | None
    submitted_by: UserRef | None
    award_value: Decimal | None
    outcome_note: str | None
    owner: UserRef | None
    created_at: datetime
    updated_at: datetime
    requirements_total: int = 0
    requirements_open: int = 0


class ApprovalInfo(BaseModel):
    id: uuid.UUID
    status: str
    requested_by: str
    decided_by: str | None
    decided_at: datetime | None
    decision_note: str | None


class TenderDetail(BaseModel):
    tender: TenderOut
    requirements: list[RequirementOut]
    approval: ApprovalInfo | None


class RequestApprovalIn(_In):
    note: str | None = Field(default=None, max_length=2000)


class SubmittedIn(_In):
    submitted_at: datetime | None = None
    note: str | None = Field(default=None, max_length=2000)


class OutcomeIn(_In):
    result: Literal["won", "lost", "cancelled"]
    award_value: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    note: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def _note(self) -> OutcomeIn:
        if self.result in ("lost", "cancelled") and not self.note:
            raise ValueError("Please record why the tender was lost or cancelled.")
        if self.result != "won" and self.award_value is not None:
            raise ValueError("An award value is only recorded for a won tender.")
        return self


class NoBidIn(_In):
    reason: str = Field(min_length=3, max_length=5000)


class TenderSummary(BaseModel):
    has_records: bool
    by_status: dict[str, int]
    active: int
    due_within_7_days: int
    overdue_unsubmitted: int
    decided: int
    won: int
