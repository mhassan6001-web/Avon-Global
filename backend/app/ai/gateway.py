"""The ActionGateway: every JARVIS tool call, typed or spoken, goes through

authentication → permission → validation → business rules → approval →
execution → audit.

Authentication is done by the API dependency before any of this runs. Each
real step is published to the user's live channel so the interface can light
the matching node; the interface never runs ahead of these events.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.platform import realtime
from app.platform.audit import service as audit
from app.platform.authz.deps import Principal

from .models import AIAction
from .tools import BY_NAME, Tool, available

log = logging.getLogger("aven.jarvis")
ACTION_TTL = timedelta(minutes=30)
MAX_RESULT_CHARS = 12_000


def emit(
    p: Principal, step: str, tool: str, conversation_id: uuid.UUID | None, **extra: Any
) -> None:
    realtime.publish(
        [p.user.id],
        {
            "type": "jarvis.step",
            "step": step,
            "tool": tool,
            "conversation_id": str(conversation_id) if conversation_id else None,
            **extra,
        },
    )


def _deny(
    db: Session, p: Principal, name: str, conv: uuid.UUID | None, reason: str
) -> tuple[str, bool]:
    audit.record(
        db,
        action="ai.tool.denied",
        actor_id=p.user.id,
        outcome="denied",
        target_type="ai_tool",
        target_id=name[:64],
        details={"reason": reason, "via": "jarvis"},
    )
    emit(p, "failed", name, conv, reason=reason)
    return json.dumps({"error": reason}), True


def _encode(data: Any) -> str:
    text = json.dumps(data, default=str, ensure_ascii=False)
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + "… [truncated: ask a narrower question]"
    return text


def _tool_for(p: Principal, name: str) -> Tool | None:
    tool = BY_NAME.get(name)
    return tool if tool is not None and tool in available(p) else None


def run_tool(
    db: Session,
    p: Principal,
    name: str,
    raw_args: Any,
    conversation_id: uuid.UUID | None,
) -> tuple[str, bool]:
    """Run one model-proposed tool call. Returns (content for the model, is_error)."""
    emit(p, "interpreting", name, conversation_id)
    tool = _tool_for(p, name)
    if tool is None:
        return _deny(db, p, name, conversation_id, "You do not have access to that capability.")
    emit(p, "permission_ok", name, conversation_id)
    try:
        args = tool.args.model_validate(raw_args or {})
    except ValidationError as exc:
        emit(p, "failed", name, conversation_id, reason="invalid input")
        problems = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()]
        return json.dumps({"error": "invalid input", "problems": problems}), True
    emit(p, "validated", name, conversation_id)
    try:
        outcome = tool.run(db, p, args)
    except AppError as exc:  # business rule or permission refusal from the module
        return _deny(db, p, name, conversation_id, exc.message)

    if tool.category == "read":
        audit.record(
            db,
            action="ai.tool.read",
            actor_id=p.user.id,
            target_type="ai_tool",
            target_id=name,
            details={"args": args.model_dump(mode="json"), "via": "jarvis"},
        )
        emit(p, "audited", name, conversation_id)
        return _encode(outcome), False

    action = AIAction(
        user_id=p.user.id,
        conversation_id=conversation_id,
        tool=name,
        payload=args.model_dump(mode="json"),
        summary=str(outcome),
        expires_at=datetime.now(UTC) + ACTION_TTL,
    )
    db.add(action)
    db.flush()
    audit.record(
        db,
        action="ai.action.proposed",
        actor_id=p.user.id,
        target_type="ai_action",
        target_id=action.id,
        details={"tool": name, "via": "jarvis"},
    )
    emit(p, "awaiting_approval", name, conversation_id, action_id=str(action.id))
    return (
        json.dumps(
            {
                "status": "awaiting_user_confirmation",
                "action_id": str(action.id),
                "summary": action.summary,
                "note": "Nothing has been done yet. The user must confirm on screen.",
            },
            ensure_ascii=False,
        ),
        False,
    )


def _own_action(db: Session, p: Principal, action_id: uuid.UUID) -> AIAction:
    action = db.get(AIAction, action_id, with_for_update=True)
    if action is None or action.user_id != p.user.id:
        raise NotFoundError("Action not found.")
    if action.status != "proposed":
        raise ConflictError(f"This action is already {action.status}.")
    return action


def confirm(db: Session, p: Principal, action_id: uuid.UUID) -> tuple[AIAction, dict[str, Any]]:
    """Execute a proposed action after the user confirmed it on screen.
    Permissions and business rules are checked again at this moment."""
    action = _own_action(db, p, action_id)
    now = datetime.now(UTC)
    if action.expires_at <= now:
        action.status, action.decided_at = "expired", now
        action.error = "This prepared action expired. Ask JARVIS to prepare it again."
        return action, {}
    tool = _tool_for(p, action.tool)
    if tool is None or tool.execute is None:
        action.status, action.decided_at = "failed", now
        action.error = "You no longer have access to this capability."
        return action, {}
    emit(p, "executing", action.tool, action.conversation_id, action_id=str(action.id))
    try:
        with db.begin_nested():
            args = tool.args.model_validate(action.payload)
            tool.run(db, p, args)  # re-check business rules
            result = tool.execute(db, p, args)
    except (AppError, ValidationError) as exc:
        message = (
            exc.message if isinstance(exc, AppError) else "The prepared input is no longer valid."
        )
        action.status, action.decided_at, action.error = "failed", now, message
        audit.record(
            db,
            action="ai.action.failed",
            actor_id=p.user.id,
            outcome="failure",
            target_type="ai_action",
            target_id=action.id,
            details={"tool": action.tool, "reason": message, "via": "jarvis"},
        )
        emit(p, "failed", action.tool, action.conversation_id, action_id=str(action.id))
        return action, {}
    notify = result.pop("notify", None)
    action.status, action.decided_at, action.result = "executed", now, result
    audit.record(
        db,
        action="ai.action.executed",
        actor_id=p.user.id,
        target_type="ai_action",
        target_id=action.id,
        details={"tool": action.tool, "result": result, "via": "jarvis"},
    )
    return action, {"notify": notify, **result}


def cancel(db: Session, p: Principal, action_id: uuid.UUID) -> AIAction:
    action = _own_action(db, p, action_id)
    action.status, action.decided_at = "cancelled", datetime.now(UTC)
    audit.record(
        db,
        action="ai.action.cancelled",
        actor_id=p.user.id,
        target_type="ai_action",
        target_id=action.id,
        details={"tool": action.tool, "via": "jarvis"},
    )
    return action
