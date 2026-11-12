"""HR and payroll (Stage 9). Salaries and payslips are restricted to
``hr.payroll.view``; payroll components are configuration with no built-in
rates; an approved payroll run and its payslips cannot change (migration 0009)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

MONEY = Numeric(18, 2)
CURRENCY_CHECK = "currency IN ('MWK', 'USD', 'ZAR', 'ZMW')"


def _pk() -> Any:
    return mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))


class Employee(TimestampMixin, Base):
    __tablename__ = "hr_employees"
    __table_args__ = (
        CheckConstraint(
            "employment_type IN ('permanent', 'fixed_term', 'casual', 'intern', 'consultant')",
            name="type_valid",
        ),
        CheckConstraint("status IN ('active', 'on_leave', 'terminated')", name="status_valid"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="dates_ordered"),
    )

    id: Mapped[uuid.UUID] = _pk()
    employee_no: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"), unique=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    job_title: Mapped[str] = mapped_column(String(120), nullable=False)
    department_code: Mapped[str] = mapped_column(String(40), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(12), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="active")
    work_email: Mapped[str | None] = mapped_column(String(320))
    work_phone: Mapped[str | None] = mapped_column(String(40))
    manager_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hr_employees.id"))
    leave_days_per_year: Mapped[Decimal] = mapped_column(
        Numeric(5, 1), nullable=False, server_default="0"
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class Compensation(Base):
    """Basic pay history: a new row per change, never edited."""

    __tablename__ = "hr_compensation"
    __table_args__ = (
        CheckConstraint("basic_pay >= 0", name="pay_non_negative"),
        CheckConstraint(CURRENCY_CHECK, name="currency_valid"),
        UniqueConstraint("employee_id", "effective_from"),
    )

    id: Mapped[uuid.UUID] = _pk()
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hr_employees.id"), nullable=False)
    basic_pay: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="MWK")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class Contract(TimestampMixin, Base):
    __tablename__ = "hr_contracts"
    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="dates_ordered"),
    )

    id: Mapped[uuid.UUID] = _pk()
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hr_employees.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sys_files.id"))
    signed_copy_on_file: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class LeaveRequest(TimestampMixin, Base):
    __tablename__ = "hr_leave_requests"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('annual', 'sick', 'maternity', 'paternity', 'compassionate', 'study', "
            "'unpaid')",
            name="kind_valid",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled')", name="status_valid"
        ),
        CheckConstraint("end_date >= start_date", name="dates_ordered"),
        CheckConstraint("days > 0", name="days_positive"),
        CheckConstraint(
            "decided_by IS NULL OR decided_by <> requested_by", name="no_self_decision"
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hr_employees.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(14), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    days: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="pending")
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth_users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[str | None] = mapped_column(Text)


class Attendance(Base):
    """A daily status recorded by HR. No device tracking or monitoring."""

    __tablename__ = "hr_attendance"
    __table_args__ = (
        CheckConstraint(
            "status IN ('present', 'absent', 'leave', 'remote', 'public_holiday', 'off')",
            name="status_valid",
        ),
        UniqueConstraint("employee_id", "work_date"),
    )

    id: Mapped[uuid.UUID] = _pk()
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hr_employees.id"), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str | None] = mapped_column(String(300))
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class PayComponent(TimestampMixin, Base):
    __tablename__ = "hr_pay_components"
    __table_args__ = (
        CheckConstraint("kind IN ('earning', 'deduction', 'employer')", name="kind_valid"),
        CheckConstraint("method IN ('fixed', 'percent', 'bands')", name="method_valid"),
        CheckConstraint("base IN ('gross', 'taxable', 'basic')", name="base_valid"),
        CheckConstraint("amount >= 0 AND rate_pct >= 0 AND rate_pct <= 100", name="values_valid"),
    )

    id: Mapped[uuid.UUID] = _pk()
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    rate_pct: Mapped[Decimal] = mapped_column(Numeric(7, 3), nullable=False, server_default="0")
    bands: Mapped[list[dict[str, str | None]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    base: Mapped[str] = mapped_column(String(8), nullable=False, server_default="gross")
    taxable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    source_note: Mapped[str] = mapped_column(String(300), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class Commission(Base):
    __tablename__ = "hr_commissions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("period ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'", name="period_format"),
    )

    id: Mapped[uuid.UUID] = _pk()
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hr_employees.id"), nullable=False)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    basis: Mapped[str] = mapped_column(String(300), nullable=False)
    payroll_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hr_payroll_runs.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class PayrollRun(TimestampMixin, Base):
    __tablename__ = "hr_payroll_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'awaiting_approval', 'approved', 'rejected')",
            name="status_valid",
        ),
        CheckConstraint("period ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'", name="period_format"),
        CheckConstraint(CURRENCY_CHECK, name="currency_valid"),
    )

    id: Mapped[uuid.UUID] = _pk()
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="MWK")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    total_gross: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    total_deductions: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    total_net: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    total_employer: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default="0")
    approval_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sys_approval_requests.id"))
    prepared_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Payslip(Base):
    __tablename__ = "hr_payslips"
    __table_args__ = (UniqueConstraint("run_id", "employee_id"),)

    id: Mapped[uuid.UUID] = _pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hr_payroll_runs.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hr_employees.id"), nullable=False)
    basic: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    gross: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    taxable: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    deductions: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    employer_cost: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    net: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    lines: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False)


class Kpi(TimestampMixin, Base):
    """A KPI agreed with the employee. Progress is entered by people, never inferred."""

    __tablename__ = "hr_kpis"
    __table_args__ = (
        CheckConstraint(
            "status IN ('agreed', 'on_track', 'at_risk', 'met', 'missed')", name="status_valid"
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hr_employees.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    target: Mapped[str] = mapped_column(String(200), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    actual: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="agreed")
    employee_agreed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)


class Review(TimestampMixin, Base):
    __tablename__ = "hr_reviews"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),)

    id: Mapped[uuid.UUID] = _pk()
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hr_employees.id"), nullable=False, index=True
    )
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    strengths: Mapped[str] = mapped_column(Text, nullable=False)
    improvements: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_users.id"), nullable=False)
    employee_comment: Mapped[str | None] = mapped_column(Text)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
