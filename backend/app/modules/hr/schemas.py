"""HR and payroll request and response models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.crm.schemas import Currency

PERIOD = r"^[0-9]{4}-(0[1-9]|1[0-2])$"
EmploymentType = Literal["permanent", "fixed_term", "casual", "intern", "consultant"]
LeaveKind = Literal["annual", "sick", "maternity", "paternity", "compassionate", "study", "unpaid"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EmployeeIn(_In):
    full_name: str = Field(min_length=2, max_length=200)
    job_title: str = Field(min_length=2, max_length=120)
    department_code: str = Field(min_length=2, max_length=40)
    employment_type: EmploymentType
    start_date: date
    end_date: date | None = None
    work_email: str | None = Field(
        default=None, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )
    work_phone: str | None = Field(default=None, max_length=40)
    user_id: uuid.UUID | None = None
    manager_id: uuid.UUID | None = None
    leave_days_per_year: Decimal = Field(
        default=Decimal(0), ge=0, le=365, max_digits=5, decimal_places=1
    )


class EmployeePatch(_In):
    job_title: str | None = Field(default=None, min_length=2, max_length=120)
    department_code: str | None = Field(default=None, min_length=2, max_length=40)
    status: Literal["active", "on_leave", "terminated"] | None = None
    end_date: date | None = None
    work_email: str | None = Field(default=None, max_length=320)
    work_phone: str | None = Field(default=None, max_length=40)
    user_id: uuid.UUID | None = None
    manager_id: uuid.UUID | None = None
    leave_days_per_year: Decimal | None = Field(
        default=None, ge=0, le=365, max_digits=5, decimal_places=1
    )


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_no: str
    user_id: uuid.UUID | None
    full_name: str
    job_title: str
    department_code: str
    employment_type: str
    start_date: date
    end_date: date | None
    status: str
    work_email: str | None
    work_phone: str | None
    manager_id: uuid.UUID | None
    leave_days_per_year: Decimal
    is_demo: bool


class CompensationIn(_In):
    basic_pay: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    currency: Currency = "MWK"
    effective_from: date
    reason: str = Field(min_length=3, max_length=300)


class CompensationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    basic_pay: Decimal
    currency: str
    effective_from: date
    reason: str
    created_at: datetime


class ContractIn(_In):
    title: str = Field(min_length=3, max_length=200)
    start_date: date
    end_date: date | None = None
    file_id: uuid.UUID | None = None


class ContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    start_date: date
    end_date: date | None
    file_id: uuid.UUID | None
    signed_copy_on_file: bool


class LeaveIn(_In):
    kind: LeaveKind
    start_date: date
    end_date: date
    days: Decimal = Field(gt=0, le=365, max_digits=5, decimal_places=1)
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _dates(self) -> LeaveIn:
        if self.end_date < self.start_date:
            raise ValueError("Leave must end on or after its start.")
        return self


class LeaveDecisionIn(_In):
    approve: bool
    note: str | None = Field(default=None, max_length=2000)


class LeaveOut(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str
    kind: str
    start_date: date
    end_date: date
    days: Decimal
    reason: str | None
    status: str
    decision_note: str | None


class LeaveBalance(BaseModel):
    year: int
    entitlement: Decimal
    taken: Decimal
    pending: Decimal
    remaining: Decimal


class AttendanceIn(_In):
    employee_id: uuid.UUID
    work_date: date
    status: Literal["present", "absent", "leave", "remote", "public_holiday", "off"]
    note: str | None = Field(default=None, max_length=300)


class AttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: uuid.UUID
    work_date: date
    status: str
    note: str | None


class BandIn(_In):
    from_amount: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    to_amount: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    rate_pct: Decimal = Field(ge=0, le=100, max_digits=7, decimal_places=3)


class ComponentIn(_In):
    code: str = Field(pattern=r"^[A-Z0-9_\-]{2,20}$")
    name: str = Field(min_length=2, max_length=120)
    kind: Literal["earning", "deduction", "employer"]
    method: Literal["fixed", "percent", "bands"]
    amount: Decimal = Field(default=Decimal(0), ge=0, max_digits=18, decimal_places=2)
    rate_pct: Decimal = Field(default=Decimal(0), ge=0, le=100, max_digits=7, decimal_places=3)
    bands: list[BandIn] = Field(default_factory=list, max_length=20)
    base: Literal["gross", "taxable", "basic"] = "gross"
    taxable: bool = True
    sort_order: int = Field(default=0, ge=0, le=1000)
    source_note: str = Field(min_length=3, max_length=300)


class ComponentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    kind: str
    method: str
    amount: Decimal
    rate_pct: Decimal
    bands: list[dict[str, str | None]]
    base: str
    taxable: bool
    sort_order: int
    is_active: bool
    source_note: str


class CommissionIn(_In):
    employee_id: uuid.UUID
    period: str = Field(pattern=PERIOD)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    basis: str = Field(min_length=3, max_length=300)


class RunIn(_In):
    period: str = Field(pattern=PERIOD)
    currency: Currency = "MWK"


class PayslipOut(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    employee_no: str
    employee_name: str
    period: str
    run_status: str
    basic: Decimal
    gross: Decimal
    taxable: Decimal
    deductions: Decimal
    employer_cost: Decimal
    net: Decimal
    lines: list[dict[str, str]]


class RunOut(BaseModel):
    id: uuid.UUID
    period: str
    currency: str
    status: str
    total_gross: Decimal
    total_deductions: Decimal
    total_net: Decimal
    total_employer: Decimal
    approved_at: datetime | None
    payslips: list[PayslipOut]


class KpiIn(_In):
    title: str = Field(min_length=3, max_length=200)
    target: str = Field(min_length=1, max_length=200)
    period: str = Field(min_length=4, max_length=20)


class KpiUpdate(_In):
    actual: str | None = Field(default=None, max_length=200)
    status: Literal["agreed", "on_track", "at_risk", "met", "missed"] | None = None


class KpiOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    title: str
    target: str
    period: str
    actual: str | None
    status: str
    employee_agreed_at: datetime | None


class ReviewIn(_In):
    period: str = Field(min_length=4, max_length=20)
    rating: int = Field(ge=1, le=5)
    strengths: str = Field(min_length=3, max_length=5000)
    improvements: str = Field(min_length=3, max_length=5000)


class AcknowledgeIn(_In):
    comment: str | None = Field(default=None, max_length=5000)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    period: str
    rating: int
    strengths: str
    improvements: str
    employee_comment: str | None
    acknowledged_at: datetime | None
    created_at: datetime


class EmployeeDetail(BaseModel):
    employee: EmployeeOut
    contracts: list[ContractOut]
    leave: list[LeaveOut]
    leave_balance: LeaveBalance
    kpis: list[KpiOut]
    reviews: list[ReviewOut]
    compensation: list[CompensationOut] | None  # None when the viewer lacks payroll access


class MyHr(BaseModel):
    """Everything an employee may see about themselves."""

    employee: EmployeeOut
    leave: list[LeaveOut]
    leave_balance: LeaveBalance
    kpis: list[KpiOut]
    reviews: list[ReviewOut]
    payslips: list[PayslipOut]
