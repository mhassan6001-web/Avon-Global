"""Helpers for Stage 2 integration tests: users, sign-in and TOTP codes."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.platform.identity import service as identity
from app.platform.identity.models import User, UserMfa
from app.platform.security import crypto, totp

PASSWORD = "Correct-Horse-Battery-77"


@dataclass
class TestUser:
    user: User
    email: str
    password: str
    secret: str | None = None


def make_user(
    db: Session, role: str, *, mfa: bool | None = None, status: str = "active"
) -> TestUser:
    email = f"{role}-{uuid.uuid4().hex[:8]}@test.aven.invalid"
    user = identity.create_user(
        db, email=email, display_name=f"TEST {role}", role_code=role, created_by=None, status=status
    )
    identity.set_password(db, user, PASSWORD)
    secret = None
    wants_mfa = mfa if mfa is not None else role in {"director", "finance", "hr_admin"}
    if wants_mfa:
        secret = totp.new_secret()
        db.add(
            UserMfa(
                user_id=user.id, secret_encrypted=crypto.encrypt(secret), enabled_at=identity.now()
            )
        )
    db.commit()
    return TestUser(user=user, email=email, password=PASSWORD, secret=secret)


def code(secret: str, steps_ahead: int = 0) -> str:
    """A valid TOTP code. Use increasing ``steps_ahead`` to avoid replay rejection."""
    return totp.totp_at(secret, time.time() + 30 * steps_ahead)


def client_for(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def sign_in(
    app: FastAPI, tu: TestUser, *, complete_mfa: bool = True, step_up: bool = False
) -> TestClient:
    c = client_for(app)
    r = c.post("/api/v1/auth/login", json={"email": tu.email, "password": tu.password})
    assert r.status_code == 200, r.text
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    if complete_mfa and r.json()["state"] == "mfa_pending":
        assert tu.secret
        v = c.post("/api/v1/auth/2fa/verify", json={"code": code(tu.secret)})
        assert v.status_code == 200, v.text
    if step_up:
        body = {"code": code(tu.secret, 1)} if tu.secret else {"password": tu.password}
        s = c.post("/api/v1/auth/step-up", json=body)
        assert s.status_code == 200, s.text
    return c
