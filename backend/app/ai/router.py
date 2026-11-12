"""JARVIS API (``/api/v1/jarvis``)."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.config import get_settings
from app.modules.comms import service as comms
from app.modules.comms.models import Conversation, Message, Task
from app.platform.authz.deps import DbSession, Principal, require

from . import gateway, schemas, service
from .briefing import Briefing, build
from .models import AIAction, AIConversation, AIMessage
from .provider import get_provider
from .tools import available

router = APIRouter(prefix="/jarvis", tags=["jarvis"])
Use = Depends(require("jarvis.use"))


def _action_out(a: AIAction) -> schemas.ActionOut:
    return schemas.ActionOut.model_validate(a, from_attributes=True)


def _messages_out(db: DbSession, rows: list[AIMessage]) -> list[schemas.MessageOut]:
    """Messages for display. Tool-result turns are folded into the turn before."""
    ids: set[uuid.UUID] = set()
    for r in rows:
        for b in r.content:
            if b.get("type") == "tool_result" and not b.get("is_error"):
                try:
                    data = json.loads(b.get("content") or "{}")
                except ValueError:
                    continue
                if isinstance(data, dict) and data.get("action_id"):
                    ids.add(uuid.UUID(data["action_id"]))
    actions = (
        {a.id: a for a in db.execute(select(AIAction).where(AIAction.id.in_(ids))).scalars()}
        if ids
        else {}
    )
    out: list[schemas.MessageOut] = []
    for r in rows:
        if r.role == "tool":
            linked = []
            for b in r.content:
                try:
                    data = json.loads(b.get("content") or "{}")
                except ValueError:
                    continue
                if isinstance(data, dict) and data.get("action_id"):
                    a = actions.get(uuid.UUID(data["action_id"]))
                    if a:
                        linked.append(_action_out(a))
            if out:
                out[-1].actions.extend(linked)
            continue
        tools = [b["name"] for b in r.content if b.get("type") == "tool_use"]
        if not r.text and not tools:
            continue
        out.append(
            schemas.MessageOut(
                id=r.id,
                role=r.role,
                text=r.text,
                tools_used=tools,
                actions=[],
                created_at=r.created_at,
            )
        )
    return out


@router.get("/status", response_model=schemas.StatusOut)
def status(principal: Principal = Use) -> schemas.StatusOut:
    provider = get_provider()
    return schemas.StatusOut(
        can_use=True,
        ai_configured=provider is not None,
        provider=provider.name if provider else None,
        model=provider.model if provider else None,
        advanced_model=get_settings().anthropic_advanced_model if provider else None,
        tools=[
            {"name": t.name, "category": t.category, "description": t.description}
            for t in available(principal)
        ],
    )


@router.get("/briefing", response_model=Briefing)
def briefing(db: DbSession, principal: Principal = Use) -> Briefing:
    return build(db, principal)


@router.get("/conversations", response_model=list[schemas.ConversationOut])
def list_conversations(db: DbSession, principal: Principal = Use) -> list[schemas.ConversationOut]:
    rows = db.execute(
        select(AIConversation)
        .where(AIConversation.user_id == principal.user.id)
        .order_by(AIConversation.updated_at.desc())
        .limit(50)
    ).scalars()
    return [schemas.ConversationOut.model_validate(c, from_attributes=True) for c in rows]


@router.post("/conversations", response_model=schemas.ConversationOut, status_code=201)
def create_conversation(
    body: schemas.ConversationIn, db: DbSession, principal: Principal = Use
) -> schemas.ConversationOut:
    conv = AIConversation(user_id=principal.user.id, title=body.title or "New conversation")
    db.add(conv)
    db.commit()
    return schemas.ConversationOut.model_validate(conv, from_attributes=True)


@router.get("/conversations/{conv_id}/messages", response_model=list[schemas.MessageOut])
def list_messages(
    conv_id: uuid.UUID, db: DbSession, principal: Principal = Use
) -> list[schemas.MessageOut]:
    conv = service.get_conversation(db, principal, conv_id)
    rows = list(
        db.execute(
            select(AIMessage)
            .where(AIMessage.conversation_id == conv.id)
            .order_by(AIMessage.created_at, AIMessage.id)
            .limit(500)
        ).scalars()
    )
    return _messages_out(db, rows)


@router.post("/conversations/{conv_id}/messages", response_model=list[schemas.MessageOut])
def ask(
    conv_id: uuid.UUID, body: schemas.AskIn, db: DbSession, principal: Principal = Use
) -> list[schemas.MessageOut]:
    conv = service.get_conversation(db, principal, conv_id)
    if conv.title == "New conversation":
        conv.title = body.text[:80]
    new = service.ask(db, principal, conv, body.text, advanced=body.depth == "advanced")
    db.commit()
    return _messages_out(db, new)


@router.get("/actions", response_model=list[schemas.ActionOut])
def pending_actions(db: DbSession, principal: Principal = Use) -> list[schemas.ActionOut]:
    rows = db.execute(
        select(AIAction)
        .where(AIAction.user_id == principal.user.id, AIAction.status == "proposed")
        .order_by(AIAction.created_at.desc())
        .limit(20)
    ).scalars()
    return [_action_out(a) for a in rows]


@router.post("/actions/{action_id}/confirm", response_model=schemas.ActionOut)
def confirm(action_id: uuid.UUID, db: DbSession, principal: Principal = Use) -> schemas.ActionOut:
    action, result = gateway.confirm(db, principal, action_id)
    db.commit()
    if action.status == "executed":
        gateway.emit(
            principal, "audited", action.tool, action.conversation_id, action_id=str(action.id)
        )
        if result.get("notify") == "task":
            task = db.get(Task, uuid.UUID(result["task_id"]))
            if task is not None:
                comms.notify_task(task, principal.user.id, "task.assigned")
        elif result.get("notify") == "message":
            conv = db.get(Conversation, uuid.UUID(result["conversation_id"]))
            msg = db.get(Message, uuid.UUID(result["message_id"]))
            if conv is not None and msg is not None:
                comms.notify_message(db, conv, msg)
    return _action_out(action)


@router.post("/actions/{action_id}/cancel", response_model=schemas.ActionOut)
def cancel(action_id: uuid.UUID, db: DbSession, principal: Principal = Use) -> schemas.ActionOut:
    action = gateway.cancel(db, principal, action_id)
    db.commit()
    return _action_out(action)
