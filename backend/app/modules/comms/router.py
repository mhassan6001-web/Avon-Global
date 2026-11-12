"""Communications API (``/api/v1/comms``). Everyone signed in; members-only reading."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select

from app.core.errors import NotFoundError
from app.platform import realtime
from app.platform.authz.deps import DbSession, Principal, require

from . import schemas
from . import service as comms
from .models import Conversation, Message, Report, ReportRequest, Task

router = APIRouter(prefix="/comms", tags=["comms"])
Own = Depends(require("comms.own.use"))
Director = Depends(require(comms.ANNOUNCE))


@router.get("/people", response_model=list[schemas.Person])
def directory(db: DbSession, _: Principal = Own) -> list[schemas.Person]:
    """Colleague names and departments, for starting conversations and assigning tasks."""
    users = comms.active_users(db)
    return sorted(comms.people(db, {u.id for u in users}).values(), key=lambda p: p.display_name)


@router.get("/conversations", response_model=list[schemas.ConversationOut])
def list_conversations(db: DbSession, principal: Principal = Own) -> list[schemas.ConversationOut]:
    out = comms.conversations(db, principal)
    db.commit()
    return out


@router.post("/conversations/direct", response_model=schemas.ConversationOut)
def open_direct(
    body: schemas.DirectIn, db: DbSession, principal: Principal = Own
) -> schemas.ConversationOut:
    conv = comms.direct(db, principal, body.user_id)
    db.commit()
    return next(c for c in comms.conversations(db, principal) if c.id == conv.id)


@router.post("/conversations/channels", response_model=schemas.ConversationOut, status_code=201)
def create_channel(
    body: schemas.ChannelIn, db: DbSession, principal: Principal = Director
) -> schemas.ConversationOut:
    conv = comms.create_channel(db, body, principal)
    db.commit()
    return next(c for c in comms.conversations(db, principal) if c.id == conv.id)


@router.get("/conversations/{conv_id}/messages", response_model=list[schemas.MessageOut])
def list_messages(
    conv_id: uuid.UUID,
    db: DbSession,
    principal: Principal = Own,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[schemas.MessageOut]:
    return comms.messages(db, comms.get_conversation(db, conv_id, principal), principal, limit)


@router.post(
    "/conversations/{conv_id}/messages", response_model=schemas.MessageOut, status_code=201
)
def send_message(
    conv_id: uuid.UUID, body: schemas.MessageIn, db: DbSession, principal: Principal = Own
) -> schemas.MessageOut:
    conv = comms.get_conversation(db, conv_id, principal)
    msg = comms.send(db, conv, body, principal)
    db.commit()
    comms.notify_message(db, conv, msg)
    return next(m for m in comms.messages(db, conv, principal, 500) if m.id == msg.id)


def _message(
    db: DbSession, message_id: uuid.UUID, principal: Principal
) -> tuple[Message, Conversation]:
    msg = db.get(Message, message_id)
    if msg is None:
        raise NotFoundError("Message not found.")
    return msg, comms.get_conversation(db, msg.conversation_id, principal)


@router.post("/messages/{message_id}/acknowledge", response_model=dict[str, bool])
def acknowledge(
    message_id: uuid.UUID, db: DbSession, principal: Principal = Own
) -> dict[str, bool]:
    msg, _ = _message(db, message_id, principal)
    comms.acknowledge(db, msg, principal)
    db.commit()
    return {"acknowledged": True}


@router.get("/messages/{message_id}/acknowledgements", response_model=schemas.AckStatus)
def acknowledgements(
    message_id: uuid.UUID, db: DbSession, principal: Principal = Own
) -> schemas.AckStatus:
    msg, conv = _message(db, message_id, principal)
    return comms.ack_status(db, conv, msg, principal)


@router.get("/tasks", response_model=list[schemas.TaskOut])
def list_tasks(
    db: DbSession,
    principal: Principal = Own,
    view: str = Query(default="mine", pattern="^(mine|assigned_by_me)$"),
    include_closed: bool = False,
) -> list[schemas.TaskOut]:
    col = Task.assigned_to if view == "mine" else Task.assigned_by
    stmt = (
        select(Task)
        .where(col == principal.user.id)
        .order_by(Task.due_at.asc().nulls_last(), Task.created_at.desc())
    )
    if not include_closed:
        stmt = stmt.where(Task.status.not_in(("done", "cancelled")))
    return comms.tasks_out(db, list(db.execute(stmt.limit(500)).scalars()))


@router.post("/tasks", response_model=schemas.TaskOut, status_code=201)
def create_task(body: schemas.TaskIn, db: DbSession, principal: Principal = Own) -> schemas.TaskOut:
    task = comms.create_task(db, body, principal)
    db.commit()
    comms.notify_task(task, principal.user.id, "task.assigned")
    return comms.tasks_out(db, [task])[0]


@router.get("/tasks/{task_id}", response_model=schemas.TaskOut)
def get_task(task_id: uuid.UUID, db: DbSession, principal: Principal = Own) -> schemas.TaskOut:
    return comms.tasks_out(db, [comms.get_task(db, task_id, principal)], with_updates=True)[0]


@router.post("/tasks/{task_id}/updates", response_model=schemas.TaskOut)
def update_task(
    task_id: uuid.UUID, body: schemas.TaskUpdateIn, db: DbSession, principal: Principal = Own
) -> schemas.TaskOut:
    task = comms.update_task(db, comms.get_task(db, task_id, principal), body, principal)
    db.commit()
    comms.notify_task(task, principal.user.id, "task.updated")
    return comms.tasks_out(db, [task], with_updates=True)[0]


@router.get("/report-requests", response_model=list[schemas.ReportRequestOut])
def list_report_requests(
    db: DbSession, principal: Principal = Own
) -> list[schemas.ReportRequestOut]:
    rows = db.execute(
        select(ReportRequest)
        .where(
            or_(
                ReportRequest.requested_from == principal.user.id,
                ReportRequest.requested_by == principal.user.id,
            )
        )
        .order_by(ReportRequest.created_at.desc())
        .limit(200)
    ).scalars()
    return comms.requests_out(db, list(rows))


@router.post("/report-requests", response_model=schemas.ReportRequestOut, status_code=201)
def request_report(
    body: schemas.ReportRequestIn, db: DbSession, principal: Principal = Director
) -> schemas.ReportRequestOut:
    row = comms.request_report(db, body, principal)
    db.commit()
    realtime.publish([row.requested_from], {"type": "report.requested", "request_id": str(row.id)})
    return comms.requests_out(db, [row])[0]


@router.get("/reports", response_model=list[schemas.ReportOut])
def list_reports(
    db: DbSession,
    principal: Principal = Own,
    author_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[schemas.ReportOut]:
    return comms.reports_visible(db, principal, author_id, limit)


@router.post("/reports", response_model=schemas.ReportOut, status_code=201)
def submit_report(
    body: schemas.ReportIn, db: DbSession, principal: Principal = Own
) -> schemas.ReportOut:
    row: Report = comms.submit_report(db, body, principal)
    db.commit()
    return next(
        r for r in comms.reports_visible(db, principal, principal.user.id, 500) if r.id == row.id
    )


@router.get("/team", response_model=list[schemas.TeamRow])
def team(db: DbSession, _: Principal = Director) -> list[schemas.TeamRow]:
    return comms.team(db)
