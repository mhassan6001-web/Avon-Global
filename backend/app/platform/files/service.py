"""Secure file storage: validation, private storage, permission-checked access."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.core.errors import AppError

# Allowed types: sniffed from content, and the declared extension must agree.
ALLOWED: dict[str, tuple[str, ...]] = {
    "application/pdf": (".pdf",),
    "image/png": (".png",),
    "image/jpeg": (".jpg", ".jpeg"),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (".docx",),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (".xlsx",),
    "text/csv": (".csv",),
    "text/plain": (".txt",),
}
_OFFICE_ZIP = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class UnsupportedFileError(AppError):
    status_code = 415
    code = "unsupported_file"
    message = "This file type is not allowed, or its content does not match its extension."


class FileTooLargeError(AppError):
    status_code = 413
    code = "file_too_large"


def sniff(content: bytes, filename: str) -> str:
    """Return the MIME type implied by the content, cross-checked with the extension."""
    ext = Path(filename).suffix.lower()
    if content.startswith(b"%PDF-"):
        mime = "application/pdf"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif content.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif content.startswith(b"PK\x03\x04") and ext in _OFFICE_ZIP:
        mime = _OFFICE_ZIP[ext]
    elif ext in (".csv", ".txt"):
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UnsupportedFileError() from exc
        if b"\x00" in content:
            raise UnsupportedFileError()
        mime = "text/csv" if ext == ".csv" else "text/plain"
    else:
        raise UnsupportedFileError()
    if ext not in ALLOWED[mime]:
        raise UnsupportedFileError()
    return mime


class StorageBackend(Protocol):
    def put(self, key: str, content: bytes) -> None: ...
    def get(self, key: str) -> bytes: ...


class LocalStorage:
    """Development/test backend. Production uses S3-compatible private storage (Stage 14)."""

    def __init__(self, root: str) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("invalid storage key")
        return path

    def put(self, key: str, content: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()


def storage() -> StorageBackend:
    return LocalStorage(get_settings().storage_dir)


def new_key() -> str:
    key = uuid.uuid4().hex
    return f"{key[:2]}/{key}"


def digest(content: bytes) -> bytes:
    return hashlib.sha256(content).digest()


def check_size(size: int) -> None:
    limit = get_settings().max_upload_mb * 1024 * 1024
    if size > limit:
        raise FileTooLargeError(f"Files are limited to {get_settings().max_upload_mb} MB.")
