"""Stage 12: voice — transcription, speech, settings and wake-word consent."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.ai import voice_router
from app.platform.audit.models import AuditEvent

from .helpers import make_user, sign_in

API = "/api/v1/jarvis/voice"


def test_voice_requires_jarvis_access(app: FastAPI, db: Session) -> None:
    staff = sign_in(app, make_user(db, "logistics"))
    assert staff.get(f"{API}/status").status_code == 403
    assert staff.post(f"{API}/speak", json={"text": "hello"}).status_code == 403


def test_defaults_wake_word_off_and_settings_persist(app: FastAPI, db: Session) -> None:
    director = sign_in(app, make_user(db, "director"))
    s = director.get(f"{API}/status").json()
    assert s["wake_word_enabled"] is False  # WW-01
    assert s["speak_replies"] is False and s["speed"] == "1.00"
    assert [v["id"] for v in s["voices"]] == ["test-voice"]
    assert director.get(f"{API}/wake-word/config").json() == {
        "enabled": False,
        "access_key": None,
        "model_url": None,
    }
    saved = director.put(
        f"{API}/settings", json={"voice_id": "test-voice", "speed": "1.10", "speak_replies": True}
    )
    assert saved.status_code == 200, saved.text
    assert director.get(f"{API}/status").json()["speed"] == "1.10"
    assert director.put(f"{API}/settings", json={"speed": "1.50"}).status_code == 422
    assert director.put(f"{API}/settings", json={"voice_id": "an-actor"}).status_code == 422


def test_transcribe_is_not_stored_and_goes_through_the_normal_chat(
    app: FastAPI, db: Session
) -> None:
    director = sign_in(app, make_user(db, "director"))
    files = {"audio": ("clip.webm", b"TEXT:Any approvals waiting?", "audio/webm")}
    r = director.post(f"{API}/transcribe", files=files)
    assert r.status_code == 200, r.text
    assert r.json() == {"text": "Any approvals waiting?"}
    db.expire_all()
    event = db.execute(
        select(AuditEvent).where(AuditEvent.action == "ai.voice.transcribed")
    ).scalar_one()
    assert "Any approvals" not in str(event.details)  # no transcript in the audit log
    # No table holds audio.
    cols = db.execute(
        text(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name LIKE 'ai_%' AND data_type = 'bytea'"
        )
    ).scalar()
    assert cols == 0

    bad = {"audio": ("x.txt", b"hello", "text/plain")}
    assert director.post(f"{API}/transcribe", files=bad).status_code == 422
    big = {"audio": ("big.webm", b"0" * (2048 * 1024 + 1), "audio/webm")}
    assert director.post(f"{API}/transcribe", files=big).status_code == 422


def test_speak_returns_audio_without_caching(app: FastAPI, db: Session) -> None:
    director = sign_in(app, make_user(db, "director"))
    r = director.post(
        f"{API}/speak", json={"text": "Good morning. Two approvals wait.", "style": "briefing"}
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.headers["cache-control"] == "no-store"
    assert r.content[:4] == b"RIFF"


def test_wake_word_consent_is_recorded_and_unlocks_config(
    app: FastAPI, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    director = sign_in(app, make_user(db, "director"))
    body = {"granted": True, "device": "Chrome on Windows (office PC)"}
    r = director.post(f"{API}/wake-word/consent", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["wake_word_enabled"] is True
    cfg = director.get(f"{API}/wake-word/config").json()
    assert cfg["enabled"] is True and cfg["access_key"] == "test-access-key-not-real"
    db.expire_all()
    audit = db.execute(
        select(AuditEvent).where(AuditEvent.action == "ai.voice.wake_word_consent")
    ).scalar_one()
    assert audit.details["device"] == body["device"]  # WW-02

    off = director.post(
        f"{API}/wake-word/consent", json={"granted": False, "device": body["device"]}
    )
    assert off.json()["wake_word_enabled"] is False
    assert director.get(f"{API}/wake-word/config").json()["access_key"] is None
    assert db.execute(text("SELECT count(*) FROM ai_voice_consents")).scalar() == 2
    with pytest.raises(DBAPIError):
        db.execute(text("DELETE FROM ai_voice_consents"))
    db.rollback()

    monkeypatch.setattr(voice_router, "_licensed", lambda: False)
    assert director.post(f"{API}/wake-word/consent", json=body).status_code == 422


def test_unconfigured_voice_falls_back_to_text(
    app: FastAPI, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(voice_router, "get_stt", lambda: None)
    monkeypatch.setattr(voice_router, "get_tts", lambda: None)
    director = sign_in(app, make_user(db, "director"))
    files = {"audio": ("clip.webm", b"TEXT:hi", "audio/webm")}
    assert director.post(f"{API}/transcribe", files=files).status_code == 503
    assert director.post(f"{API}/speak", json={"text": "hi"}).status_code == 503  # VO-04
    s = director.get(f"{API}/status").json()
    assert s["stt_configured"] is False and s["voices"] == []
