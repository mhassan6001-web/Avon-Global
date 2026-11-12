"""Stage 6: suppliers, bank-detail dual control, quotations, approval, orders."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import FastAPI
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.platform.audit.models import AuditEvent

from .helpers import make_user, sign_in

API = "/api/v1/procurement"


def _supplier(c, name: str, verify_with=None):  # type: ignore[no-untyped-def]
    s = c.post(f"{API}/suppliers", json={"name": name, "categories": "Stationery"}).json()
    if verify_with is not None:
        r = verify_with.post(
            f"{API}/suppliers/{s['id']}/verification",
            json={"status": "verified", "note": "Registration checked"},
        )
        assert r.status_code == 200, r.text
    return s


def test_bank_details_are_encrypted_masked_and_dual_controlled(app: FastAPI, db: Session) -> None:
    prc = sign_in(app, make_user(db, "procurement"))
    s = _supplier(prc, "TEST Lilongwe Stationers")
    body = {
        "bank_name": "TEST Bank",
        "account_name": "TEST Lilongwe Stationers Ltd",
        "account_number": "1002003004",
        "currency": "MWK",
        "reason": "New supplier onboarding",
    }
    r = prc.post(f"{API}/suppliers/{s['id']}/bank-change", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["pending_bank_change"] is True and r.json()["has_active_bank_account"] is False

    # Stored encrypted: the plaintext number is nowhere in the row.
    raw = db.execute(
        text("SELECT account_number_encrypted FROM prc_supplier_bank_accounts")
    ).scalar_one()
    assert b"1002003004" not in bytes(raw)

    # Procurement sees only the last four digits; a second change is refused.
    detail = prc.get(f"{API}/suppliers/{s['id']}").json()
    assert detail["bank_details_visible"] is False
    assert detail["bank_accounts"][0]["account_last4"] == "3004"
    assert "account_number" not in detail["bank_accounts"][0]
    assert prc.post(f"{API}/suppliers/{s['id']}/bank-change", json=body).status_code == 409

    # Procurement cannot approve; the Director can, after step-up.
    approvals = sign_in(app, make_user(db, "director"), step_up=True)
    queue = approvals.get("/api/v1/approvals").json()
    assert len(queue) == 1 and "3004" in queue[0]["summary"]
    assert "1002003004" not in str(queue[0])
    assert (
        prc.post(f"/api/v1/approvals/{queue[0]['id']}/decide", json={"approve": True}).status_code
        == 403
    )
    assert (
        approvals.post(
            f"/api/v1/approvals/{queue[0]['id']}/decide", json={"approve": True}
        ).status_code
        == 200
    )

    full = approvals.get(f"{API}/suppliers/{s['id']}").json()
    assert full["bank_details_visible"] is True
    assert full["bank_accounts"][0]["account_number"] == "1002003004"
    assert full["bank_accounts"][0]["status"] == "active"

    # A later change supersedes the old account only once approved.
    prc.post(f"{API}/suppliers/{s['id']}/bank-change", json={**body, "account_number": "99998888"})
    aid = approvals.get("/api/v1/approvals").json()[0]["id"]
    approvals.post(f"/api/v1/approvals/{aid}/decide", json={"approve": True})
    statuses = [
        a["status"] for a in approvals.get(f"{API}/suppliers/{s['id']}").json()["bank_accounts"]
    ]
    assert sorted(statuses) == ["active", "superseded"]

    # Audit never contains the account number; viewing full details is audited.
    details = " ".join(str(d) for d in db.execute(select(AuditEvent.details)).scalars())
    assert "1002003004" not in details and "99998888" not in details
    assert db.execute(
        select(AuditEvent.seq).where(AuditEvent.action == "procurement.supplier_bank.viewed")
    ).first()


def test_purchase_request_quotes_approval_and_order(app: FastAPI, db: Session) -> None:
    prc_user = make_user(db, "procurement")
    prc = sign_in(app, prc_user)
    director = sign_in(app, make_user(db, "director"), step_up=True)
    cheap = _supplier(prc, "TEST Cheap Supplies", verify_with=prc)
    dear = _supplier(prc, "TEST Dear Supplies", verify_with=prc)
    unverified = _supplier(prc, "TEST Unverified Supplies")
    zar = _supplier(prc, "TEST Rand Supplies", verify_with=prc)

    r = prc.post(
        f"{API}/requests",
        json={
            "title": "Office paper for Q1",
            "currency": "MWK",
            "lines": [
                {"description": "A4 paper ream", "quantity": "40", "unit": "ream"},
                {"description": "Toner cartridge", "quantity": "3"},
            ],
        },
    )
    assert r.status_code == 201, r.text
    pr = r.json()
    rid = pr["request"]["id"]
    l1, l2 = (line["id"] for line in pr["lines"])
    assert pr["request"]["reference"].startswith("PR-")

    def quote(supplier, prices, currency="MWK", **extra):  # type: ignore[no-untyped-def]
        lines = [{"request_line_id": k, "unit_price": v} for k, v in prices.items()]
        return prc.post(
            f"{API}/requests/{rid}/quotes",
            json={"supplier_id": supplier["id"], "currency": currency, "lines": lines, **extra},
        )

    assert quote(cheap, {l1: "5000", l2: "60000"}).status_code == 200
    assert quote(dear, {l1: "5500", l2: "61000"}).status_code == 200
    assert quote(unverified, {l1: "4000", l2: "50000"}).status_code == 200
    assert quote(zar, {l1: "50", l2: "600"}, currency="ZAR").status_code == 200
    partial = quote(dear, {l1: "1"}, valid_until=str(date.today() - timedelta(days=1)))
    detail = partial.json()
    totals = {q["supplier_name"]: q["total"] for q in detail["quotes"]}
    assert totals["TEST Cheap Supplies"] == "380000.00"  # 40*5000 + 3*60000
    # Cheapest complete, valid quote in the request currency; ZAR is listed, not ranked.
    cheapest = next(q for q in detail["quotes"] if q["id"] == detail["cheapest_complete_quote_id"])
    assert cheapest["supplier_name"] == "TEST Unverified Supplies"
    assert "not ranked" in detail["comparison_note"]

    quotes = {q["supplier_name"]: q for q in detail["quotes"] if q["complete"]}
    # Unverified supplier cannot be chosen; choosing a dearer quote needs a reason.
    unv = quotes["TEST Unverified Supplies"]["id"]
    assert prc.post(f"{API}/requests/{rid}/submit", json={"quote_id": unv}).status_code == 409
    dear_id = quotes["TEST Dear Supplies"]["id"]
    assert prc.post(f"{API}/requests/{rid}/submit", json={"quote_id": dear_id}).status_code == 422
    r = prc.post(
        f"{API}/requests/{rid}/submit",
        json={
            "quote_id": dear_id,
            "note": "Cheapest bidder not verified; dear one delivers in 2 days",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["request"]["status"] == "awaiting_approval"

    # Cannot order before approval; Director approves; then a PO is issued once.
    assert prc.post(f"{API}/requests/{rid}/order", json={}).status_code == 409
    aid = director.get("/api/v1/approvals").json()[0]["id"]
    assert (
        director.post(f"/api/v1/approvals/{aid}/decide", json={"approve": True}).status_code == 200
    )
    po = prc.post(f"{API}/requests/{rid}/order", json={"delivery_address": "Lilongwe HQ"})
    assert po.status_code == 200, po.text
    order = po.json()
    assert order["reference"].startswith("PO-")
    assert order["total_amount"] == "403000.00"  # 40*5500 + 3*61000
    assert [line["line_total"] for line in order["lines"]] == ["220000.00", "183000.00"]
    assert prc.post(f"{API}/requests/{rid}/order", json={}).status_code == 409

    cancelled = prc.post(f"{API}/orders/{order['id']}/cancel", json={"reason": "Budget freeze"})
    assert cancelled.json()["status"] == "cancelled"


def test_landed_cost_estimate_and_permissions(app: FastAPI, db: Session) -> None:
    prc = sign_in(app, make_user(db, "procurement"))
    r = prc.post(
        f"{API}/landed-cost",
        json={
            "goods_value": "1000",
            "supplier_currency": "USD",
            "freight": "150",
            "insurance": "10",
            "exchange_rate": "1750",
            "exchange_rate_source": "TEST rate entered by user",
            "duty_rate_pct": "10",
            "vat_rate_pct": "16.5",
            "local_charges": "250000",
            "quantity": "20",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["landed_cost"] == "2483000.00" and body["is_estimate"] is True
    assert "Estimate only" in body["note"]

    for role in ("business_development", "finance", "logistics", "hr_admin"):
        other = sign_in(app, make_user(db, role))
        assert other.get(f"{API}/suppliers").status_code == 403
