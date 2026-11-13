"""Stage 16: company identity with print approval, approval rules, quotations,
and JARVIS model routing."""

from __future__ import annotations

import re
import zlib
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from .helpers import make_user, sign_in
from .test_finance import _setup

API = "/api/v1"
TODAY = date.today()


def _pdf_text(data: bytes) -> bytes:
    return b"".join(
        zlib.decompress(m.group(1))
        for m in re.finditer(rb"/FlateDecode >>\nstream\n(.*?)\nendstream", data, re.DOTALL)
    )


def _profile(**extra: Any) -> dict[str, Any]:
    return {
        "trading_name": "AVEN GLOBAL",
        "legal_name": "TEST Legal Name",
        "registration_status": "registered",
        "registration_number": "TEST-REG-0001",
        "headquarters_city": "Lilongwe",
        "headquarters_country_code": "MW",
        "functional_currency": "MWK",
        **extra,
    }


def test_tax_numbers_stay_off_documents_until_approved_for_print(app: FastAPI, db: Session) -> None:
    director = sign_in(app, make_user(db, "director"), step_up=True)
    staff = sign_in(app, make_user(db, "logistics"))
    # Approving something for print without a value is refused.
    r = director.put(f"{API}/organisation/profile", json=_profile(print_tpin=True))
    assert r.status_code == 422
    r = director.put(
        f"{API}/organisation/profile",
        json=_profile(
            address_line1="TEST Street 1",
            phone="+265 000 000",
            tpin="TEST-TPIN",
            vat_number="TEST-VAT",
        ),
    )
    assert r.status_code == 200, r.text
    page = _pdf_text(staff.get(f"{API}/documents/letterhead", params={"format": "pdf"}).content)
    assert b"TEST Legal Name" in page and b"Registration no. TEST-REG-0001" in page
    for hidden in (b"TEST-TPIN", b"TEST-VAT", b"TEST Street 1", b"+265 000 000"):
        assert hidden not in page

    r = director.put(
        f"{API}/organisation/profile",
        json=_profile(
            address_line1="TEST Street 1",
            phone="+265 000 000",
            tpin="TEST-TPIN",
            vat_number="TEST-VAT",
            print_address=True,
            print_tpin=True,
        ),
    )
    assert r.status_code == 200, r.text
    page = _pdf_text(staff.get(f"{API}/documents/letterhead", params={"format": "pdf"}).content)
    assert b"TEST Street 1" in page and b"TPIN TEST-TPIN" in page
    assert b"TEST-VAT" not in page and b"+265 000 000" not in page
    # Staff cannot change company identity.
    assert staff.put(f"{API}/organisation/profile", json=_profile()).status_code == 403
    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE organisation_profile SET print_vat = true, vat_number = NULL"))
    db.rollback()


def _quote(customer: str, price: str = "1000", **extra: Any) -> dict[str, Any]:
    return {
        "customer_id": customer,
        "title": "TEST office furniture",
        "quote_date": str(TODAY),
        "valid_until": str(TODAY + timedelta(days=30)),
        "terms": "TEST terms: 50% deposit",
        "lines": [{"description": "Desk", "quantity": "10", "unit_price": price}],
        **extra,
    }


def test_quotation_lifecycle_numbering_tax_and_freeze(app: FastAPI, db: Session) -> None:
    b = _setup(app, db)  # finance books with a TEST output tax code at 16.5%
    director = b.director
    assert (
        director.put(f"{API}/approvals/rules/crm_quotation", json={"enabled": False}).status_code
        == 200
    )
    bd = sign_in(app, make_user(db, "business_development"))
    codes = bd.get(f"{API}/crm/quotations/tax-codes").json()
    assert [c["code"] for c in codes] == ["VAT-OUT"]

    body = _quote(b.customer)
    body["lines"][0]["tax_code_id"] = codes[0]["id"]
    q = bd.post(f"{API}/crm/quotations", json=body)
    assert q.status_code == 201, q.text
    q = q.json()
    assert q["number"] is None and q["status"] == "draft"
    assert (q["subtotal"], q["tax_total"], q["total"]) == ("10000.00", "1650.00", "11650.00")

    draft = _pdf_text(bd.get(f"{API}/documents/records/quotation/{q['id']}").content)
    assert b"DRAFT - NOT ISSUED" in draft and b"TEST terms: 50% deposit" in draft

    body["lines"].append({"description": "Chair", "quantity": "2", "unit_price": "500"})
    q = bd.put(f"{API}/crm/quotations/{q['id']}", json=body).json()
    assert q["total"] == "12650.00" and len(q["lines"]) == 2

    issued = bd.post(f"{API}/crm/quotations/{q['id']}/issue").json()
    assert issued["status"] == "issued" and issued["number"] == f"QUO-{TODAY.year}-00001"
    assert bd.put(f"{API}/crm/quotations/{q['id']}", json=body).status_code == 409
    assert bd.post(f"{API}/crm/quotations/{q['id']}/issue").status_code == 409
    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE crm_quotations SET total = 1"))
    db.rollback()
    with pytest.raises(DBAPIError):
        db.execute(text("DELETE FROM crm_quotation_lines"))
    db.rollback()

    pdf = _pdf_text(bd.get(f"{API}/documents/records/quotation/{q['id']}").content)
    assert issued["number"].encode() in pdf and b"DRAFT" not in pdf and b"12,650.00" in pdf
    done = bd.post(f"{API}/crm/quotations/{q['id']}/outcome", json={"status": "accepted"})
    assert done.json()["status"] == "accepted"
    # Other departments cannot see quotations or their documents.
    other = sign_in(app, make_user(db, "logistics"))
    assert other.get(f"{API}/crm/quotations").status_code == 403
    assert other.get(f"{API}/documents/records/quotation/{q['id']}").status_code == 403


