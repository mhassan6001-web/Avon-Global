"""Password hashing (Argon2id) and password policy."""

from __future__ import annotations

from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings
from app.platform.security.common_passwords import COMMON_PASSWORDS

MIN_LENGTH = 12
MAX_LENGTH = 128


class PasswordPolicyError(ValueError):
    pass


@lru_cache(maxsize=2)
def _hasher(time_cost: int, memory_kib: int) -> PasswordHasher:
    # argon2-cffi defaults to the Argon2id variant.
    return PasswordHasher(time_cost=time_cost, memory_cost=memory_kib, parallelism=4)


def hasher() -> PasswordHasher:
    settings = get_settings()
    return _hasher(settings.argon2_time_cost, settings.argon2_memory_kib)


def hash_password(password: str) -> str:
    return hasher().hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return hasher().verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    return hasher().check_needs_rehash(stored_hash)


# A real hash of a random value, used to equalise timing for unknown accounts.
_DUMMY_HASH: str | None = None


def dummy_verify(password: str) -> None:
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("unused-dummy-password-for-timing")
    verify_password(_DUMMY_HASH, password)


def check_policy(password: str, email: str | None = None, display_name: str | None = None) -> None:
    """Raise PasswordPolicyError with a user-presentable message."""
    if len(password) < MIN_LENGTH:
        raise PasswordPolicyError(f"Use at least {MIN_LENGTH} characters.")
    if len(password) > MAX_LENGTH:
        raise PasswordPolicyError(f"Use at most {MAX_LENGTH} characters.")
    lowered = password.lower()
    if lowered in COMMON_PASSWORDS or lowered.rstrip("0123456789!") in COMMON_PASSWORDS:
        raise PasswordPolicyError("This password is too common. Choose a less predictable one.")
    if len(set(password)) < 5:
        raise PasswordPolicyError("Use a greater variety of characters.")
    for personal in (email.split("@")[0] if email else None, display_name):
        if personal and len(personal) >= 4 and personal.lower() in lowered:
            raise PasswordPolicyError("Do not include your name or email in the password.")
