"""Role-by-endpoint matrix: every protected endpoint, every role, anonymous and suspended.

Business-module endpoints do not exist yet (no fake modules); their access rules
are covered by the catalogue tests in ``tests/unit/test_security_primitives.py``
and these tests extend automatically as module routers are added in later stages.
"""

from __future__ import annotations

import io
import uuid

import pytest
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.platform.approvals import service as approvals
from app.platform.authz.catalogue import ROLES
from app.platform.authz.deps import Principal
from app.platform.identity import service as identity

from .helpers import client_for, make_user, sign_in

API = "/api/v1"
ALL_ROLES = [r.code for r in ROLES]
DIRECTOR = {"director"}
EVERYONE = set(ALL_ROLES)
CRM = {"director", "business_development"}
PRC = {"director", "procurement"}
FIN = {"director", "finance"}
LGX = {"director", "logistics"}
HRA = {"director", "hr_admin"}

PDF = b"%PDF-1.4\n% AVEN test document\n%%EOF\n"


def _upload(c, permission: str = "files.upload"):  # type: ignore[no-untyped-def]
    return c.post(
        f"{API}/files",
        data={"module": "general", "required_permission": permission},
        files={"file": ("note.pdf", io.BytesIO(PDF), "application/pdf")},
    )


# (method, path, body, roles allowed)
MATRIX: list[tuple[str, str, dict | None, set[str]]] = [
    ("GET", "/auth/me", None, EVERYONE),
    ("GET", "/auth/sessions", None, EVERYONE),
    ("GET", "/auth/login-history", None, EVERYONE),
    ("GET", "/organisation/profile", None, EVERYONE),
    ("PUT", "/organisation/profile", {"trading_name": "AVEN GLOBAL"}, DIRECTOR),
    ("GET", "/admin/users", None, DIRECTOR),
    ("GET", "/admin/roles", None, DIRECTOR),
    ("GET", "/admin/permissions", None, DIRECTOR),
    (
        "POST",
        "/admin/users",
        {"email": "m@test.aven.invalid", "display_name": "Matrix", "role": "logistics"},
        DIRECTOR,
    ),
    ("GET", "/admin/audit", None, DIRECTOR),
    ("POST", "/admin/audit/verify", None, DIRECTOR),
    ("GET", "/admin/login-history", None, DIRECTOR),
    ("GET", "/admin/security-alerts", None, DIRECTOR),
    ("GET", f"/admin/users/{uuid.uuid4()}/overrides", None, DIRECTOR),
    # Stage 4: Director dashboard and CRM (Business Development's section)
    ("GET", "/director/dashboard", None, DIRECTOR),
    ("GET", "/crm/summary", None, CRM),
    ("GET", "/crm/customers", None, CRM),
    ("POST", "/crm/customers", {"name": "Matrix Customer TEST"}, CRM),
    ("GET", f"/crm/customers/{uuid.uuid4()}", None, CRM),
    ("GET", "/crm/opportunities", None, CRM),
    ("GET", "/crm/activities", None, CRM),
    (
        "POST",
        "/crm/opportunities",
        {"customer_id": str(uuid.uuid4()), "title": "x1", "division": "technologies"},
        CRM,
    ),
    # Stage 5: tenders (Business Development) and the approval queue (everyone signed in)
    ("GET", "/tenders", None, CRM),
    ("GET", "/tenders/summary", None, CRM),
    ("GET", f"/tenders/{uuid.uuid4()}", None, CRM),
    (
        "POST",
        "/tenders",
        {
            "title": "Matrix",
            "issuer_name": "TEST",
            "kind": "rfq",
            "submission_deadline": "2031-01-01T10:00:00+02:00",
        },
        CRM,
    ),
    ("GET", "/approvals", None, EVERYONE),
    # Stage 6: procurement
    ("GET", "/procurement/suppliers", None, PRC),
    ("POST", "/procurement/suppliers", {"name": "Matrix Supplier TEST"}, PRC),
    ("GET", "/procurement/requests", None, PRC),
    ("GET", "/procurement/orders", None, PRC),
    (
        "POST",
        f"/procurement/suppliers/{uuid.uuid4()}/bank-change",
        {
            "bank_name": "TEST",
            "account_name": "TEST",
            "account_number": "12345678",
            "reason": "matrix check",
        },
        PRC,
    ),
    # Stage 7: finance
    ("GET", "/finance/invoices", None, FIN),
    ("GET", "/finance/accounts", None, FIN),
    ("GET", "/finance/reports/trial-balance", None, FIN),
    ("GET", "/finance/overview", None, FIN),
    ("GET", "/finance/bills", None, FIN),
    (
        "POST",
        "/finance/periods",
        {"name": "Matrix", "start_date": "2001-01-01", "end_date": "2001-01-31"},
        FIN,
    ),
    ("POST", f"/finance/periods/{uuid.uuid4()}/close", None, DIRECTOR),
    # Stage 8: inventory and logistics
    ("GET", "/inventory/products", None, LGX),
    ("GET", "/inventory/levels", None, LGX),
    ("GET", "/inventory/open-orders", None, LGX),
    ("GET", "/logistics/shipments", None, LGX),
    ("GET", "/logistics/delivery-notes", None, LGX),
    ("GET", "/logistics/customers", None, LGX),
    # Stage 9: HR and payroll
    ("GET", "/hr/employees", None, HRA),
    ("GET", "/hr/leave", None, HRA),
    ("GET", "/hr/payroll-runs", None, HRA),
    ("GET", "/hr/pay-components", None, HRA),
]


