"""Stage 10: messaging, acknowledgements, tasks, reports and the WebSocket stream."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from .helpers import client_for, make_user, sign_in

API = "/api/v1/comms"


def test_direct_messages_are_private_to_their_members(app: FastAPI, db: Session) -> None:
    a_user, b_user = make_user(db, "procurement"), make_user(db, "logistics")
    a, b = sign_in(app, a_user), sign_in(app, b_user)
    director = sign_in(app, make_user(db, "director"))
    conv = a.post(f"{API}/conversations/direct", json={"user_id": str(b_user.user.id)}).json()
    again = b.post(f"{API}/conversations/direct", json={"user_id": str(a_user.user.id)}).json()
    assert conv["id"] == again["id"]

    m = a.post(f"{API}/conversations/{conv['id']}/messages", json={"body": "Truck arrives at 3"})
    assert m.status_code == 201, m.text
    unread = next(c for c in b.get(f"{API}/conversations").json() if c["id"] == conv["id"])[
        "unread"
    ]
    assert unread == 1
    assert [x["body"] for x in b.get(f"{API}/conversations/{conv['id']}/messages").json()] == [
        "Truck arrives at 3"
    ]
    assert (
        next(c for c in b.get(f"{API}/conversations").json() if c["id"] == conv["id"])["unread"]
        == 0
    )

    # Not even the Director can read a conversation they are not part of.
    assert director.get(f"{API}/conversations/{conv['id']}/messages").status_code == 404
    assert all(c["id"] != conv["id"] for c in director.get(f"{API}/conversations").json())

    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE com_messages SET body = 'changed'"))
    db.rollback()


def test_announcements_and_acknowledgements(app: FastAPI, db: Session) -> None:
    director = sign_in(app, make_user(db, "director"))
    staff_user = make_user(db, "finance")
    staff = sign_in(app, staff_user)
    other = sign_in(app, make_user(db, "logistics"))
    ann = next(c for c in staff.get(f"{API}/conversations").json() if c["kind"] == "announcements")
    assert (
        staff.post(f"{API}/conversations/{ann['id']}/messages", json={"body": "hi"}).status_code
        == 403
    )
    msg = director.post(
        f"{API}/conversations/{ann['id']}/messages",
        json={"body": "Office closed Friday", "requires_ack": True},
    ).json()
    assert staff.post(f"{API}/messages/{msg['id']}/acknowledge").status_code == 200
    status = director.get(f"{API}/messages/{msg['id']}/acknowledgements").json()
    assert [p["display_name"] for p in status["acknowledged"]] == ["TEST finance"]
    assert len(status["pending"]) >= 1
    assert other.get(f"{API}/messages/{msg['id']}/acknowledgements").status_code == 403

    # Department channels: Director only; members are the department plus the Director.
    assert staff.post(f"{API}/conversations/channels", json={"name": "x" * 3}).status_code == 403
    ch = director.post(
        f"{API}/conversations/channels", json={"name": "Finance team", "department_code": "finance"}
    )
    assert ch.status_code == 201, ch.text
    assert {p["display_name"] for p in ch.json()["members"]} >= {"TEST finance", "TEST director"}
    assert other.get(f"{API}/conversations/{ch.json()['id']}/messages").status_code == 404


def test_tasks_and_reports(app: FastAPI, db: Session) -> None:
    director = sign_in(app, make_user(db, "director"))
    staff_user = make_user(db, "procurement")
    staff = sign_in(app, staff_user)
    peer_user = make_user(db, "logistics")
    peer = sign_in(app, peer_user)

    due = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    t = director.post(
        f"{API}/tasks",
        json={
            "title": "Get three quotes",
            "assigned_to": str(staff_user.user.id),
            "due_at": due,
            "priority": "high",
        },
    ).json()
    assert t["overdue"] is True and t["assigned_by"]["display_name"] == "TEST director"
    assert (
        staff.post(
            f"{API}/tasks", json={"title": "x" * 3, "assigned_to": str(peer_user.user.id)}
        ).status_code
        == 403
    )
    assert staff.post(f"{API}/tasks", json={"title": "My own reminder"}).status_code == 201
    assert peer.get(f"{API}/tasks/{t['id']}").status_code == 404

    assert (
        staff.post(
            f"{API}/tasks/{t['id']}/updates", json={"status": "cancelled", "note": "no"}
        ).status_code
        == 403
    )
    done = staff.post(
        f"{API}/tasks/{t['id']}/updates", json={"status": "done", "note": "Three quotes attached"}
    ).json()
    assert done["status"] == "done" and done["acknowledged_at"] and done["completed_at"]
    assert [u["note"] for u in director.get(f"{API}/tasks/{t['id']}").json()["updates"]] == [
        "Three quotes attached"
    ]

    today = str(date.today())
    assert (
        staff.post(
            f"{API}/reports",
            json={"kind": "morning_plan", "report_date": today, "body": "Visit suppliers"},
        ).status_code
        == 201
    )
    assert (
        staff.post(
            f"{API}/reports", json={"kind": "morning_plan", "report_date": today, "body": "Again"}
        ).status_code
        == 409
    )
    req = director.post(
        f"{API}/report-requests",
        json={"requested_from": str(staff_user.user.id), "topic": "Fuel costs this month"},
    ).json()
    assert (
        staff.post(
            f"{API}/report-requests",
            json={"requested_from": str(peer_user.user.id), "topic": "abc"},
        ).status_code
        == 403
    )
    ans = staff.post(
        f"{API}/reports",
        json={
            "kind": "requested",
            "report_date": today,
            "body": "Fuel was 1.2m",
            "request_id": req["id"],
        },
    )
    assert ans.status_code == 201, ans.text
    assert {r["kind"] for r in director.get(f"{API}/reports").json()} == {
        "morning_plan",
        "requested",
    }
    assert peer.get(f"{API}/reports").json() == []
    team = {row["user"]["id"]: row for row in director.get(f"{API}/team").json()}
    assert team[str(staff_user.user.id)]["morning_plan_today"] is True
    assert staff.get(f"{API}/team").status_code == 403


def test_websocket_delivers_events_to_the_right_user_only(app: FastAPI, db: Session) -> None:
    a_user, b_user = make_user(db, "procurement"), make_user(db, "logistics")
    a, b = sign_in(app, a_user), sign_in(app, b_user)
    with pytest.raises(WebSocketDisconnect), client_for(app).websocket_connect("/api/v1/ws"):
        pass  # no session cookie: refused
    conv = a.post(f"{API}/conversations/direct", json={"user_id": str(b_user.user.id)}).json()
    with b.websocket_connect("/api/v1/ws") as ws:
        assert json.loads(ws.receive_text())["type"] == "ready"
        a.post(f"{API}/conversations/{conv['id']}/messages", json={"body": "Ping"})
        event = json.loads(ws.receive_text())
        assert event["type"] == "message.created" and event["conversation_id"] == conv["id"]
        ws.send_text("ping")
        assert json.loads(ws.receive_text())["type"] == "pong"
    evil = {"origin": "https://evil.example"}
    with pytest.raises(WebSocketDisconnect), b.websocket_connect("/api/v1/ws", headers=evil):
        pass  # foreign origin: refused
