"""HR rules: employees, pay history, leave (never self-approved), attendance,
KPIs, reviews and payroll runs approved by the Director."""

from __future__ import annotations

import calendar
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.platform.approvals import service as approvals
from app.platform.approvals.models import ApprovalRequest
from app.platform.audit import service as audit
from app.platform.authz.deps import Principal
from app.platform.files.models import StoredFile
from app.platform.identity.models import User
from app.platform.references import next_reference

from . import payroll_calc as calc
from . import schemas
from .models import (
    Attendance,
    Commission,
    Compensation,
    Contract,
    Employee,
    Kpi,
    LeaveRequest,
    PayComponent,
    PayrollRun,
    Payslip,
    Review,
)

RUN_SUBJECT = "payroll_run"


class HrRuleError(AppError):
    status_code = 422
    code = "validation_error"


def now() -> datetime:
    return datetime.now(UTC)


def _audit(
    db: Session, action: str, actor: uuid.UUID, kind: str, target: Any, **details: Any
) -> None:
    audit.record(
        db,
        action=f"hr.{action}",
        actor_id=actor,
        target_type=kind,
        target_id=target,
        details=details,
    )


def get_employee(db: Session, employee_id: uuid.UUID) -> Employee:
    row = db.get(Employee, employee_id)
    if row is None:
        raise NotFoundError("Employee not found.")
    return row


