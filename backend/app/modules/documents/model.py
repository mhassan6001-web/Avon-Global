"""Format-neutral document model shared by the PDF and Word renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Align = Literal["left", "right"]


@dataclass
class Column:
    title: str
    width: float  # relative
    align: Align = "left"


@dataclass
class Document:
    kind: str  # e.g. "Tax invoice", "Purchase order"
    number: str
    issuer: list[str]
    recipient_title: str
    recipient: list[str]
    meta: list[tuple[str, str]]
    columns: list[Column]
    rows: list[list[str]]
    totals: list[tuple[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    footer: list[str] = field(default_factory=list)
    banners: list[str] = field(default_factory=list)  # e.g. DRAFT, DEVELOPMENT DEMO DATA


@dataclass
class Sheet:
    title: str
    subtitle: list[str]
    headers: list[str]
    rows: list[list[str | float | int | None]]
    numeric: set[int] = field(default_factory=set)  # column indexes formatted as amounts
