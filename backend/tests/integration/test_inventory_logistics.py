"""Stage 8: stock ledger (weighted average), goods received against orders,
shipments, delivery notes and proof of delivery."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from .helpers import make_user, sign_in

INV = "/api/v1/inventory"
LGX = "/api/v1/logistics"
TODAY = str(date.today())


def _basics(c: TestClient) -> tuple[str, str, str]:
    p = c.post(
        f"{INV}/products",
        json={"sku": "TEST-CHAIR", "name": "TEST Office chair", "reorder_level": "5"},
    )
    assert p.status_code == 201, p.text
    w1 = c.post(f"{INV}/warehouses", json={"code": "LLW", "name": "TEST Lilongwe store"}).json()
    w2 = c.post(f"{INV}/warehouses", json={"code": "BT", "name": "TEST Blantyre store"}).json()
    return p.json()["id"], w1["id"], w2["id"]


def test_weighted_average_cost_and_no_negative_stock(app: FastAPI, db: Session) -> None:
    c = sign_in(app, make_user(db, "logistics"))
    product, llw, bt = _basics(c)
    assert c.post(f"{INV}/products", json={"sku": "TEST-CHAIR", "name": "Dup"}).status_code == 409
    assert c.post(f"{INV}/products", json={"sku": "bad sku", "name": "Bad"}).status_code == 422

    def adjust(qty: str, cost: str | None = None, kind: str = "adjustment", reason: str = "Count"):  # type: ignore[no-untyped-def]
        body = {
            "product_id": product,
            "warehouse_id": llw,
            "quantity": qty,
            "movement_date": TODAY,
            "kind": kind,
            "reason": reason,
        }
        if cost:
            body["unit_cost"] = cost
        return c.post(f"{INV}/adjustments", json=body)

    assert adjust("10", kind="opening").status_code == 422  # opening needs a cost
    assert adjust("10", "100", kind="opening").status_code == 201
    assert adjust("10", "200").status_code == 201
    level = c.get(f"{INV}/levels", params={"product_id": product}).json()[0]
    assert (level["quantity"], level["average_cost"], level["value"]) == (
        "20.000",
        "150.0000",
        "3000.00",
    )

    assert adjust("-25", reason="Damaged").status_code == 409  # cannot go negative
    out = adjust("-5", reason="Damaged in transit")
    assert out.status_code == 201 and out.json()["unit_cost"] == "150.0000"

    r = c.post(
        f"{INV}/transfers",
        json={
            "product_id": product,
            "from_warehouse_id": llw,
            "to_warehouse_id": bt,
            "quantity": "5",
            "movement_date": TODAY,
        },
    )
    assert r.status_code == 200, r.text
    levels = {lv["warehouse_code"]: lv for lv in r.json()}
    assert levels["LLW"]["quantity"] == "10.000" and levels["BT"]["average_cost"] == "150.0000"

    products = c.get(f"{INV}/products").json()
    assert products[0]["on_hand"] == "15.000" and products[0]["below_reorder"] is False
    adjust("-10", reason="Sold off")
    assert c.get(f"{INV}/products", params={"below_reorder": True}).json()[0]["sku"] == "TEST-CHAIR"
    summary = c.get(f"{INV}/summary").json()
    assert summary["below_reorder"] == 1 and summary["stock_value"] == "750.00"

    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE inv_stock_movements SET quantity = 999"))
    db.rollback()


def _approved_order(app: FastAPI, db: Session) -> dict:  # type: ignore[type-arg]
    prc = sign_in(app, make_user(db, "procurement"))
    director = sign_in(app, make_user(db, "director"), step_up=True)
    s = prc.post("/api/v1/procurement/suppliers", json={"name": "TEST Furniture Ltd"}).json()
    prc.post(
        f"/api/v1/procurement/suppliers/{s['id']}/verification",
        json={"status": "verified", "note": "Checked"},
    )
    pr = prc.post(
        "/api/v1/procurement/requests",
        json={
            "title": "Chairs",
            "lines": [
                {"description": "Office chair", "quantity": "8"},
                {"description": "Desk", "quantity": "2"},
            ],
        },
    ).json()
    rid = pr["request"]["id"]
    lines = [
        {"request_line_id": line["id"], "unit_price": p}
        for line, p in zip(pr["lines"], ("120", "500"), strict=True)
    ]
    q = prc.post(
        f"/api/v1/procurement/requests/{rid}/quotes",
        json={"supplier_id": s["id"], "currency": "MWK", "lines": lines},
    ).json()
    prc.post(f"/api/v1/procurement/requests/{rid}/submit", json={"quote_id": q["quotes"][0]["id"]})
    aid = director.get("/api/v1/approvals").json()[0]["id"]
    director.post(f"/api/v1/approvals/{aid}/decide", json={"approve": True})
    return prc.post(f"/api/v1/procurement/requests/{rid}/order", json={}).json()


def test_goods_received_against_purchase_order(app: FastAPI, db: Session) -> None:
    order = _approved_order(app, db)
    c = sign_in(app, make_user(db, "logistics"))
    product, llw, _ = _basics(c)
    desk = c.post(f"{INV}/products", json={"sku": "TEST-DESK", "name": "TEST Desk"}).json()["id"]
    open_orders = c.get(f"{INV}/open-orders").json()
    assert open_orders[0]["reference"] == order["reference"]
    assert "unit_price" not in str(open_orders)  # Logistics sees quantities, not prices

    body = {
        "purchase_order_id": order["id"],
        "warehouse_id": llw,
        "received_on": TODAY,
        "delivery_note_ref": "SUPPLIER-DN-1",
        "lines": [{"line_no": 1, "product_id": product, "quantity": "5"}],
    }
    r = c.post(f"{INV}/goods-receipts", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["number"] == "GRN-00001" and r.json()["order_status"] == "partially_received"
    level = c.get(f"{INV}/levels", params={"product_id": product}).json()[0]
    assert level["quantity"] == "5.000" and level["average_cost"] == "120.0000"

    over = {**body, "lines": [{"line_no": 1, "product_id": product, "quantity": "4"}]}
    assert c.post(f"{INV}/goods-receipts", json=over).status_code == 409
    rest = {
        **body,
        "lines": [
            {"line_no": 1, "product_id": product, "quantity": "3"},
            {"line_no": 2, "product_id": desk, "quantity": "2"},
        ],
    }
    assert c.post(f"{INV}/goods-receipts", json=rest).json()["order_status"] == "received"
    assert c.post(f"{INV}/goods-receipts", json=rest).status_code == 409  # order closed
    # A received order cannot be cancelled.
    prc = sign_in(app, make_user(db, "procurement"))
    assert (
        prc.post(
            f"/api/v1/procurement/orders/{order['id']}/cancel", json={"reason": "x" * 5}
        ).status_code
        == 409
    )


def test_shipment_timeline_and_delivery_with_proof(app: FastAPI, db: Session) -> None:
    c = sign_in(app, make_user(db, "logistics"))
    director = sign_in(app, make_user(db, "director"))
    customer = director.post(
        "/api/v1/crm/customers", json={"name": "TEST Delivery Customer"}
    ).json()
    product, llw, _ = _basics(c)
    c.post(
        f"{INV}/adjustments",
        json={
            "product_id": product,
            "warehouse_id": llw,
            "quantity": "10",
            "unit_cost": "100",
            "movement_date": TODAY,
            "kind": "opening",
            "reason": "Opening count",
        },
    )

    bad = {
        "direction": "inbound",
        "mode": "sea",
        "origin": "Durban",
        "destination": "Lilongwe",
        "etd": TODAY,
        "eta": str(date.today() - timedelta(days=3)),
    }
    assert c.post(f"{LGX}/shipments", json=bad).status_code == 422
    ok = {
        **bad,
        "eta": str(date.today() + timedelta(days=20)),
        "freight_cost": "2500",
        "freight_currency": "USD",
    }
    s = c.post(f"{LGX}/shipments", json=ok)
    assert s.status_code == 201, s.text
    sid = s.json()["shipment"]["id"]
    assert s.json()["shipment"]["reference"] == "SHP-00001"
    c.post(f"{LGX}/shipments/{sid}/status", json={"status": "in_transit", "location": "Beira"})
    c.post(
        f"{LGX}/shipments/{sid}/status", json={"status": "at_customs", "location": "Mwanza border"}
    )
    assert c.post(f"{LGX}/shipments/{sid}/status", json={"status": "cleared"}).status_code == 422
    c.post(
        f"{LGX}/shipments/{sid}/status",
        json={"status": "cleared", "customs_entry_number": "TEST-CE-1"},
    )
    detail = c.post(f"{LGX}/shipments/{sid}/status", json={"status": "delivered"}).json()
    assert [e["status"] for e in detail["events"]] == [
        "planned",
        "in_transit",
        "at_customs",
        "cleared",
        "delivered",
    ]
    assert c.post(f"{LGX}/shipments/{sid}/status", json={"status": "in_transit"}).status_code == 409

    customers = c.get(f"{LGX}/customers").json()
    assert customers == [
        {"id": customer["id"], "name": "TEST Delivery Customer", "reference": customer["reference"]}
    ]
    dn = c.post(
        f"{LGX}/delivery-notes",
        json={
            "customer_id": customer["id"],
            "warehouse_id": llw,
            "delivery_address": "Area 3, Lilongwe",
            "lines": [{"product_id": product, "quantity": "4"}],
        },
    )
    assert dn.status_code == 201, dn.text
    note = dn.json()
    assert note["number"] == "DN-00001" and note["status"] == "draft"
    assert (
        c.post(
            f"{LGX}/delivery-notes/{note['id']}/proof", json={"received_by_name": "TEST"}
        ).status_code
        == 409
    )
    d = c.post(f"{LGX}/delivery-notes/{note['id']}/dispatch")
    assert d.json()["status"] == "dispatched"
    assert c.get(f"{INV}/levels", params={"product_id": product}).json()[0]["quantity"] == "6.000"
    assert (
        c.post(
            f"{LGX}/delivery-notes/{note['id']}/proof", json={"received_by_name": "x"}
        ).status_code
        == 422
    )
    p = c.post(
        f"{LGX}/delivery-notes/{note['id']}/proof",
        json={"received_by_name": "TEST Receiver Name", "note": "Signed paper copy filed"},
    )
    assert (
        p.json()["status"] == "delivered" and p.json()["received_by_name"] == "TEST Receiver Name"
    )

    big = c.post(
        f"{LGX}/delivery-notes",
        json={
            "customer_id": customer["id"],
            "warehouse_id": llw,
            "delivery_address": "Area 3, Lilongwe",
            "lines": [{"product_id": product, "quantity": "50"}],
        },
    ).json()
    assert c.post(f"{LGX}/delivery-notes/{big['id']}/dispatch").status_code == 409
    assert (
        c.post(
            f"{LGX}/delivery-notes/{big['id']}/cancel", json={"reason": "Not enough stock"}
        ).json()["status"]
        == "cancelled"
    )
    s = c.get(f"{LGX}/summary").json()
    assert s["has_records"] is True and s["awaiting_proof"] == 0


def test_inventory_and_logistics_permissions(app: FastAPI, db: Session) -> None:
    for role in ("business_development", "procurement", "finance", "hr_admin"):
        other = sign_in(app, make_user(db, role))
        assert other.get(f"{INV}/products").status_code == 403, role
        assert other.get(f"{LGX}/shipments").status_code == 403, role
