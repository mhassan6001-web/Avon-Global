"""Identity service: login, sessions, MFA, step-up, invitations, resets, passwords."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.platform import ratelimit
from app.platform.audit import service as audit
from app.platform.authz.catalogue import ROLE_BY_CODE, effective_permissions
from app.platform.identity.models import (
    AuthSession,
    Department,
    LoginEvent,
    OneTimeToken,
    Permission,
    PermissionOverride,
    Role,
    User,
    UserMfa,
)
from app.platform.security import crypto, passwords, tokens, totp
from app.platform.security.passwords import PasswordPolicyError


class InvalidCredentialsError(AppError):
    status_code = 401
    code = "invalid_credentials"
    message = "Email or password is incorrect."


class UnauthenticatedError(AppError):
    status_code = 401
    code = "unauthenticated"
    message = "Please sign in."


class InvalidCodeError(AppError):
    status_code = 400
    code = "invalid_code"
    message = "That code is not valid. Check your authenticator app and try again."


class InvalidLinkError(AppError):
    status_code = 400
    code = "invalid_link"
    message = "This link is invalid, has expired or has already been used."


class WeakPasswordError(AppError):
    status_code = 422
    code = "weak_password"


def now() -> datetime:
    return datetime.now(UTC)


def normalise_email(email: str) -> str:
    return email.strip().lower()


# --------------------------------------------------------------------------- lookups


def role_of(db: Session, user: User) -> Role:
    return db.get_one(Role, user.role_id)


def overrides_of(db: Session, user_id: uuid.UUID) -> tuple[set[str], set[str]]:
    rows = db.execute(
        select(Permission.code, PermissionOverride.effect)
        .join(Permission, Permission.id == PermissionOverride.permission_id)
        .where(PermissionOverride.user_id == user_id)
    ).all()
    grants = {code for code, effect in rows if effect == "grant"}
    denies = {code for code, effect in rows if effect == "deny"}
    return grants, denies


def permissions_of(db: Session, user: User) -> frozenset[str]:
    role = role_of(db, user)
    grants, denies = overrides_of(db, user.id)
    return effective_permissions(role.code, grants, denies)


def mfa_enabled(db: Session, user_id: uuid.UUID) -> bool:
    mfa = db.get(UserMfa, user_id)
    return bool(mfa and mfa.enabled_at)


# --------------------------------------------------------------------------- sessions


@dataclass
class NewSession:
    session: AuthSession
    token: str
    csrf_token: str


@dataclass
class LoginResult:
    user: User
    new_session: NewSession
    state: str
    extra: dict[str, str] = field(default_factory=dict)


def _create_session(
    db: Session, user: User, state: str, ip: str | None, user_agent: str | None
) -> NewSession:
    settings = get_settings()
    token, csrf = tokens.new_token(), tokens.new_token()
    t = now()
    session = AuthSession(
        user_id=user.id,
        token_hash=tokens.hash_token(token),
        csrf_hash=tokens.hash_token(csrf),
        state=state,
        created_at=t,
        last_seen_at=t,
        expires_at=t + timedelta(hours=settings.session_absolute_hours),
        ip=ip,
        user_agent=(user_agent or "")[:400] or None,
    )
    db.add(session)
    db.flush()
    return NewSession(session=session, token=token, csrf_token=csrf)


def find_session(db: Session, raw_token: str) -> tuple[AuthSession, User] | None:
    """Return a live session and its active user, or None. Updates last-seen."""
    settings = get_settings()
    session = db.execute(
        select(AuthSession).where(AuthSession.token_hash == tokens.hash_token(raw_token))
    ).scalar_one_or_none()
    t = now()
    if session is None or session.revoked_at is not None or session.expires_at <= t:
        return None
    if session.last_seen_at + timedelta(minutes=settings.session_idle_minutes) <= t:
        session.revoked_at = t
        db.commit()
        return None
    user = db.get(User, session.user_id)
    if user is None or user.status != "active":
        session.revoked_at = t
        db.commit()
        return None
    if (t - session.last_seen_at).total_seconds() > 60:
        session.last_seen_at = t
        db.commit()
    return session, user


def revoke_sessions(db: Session, user_id: uuid.UUID, except_id: uuid.UUID | None = None) -> int:
    stmt = (
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now())
    )
    if except_id is not None:
        stmt = stmt.where(AuthSession.id != except_id)
    return db.execute(stmt).rowcount or 0  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- login


def _login_event(
    db: Session,
    email: str,
    outcome: str,
    user: User | None,
    ip: str | None,
    user_agent: str | None,
) -> None:
    db.add(
        LoginEvent(
            user_id=user.id if user else None,
            email_attempted=email[:320],
            outcome=outcome,
            ip=ip,
            user_agent=(user_agent or "")[:400] or None,
            occurred_at=now(),
        )
    )


def login(
    db: Session, email: str, password: str, ip: str | None, user_agent: str | None
) -> LoginResult:
    email = normalise_email(email)
    ratelimit.hit(ratelimit.LOGIN_PER_IP, ip or "unknown")
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    if user is not None and ratelimit.is_locked(str(user.id)):
        _login_event(db, email, "locked", user, ip, user_agent)
        db.commit()
        raise ratelimit.RateLimitedError()

    if user is None or not user.password_hash:
        passwords.dummy_verify(password)
        ok = False
    else:
        ok = passwords.verify_password(user.password_hash, password)

    if not ok:
        _login_event(db, email, "bad_credentials", user, ip, user_agent)
        try:
            ratelimit.hit(ratelimit.LOGIN_PER_ACCOUNT, email)
        except ratelimit.RateLimitedError:
            if user is not None:
                ratelimit.lock_account(str(user.id))
                _login_event(db, email, "locked", user, ip, user_agent)
                audit.raise_alert(
                    db,
                    kind="account_locked",
                    message=f"Account {email} locked after repeated failed sign-in attempts.",
                    subject_user_id=user.id,
                )
                audit.record(
                    db,
                    action="auth.lockout",
                    actor_id=None,
                    actor_kind="system",
                    target_type="user",
                    target_id=user.id,
                    outcome="success",
                    ip=ip,
                )
            db.commit()
            raise
        db.commit()
        raise InvalidCredentialsError()

    assert user is not None and user.password_hash is not None  # nosec B101
    if user.status != "active":
        _login_event(db, email, f"rejected_{user.status}", user, ip, user_agent)
        db.commit()
        raise InvalidCredentialsError()

    if passwords.needs_rehash(user.password_hash):
        user.password_hash = passwords.hash_password(password)

    role = role_of(db, user)
    if mfa_enabled(db, user.id):
        state = "mfa_pending"
    elif role.mfa_required:
        state = "mfa_enrolment_required"
    else:
        state = "active"
    new_session = _create_session(db, user, state, ip, user_agent)
    ratelimit.clear_account(str(user.id), email)
    _login_event(
        db, email, "success" if state == "active" else "password_ok_" + state, user, ip, user_agent
    )
    audit.record(
        db,
        action="auth.login",
        actor_id=user.id,
        target_type="session",
        target_id=new_session.session.id,
        details={"state": state},
        ip=ip,
    )
    db.commit()
    return LoginResult(user=user, new_session=new_session, state=state)


def logout(db: Session, session: AuthSession) -> None:
    session.revoked_at = now()
    audit.record(
        db,
        action="auth.logout",
        actor_id=session.user_id,
        target_type="session",
        target_id=session.id,
    )
    db.commit()


# --------------------------------------------------------------------------- MFA


def _check_totp(db: Session, user_id: uuid.UUID, code: str) -> bool:
    mfa = db.get(UserMfa, user_id)
    if mfa is None:
        return False
    secret = crypto.decrypt(mfa.secret_encrypted)
    step = totp.verify(secret, code)
    if step is None or (mfa.last_used_step is not None and step <= mfa.last_used_step):
        return False  # invalid or replayed
    mfa.last_used_step = step
    return True


def _check_recovery_code(db: Session, user_id: uuid.UUID, code: str) -> bool:
    mfa = db.get(UserMfa, user_id)
    if mfa is None or not mfa.enabled_at:
        return False
    digest = tokens.hash_token(code.strip().replace("-", "").lower()).hex()
    if digest not in mfa.recovery_code_hashes:
        return False
    mfa.recovery_code_hashes = [h for h in mfa.recovery_code_hashes if h != digest]
    return True


def verify_mfa(
    db: Session, session: AuthSession, code: str | None, recovery_code: str | None
) -> None:
    ratelimit.hit(ratelimit.MFA_PER_USER, str(session.user_id))
    if session.state != "mfa_pending":
        raise ConflictError("Two-factor verification is not pending for this session.")
    ok = (bool(code) and _check_totp(db, session.user_id, code or "")) or (
        bool(recovery_code) and _check_recovery_code(db, session.user_id, recovery_code or "")
    )
    if not ok:
        audit.record(db, action="auth.mfa_verify", actor_id=session.user_id, outcome="failure")
        db.commit()
        raise InvalidCodeError()
    session.state = "active"
    session.step_up_at = now()
    audit.record(
        db,
        action="auth.mfa_verify",
        actor_id=session.user_id,
        details={"method": "recovery_code" if recovery_code else "totp"},
    )
    db.commit()


@dataclass
class MfaSetup:
    secret: str
    otpauth_uri: str


def begin_mfa_setup(db: Session, user: User) -> MfaSetup:
    existing = db.get(UserMfa, user.id)
    if existing and existing.enabled_at:
        raise ConflictError("Two-factor authentication is already enabled.")
    secret = totp.new_secret()
    if existing is None:
        db.add(UserMfa(user_id=user.id, secret_encrypted=crypto.encrypt(secret)))
    else:
        existing.secret_encrypted = crypto.encrypt(secret)
        existing.last_used_step = None
    db.commit()
    return MfaSetup(secret=secret, otpauth_uri=totp.provisioning_uri(secret, user.email))


_RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def _new_recovery_codes() -> tuple[list[str], list[str]]:
    codes = ["".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(10)) for _ in range(10)]
    display = [f"{c[:5]}-{c[5:]}" for c in codes]
    hashes = [tokens.hash_token(c.replace("-", "")).hex() for c in codes]
    return display, hashes


def enable_mfa(db: Session, session: AuthSession, user: User, code: str) -> list[str]:
    mfa = db.get(UserMfa, user.id)
    if mfa is None:
        raise ConflictError("Start two-factor setup first.")
    if mfa.enabled_at:
        raise ConflictError("Two-factor authentication is already enabled.")
    if not _check_totp(db, user.id, code):
        db.commit()
        raise InvalidCodeError()
    display, hashes = _new_recovery_codes()
    mfa.enabled_at = now()
    mfa.recovery_code_hashes = hashes
    if session.state == "mfa_enrolment_required":
        session.state = "active"
    session.step_up_at = now()
    audit.record(
        db, action="auth.mfa_enabled", actor_id=user.id, target_type="user", target_id=user.id
    )
    db.commit()
    return display


def disable_mfa(db: Session, user: User) -> None:
    role = role_of(db, user)
    if role.mfa_required:
        raise PermissionDeniedError("Two-factor authentication is mandatory for your role.")
    mfa = db.get(UserMfa, user.id)
    if mfa is not None:
        db.delete(mfa)
    audit.record(
        db, action="auth.mfa_disabled", actor_id=user.id, target_type="user", target_id=user.id
    )
    db.commit()


def step_up(
    db: Session, session: AuthSession, user: User, code: str | None, password: str | None
) -> None:
    ratelimit.hit(ratelimit.MFA_PER_USER, str(user.id))
    if mfa_enabled(db, user.id):
        ok = bool(code) and _check_totp(db, user.id, code or "")
    else:
        ok = (
            bool(password)
            and bool(user.password_hash)
            and passwords.verify_password(user.password_hash or "", password or "")
        )
    if not ok:
        audit.record(db, action="auth.step_up", actor_id=user.id, outcome="failure")
        db.commit()
        raise InvalidCodeError("Verification failed.")
    session.step_up_at = now()
    audit.record(db, action="auth.step_up", actor_id=user.id)
    db.commit()


def has_recent_step_up(session: AuthSession) -> bool:
    minutes = get_settings().step_up_minutes
    return (
        session.step_up_at is not None and session.step_up_at + timedelta(minutes=minutes) > now()
    )


# --------------------------------------------------------------------------- passwords & links


def set_password(db: Session, user: User, new_password: str) -> None:
    try:
        passwords.check_policy(new_password, user.email, user.display_name)
    except PasswordPolicyError as exc:
        raise WeakPasswordError(str(exc)) from exc
    user.password_hash = passwords.hash_password(new_password)
    user.password_changed_at = now()
    user.version += 1


def change_password(db: Session, session: AuthSession, user: User, current: str, new: str) -> None:
    if not user.password_hash or not passwords.verify_password(user.password_hash, current):
        raise InvalidCredentialsError("Your current password is incorrect.")
    set_password(db, user, new)
    revoke_sessions(db, user.id, except_id=session.id)
    audit.record(
        db, action="auth.password_changed", actor_id=user.id, target_type="user", target_id=user.id
    )
    db.commit()


def issue_link(db: Session, user: User, purpose: str, created_by: uuid.UUID) -> str:
    settings = get_settings()
    if purpose == "invitation":
        ttl = timedelta(hours=settings.invitation_valid_hours)
        path = "/invite"
    else:
        ttl = timedelta(minutes=settings.reset_link_valid_minutes)
        path = "/reset-password"
    # Invalidate previous unused links of the same purpose.
    db.execute(
        update(OneTimeToken)
        .where(
            OneTimeToken.user_id == user.id,
            OneTimeToken.purpose == purpose,
            OneTimeToken.used_at.is_(None),
        )
        .values(used_at=now())
    )
    raw = tokens.new_token()
    db.add(
        OneTimeToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=tokens.hash_token(raw),
            created_by=created_by,
            created_at=now(),
            expires_at=now() + ttl,
        )
    )
    db.flush()
    return f"{settings.public_base_url.rstrip('/')}{path}?token={raw}"


def redeem_link(
    db: Session, raw_token: str, purpose: str, new_password: str, ip: str | None
) -> User:
    ratelimit.hit(ratelimit.TOKEN_PER_IP, ip or "unknown")
    record = db.execute(
        select(OneTimeToken).where(OneTimeToken.token_hash == tokens.hash_token(raw_token))
    ).scalar_one_or_none()
    if (
        record is None
        or record.purpose != purpose
        or record.used_at is not None
        or record.expires_at <= now()
    ):
        raise InvalidLinkError()
    user = db.get_one(User, record.user_id)
    if user.status == "suspended":
        raise InvalidLinkError()
    set_password(db, user, new_password)
    record.used_at = now()
    if purpose == "invitation":
        user.status = "active"
    revoke_sessions(db, user.id)
    audit.record(
        db,
        action=f"auth.{purpose}_redeemed",
        actor_id=user.id,
        target_type="user",
        target_id=user.id,
        ip=ip,
    )
    db.commit()
    return user


# --------------------------------------------------------------------------- user creation


def create_user(
    db: Session,
    *,
    email: str,
    display_name: str,
    role_code: str,
    created_by: uuid.UUID | None,
    is_dev_account: bool = False,
    status: str = "invited",
) -> User:
    email = normalise_email(email)
    if role_code not in ROLE_BY_CODE:
        raise NotFoundError("Unknown role.")
    if db.execute(select(User.id).where(User.email == email)).scalar_one_or_none():
        raise ConflictError("A user with this email already exists.")
    role = db.execute(select(Role).where(Role.code == role_code)).scalar_one()
    department = db.execute(
        select(Department).where(Department.code == ROLE_BY_CODE[role_code].department_code)
    ).scalar_one()
    user = User(
        email=email,
        display_name=display_name.strip(),
        role_id=role.id,
        department_id=department.id,
        status=status,
        is_dev_account=is_dev_account,
    )
    db.add(user)
    db.flush()
    audit.record(
        db,
        action="admin.user_created",
        actor_id=created_by,
        actor_kind="user" if created_by else "system",
        target_type="user",
        target_id=user.id,
        details={"role": role_code, "dev_account": is_dev_account},
    )
    return user
