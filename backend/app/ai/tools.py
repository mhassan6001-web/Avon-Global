"""Typed JARVIS tools. Each wraps an existing, permission-checked business
function; none touches SQL or the ORM session directly.

* ``read`` tools return data the caller is already allowed to see.
* ``prepare`` tools create a proposed action. Nothing changes until the user
  confirms it on screen, and the change then runs through the module's own
  service with its business rules.

Never registered, by design: payments, supplier bank changes, tender
submission, approving anything, or any tool that bypasses approvals.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.platform.authz.deps import Principal

Category = Literal["read", "prepare"]


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class NoArgs(_Args):
    pass


class TendersDueArgs(_Args):
    days: int = Field(default=14, ge=1, le=90, description="Look-ahead window in days")


class SearchArgs(_Args):
    q: str = Field(min_length=2, max_length=100, description="Name or part of a name")


class RequestsArgs(_Args):
    status: str | None = Field(default=None, max_length=20, description="Optional status filter")


class TaskArgs(_Args):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    assigned_to: uuid.UUID | None = Field(
        default=None, description="Colleague's id from find_colleague; omit for the user"
    )
    due_at: datetime | None = Field(default=None, description="ISO 8601 with time zone")
    priority: Literal["low", "normal", "high", "urgent"] = "normal"


class MessageArgs(_Args):
    to_user_id: uuid.UUID = Field(description="Colleague's id from find_colleague")
    body: str = Field(min_length=1, max_length=5000)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    category: Category
    permission: str
    args: type[_Args]
    # read: returns JSON-safe data. prepare: returns a one-line summary after
    # validating the business rules without changing anything.
    run: Callable[[Session, Principal, Any], Any]
    # prepare only: performs the change through the module service.
    execute: Callable[[Session, Principal, Any], dict[str, Any]] | None = None

    def schema(self) -> dict[str, Any]:
        s = self.args.model_json_schema()
        s.pop("title", None)
        return s


def _dump(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_dump(v) for v in value]
    return value


# --- read tools ----------------------------------------------------------


def _overview(db: Session, p: Principal, _: NoArgs) -> Any:
    from app.modules.director.router import dashboard

    return _dump(dashboard(db, p))


def _approvals(db: Session, p: Principal, _: NoArgs) -> Any:
    from app.platform.approvals.router import list_approvals

    return _dump(list_approvals(p, db, view="to_decide", limit=20))


def _tenders(db: Session, p: Principal, a: TendersDueArgs) -> Any:
    from app.modules.tenders.router import list_tenders

    page = list_tenders(
        db, p, q=None, status=None, kind=None, active_only=True,
        due_within_days=a.days, page=1, size=20,
    )  # fmt: skip
    return _dump(page)


def _receivables(db: Session, p: Principal, _: NoArgs) -> Any:
    from app.modules.finance.router import ageing

    return _dump(ageing(db, "receivable", p, None))


def _stock(db: Session, p: Principal, _: NoArgs) -> Any:
    from app.modules.inventory.router import list_products

    rows = list_products(db, p, q=None, below_reorder=True, include_inactive=False)
    return [
        {
            "sku": r.sku,
            "name": r.name,
            "on_hand": str(r.on_hand),
            "reorder_level": str(r.reorder_level),
        }
        for r in rows[:50]
    ]


def _my_tasks(db: Session, p: Principal, _: NoArgs) -> Any:
    from app.modules.comms.router import list_tasks

    return _dump(list_tasks(db, p, view="mine", include_closed=False))


def _customers(db: Session, p: Principal, a: SearchArgs) -> Any:
    from app.modules.crm.router import list_customers

    page = list_customers(
        db, p, q=a.q, status=None, country=None, owner_id=None,
        include_archived=False, page=1, size=10,
    )  # fmt: skip
    return _dump(page)


def _requests(db: Session, p: Principal, a: RequestsArgs) -> Any:
    from app.modules.procurement.router import list_requests

    return _dump(list_requests(db, p, q=None, status=a.status, page=1, size=20))


def _colleagues(db: Session, p: Principal, a: SearchArgs) -> Any:
    from app.modules.comms.router import directory

    needle = a.q.lower()
    return [_dump(x) for x in directory(db, p) if needle in x.display_name.lower()][:10]


def _briefing(db: Session, p: Principal, _: NoArgs) -> Any:
    from app.ai.briefing import build

    return _dump(build(db, p))


# --- prepare tools -------------------------------------------------------


def _task_summary(db: Session, p: Principal, a: TaskArgs) -> str:
    from app.core.errors import PermissionDeniedError
    from app.modules.comms import service as comms
    from app.platform.identity.models import User

    target = a.assigned_to or p.user.id
    if target != p.user.id and not p.has(comms.ANNOUNCE):
        raise PermissionDeniedError("Only the Director assigns tasks to other people.")
    user = db.get(User, target)
    if user is None or user.status != "active":
        raise PermissionDeniedError("That person is not an active user.")
    who = "you" if target == p.user.id else user.display_name
    due = f", due {a.due_at:%d %b %Y %H:%M}" if a.due_at else ""
    return f"Create task “{a.title}” for {who} ({a.priority}{due})."


def _task_execute(db: Session, p: Principal, a: TaskArgs) -> dict[str, Any]:
    from app.modules.comms import schemas
    from app.modules.comms import service as comms

    body = schemas.TaskIn(**a.model_dump())
    task = comms.create_task(db, body, p, ai_generated=True)
    return {"task_id": str(task.id), "notify": "task"}


def _message_summary(db: Session, p: Principal, a: MessageArgs) -> str:
    from app.core.errors import PermissionDeniedError
    from app.platform.identity.models import User

    user = db.get(User, a.to_user_id)
    if user is None or user.status != "active" or user.id == p.user.id:
        raise PermissionDeniedError("That person is not an active colleague.")
    preview = a.body if len(a.body) <= 160 else a.body[:157] + "…"
    return f"Send {user.display_name} a message on your behalf: “{preview}”"


def _message_execute(db: Session, p: Principal, a: MessageArgs) -> dict[str, Any]:
    from app.modules.comms import schemas
    from app.modules.comms import service as comms

    conv = comms.direct(db, p, a.to_user_id)
    msg = comms.send(db, conv, schemas.MessageIn(body=a.body), p, ai_generated=True)
    return {"conversation_id": str(conv.id), "message_id": str(msg.id), "notify": "message"}


TOOLS: tuple[Tool, ...] = (
    Tool("daily_briefing", "The user's briefing: approvals, deadlines, finance, stock, tasks. "
         "Only sections the user may see.", "read", "jarvis.use", NoArgs, _briefing),
    Tool("business_overview", "Director command-centre figures (pipeline, finance, tenders, "
         "procurement).", "read", "director.dashboard.view", NoArgs, _overview),
    Tool("list_pending_approvals", "Approval requests waiting for this user's decision.",
         "read", "jarvis.use", NoArgs, _approvals),
    Tool("tenders_due", "Active tenders with deadlines within N days.", "read",
         "tenders.records.view", TendersDueArgs, _tenders),
    Tool("receivables_ageing", "Customer balances outstanding, by age.", "read",
         "finance.records.view", NoArgs, _receivables),
    Tool("stock_below_reorder", "Products at or below their reorder level.", "read",
         "inventory.records.view", NoArgs, _stock),
    Tool("list_my_tasks", "The user's open tasks.", "read", "comms.own.use", NoArgs, _my_tasks),
    Tool("search_customers", "Find customers by name.", "read", "crm.records.view", SearchArgs,
         _customers),
    Tool("purchase_requests", "Purchase requests, optionally by status.", "read",
         "procurement.records.view", RequestsArgs, _requests),
    Tool("find_colleague", "Find an active colleague's id and department by name.", "read",
         "comms.own.use", SearchArgs, _colleagues),
    Tool("prepare_task", "Prepare a task. The user must confirm before it is created.",
         "prepare", "comms.own.use", TaskArgs, _task_summary, _task_execute),
    Tool("prepare_message", "Prepare a direct message to a colleague, sent on the user's "
         "behalf and labelled as prepared by JARVIS. The user must confirm before it is sent.",
         "prepare", "comms.own.use", MessageArgs, _message_summary, _message_execute),
)  # fmt: skip
BY_NAME: dict[str, Tool] = {t.name: t for t in TOOLS}

# Defence in depth: these capabilities must never become tools.
FORBIDDEN_WORDS = ("payment", "bank", "submit", "approve", "decide", "sql")
assert not any(w in t.name for t in TOOLS for w in FORBIDDEN_WORDS), (
    "a forbidden capability was registered as a JARVIS tool"
)


def available(principal: Principal) -> list[Tool]:
    """Tools this user may use. The model is only told about these."""
    if not principal.has("jarvis.use"):
        return []
    return [t for t in TOOLS if principal.has(t.permission)]
