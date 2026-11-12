"""Director Command Centre data (``/api/v1/director``).

Every figure is computed from stored records at request time. A section whose
module is not built yet is reported as ``available: false`` so the screen
shows "No data yet" rather than a zero or an estimate.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from app.modules.crm import service as crm
from app.modules.crm.models import OPEN_STAGES, Customer, Opportunity
from app.modules.crm.schemas import CrmSummary
from app.modules.finance import reports as finance_reports
from app.modules.finance.schemas import FinanceOverview
from app.modules.organisation.models import OrganisationProfile
from app.platform.approvals.models import ApprovalRequest
from app.platform.audit.models import SecurityAlert
from app.platform.authz.deps import DbSession, Principal, require
from app.platform.identity.models import User

router = APIRouter(prefix="/director", tags=["director"])


class ModuleStatus(BaseModel):
    available: bool
    stage: int


class PendingApproval(BaseModel):
    id: uuid.UUID
    summary: str
    subject_type: str
    requested_by: str
    created_at: datetime


class TopCustomer(BaseModel):
    customer_id: uuid.UUID
    name: str
    open_value: Decimal
    open_count: int


class DirectorDashboard(BaseModel):
    generated_at: datetime
    functional_currency: str
    crm: CrmSummary
    top_customers_open_pipeline: list[TopCustomer]
    approvals_pending: list[PendingApproval]
    approvals_pending_count: int
    security_alerts_open: int
    finance: FinanceOverview
    tenders: ModuleStatus
    procurement: ModuleStatus


def _functional_currency(db: DbSession) -> str:
    value = db.execute(select(OrganisationProfile.functional_currency).limit(1)).scalar()
    return value or "MWK"


@router.get("/dashboard", response_model=DirectorDashboard)
def dashboard(
    db: DbSession, _: Principal = Depends(require("director.dashboard.view"))
) -> DirectorDashboard:
    currency = _functional_currency(db)
    top = db.execute(
        select(
            Customer.id,
            Customer.name,
            func.coalesce(func.sum(Opportunity.value_amount), 0),
            func.count(Opportunity.id),
        )
        .join(Opportunity, Opportunity.customer_id == Customer.id)
        .where(Opportunity.stage.in_(OPEN_STAGES), Opportunity.currency == currency)
        .group_by(Customer.id, Customer.name)
        .order_by(func.coalesce(func.sum(Opportunity.value_amount), 0).desc())
        .limit(6)
    ).all()
    pending_q = (
        select(ApprovalRequest, User.display_name)
        .join(User, User.id == ApprovalRequest.requested_by)
        .where(ApprovalRequest.status == "pending")
    )
    pending = db.execute(pending_q.order_by(ApprovalRequest.created_at.asc()).limit(10)).all()
    pending_count = db.execute(
        select(func.count()).select_from(ApprovalRequest).where(ApprovalRequest.status == "pending")
    ).scalar_one()
    alerts = db.execute(
        select(func.count())
        .select_from(SecurityAlert)
        .where(SecurityAlert.acknowledged_at.is_(None))
    ).scalar_one()
    return DirectorDashboard(
        generated_at=crm.now(),
        functional_currency=currency,
        crm=crm.summary(db),
        top_customers_open_pipeline=[
            TopCustomer(customer_id=i, name=n, open_value=Decimal(v), open_count=c)
            for i, n, v, c in top
        ],
        approvals_pending=[
            PendingApproval(
                id=a.id,
                summary=a.summary,
                subject_type=a.subject_type,
                requested_by=name,
                created_at=a.created_at,
            )
            for a, name in pending
        ],
        approvals_pending_count=pending_count,
        security_alerts_open=alerts,
        finance=finance_reports.overview(db, crm.now().date()),
        tenders=ModuleStatus(available=True, stage=5),
        procurement=ModuleStatus(available=True, stage=6),
    )
