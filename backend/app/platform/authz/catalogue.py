"""Permission catalogue, roles and the department-scoped role matrix.

Single source of truth. The catalogue is synchronised into the database at
startup (``app.platform.authz.sync``). Permissions for modules not yet built
are defined now so later stages plug in without redesign; no endpoint uses
them until the module exists.

Director decision (2026-11-12): only the Director can access all records.
Every other role is limited to its department's section. Exceptions are
individual, audited overrides granted by the Director.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Permission:
    code: str
    description: str
    sensitive: bool = False


P = Permission
PERMISSIONS: tuple[Permission, ...] = (
    # Organisation and administration (module K)
    P("org.profile.view", "View the organisation profile"),
    P("org.profile.edit", "Edit legal name, registration and settings", sensitive=True),
    P("admin.users.manage", "Create, suspend and assign users", sensitive=True),
    P("admin.permissions.manage", "Grant or deny individual permissions", sensitive=True),
    P("admin.audit.view", "View the audit log and security alerts", sensitive=True),
    P("admin.login_history.view", "View everyone's login history", sensitive=True),
    # Files
    P("files.upload", "Upload files to sections the user can access"),
    # Director command centre
    P("director.dashboard.view", "View the Director command centre", sensitive=True),
    # CRM and sales
    P("crm.records.view", "View customers, contacts, opportunities, quotations"),
    P("crm.records.edit", "Create and edit CRM records and quotations"),
    P("crm.quotation.approve", "Approve quotations", sensitive=True),
    # Tenders
    P("tenders.records.view", "View the tender register"),
    P("tenders.records.edit", "Create and edit tenders and bid documents"),
    P("tenders.submission.approve", "Approve a bid for submission", sensitive=True),
    # Procurement and suppliers
    P("procurement.records.view", "View suppliers, quotations, requests and orders"),
    P("procurement.records.edit", "Create and edit procurement records"),
    P("procurement.order.approve", "Approve purchase requests and orders", sensitive=True),
    P("procurement.supplier_bank.view", "View supplier bank details", sensitive=True),
    P("procurement.supplier_bank.request_change", "Request a supplier bank-detail change"),
    P("procurement.supplier_bank.approve_change", "Approve supplier bank changes", sensitive=True),
    # Finance
    P("finance.records.view", "View invoices, bills, receipts, payments", sensitive=True),
    P("finance.records.edit", "Prepare finance transactions", sensitive=True),
    P("finance.ledger.view", "View the general ledger and reports", sensitive=True),
    P("finance.transaction.approve", "Approve and post restricted transactions", sensitive=True),
    # Inventory and logistics
    P("inventory.records.view", "View stock, warehouses and movements"),
    P("inventory.records.edit", "Record stock movements"),
    P("logistics.records.view", "View shipments and deliveries"),
    P("logistics.records.edit", "Edit shipments and deliveries"),
    # Human resources
    P("hr.records.view", "View employee records, leave and attendance", sensitive=True),
    P("hr.records.edit", "Edit employee records, leave and attendance", sensitive=True),
    P("hr.payroll.view", "View salaries and payroll", sensitive=True),
    P("hr.payroll.prepare", "Prepare payroll runs", sensitive=True),
    P("hr.payroll.approve", "Approve payroll runs", sensitive=True),
    # Communications
    P("comms.own.use", "Messages, tasks and reports addressed to the user"),
    P("comms.announcements.send", "Send company announcements"),
    # JARVIS
    P("jarvis.use", "Use the JARVIS assistant"),
)
del P

PERMISSION_CODES: frozenset[str] = frozenset(p.code for p in PERMISSIONS)
SENSITIVE_CODES: frozenset[str] = frozenset(p.code for p in PERMISSIONS if p.sensitive)


@dataclass(frozen=True)
class Role:
    code: str
    name: str
    department_code: str
    mfa_required: bool


ROLES: tuple[Role, ...] = (
    Role("director", "Director", "executive", mfa_required=True),
    Role("business_development", "Business Development", "business_development", False),
    Role("procurement", "Procurement", "procurement", False),
    Role("finance", "Finance", "finance", mfa_required=True),
    Role("logistics", "Logistics", "logistics", False),
    Role("hr_admin", "HR/Admin", "hr_admin", mfa_required=True),
)
ROLE_BY_CODE = {r.code: r for r in ROLES}

DEPARTMENTS: tuple[tuple[str, str], ...] = (
    ("executive", "Executive"),
    ("business_development", "Business Development"),
    ("procurement", "Procurement"),
    ("finance", "Finance"),
    ("logistics", "Logistics"),
    ("hr_admin", "HR/Admin"),
)

_EVERYONE = {"org.profile.view", "files.upload", "comms.own.use"}

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "director": PERMISSION_CODES,
    "business_development": frozenset(
        _EVERYONE
        | {"crm.records.view", "crm.records.edit", "tenders.records.view", "tenders.records.edit"}
    ),
    "procurement": frozenset(
        _EVERYONE
        | {
            "procurement.records.view",
            "procurement.records.edit",
            "procurement.supplier_bank.request_change",
        }
    ),
    "finance": frozenset(
        _EVERYONE | {"finance.records.view", "finance.records.edit", "finance.ledger.view"}
    ),
    "logistics": frozenset(
        _EVERYONE
        | {
            "inventory.records.view",
            "inventory.records.edit",
            "logistics.records.view",
            "logistics.records.edit",
        }
    ),
    "hr_admin": frozenset(
        _EVERYONE | {"hr.records.view", "hr.records.edit", "hr.payroll.view", "hr.payroll.prepare"}
    ),
}

# Permissions that only the Director may ever hold by role. Overrides cannot grant these.
DIRECTOR_ONLY: frozenset[str] = frozenset(
    {
        "admin.users.manage",
        "admin.permissions.manage",
        "admin.audit.view",
        "admin.login_history.view",
        "org.profile.edit",
        "procurement.supplier_bank.approve_change",
        "finance.transaction.approve",
        "hr.payroll.approve",
        "tenders.submission.approve",
        "procurement.order.approve",
        "crm.quotation.approve",
    }
)


def effective_permissions(
    role_code: str | None, grants: set[str] | frozenset[str], denies: set[str] | frozenset[str]
) -> frozenset[str]:
    """Role permissions plus individual grants, minus individual denies (deny wins)."""
    base = ROLE_PERMISSIONS.get(role_code or "", frozenset())
    allowed_grants = {g for g in grants if g in PERMISSION_CODES and g not in DIRECTOR_ONLY}
    return frozenset((base | allowed_grants) - set(denies))
