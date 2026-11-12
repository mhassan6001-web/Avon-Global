"""Stage 3: per-user interface preferences (display and sound)."""

from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy.orm import Session

from .helpers import client_for, make_user, sign_in


def test_defaults_follow_immersive_profile(app: FastAPI, db: Session) -> None:
    c = sign_in(app, make_user(db, "procurement"))
    body = c.get("/api/v1/auth/preferences").json()
    assert body["stored"] is False
    assert body["sound"]["preset"] == "immersive"
    assert body["display"] == {"motion": "system", "contrast": "standard"}


def test_save_and_reload_is_per_user(app: FastAPI, db: Session) -> None:
    a = sign_in(app, make_user(db, "procurement"))
    b = sign_in(app, make_user(db, "logistics"))
    r = a.put(
        "/api/v1/auth/preferences",
        json={"sound": {"preset": "quiet", "muted": True, "master": 0.4}},
    )
    assert r.status_code == 200, r.text
    assert r.json()["sound"]["muted"] is True
    assert a.get("/api/v1/auth/preferences").json()["sound"]["preset"] == "quiet"
    # Another user's preferences are untouched.
    assert b.get("/api/v1/auth/preferences").json()["stored"] is False
    # Updating display keeps the saved sound settings.
    a.put("/api/v1/auth/preferences", json={"display": {"motion": "off", "contrast": "high"}})
    saved = a.get("/api/v1/auth/preferences").json()
    assert saved["display"]["motion"] == "off" and saved["sound"]["muted"] is True


def test_rejects_invalid_values_and_unknown_fields(app: FastAPI, db: Session) -> None:
    c = sign_in(app, make_user(db, "procurement"))
    for bad in (
        {"sound": {"master": 3}},
        {"sound": {"preset": "loud"}},
        {"display": {"motion": "wild"}},
        {"sound": {"autoplay": True}},
        {"other": 1},
    ):
        assert c.put("/api/v1/auth/preferences", json=bad).status_code == 422, bad


def test_requires_sign_in_and_csrf(app: FastAPI, db: Session) -> None:
    anon = client_for(app)
    assert anon.get("/api/v1/auth/preferences").status_code == 401
    c = sign_in(app, make_user(db, "procurement"))
    del c.headers["X-CSRF-Token"]
    assert c.put("/api/v1/auth/preferences", json={}).status_code == 403
