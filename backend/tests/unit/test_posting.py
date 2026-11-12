"""Pure checks of the journal balancing rules (no database)."""

import uuid
from decimal import Decimal

import pytest

pytest.importorskip("sqlalchemy", reason="the posting module imports SQLAlchemy")

from app.modules.finance.posting import (
    FinanceRuleError,
    Line,
    prepare_lines,
)

A, B, C = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def test_balanced_functional_entry_passes_unchanged() -> None:
    lines = [
        Line(A, "debit", Decimal("100"), "MWK", Decimal(1)),
        Line(B, "credit", Decimal("100"), "MWK", Decimal(1)),
    ]
    assert [f for _, f in prepare_lines(lines)] == [Decimal("100.00"), Decimal("100.00")]


def test_unbalanced_functional_entry_is_refused() -> None:
    with pytest.raises(FinanceRuleError):
        prepare_lines(
            [
                Line(A, "debit", Decimal("100"), "MWK", Decimal(1)),
                Line(B, "credit", Decimal("99.99"), "MWK", Decimal(1)),
            ]
        )


def test_foreign_conversion_rounding_is_absorbed_up_to_five_cents() -> None:
    rate = Decimal("1.005")  # 10.00 → 10.05, but 3.33 + 3.33 + 3.34 → 3.35 + 3.35 + 3.36
    lines = [
        Line(A, "debit", Decimal("10.00"), "USD", rate),
        Line(B, "credit", Decimal("3.33"), "USD", rate),
        Line(C, "credit", Decimal("3.33"), "USD", rate),
        Line(C, "credit", Decimal("3.34"), "USD", rate),
    ]
    out = prepare_lines(lines)
    debit = sum(f for line, f in out if line.side == "debit")
    credit = sum(f for line, f in out if line.side == "credit")
    assert debit == credit == Decimal("10.06")


def test_large_difference_is_never_absorbed() -> None:
    with pytest.raises(FinanceRuleError):
        prepare_lines(
            [
                Line(A, "debit", Decimal("10"), "USD", Decimal("1700")),
                Line(B, "credit", Decimal("9"), "USD", Decimal("1700")),
            ]
        )


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-5")])
def test_non_positive_lines_are_refused(amount: Decimal) -> None:
    with pytest.raises(FinanceRuleError):
        prepare_lines(
            [
                Line(A, "debit", amount, "MWK", Decimal(1)),
                Line(B, "credit", amount, "MWK", Decimal(1)),
            ]
        )


def test_single_line_is_refused() -> None:
    with pytest.raises(FinanceRuleError):
        prepare_lines([Line(A, "debit", Decimal("1"), "MWK", Decimal(1))])
