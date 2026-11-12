"""Stage 7: double-entry finance. Balanced, numbered, immutable, approved by someone else."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from .helpers import make_user, sign_in

API = "/api/v1/finance"
TODAY = date.today()
YEAR_START = date(TODAY.year, 1, 1)
YEAR_END = date(TODAY.year, 12, 31)
# A test rate only. The application has no built-in tax rate.
TEST_VAT = "16.5"


@dataclass
class Books:
    fin: TestClient
    director: TestClient
    acc: dict[str, str]
    vat_out: str
    vat_in: str
    customer: str
    supplier: str


def _setup(app: FastAPI, db: Session) -> Books:
    fin = sign_in(app, make_user(db, "finance"))
    director = sign_in(app, make_user(db, "director"), step_up=True)
    acc = {}
    for code, name, subtype, currency in [
        ("1000", "Main bank MWK", "bank", "MWK"),
        ("1010", "USD account", "bank", "USD"),
        ("1100", "Debtors control", "receivable", None),
        ("2000", "Creditors control", "payable", None),
        ("2100", "VAT output", "tax", None),
        ("2110", "VAT input", "tax", None),
        ("3000", "Owner's capital", "equity", None),
        ("4000", "Sales", "revenue", None),
        ("4010", "Services", "revenue", None),
        ("5000", "Office expenses", "expense", None),
        ("7000", "Exchange differences", "fx_gain_loss", None),
    ]:
        body = {"code": code, "name": f"TEST {name}", "subtype": subtype}
        if currency:
            body["currency"] = currency
        r = fin.post(f"{API}/accounts", json=body)
        assert r.status_code == 201, r.text
        acc[code] = r.json()["id"]
    assert (
        fin.put(
            f"{API}/settings",
            json={
                "receivable_account_id": acc["1100"],
                "payable_account_id": acc["2000"],
                "fx_gain_loss_account_id": acc["7000"],
            },
        ).status_code
        == 200
    )
    period = {"name": f"FY{TODAY.year}", "start_date": str(YEAR_START), "end_date": str(YEAR_END)}
    assert fin.post(f"{API}/periods", json=period).status_code == 201
    taxes = []
    for code, kind, account in (("VAT-OUT", "output", "2100"), ("VAT-IN", "input", "2110")):
        r = fin.post(
            f"{API}/tax-codes",
            json={
                "code": code,
                "name": f"TEST {code}",
                "kind": kind,
                "rate_pct": TEST_VAT,
                "account_id": acc[account],
                "effective_from": str(YEAR_START),
            },
        )
        assert r.status_code == 201, r.text
        taxes.append(r.json()["id"])
    customer = director.post("/api/v1/crm/customers", json={"name": "TEST Finance Customer"})
    supplier = director.post(
        "/api/v1/procurement/suppliers", json={"name": "TEST Finance Supplier"}
    )
    return Books(
        fin, director, acc, taxes[0], taxes[1], customer.json()["id"], supplier.json()["id"]
    )


def _invoice(b: Books, lines: list[dict], currency: str = "MWK", **extra) -> dict:  # type: ignore[type-arg]
    r = b.fin.post(
        f"{API}/invoices",
        json={
            "customer_id": b.customer,
            "currency": currency,
            "issue_date": str(TODAY),
            "due_date": str(TODAY + timedelta(days=30)),
            "lines": lines,
            **extra,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _tb(b: Books) -> dict:  # type: ignore[type-arg]
    tb = b.fin.get(f"{API}/reports/trial-balance").json()
    assert tb["balanced"] is True, tb
    return {row["code"]: row for row in tb["rows"]}


def test_issue_posts_balanced_numbered_journal_that_cannot_change(
    app: FastAPI, db: Session
) -> None:
    b = _setup(app, db)
    inv = _invoice(
        b,
        [
            {
                "description": "Desks",
                "quantity": "10",
                "unit_price": "1000",
                "account_id": b.acc["4000"],
                "tax_code_id": b.vat_out,
            },
            {
                "description": "Delivery",
                "quantity": "1",
                "unit_price": "500",
                "account_id": b.acc["4010"],
            },
        ],
    )
    assert (inv["subtotal"], inv["tax_total"], inv["total"]) == ("10500.00", "1650.00", "12150.00")
    assert inv["number"] is None and inv["status"] == "draft"

    r = b.fin.post(f"{API}/invoices/{inv['id']}/issue", json={})
    assert r.status_code == 200, r.text
    issued = r.json()
    assert issued["number"] == f"INV-{TODAY.year}-00001" and issued["status"] == "issued"
    assert b.fin.post(f"{API}/invoices/{inv['id']}/issue", json={}).status_code == 409

    journal = b.fin.get(f"{API}/journals/{issued['journal_id']}").json()
    assert journal["status"] == "posted" and journal["number"].startswith(f"JE-{TODAY.year}-")
    by_code = {(line["account_code"], line["debit"], line["credit"]) for line in journal["lines"]}
    assert by_code == {
        ("1100", "12150.00", "0.00"),
        ("4000", "0.00", "10000.00"),
        ("4010", "0.00", "500.00"),
        ("2100", "0.00", "1650.00"),
    }
    tb = _tb(b)
    assert tb["1100"]["balance"] == "12150.00" and tb["4000"]["balance"] == "10000.00"

    # The database itself refuses edits to posted records.
    for sql in (
        "UPDATE fin_journal_lines SET debit = debit + 1 WHERE entry_id = :e AND debit > 0",
        "DELETE FROM fin_journal_lines WHERE entry_id = :e",
        "UPDATE fin_journal_entries SET description = 'changed' WHERE id = :e",
        "DELETE FROM fin_journal_entries WHERE id = :e",
    ):
        with pytest.raises(DBAPIError):
            db.execute(text(sql), {"e": issued["journal_id"]})
        db.rollback()
    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE fin_invoices SET total = 1 WHERE id = :i"), {"i": inv["id"]})
    db.rollback()

    # Numbers are gap-free and sequential.
    for _ in range(2):
        nxt = _invoice(
            b,
            [
                {
                    "description": "Item",
                    "quantity": "1",
                    "unit_price": "10",
                    "account_id": b.acc["4000"],
                }
            ],
        )
        b.fin.post(f"{API}/invoices/{nxt['id']}/issue", json={})
    numbers = sorted(i["number"] for i in b.fin.get(f"{API}/invoices").json())
    assert numbers == [f"INV-{TODAY.year}-0000{n}" for n in (1, 2, 3)]


def test_receipts_allocate_and_settle(app: FastAPI, db: Session) -> None:
    b = _setup(app, db)
    inv = _invoice(
        b,
        [
            {
                "description": "Chairs",
                "quantity": "4",
                "unit_price": "2500",
                "account_id": b.acc["4000"],
            }
        ],
    )
    b.fin.post(f"{API}/invoices/{inv['id']}/issue", json={})

    def receipt(amount: str, alloc: str | None = None):  # type: ignore[no-untyped-def]
        return b.fin.post(
            f"{API}/receipts",
            json={
                "customer_id": b.customer,
                "receipt_date": str(TODAY),
                "currency": "MWK",
                "amount": amount,
                "bank_account_id": b.acc["1000"],
                "method": "bank_transfer",
                "allocations": [{"invoice_id": inv["id"], "amount": alloc or amount}],
            },
        )

    assert receipt("20000").status_code == 422  # more than owed
    assert receipt("4000", "3000").status_code == 422  # not fully allocated
    r = receipt("4000")
    assert r.status_code == 201, r.text
    assert r.json()["number"] == f"RCT-{TODAY.year}-00001"
    assert b.fin.get(f"{API}/invoices/{inv['id']}").json()["status"] == "partially_paid"
    receipt("6000")
    final = b.fin.get(f"{API}/invoices/{inv['id']}").json()
    assert (final["status"], final["outstanding"]) == ("paid", "0.00")
    tb = _tb(b)
    assert tb["1000"]["balance"] == "10000.00" and "1100" in tb and tb["1100"]["balance"] == "0.00"

    # Receipts are append-only in the database.
    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE fin_receipts SET amount = 1"))
    db.rollback()

    overview = b.fin.get(f"{API}/overview").json()
    assert overview["has_records"] is True
    assert overview["invoiced_this_month"] == "10000.00"
    assert overview["collected_this_month"] == "10000.00"
    assert overview["cash_position"] == "10000.00"


def test_foreign_currency_receipt_books_exchange_difference(app: FastAPI, db: Session) -> None:
    b = _setup(app, db)
    inv = _invoice(
        b,
        [
            {
                "description": "Laptop",
                "quantity": "1",
                "unit_price": "100",
                "account_id": b.acc["4000"],
            }
        ],
        currency="USD",
    )
    missing = b.fin.post(f"{API}/invoices/{inv['id']}/issue", json={})
    assert missing.status_code == 422 and "exchange rate" in missing.json()["error"]["message"]

    rate = {"currency": "USD", "rate_date": str(TODAY), "rate": "1700", "source": "TEST rate"}
    assert b.fin.post(f"{API}/exchange-rates", json=rate).status_code == 201
    assert b.fin.post(f"{API}/exchange-rates", json=rate).status_code == 409  # history, not edits
    issued = b.fin.post(f"{API}/invoices/{inv['id']}/issue", json={}).json()
    assert issued["fx_rate"] == "1700.000000"

    r = b.fin.post(
        f"{API}/receipts",
        json={
            "customer_id": b.customer,
            "receipt_date": str(TODAY),
            "currency": "USD",
            "amount": "100",
            "fx_rate": "1750",
            "bank_account_id": b.acc["1010"],
            "method": "bank_transfer",
            "allocations": [{"invoice_id": inv["id"], "amount": "100"}],
        },
    )
    assert r.status_code == 201, r.text
    tb = _tb(b)
    assert tb["1010"]["balance"] == "175000.00"
    assert tb["1100"]["balance"] == "0.00"
    assert tb["7000"]["balance"] == "5000.00"  # realised gain
    pl = b.fin.get(
        f"{API}/reports/profit-and-loss",
        params={"date_from": str(YEAR_START), "date_to": str(YEAR_END)},
    ).json()
    assert pl["total_income"] == "175000.00" and pl["net_profit"] == "175000.00"
    cash = b.fin.get(
        f"{API}/reports/cashbook",
        params={
            "account_id": b.acc["1010"],
            "date_from": str(YEAR_START),
            "date_to": str(YEAR_END),
        },
    ).json()
    assert cash["currency"] == "USD" and cash["closing_balance"] == "100.00"


def test_credit_note_needs_a_different_approver(app: FastAPI, db: Session) -> None:
    b = _setup(app, db)
    inv = _invoice(
        b,
        [
            {
                "description": "Service",
                "quantity": "1",
                "unit_price": "10000",
                "account_id": b.acc["4000"],
                "tax_code_id": b.vat_out,
            }
        ],
    )
    b.fin.post(f"{API}/invoices/{inv['id']}/issue", json={})
    body = {
        "invoice_id": inv["id"],
        "credit_date": str(TODAY),
        "amount": "2330",
        "reason": "Partial return",
    }
    assert b.fin.post(f"{API}/credit-notes", json={**body, "amount": "99999"}).status_code == 422
    r = b.fin.post(f"{API}/credit-notes", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "awaiting_approval" and r.json()["number"] is None

    approval = b.director.get("/api/v1/approvals").json()[0]
    assert (
        b.fin.post(f"/api/v1/approvals/{approval['id']}/decide", json={"approve": True}).status_code
        == 403
    )
    d = b.director.post(f"/api/v1/approvals/{approval['id']}/decide", json={"approve": True})
    assert d.status_code == 200, d.text
    note = b.fin.get(f"{API}/credit-notes").json()[0]
    assert note["status"] == "posted" and note["number"] == f"CN-{TODAY.year}-00001"
    invoice = b.fin.get(f"{API}/invoices/{inv['id']}").json()
    assert invoice["amount_credited"] == "2330.00" and invoice["outstanding"] == "9320.00"
    tb = _tb(b)
    assert tb["4000"]["balance"] == "8000.00"  # 10000 - 2000 net
    assert tb["2100"]["balance"] == "1320.00"  # 1650 - 330 tax


def test_bill_and_payment_dual_control(app: FastAPI, db: Session) -> None:
    b = _setup(app, db)
    r = b.fin.post(
        f"{API}/bills",
        json={
            "supplier_id": b.supplier,
            "supplier_invoice_ref": "SUP-INV-77",
            "bill_date": str(TODAY),
            "due_date": str(TODAY + timedelta(days=14)),
            "lines": [
                {
                    "description": "Paper",
                    "quantity": "10",
                    "unit_price": "1000",
                    "account_id": b.acc["5000"],
                    "tax_code_id": b.vat_in,
                }
            ],
        },
    )
    assert r.status_code == 201, r.text
    bill = r.json()
    dup = {
        **{k: bill[k] for k in ("supplier_id", "supplier_invoice_ref")},
        "bill_date": str(TODAY),
        "due_date": str(TODAY),
        "lines": [
            {"description": "xx", "quantity": "1", "unit_price": "1", "account_id": b.acc["5000"]}
        ],
    }
    assert b.fin.post(f"{API}/bills", json=dup).status_code == 409
    posted = b.fin.post(f"{API}/bills/{bill['id']}/post", json={}).json()
    assert posted["number"] == f"BILL-{TODAY.year}-00001" and posted["total"] == "11650.00"

    pay = {
        "bill_id": bill["id"],
        "payment_date": str(TODAY),
        "amount": "11650",
        "bank_account_id": b.acc["1000"],
        "method": "bank_transfer",
    }
    no_bank = b.fin.post(f"{API}/payments", json=pay)
    assert no_bank.status_code == 409 and "bank account" in no_bank.json()["error"]["message"]
    r = b.fin.post(f"{API}/payments", json={**pay, "method": "cheque", "reference": "CHQ 0001"})
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "awaiting_approval" and r.json()["number"] is None
    assert b.fin.post(f"{API}/payments", json={**pay, "method": "cheque"}).status_code == 422

    aid = b.director.get("/api/v1/approvals").json()[0]["id"]
    assert (
        b.director.post(f"/api/v1/approvals/{aid}/decide", json={"approve": True}).status_code
        == 200
    )
    payment = b.fin.get(f"{API}/payments").json()[0]
    assert payment["status"] == "posted" and payment["number"] == f"PAY-{TODAY.year}-00001"
    assert b.fin.get(f"{API}/bills").json()[0]["status"] == "paid"
    tb = _tb(b)
    assert tb["2000"]["balance"] == "0.00" and tb["1000"]["balance"] == "-11650.00"

    # The Director cannot approve a payment the Director prepared.
    bill2 = b.fin.post(
        f"{API}/bills",
        json={
            **dup,
            "supplier_invoice_ref": "SUP-INV-78",
            "lines": [
                {
                    "description": "Ink",
                    "quantity": "1",
                    "unit_price": "100",
                    "account_id": b.acc["5000"],
                }
            ],
        },
    ).json()
    b.fin.post(f"{API}/bills/{bill2['id']}/post", json={})
    b.director.post(
        f"{API}/payments", json={**pay, "bill_id": bill2["id"], "amount": "100", "method": "cash"}
    )
    own = b.director.get("/api/v1/approvals", params={"view": "mine"}).json()[0]
    blocked = b.director.post(f"/api/v1/approvals/{own['id']}/decide", json={"approve": True})
    assert (
        blocked.status_code == 403 and blocked.json()["error"]["code"] == "self_approval_forbidden"
    )


def test_manual_journal_reversal_period_close_and_reports(app: FastAPI, db: Session) -> None:
    b = _setup(app, db)
    unbalanced = {
        "entry_date": str(TODAY),
        "description": "Bad",
        "lines": [
            {"account_id": b.acc["5000"], "debit": "300"},
            {"account_id": b.acc["1000"], "credit": "200"},
        ],
    }
    assert b.fin.post(f"{API}/journals", json=unbalanced).status_code == 422
    capital = {
        "entry_date": str(TODAY),
        "description": "Capital introduced",
        "lines": [
            {"account_id": b.acc["1000"], "debit": "50000"},
            {"account_id": b.acc["3000"], "credit": "50000"},
        ],
    }
    r = b.fin.post(f"{API}/journals", json=capital)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "awaiting_approval" and r.json()["number"] is None
    assert b.fin.get(f"{API}/reports/trial-balance").json()["rows"] == []  # nothing posted yet

    aid = b.director.get("/api/v1/approvals").json()[0]["id"]
    b.director.post(f"/api/v1/approvals/{aid}/decide", json={"approve": True})
    entry = b.fin.get(f"{API}/journals/{r.json()['id']}").json()
    assert entry["status"] == "posted"

    expense = {
        "entry_date": str(TODAY),
        "description": "Petty expense",
        "lines": [
            {"account_id": b.acc["5000"], "debit": "300"},
            {"account_id": b.acc["1000"], "credit": "300"},
        ],
    }
    e2 = b.fin.post(f"{API}/journals", json=expense).json()
    aid = b.director.get("/api/v1/approvals").json()[0]["id"]
    b.director.post(f"/api/v1/approvals/{aid}/decide", json={"approve": True})
    rev = b.fin.post(
        f"{API}/journals/{e2['id']}/reverse",
        json={"entry_date": str(TODAY), "reason": "Wrong account"},
    )
    assert rev.status_code == 200
    aid = b.director.get("/api/v1/approvals").json()[0]["id"]
    b.director.post(f"/api/v1/approvals/{aid}/decide", json={"approve": True})
    original = b.fin.get(f"{API}/journals/{e2['id']}").json()
    assert original["status"] == "reversed" and original["reversed_by_id"]
    tb = _tb(b)
    assert tb["5000"]["balance"] == "0.00" and tb["1000"]["balance"] == "50000.00"

    sheet = b.fin.get(f"{API}/reports/balance-sheet").json()
    assert sheet["balanced"] is True and sheet["total_assets"] == "50000.00"

    # Reconciliation: match a statement line to the capital receipt.
    line = b.fin.post(
        f"{API}/bank-statements",
        json={
            "bank_account_id": b.acc["1000"],
            "statement_date": str(TODAY),
            "description": "Deposit",
            "amount": "50000",
        },
    ).json()
    book = b.fin.get(
        f"{API}/reports/cashbook",
        params={
            "account_id": b.acc["1000"],
            "date_from": str(YEAR_START),
            "date_to": str(YEAR_END),
        },
    ).json()
    deposit = next(row for row in book["rows"] if row["money_in"] == "50000.00")
    wrong = next(row for row in book["rows"] if row["money_in"] == "300.00")
    assert (
        b.fin.post(
            f"{API}/bank-statements/{line['id']}/match", json={"journal_line_id": wrong["line_id"]}
        ).status_code
        == 422
    )
    assert (
        b.fin.post(
            f"{API}/bank-statements/{line['id']}/match",
            json={"journal_line_id": deposit["line_id"]},
        ).status_code
        == 200
    )

    # Closing the period: Director only, then nothing posts into it.
    periods = b.fin.get(f"{API}/periods").json()
    assert b.fin.post(f"{API}/periods/{periods[0]['id']}/close").status_code == 403
    assert b.director.post(f"{API}/periods/{periods[0]['id']}/close").status_code == 200
    inv = _invoice(
        b,
        [{"description": "Late", "quantity": "1", "unit_price": "10", "account_id": b.acc["4000"]}],
    )
    assert b.fin.post(f"{API}/invoices/{inv['id']}/issue", json={}).status_code == 409


def test_finance_is_restricted_to_finance_and_director(app: FastAPI, db: Session) -> None:
    for role in ("business_development", "procurement", "logistics", "hr_admin"):
        other = sign_in(app, make_user(db, role))
        for path in ("/invoices", "/reports/trial-balance", "/overview", "/accounts"):
            assert other.get(f"{API}{path}").status_code == 403, (role, path)
    fin = sign_in(app, make_user(db, "finance"))
    assert fin.get(f"{API}/overview").json()["has_records"] is False
    assert fin.get(f"{API}/settings").json()["missing"]


def test_decimal_amounts_are_exact(app: FastAPI, db: Session) -> None:
    b = _setup(app, db)
    inv = _invoice(
        b,
        [
            {
                "description": "Thirds",
                "quantity": "3",
                "unit_price": "0.3333",
                "account_id": b.acc["4000"],
                "tax_code_id": b.vat_out,
            }
        ],
    )
    assert Decimal(inv["subtotal"]) == Decimal("1.00")  # 0.9999 rounded half-up
    assert Decimal(inv["tax_total"]) == Decimal("0.17")
