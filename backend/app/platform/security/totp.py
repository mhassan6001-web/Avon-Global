"""Time-based one-time passwords (RFC 6238, SHA-1, 6 digits, 30 s).

Implemented directly on the standard library so the algorithm is small,
auditable and tested against the RFC 6238 reference vectors.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote, urlencode

PERIOD = 30
DIGITS = 6
ISSUER = "AVEN GLOBAL"


def new_secret() -> str:
    """A 160-bit secret, base32 without padding (authenticator-app format)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _key(secret_b32: str) -> bytes:
    return base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8), casefold=True)


def hotp(key: bytes, counter: int, digits: int = DIGITS) -> str:
    mac = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    code = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10**digits)).zfill(digits)


def totp_at(secret_b32: str, at: float, digits: int = DIGITS) -> str:
    return hotp(_key(secret_b32), int(at // PERIOD), digits)


def verify(secret_b32: str, code: str, at: float | None = None, window: int = 1) -> int | None:
    """Return the matched time-step counter, or None.

    Accepts the current step and ``window`` steps either side for clock drift.
    Callers store the returned counter and reject reuse of the same or an older
    step (replay protection).
    """
    code = code.strip().replace(" ", "")
    if len(code) != DIGITS or not code.isdigit():
        return None
    now = time.time() if at is None else at
    key = _key(secret_b32)
    current = int(now // PERIOD)
    for counter in range(current - window, current + window + 1):
        if hmac.compare_digest(hotp(key, counter), code):
            return counter
    return None


def provisioning_uri(secret_b32: str, account: str) -> str:
    label = quote(f"{ISSUER}:{account}")
    query = urlencode({"secret": secret_b32, "issuer": ISSUER, "digits": DIGITS, "period": PERIOD})
    return f"otpauth://totp/{label}?{query}"
