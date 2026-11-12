"""Stage 9: HR records, leave without self-approval, self-service and payroll
runs from configured components, approved by the Director and then frozen."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi import FastAPI
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.platform.audit.models import AuditEvent

from .helpers import make_user, sign_in

API = "/api/v1/hr"
YEAR = date.today().year
# Illustrative values for tests only. The application ships with no rates.
TEST_BANDS = [
    {"from_amount": "0", "to_amount": "100000", "rate_pct": "0"},
    {"from_amount": "100000", "to_amount": None, "rate_pct": "25"},
]


def _employee(c, name="TEST Employee", **extra):  # type: ignore[no-untyped-def]
    body = {
        "full_name": name,
        "job_title": "Officer",
        "department_code": "logistics",
        "employment_type": "permanent",
        "start_date": f"{YEAR}-01-01",
        "leave_days_per_year": "18",
        **extra,
    }
    r = c.post(f"{API}/employees", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_employee_records_leave_and_self_service(app: FastAPI, db: Session) -> None:
    hr_user = make_user(db, "hr_admin")
    hr = sign_in(app, hr_user)
    staff_user = make_user(db, "logistics")
    staff = sign_in(app, staff_user)
    assert staff.get(f"{API}/me").status_code == 404  # not linked yet

    emp = _employee(hr, user_id=str(staff_user.user.id))
    assert emp["employee_no"] == "EMP-00001"
    assert (
        hr.post(
            f"{API}/employees",
            json={
                **{
                    k: emp[k]
                    for k in (
                        "full_name",
                        "job_title",
                        "department_code",
                        "employment_type",
                        "start_date",
                    )
                },
                "user_id": str(staff_user.user.id),
            },
        ).status_code
        == 409
    )

    # Staff request their own leave; HR decides; nobody decides their own.
    r = staff.post(
        f"{API}/me/leave",
        json={
            "kind": "annual",
            "start_date": f"{YEAR}-03-02",
            "end_date": f"{YEAR}-03-06",
            "days": "5",
        },
    )
    assert r.status_code == 201, r.text
    leave = r.json()
    too_many = {
        "kind": "annual",
        "start_date": f"{YEAR}-06-01",
        "end_date": f"{YEAR}-07-30",
        "days": "14",
    }
    assert staff.post(f"{API}/me/leave", json=too_many).status_code == 409  # 18 - 5 pending = 13
    overlap = {
        "kind": "sick",
        "start_date": f"{YEAR}-03-05",
        "end_date": f"{YEAR}-03-05",
        "days": "1",
    }
    assert staff.post(f"{API}/me/leave", json=overlap).status_code == 409
    assert (
        staff.post(f"{API}/leave/{leave['id']}/decide", json={"approve": True}).status_code == 403
    )
    d = hr.post(f"{API}/leave/{leave['id']}/decide", json={"approve": True, "note": "Enjoy"})
    assert d.json()["status"] == "approved"

    # HR cannot approve leave HR raised for themselves.
    hr_emp = _employee(hr, "TEST HR Officer", user_id=str(hr_user.user.id))
    own = hr.post(
        f"{API}/employees/{hr_emp['id']}/leave",
        json={
            "kind": "sick",
            "start_date": f"{YEAR}-04-01",
            "end_date": f"{YEAR}-04-01",
            "days": "1",
        },
    ).json()
    assert hr.post(f"{API}/leave/{own['id']}/decide", json={"approve": True}).status_code == 403

    # KPI agreed by the employee; review acknowledged by the employee.
    kpi = hr.post(
        f"{API}/employees/{emp['id']}/kpis",
        json={"title": "On-time deliveries", "target": "95%", "period": f"{YEAR}"},
    ).json()
    assert staff.post(f"{API}/me/kpis/{kpi['id']}/agree").json()["employee_agreed_at"]
    review = hr.post(
        f"{API}/employees/{emp['id']}/reviews",
        json={
            "period": f"{YEAR}-H1",
            "rating": 4,
            "strengths": "Reliable",
            "improvements": "Paperwork",
        },
    ).json()
    ack = staff.post(f"{API}/me/reviews/{review['id']}/acknowledge", json={"comment": "Agreed"})
    assert ack.json()["acknowledged_at"]
    assert (
        hr.post(
            f"{API}/employees/{hr_emp['id']}/reviews",
            json={"period": "x" * 4, "rating": 5, "strengths": "Me", "improvements": "None"},
        ).status_code
        == 403
    )

    mine = staff.get(f"{API}/me").json()
    assert mine["leave_balance"]["taken"] == "5.0" and mine["leave_balance"]["remaining"] == "13.0"
    assert mine["payslips"] == []

    assert (
        hr.post(
            f"{API}/attendance",
            json={"employee_id": emp["id"], "work_date": "2999-01-01", "status": "present"},
        ).status_code
        == 422
    )
    assert (
        hr.post(
            f"{API}/attendance",
            json={"employee_id": emp["id"], "work_date": str(date.today()), "status": "remote"},
        ).status_code
        == 200
    )


def test_payroll_run_from_configured_components(app: FastAPI, db: Session) -> None:
    hr = sign_in(app, make_user(db, "hr_admin"))
    director = sign_in(app, make_user(db, "director"), step_up=True)
    staff_user = make_user(db, "logistics")
    staff = sign_in(app, staff_user)
    a = _employee(hr, "TEST Alpha", user_id=str(staff_user.user.id))
    b = _employee(hr, "TEST Beta")
    _employee(hr, "TEST No Pay Yet")
    for e, pay in ((a, "300000"), (b, "80000")):
        r = hr.post(
            f"{API}/employees/{e['id']}/compensation",
            json={"basic_pay": pay, "effective_from": f"{YEAR}-01-01", "reason": "Starting salary"},
        )
        assert r.status_code == 201, r.text

    bad = {
        "code": "TAX",
        "name": "Test tax",
        "kind": "deduction",
        "method": "bands",
        "base": "taxable",
        "bands": [
            {"from_amount": "0", "to_amount": "100", "rate_pct": "0"},
            {"from_amount": "200", "to_amount": None, "rate_pct": "10"},
        ],
        "source_note": "TEST only",
    }
    assert hr.post(f"{API}/pay-components", json=bad).status_code == 422  # gap in bands
    assert hr.post(f"{API}/pay-components", json={**bad, "bands": TEST_BANDS}).status_code == 201
    hr.post(
        f"{API}/pay-components",
        json={
            "code": "PEN",
            "name": "Test pension",
            "kind": "deduction",
            "method": "percent",
            "rate_pct": "5",
            "base": "basic",
            "source_note": "TEST only",
        },
    )
    hr.post(
        f"{API}/commissions",
        json={
            "employee_id": a["id"],
            "period": f"{YEAR}-03",
            "amount": "20000",
            "basis": "TEST sales commission",
        },
    )

    r = hr.post(f"{API}/payroll-runs", json={"period": f"{YEAR}-03"})
    assert r.status_code == 201, r.text
    run = r.json()
    slips = {p["employee_name"]: p for p in run["payslips"]}
    assert set(slips) == {"TEST Alpha", "TEST Beta"}  # no pay record → no payslip
    alpha = slips["TEST Alpha"]
    assert (alpha["gross"], alpha["taxable"]) == ("320000.00", "320000.00")
    assert alpha["deductions"] == "70000.00"  # tax 25% of 220000 = 55000; pension 15000
    assert alpha["net"] == "250000.00"
    assert slips["TEST Beta"]["net"] == "76000.00"  # no tax under 100000; pension 4000
    assert run["total_net"] == "326000.00"
    assert hr.post(f"{API}/payroll-runs", json={"period": f"{YEAR}-03"}).status_code == 409

    # Payroll amounts never enter the audit log.
    details = " ".join(str(x) for x in db.execute(select(AuditEvent.details)).scalars())
    assert "300000" not in details and "250000" not in details

    # Restricted: Finance and other staff cannot see payroll.
    fin = sign_in(app, make_user(db, "finance"))
    assert fin.get(f"{API}/payroll-runs").status_code == 403
    assert staff.get(f"{API}/payroll-runs").status_code == 403
    detail = director.get(f"{API}/employees/{a['id']}").json()
    assert detail["compensation"][0]["basic_pay"] == "300000.00"

    sub = hr.post(f"{API}/payroll-runs/{run['id']}/submit")
    assert sub.json()["status"] == "awaiting_approval"
    assert hr.get("/api/v1/approvals").json() == []  # HR cannot approve payroll
    aid = director.get("/api/v1/approvals").json()[0]["id"]
    assert (
        director.post(f"/api/v1/approvals/{aid}/decide", json={"approve": True}).status_code == 200
    )
    approved = hr.get(f"{API}/payroll-runs").json()[0]
    assert approved["status"] == "approved"
    assert hr.post(f"{API}/payroll-runs/{run['id']}/recalculate").status_code == 409

    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE hr_payslips SET net = 1"))
    db.rollback()

    # The employee sees their own approved payslip, and nobody else's.
    mine = staff.get(f"{API}/me").json()
    assert [p["net"] for p in mine["payslips"]] == ["250000.00"]


def test_hr_section_is_restricted(app: FastAPI, db: Session) -> None:
    for role in ("business_development", "procurement", "finance", "logistics"):
        other = sign_in(app, make_user(db, role))
        assert other.get(f"{API}/employees").status_code == 403, role
