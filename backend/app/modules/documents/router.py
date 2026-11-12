"""Documents API (``/api/v1/documents``).

Every document is generated on request from the current validated record,
checked against the caller's permission for that record type, and entered in
the register with a version number and the SHA-256 of the bytes returned.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.errors import AppError, PermissionDeniedError
from app.platform.audit import service as audit
from app.platform.authz.deps import CurrentPrincipal, DbSession, Principal

from . import builders
from .models import GeneratedDocument
from .render import docx, pdf, xlsx

router = APIRouter(prefix="/documents", tags=["documents"])
MEDIA = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
REPORTS = {
    "trial_balance": "finance.ledger.view",
    "receivables": "finance.records.view",
    "payables": "finance.records.view",
    "stock": "inventory.records.view",
}
KIND_PERMISSION = {k: perm for k, (_, perm) in builders.BUILDERS.items()} | REPORTS
KIND_PERMISSION["letterhead"] = "org.profile.view"
KIND_PERMISSION["statement"] = "finance.records.view"


class RegisterRow(BaseModel):
    id: uuid.UUID
    kind: str
    subject: str
    number: str
    format: str
    version: int
    sha256: str
    size_bytes: int
    generated_by: str
    created_at: datetime


def _need(p: Principal, permission: str) -> None:
    if not p.has(permission):
        raise PermissionDeniedError()


def _deliver(
    db: DbSession, p: Principal, kind: str, subject: str, number: str, fmt: str, data: bytes
) -> Response:
    version = (
        db.execute(
            select(func.coalesce(func.max(GeneratedDocument.version), 0)).where(
                GeneratedDocument.kind == kind,
                GeneratedDocument.subject == subject,
                GeneratedDocument.format == fmt,
            )
        ).scalar_one()
        + 1
    )
    digest = hashlib.sha256(data).hexdigest()
    row = GeneratedDocument(
        kind=kind,
        subject=subject,
        number=number,
        format=fmt,
        version=version,
        sha256=digest,
        size_bytes=len(data),
        generated_by=p.user.id,
    )
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
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", number)[:80] or kind
    return Response(
        content=data,
        media_type=MEDIA[fmt],
        headers={
            "Content-Disposition": f'attachment; filename="{safe}-v{version}.{fmt}"',
            "Cache-Control": "no-store",
            "X-Document-Version": str(version),
            "X-Document-SHA256": digest,
        },
    )


@router.get("/records/{kind}/{record_id}")
def record_document(
    kind: Literal["quotation", "invoice", "receipt", "purchase_order", "delivery_note", "rfq"],
    record_id: uuid.UUID,
    principal: CurrentPrincipal,
    db: DbSession,
    fmt: Literal["pdf", "docx"] = Query(default="pdf", alias="format"),
) -> Response:
    build, permission = builders.BUILDERS[kind]
    _need(principal, permission)
    now = datetime.now(UTC)
    doc = build(db, record_id, principal.user.display_name, now)
    data = pdf.render(doc) if fmt == "pdf" else docx.render(doc, now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return _deliver(db, principal, kind, str(record_id), doc.number, fmt, data)


@router.get("/statements/{customer_id}")
def customer_statement(
    customer_id: uuid.UUID,
    principal: CurrentPrincipal,
    db: DbSession,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    fmt: Literal["pdf", "docx", "xlsx"] = Query(default="pdf", alias="format"),
) -> Response:
    """Customer account statement (PDF, Word or Excel) from posted finance records."""
    _need(principal, "finance.records.view")
    now = datetime.now(UTC)
    end = date_to or now.astimezone(builders.TZ).date()
    start = date_from or date(end.year, 1, 1)
    if start > end:
        raise AppError(
            "The start date is after the end date.", status_code=422, code="validation_error"
        )
    doc, sheet = builders.statement(db, customer_id, start, end, principal.user.display_name, now)
    if fmt == "pdf":
        data = pdf.render(doc)
    elif fmt == "docx":
        data = docx.render(doc, now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    else:
        data = xlsx.render(sheet)
    subject = f"{customer_id}:{start.isoformat()}:{end.isoformat()}"[:80]
    return _deliver(db, principal, "statement", subject, doc.number, fmt, data)


@router.get("/reports/{name}")
def report_workbook(
    name: Literal["trial_balance", "receivables", "payables", "stock"],
    principal: CurrentPrincipal,
    db: DbSession,
    as_of: date | None = Query(default=None),
) -> Response:
    _need(principal, REPORTS[name])
    now = datetime.now(UTC)
    when = as_of or now.astimezone(builders.TZ).date()
    by = principal.user.display_name
    if name == "trial_balance":
        sheet = builders.trial_balance(db, when, by, now)
    elif name in ("receivables", "payables"):
        sheet = builders.ageing(
            db, "receivable" if name == "receivables" else "payable", when, by, now
        )
    else:
        sheet = builders.stock(db, by, now)
    subject = name if name == "stock" else f"{name}:{when.isoformat()}"
    number = f"{name.replace('_', '-')}-{when.isoformat()}"
    return _deliver(db, principal, name, subject, number, "xlsx", xlsx.render(sheet))


@router.get("/letterhead")
def letterhead(
    principal: CurrentPrincipal,
    db: DbSession,
    fmt: Literal["pdf", "docx"] = Query(default="docx", alias="format"),
) -> Response:
    """Blank company letterhead (Word to type in, or PDF to print). Every
    signed-in user may download it; it carries no signature or approval."""
    now = datetime.now(UTC)
    issuer = builders.issuer_lines(db)
    if fmt == "pdf":
        data = pdf.letterhead(issuer)
    else:
        data = docx.letterhead(issuer, now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return _deliver(db, principal, "letterhead", "letterhead", "AVEN-GLOBAL-letterhead", fmt, data)


@router.get("/register", response_model=list[RegisterRow])
def register(
    principal: CurrentPrincipal,
    db: DbSession,
    subject: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[RegisterRow]:
    """Generated versions of the document types this user may see."""
    from app.platform.identity.models import User

    kinds = [k for k, perm in KIND_PERMISSION.items() if principal.has(perm)]
    stmt = (
        select(GeneratedDocument, User.display_name)
        .join(User, User.id == GeneratedDocument.generated_by)
        .where(GeneratedDocument.kind.in_(kinds))
        .order_by(GeneratedDocument.created_at.desc())
        .limit(limit)
    )
    if subject:
        stmt = stmt.where(GeneratedDocument.subject == subject)
    return [
        RegisterRow(
            id=g.id,
            kind=g.kind,
            subject=g.subject,
            number=g.number,
            format=g.format,
            version=g.version,
            sha256=g.sha256,
            size_bytes=g.size_bytes,
            generated_by=name,
            created_at=g.created_at,
        )
        for g, name in db.execute(stmt).tuples()
    ]
