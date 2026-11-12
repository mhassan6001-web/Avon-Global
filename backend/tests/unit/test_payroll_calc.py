"""Payroll arithmetic with illustrative test components (not real statutory rates)."""

from decimal import Decimal as Dec

import pytest

from app.modules.hr.payroll_calc import Band, Component, Line, banded, calculate, validate_bands

# Illustrative bands for testing only. The application ships with none.
TEST_BANDS = (
    Band(Dec("0"), Dec("100000"), Dec("0")),
    Band(Dec("100000"), Dec("400000"), Dec("25")),
    Band(Dec("400000"), None, Dec("30")),
)


def test_progressive_bands() -> None:
    assert banded(Dec("90000"), TEST_BANDS) == Dec("0.00")
    assert banded(Dec("100000"), TEST_BANDS) == Dec("0.00")
    assert banded(Dec("250000"), TEST_BANDS) == Dec("37500.00")
    assert banded(Dec("500000"), TEST_BANDS) == Dec("105000.00")  # 75000 + 30000


def test_band_validation() -> None:
    validate_bands(TEST_BANDS)
    with pytest.raises(ValueError):
        validate_bands((Band(Dec("0"), Dec("100"), Dec("0")), Band(Dec("150"), None, Dec("10"))))
    with pytest.raises(ValueError):
        validate_bands((Band(Dec("0"), Dec("100"), Dec("120")),))


def test_payslip_order_and_totals() -> None:
    comps = [
        Component("HOUSE", "Housing allowance", "earning", "fixed", amount=Dec("50000")),
        Component(
            "TRANSPORT",
            "Transport (not taxable)",
            "earning",
            "fixed",
            amount=Dec("20000"),
            taxable=False,
        ),
        Component("TAX", "Income tax", "deduction", "bands", bands=TEST_BANDS, base="taxable"),
        Component(
            "PEN", "Pension (employee)", "deduction", "percent", rate_pct=Dec("5"), base="basic"
        ),
        Component(
            "PEN-ER", "Pension (employer)", "employer", "percent", rate_pct=Dec("10"), base="basic"
        ),
    ]
    slip = calculate(Dec("400000"), comps, [Line("COMM", "Commission", "earning", Dec("30000"))])
    assert slip.gross == Dec("500000.00")  # 400k + 30k + 50k + 20k
    assert slip.taxable == Dec("480000.00")  # transport excluded
    tax = next(line.amount for line in slip.lines if line.code == "TAX")
    assert tax == Dec("99000.00")  # 75000 + 30% of 80000
    assert slip.deductions == Dec("119000.00")  # tax + 5% of 400k
    assert slip.employer == Dec("40000.00")
    assert slip.net == Dec("381000.00")


def test_deductions_cannot_exceed_gross() -> None:
    with pytest.raises(ValueError):
        calculate(Dec("100"), [Component("LOAN", "Loan", "deduction", "fixed", amount=Dec("500"))])
