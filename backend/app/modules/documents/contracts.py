# ruff: noqa: E501  (long literal strings read better unwrapped)
"""Contracts, service agreements and tender packs (Stage 22).

The system supplies layout, numbering and the company block. It supplies no
legal wording: every clause is written by the company and should be reviewed
by a lawyer. Signature lines are printed blank; the system never signs.
"""

from __future__ import annotations

import hashlib
import io
import re
import uuid
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.modules.crm.models import Customer
from app.modules.finance import posting
from app.modules.procurement.models import Supplier
from app.modules.tenders.models import Requirement, Tender
from app.platform.audit import service as audit
from app.platform.authz.deps import CurrentPrincipal, DbSession, Principal
from app.platform.files import service as files
from app.platform.files.models import StoredFile

from . import builders
from .model import Column, Document
from .models import BusinessContract as Contract
from .models import GeneratedDocument
from .render import docx, pdf

router = APIRouter(prefix="/documents", tags=["documents"])
PERMS = {
    # party type: (view, edit, finalise)
    "customer": ("crm.records.view", "crm.records.edit", "crm.quotation.approve"),
    "supplier": (
        "procurement.records.view",
        "procurement.records.edit",
        "procurement.order.approve",
    ),
}
SIGNATURE = "Name: ______________________   Signature: ______________________   Date: ____________"


class ContractRuleError(AppError):
    status_code = 422
    code = "contract_rule"