@pytest.mark.parametrize("role", ALL_ROLES)
def test_role_matrix(app: FastAPI, db: Session, role: str) -> None:
    tu = make_user(db, role)
    c = sign_in(app, tu, step_up=True)
    for method, path, body, allowed in MATRIX:
        if body and "email" in body:
            body = {**body, "email": f"{role}-{uuid.uuid4().hex[:6]}@test.aven.invalid"}
        r = c.request(method, f"{API}{path}", json=body)
        if role in allowed:
            assert r.status_code not in (401, 403), (
                f"{role} {method} {path} -> {r.status_code} {r.text}"
            )
        else:
            assert r.status_code == 403, f"{role} {method} {path} -> {r.status_code}"
            assert r.json()["error"]["code"] == "permission_denied"


def test_anonymous_and_suspended_are_rejected(app: FastAPI, db: Session) -> None:
    anon = client_for(app)
    tu = make_user(db, "logistics")
    suspended = sign_in(app, tu)
    tu.user.status = "suspended"
    db.commit()
    for method, path, body, _ in MATRIX:
        assert anon.request(method, f"{API}{path}", json=body).status_code == 401, path
        assert suspended.request(method, f"{API}{path}", json=body).status_code == 401, path


def test_overrides_extend_and_restrict_individuals(app: FastAPI, db: Session) -> None:
    director = make_user(db, "director")
    finance = make_user(db, "finance")
    d = sign_in(app, director, step_up=True)
    grant = {
        "permission": "procurement.supplier_bank.view",
        "effect": "grant",
        "reason": "Needs bank details to prepare supplier payments",
    }
    assert d.post(f"{API}/admin/users/{finance.user.id}/overrides", json=grant).status_code == 201
    f = sign_in(app, finance)
    assert "procurement.supplier_bank.view" in f.get(f"{API}/auth/me").json()["permissions"]
    deny = {
        "permission": "finance.ledger.view",
        "effect": "deny",
        "reason": "Temporary restriction",
    }
    assert d.post(f"{API}/admin/users/{finance.user.id}/overrides", json=deny).status_code == 201
    assert "finance.ledger.view" not in f.get(f"{API}/auth/me").json()["permissions"]
    # Director-only permissions can never be granted.
    bad = {
        "permission": "admin.users.manage",
        "effect": "grant",
        "reason": "Should not be possible",
    }
    assert d.post(f"{API}/admin/users/{finance.user.id}/overrides", json=bad).status_code == 403
    assert (
        d.delete(
            f"{API}/admin/users/{finance.user.id}/overrides/procurement.supplier_bank.view"
        ).status_code
        == 200
    )
    assert "procurement.supplier_bank.view" not in f.get(f"{API}/auth/me").json()["permissions"]


def test_director_accounts_cannot_be_created_or_assigned_via_api(app: FastAPI, db: Session) -> None:
    director = make_user(db, "director")
    staff = make_user(db, "logistics")
    d = sign_in(app, director, step_up=True)
    r = d.post(
        f"{API}/admin/users",
        json={"email": "d2@test.aven.invalid", "display_name": "Second", "role": "director"},
    )
    assert r.status_code == 403
    assert (
        d.put(f"{API}/admin/users/{staff.user.id}/role", json={"role": "director"}).status_code
        == 403
    )
    moved = d.put(f"{API}/admin/users/{staff.user.id}/role", json={"role": "procurement"})
    assert moved.status_code == 200 and moved.json()["role"] == "procurement"


def test_organisation_profile_rules(app: FastAPI, db: Session) -> None:
    director = make_user(db, "director")
    d = sign_in(app, director, step_up=True)
    bad = {"trading_name": "AVEN GLOBAL", "registration_status": "registered"}
    assert d.put(f"{API}/organisation/profile", json=bad).status_code == 422
    ok = {
        "trading_name": "AVEN GLOBAL",
        "registration_status": "not_confirmed",
        "headquarters_city": "Lilongwe",
        "headquarters_country_code": "MW",
    }
    r = d.put(f"{API}/organisation/profile", json=ok)
    assert r.status_code == 200 and r.json()["configured"] is True
    assert r.json()["registration_status"] == "not_confirmed"


