"""Stage 11: JARVIS core — access, briefing, gateway, proposed actions, audit."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.ai import service as ai_service
from app.ai.provider import FakeProvider, ProviderResult
from app.ai.tools import TOOLS
from app.modules.comms.models import Message, Task
from app.platform.audit.models import AuditEvent

from .helpers import make_user, sign_in

API = "/api/v1/jarvis"


def _conv(c: Any) -> str:
    r = c.post(f"{API}/conversations", json={})
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _audits(db: Session, action: str) -> list[AuditEvent]:
    db.expire_all()
    return list(db.execute(select(AuditEvent).where(AuditEvent.action == action)).scalars())


def test_access_status_and_no_forbidden_tools(app: FastAPI, db: Session) -> None:
    staff = sign_in(app, make_user(db, "procurement"))
    assert staff.get(f"{API}/status").status_code == 403
    assert staff.get(f"{API}/briefing").status_code == 403

    director = sign_in(app, make_user(db, "director"))
    s = director.get(f"{API}/status").json()
    assert s["ai_configured"] is True and s["provider"] == "fake"
    names = {t["name"] for t in s["tools"]}
    assert {"daily_briefing", "prepare_task", "prepare_message"} <= names
    for t in TOOLS:
        for word in ("payment", "bank", "submit", "approve", "sql"):
            assert word not in t.name


def test_briefing_is_honest_when_there_is_no_data(app: FastAPI, db: Session) -> None:
    director = sign_in(app, make_user(db, "director"))
    b = director.get(f"{API}/briefing").json()
    keys = [s["key"] for s in b["sections"]]
    assert keys == ["approvals", "tenders", "receivables", "stock", "tasks", "staff"]
    by = {s["key"]: s for s in b["sections"]}
    assert by["receivables"]["empty"] is True
    assert by["receivables"]["lines"] == ["No posted customer balances are outstanding."]
    assert b["greeting"].startswith("Good ")


def test_read_tool_runs_through_gateway_and_is_audited(app: FastAPI, db: Session) -> None:
    director = sign_in(app, make_user(db, "director"))
    conv = _conv(director)
    r = director.post(
        f"{API}/conversations/{conv}/messages", json={"text": "Any approvals waiting?"}
    )
    assert r.status_code == 200, r.text
    msgs = r.json()
    assert msgs[0]["role"] == "user"
    assert msgs[1]["tools_used"] == ["list_pending_approvals"]
    assert msgs[-1]["text"].startswith("Here is what the system returned")
    assert _audits(db, "ai.tool.read")
    usage = db.execute(text("SELECT count(*) FROM ai_usage")).scalar()
    assert usage == 2
    history = director.get(f"{API}/conversations/{conv}/messages").json()
    assert [m["role"] for m in history] == ["user", "assistant", "assistant"]
    convs = director.get(f"{API}/conversations").json()
    assert convs[0]["title"] == "Any approvals waiting?"

    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE ai_messages SET text = 'changed'"))
    db.rollback()

    # Conversations are private to their owner.
    other = sign_in(app, make_user(db, "director"))
    assert other.get(f"{API}/conversations/{conv}/messages").status_code == 404


def test_prepared_task_needs_confirmation(app: FastAPI, db: Session) -> None:
    director = sign_in(app, make_user(db, "director"))
    conv = _conv(director)
    msgs = director.post(
        f"{API}/conversations/{conv}/messages",
        json={"text": "Create task: Call the clearing agent"},
    ).json()
    actions = [a for m in msgs for a in m["actions"]]
    assert len(actions) == 1 and actions[0]["status"] == "proposed"
    assert "Call the clearing agent" in actions[0]["summary"]
    db.expire_all()
    assert db.execute(select(Task)).first() is None  # nothing happened yet

    done = director.post(f"{API}/actions/{actions[0]['id']}/confirm")
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "executed"
    db.expire_all()
    task = db.execute(select(Task)).scalar_one()
    assert task.ai_generated is True and task.title == "Call the clearing agent"
    assert director.post(f"{API}/actions/{actions[0]['id']}/confirm").status_code == 409
    assert _audits(db, "ai.action.proposed") and _audits(db, "ai.action.executed")

    # Cancelled actions never run; other users cannot touch someone else's action.
    msgs = director.post(
        f"{API}/conversations/{conv}/messages", json={"text": "Create task: Second one"}
    ).json()
    second = next(a for m in msgs for a in m["actions"])["id"]
    intruder = sign_in(app, make_user(db, "director"))
    assert intruder.post(f"{API}/actions/{second}/confirm").status_code == 404
    assert director.get(f"{API}/actions").json()[0]["id"] == second
    assert director.post(f"{API}/actions/{second}/cancel").json()["status"] == "cancelled"
    db.expire_all()
    assert db.execute(text("SELECT count(*) FROM com_tasks")).scalar() == 1


class _Scripted(FakeProvider):
    """Always asks for one tool, then reports what came back."""

    def __init__(self, tool: str, args: dict[str, Any]) -> None:
        self.tool, self.args = tool, args

    def complete(self, system: str, messages: Any, tools: Any, max_tokens: int) -> ProviderResult:
        if any(b.get("type") == "tool_result" for b in messages[-1].content):
            return super().complete(system, messages, tools, max_tokens)
        return self._tool(self.tool, self.args)


def test_gateway_refuses_tools_outside_the_users_permissions(
    app: FastAPI, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    director = sign_in(app, make_user(db, "director"), step_up=True)
    staff_user = make_user(db, "procurement")
    grant = {"permission": "jarvis.use", "effect": "grant", "reason": "Pilot JARVIS access"}
    r = director.post(f"/api/v1/admin/users/{staff_user.user.id}/overrides", json=grant)
    assert r.status_code == 201, r.text
    staff = sign_in(app, staff_user)
    names = {t["name"] for t in staff.get(f"{API}/status").json()["tools"]}
    assert "receivables_ageing" not in names and "business_overview" not in names
    assert "staff" not in [s["key"] for s in staff.get(f"{API}/briefing").json()["sections"]]

    monkeypatch.setattr(ai_service, "get_provider", lambda: _Scripted("receivables_ageing", {}))
    conv = _conv(staff)
    msgs = staff.post(f"{API}/conversations/{conv}/messages", json={"text": "Who owes us?"}).json()
    assert "You do not have access" in msgs[-1]["text"]
    assert _audits(db, "ai.tool.denied")

    # Invalid input is rejected by validation before anything runs.
    monkeypatch.setattr(
        ai_service, "get_provider", lambda: _Scripted("prepare_task", {"title": "x"})
    )
    msgs = staff.post(f"{API}/conversations/{conv}/messages", json={"text": "task"}).json()
    assert "invalid input" in msgs[-1]["text"]

    # Staff cannot get JARVIS to assign work to someone else.
    other = make_user(db, "logistics")
    monkeypatch.setattr(
        ai_service,
        "get_provider",
        lambda: _Scripted("prepare_task", {"title": "Do this", "assigned_to": str(other.user.id)}),
    )
    msgs = staff.post(f"{API}/conversations/{conv}/messages", json={"text": "assign"}).json()
    assert "Only the Director assigns tasks" in msgs[-1]["text"]
    assert not [a for m in msgs for a in m["actions"]]


def test_prepared_message_is_labelled_and_sent_on_confirm(
    app: FastAPI, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    director = sign_in(app, make_user(db, "director"))
    colleague = make_user(db, "finance")
    monkeypatch.setattr(
        ai_service,
        "get_provider",
        lambda: _Scripted(
            "prepare_message",
            {"to_user_id": str(colleague.user.id), "body": "Please send the Q3 ageing."},
        ),
    )
    conv = _conv(director)
    msgs = director.post(f"{API}/conversations/{conv}/messages", json={"text": "message"}).json()
    action = next(a for m in msgs for a in m["actions"])
    db.expire_all()
    assert db.execute(select(Message)).first() is None
    assert director.post(f"{API}/actions/{action['id']}/confirm").json()["status"] == "executed"
    db.expire_all()
    msg = db.execute(select(Message)).scalar_one()
    assert msg.ai_generated is True and msg.body == "Please send the Q3 ageing."
    inbox = sign_in(app, colleague).get("/api/v1/comms/conversations").json()
    assert any(c["kind"] == "direct" for c in inbox)


def test_not_configured_is_explicit(
    app: FastAPI, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ai_service, "get_provider", lambda: None)
    director = sign_in(app, make_user(db, "director"))
    conv = _conv(director)
    r = director.post(f"{API}/conversations/{conv}/messages", json={"text": "hello"})
    assert r.status_code == 503
    assert "not configured" in r.json()["error"]["message"]
    assert director.get(f"{API}/briefing").status_code == 200
