"""Random tokens, hashing for storage, and short-lived signed values."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time


def new_token(nbytes: int = 32) -> str:
    """A URL-safe random token (256 bits by default)."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> bytes:
    """SHA-256 of a token. Only this hash is ever stored."""
    return hashlib.sha256(token.encode("utf-8")).digest()


def tokens_equal(a: bytes, b: bytes) -> bool:
    return hmac.compare_digest(a, b)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign(payload: str, secret: str, ttl_seconds: int, now: float | None = None) -> str:
    """Return ``payload.expiry.signature``; the payload must not contain '.'."""
    if "." in payload:
        raise ValueError("payload must not contain '.'")
    expires = int((now if now is not None else time.time()) + ttl_seconds)
    body = f"{payload}.{expires}"
    mac = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(mac)}"


def verify_signed(token: str, secret: str, now: float | None = None) -> str | None:
    """Return the payload if the signature is valid and unexpired, else None."""
    try:
        payload, expires_text, mac_text = token.rsplit(".", 2)
        expires = int(expires_text)
        mac = _unb64(mac_text)
    except (ValueError, TypeError):
        return None
    expected = hmac.new(secret.encode(), f"{payload}.{expires}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        return None
    if (now if now is not None else time.time()) > expires:
        return None
    return payload
