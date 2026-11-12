"""Provider-independent speech layer (Stage 12).

Audio is processed in memory and never written to disk or the database
(acceptance SV-03). Only the transcript continues, as an ordinary typed
question, through the same JARVIS gateway. A recognised voice never
authorises anything.
"""

from __future__ import annotations

import io
import struct
import wave
from dataclasses import dataclass
from typing import Literal, Protocol

from app.core.config import get_settings

Style = Literal["briefing", "conversation", "alert", "urgent"]


@dataclass(frozen=True)
class Voice:
    id: str
    name: str
    description: str


@dataclass(frozen=True)
class Speech:
    audio: bytes
    media_type: str


class SpeechToTextProvider(Protocol):
    name: str

    def transcribe(self, audio: bytes, media_type: str) -> str: ...


class TextToSpeechProvider(Protocol):
    name: str

    def voices(self) -> list[Voice]: ...

    def synthesize(self, text: str, voice_id: str | None, speed: float, style: Style) -> Speech: ...


class FakeSpeechToText:
    """Test provider: a clip that starts with ``TEXT:`` transcribes to the rest."""

    name = "fake"

    def transcribe(self, audio: bytes, media_type: str) -> str:
        if audio.startswith(b"TEXT:"):
            return audio[5:].decode("utf-8", "replace").strip()
        return ""


class FakeTextToSpeech:
    """Test provider: returns a short silent WAV whose length follows the text."""

    name = "fake"

    def voices(self) -> list[Voice]:
        return [Voice("test-voice", "Test voice", "Silent test output, not a real voice")]

    def synthesize(self, text: str, voice_id: str | None, speed: float, style: Style) -> Speech:
        rate = 8000
        frames = int(rate * min(5.0, 0.05 * len(text.split()) / speed + 0.1))
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(struct.pack("<h", 0) * frames)
        return Speech(buf.getvalue(), "audio/wav")


def get_stt() -> SpeechToTextProvider | None:
    return FakeSpeechToText() if get_settings().stt_provider == "fake" else None


def get_tts() -> TextToSpeechProvider | None:
    return FakeTextToSpeech() if get_settings().tts_provider == "fake" else None
