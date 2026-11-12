"""Stage 2 acceptance tests: sign-in, sessions, CSRF, 2FA, step-up, links, lockout."""

from __future__ import annotations

import logging
from datetime import timedelta

import pytest
from fastapi import FastAPI
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.platform.audit.models import SecurityAlert
from app.platform.identity import service as identity
from app.platform.identity.models import AuthSession, LoginEvent, OneTimeToken, User

from .helpers import PASSWORD, client_for, code, make_user, sign_in

API = "/api/v1"


def test_login_success_sets_secure_session(app: FastAPI, db: Session) -> None:
    tu = make_user(db, "procurement")
    c = client_for(app)
    r = c.post(f"{API}/auth/login", json={"email": tu.email.upper(), "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "active"
    cookie = r.headers["set-cookie"]
    assert "aven_session=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    me = c.get(f"{API}/auth/me").json()
    assert me["user"]["role"] == "procurement"
    assert "procurement.records.view" in me["permissions"]
    assert "finance.records.view" not in me["permissions"]
    # Password stored only as an Argon2id hash.
    db.refresh(tu.user)
    assert tu.user.password_hash and tu.user.password_hash.startswith("$argon2id$")
    assert PASSWORD not in tu.user.password_hash


def test_wrong_password_and_unknown_email_are_indistinguishable(app: FastAPI, db: Session) -> None:
    tu = make_user(db, "logistics")
    c = client_for(app)
    wrong = c.post(f"{API}/auth/login", json={"email": tu.email, "password": "nope-nope-nope"})
    unknown = c.post(
        f"{API}/auth/login", json={"email": "nobody@test.aven.invalid", "password": "x"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["code"] == unknown.json()["error"]["code"] == "invalid_credentials"
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]


def test_lockout_after_repeated_failures(app: FastAPI, db: Session) -> None:
    tu = make_user(db, "business_development")
    c = client_for(app)
    for _ in range(5):
        assert (
            c.post(f"{API}/auth/login", json={"email": tu.email, "password": "bad"}).status_code
            == 401
        )
    assert (
        c.post(f"{API}/auth/login", json={"email": tu.email, "password": "bad"}).status_code == 429
    )
    # Even the right password is refused while locked.
    locked = c.post(f"{API}/auth/login", json={"email": tu.email, "password": PASSWORD})
    assert locked.status_code == 429
    outcomes = (
        db.execute(select(LoginEvent.outcome).where(LoginEvent.user_id == tu.user.id))
        .scalars()
        .all()
    )
    assert outcomes.count("bad_credentials") == 6 and "locked" in outcomes
    alert = db.execute(
        select(SecurityAlert).where(SecurityAlert.subject_user_id == tu.user.id)
    ).scalar_one()
    assert alert.kind == "account_locked"


def test_per_ip_rate_limit(app: FastAPI) -> None:
    c = client_for(app)
    statuses = [
        c.post(
            f"{API}/auth/login", json={"email": f"x{i}@test.aven.invalid", "password": "x"}
        ).status_code
        for i in range(21)
    ]
    assert statuses[:20] == [401] * 20 and statuses[20] == 429


def test_csrf_required_for_state_changes(app: FastAPI, db: Session) -> None:
    tu = make_user(db, "procurement")
    c = sign_in(app, tu)
    token = c.headers.pop("X-CSRF-Token")
    body = {"current_password": PASSWORD, "new_password": "Another-Strong-Pass-99"}
    r = c.post(f"{API}/auth/password/change", json=body)
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf_failed"
    c.headers["X-CSRF-Token"] = "wrong-" + token
    assert c.post(f"{API}/auth/password/change", json=body).status_code == 403
    c.headers["X-CSRF-Token"] = token
    assert c.post(f"{API}/auth/password/change", json=body).status_code == 200


def test_logout_invalidates_server_side(app: FastAPI, db: Session) -> None:
    tu = make_user(db, "logistics")
    c = sign_in(app, tu)
    raw = c.cookies.get("aven_session")
    assert c.post(f"{API}/auth/logout").status_code == 200
    replay = client_for(app)
    replay.cookies.set("aven_session", raw)
    assert replay.get(f"{API}/auth/me").status_code == 401


def test_idle_and_absolute_expiry(app: FastAPI, db: Session) -> None:
    tu = make_user(db, "logistics")
    c = sign_in(app, tu)
    session = db.execute(select(AuthSession).where(AuthSession.user_id == tu.user.id)).scalar_one()
    session.last_seen_at = identity.now() - timedelta(minutes=31)
    db.commit()
    assert c.get(f"{API}/auth/me").status_code == 401

    c2 = sign_in(app, tu)
    s2 = db.execute(
        select(AuthSession).where(
            AuthSession.user_id == tu.user.id, AuthSession.revoked_at.is_(None)
        )
    ).scalar_one()
    s2.expires_at = identity.now() - timedelta(seconds=1)
    db.commit()
    assert c2.get(f"{API}/auth/me").status_code == 401


def test_mandatory_mfa_enrolment(app: FastAPI, db: Session) -> None:
    tu = make_user(db, "finance", mfa=False)
    c = client_for(app)
    r = c.post(f"{API}/auth/login", json={"email": tu.email, "password": PASSWORD})
    assert r.json()["state"] == "mfa_enrolment_required"
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    blocked = c.get(f"{API}/organisation/profile")
    assert (
        blocked.status_code == 403 and blocked.json()["error"]["code"] == "mfa_enrolment_required"
    )
    setup = c.post(f"{API}/auth/2fa/setup").json()
    assert setup["otpauth_uri"].startswith("otpauth://totp/") and "<svg" in setup["qr_svg"]
    assert c.post(f"{API}/auth/2fa/enable", json={"code": "000000"}).status_code == 400
    enabled = c.post(f"{API}/auth/2fa/enable", json={"code": code(setup["secret"])})
    assert enabled.status_code == 200 and len(enabled.json()["recovery_codes"]) == 10
    assert c.get(f"{API}/organisation/profile").status_code == 200
    # Mandatory roles cannot switch it off.
    assert c.post(f"{API}/auth/2fa/disable").status_code == 403


def test_mfa_login_replay_and_recovery_code(app: FastAPI, db: Session) -> None:
    tu = make_user(db, "hr_admin")
    assert tu.secret
    c = client_for(app)
    r = c.post(f"{API}/auth/login", json={"email": tu.email, "password": PASSWORD})
    assert r.json()["state"] == "mfa_pending"
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    assert c.get(f"{API}/organisation/profile").json()["error"]["code"] == "mfa_required"
    assert c.post(f"{API}/auth/2fa/verify", json={"code": "123456"}).status_code == 400
    current = code(tu.secret)
    assert c.post(f"{API}/auth/2fa/verify", json={"code": current}).status_code == 200
    # The same code cannot be replayed for step-up.
    assert c.post(f"{API}/auth/step-up", json={"code": current}).status_code == 400
    assert c.post(f"{API}/auth/step-up", json={"code": code(tu.secret, 1)}).status_code == 200


def test_recovery_codes_single_use(app: FastAPI, db: Session) -> None:
    tu = make_user(db, "business_development", mfa=False)
    c = sign_in(app, tu)
    setup = c.post(f"{API}/auth/2fa/setup").json()
    codes = c.post(f"{API}/auth/2fa/enable", json={"code": code(setup["secret"])}).json()[
        "recovery_codes"
    ]
    for expected in (200, 400):
        c2 = client_for(app)
        r = c2.post(f"{API}/auth/login", json={"email": tu.email, "password": PASSWORD})
        c2.headers["X-CSRF-Token"] = r.json()["csrf_token"]
        assert (
            c2.post(f"{API}/auth/2fa/verify", json={"recovery_code": codes[0]}).status_code
            == expected
        )


def test_step_up_required_for_admin_changes(app: FastAPI, db: Session) -> None:
    director = make_user(db, "director")
    c = sign_in(app, director)
    payload = {
        "email": "newstaff@test.aven.invalid",
        "display_name": "New Staff",
        "role": "logistics",
    }
    r = c.post(f"{API}/admin/users", json=payload)
    assert r.status_code == 403 and r.json()["error"]["code"] == "step_up_required"
    assert (
        c.post(f"{API}/auth/step-up", json={"code": code(director.secret or "", 1)}).status_code
        == 200
    )
    created = c.post(f"{API}/admin/users", json=payload)
    assert created.status_code == 201, created.text
    assert "/invite?token=" in created.json()["invitation_url"]


def test_invitation_flow_and_hash_only_storage(app: FastAPI, db: Session) -> None:
    director = make_user(db, "director")
    c = sign_in(app, director, step_up=True)
    email = "invitee@test.aven.invalid"
    url = c.post(
        f"{API}/admin/users",
        json={"email": email, "display_name": "Invitee Person", "role": "procurement"},
    ).json()["invitation_url"]
    raw = url.split("token=")[1]
    stored = db.execute(select(OneTimeToken.token_hash)).scalars().all()
    assert all(raw.encode() not in h for h in stored)
    anon = client_for(app)
    weak = anon.post(
        f"{API}/auth/invitations/accept", json={"token": raw, "new_password": "password123"}
    )
    assert weak.status_code == 422 and weak.json()["error"]["code"] == "weak_password"
    ok = anon.post(
        f"{API}/auth/invitations/accept",
        json={"token": raw, "new_password": "Invitee-Strong-Pass-1"},
    )
    assert ok.status_code == 200
    again = anon.post(
        f"{API}/auth/invitations/accept",
        json={"token": raw, "new_password": "Invitee-Strong-Pass-2"},
    )
    assert again.status_code == 400 and again.json()["error"]["code"] == "invalid_link"
    login = anon.post(
        f"{API}/auth/login", json={"email": email, "password": "Invitee-Strong-Pass-1"}
    )
    assert login.json()["state"] == "active"


def test_reset_link_revokes_sessions_and_expires(app: FastAPI, db: Session) -> None:
    director = make_user(db, "director")
    staff = make_user(db, "logistics")
    staff_client = sign_in(app, staff)
    c = sign_in(app, director, step_up=True)
    url = c.post(f"{API}/admin/users/{staff.user.id}/reset-link").json()["url"]
    raw = url.split("token=")[1]
    anon = client_for(app)
    assert (
        anon.post(
            f"{API}/auth/password/reset", json={"token": raw, "new_password": "Brand-New-Secret-42"}
        ).status_code
        == 200
    )
    assert staff_client.get(f"{API}/auth/me").status_code == 401  # old session revoked
    url2 = c.post(f"{API}/admin/users/{staff.user.id}/reset-link").json()["url"]
    tok = db.execute(select(OneTimeToken).where(OneTimeToken.used_at.is_(None))).scalars().all()
    for t in tok:
        t.expires_at = identity.now() - timedelta(seconds=1)
    db.commit()
    expired = anon.post(
        f"{API}/auth/password/reset",
        json={"token": url2.split("token=")[1], "new_password": "Brand-New-Secret-43"},
    )
    assert expired.status_code == 400


def test_suspension_revokes_sessions_immediately(app: FastAPI, db: Session) -> None:
    director = make_user(db, "director")
    staff = make_user(db, "procurement")
    staff_client = sign_in(app, staff)
    assert staff_client.get(f"{API}/auth/me").status_code == 200
    c = sign_in(app, director, step_up=True)
    assert c.post(f"{API}/admin/users/{staff.user.id}/suspend").status_code == 200
    assert staff_client.get(f"{API}/auth/me").status_code == 401
    relogin = client_for(app).post(
        f"{API}/auth/login", json={"email": staff.email, "password": PASSWORD}
    )
    assert relogin.status_code == 401
    # The Director cannot suspend themselves.
    assert c.post(f"{API}/admin/users/{director.user.id}/suspend").status_code == 403


def test_password_change_revokes_other_sessions(app: FastAPI, db: Session) -> None:
    tu = make_user(db, "logistics")
    other = sign_in(app, tu)
    current = sign_in(app, tu)
    r = current.post(
        f"{API}/auth/password/change",
        json={"current_password": PASSWORD, "new_password": "Totally-New-Pass-88"},
    )
    assert r.status_code == 200
    assert other.get(f"{API}/auth/me").status_code == 401
    assert current.get(f"{API}/auth/me").status_code == 200


def test_no_plaintext_password_in_logs(
    app: FastAPI, db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    tu = make_user(db, "logistics")
    caplog.set_level(logging.DEBUG)
    client_for(app).post(f"{API}/auth/login", json={"email": tu.email, "password": PASSWORD})
    client_for(app).post(
        f"{API}/auth/login", json={"email": tu.email, "password": "Wrong-Guess-123"}
    )
    assert PASSWORD not in caplog.text and "Wrong-Guess-123" not in caplog.text


def test_dev_users_only_exist_in_development(db: Session) -> None:
    from app.cli import main

    assert main(["seed-dev-users"]) == 2  # APP_ENV=test → refused
    assert not db.execute(select(User).where(User.email.like("%@dev.aven.invalid"))).first()


def test_sessions_and_login_history_are_own_only(app: FastAPI, db: Session) -> None:
    a = make_user(db, "logistics")
    b = make_user(db, "procurement")
    ca, cb = sign_in(app, a), sign_in(app, b)
    sessions = ca.get(f"{API}/auth/sessions").json()
    assert len(sessions) == 1 and sessions[0]["current"] is True
    b_session = cb.get(f"{API}/auth/sessions").json()[0]["id"]
    assert ca.delete(f"{API}/auth/sessions/{b_session}").status_code == 404
    history = ca.get(f"{API}/auth/login-history").json()
    assert history and all(h["email_attempted"] == a.email for h in history)
    assert ca.get(f"{API}/admin/login-history").status_code == 403


def test_audit_log_append_only_and_tamper_evident(app: FastAPI, db: Session) -> None:
    director = make_user(db, "director")
    c = sign_in(app, director)
    assert c.post(f"{API}/admin/audit/verify").json()["ok"] is True
    for stmt in (
        "UPDATE sys_audit_events SET action = 'x'",
        "DELETE FROM sys_audit_events",
        "TRUNCATE sys_audit_events",
    ):
        with pytest.raises(Exception, match="append-only"):
            db.execute(text(stmt))
        db.rollback()
    # Simulate tampering by a privileged actor bypassing the trigger.
    db.execute(text("ALTER TABLE sys_audit_events DISABLE TRIGGER trg_sys_audit_events_no_modify"))
    db.execute(
        text(
            "UPDATE sys_audit_events SET action = 'tampered' "
            "WHERE seq = (SELECT min(seq) FROM sys_audit_events)"
        )
    )
    db.execute(text("ALTER TABLE sys_audit_events ENABLE TRIGGER trg_sys_audit_events_no_modify"))
    db.commit()
    report = c.post(f"{API}/admin/audit/verify").json()
    assert report["ok"] is False and report["first_bad_seq"] is not None
    alerts = db.execute(select(SecurityAlert.kind)).scalars().all()
    assert "audit_chain_broken" in alerts
