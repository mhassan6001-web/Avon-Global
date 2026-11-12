from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AskIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=4000)


class ConversationIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str | None = Field(default=None, max_length=200)


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ActionOut(BaseModel):
    id: uuid.UUID
    tool: str
    summary: str
    status: str
    error: str | None
    result: dict[str, Any] | None
    expires_at: datetime
    created_at: datetime


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    text: str
    tools_used: list[str]
    actions: list[ActionOut]
    created_at: datetime


class StatusOut(BaseModel):
    can_use: bool
    ai_configured: bool
    provider: str | None
    tools: list[dict[str, str]]
