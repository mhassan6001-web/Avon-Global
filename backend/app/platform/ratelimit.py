"""Fixed-window rate limiting and account lockout in Redis.

Authentication endpoints **fail closed**: if Redis is unreachable they refuse
with 503 rather than allow unlimited guessing.
"""

from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass
from functools import lru_cache

import redis

from app.core.config import get_settings
from app.core.errors import AppError, ServiceUnavailableError


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"
    message = "Too many attempts. Please wait and try again."


@dataclass(frozen=True)
class Limit:
    name: str
    max_hits: int
    window_seconds: int


LOGIN_PER_IP = Limit("login_ip", 20, 15 * 60)
LOGIN_PER_ACCOUNT = Limit("login_account", 5, 15 * 60)
MFA_PER_USER = Limit("mfa_user", 5, 5 * 60)
TOKEN_PER_IP = Limit("token_ip", 10, 60 * 60)
LOCKOUT_SECONDS = 15 * 60


@lru_cache(maxsize=1)
def client() -> redis.Redis:
    settings = get_settings()
    return redis.Redis.from_url(
        settings.redis_url, socket_timeout=2, socket_connect_timeout=2, decode_responses=True
    )


def _key(limit: Limit, subject: str, now: float) -> str:
    window = int(now // limit.window_seconds)
    return f"rl:{limit.name}:{subject}:{window}"


def hit(limit: Limit, subject: str) -> int:
    """Count one attempt. Raises RateLimitedError when the limit is exceeded."""
    now = time.time()
    key = _key(limit, subject, now)
    try:
        pipe = client().pipeline()
        pipe.incr(key)
        pipe.expire(key, limit.window_seconds)
        count = int(pipe.execute()[0])
    except redis.RedisError as exc:
        raise ServiceUnavailableError("Sign-in is temporarily unavailable.") from exc
    if count > limit.max_hits:
        raise RateLimitedError()
    return count


def lock_account(user_id: str) -> None:
    try:
        client().set(f"lock:{user_id}", "1", ex=LOCKOUT_SECONDS)
    except redis.RedisError as exc:
        raise ServiceUnavailableError("Sign-in is temporarily unavailable.") from exc


def is_locked(user_id: str) -> bool:
    try:
        return bool(client().exists(f"lock:{user_id}"))
    except redis.RedisError as exc:
        raise ServiceUnavailableError("Sign-in is temporarily unavailable.") from exc


def clear_account(user_id: str, subject_email: str) -> None:
    """Reset the failure counter after a successful login."""
    now = time.time()
    with contextlib.suppress(redis.RedisError):  # non-critical
        client().delete(_key(LOGIN_PER_ACCOUNT, subject_email, now))
