"""Field-level encryption for secrets at rest (TOTP secrets now; bank details later).

Uses Fernet (AES-128-CBC + HMAC-SHA256) via ``MultiFernet``: the first key
encrypts, every configured key can decrypt, so keys can be rotated.
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.config import get_settings


class DecryptionError(RuntimeError):
    pass


@lru_cache(maxsize=4)
def _cipher(keys: tuple[str, ...]) -> MultiFernet:
    return MultiFernet([Fernet(k.encode()) for k in keys])


def encrypt(plaintext: str, keys: tuple[str, ...] | None = None) -> bytes:
    keys = keys or tuple(get_settings().field_encryption_keys)
    return _cipher(keys).encrypt(plaintext.encode("utf-8"))


def decrypt(token: bytes, keys: tuple[str, ...] | None = None) -> str:
    keys = keys or tuple(get_settings().field_encryption_keys)
    try:
        return _cipher(keys).decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        raise DecryptionError("ciphertext could not be decrypted with the configured keys") from exc
