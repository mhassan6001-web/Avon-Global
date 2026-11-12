"""Stage 5: tender register, requirement checklist, bid approval and outcomes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.platform.audit.models import AuditEvent

from .helpers import make_user, sign_in

API = "/api/v1"


def _deadline(days: float) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def _tender(c, **extra):  # type: ignore[no-untyped-def]
    body = {
        "title": "Supply of laboratory consumables",
        "issuer_name": "TEST Ministry of Health",
        "kind": "rfq",
        "submission_deadline": _deadline(10),
        **extra,
    }
    r = c.post(f"{API}/tenders", json=body)
    assert r.status_code == 201, r.text
    return r.json()["tender"]


def test_register_search_and_summary(app: FastAPI, db: Session) -> None:
    c = sign_in(app, make_user(db, "business_development"))
    assert c.get(f"{API}/tenders/summary").json()["has_records"] is False
    t = _tender(c, issuer_reference="MOH/RFQ/001")
    assert t["reference"].startswith("TND-") and t["status"] == "identified"
    _tender(c, title="Road works EOI", kind="eoi", submission_deadline=_deadline(3))
    _tender(c, title="Old tender", submission_deadline=_deadline(-2))
    assert c.get(f"{API}/tenders?q=moh/rfq").json()["total"] == 1
    assert c.get(f"{API}/tenders?kind=eoi").json()["total"] == 1
    assert c.get(f"{API}/tenders?due_within_days=7").json()["total"] == 1
    s = c.get(f"{API}/tenders/summary").json()
    assert (s["active"], s["due_within_7_days"], s["overdue_unsubmitted"]) == (3, 1, 1)

    # Clarification must come before submission; deadlines need a time zone.
    bad = {"clarification_deadline": _deadline(20)}
    assert c.post(f"{API}/tenders", json={**_body(), **bad}).status_code == 422
    naive = {"submission_deadline": "2030-01-01T10:00:00"}
    assert c.post(f"{API}/tenders", json={**_body(), **naive}).status_code == 422


def _body() -> dict[str, str]:
    return {
        "title": "Valid title",
        "issuer_name": "TEST Issuer",
        "kind": "rfp",
        "submission_deadline": _deadline(5),
    }


def test_bid_approval_flow_with_separation_of_duties(app: FastAPI, db: Session) -> None:
    bd_user = make_user(db, "business_development")
    bd = sign_in(app, bd_user)
    t = _tender(bd)
    tid = t["id"]
    bd.patch(f"{API}/tenders/{tid}", json={"status": "bidding"})
    req = bd.post(
        f"{API}/tenders/{tid}/requirements",
        json={"kind": "document", "description": "Valid tax clearance certificate"},
    ).json()
    bd.post(
        f"{API}/tenders/{tid}/requirements",
        json={"kind": "technical", "description": "Optional brochure", "mandatory": False},
    )

    # Mandatory requirement still pending → refused, with the open item listed.
    r = bd.post(f"{API}/tenders/{tid}/request-approval", json={})
    assert r.status_code == 409
    assert r.json()["error"]["details"]["open_requirements"] == ["Valid tax clearance certificate"]

    bd.patch(f"{API}/tenders/requirements/{req['id']}", json={"status": "met"})
    r = bd.post(f"{API}/tenders/{tid}/request-approval", json={"note": "Priced and checked"})
    assert r.status_code == 200, r.text
    assert r.json()["tender"]["status"] == "awaiting_approval"

    # Frozen while awaiting approval (notes still allowed).
    assert bd.patch(f"{API}/tenders/{tid}", json={"title": "Changed"}).status_code == 409
    assert bd.patch(f"{API}/tenders/{tid}", json={"notes": "Courier booked"}).status_code == 200

    # Business Development cannot submit or approve its own bid.
    assert bd.post(f"{API}/tenders/{tid}/submitted", json={}).status_code == 409
    queue = bd.get(f"{API}/approvals").json()
    assert queue == []
    approval_id = r.json()["approval"]["id"]
    assert (
        bd.post(f"{API}/approvals/{approval_id}/decide", json={"approve": True}).status_code == 403
    )

    director = sign_in(app, make_user(db, "director"), step_up=True)
    queue = director.get(f"{API}/approvals").json()
    assert [q["id"] for q in queue] == [approval_id] and queue[0]["can_decide"] is True
    d = director.post(f"{API}/approvals/{approval_id}/decide", json={"approve": True})
    assert d.status_code == 200, d.text
    detail = bd.get(f"{API}/tenders/{tid}").json()
    assert detail["tender"]["status"] == "approved"
    assert detail["approval"]["status"] == "approved"

    # A human records the submission; then the outcome.
    s = bd.post(f"{API}/tenders/{tid}/submitted", json={"note": "Delivered to procurement office"})
    assert s.json()["tender"]["status"] == "submitted" and s.json()["tender"]["submitted_at"]
    assert bd.post(f"{API}/tenders/{tid}/outcome", json={"result": "lost"}).status_code == 422
    won = bd.post(
        f"{API}/tenders/{tid}/outcome", json={"result": "won", "award_value": "980000.00"}
    ).json()["tender"]
    assert won["status"] == "won" and won["award_value"] == "980000.00"
    assert bd.patch(f"{API}/tenders/{tid}", json={"notes": "x"}).status_code == 409

    actions = set(
        db.execute(select(AuditEvent.action).where(AuditEvent.target_id == tid)).scalars()
    )
    assert {
        "tenders.created",
        "tenders.approval.requested",
        "approval.approved",
        "tenders.submitted",
        "tenders.outcome.won",
    } <= actions


def test_director_cannot_approve_own_request_and_rejection_returns_to_bidding(
    app: FastAPI, db: Session
) -> None:
    director = sign_in(app, make_user(db, "director"), step_up=True)
    t = _tender(director)
    director.patch(f"{API}/tenders/{t['id']}", json={"status": "bidding"})
    r = director.post(f"{API}/tenders/{t['id']}/request-approval", json={}).json()
    aid = r["approval"]["id"]
    assert director.get(f"{API}/approvals").json() == []  # own requests are never "to decide"
    own = director.post(f"{API}/approvals/{aid}/decide", json={"approve": True})
    assert own.status_code == 403 and own.json()["error"]["code"] == "self_approval_forbidden"

    second = sign_in(app, make_user(db, "director"), step_up=True)
    second.post(f"{API}/approvals/{aid}/decide", json={"approve": False, "note": "Price too low"})
    assert director.get(f"{API}/tenders/{t['id']}").json()["tender"]["status"] == "bidding"


def test_deadline_no_bid_and_permissions(app: FastAPI, db: Session) -> None:
    bd = sign_in(app, make_user(db, "business_development"))
    late = _tender(bd, submission_deadline=_deadline(-1))
    bd.patch(f"{API}/tenders/{late['id']}", json={"status": "bidding"})
    assert bd.post(f"{API}/tenders/{late['id']}/request-approval", json={}).status_code == 409

    t = _tender(bd)
    assert bd.post(f"{API}/tenders/{t['id']}/no-bid", json={"reason": ""}).status_code == 422
    nb = bd.post(f"{API}/tenders/{t['id']}/no-bid", json={"reason": "Outside our licence scope"})
    assert nb.json()["tender"]["status"] == "no_bid"

    for role in ("procurement", "finance", "logistics", "hr_admin"):
        other = sign_in(app, make_user(db, role))
        assert other.get(f"{API}/tenders").status_code == 403
