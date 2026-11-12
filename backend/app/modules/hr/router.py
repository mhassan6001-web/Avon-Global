"""HR API (``/api/v1/hr``). HR/Admin's section; payroll amounts need payroll
permission; every employee can see their own record through ``/hr/me``."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core.errors import NotFoundError
from app.platform.authz.deps import DbSession, Principal, require

from . import schemas
from . import service as hr
from .models import (
    Attendance,
    Commission,
    Employee,
    Kpi,
    LeaveRequest,
    PayComponent,
    PayrollRun,
    Review,
)

router = APIRouter(prefix="/hr", tags=["hr"])

View = Depends(require("hr.records.view"))
Edit = Depends(require("hr.records.edit"))
PayView = Depends(require("hr.payroll.view"))
PayPrepare = Depends(require("hr.payroll.prepare"))
Own = Depends(require("comms.own.use"))


# --- Self-service ------------------------------------------------------------------


@router.get("/me", response_model=schemas.MyHr)
def my_record(db: DbSession, principal: Principal = Own) -> schemas.MyHr:
    return hr.my_hr(db, principal.user.id)


@router.post("/me/leave", response_model=schemas.LeaveOut, status_code=201)
def request_my_leave(
    body: schemas.LeaveIn, db: DbSession, principal: Principal = Own
) -> schemas.LeaveOut:
    emp = hr.employee_for_user(db, principal.user.id)
    row = hr.request_leave(db, emp, body, principal.user.id)
    db.commit()
    return hr._leave_out(db, [row])[0]


@router.post("/me/kpis/{kpi_id}/agree", response_model=schemas.KpiOut)
def agree_kpi(kpi_id: uuid.UUID, db: DbSession, principal: Principal = Own) -> schemas.KpiOut:
    emp = hr.employee_for_user(db, principal.user.id)
    kpi = db.get(Kpi, kpi_id)
    if kpi is None or kpi.employee_id != emp.id:
        raise NotFoundError("KPI not found.")
    kpi.employee_agreed_at = kpi.employee_agreed_at or hr.now()
    db.commit()
    return schemas.KpiOut.model_validate(kpi)


@router.post("/me/reviews/{review_id}/acknowledge", response_model=schemas.ReviewOut)
def acknowledge_review(
    review_id: uuid.UUID, body: schemas.AcknowledgeIn, db: DbSession, principal: Principal = Own
) -> schemas.ReviewOut:
    emp = hr.employee_for_user(db, principal.user.id)
    review = db.get(Review, review_id)
    if review is None or review.employee_id != emp.id:
        raise NotFoundError("Review not found.")
    review.acknowledged_at = hr.now()
    review.employee_comment = body.comment
    db.commit()
    return schemas.ReviewOut.model_validate(review)


# --- Employees -------------------------------------------------------------------------


@router.get("/employees", response_model=list[schemas.EmployeeOut])
def list_employees(
    db: DbSession, _: Principal = View, include_left: bool = False
) -> list[schemas.EmployeeOut]:
    stmt = select(Employee).order_by(Employee.full_name)
    if not include_left:
        stmt = stmt.where(Employee.status != "terminated")
    return [schemas.EmployeeOut.model_validate(e) for e in db.execute(stmt).scalars()]


@router.post("/employees", response_model=schemas.EmployeeOut, status_code=201)
def create_employee(
    body: schemas.EmployeeIn, db: DbSession, principal: Principal = Edit
) -> schemas.EmployeeOut:
    row = hr.create_employee(db, body, principal.user.id)
    db.commit()
    return schemas.EmployeeOut.model_validate(row)


@router.get("/employees/{employee_id}", response_model=schemas.EmployeeDetail)
def employee_detail(
    employee_id: uuid.UUID, db: DbSession, principal: Principal = View
) -> schemas.EmployeeDetail:
    return hr.employee_detail(db, hr.get_employee(db, employee_id), principal)


@router.patch("/employees/{employee_id}", response_model=schemas.EmployeeOut)
def update_employee(
    employee_id: uuid.UUID, body: schemas.EmployeePatch, db: DbSession, principal: Principal = Edit
) -> schemas.EmployeeOut:
    row = hr.update_employee(db, hr.get_employee(db, employee_id), body, principal.user.id)
    db.commit()
    return schemas.EmployeeOut.model_validate(row)


@router.post(
    "/employees/{employee_id}/compensation", response_model=schemas.CompensationOut, status_code=201
)
def add_compensation(
    employee_id: uuid.UUID,
    body: schemas.CompensationIn,
    db: DbSession,
    principal: Principal = PayPrepare,
) -> schemas.CompensationOut:
    row = hr.add_compensation(db, hr.get_employee(db, employee_id), body, principal.user.id)
    db.commit()
    return schemas.CompensationOut.model_validate(row)


@router.post(
    "/employees/{employee_id}/contracts", response_model=schemas.ContractOut, status_code=201
)
def add_contract(
    employee_id: uuid.UUID, body: schemas.ContractIn, db: DbSession, principal: Principal = Edit
) -> schemas.ContractOut:
    row = hr.add_contract(db, hr.get_employee(db, employee_id), body, principal.user.id)
    db.commit()
    return schemas.ContractOut.model_validate(row)


@router.post("/employees/{employee_id}/leave", response_model=schemas.LeaveOut, status_code=201)
def request_leave(
    employee_id: uuid.UUID, body: schemas.LeaveIn, db: DbSession, principal: Principal = Edit
) -> schemas.LeaveOut:
    row = hr.request_leave(db, hr.get_employee(db, employee_id), body, principal.user.id)
    db.commit()
    return hr._leave_out(db, [row])[0]


@router.post("/employees/{employee_id}/kpis", response_model=schemas.KpiOut, status_code=201)
def add_kpi(
    employee_id: uuid.UUID, body: schemas.KpiIn, db: DbSession, principal: Principal = Edit
) -> schemas.KpiOut:
    row = hr.add_kpi(db, hr.get_employee(db, employee_id), body, principal.user.id)
    db.commit()
    return schemas.KpiOut.model_validate(row)


@router.patch("/kpis/{kpi_id}", response_model=schemas.KpiOut)
def update_kpi(
    kpi_id: uuid.UUID, body: schemas.KpiUpdate, db: DbSession, principal: Principal = Edit
) -> schemas.KpiOut:
    kpi = db.get(Kpi, kpi_id)
    if kpi is None:
        raise NotFoundError("KPI not found.")
    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(kpi, key, value)
    hr._audit(db, "kpi.updated", principal.user.id, "hr_employee", kpi.employee_id)
    db.commit()
    return schemas.KpiOut.model_validate(kpi)


@router.post("/employees/{employee_id}/reviews", response_model=schemas.ReviewOut, status_code=201)
def add_review(
    employee_id: uuid.UUID, body: schemas.ReviewIn, db: DbSession, principal: Principal = Edit
) -> schemas.ReviewOut:
    row = hr.add_review(db, hr.get_employee(db, employee_id), body, principal.user.id)
    db.commit()
    return schemas.ReviewOut.model_validate(row)


# --- Leave and attendance --------------------------------------------------------------


@router.get("/leave", response_model=list[schemas.LeaveOut])
def list_leave(
    db: DbSession, _: Principal = View, status: str | None = Query(default=None, max_length=10)
) -> list[schemas.LeaveOut]:
    stmt = select(LeaveRequest).order_by(LeaveRequest.start_date.desc()).limit(500)
    if status:
        stmt = stmt.where(LeaveRequest.status == status)
    return hr._leave_out(db, list(db.execute(stmt).scalars()))


@router.post("/leave/{leave_id}/decide", response_model=schemas.LeaveOut)
def decide_leave(
    leave_id: uuid.UUID, body: schemas.LeaveDecisionIn, db: DbSession, principal: Principal = Edit
) -> schemas.LeaveOut:
    row = db.get(LeaveRequest, leave_id)
    if row is None:
        raise NotFoundError("Leave request not found.")
    hr.decide_leave(db, row, body, principal)
    db.commit()
    return hr._leave_out(db, [row])[0]


@router.get("/attendance", response_model=list[schemas.AttendanceOut])
def list_attendance(
    db: DbSession, _: Principal = View, employee_id: uuid.UUID | None = None
) -> list[schemas.AttendanceOut]:
    stmt = select(Attendance).order_by(Attendance.work_date.desc()).limit(500)
    if employee_id:
        stmt = stmt.where(Attendance.employee_id == employee_id)
    return [schemas.AttendanceOut.model_validate(a) for a in db.execute(stmt).scalars()]


@router.post("/attendance", response_model=schemas.AttendanceOut)
def record_attendance(
    body: schemas.AttendanceIn, db: DbSession, principal: Principal = Edit
) -> schemas.AttendanceOut:
    row = hr.record_attendance(db, body, principal.user.id)
    db.commit()
    return schemas.AttendanceOut.model_validate(row)


# --- Payroll ---------------------------------------------------------------------------


@router.get("/pay-components", response_model=list[schemas.ComponentOut])
def list_components(db: DbSession, _: Principal = PayView) -> list[schemas.ComponentOut]:
    rows = db.execute(select(PayComponent).order_by(PayComponent.sort_order, PayComponent.code))
    return [schemas.ComponentOut.model_validate(c) for c in rows.scalars()]


@router.post("/pay-components", response_model=schemas.ComponentOut, status_code=201)
def create_component(
    body: schemas.ComponentIn, db: DbSession, principal: Principal = PayPrepare
) -> schemas.ComponentOut:
    row = hr.create_component(db, body, principal.user.id)
    db.commit()
    return schemas.ComponentOut.model_validate(row)


@router.post("/commissions", status_code=201)
def add_commission(
    body: schemas.CommissionIn, db: DbSession, principal: Principal = PayPrepare
) -> dict[str, str]:
    hr.get_employee(db, body.employee_id)
    row = Commission(created_by=principal.user.id, **body.model_dump())
    db.add(row)
    db.flush()
    hr._audit(
        db,
        "commission.added",
        principal.user.id,
        "hr_employee",
        body.employee_id,
        period=body.period,
    )
    db.commit()
    return {"id": str(row.id)}


@router.get("/payroll-runs", response_model=list[schemas.RunOut])
def list_runs(db: DbSession, _: Principal = PayView) -> list[schemas.RunOut]:
    rows = db.execute(select(PayrollRun).order_by(PayrollRun.period.desc()).limit(36)).scalars()
    return [hr.run_out(db, r) for r in rows]


@router.post("/payroll-runs", response_model=schemas.RunOut, status_code=201)
def create_run(
    body: schemas.RunIn, db: DbSession, principal: Principal = PayPrepare
) -> schemas.RunOut:
    run = hr.create_run(db, body, principal.user.id)
    db.commit()
    return hr.run_out(db, run)


@router.post("/payroll-runs/{run_id}/recalculate", response_model=schemas.RunOut)
def recalculate(
    run_id: uuid.UUID, db: DbSession, principal: Principal = PayPrepare
) -> schemas.RunOut:
    run = hr.recalculate(db, hr.get_run(db, run_id), principal.user.id)
    db.commit()
    return hr.run_out(db, run)


@router.post("/payroll-runs/{run_id}/submit", response_model=schemas.RunOut)
def submit_run(
    run_id: uuid.UUID, db: DbSession, principal: Principal = PayPrepare
) -> schemas.RunOut:
    run = hr.submit_run(db, hr.get_run(db, run_id), principal)
    db.commit()
    return hr.run_out(db, run)