def employee_for_user(db: Session, user_id: uuid.UUID) -> Employee:
    row = db.execute(select(Employee).where(Employee.user_id == user_id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Your login is not linked to an employee record yet. Ask HR.")
    return row


def create_employee(db: Session, body: schemas.EmployeeIn, actor: uuid.UUID) -> Employee:
    if body.user_id:
        if db.get(User, body.user_id) is None:
            raise HrRuleError("The linked login does not exist.")
        if db.execute(select(Employee.id).where(Employee.user_id == body.user_id)).first():
            raise ConflictError("That login is already linked to another employee.")
    if body.manager_id:
        get_employee(db, body.manager_id)
    if body.end_date and body.end_date < body.start_date:
        raise HrRuleError("The end date cannot be before the start date.")
    row = Employee(employee_no=next_reference(db, "EMP"), created_by=actor, **body.model_dump())
    db.add(row)
    db.flush()
    _audit(db, "employee.created", actor, "hr_employee", row.id, employee_no=row.employee_no)
    return row


def update_employee(
    db: Session, row: Employee, body: schemas.EmployeePatch, actor: uuid.UUID
) -> Employee:
    changes = body.model_dump(exclude_unset=True)
    if (
        changes.get("user_id")
        and db.execute(
            select(Employee.id).where(Employee.user_id == changes["user_id"], Employee.id != row.id)
        ).first()
    ):
        raise ConflictError("That login is already linked to another employee.")
    if changes.get("manager_id") == row.id:
        raise HrRuleError("An employee cannot manage themselves.")
    for key, value in changes.items():
        if value is None and key in (
            "job_title",
            "department_code",
            "status",
            "leave_days_per_year",
        ):
            continue
        setattr(row, key, value)
    _audit(db, "employee.updated", actor, "hr_employee", row.id, fields=sorted(changes))
    return row


def add_compensation(
    db: Session, row: Employee, body: schemas.CompensationIn, actor: uuid.UUID
) -> Compensation:
    if db.execute(
        select(Compensation.id).where(
            Compensation.employee_id == row.id, Compensation.effective_from == body.effective_from
        )
    ).first():
        raise ConflictError("A pay change already exists for that date. Pay history is not edited.")
    comp = Compensation(employee_id=row.id, created_by=actor, **body.model_dump())
    db.add(comp)
    db.flush()
    # Amounts are not written to the audit log (restricted payroll data).
    _audit(
        db, "compensation.changed", actor, "hr_employee", row.id, effective_from=body.effective_from
    )
    return comp


def add_contract(
    db: Session, row: Employee, body: schemas.ContractIn, actor: uuid.UUID
) -> Contract:
    if body.file_id:
        f = db.get(StoredFile, body.file_id)
        if f is None or f.module != "hr":
            raise HrRuleError("Attach a document uploaded to the HR section.")
    contract = Contract(
        employee_id=row.id,
        created_by=actor,
        signed_copy_on_file=body.file_id is not None,
        **body.model_dump(),
    )
    db.add(contract)
    db.flush()
    _audit(db, "contract.added", actor, "hr_employee", row.id)
    return contract


# --- Leave -----------------------------------------------------------------------------


def _leave_out(db: Session, rows: list[LeaveRequest]) -> list[schemas.LeaveOut]:
    names = (
        dict(
            db.execute(
                select(Employee.id, Employee.full_name).where(
                    Employee.id.in_({r.employee_id for r in rows})
                )
            )
            .tuples()
            .all()
        )
        if rows
        else {}
    )
    return [
        schemas.LeaveOut(
            id=r.id,
            employee_id=r.employee_id,
            employee_name=names.get(r.employee_id, ""),
            kind=r.kind,
            start_date=r.start_date,
            end_date=r.end_date,
            days=r.days,
            reason=r.reason,
            status=r.status,
            decision_note=r.decision_note,
        )
        for r in rows
    ]


def leave_balance(db: Session, employee: Employee, year: int) -> schemas.LeaveBalance:
    def total(status: str) -> Decimal:
        return Decimal(
            db.execute(
                select(func.coalesce(func.sum(LeaveRequest.days), 0)).where(
                    LeaveRequest.employee_id == employee.id,
                    LeaveRequest.kind == "annual",
                    LeaveRequest.status == status,
                    func.extract("year", LeaveRequest.start_date) == year,
                )
            ).scalar_one()
        )

    taken, pending = total("approved"), total("pending")
    return schemas.LeaveBalance(
        year=year,
        entitlement=employee.leave_days_per_year,
        taken=taken,
        pending=pending,
        remaining=employee.leave_days_per_year - taken - pending,
    )


def request_leave(
    db: Session, employee: Employee, body: schemas.LeaveIn, actor: uuid.UUID
) -> LeaveRequest:
    if employee.status == "terminated":
        raise ConflictError("This employee has left.")
    overlap = db.execute(
        select(LeaveRequest.id).where(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.status.in_(("pending", "approved")),
            LeaveRequest.start_date <= body.end_date,
            LeaveRequest.end_date >= body.start_date,
        )
    ).first()
    if overlap:
        raise ConflictError("These dates overlap another leave request.")
    span = Decimal((body.end_date - body.start_date).days + 1)
    if body.days > span:
        raise HrRuleError("More leave days than calendar days in the range.")
    if body.kind == "annual":
        balance = leave_balance(db, employee, body.start_date.year)
        if body.days > balance.remaining:
            raise ConflictError(f"Only {balance.remaining} annual leave days remain.")
    row = LeaveRequest(employee_id=employee.id, requested_by=actor, **body.model_dump())
    db.add(row)
    db.flush()
    _audit(
        db,
        "leave.requested",
        actor,
        "hr_employee",
        employee.id,
        days=body.days,
        leave_kind=body.kind,
    )
    return row


def decide_leave(
    db: Session, row: LeaveRequest, body: schemas.LeaveDecisionIn, principal: Principal
) -> LeaveRequest:
    if row.status != "pending":
        raise ConflictError("This request has already been decided.")
    employee = get_employee(db, row.employee_id)
    if principal.user.id in (row.requested_by, employee.user_id):
        raise PermissionDeniedError("You cannot decide your own leave request.")
    row.status = "approved" if body.approve else "rejected"
    row.decided_by = principal.user.id
    row.decided_at = now()
    row.decision_note = body.note
    _audit(db, f"leave.{row.status}", principal.user.id, "hr_employee", employee.id)
    return row


# --- Attendance, KPIs, reviews ------------------------------------------------------------


def record_attendance(db: Session, body: schemas.AttendanceIn, actor: uuid.UUID) -> Attendance:
    get_employee(db, body.employee_id)
    if body.work_date > now().date():
        raise HrRuleError("Attendance cannot be recorded for a future date.")
    row = db.execute(
        select(Attendance).where(
            Attendance.employee_id == body.employee_id, Attendance.work_date == body.work_date
        )
    ).scalar_one_or_none()
    if row is None:
        row = Attendance(recorded_by=actor, **body.model_dump())
        db.add(row)
    else:
        row.status, row.note, row.recorded_by = body.status, body.note, actor
    db.flush()
    _audit(db, "attendance.recorded", actor, "hr_employee", body.employee_id, date=body.work_date)
    return row


def add_kpi(db: Session, employee: Employee, body: schemas.KpiIn, actor: uuid.UUID) -> Kpi:
    row = Kpi(employee_id=employee.id, created_by=actor, **body.model_dump())
    db.add(row)
    db.flush()
    _audit(db, "kpi.added", actor, "hr_employee", employee.id)
    return row


def add_review(db: Session, employee: Employee, body: schemas.ReviewIn, actor: uuid.UUID) -> Review:
    if employee.user_id == actor:
        raise PermissionDeniedError("You cannot review yourself.")
    row = Review(employee_id=employee.id, reviewer_id=actor, **body.model_dump())
    db.add(row)
    db.flush()
    _audit(db, "review.added", actor, "hr_employee", employee.id)
    return row


# --- Payroll ------------------------------------------------------------------------------


def create_component(db: Session, body: schemas.ComponentIn, actor: uuid.UUID) -> PayComponent:
    if db.execute(select(PayComponent.id).where(PayComponent.code == body.code)).first():
        raise ConflictError(f"Component {body.code} already exists.")
    bands = tuple(calc.Band(b.from_amount, b.to_amount, b.rate_pct) for b in body.bands)
    if body.method == "bands":
        if not bands:
            raise HrRuleError("A banded component needs at least one band.")
        try:
            calc.validate_bands(bands)
        except ValueError as exc:
            raise HrRuleError(str(exc)) from exc
    elif body.bands:
        raise HrRuleError("Bands are only used with the 'bands' method.")
    row = PayComponent(
        created_by=actor,
        **body.model_dump(exclude={"bands"}),
        bands=[
            {
                "from_amount": str(b.from_amount),
                "to_amount": None if b.to_amount is None else str(b.to_amount),
                "rate_pct": str(b.rate_pct),
            }
            for b in body.bands
        ],
    )
    db.add(row)
    db.flush()
    _audit(db, "pay_component.created", actor, "hr_pay_component", row.id, code=row.code)
    return row


def _components(db: Session) -> list[calc.Component]:
    out = []
    for c in db.execute(select(PayComponent).where(PayComponent.is_active)).scalars():
        out.append(
            calc.Component(
                code=c.code,
                name=c.name,
                kind=c.kind,
                method=c.method,
                amount=c.amount,
                rate_pct=c.rate_pct,
                base=c.base,
                taxable=c.taxable,
                order=c.sort_order,
                bands=tuple(
                    calc.Band(
                        Decimal(b["from_amount"] or "0"),
                        None if b["to_amount"] is None else Decimal(b["to_amount"]),
                        Decimal(b["rate_pct"] or "0"),
                    )
                    for b in c.bands
                ),
            )
        )
    return out


def _period_end(period: str) -> date:
    year, month = (int(x) for x in period.split("-"))
    return date(year, month, calendar.monthrange(year, month)[1])


def get_run(db: Session, run_id: uuid.UUID) -> PayrollRun:
    row = db.get(PayrollRun, run_id)
    if row is None:
        raise NotFoundError("Payroll run not found.")
    return row


def _calculate(db: Session, run: PayrollRun) -> None:
    for old in db.execute(select(Payslip).where(Payslip.run_id == run.id)).scalars():
        db.delete(old)
    db.flush()
    end = _period_end(run.period)
    start = end.replace(day=1)
    components = _components(db)
    employees = db.execute(
        select(Employee).where(
            Employee.start_date <= end,
            (Employee.end_date.is_(None)) | (Employee.end_date >= start),
        )
    ).scalars()
    totals = {
        "gross": Decimal(0),
        "deductions": Decimal(0),
        "net": Decimal(0),
        "employer": Decimal(0),
    }
    for emp in employees:
        pay = db.execute(
            select(Compensation)
            .where(Compensation.employee_id == emp.id, Compensation.effective_from <= end)
            .order_by(Compensation.effective_from.desc())
            .limit(1)
        ).scalar_one_or_none()
        if pay is None or pay.currency != run.currency:
            continue
        extras = [
            calc.Line("COMMISSION", f"Commission: {c.basis}", "earning", c.amount)
            for c in db.execute(
                select(Commission).where(
                    Commission.employee_id == emp.id,
                    Commission.period == run.period,
                    (Commission.payroll_run_id.is_(None)) | (Commission.payroll_run_id == run.id),
                )
            ).scalars()
        ]
        try:
            slip = calc.calculate(pay.basic_pay, components, extras)
        except ValueError as exc:
            raise HrRuleError(f"{emp.employee_no}: {exc}") from exc
        db.add(
            Payslip(
                run_id=run.id,
                employee_id=emp.id,
                basic=slip.basic,
                gross=slip.gross,
                taxable=slip.taxable,
                deductions=slip.deductions,
                employer_cost=slip.employer,
                net=slip.net,
                lines=[
                    {"code": ln.code, "name": ln.name, "kind": ln.kind, "amount": str(ln.amount)}
                    for ln in slip.lines
                ],
            )
        )
        totals["gross"] += slip.gross
        totals["deductions"] += slip.deductions
        totals["net"] += slip.net
        totals["employer"] += slip.employer
    run.total_gross = totals["gross"]
    run.total_deductions = totals["deductions"]
    run.total_net = totals["net"]
    run.total_employer = totals["employer"]
    db.flush()


def create_run(db: Session, body: schemas.RunIn, actor: uuid.UUID) -> PayrollRun:
    if db.execute(
        select(PayrollRun.id).where(
            PayrollRun.period == body.period, PayrollRun.status != "rejected"
        )
    ).first():
        raise ConflictError(f"A payroll run for {body.period} already exists.")
    run = PayrollRun(prepared_by=actor, **body.model_dump())
    db.add(run)
    db.flush()
    _calculate(db, run)
    _audit(db, "payroll.prepared", actor, "hr_payroll_run", run.id, period=run.period)
    return run


def recalculate(db: Session, run: PayrollRun, actor: uuid.UUID) -> PayrollRun:
    if run.status != "draft":
        raise ConflictError("Only a draft payroll run can be recalculated.")
    _calculate(db, run)
    _audit(db, "payroll.recalculated", actor, "hr_payroll_run", run.id)
    return run


def submit_run(db: Session, run: PayrollRun, principal: Principal) -> PayrollRun:
    if run.status != "draft":
        raise ConflictError("Only a draft payroll run can be sent for approval.")
    count = db.execute(
        select(func.count()).select_from(Payslip).where(Payslip.run_id == run.id)
    ).scalar_one()
    if not count:
        raise ConflictError("The run has no payslips. Add pay details for employees first.")
    req = approvals.create_request(
        db,
        principal=principal,
        subject_type=RUN_SUBJECT,
        subject_id=str(run.id),
        permission_required="hr.payroll.approve",
        summary=f"Approve payroll {run.period}: {count} payslip(s), "
        f"net {run.currency} {run.total_net:,.2f}",
        payload={
            "period": run.period,
            "payslips": count,
            "currency": run.currency,
            "total_net": str(run.total_net),
            "total_gross": str(run.total_gross),
        },
    )
    run.approval_id = req.id
    run.status = "awaiting_approval"
    _audit(db, "payroll.submitted", principal.user.id, "hr_payroll_run", run.id)
    return run


def _apply_run_decision(db: Session, request: ApprovalRequest) -> None:
    run = db.get(PayrollRun, uuid.UUID(request.subject_id))
    if run is None or run.status != "awaiting_approval" or run.approval_id != request.id:
        raise ConflictError("This payroll run is no longer waiting for approval.")
    if request.status != "approved":
        run.status = "draft"
        return
    run.status = "approved"
    run.approved_at = now()
    for slip in db.execute(select(Payslip).where(Payslip.run_id == run.id)).scalars():
        for c in db.execute(
            select(Commission).where(
                Commission.employee_id == slip.employee_id,
                Commission.period == run.period,
                Commission.payroll_run_id.is_(None),
            )
        ).scalars():
            c.payroll_run_id = run.id


approvals.register_handler(RUN_SUBJECT, _apply_run_decision)


def payslips_out(db: Session, rows: list[Payslip]) -> list[schemas.PayslipOut]:
    if not rows:
        return []
    emps = {
        e.id: e
        for e in db.execute(
            select(Employee).where(Employee.id.in_({r.employee_id for r in rows}))
        ).scalars()
    }
    runs = {
        r.id: r
        for r in db.execute(
            select(PayrollRun).where(PayrollRun.id.in_({r.run_id for r in rows}))
        ).scalars()
    }
    return [
        schemas.PayslipOut(
            id=r.id,
            employee_id=r.employee_id,
            employee_no=emps[r.employee_id].employee_no,
            employee_name=emps[r.employee_id].full_name,
            period=runs[r.run_id].period,
            run_status=runs[r.run_id].status,
            basic=r.basic,
            gross=r.gross,
            taxable=r.taxable,
            deductions=r.deductions,
            employer_cost=r.employer_cost,
            net=r.net,
            lines=r.lines,
        )
        for r in rows
    ]


def run_out(db: Session, run: PayrollRun) -> schemas.RunOut:
    slips = list(db.execute(select(Payslip).where(Payslip.run_id == run.id)).scalars())
    return schemas.RunOut(
        id=run.id,
        period=run.period,
        currency=run.currency,
        status=run.status,
        total_gross=run.total_gross,
        total_deductions=run.total_deductions,
        total_net=run.total_net,
        total_employer=run.total_employer,
        approved_at=run.approved_at,
        payslips=sorted(payslips_out(db, slips), key=lambda p: p.employee_no),
    )


def my_hr(db: Session, user_id: uuid.UUID) -> schemas.MyHr:
    emp = employee_for_user(db, user_id)
    slips = list(
        db.execute(
            select(Payslip)
            .join(PayrollRun, PayrollRun.id == Payslip.run_id)
            .where(Payslip.employee_id == emp.id, PayrollRun.status == "approved")
            .order_by(PayrollRun.period.desc())
        ).scalars()
    )
    return schemas.MyHr(
        employee=schemas.EmployeeOut.model_validate(emp),
        leave=_leave_out(
            db,
            list(
                db.execute(
                    select(LeaveRequest)
                    .where(LeaveRequest.employee_id == emp.id)
                    .order_by(LeaveRequest.start_date.desc())
                ).scalars()
            ),
        ),
        leave_balance=leave_balance(db, emp, now().year),
        kpis=[
            schemas.KpiOut.model_validate(k)
            for k in db.execute(select(Kpi).where(Kpi.employee_id == emp.id)).scalars()
        ],
        reviews=[
            schemas.ReviewOut.model_validate(r)
            for r in db.execute(select(Review).where(Review.employee_id == emp.id)).scalars()
        ],
        payslips=payslips_out(db, slips),
    )


def employee_detail(db: Session, emp: Employee, principal: Principal) -> schemas.EmployeeDetail:
    show_pay = principal.has("hr.payroll.view")
    return schemas.EmployeeDetail(
        employee=schemas.EmployeeOut.model_validate(emp),
        contracts=[
            schemas.ContractOut.model_validate(c)
            for c in db.execute(select(Contract).where(Contract.employee_id == emp.id)).scalars()
        ],
        leave=_leave_out(
            db,
            list(
                db.execute(
                    select(LeaveRequest)
                    .where(LeaveRequest.employee_id == emp.id)
                    .order_by(LeaveRequest.start_date.desc())
                ).scalars()
            ),
        ),
        leave_balance=leave_balance(db, emp, now().year),
        kpis=[
            schemas.KpiOut.model_validate(k)
            for k in db.execute(select(Kpi).where(Kpi.employee_id == emp.id)).scalars()
        ],
        reviews=[
            schemas.ReviewOut.model_validate(r)
            for r in db.execute(select(Review).where(Review.employee_id == emp.id)).scalars()
        ],
        compensation=[
            schemas.CompensationOut.model_validate(c)
            for c in db.execute(
                select(Compensation)
                .where(Compensation.employee_id == emp.id)
                .order_by(Compensation.effective_from.desc())
            ).scalars()
        ]
        if show_pay
        else None,
    )
