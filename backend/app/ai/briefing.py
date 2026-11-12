"""The daily briefing, built only from recorded data the user may see.

Deterministic: no AI model is needed, so the briefing works before an AI key
is configured. Every figure carries its date and currency. A section with no
records says so rather than guessing.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.platform.authz.deps import Principal

TZ = ZoneInfo("Africa/Blantyre")


class Section(BaseModel):
    key: str
    title: str
    lines: list[str]
    empty: bool
    href: str | None = None


class Briefing(BaseModel):
    generated_at: datetime
    local_date: date
    greeting: str
    sections: list[Section]


def _greeting(now: datetime, name: str) -> str:
    h = now.hour
    part = "Good morning" if h < 12 else "Good afternoon" if h < 18 else "Good evening"
    return f"{part}, {name.split()[0]}."


def _section(key: str, title: str, lines: list[str], empty: str, href: str) -> Section:
    return Section(key=key, title=title, lines=lines or [empty], empty=not lines, href=href)


def build(db: Session, p: Principal) -> Briefing:
    from app.modules.comms.router import list_tasks
    from app.platform.approvals.router import list_approvals

    now = datetime.now(UTC)
    local = now.astimezone(TZ)
    sections: list[Section] = []

    approvals = list_approvals(p, db, view="to_decide", limit=20)
    sections.append(
        _section(
            "approvals",
            "Pending approvals",
            [a.summary for a in approvals],
            "Nothing is waiting for your decision.",
            "/approvals",
        )
    )

    if p.has("tenders.records.view"):
        from app.modules.tenders.router import list_tenders

        page = list_tenders(
            db, p, q=None, status=None, kind=None, active_only=True,
            due_within_days=14, page=1, size=20,
        )  # fmt: skip
        sections.append(
            _section(
                "tenders",
                "Tender deadlines (next 14 days)",
                [
                    f"{t.reference} {t.title}: submission "
                    f"{t.submission_deadline.astimezone(TZ):%a %d %b %H:%M}"
                    for t in page.items
                ],
                "No active tender closes in the next 14 days.",
                "/tenders",
            )
        )

    if p.has("finance.records.view"):
        from app.modules.finance.router import ageing

        report = ageing(db, "receivable", p, None)
        totals: dict[str, Decimal] = defaultdict(Decimal)
        overdue: dict[str, Decimal] = defaultdict(Decimal)
        for r in report.rows:
            totals[r.currency] += r.total
            overdue[r.currency] += r.total - r.current
        lines = [
            f"Owed by customers as of {report.as_of:%d %b %Y}: {c} {totals[c]:,.2f} "
            f"(overdue {c} {overdue[c]:,.2f})"
            for c in sorted(totals)
            if totals[c]
        ]
        sections.append(
            _section(
                "receivables",
                "Customer payments outstanding",
                lines,
                "No posted customer balances are outstanding.",
                "/finance/reports",
            )
        )

    if p.has("inventory.records.view"):
        from app.modules.inventory.router import list_products

        low = list_products(db, p, q=None, below_reorder=True, include_inactive=False)
        sections.append(
            _section(
                "stock",
                "Stock at or below reorder level",
                [
                    f"{x.sku} {x.name}: {x.on_hand} on hand (reorder at {x.reorder_level})"
                    for x in low[:10]
                ],
                "No product is at or below its reorder level.",
                "/inventory",
            )
        )

    tasks = list_tasks(db, p, view="mine", include_closed=False)
    lines = [
        f"{'OVERDUE: ' if t.overdue else ''}{t.title}"
        + (f" (due {t.due_at.astimezone(TZ):%d %b %H:%M})" if t.due_at else "")
        for t in tasks[:10]
    ]
    sections.append(
        _section("tasks", "Your open tasks", lines, "You have no open tasks.", "/tasks")
    )

    if p.has("comms.announcements.send"):
        from app.modules.comms.router import team

        rows = team(db, p)
        lines = [
            f"{r.user.display_name}: {r.open_tasks} open, {r.overdue_tasks} overdue"
            for r in rows
            if r.overdue_tasks
        ]
        missing = [r.user.display_name for r in rows if not r.morning_plan_today]
        if missing and rows:
            lines.append(f"No morning plan yet today from: {', '.join(missing)}")
        sections.append(
            _section(
                "staff",
                "Staff activity",
                lines,
                "No overdue staff tasks recorded.",
                "/reports",
            )
        )

    return Briefing(
        generated_at=now,
        local_date=local.date(),
        greeting=_greeting(local, p.user.display_name),
        sections=sections,
    )
