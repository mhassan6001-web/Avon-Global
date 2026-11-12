"""FastAPI dependencies for authentication, permissions, CSRF and step-up.

Every route under ``/api/v1`` must declare one of these guards (or be listed
as public); ``tests/integration/test_route_coverage.py`` enforces it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import PermissionDeniedError
from app.db.session import get_db
from app.platform.identity import service as identity
from app.platform.identity.models import AuthSession, Role, User
from app.platform.security import tokens

SESSION_COOKIE = "aven_session"
CSRF_COOKIE = "aven_csrf"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

DbSession = Annotated[Session, Depends(get_db)]


class CsrfError(PermissionDeniedError):
    code = "csrf_failed"
    message = "Security token missing or invalid. Refresh the page and try again."


class MfaRequiredError(PermissionDeniedError):
    code = "mfa_required"
    message = "Complete two-factor verification first."


class MfaEnrolmentRequiredError(PermissionDeniedError):
    code = "mfa_enrolment_required"
    message = "Your role requires two-factor authentication. Set it up to continue."


class StepUpRequiredError(PermissionDeniedError):
    code = "step_up_required"
    message = "Confirm your identity again to continue."


@dataclass
class Principal:
    session: AuthSession
    user: User
    role: Role
    permissions: frozenset[str]

    def has(self, permission: str) -> bool:
        return permission in self.permissions


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _load(request: Request, db: Session) -> Principal:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        raise identity.UnauthenticatedError()
    found = identity.find_session(db, raw)
    if found is None:
        raise identity.UnauthenticatedError("Your session has ended. Please sign in again.")
    session, user = found
    if request.method not in SAFE_METHODS:
        header = request.headers.get(CSRF_HEADER, "")
        if not header or not tokens.tokens_equal(tokens.hash_token(header), session.csrf_hash):
            raise CsrfError()
    return Principal(
        session=session,
        user=user,
        role=identity.role_of(db, user),
        permissions=identity.permissions_of(db, user),
    )


def _mark(fn: Callable[..., Any], kind: str, value: str = "") -> Callable[..., Any]:
    fn.__aven_guard__ = (kind, value)  # type: ignore[attr-defined]
    return fn


def any_session_state(request: Request, db: DbSession) -> Principal:
    """Signed-in with a password, whatever the MFA state (MFA and logout endpoints)."""
    return _load(request, db)


_mark(any_session_state, "partial")


def authenticated(request: Request, db: DbSession) -> Principal:
    """A fully authenticated session (MFA completed or not required)."""
    principal = _load(request, db)
    if principal.session.state == "mfa_pending":
        raise MfaRequiredError()
    if principal.session.state == "mfa_enrolment_required":
        raise MfaEnrolmentRequiredError()
    return principal


_mark(authenticated, "authenticated")

CurrentPrincipal = Annotated[Principal, Depends(authenticated)]
PartialPrincipal = Annotated[Principal, Depends(any_session_state)]


def require(permission: str) -> Callable[..., Principal]:
    """Dependency factory: a fully authenticated user holding ``permission``."""
    from app.platform.authz.catalogue import PERMISSION_CODES

    if permission not in PERMISSION_CODES:
        raise ValueError(f"unknown permission {permission!r}")

    def dependency(principal: CurrentPrincipal) -> Principal:
        if not principal.has(permission):
            raise PermissionDeniedError()
        return principal

    dependency.__name__ = f"require_{permission.replace('.', '_')}"
    return _mark(dependency, "permission", permission)


def require_step_up(principal: CurrentPrincipal) -> Principal:
    if not identity.has_recent_step_up(principal.session):
        raise StepUpRequiredError()
    return principal


_mark(require_step_up, "step_up")


def public(_: Request) -> None:
    """Explicit marker for routes that need no session (login, link redemption, health)."""


_mark(public, "public")


def iter_guards(dependant: Any) -> Iterator[tuple[str, str]]:
    """Yield guard markers found anywhere in a route's dependency tree."""
    for dep in dependant.dependencies:
        marker = getattr(dep.call, "__aven_guard__", None)
        if marker:
            yield marker
        yield from iter_guards(dep)
