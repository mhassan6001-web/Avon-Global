"""File upload and download (``/api/v1/files``)."""

from __future__ import annotations

import uuid
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.errors import NotFoundError, PermissionDeniedError
from app.platform.audit import service as audit
from app.platform.authz.catalogue import PERMISSION_CODES
from app.platform.authz.deps import CurrentPrincipal, DbSession, Principal, client_ip, require
from app.platform.files import service
from app.platform.files.models import StoredFile
from app.platform.security import tokens

router = APIRouter(prefix="/files", tags=["files"])
SIGNED_TTL_SECONDS = 60


class FileOut(BaseModel):
    id: uuid.UUID
    original_name: str
    mime_type: str
    size_bytes: int
    module: str
    required_permission: str
    created_at: datetime


class SignedUrlOut(BaseModel):
    url: str
    expires_in_seconds: int = SIGNED_TTL_SECONDS


def _out(f: StoredFile) -> FileOut:
    return FileOut.model_validate(f, from_attributes=True)


def _authorise(principal: Principal, f: StoredFile) -> None:
    if not principal.has(f.required_permission):
        raise PermissionDeniedError("You do not have access to this file.")


@router.post("", response_model=FileOut, status_code=201)
def upload(
    request: Request,
    db: DbSession,
    principal: Principal = Depends(require("files.upload")),
    file: UploadFile = File(...),
    module: str = Form(..., max_length=64),
    required_permission: str = Form(..., max_length=120),
) -> FileOut:
    if required_permission not in PERMISSION_CODES:
        raise NotFoundError("Unknown permission.")
    # Users may only file documents into sections they themselves can access.
    if not principal.has(required_permission):
        raise PermissionDeniedError("You cannot store files in a section you cannot access.")
    limit = get_settings().max_upload_mb * 1024 * 1024
    content = file.file.read(limit + 1)
    service.check_size(len(content))
    name = (file.filename or "upload").replace("/", "_").replace("\\", "_")[:255]
    mime = service.sniff(content, name)
    key = service.new_key()
    service.storage().put(key, content)
    record = StoredFile(
        module=module,
        required_permission=required_permission,
        original_name=name,
        storage_key=key,
        mime_type=mime,
        size_bytes=len(content),
        sha256=service.digest(content),
        owner_id=principal.user.id,
    )
    db.add(record)
    db.flush()
    audit.record(
        db,
        action="files.uploaded",
        actor_id=principal.user.id,
        target_type="file",
        target_id=record.id,
        details={"module": module, "mime": mime, "permission": required_permission},
        ip=client_ip(request),
    )
    db.commit()
    return _out(record)


def _get(db: DbSession, file_id: uuid.UUID) -> StoredFile:
    f = db.get(StoredFile, file_id)
    if f is None:
        raise NotFoundError("File not found.")
    return f


def _download(
    db: DbSession, principal: Principal, f: StoredFile, request: Request, via: str
) -> Response:
    content = service.storage().get(f.storage_key)
    audit.record(
        db,
        action="files.downloaded",
        actor_id=principal.user.id,
        target_type="file",
        target_id=f.id,
        details={"via": via},
        ip=client_ip(request),
    )
    db.commit()
    return Response(
        content,
        media_type=f.mime_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(f.original_name)}",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{file_id}", response_model=FileOut)
def metadata(file_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> FileOut:
    f = _get(db, file_id)
    _authorise(principal, f)
    return _out(f)


@router.get("/{file_id}/download")
def download(
    file_id: uuid.UUID, request: Request, principal: CurrentPrincipal, db: DbSession
) -> Response:
    f = _get(db, file_id)
    _authorise(principal, f)
    return _download(db, principal, f, request, "direct")


@router.post("/{file_id}/signed-url", response_model=SignedUrlOut)
def signed_url(file_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> SignedUrlOut:
    f = _get(db, file_id)
    _authorise(principal, f)
    token = tokens.sign(
        f"{f.id}:{principal.user.id}", get_settings().signing_secret, SIGNED_TTL_SECONDS
    )
    return SignedUrlOut(url=f"/api/v1/files/signed/{token}")


@router.get("/signed/{token}")
def signed_download(
    token: str, request: Request, principal: CurrentPrincipal, db: DbSession
) -> Response:
    payload = tokens.verify_signed(token, get_settings().signing_secret)
    if payload is None:
        raise PermissionDeniedError("This download link has expired.")
    file_id, user_id = payload.split(":", 1)
    if user_id != str(principal.user.id):
        raise PermissionDeniedError("This download link belongs to another user.")
    f = _get(db, uuid.UUID(file_id))
    _authorise(principal, f)  # permission re-checked at use time
    return _download(db, principal, f, request, "signed")
