"""Communication rules. Members-only reading; no silent access for anyone."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.platform import realtime
from app.platform.audit import service as audit
from app.platform.authz.deps import Principal
from app.platform.files.models import StoredFile
from app.platform.identity.models import Department, User

from . import schemas
from .models import (
    Acknowledgement,
    Conversation,
    Member,
    Message,
    Report,
    ReportRequest,
    Task,
    TaskUpdate,
)

ANNOUNCE = "comms.announcements.send"


class CommsRuleError(AppError):
    status_code = 422
    code = "validation_error"


def now() -> datetime:
    return datetime.now(UTC)


def people(db: Session, ids: set[uuid.UUID]) -> dict[uuid.UUID, schemas.Person]:
    if not ids:
        return {}
    rows = db.execute(
        select(User.id, User.display_name, Department.name)
        .join(Department, Department.id == User.department_id, isouter=True)
        .where(User.id.in_(ids))
    ).all()
    return {i: schemas.Person(id=i, display_name=n, department=d) for i, n, d in rows}


def active_users(db: Session) -> list[User]:
    return list(db.execute(select(User).where(User.status == "active")).scalars())


def _file_ok(db: Session, file_id: uuid.UUID | None, principal: Principal) -> None:
    if file_id is None:
        return
    f = db.get(StoredFile, file_id)
    if f is None or f.owner_id != principal.user.id:
        raise CommsRuleError("Attach a file you uploaded.")


# --- Conversations ---------------------------------------------------------------


def announcements(db: Session, actor: uuid.UUID) -> Conversation:
    conv = db.execute(
        select(Conversation).where(Conversation.kind == "announcements")
    ).scalar_one_or_none()
    if conv is None:
        conv = Conversation(kind="announcements", name="Company announcements", created_by=actor)
        db.add(conv)
        db.flush()
    return conv


def member_ids(db: Session, conv: Conversation) -> set[uuid.UUID]:
    if conv.kind == "announcements":
        return {u.id for u in active_users(db)}
    return set(
        db.execute(select(Member.user_id).where(Member.conversation_id == conv.id)).scalars()
    )


def can_read(db: Session, conv: Conversation, user_id: uuid.UUID) -> bool:
    if conv.kind == "announcements":
        return True
    return (
        db.execute(
            select(Member.user_id).where(
                Member.conversation_id == conv.id, Member.user_id == user_id
            )
        ).first()
        is not None
    )


def get_conversation(db: Session, conv_id: uuid.UUID, principal: Principal) -> Conversation:
    conv = db.get(Conversation, conv_id)
    # Same answer whether it does not exist or the user is not a member.
    if conv is None or not can_read(db, conv, principal.user.id):
        raise NotFoundError("Conversation not found.")
    return conv


def direct(db: Session, principal: Principal, other_id: uuid.UUID) -> Conversation:
    if other_id == principal.user.id:
        raise CommsRuleError("Start a conversation with someone else.")
    other = db.get(User, other_id)
    if other is None or other.status != "active":
        raise CommsRuleError("That person is not an active user.")
    key = ":".join(sorted((str(principal.user.id), str(other_id))))
    conv = db.execute(
        select(Conversation).where(Conversation.direct_key == key)
    ).scalar_one_or_none()
    if conv is None:
        conv = Conversation(kind="direct", direct_key=key, created_by=principal.user.id)
        db.add(conv)
        db.flush()
        db.add_all(
            [Member(conversation_id=conv.id, user_id=u) for u in (principal.user.id, other_id)]
        )
        db.flush()
    return conv


def create_channel(db: Session, body: schemas.ChannelIn, principal: Principal) -> Conversation:
    if not principal.has(ANNOUNCE):
        raise PermissionDeniedError("Only the Director creates group channels.")
    users = set(body.member_ids) | {principal.user.id}
    if body.department_code:
        dept = db.execute(
            select(Department).where(Department.code == body.department_code)
        ).scalar_one_or_none()
        if dept is None:
            raise CommsRuleError("Unknown department.")
        users |= set(
            db.execute(
                select(User.id).where(User.department_id == dept.id, User.status == "active")
            ).scalars()
        )
    known = set(db.execute(select(User.id).where(User.id.in_(users))).scalars())
    if known != users:
        raise CommsRuleError("Some members do not exist.")
    conv = Conversation(
        kind="channel",
        name=body.name,
        department_code=body.department_code,
        created_by=principal.user.id,
    )
    db.add(conv)
    db.flush()
    db.add_all([Member(conversation_id=conv.id, user_id=u) for u in users])
    audit.record(
        db,
        action="comms.channel.created",
        actor_id=principal.user.id,
        target_type="conversation",
        target_id=conv.id,
        details={"members": len(users)},
    )
    return conv


def conversations(db: Session, principal: Principal) -> list[schemas.ConversationOut]:
    uid = principal.user.id
    announcements(db, uid)
    convs = list(
        db.execute(
            select(Conversation).where(
                or_(
                    Conversation.kind == "announcements",
                    Conversation.id.in_(
                        select(Member.conversation_id).where(Member.user_id == uid)
                    ),
                )
            )
        ).scalars()
    )
    reads = dict(
        db.execute(select(Member.conversation_id, Member.last_read_at).where(Member.user_id == uid))
        .tuples()
        .all()
    )
    out = []
    for conv in convs:
        members = member_ids(db, conv)
        last_read = reads.get(conv.id)
        unread_q = (
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conv.id, Message.sender_id != uid)
        )
        if last_read:
            unread_q = unread_q.where(Message.created_at > last_read)
        last = db.execute(
            select(func.max(Message.created_at)).where(Message.conversation_id == conv.id)
        ).scalar()
        shown = people(db, members if conv.kind != "announcements" else set())
        title = (
            conv.name
            or ", ".join(p.display_name for i, p in shown.items() if i != uid)
            or "Conversation"
        )
        out.append(
            schemas.ConversationOut(
                id=conv.id,
                kind=conv.kind,
                title=title,
                department_code=conv.department_code,
                members=list(shown.values()),
                unread=db.execute(unread_q).scalar_one(),
                last_message_at=last,
            )
        )
    return sorted(
        out,
        key=lambda c: (
            c.kind != "announcements",
            -(c.last_message_at.timestamp() if c.last_message_at else 0),
        ),
    )


def messages(
    db: Session, conv: Conversation, principal: Principal, limit: int
) -> list[schemas.MessageOut]:
    rows = list(
        db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        ).scalars()
    )
    rows.reverse()
    ids = [m.id for m in rows]
    acks: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    if ids:
        for mid, uid in db.execute(
            select(Acknowledgement.message_id, Acknowledgement.user_id).where(
                Acknowledgement.message_id.in_(ids)
            )
        ).all():
            acks[mid].add(uid)
    senders = people(db, {m.sender_id for m in rows})
    member = db.execute(
        select(Member).where(Member.conversation_id == conv.id, Member.user_id == principal.user.id)
    ).scalar_one_or_none()
    if member is not None:
        member.last_read_at = now()
    elif conv.kind == "announcements":
        db.add(Member(conversation_id=conv.id, user_id=principal.user.id, last_read_at=now()))
    db.commit()
    return [
        schemas.MessageOut(
            id=m.id,
            conversation_id=m.conversation_id,
            sender=senders[m.sender_id],
            body=m.body,
            requires_ack=m.requires_ack,
            ai_generated=m.ai_generated,
            file_id=m.file_id,
            created_at=m.created_at,
            acknowledged_by_me=principal.user.id in acks[m.id],
            ack_count=len(acks[m.id]),
        )
        for m in rows
    ]


def send(
    db: Session,
    conv: Conversation,
    body: schemas.MessageIn,
    principal: Principal,
    ai_generated: bool = False,
) -> Message:
    if conv.kind == "announcements" and not principal.has(ANNOUNCE):
        raise PermissionDeniedError("Only the Director posts company announcements.")
    _file_ok(db, body.file_id, principal)
    msg = Message(
        conversation_id=conv.id,
        sender_id=principal.user.id,
        ai_generated=ai_generated,
        **body.model_dump(),
    )
    db.add(msg)
    db.flush()
    return msg


def notify_message(db: Session, conv: Conversation, msg: Message) -> None:
    targets = member_ids(db, conv) - {msg.sender_id}
    realtime.publish(
        targets,
        {
            "type": "message.created",
            "conversation_id": str(conv.id),
            "message_id": str(msg.id),
            "requires_ack": msg.requires_ack,
        },
    )


def acknowledge(db: Session, msg: Message, principal: Principal) -> None:
    if not msg.requires_ack:
        raise CommsRuleError("This message does not ask for acknowledgement.")
    if msg.sender_id == principal.user.id:
        raise CommsRuleError("You sent this message.")
    if db.get(Acknowledgement, (msg.id, principal.user.id)) is None:
        db.add(Acknowledgement(message_id=msg.id, user_id=principal.user.id))
        db.flush()
        realtime.publish(
            [msg.sender_id], {"type": "message.acknowledged", "message_id": str(msg.id)}
        )


def ack_status(
    db: Session, conv: Conversation, msg: Message, principal: Principal
) -> schemas.AckStatus:
    if msg.sender_id != principal.user.id:
        raise PermissionDeniedError("Only the sender sees who acknowledged.")
    done = set(
        db.execute(
            select(Acknowledgement.user_id).where(Acknowledgement.message_id == msg.id)
        ).scalars()
    )
    everyone = member_ids(db, conv) - {msg.sender_id}
    ppl = people(db, everyone)
    return schemas.AckStatus(
        message_id=msg.id,
        acknowledged=[p for i, p in ppl.items() if i in done],
        pending=[p for i, p in ppl.items() if i not in done],
    )


# --- Tasks -------------------------------------------------------------------------


def tasks_out(db: Session, rows: list[Task], with_updates: bool = False) -> list[schemas.TaskOut]:
    ppl = people(db, {r.assigned_to for r in rows} | {r.assigned_by for r in rows})
    updates: dict[uuid.UUID, list[schemas.TaskUpdateOut]] = defaultdict(list)
    if with_updates and rows:
        ups = list(
            db.execute(
                select(TaskUpdate)
                .where(TaskUpdate.task_id.in_([r.id for r in rows]))
                .order_by(TaskUpdate.created_at)
            ).scalars()
        )
        authors = people(db, {u.author_id for u in ups})
        for u in ups:
            updates[u.task_id].append(
                schemas.TaskUpdateOut(
                    author=authors[u.author_id],
                    status=u.status,
                    note=u.note,
                    file_id=u.file_id,
                    created_at=u.created_at,
                )
            )
    t = now()
    return [
        schemas.TaskOut(
            id=r.id,
            title=r.title,
            description=r.description,
            assigned_to=ppl[r.assigned_to],
            assigned_by=ppl[r.assigned_by],
            due_at=r.due_at,
            priority=r.priority,
            status=r.status,
            acknowledged_at=r.acknowledged_at,
            completed_at=r.completed_at,
            overdue=bool(r.due_at and r.due_at < t and r.status not in ("done", "cancelled")),
            ai_generated=r.ai_generated,
            updates=updates.get(r.id, []),
        )
        for r in rows
    ]


def create_task(
    db: Session, body: schemas.TaskIn, principal: Principal, ai_generated: bool = False
) -> Task:
    assignee = body.assigned_to or principal.user.id
    if assignee != principal.user.id and not principal.has(ANNOUNCE):
        raise PermissionDeniedError("Only the Director assigns tasks to other people.")
    user = db.get(User, assignee)
    if user is None or user.status != "active":
        raise CommsRuleError("That person is not an active user.")
    task = Task(
        title=body.title,
        description=body.description,
        assigned_to=assignee,
        assigned_by=principal.user.id,
        due_at=body.due_at,
        priority=body.priority,
        ai_generated=ai_generated,
    )
    db.add(task)
    db.flush()
    audit.record(
        db,
        action="comms.task.assigned",
        actor_id=principal.user.id,
        target_type="task",
        target_id=task.id,
        details={"assignee": str(assignee)},
    )
    return task


def get_task(db: Session, task_id: uuid.UUID, principal: Principal) -> Task:
    task = db.get(Task, task_id)
    if task is None or principal.user.id not in (task.assigned_to, task.assigned_by):
        raise NotFoundError("Task not found.")
    return task


def update_task(db: Session, task: Task, body: schemas.TaskUpdateIn, principal: Principal) -> Task:
    uid = principal.user.id
    if task.status in ("done", "cancelled") and body.status not in (None, "open", "in_progress"):
        raise ConflictError("This task is closed.")
    if body.status == "cancelled" and uid != task.assigned_by:
        raise PermissionDeniedError("Only the person who assigned the task can cancel it.")
    if (
        body.status in ("open", "in_progress")
        and task.status in ("done", "cancelled")
        and uid != task.assigned_by
    ):
        raise PermissionDeniedError("Only the person who assigned the task can reopen it.")
    _file_ok(db, body.file_id, principal)
    if uid == task.assigned_to and task.acknowledged_at is None:
        task.acknowledged_at = now()
    if body.status:
        task.status = body.status
        task.completed_at = now() if body.status == "done" else None
    db.add(
        TaskUpdate(
            task_id=task.id, author_id=uid, status=body.status, note=body.note, file_id=body.file_id
        )
    )
    db.flush()
    return task


def notify_task(task: Task, actor: uuid.UUID, kind: str) -> None:
    targets = {task.assigned_to, task.assigned_by} - {actor}
    realtime.publish(targets, {"type": kind, "task_id": str(task.id), "status": task.status})


# --- Reports -------------------------------------------------------------------------


def request_report(
    db: Session, body: schemas.ReportRequestIn, principal: Principal
) -> ReportRequest:
    if not principal.has(ANNOUNCE):
        raise PermissionDeniedError("Only the Director requests reports.")
    if db.get(User, body.requested_from) is None:
        raise CommsRuleError("Unknown person.")
    row = ReportRequest(requested_by=principal.user.id, **body.model_dump())
    db.add(row)
    db.flush()
    return row


def submit_report(db: Session, body: schemas.ReportIn, principal: Principal) -> Report:
    if body.report_date > now().date() + timedelta(days=1):
        raise CommsRuleError("A report cannot be dated in the future.")
    _file_ok(db, body.file_id, principal)
    req = None
    if body.kind == "requested":
        if body.request_id is None:
            raise CommsRuleError("Choose the report request you are answering.")
        req = db.get(ReportRequest, body.request_id)
        if req is None or req.requested_from != principal.user.id:
            raise NotFoundError("Report request not found.")
        if req.status != "open":
            raise ConflictError("This request has already been answered.")
    elif body.request_id:
        raise CommsRuleError("Only requested reports link to a request.")
    exists = db.execute(
        select(Report.id).where(
            Report.author_id == principal.user.id,
            Report.kind == body.kind,
            Report.report_date == body.report_date,
            Report.request_id.is_(None)
            if body.request_id is None
            else Report.request_id == body.request_id,
        )
    ).first()
    if exists:
        raise ConflictError("You have already submitted this report.")
    row = Report(author_id=principal.user.id, **body.model_dump())
    db.add(row)
    if req is not None:
        req.status = "submitted"
    db.flush()
    return row


def reports_visible(
    db: Session, principal: Principal, author_id: uuid.UUID | None, limit: int
) -> list[schemas.ReportOut]:
    """Own reports, answers to my requests; the Director also sees daily plans and EOD reports."""
    uid = principal.user.id
    conditions = [
        Report.author_id == uid,
        Report.request_id.in_(select(ReportRequest.id).where(ReportRequest.requested_by == uid)),
    ]
    if principal.has(ANNOUNCE):
        conditions.append(Report.kind.in_(("morning_plan", "end_of_day")))
    stmt = (
        select(Report)
        .where(or_(*conditions))
        .order_by(Report.report_date.desc(), Report.created_at.desc())
        .limit(limit)
    )
    if author_id:
        stmt = stmt.where(Report.author_id == author_id)
    rows = list(db.execute(stmt).scalars())
    ppl = people(db, {r.author_id for r in rows})
    return [
        schemas.ReportOut(
            id=r.id,
            author=ppl[r.author_id],
            kind=r.kind,
            report_date=r.report_date,
            body=r.body,
            request_id=r.request_id,
            file_id=r.file_id,
            created_at=r.created_at,
        )
        for r in rows
    ]


def requests_out(db: Session, rows: list[ReportRequest]) -> list[schemas.ReportRequestOut]:
    ppl = people(db, {r.requested_by for r in rows} | {r.requested_from for r in rows})
    return [
        schemas.ReportRequestOut(
            id=r.id,
            requested_by=ppl[r.requested_by],
            requested_from=ppl[r.requested_from],
            topic=r.topic,
            due_at=r.due_at,
            status=r.status,
            created_at=r.created_at,
        )
        for r in rows
    ]


def team(db: Session) -> list[schemas.TeamRow]:
    """Director overview built only from tasks and reports staff knowingly submit."""
    today = now().date()
    yesterday = today - timedelta(days=1)
    week = now() - timedelta(days=7)
    out = []
    for user in active_users(db):
        tasks = list(db.execute(select(Task).where(Task.assigned_to == user.id)).scalars())
        open_ = [t for t in tasks if t.status not in ("done", "cancelled")]
        reports = set(
            db.execute(
                select(Report.kind, Report.report_date).where(
                    Report.author_id == user.id, Report.report_date.in_((today, yesterday))
                )
            )
            .tuples()
            .all()
        )
        out.append(
            schemas.TeamRow(
                user=people(db, {user.id})[user.id],
                open_tasks=len(open_),
                overdue_tasks=sum(1 for t in open_ if t.due_at and t.due_at < now()),
                done_last_7_days=sum(1 for t in tasks if t.completed_at and t.completed_at >= week),
                morning_plan_today=("morning_plan", today) in reports,
                end_of_day_yesterday=("end_of_day", yesterday) in reports,
            )
        )
    return sorted(out, key=lambda r: r.user.display_name)