class Clause(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    heading: str = Field(min_length=2, max_length=120)
    text: str = Field(min_length=2, max_length=1500)


class ContractIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: Literal["supply", "service"]
    party_type: Literal["customer", "supplier"]
    party_id: uuid.UUID
    title: str = Field(min_length=2, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    currency: Literal["MWK", "USD", "ZAR", "ZMW"] | None = None
    value: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    clauses: list[Clause] = Field(min_length=1, max_length=60)

    @model_validator(mode="after")
    def _check(self) -> ContractIn:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("The end date cannot be before the start date.")
        if (self.value is None) != (self.currency is None):
            raise ValueError("Give both the contract value and its currency, or neither.")
        return self


class ContractOut(BaseModel):
    id: uuid.UUID
    reference: str
    kind: str
    party_type: str
    party_id: uuid.UUID
    party_name: str
    title: str
    start_date: date | None
    end_date: date | None
    currency: str | None
    value: Decimal | None
    clauses: list[Clause]
    status: str
    created_at: datetime


def _need(p: Principal, permission: str) -> None:
    if not p.has(permission):
        raise PermissionDeniedError()


def _party(db: Session, party_type: str, party_id: uuid.UUID) -> Customer | Supplier:
    row: Customer | Supplier | None = (
        db.get(Customer, party_id) if party_type == "customer" else db.get(Supplier, party_id)
    )
    if row is None:
        raise ContractRuleError("Choose an existing customer or supplier.")
    return row


def _get(db: Session, contract_id: uuid.UUID, lock: bool = False) -> Contract:
    row = db.get(Contract, contract_id, with_for_update=lock)
    if row is None:
        raise NotFoundError("Contract not found.")
    return row


def _out(db: Session, row: Contract) -> ContractOut:
    return ContractOut(
        id=row.id,
        reference=row.reference,
        kind=row.kind,
        party_type=row.party_type,
        party_id=row.party_id,
        party_name=_party(db, row.party_type, row.party_id).name,
        title=row.title,
        start_date=row.start_date,
        end_date=row.end_date,
        currency=row.currency,
        value=row.value,
        clauses=[Clause(**c) for c in row.clauses],
        status=row.status,
        created_at=row.created_at,
    )


@router.get("/contracts", response_model=list[ContractOut])
def list_contracts(principal: CurrentPrincipal, db: DbSession) -> list[ContractOut]:
    """Contracts for the party types this user may see."""
    types = [t for t, (view, _, _) in PERMS.items() if principal.has(view)]
    if not types:
        raise PermissionDeniedError()
    rows = db.execute(
        select(Contract)
        .where(Contract.party_type.in_(types))
        .order_by(Contract.created_at.desc())
        .limit(200)
    ).scalars()
    return [_out(db, r) for r in rows]


@router.post("/contracts", response_model=ContractOut, status_code=201)
def create_contract(body: ContractIn, principal: CurrentPrincipal, db: DbSession) -> ContractOut:
    _need(principal, PERMS[body.party_type][1])
    _party(db, body.party_type, body.party_id)
    today = posting.now().date()
    row = Contract(
        reference=posting.next_number(db, "CON", today),
        created_by=principal.user.id,
        **body.model_dump(mode="json", exclude={"clauses", "start_date", "end_date", "value"}),
        start_date=body.start_date,
        end_date=body.end_date,
        value=body.value,
        clauses=[c.model_dump() for c in body.clauses],
    )
    db.add(row)
    db.flush()
    audit.record(
        db,
        action="documents.contract.created",
        actor_id=principal.user.id,
        target_type="doc_contract",
        target_id=row.id,
        details={"reference": row.reference, "party_type": row.party_type},
    )
    db.commit()
    return _out(db, row)


@router.put("/contracts/{contract_id}", response_model=ContractOut)
def update_contract(
    contract_id: uuid.UUID, body: ContractIn, principal: CurrentPrincipal, db: DbSession
) -> ContractOut:
    row = _get(db, contract_id, lock=True)
    _need(principal, PERMS[row.party_type][1])
    if row.status != "draft":
        raise ConflictError("A final contract cannot be changed. Prepare a new one.")
    if body.party_type != row.party_type:
        raise ContractRuleError("The party type cannot be changed.")
    _party(db, body.party_type, body.party_id)
    for name in ("kind", "party_id", "title", "start_date", "end_date", "currency", "value"):
        setattr(row, name, getattr(body, name))
    row.clauses = [c.model_dump() for c in body.clauses]
    row.updated_at = posting.now()
    audit.record(
        db,
        action="documents.contract.updated",
        actor_id=principal.user.id,
        target_type="doc_contract",
        target_id=row.id,
        details={"reference": row.reference},
    )
    db.commit()
    return _out(db, row)


@router.post("/contracts/{contract_id}/finalise", response_model=ContractOut)
def finalise_contract(
    contract_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession
) -> ContractOut:
    """Director only: freeze the text. This is not a signature or legal approval."""
    row = _get(db, contract_id, lock=True)
    _need(principal, PERMS[row.party_type][2])
    if row.status != "draft":
        raise ConflictError("This contract is already final.")
    row.status, row.finalised_by, row.finalised_at = "final", principal.user.id, posting.now()
    audit.record(
        db,
        action="documents.contract.finalised",
        actor_id=principal.user.id,
        target_type="doc_contract",
        target_id=row.id,
        details={"reference": row.reference},
    )
    db.commit()
    return _out(db, row)


def contract_document(db: Session, row: Contract, by: str, now: datetime) -> Document:
    party = _party(db, row.party_type, row.party_id)
    meta = [("Type", "Supply contract" if row.kind == "supply" else "Service agreement")]
    if row.start_date:
        meta.append(("Start date", builders.day(row.start_date)))
    if row.end_date:
        meta.append(("End date", builders.day(row.end_date)))
    if row.value is not None and row.currency:
        meta.append(("Contract value", f"{row.currency} {builders.money(row.value)}"))
    issuer = builders.issuer_lines(db)
    return Document(
        kind="Service agreement" if row.kind == "service" else "Contract",
        number=row.reference,
        issuer=issuer,
        recipient_title="Between AVEN GLOBAL and",
        recipient=[x for x in (party.name, getattr(party, "city", None), party.email) if x],
        meta=meta,
        columns=[Column("No.", 0.6), Column("Clause", 2.4), Column("Terms", 7)],
        rows=[[str(i), c["heading"], c["text"]] for i, c in enumerate(row.clauses, start=1)],
        notes=[
            f"Subject: {row.title}",
            f"Signed for and on behalf of {issuer[0]}:",
            SIGNATURE,
            f"Signed for and on behalf of {party.name}:",
            SIGNATURE,
        ],
        footer=builders.footer(by, now),
        banners=[] if row.status == "final" else ["DRAFT - NOT FINAL"],
    )


def _register(
    db: Session, p: Principal, kind: str, subject: str, number: str, fmt: str, data: bytes
) -> tuple[int, str]:
    from .router import next_version

    version = next_version(db, kind, subject, fmt)
    digest = hashlib.sha256(data).hexdigest()
    row = GeneratedDocument(
        kind=kind, subject=subject, number=number, format=fmt, version=version,
        sha256=digest, size_bytes=len(data), generated_by=p.user.id,
    )  # fmt: skip
    db.add(row)
    db.flush()
    audit.record(
        db,
        action="documents.generated",
        actor_id=p.user.id,
        target_type="document",
        target_id=row.id,
        details={
            "kind": kind,
            "number": number,
            "format": fmt,
            "version": version,
            "sha256": digest,
        },
    )
    db.commit()
    return version, digest


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:80] or "document"


@router.get("/contracts/{contract_id}/file")
def contract_file(
    contract_id: uuid.UUID,
    principal: CurrentPrincipal,
    db: DbSession,
    fmt: Literal["pdf", "docx"] = Query(default="pdf", alias="format"),
) -> Response:
    row = _get(db, contract_id)
    _need(principal, PERMS[row.party_type][0])
    now = datetime.now(UTC)
    doc = contract_document(db, row, principal.user.display_name, now)
    data = pdf.render(doc) if fmt == "pdf" else docx.render(doc, now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    version, digest = _register(db, principal, "contract", str(row.id), row.reference, fmt, data)
    media = (
        "application/pdf"
        if fmt == "pdf"
        else ("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    )
    return Response(
        content=data,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="{_safe(row.reference)}-v{version}.{fmt}"',
            "Cache-Control": "no-store",
            "X-Document-Version": str(version),
            "X-Document-SHA256": digest,
        },
    )


# --- Tender packs --------------------------------------------------------------------

PACK_TITLE = {
    "eoi": "Expression of interest",
    "rfq": "Quotation submission",
    "rfp": "Proposal submission",
    "itb": "Bid submission",
    "other": "Tender submission",
}


def _tender_documents(
    db: Session, tender: Tender, reqs: list[Requirement], by: str, now: datetime
) -> tuple[Document, Document]:
    issuer = builders.issuer_lines(db)
    title = PACK_TITLE.get(tender.kind, "Tender submission")
    meta = [
        ("Our reference", tender.reference),
        ("Their reference", tender.issuer_reference or "—"),
        (
            "Submission deadline",
            f"{tender.submission_deadline.astimezone(builders.TZ):%d %b %Y %H:%M}",
        ),
        ("Submission method", (tender.submission_method or "—").replace("_", " ")),
    ]
    cover = Document(
        kind=title,
        number=tender.reference,
        issuer=issuer,
        recipient_title="To",
        recipient=[tender.issuer_name],
        meta=meta,
        columns=[Column("No.", 0.6), Column("Enclosed document", 7), Column("Included", 1.6)],
        rows=[
            [str(i), r.description, "Yes" if r.file_id else "Not attached"]
            for i, r in enumerate(reqs, start=1)
        ]
        or [["", "No requirements are recorded for this tender.", ""]],
        notes=[
            f"Subject: {tender.title}",
            f"{issuer[0]} submits the enclosed documents in response to the above.",
            f"Signed for and on behalf of {issuer[0]}:",
            SIGNATURE,
        ],
        footer=builders.footer(by, now),
        banners=[]
        if tender.status in ("approved", "submitted", "won", "lost")
        else ["DRAFT - BID NOT YET APPROVED FOR SUBMISSION"],
    )
    checklist = Document(
        kind="Requirements checklist",
        number=tender.reference,
        issuer=issuer,
        recipient_title="Tender",
        recipient=[tender.title, tender.issuer_name],
        meta=meta,
        columns=[
            Column("No.", 0.6),
            Column("Type", 1.5),
            Column("Requirement", 5.5),
            Column("Mandatory", 1.3),
            Column("Status", 1.5),
        ],
        rows=[
            [
                str(i),
                r.kind,
                r.description,
                "Yes" if r.mandatory else "No",
                r.status.replace("_", " "),
            ]
            for i, r in enumerate(reqs, start=1)
        ]
        or [["", "", "No requirements recorded.", "", ""]],
        notes=[
            "Internal working document. Not part of the submission unless you choose to include it."
        ],
        footer=builders.footer(by, now),
        banners=[],
    )
    return cover, checklist


@router.get("/tender-packs/{tender_id}")
def tender_pack(tender_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> Response:
    """ZIP: cover document, requirements checklist and the files attached to
    the tender's requirements. Generating a pack does not submit anything."""
    _need(principal, "tenders.records.view")
    tender = db.get(Tender, tender_id)
    if tender is None:
        raise NotFoundError("Tender not found.")
    reqs = list(
        db.execute(
            select(Requirement)
            .where(Requirement.tender_id == tender.id)
            .order_by(Requirement.created_at)
        ).scalars()
    )
    now = datetime.now(UTC)
    cover, checklist = _tender_documents(db, tender, reqs, principal.user.display_name, now)
    buf = io.BytesIO()
    missing: list[str] = []
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("00-cover.pdf", pdf.render(cover))
        z.writestr("00-cover.docx", docx.render(cover, now.strftime("%Y-%m-%dT%H:%M:%SZ")))
        z.writestr("01-requirements-checklist.pdf", pdf.render(checklist))
        for i, r in enumerate(reqs, start=1):
            stored = db.get(StoredFile, r.file_id) if r.file_id else None
            if stored is None:
                continue
            try:
                content = files.storage().get(stored.storage_key)
            except OSError:
                missing.append(stored.original_name)
                continue
            z.writestr(f"{i + 1:02d}-{_safe(stored.original_name)}", content)
        if missing:
            z.writestr(
                "MISSING-FILES.txt",
                "These attached files could not be read:\n" + "\n".join(missing),
            )
    data = buf.getvalue()
    version, digest = _register(
        db, principal, "tender_pack", str(tender.id), tender.reference, "zip", data
    )
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{_safe(tender.reference)}-pack-v{version}.zip"',
            "Cache-Control": "no-store",
            "X-Document-Version": str(version),
            "X-Document-SHA256": digest,
        },
    )
