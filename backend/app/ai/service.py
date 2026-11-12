"""Conversations with JARVIS: system prompt, history replay, the bounded
tool loop and the usage ledger."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError, ServiceUnavailableError
from app.core.request_context import get_request_id
from app.modules.organisation.models import OrganisationProfile
from app.platform.authz.deps import Principal

from . import gateway
from .models import AIConversation, AIMessage, AIUsage
from .provider import AIProvider, AIProviderError, ProviderMessage, ToolSpec, get_provider
from .tools import available

TZ = ZoneInfo("Africa/Blantyre")
HISTORY_LIMIT = 40
PROMPT = Path(__file__).parent / "prompts" / "jarvis_personality.md"

RULES = """
## System rules (enforced by the backend; stated so you can explain them)
- Use only the tools provided. They return only what this user may see. If a
  question needs data you have no tool for, say so plainly; never guess.
- Never invent figures, customers, suppliers, staff, tenders or outcomes. State
  the period and currency of every figure. Sections with no records: say so.
- prepare_* tools only propose. Tell the user to confirm the card on screen;
  never say a task was created or a message sent until the system confirms.
- You cannot make payments, change supplier bank details, submit tenders,
  approve anything or bypass approvals. Explain this if asked.
- If the request is ambiguous, ask one short clarifying question.
""".strip()


@lru_cache(maxsize=1)
def _personality() -> str:
    text = PROMPT.read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


def system_prompt(db: Session, p: Principal) -> str:
    currency = db.execute(select(OrganisationProfile.functional_currency).limit(1)).scalar()
    now = datetime.now(UTC).astimezone(TZ)
    tools = ", ".join(t.name for t in available(p)) or "none"
    context = (
        "## Context\n"
        f"- User: {p.user.display_name} ({p.role.name})\n"
        f"- Local time: {now:%A %d %B %Y, %H:%M} (Africa/Blantyre)\n"
        f"- Functional currency: {currency or 'MWK'}\n"
        f"- Tools available to this user: {tools}"
    )
    return f"{_personality()}\n\n{RULES}\n\n{context}"


def get_conversation(db: Session, p: Principal, conv_id: uuid.UUID) -> AIConversation:
    conv = db.get(AIConversation, conv_id)
    if conv is None or conv.user_id != p.user.id:
        raise NotFoundError("Conversation not found.")
    return conv


def history(db: Session, conv: AIConversation) -> list[ProviderMessage]:
    rows = list(
        db.execute(
            select(AIMessage)
            .where(AIMessage.conversation_id == conv.id)
            .order_by(AIMessage.created_at.desc(), AIMessage.id.desc())
            .limit(HISTORY_LIMIT)
        ).scalars()
    )[::-1]
    # Start at a plain user turn so tool results never lose their tool call.
    while rows and rows[0].role != "user":
        rows.pop(0)
    out: list[ProviderMessage] = []
    for r in rows:
        role = "assistant" if r.role == "assistant" else "user"
        if out and out[-1].role == role:
            out[-1].content.extend(r.content)
        else:
            out.append(ProviderMessage(role, list(r.content)))
    return out


def _store(
    db: Session, conv: AIConversation, role: str, content: list[dict[str, Any]], text: str
) -> AIMessage:
    msg = AIMessage(conversation_id=conv.id, role=role, content=content, text=text)
    db.add(msg)
    db.flush()
    return msg


def _usage(
    db: Session, p: Principal, conv: AIConversation, provider: AIProvider, outcome: str, **kw: Any
) -> None:
    db.add(
        AIUsage(
            user_id=p.user.id,
            conversation_id=conv.id,
            provider=provider.name,
            model=kw.pop("model", provider.model),
            outcome=outcome,
            request_id=(kw.pop("request_id", None) or get_request_id() or None),
            **kw,
        )
    )


def ask(
    db: Session, p: Principal, conv: AIConversation, text: str, advanced: bool = False
) -> list[AIMessage]:
    """``advanced`` selects the configured advanced model (higher cost) for this question."""
    provider = get_provider()
    if provider is None:
        raise ServiceUnavailableError(
            "JARVIS's AI service is not configured yet. The daily briefing still works."
        )
    settings = get_settings()
    model = settings.anthropic_advanced_model if advanced else None
    new = [_store(db, conv, "user", [{"type": "text", "text": text}], text)]
    tools = [ToolSpec(t.name, t.description, t.schema()) for t in available(p)]
    system = system_prompt(db, p)
    for _ in range(settings.ai_max_tool_rounds):
        try:
            result = provider.complete(
                system, history(db, conv), tools, settings.ai_max_output_tokens, model
            )
        except AIProviderError as exc:
            _usage(db, p, conv, provider, "error")
            new.append(
                _store(db, conv, "assistant", [{"type": "text", "text": exc.message}], exc.message)
            )
            break
        _usage(
            db, p, conv, provider, "ok", model=result.model, request_id=result.request_id,
            input_tokens=result.input_tokens, output_tokens=result.output_tokens,
            latency_ms=result.latency_ms,
        )  # fmt: skip
        new.append(_store(db, conv, "assistant", result.content, result.text))
        calls = result.tool_calls
        if not calls:
            break
        blocks = []
        for call in calls:
            content, is_error = gateway.run_tool(db, p, call["name"], call.get("input"), conv.id)
            blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": call["id"],
                    "content": content,
                    "is_error": is_error,
                }
            )
        new.append(_store(db, conv, "tool", blocks, ""))
    else:
        note = "I stopped after the maximum number of steps. Ask me to continue if needed."
        new.append(_store(db, conv, "assistant", [{"type": "text", "text": note}], note))
    conv.updated_at = datetime.now(UTC)
    return new
