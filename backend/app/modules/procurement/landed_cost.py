"""Landed-cost estimate. Pure arithmetic with ``Decimal``; every rate is an input.

No duty, excise or VAT rate is stored or assumed here (master §9: tax rates are
configuration, never hardcoded). The result is an estimate for decision
support, labelled as such, and must be confirmed with the clearing agent and
the revenue authority's current tariff before it is relied on.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class LandedCostInput:
    goods_value: Decimal  # in the supplier's currency
    freight: Decimal  # supplier currency
    insurance: Decimal  # supplier currency
    exchange_rate: Decimal  # functional currency per 1 unit of supplier currency
    duty_rate_pct: Decimal
    excise_rate_pct: Decimal
    vat_rate_pct: Decimal
    vat_recoverable: bool
    local_charges: Decimal  # clearing, port, inland transport: functional currency
    quantity: Decimal | None = None


@dataclass(frozen=True)
class LandedCost:
    customs_value: Decimal
    duty: Decimal
    excise: Decimal
    vat: Decimal
    local_charges: Decimal
    landed_cost: Decimal
    unit_cost: Decimal | None
    vat_included_in_cost: bool


def calculate(i: LandedCostInput) -> LandedCost:
    for name in ("goods_value", "freight", "insurance", "local_charges"):
        if getattr(i, name) < 0:
            raise ValueError(f"{name} cannot be negative")
    if i.exchange_rate <= 0:
        raise ValueError("exchange_rate must be greater than zero")
    for name in ("duty_rate_pct", "excise_rate_pct", "vat_rate_pct"):
        rate = getattr(i, name)
        if rate < 0 or rate > 500:
            raise ValueError(f"{name} must be between 0 and 500")
    if i.quantity is not None and i.quantity <= 0:
        raise ValueError("quantity must be greater than zero")

    hundred = Decimal(100)
    customs_value = money((i.goods_value + i.freight + i.insurance) * i.exchange_rate)
    duty = money(customs_value * i.duty_rate_pct / hundred)
    excise = money((customs_value + duty) * i.excise_rate_pct / hundred)
    vat = money((customs_value + duty + excise) * i.vat_rate_pct / hundred)
    local = money(i.local_charges)
    total = customs_value + duty + excise + local + (Decimal(0) if i.vat_recoverable else vat)
    unit = money(total / i.quantity) if i.quantity else None
    return LandedCost(
        customs_value=customs_value,
        duty=duty,
        excise=excise,
        vat=vat,
        local_charges=local,
        landed_cost=money(total),
        unit_cost=unit,
        vat_included_in_cost=not i.vat_recoverable,
    )
