"""Authentication and own-account endpoints (``/api/v1/auth``)."""

from __future__ import annotations

import uuid
from datetime import timedelta

import segno
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.platform.authz.deps import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    CurrentPrincipal,
    DbSession,
    PartialPrincipal,
    Principal,
    client_ip,
    public,
)
from app.platform.identity import schemas
from app.platform.identity import service as identity
from app.platform.identity.models import AuthSession, Department, LoginEvent, User

router = APIRouter(prefix="/auth", tags=["auth"])
Public = Depends(public)


def user_out(db: DbSession, user: User) -> schemas.UserOut:
    role = identity.role_of(db, user)
    department = db.get_one(Department, user.department_id)
    return schemas.UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=role.code,
        role_name=role.name,
        department=department.name,
        status=user.status,
        is_dev_account=user.is_dev_account,
        mfa_enabled=identity.mfa_enabled(db, user.id),
    )


def _set_cookies(response: Response, token: str, csrf: str) -> None:
    settings = get_settings()
    max_age = settings.session_absolute_hours * 3600
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    # Readable by the web app so it can echo it in the X-CSRF-Token header.
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        max_age=max_age,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


def _clear_cookies(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


@router.post("/login", response_model=schemas.LoginOut, dependencies=[Public])
def login(
    body: schemas.LoginRequest, request: Request, response: Response, db: DbSession
) -> schemas.LoginOut:
    result = identity.login(
        db, body.email, body.password, client_ip(request), request.headers.get("user-agent")
    )
    _set_cookies(response, result.new_session.token, result.new_session.csrf_token)
    return schemas.LoginOut(
        state=result.state, csrf_token=result.new_session.csrf_token, user=user_out(db, result.user)
    )


@router.post("/logout", response_model=schemas.OkOut)
def logout(principal: PartialPrincipal, response: Response, db: DbSession) -> schemas.OkOut:
    identity.logout(db, principal.session)
    _clear_cookies(response)
    return schemas.OkOut()


@router.get("/me", response_model=schemas.MeOut)
def me(principal: PartialPrincipal, db: DbSession) -> schemas.MeOut:
    step_up_until = (
        principal.session.step_up_at + timedelta(minutes=get_settings().step_up_minutes)
        if principal.session.step_up_at
        else None
    )
    full = principal.session.state == "active"
    return schemas.MeOut(
        user=user_out(db, principal.user),
        session_state=principal.session.state,
        permissions=sorted(principal.permissions) if full else [],
        mfa_required_by_role=principal.role.mfa_required,
        step_up_valid_until=step_up_until,
    )


@router.post("/2fa/verify", response_model=schemas.OkOut)
def verify_mfa(
    body: schemas.MfaVerifyRequest, principal: PartialPrincipal, db: DbSession
) -> schemas.OkOut:
    identity.verify_mfa(db, principal.session, body.code, body.recovery_code)
    return schemas.OkOut()


def _setup_allowed(principal: Principal) -> None:
    if principal.session.state == "mfa_pending":
        from app.platform.authz.deps import MfaRequiredError

        raise MfaRequiredError()


@router.post("/2fa/setup", response_model=schemas.MfaSetupOut)
def mfa_setup(principal: PartialPrincipal, db: DbSession) -> schemas.MfaSetupOut:
    _setup_allowed(principal)
    setup = identity.begin_mfa_setup(db, principal.user)
    qr = segno.make(setup.otpauth_uri, error="m")
    svg = qr.svg_inline(scale=5, dark="#0b0d12", light="#f5efe2")
    return schemas.MfaSetupOut(secret=setup.secret, otpauth_uri=setup.otpauth_uri, qr_svg=svg)


@router.post("/2fa/enable", response_model=schemas.RecoveryCodesOut)
def mfa_enable(
    body: schemas.MfaEnableRequest, principal: PartialPrincipal, db: DbSession
) -> schemas.RecoveryCodesOut:
    _setup_allowed(principal)
    codes = identity.enable_mfa(db, principal.session, principal.user, body.code)
    return schemas.RecoveryCodesOut(recovery_codes=codes)


@router.post("/2fa/disable", response_model=schemas.OkOut)
def mfa_disable(principal: CurrentPrincipal, db: DbSession) -> schemas.OkOut:
    if not identity.has_recent_step_up(principal.session):
        from app.platform.authz.deps import StepUpRequiredError

        raise StepUpRequiredError()
    identity.disable_mfa(db, principal.user)
    return schemas.OkOut()


@router.post("/step-up", response_model=schemas.OkOut)
def step_up(
    body: schemas.StepUpRequest, principal: CurrentPrincipal, db: DbSession
) -> schemas.OkOut:
    identity.step_up(db, principal.session, principal.user, body.code, body.password)
    return schemas.OkOut()


@router.post("/password/change", response_model=schemas.OkOut)
def change_password(
    body: schemas.ChangePasswordRequest, principal: CurrentPrincipal, db: DbSession
) -> schemas.OkOut:
    identity.change_password(
        db, principal.session, principal.user, body.current_password, body.new_password
    )
    return schemas.OkOut()


@router.post("/invitations/accept", response_model=schemas.OkOut, dependencies=[Public])
def accept_invitation(
    body: schemas.RedeemLinkRequest, request: Request, db: DbSession
) -> schemas.OkOut:
    identity.redeem_link(db, body.token, "invitation", body.new_password, client_ip(request))
    return schemas.OkOut()


@router.post("/password/reset", response_model=schemas.OkOut, dependencies=[Public])
def reset_password(
    body: schemas.RedeemLinkRequest, request: Request, db: DbSession
) -> schemas.OkOut:
    identity.redeem_link(db, body.token, "password_reset", body.new_password, client_ip(request))
    return schemas.OkOut()


@router.get("/sessions", response_model=list[schemas.SessionOut])
def my_sessions(principal: CurrentPrincipal, db: DbSession) -> list[schemas.SessionOut]:
    now = identity.now()
    rows = db.execute(
        select(AuthSession)
        .where(
            AuthSession.user_id == principal.user.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .order_by(AuthSession.last_seen_at.desc())
    ).scalars()
    return [
        schemas.SessionOut(
            id=s.id,
            created_at=s.created_at,
            last_seen_at=s.last_seen_at,
            expires_at=s.expires_at,
            ip=str(s.ip) if s.ip else None,
            user_agent=s.user_agent,
            current=s.id == principal.session.id,
        )
        for s in rows
    ]


@router.delete("/sessions/{session_id}", response_model=schemas.OkOut)
def revoke_my_session(
    session_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession
) -> schemas.OkOut:
    session = db.get(AuthSession, session_id)
    if session is None or session.user_id != principal.user.id:
        raise NotFoundError()
    session.revoked_at = identity.now()
    db.commit()
    return schemas.OkOut()


@router.get("/login-history", response_model=list[schemas.LoginEventOut])
def my_login_history(
    principal: CurrentPrincipal, db: DbSession, limit: int = 50
) -> list[schemas.LoginEventOut]:
    rows = db.execute(
        select(LoginEvent)
        .where(LoginEvent.user_id == principal.user.id)
        .order_by(LoginEvent.occurred_at.desc())
        .limit(min(max(limit, 1), 200))
    ).scalars()
    return [
        schemas.LoginEventOut(
            occurred_at=e.occurred_at,
            email_attempted=e.email_attempted,
            outcome=e.outcome,
            ip=str(e.ip) if e.ip else None,
            user_agent=e.user_agent,
        )
        for e in rows
    ]
