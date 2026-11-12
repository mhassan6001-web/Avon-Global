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
    address_line1: str | None = Field(default=None, max_length=200)
    address_line2: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=200)
    tpin: str | None = Field(default=None, max_length=40)
    vat_number: str | None = Field(default=None, max_length=40)
    # Director's approval to print each item on documents. Off by default.
    print_address: bool = False
    print_phone: bool = False
    print_email: bool = False
    print_tpin: bool = False
    print_vat: bool = False

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
        for flag, value, label in (
            (self.print_address, self.address_line1, "address"),
            (self.print_phone, self.phone, "telephone number"),
            (self.print_email, self.email, "email address"),
            (self.print_tpin, self.tpin, "TPIN"),
            (self.print_vat, self.vat_number, "VAT number"),
        ):
            if flag and not value:
                raise ValueError(f"Enter the {label} before approving it for print.")
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
        **{name: getattr(row, name) for name in ProfileIn.model_fields},
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
    for name, value in body.model_dump(mode="json").items():
        # Empty strings are stored as "not provided"; booleans are kept as given.
        setattr(row, name, value if isinstance(value, bool) else (value or None))
    row.trading_name = body.trading_name
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
