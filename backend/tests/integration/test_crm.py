"""Stage 4: CRM rules, search, audit and the Director dashboard."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.platform.audit.models import AuditEvent

from .helpers import make_user, sign_in

API = "/api/v1"


def _bd(app: FastAPI, db: Session):  # type: ignore[no-untyped-def]
    return sign_in(app, make_user(db, "business_development"))


def test_empty_state_is_distinct_from_zero(app: FastAPI, db: Session) -> None:
    c = _bd(app, db)
    s = c.get(f"{API}/crm/summary").json()
    assert s["has_records"] is False
    assert s["follow_ups_overdue"] == 0
    c.post(f"{API}/crm/customers", json={"name": "TEST Lilongwe Water Works"})
    s = c.get(f"{API}/crm/summary").json()
    assert s["has_records"] is True
    assert s["customers_by_status"] == {"prospect": 1}
    assert all(stage["count"] == 0 for stage in s["pipeline"])


def test_customer_lifecycle_search_and_audit(app: FastAPI, db: Session) -> None:
    c = _bd(app, db)
    r = c.post(
        f"{API}/crm/customers",
        json={
            "name": "TEST Blantyre Clinic",
            "kind": "ngo",
            "city": "Blantyre",
            "industry": "Health",
        },
    )
    assert r.status_code == 201, r.text
    first = r.json()
    assert first["reference"].startswith("CUS-") and first["status"] == "prospect"
    c.post(f"{API}/crm/customers", json={"name": "TEST Lusaka Builders", "country_code": "ZM"})

    # Duplicate names are refused (case-insensitive).
    dup = c.post(f"{API}/crm/customers", json={"name": "test blantyre clinic"})
    assert dup.status_code == 409

    # Search and filters.
    assert [x["name"] for x in c.get(f"{API}/crm/customers?q=health").json()["items"]] == [
        "TEST Blantyre Clinic"
    ]
    assert c.get(f"{API}/crm/customers?country=ZM").json()["total"] == 1
    page = c.get(f"{API}/crm/customers?size=1&page=2").json()
    assert page["total"] == 2 and len(page["items"]) == 1

    # Validation.
    assert c.post(f"{API}/crm/customers", json={"name": "x"}).status_code == 422
    assert (
        c.post(f"{API}/crm/customers", json={"name": "Ok Name", "email": "bad"}).status_code == 422
    )
    assert c.post(f"{API}/crm/customers", json={"name": "Ok Name", "extra": 1}).status_code == 422

    upd = c.patch(f"{API}/crm/customers/{first['id']}", json={"status": "active"})
    assert upd.json()["status"] == "active"

    # Archive hides from the default list; restore brings it back.
    c.post(f"{API}/crm/customers/{first['id']}/archive")
    assert c.get(f"{API}/crm/customers").json()["total"] == 1
    assert c.patch(f"{API}/crm/customers/{first['id']}", json={"city": "Zomba"}).status_code == 409
    c.post(f"{API}/crm/customers/{first['id']}/restore")
    assert c.get(f"{API}/crm/customers").json()["total"] == 2

    actions = set(
        db.execute(select(AuditEvent.action).where(AuditEvent.action.like("crm.%"))).scalars()
    )
    assert {
        "crm.customer.created",
        "crm.customer.updated",
        "crm.customer.archived",
        "crm.customer.restored",
    } <= actions


def test_contacts_single_primary(app: FastAPI, db: Session) -> None:
    c = _bd(app, db)
    cid = c.post(f"{API}/crm/customers", json={"name": "TEST Mzuzu Traders"}).json()["id"]
    a = c.post(
        f"{API}/crm/customers/{cid}/contacts", json={"name": "Contact A", "is_primary": True}
    )
    b = c.post(
        f"{API}/crm/customers/{cid}/contacts", json={"name": "Contact B", "is_primary": True}
    )
    assert a.status_code == b.status_code == 201
    contacts = c.get(f"{API}/crm/customers/{cid}").json()["contacts"]
    assert [x["name"] for x in contacts if x["is_primary"]] == ["Contact B"]
    assert c.delete(f"{API}/crm/contacts/{a.json()['id']}").status_code == 200
    assert len(c.get(f"{API}/crm/customers/{cid}").json()["contacts"]) == 1


def test_opportunity_rules(app: FastAPI, db: Session) -> None:
    c = _bd(app, db)
    cid = c.post(f"{API}/crm/customers", json={"name": "TEST Kasungu Farms"}).json()["id"]
    r = c.post(
        f"{API}/crm/opportunities",
        json={
            "customer_id": cid,
            "title": "Irrigation pumps",
            "division": "industrial_construction",
            "value_amount": "1500000.00",
            "currency": "MWK",
        },
    )
    assert r.status_code == 201, r.text
    opp = r.json()
    assert opp["reference"].startswith("OPP-") and opp["stage"] == "lead"

    # Negative values, unknown currencies and divisions are refused.
    for bad in ({"value_amount": "-1"}, {"currency": "EUR"}, {"division": "mining"}):
        body = {"customer_id": cid, "title": "Bad", "division": "technologies", **bad}
        assert c.post(f"{API}/crm/opportunities", json=body).status_code == 422, bad

    # Archiving a customer with an open opportunity is refused.
    assert c.post(f"{API}/crm/customers/{cid}/archive").status_code == 409

    # Lost needs a reason; won closes it at 100 %.
    oid = opp["id"]
    assert c.patch(f"{API}/crm/opportunities/{oid}", json={"stage": "lost"}).status_code == 422
    won = c.patch(f"{API}/crm/opportunities/{oid}", json={"stage": "won"}).json()
    assert won["closed_at"] and won["probability"] == 100

    summary = c.get(f"{API}/crm/summary").json()
    won_row = next(s for s in summary["pipeline"] if s["stage"] == "won")
    assert won_row["count"] == 1 and won_row["value_by_currency"] == {"MWK": "1500000.00"}

    # Reopening clears the close date.
    reopened = c.patch(f"{API}/crm/opportunities/{oid}", json={"stage": "negotiation"}).json()
    assert reopened["closed_at"] is None
    assert c.get(f"{API}/crm/opportunities?open_only=true").json()["total"] == 1


def test_follow_ups_and_activity_timeline(app: FastAPI, db: Session) -> None:
    c = _bd(app, db)
    cid = c.post(f"{API}/crm/customers", json={"name": "TEST Salima Hotel"}).json()["id"]
    assert (
        c.post(
            f"{API}/crm/activities",
            json={"customer_id": cid, "kind": "follow_up", "subject": "Call back"},
        ).status_code
        == 422
    )
    now = datetime.now(UTC)
    overdue = c.post(
        f"{API}/crm/activities",
        json={
            "customer_id": cid,
            "kind": "follow_up",
            "subject": "Send price list",
            "due_at": (now - timedelta(days=1)).isoformat(),
        },
    ).json()
    c.post(
        f"{API}/crm/activities",
        json={
            "customer_id": cid,
            "kind": "follow_up",
            "subject": "Confirm delivery date",
            "due_at": (now + timedelta(days=2)).isoformat(),
        },
    )
    c.post(f"{API}/crm/activities", json={"customer_id": cid, "kind": "note", "subject": "Met GM"})
    s = c.get(f"{API}/crm/summary").json()
    assert (s["follow_ups_overdue"], s["follow_ups_due_7_days"]) == (1, 1)
    assert [a["subject"] for a in c.get(f"{API}/crm/activities?due=overdue&mine=true").json()] == [
        "Send price list"
    ]
    c.post(f"{API}/crm/activities/{overdue['id']}/complete")
    assert c.get(f"{API}/crm/summary").json()["follow_ups_overdue"] == 0
    timeline = c.get(f"{API}/crm/customers/{cid}").json()["activities"]
    assert len(timeline) == 3


def test_director_dashboard_aggregates_real_records(app: FastAPI, db: Session) -> None:
    director = sign_in(app, make_user(db, "director"))
    empty = director.get(f"{API}/director/dashboard").json()
    assert empty["crm"]["has_records"] is False
    assert empty["finance"]["has_records"] is False
    assert empty["top_customers_open_pipeline"] == []

    bd = _bd(app, db)
    cid = bd.post(f"{API}/crm/customers", json={"name": "TEST Dedza Schools"}).json()["id"]
    for amount in ("200.00", "300.00"):
        bd.post(
            f"{API}/crm/opportunities",
            json={
                "customer_id": cid,
                "title": f"Desks {amount}",
                "division": "general_supplies",
                "value_amount": amount,
            },
        )
    bd.post(
        f"{API}/crm/opportunities",
        json={
            "customer_id": cid,
            "title": "Laptops",
            "division": "technologies",
            "value_amount": "50.00",
            "currency": "USD",
        },
    )
    data = director.get(f"{API}/director/dashboard").json()
    assert data["crm"]["has_records"] is True
    top = data["top_customers_open_pipeline"]
    # Only functional-currency (MWK) values are summed; no FX conversion is invented.
    assert top == [
        {"customer_id": cid, "name": "TEST Dedza Schools", "open_value": "500.00", "open_count": 2}
    ]
    assert bd.get(f"{API}/director/dashboard").status_code == 403
