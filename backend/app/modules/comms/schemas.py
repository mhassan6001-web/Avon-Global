"""Communications request and response models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DirectIn(_In):
    user_id: uuid.UUID


class ChannelIn(_In):
    name: str = Field(min_length=2, max_length=120)
    department_code: str | None = Field(default=None, max_length=40)
    member_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)


class MessageIn(_In):
    body: str = Field(min_length=1, max_length=10000)
    requires_ack: bool = False
    file_id: uuid.UUID | None = None


class Person(BaseModel):
    id: uuid.UUID
    display_name: str
    department: str | None = None


class ConversationOut(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    department_code: str | None
    members: list[Person]
    unread: int
    last_message_at: datetime | None


class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender: Person
    body: str
    requires_ack: bool
    ai_generated: bool
    file_id: uuid.UUID | None
    created_at: datetime
    acknowledged_by_me: bool
    ack_count: int


class AckStatus(BaseModel):
    message_id: uuid.UUID
    acknowledged: list[Person]
    pending: list[Person]


class TaskIn(_In):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    assigned_to: uuid.UUID | None = None  # default: myself
    due_at: datetime | None = None
    priority: Literal["low", "normal", "high", "urgent"] = "normal"


class TaskUpdateIn(_In):
    status: Literal["open", "in_progress", "blocked", "done", "cancelled"] | None = None
    note: str = Field(min_length=1, max_length=5000)
    file_id: uuid.UUID | None = None


class TaskUpdateOut(BaseModel):
    author: Person
    status: str | None
    note: str
    file_id: uuid.UUID | None
    created_at: datetime


class TaskOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    assigned_to: Person
    assigned_by: Person
    due_at: datetime | None
    priority: str
    status: str
    acknowledged_at: datetime | None
    completed_at: datetime | None
    overdue: bool
    ai_generated: bool
    updates: list[TaskUpdateOut] = []


class ReportRequestIn(_In):
    requested_from: uuid.UUID
    topic: str = Field(min_length=3, max_length=300)
    due_at: datetime | None = None


class ReportIn(_In):
    kind: Literal["morning_plan", "end_of_day", "requested"]
    report_date: date
    body: str = Field(min_length=3, max_length=20000)
    request_id: uuid.UUID | None = None
    file_id: uuid.UUID | None = None


class ReportRequestOut(BaseModel):
    id: uuid.UUID
    requested_by: Person
    requested_from: Person
    topic: str
    due_at: datetime | None
    status: str
    created_at: datetime


class ReportOut(BaseModel):
    id: uuid.UUID
    author: Person
    kind: str
    report_date: date
    body: str
    request_id: uuid.UUID | None
    file_id: uuid.UUID | None
    created_at: datetime


class TeamRow(BaseModel):
    user: Person
    open_tasks: int
    overdue_tasks: int
    done_last_7_days: int
    morning_plan_today: bool
    end_of_day_yesterday: bool
