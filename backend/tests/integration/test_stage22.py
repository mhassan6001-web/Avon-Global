"""Stage 22: contracts, service agreements and tender packs."""

from __future__ import annotations

import io
import re
import zipfile
import zlib
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from .helpers import make_user, sign_in

API = "/api/v1"
TODAY = date.today()


def _pdf_text(data: bytes) -> bytes:
    return b"".join(
        zlib.decompress(m.group(1))
        for m in re.finditer(rb"/FlateDecode >>\nstream\n(.*?)\nendstream", data, re.DOTALL)
    )


def test_contract_draft_finalise_and_freeze(app: FastAPI, db: Session) -> None:
    bd = sign_in(app, make_user(db, "business_development"))
    director = sign_in(app, make_user(db, "director"))
    customer = bd.post(f"{API}/crm/customers", json={"name": "TEST Contract Customer"}).json()
    body = {
        "kind": "service",
        "party_type": "customer",
        "party_id": customer["id"],
        "title": "TEST maintenance services",
        "start_date": str(TODAY),
        "end_date": str(TODAY + timedelta(days=365)),
        "currency": "MWK",
        "value": "1200000",
        "clauses": [
            {"heading": "Scope", "text": "TEST scope written by the company (not legal advice)."},
            {"heading": "Payment", "text": "TEST payment terms."},
        ],
    }
    assert bd.post(f"{API}/documents/contracts", json={**body, "currency": None}).status_code == 422
    r = bd.post(f"{API}/documents/contracts", json=body)
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["reference"] == f"CON-{TODAY.year}-00001" and c["status"] == "draft"

    draft = bd.get(f"{API}/documents/contracts/{c['id']}/file")
    page = _pdf_text(draft.content)
    assert b"DRAFT - NOT FINAL" in page and b"TEST scope written by the company" in page
    assert b"Signature: ____" in page  # blank signature lines only

    body["clauses"].append({"heading": "Term", "text": "TEST twelve months."})
    assert len(bd.put(f"{API}/documents/contracts/{c['id']}", json=body).json()["clauses"]) == 3
    assert bd.post(f"{API}/documents/contracts/{c['id']}/finalise").status_code == 403
    final = director.post(f"{API}/documents/contracts/{c['id']}/finalise")
    assert final.status_code == 200 and final.json()["status"] == "final"
    assert bd.put(f"{API}/documents/contracts/{c['id']}", json=body).status_code == 409
    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE doc_contracts SET title = 'changed'"))
    db.rollback()
    word = bd.get(f"{API}/documents/contracts/{c['id']}/file", params={"format": "docx"})
    with zipfile.ZipFile(io.BytesIO(word.content)) as z:
        xml = z.read("word/document.xml").decode()
    assert "TEST twelve months." in xml and "DRAFT" not in xml

    # Departments see only the contracts of their own party type.
    prc = sign_in(app, make_user(db, "procurement"))
    assert prc.get(f"{API}/documents/contracts").json() == []
    assert prc.get(f"{API}/documents/contracts/{c['id']}/file").status_code == 403
    assert (
        sign_in(app, make_user(db, "logistics")).get(f"{API}/documents/contracts").status_code
        == 403
    )


def test_tender_pack_zip(app: FastAPI, db: Session) -> None:
    bd = sign_in(app, make_user(db, "business_development"))
    deadline = (datetime.now(UTC) + timedelta(days=10)).isoformat()
    t = bd.post(
        f"{API}/tenders",
        json={
            "title": "TEST supply of laptops",
            "issuer_name": "TEST Ministry",
            "kind": "rfq",
            "submission_deadline": deadline,
        },
    )
    assert t.status_code == 201, t.text
    tender = t.json()["tender"]
    req = bd.post(
        f"{API}/tenders/{tender['id']}/requirements",
        json={
            "kind": "document",
            "description": "TEST tax clearance certificate",
            "mandatory": True,
        },
    )
    assert req.status_code == 201, req.text

    pack = bd.get(f"{API}/documents/tender-packs/{tender['id']}")
    assert pack.status_code == 200, pack.text
    assert pack.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(pack.content)) as z:
        names = z.namelist()
        cover = _pdf_text(z.read("00-cover.pdf"))
        checklist = _pdf_text(z.read("01-requirements-checklist.pdf"))
    assert names[:3] == ["00-cover.pdf", "00-cover.docx", "01-requirements-checklist.pdf"]
    assert b"QUOTATION SUBMISSION" in cover and b"TEST Ministry" in cover
    assert b"DRAFT - BID NOT YET APPROVED" in cover and b"Not attached" in cover
    assert b"TEST tax clearance certificate" in checklist
    db.expire_all()
    # Generating a pack never submits the tender.
    assert db.execute(text("SELECT status FROM tnd_tenders")).scalar() != "submitted"
    assert db.execute(text("SELECT format FROM doc_generated")).scalar() == "zip"
    other = sign_in(app, make_user(db, "finance"))
    assert other.get(f"{API}/documents/tender-packs/{tender['id']}").status_code == 403
