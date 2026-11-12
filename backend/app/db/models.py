"""Import every model so Alembic and the metadata see the full schema."""

from app.db.base import Base
from app.modules.crm.models import Activity, Contact, Customer, Opportunity
from app.modules.organisation.models import OrganisationProfile
from app.modules.procurement.models import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequest,
    PurchaseRequestLine,
    Supplier,
    SupplierBankAccount,
    SupplierQuote,
    SupplierQuoteLine,
)
from app.modules.tenders.models import Requirement, Tender
from app.platform.approvals.models import ApprovalRequest
from app.platform.audit.models import AuditEvent, SecurityAlert
from app.platform.files.models import StoredFile
from app.platform.identity.models import (
    AuthSession,
    Department,
    LoginEvent,
    OneTimeToken,
    Permission,
    PermissionOverride,
    Role,
    RolePermission,
    User,
    UserMfa,
    UserPreferences,
)

__all__ = [
    "Activity",
    "ApprovalRequest",
    "AuditEvent",
    "AuthSession",
    "Base",
    "Contact",
    "Customer",
    "Department",
    "LoginEvent",
    "OneTimeToken",
    "Opportunity",
    "OrganisationProfile",
    "Permission",
    "PermissionOverride",
    "PurchaseOrder",
    "PurchaseOrderLine",
    "PurchaseRequest",
    "PurchaseRequestLine",
    "Requirement",
    "Role",
    "RolePermission",
    "SecurityAlert",
    "StoredFile",
    "Supplier",
    "SupplierBankAccount",
    "SupplierQuote",
    "SupplierQuoteLine",
    "Tender",
    "User",
    "UserMfa",
    "UserPreferences",
]
