"""Stage 18: perpetual inventory accounting."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from .helpers import make_user, sign_in
from .test_finance import _setup
from .test_inventory_logistics import _basics

API = "/api/v1"
INV = f"{API}/inventory"
TODAY = date.today()


def _balance(c: Any, code: str) -> str:
    tb = c.get(f"{API}/finance/reports/trial-balance").json()
    row = next((r for r in tb["rows"] if r["code"] == code), None)
    return "0" if row is None else str(float(row["debit"]) - float(row["credit"]))


def test_movements_post_balanced_journals_once_enabled(app: FastAPI, db: Session) -> None:
    b = _setup(app, db)
    acc = dict(b.acc)
    for code, name, subtype in [
        ("1300", "Inventory", "inventory"),
        ("2200", "Goods received not invoiced", "other_liability"),
        ("5100", "Cost of sales", "cost_of_sales"),
        ("5200", "Stock adjustments", "expense"),
    ]:
        r = b.fin.post(
            f"{API}/finance/accounts",
            json={"code": code, "name": f"TEST {name}", "subtype": subtype},
        )
        assert r.status_code == 201, r.text
        acc[code] = r.json()["id"]
    stock = sign_in(app, make_user(db, "logistics"))
    product, llw, bt = _basics(stock)

    def adjust(qty: str, kind: str, cost: str | None = None, on: date = TODAY) -> Any:
        body = {
            "product_id": product,
            "warehouse_id": llw,
            "quantity": qty,
            "movement_date": str(on),
            "kind": kind,
            "reason": "TEST movement",
        }
        if cost:
            body["unit_cost"] = cost
        return stock.post(f"{INV}/adjustments", json=body)

    # Before posting is switched on: stock moves, the ledger does not.
    assert adjust("10", "opening", "100").status_code == 201
    rec = b.fin.get(f"{API}/finance/reports/stock-reconciliation").json()
    assert rec["posting_enabled"] is False and rec["stock_value"] == "1000.00"
    assert rec["ledger_balance"] is None and rec["movements_not_posted"] == 1
    assert rec["reconciled"] is False

    mapping = {
        "inventory_account_id": acc["1300"],
        "grni_account_id": acc["2200"],
        "cogs_account_id": acc["5100"],
        "adjustment_account_id": acc["5200"],
        "opening_account_id": acc["3000"],
    }
    url = f"{API}/finance/stock-posting"
    assert b.fin.put(url, json=mapping).status_code == 403  # Director only
    # Cannot be switched on without the reviewing accountant on record.
    assert b.director.put(url, json={**mapping, "enabled": True}).status_code == 422
    wrong = {**mapping, "inventory_account_id": acc["5000"]}
    assert b.director.put(url, json=wrong).status_code == 422  # not an asset account
    on = {
        **mapping,
        "enabled": True,
        "reviewed_by_name": "TEST Accountant",
        "reviewed_on": str(TODAY),
    }
    r = b.director.put(url, json=on)
    assert r.status_code == 200, r.text
    assert r.json()["valuation_method"] == "weighted_average"

    assert adjust("10", "adjustment", "200").status_code == 201  # found stock: +2,000
    assert adjust("-4", "damage").status_code == 201  # 4 x average 150 = 600 out
    assert adjust("2", "return_in").status_code == 201  # 2 x 150 back in
    assert adjust("3", "damage").status_code == 422
    transfer = {
        "product_id": product,
        "from_warehouse_id": llw,
        "to_warehouse_id": bt,
        "quantity": "5",
        "movement_date": str(TODAY),
    }
    assert stock.post(f"{INV}/transfers", json=transfer).status_code == 201

    journals = db.execute(
        text(
            "SELECT e.description, sum(l.debit), sum(l.credit) FROM fin_journal_entries e "
            "JOIN fin_journal_lines l ON l.entry_id = e.id WHERE e.source_type = 'stock' "
            "GROUP BY e.id, e.description ORDER BY e.number"
        )
    ).all()
    assert len(journals) == 3  # the transfer posts nothing
    assert all(d == c for _, d, c in journals)
    assert _balance(b.fin, "1300") == "1700.0"  # +2000 - 600 + 300
    assert _balance(b.fin, "5200") == "-1400.0"  # gain 2000, damage 600
    assert _balance(b.fin, "5100") == "-300.0"  # return reduces cost of sales

    rec = b.fin.get(f"{API}/finance/reports/stock-reconciliation").json()
    # Stock ledger 2,700 = opening 1,000 (before switch-on, not posted) + 1,700 posted.
    assert rec["stock_value"] == "2700.00" and rec["ledger_balance"] == "1700.00"
    assert rec["difference"] == "1000.00" and rec["movements_not_posted"] == 1
    assert rec["reconciled"] is False

    # A movement dated in a closed or missing period is refused, so stock and ledger stay in step.
    before = db.execute(text("SELECT count(*) FROM inv_stock_movements")).scalar()
    far = adjust("1", "adjustment", "50", on=TODAY + timedelta(days=800))
    assert far.status_code == 422
    db.expire_all()
    assert db.execute(text("SELECT count(*) FROM inv_stock_movements")).scalar() == before
    assert stock.get(f"{API}/finance/stock-posting").status_code == 403
