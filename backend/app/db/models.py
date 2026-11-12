"""Import every model so Alembic and the metadata see the full schema."""

from app.db.base import Base
from app.modules.crm.models import Activity, Contact, Customer, Opportunity
from app.modules.organisation.models import OrganisationProfile
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
    "Role",
    "RolePermission",
    "SecurityAlert",
    "StoredFile",
    "User",
    "UserMfa",
    "UserPreferences",
]