def test_files_access_follows_permissions(app: FastAPI, db: Session) -> None:
    procurement = make_user(db, "procurement")
    finance = make_user(db, "finance")
    director = make_user(db, "director")
    p, f, d = sign_in(app, procurement), sign_in(app, finance), sign_in(app, director)
    # Cannot file into a section you cannot access.
    assert _upload(p, "finance.records.view").status_code == 403
    up = _upload(p, "procurement.records.view")
    assert up.status_code == 201, up.text
    file_id = up.json()["id"]
    assert f.get(f"{API}/files/{file_id}/download").status_code == 403
    dl = d.get(f"{API}/files/{file_id}/download")
    assert dl.status_code == 200 and dl.content == PDF
    assert dl.headers["content-type"].startswith("application/pdf")
    # Signed URL: works for its owner, not for anyone else.
    url = p.post(f"{API}/files/{file_id}/signed-url").json()["url"]
    assert p.get(url).status_code == 200
    assert d.get(url).status_code == 403


def test_file_validation(app: FastAPI, db: Session) -> None:
    c = sign_in(app, make_user(db, "logistics"))
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    spoof = c.post(
        f"{API}/files",
        data={"module": "g", "required_permission": "files.upload"},
        files={"file": ("invoice.pdf", io.BytesIO(png), "application/pdf")},
    )
    assert spoof.status_code == 415
    exe = c.post(
        f"{API}/files",
        data={"module": "g", "required_permission": "files.upload"},
        files={"file": ("tool.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")},
    )
    assert exe.status_code == 415
    big = b"%PDF-1.4\n" + b"0" * (1024 * 1024 + 10)  # MAX_UPLOAD_MB=1 in tests
    too_big = c.post(
        f"{API}/files",
        data={"module": "g", "required_permission": "files.upload"},
        files={"file": ("big.pdf", io.BytesIO(big), "application/pdf")},
    )
    assert too_big.status_code == 413


def test_expired_signed_url(app: FastAPI, db: Session) -> None:
    from app.core.config import get_settings
    from app.platform.security import tokens

    tu = make_user(db, "logistics")
    c = sign_in(app, tu)
    file_id = _upload(c).json()["id"]
    stale = tokens.sign(f"{file_id}:{tu.user.id}", get_settings().signing_secret, 60, now=0)
    assert c.get(f"{API}/files/signed/{stale}").status_code == 403


def _principal(db: Session, tu) -> Principal:  # type: ignore[no-untyped-def]
    from sqlalchemy import select

    from app.platform.identity.models import AuthSession

    sign = identity._create_session(db, tu.user, "active", None, None)
    sign.session.step_up_at = identity.now()
    db.commit()
    session = db.execute(select(AuthSession).where(AuthSession.id == sign.session.id)).scalar_one()
    return Principal(
        session=session,
        user=tu.user,
        role=identity.role_of(db, tu.user),
        permissions=identity.permissions_of(db, tu.user),
    )


def test_separation_of_duties(db: Session) -> None:
    from sqlalchemy import update
    from sqlalchemy.exc import IntegrityError

    from app.platform.approvals.models import ApprovalRequest

    director = make_user(db, "director")
    procurement = make_user(db, "procurement")
    d, p = _principal(db, director), _principal(db, procurement)

    # The Director cannot approve their own restricted request.
    own = approvals.create_request(
        db,
        principal=d,
        subject_type="test_subject",
        subject_id="S-1",
        permission_required="procurement.supplier_bank.approve_change",
        summary="Change bank details",
    )
    with pytest.raises(approvals.SelfApprovalError):
        approvals.decide(db, principal=d, request=own, approve=True)

    # A staff member's request is approved by a different user holding the permission.
    req = approvals.create_request(
        db,
        principal=p,
        subject_type="test_subject",
        subject_id="S-2",
        permission_required="procurement.supplier_bank.approve_change",
        summary="Change bank details",
    )
    from app.core.errors import PermissionDeniedError

    with pytest.raises(PermissionDeniedError):  # requester lacks the permission anyway
        approvals.decide(db, principal=p, request=req, approve=True)
    decided = approvals.decide(db, principal=d, request=req, approve=True)
    assert decided.status == "approved" and decided.decided_by == director.user.id
    db.commit()

    # The database itself refuses a self-decision, even bypassing the service.
    with pytest.raises(IntegrityError):
        db.execute(
            update(ApprovalRequest)
            .where(ApprovalRequest.id == own.id)
            .values(decided_by=director.user.id, status="approved")
        )
    db.rollback()
