"""Payroll arithmetic. Pure, Decimal-only, and driven entirely by configured
components: no tax band, rate or statutory amount is built in. Results are
for HR to check and the Director to approve; statutory settings must be
confirmed by a qualified local accountant before live use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def money(v: Decimal) -> Decimal:
    return v.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Band:
    """Rate applies to the slice of the base above ``from_amount`` up to ``to_amount``."""

    from_amount: Decimal
    to_amount: Decimal | None
    rate_pct: Decimal


@dataclass(frozen=True)
class Component:
    code: str
    name: str
    kind: str  # earning | deduction | employer
    method: str  # fixed | percent | bands
    amount: Decimal = Decimal(0)
    rate_pct: Decimal = Decimal(0)
    bands: tuple[Band, ...] = ()
    base: str = "gross"  # gross | taxable | basic
    taxable: bool = True  # for earnings: counts toward the taxable base
    order: int = 0


@dataclass
class Line:
    code: str
    name: str
    kind: str
    amount: Decimal


@dataclass
class Payslip:
    basic: Decimal
    gross: Decimal = Decimal(0)
    taxable: Decimal = Decimal(0)
    deductions: Decimal = Decimal(0)
    employer: Decimal = Decimal(0)
    net: Decimal = Decimal(0)
    lines: list[Line] = field(default_factory=list)


def banded(amount: Decimal, bands: tuple[Band, ...]) -> Decimal:
    total = Decimal(0)
    for band in sorted(bands, key=lambda b: b.from_amount):
        if amount <= band.from_amount:
            continue
        top = amount if band.to_amount is None else min(amount, band.to_amount)
        total += (top - band.from_amount) * band.rate_pct / 100
    return money(total)


def validate_bands(bands: tuple[Band, ...]) -> None:
    ordered = sorted(bands, key=lambda b: b.from_amount)
    for i, band in enumerate(ordered):
        if band.rate_pct < 0 or band.rate_pct > 100:
            raise ValueError("Band rates must be between 0 and 100.")
        if band.to_amount is not None and band.to_amount <= band.from_amount:
            raise ValueError("Each band must end above where it starts.")
        if i < len(ordered) - 1:
            nxt = ordered[i + 1]
            if band.to_amount is None or band.to_amount != nxt.from_amount:
                raise ValueError("Bands must be continuous with no gaps or overlaps.")


def calculate(
    basic: Decimal, components: list[Component], extra_earnings: list[Line] | None = None
) -> Payslip:
    if basic < 0:
        raise ValueError("Basic pay cannot be negative.")
    slip = Payslip(basic=money(basic))
    slip.lines.append(Line("BASIC", "Basic pay", "earning", slip.basic))
    slip.gross = slip.basic
    slip.taxable = slip.basic
    for extra in extra_earnings or []:
        slip.lines.append(extra)
        slip.gross += extra.amount
        slip.taxable += extra.amount
    ordered = sorted(components, key=lambda c: (c.kind != "earning", c.order, c.code))

    def base_of(c: Component) -> Decimal:
        return {"gross": slip.gross, "taxable": slip.taxable, "basic": slip.basic}[c.base]

    for c in ordered:
        if c.method == "fixed":
            value = money(c.amount)
        elif c.method == "percent":
            value = money(base_of(c) * c.rate_pct / 100)
        else:
            value = banded(base_of(c), c.bands)
        if value == 0:
            continue
        slip.lines.append(Line(c.code, c.name, c.kind, value))
        if c.kind == "earning":
            slip.gross += value
            if c.taxable:
                slip.taxable += value
        elif c.kind == "deduction":
            slip.deductions += value
        else:
            slip.employer += value
    slip.net = slip.gross - slip.deductions
    if slip.net < 0:
        raise ValueError("Deductions exceed gross pay.")
    return slip
