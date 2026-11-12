"""JARVIS voice API (``/api/v1/jarvis/voice``).

* ``transcribe`` turns one push-to-talk or post-wake-word clip into text. The
  clip is read into memory, transcribed and discarded; the client then sends
  the text through the ordinary JARVIS conversation, so voice and typing pass
  the same gateway (acceptance SV-02).
* ``speak`` returns synthesised audio for a reply. Nothing is stored.
* Wake-word consent is recorded (user, device, time) and audited (WW-02).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import AppError, ServiceUnavailableError
from app.platform.audit import service as audit
from app.platform.authz.deps import DbSession, Principal, client_ip, require

from .models import AIVoiceConsent, AIVoiceSettings
from .voice import get_stt, get_tts

router = APIRouter(prefix="/jarvis/voice", tags=["jarvis"])
Use = Depends(require("jarvis.use"))
AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/mpeg"}


class VoiceRuleError(AppError):
    status_code = 422
    code = "voice_rule"


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class VoiceSettingsIn(_In):
    voice_id: str | None = Field(default=None, max_length=80)
    speed: Decimal = Field(default=Decimal("1.00"), ge=Decimal("0.80"), le=Decimal("1.25"))
    speak_replies: bool = False


class ConsentIn(_In):
    granted: bool
    device: str = Field(min_length=2, max_length=120)


class SpeakIn(_In):
    text: str = Field(min_length=1, max_length=2000)
    style: Literal["briefing", "conversation", "alert", "urgent"] = "conversation"


class VoiceOption(BaseModel):
    id: str
    name: str
    description: str


class VoiceStatus(BaseModel):
    stt_configured: bool
    tts_configured: bool
    voices: list[VoiceOption]
    voice_id: str | None
    speed: Decimal
    speak_replies: bool
    wake_word_licensed: bool
    wake_word_enabled: bool
    max_clip_kb: int


class WakeWordConfig(BaseModel):
    enabled: bool
    access_key: str | None
    model_url: str | None


def _settings(db: DbSession, p: Principal) -> AIVoiceSettings:
    row = db.get(AIVoiceSettings, p.user.id)
    if row is None:
        row = AIVoiceSettings(user_id=p.user.id, speed=Decimal("1.00"))
        db.add(row)
        db.flush()
    return row


def _licensed() -> bool:
    s = get_settings()
    return bool(s.picovoice_access_key.get_secret_value() and s.wake_word_model_url)


def _status(db: DbSession, p: Principal) -> VoiceStatus:
    row = _settings(db, p)
    tts = get_tts()
    return VoiceStatus(
        stt_configured=get_stt() is not None,
        tts_configured=tts is not None,
        voices=[VoiceOption(**v.__dict__) for v in (tts.voices() if tts else [])],
        voice_id=row.voice_id,
        speed=row.speed,
        speak_replies=row.speak_replies,
        wake_word_licensed=_licensed(),
        wake_word_enabled=row.wake_word_enabled,
        max_clip_kb=get_settings().voice_max_clip_kb,
    )


@router.get("/status", response_model=VoiceStatus)
def status(db: DbSession, principal: Principal = Use) -> VoiceStatus:
    out = _status(db, principal)
    db.commit()
    return out


@router.put("/settings", response_model=VoiceStatus)
def save_settings(body: VoiceSettingsIn, db: DbSession, principal: Principal = Use) -> VoiceStatus:
    tts = get_tts()
    if body.voice_id and (tts is None or body.voice_id not in {v.id for v in tts.voices()}):
        raise VoiceRuleError("That voice is not available.")
    row = _settings(db, principal)
    row.voice_id, row.speed, row.speak_replies = body.voice_id, body.speed, body.speak_replies
    row.updated_at = datetime.now(UTC)
    out = _status(db, principal)
    db.commit()
    return out


@router.post("/transcribe", response_model=dict[str, str])
async def transcribe(
    db: DbSession, principal: Principal = Use, audio: UploadFile = File(...)
) -> dict[str, str]:
    stt = get_stt()
    if stt is None:
        raise ServiceUnavailableError("Speech recognition is not configured yet. Type instead.")
    media_type = (audio.content_type or "").split(";")[0].strip().lower()
    if media_type not in AUDIO_TYPES:
        raise VoiceRuleError("Unsupported audio format.")
    limit = get_settings().voice_max_clip_kb * 1024
    clip = await audio.read(limit + 1)
    if len(clip) > limit:
        raise VoiceRuleError("The recording is too long. Keep voice requests under 15 seconds.")
    try:
        text = stt.transcribe(clip, media_type)
    finally:
        del clip  # never stored (SV-03)
    audit.record(
        db,
        action="ai.voice.transcribed",
        actor_id=principal.user.id,
        target_type="ai_voice",
        details={"chars": len(text), "via": "jarvis"},
    )
    db.commit()
    return {"text": text}


@router.post("/speak")
def speak(body: SpeakIn, db: DbSession, principal: Principal = Use) -> Response:
    tts = get_tts()
    if tts is None:
        raise ServiceUnavailableError(
            "JARVIS's voice is not configured yet. Replies stay on screen."
        )
    row = _settings(db, principal)
    db.commit()
    speech = tts.synthesize(body.text, row.voice_id, float(row.speed), body.style)
    return Response(
        content=speech.audio, media_type=speech.media_type, headers={"Cache-Control": "no-store"}
    )


@router.post("/wake-word/consent", response_model=VoiceStatus)
def consent(
    body: ConsentIn, request: Request, db: DbSession, principal: Principal = Use
) -> VoiceStatus:
    if body.granted and not _licensed():
        raise VoiceRuleError("The wake word is not licensed yet. Push-to-talk is available.")
    db.add(AIVoiceConsent(user_id=principal.user.id, device=body.device, granted=body.granted))
    row = _settings(db, principal)
    row.wake_word_enabled = body.granted
    row.updated_at = datetime.now(UTC)
    audit.record(
        db,
        action="ai.voice.wake_word_consent",
        actor_id=principal.user.id,
        outcome="success",
        target_type="ai_voice",
        details={"granted": body.granted, "device": body.device},
        ip=client_ip(request),
    )
    out = _status(db, principal)
    db.commit()
    return out


@router.get("/wake-word/config", response_model=WakeWordConfig)
def wake_word_config(db: DbSession, principal: Principal = Use) -> WakeWordConfig:
    """Released only to a consenting user while the licence is configured."""
    row = db.execute(
        select(AIVoiceSettings).where(AIVoiceSettings.user_id == principal.user.id)
    ).scalar_one_or_none()
    s = get_settings()
    if row is None or not row.wake_word_enabled or not _licensed():
        return WakeWordConfig(enabled=False, access_key=None, model_url=None)
    return WakeWordConfig(
        enabled=True,
        access_key=s.picovoice_access_key.get_secret_value(),
        model_url=s.wake_word_model_url,
    )