def test_approval_limit_and_sole_approver(app: FastAPI, db: Session) -> None:
    director_user = make_user(db, "director")
    director = sign_in(app, director_user, step_up=True)
    customer = director.post(f"{API}/crm/customers", json={"name": "TEST Limit Customer"}).json()
    rules = director.put(
        f"{API}/approvals/rules/crm_quotation", json={"enabled": True, "threshold": "50000"}
    )
    assert rules.status_code == 200, rules.text
    assert (
        director.put(f"{API}/approvals/rules/payroll_run", json={"enabled": False}).status_code
        == 409
    )  # fixed controls cannot be switched off
    bd = sign_in(app, make_user(db, "business_development"))
    assert bd.get(f"{API}/approvals/rules").status_code == 403

    small = bd.post(f"{API}/crm/quotations", json=_quote(customer["id"], "100")).json()
    assert bd.post(f"{API}/crm/quotations/{small['id']}/issue").json()["status"] == "issued"

    big = bd.post(f"{API}/crm/quotations", json=_quote(customer["id"], "9000")).json()
    waiting = bd.post(f"{API}/crm/quotations/{big['id']}/issue").json()
    assert waiting["status"] == "awaiting_approval" and waiting["number"] is None
    mine = bd.get(f"{API}/approvals", params={"view": "mine"}).json()
    assert mine[0]["blocked_reason"] is None  # the Director can decide a staff request
    pending = director.get(f"{API}/approvals").json()
    approval = next(a for a in pending if a["subject_id"] == big["id"])
    assert (
        director.post(
            f"{API}/approvals/{approval['id']}/decide", json={"approve": True}
        ).status_code
        == 200
    )
    after = bd.get(f"{API}/crm/quotations/{big['id']}").json()
    assert after["status"] == "issued" and after["number"].startswith("QUO-")

    # The Director holds the approval permission and issues their own quotation directly.
    own = director.post(f"{API}/crm/quotations", json=_quote(customer["id"], "9000")).json()
    assert director.post(f"{API}/crm/quotations/{own['id']}/issue").json()["status"] == "issued"


def test_director_raised_restricted_request_is_blocked_without_second_approver(
    app: FastAPI, db: Session
) -> None:
    from app.platform.approvals import service as approvals
    from app.platform.authz.deps import Principal
    from app.platform.identity import service as identity
    from app.platform.identity.models import User

    # Make this Director the only active one for the check below.
    director_user = make_user(db, "director")
    others = [
        u
        for u in db.query(User).filter(User.status == "active", User.id != director_user.user.id)
        if "finance.transaction.approve" in identity.permissions_of(db, u)
    ]
    for u in others:
        u.status = "suspended"
    db.commit()
    try:
        director = sign_in(app, director_user, step_up=True)
        me = director.get(f"{API}/auth/me").json()
        principal = Principal(
            session=None,  # type: ignore[arg-type]
            user=director_user.user,
            role=identity.role_of(db, director_user.user),
            permissions=frozenset(me["permissions"]),
        )
        req = approvals.create_request(
            db,
            principal=principal,
            subject_type="test_subject",
            subject_id="x",
            permission_required="finance.transaction.approve",
            summary="TEST restricted request raised by the Director",
        )
        db.commit()
        mine = director.get(f"{API}/approvals", params={"view": "mine"}).json()
        row = next(a for a in mine if a["id"] == str(req.id))
        assert row["can_decide"] is False
        assert "no second authorised approver" in row["blocked_reason"]
        r = director.post(f"{API}/approvals/{req.id}/decide", json={"approve": True})
        assert r.status_code == 403 and r.json()["error"]["code"] == "self_approval_forbidden"
        rule = next(
            x for x in director.get(f"{API}/approvals/rules").json() if x["key"] == "payroll_run"
        )
        assert rule["second_approver_exists"] is False and rule["configurable"] is False
    finally:
        for u in others:
            u.status = "active"
        db.commit()


