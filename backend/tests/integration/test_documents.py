"""Stage 13: documents from validated records, permissions and the register."""

from __future__ import annotations

import io
import re
import zipfile
import zlib

import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from .helpers import make_user, sign_in
from .test_finance import _invoice, _setup
from .test_inventory_logistics import _approved_order

API = "/api/v1/documents"


def _pdf_text(data: bytes) -> bytes:
    return b"".join(
        zlib.decompress(m.group(1))
        for m in re.finditer(rb"stream\n(.*?)\nendstream", data, re.DOTALL)
    )


def test_invoice_pdf_and_word_from_the_record(app: FastAPI, db: Session) -> None:
    b = _setup(app, db)
    inv = _invoice(
        b,
        [
            {
                "description": "Desks (oak)",
                "quantity": "10",
                "unit_price": "1000",
                "account_id": b.acc["4000"],
                "tax_code_id": b.vat_out,
            }
        ],
    )
    draft = b.fin.get(f"{API}/records/invoice/{inv['id']}")
    assert draft.status_code == 200, draft.text
    assert draft.headers["content-type"] == "application/pdf"
    body = _pdf_text(draft.content)
    assert b"DRAFT - NOT ISSUED" in body and b"Desks \\(oak\\)" in body
    assert b"signature" in body  # states that no signature is applied
    assert b"legal name not yet confirmed" in body or b"profile not set up" in body

    issued = b.fin.post(f"/api/v1/finance/invoices/{inv['id']}/issue", json={}).json()
    pdf = b.fin.get(f"{API}/records/invoice/{inv['id']}")
    assert pdf.headers["x-document-version"] == "2"
    text_ = _pdf_text(pdf.content)
    assert issued["number"].encode() in text_ and b"DRAFT" not in text_
    assert b"11,650.00" in text_  # total from the record (test VAT 16.5%)
    assert issued["number"] in pdf.headers["content-disposition"]

    word = b.fin.get(f"{API}/records/invoice/{inv['id']}", params={"format": "docx"})
    assert word.status_code == 200
    with zipfile.ZipFile(io.BytesIO(word.content)) as z:
        assert issued["number"] in z.read("word/document.xml").decode()

    reg = b.fin.get(f"{API}/register", params={"subject": inv["id"]}).json()
    assert [(r["format"], r["version"]) for r in reg] == [("docx", 1), ("pdf", 2), ("pdf", 1)]
    assert all(len(r["sha256"]) == 64 for r in reg)
    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE doc_generated SET version = 9"))
    db.rollback()

    # Other departments cannot generate finance documents or see them in the register.
    logistics = sign_in(app, make_user(db, "logistics"))
    assert logistics.get(f"{API}/records/invoice/{inv['id']}").status_code == 403
    assert logistics.get(f"{API}/register", params={"subject": inv["id"]}).json() == []


def test_purchase_order_and_reports(app: FastAPI, db: Session) -> None:
    order = _approved_order(app, db)
    prc = sign_in(app, make_user(db, "procurement"))
    r = prc.get(f"{API}/records/purchase_order/{order['id']}")
    assert r.status_code == 200, r.text
    assert order["reference"].encode() in _pdf_text(r.content)
    assert prc.get(f"{API}/reports/trial_balance").status_code == 403

    b = _setup(app, db)
    tb = b.fin.get(f"{API}/reports/trial_balance")
    assert tb.status_code == 200
    assert tb.headers["content-type"].startswith("application/vnd.openxmlformats")
    with zipfile.ZipFile(io.BytesIO(tb.content)) as z:
        assert "Trial balance" in z.read("xl/worksheets/sheet1.xml").decode()
    assert b.fin.get(f"{API}/reports/receivables").status_code == 200
    assert b.fin.get(f"{API}/reports/stock").status_code == 403


def test_missing_records_are_404(app: FastAPI, db: Session) -> None:
    director = sign_in(app, make_user(db, "director"))
    missing = "00000000-0000-0000-0000-000000000000"
    assert director.get(f"{API}/records/receipt/{missing}").status_code == 404
    assert director.get(f"{API}/records/unknown/{missing}").status_code == 422
