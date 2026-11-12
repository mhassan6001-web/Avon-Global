"""Organisation profile API. Everyone signed in may read; only the Director edits."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from app.platform.audit import service as audit
from app.platform.authz.deps import DbSession, Principal, require, require_step_up

from .models import SUPPORTED_CURRENCIES, OrganisationProfile, RegistrationStatus

router = APIRouter(prefix="/organisation", tags=["organisation"])


class ProfileIn(BaseModel):
    trading_name: str = Field(min_length=2, max_length=200)
    legal_name: str | None = Field(default=None, max_length=300)
    registration_status: RegistrationStatus = RegistrationStatus.NOT_CONFIRMED
    registration_number: str | None = Field(default=None, max_length=100)
    headquarters_city: str | None = Field(default=None, max_length=120)
    headquarters_country_code: str | None = Field(default=None, pattern="^[A-Z]{2}$")
    functional_currency: str = Field(default="MWK", pattern="^[A-Z]{3}$")

    @model_validator(mode="after")
    def _rules(self) -> ProfileIn:
        if self.functional_currency not in SUPPORTED_CURRENCIES:
            raise ValueError(
                f"functional_currency must be one of {', '.join(SUPPORTED_CURRENCIES)}"
            )
        if (
            self.registration_status is RegistrationStatus.REGISTERED
            and not self.registration_number
        ):
            raise ValueError("A registration number is required when status is 'registered'.")
        return self


class ProfileOut(ProfileIn):
    configured: bool


def _current(db: DbSession) -> OrganisationProfile | None:
    return db.execute(select(OrganisationProfile).limit(1)).scalar_one_or_none()


@router.get("/profile", response_model=ProfileOut)
def get_profile(db: DbSession, _: Principal = Depends(require("org.profile.view"))) -> ProfileOut:
    row = _current(db)
    if row is None:
        return ProfileOut(trading_name="AVEN GLOBAL", configured=False)
    return ProfileOut(
        trading_name=row.trading_name,
        legal_name=row.legal_name,
        registration_status=RegistrationStatus(row.registration_status),
        registration_number=row.registration_number,
        headquarters_city=row.headquarters_city,
        headquarters_country_code=row.headquarters_country_code,
        functional_currency=row.functional_currency,
        configured=True,
    )


@router.put("/profile", response_model=ProfileOut, dependencies=[Depends(require_step_up)])
def put_profile(
    body: ProfileIn, db: DbSession, principal: Principal = Depends(require("org.profile.edit"))
) -> ProfileOut:
    row = _current(db)
    before = None
    if row is None:
        row = OrganisationProfile(trading_name=body.trading_name)
        db.add(row)
    else:
        before = {"legal_name": row.legal_name, "registration_status": row.registration_status}
    row.trading_name = body.trading_name
    row.legal_name = body.legal_name
    row.registration_status = body.registration_status.value
    row.registration_number = body.registration_number
    row.headquarters_city = body.headquarters_city
    row.headquarters_country_code = body.headquarters_country_code
    row.functional_currency = body.functional_currency
    db.flush()
    audit.record(
        db,
        action="org.profile_updated",
        actor_id=principal.user.id,
        target_type="organisation_profile",
        target_id=row.id,
        details={"before": before or {}, "after": body.model_dump(mode="json")},
    )
    db.commit()
    return get_profile(db, principal)