def test_jarvis_uses_the_advanced_model_only_when_asked(app: FastAPI, db: Session) -> None:
    director = sign_in(app, make_user(db, "director"))
    status = director.get(f"{API}/jarvis/status").json()
    assert status["advanced_model"] == "claude-opus-5-5"
    conv = director.post(f"{API}/jarvis/conversations", json={}).json()["id"]
    url = f"{API}/jarvis/conversations/{conv}/messages"
    assert director.post(url, json={"text": "hello"}).status_code == 200
    assert director.post(url, json={"text": "hello again", "depth": "advanced"}).status_code == 200
    models = [m for (m,) in db.execute(text("SELECT model FROM ai_usage ORDER BY created_at"))]
    assert models == ["fake-jarvis", "claude-opus-5-5"]
    assert director.post(url, json={"text": "x", "depth": "max"}).status_code == 422


def test_customer_statement_and_rfq_documents(app: FastAPI, db: Session) -> None:
    """Stage 17: statements from posted records; request-for-quotation documents."""
    import io
    import zipfile

    from .test_finance import _invoice
    from .test_inventory_logistics import _approved_order

    b = _setup(app, db)
    inv = _invoice(
        b,
        [
            {
                "description": "Desks",
                "quantity": "10",
                "unit_price": "1000",
                "account_id": b.acc["4000"],
            }
        ],
    )
    draft_only = _invoice(
        b,
        [
            {
                "description": "Never issued",
                "quantity": "1",
                "unit_price": "77",
                "account_id": b.acc["4000"],
            }
        ],
    )
    issued = b.fin.post(f"{API}/finance/invoices/{inv['id']}/issue", json={}).json()
    receipt = b.fin.post(
        f"{API}/finance/receipts",
        json={
            "customer_id": b.customer,
            "receipt_date": str(TODAY),
            "currency": "MWK",
            "amount": "4000",
            "bank_account_id": b.acc["1000"],
            "method": "bank_transfer",
            "allocations": [{"invoice_id": inv["id"], "amount": "4000"}],
        },
    )
    assert receipt.status_code == 201, receipt.text

    st = b.fin.get(f"{API}/finance/reports/statement", params={"customer_id": b.customer}).json()
    assert [r["kind"] for r in st["rows"]] == ["invoice", "receipt"]
    assert st["rows"][0]["number"] == issued["number"]
    assert st["rows"][-1]["balance"] == "6000.00"
    assert st["totals"] == [
        {
            "currency": "MWK",
            "opening": "0",
            "invoiced": "10000.00",
            "received": "4000.00",
            "credited": "0",
            "closing": "6000.00",
        }
    ]
    assert draft_only["id"]  # the draft invoice never appears on a statement
    # A later period carries the balance forward as the opening balance.
    later = b.fin.get(
        f"{API}/finance/reports/statement",
        params={
            "customer_id": b.customer,
            "date_from": str(TODAY + timedelta(days=1)),
            "date_to": str(TODAY + timedelta(days=30)),
        },
    ).json()
    assert later["rows"] == [] and later["totals"][0]["opening"] == "6000.00"

    pdf = b.fin.get(f"{API}/documents/statements/{b.customer}")
    assert pdf.status_code == 200, pdf.text
    page = _pdf_text(pdf.content)
    assert b"STATEMENT OF ACCOUNT" in page and b"6,000.00" in page and b"Never issued" not in page
    xlsx = b.fin.get(f"{API}/documents/statements/{b.customer}", params={"format": "xlsx"})
    with zipfile.ZipFile(io.BytesIO(xlsx.content)) as z:
        assert issued["number"] in z.read("xl/worksheets/sheet1.xml").decode()
    staff = sign_in(app, make_user(db, "logistics"))
    assert staff.get(f"{API}/documents/statements/{b.customer}").status_code == 403
    assert (
        staff.get(
            f"{API}/finance/reports/statement", params={"customer_id": b.customer}
        ).status_code
        == 403
    )

    order = _approved_order(app, db)
    prc = sign_in(app, make_user(db, "procurement"))
    request_id = prc.get(f"{API}/procurement/requests").json()["items"][0]["id"]
    rfq = prc.get(f"{API}/documents/records/rfq/{request_id}")
    assert rfq.status_code == 200, rfq.text
    text_ = _pdf_text(rfq.content)
    assert b"REQUEST FOR QUOTATION" in text_ and b"Office chair" in text_
    assert b"not an order" in text_ and b"Your unit price" in text_
    assert order["reference"]
    assert staff.get(f"{API}/documents/records/rfq/{request_id}").status_code == 403
