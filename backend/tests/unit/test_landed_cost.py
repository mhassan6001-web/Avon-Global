from decimal import Decimal

import pytest

from app.modules.procurement.landed_cost import LandedCostInput, calculate


def _input(**kw):  # type: ignore[no-untyped-def]
    base = {
        "goods_value": Decimal("1000"),
        "freight": Decimal("150"),
        "insurance": Decimal("10"),
        "exchange_rate": Decimal("1750"),
        "duty_rate_pct": Decimal("10"),
        "excise_rate_pct": Decimal("0"),
        "vat_rate_pct": Decimal("16.5"),
        "vat_recoverable": True,
        "local_charges": Decimal("250000"),
        "quantity": Decimal("20"),
    }
    base.update(kw)
    return LandedCostInput(**base)


def test_worked_example() -> None:
    r = calculate(_input())
    assert r.customs_value == Decimal("2030000.00")  # (1000+150+10) * 1750
    assert r.duty == Decimal("203000.00")
    assert r.excise == Decimal("0.00")
    assert r.vat == Decimal("368445.00")  # 16.5 % of 2,233,000 (rate is an input, not a constant)
    assert r.landed_cost == Decimal("2483000.00")  # VAT recoverable: excluded
    assert r.unit_cost == Decimal("124150.00")


def test_non_recoverable_vat_and_excise_compound() -> None:
    r = calculate(_input(excise_rate_pct=Decimal("5"), vat_recoverable=False, quantity=None))
    assert r.excise == Decimal("111650.00")  # 5 % of (CIF + duty)
    assert r.vat == Decimal("386867.25")
    assert r.landed_cost == Decimal("2981517.25")
    assert r.unit_cost is None and r.vat_included_in_cost


@pytest.mark.parametrize(
    "bad",
    [
        {"exchange_rate": Decimal("0")},
        {"goods_value": Decimal("-1")},
        {"duty_rate_pct": Decimal("-5")},
        {"quantity": Decimal("0")},
    ],
)
def test_rejects_invalid_inputs(bad: dict) -> None:  # type: ignore[type-arg]
    with pytest.raises(ValueError):
        calculate(_input(**bad))
