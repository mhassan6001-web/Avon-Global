"""Organisation profile.

Holds the company identity as configurable data rather than hardcoded text:
trading name, legal name and registration status. Registration status defaults
to ``not_confirmed`` — the system never assumes the company is registered.

Stage 1 creates the table only. Reading and editing it through the API is
deferred until authentication and Director permissions exist (Stage 2), so it
cannot be changed by an unauthenticated caller.
"""

from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RegistrationStatus(StrEnum):
    NOT_CONFIRMED = "not_confirmed"
    PENDING = "pending"
    REGISTERED = "registered"


SUPPORTED_CURRENCIES = ("MWK", "USD", "ZAR", "ZMW")


class OrganisationProfile(TimestampMixin, Base):
    __tablename__ = "organisation_profile"
    __table_args__ = (
        CheckConstraint(
            "registration_status IN ('not_confirmed', 'pending', 'registered')",
            name="registration_status_valid",
        ),
        CheckConstraint(
            "functional_currency IN ('MWK', 'USD', 'ZAR', 'ZMW')",
            name="functional_currency_supported",
        ),
        CheckConstraint(
            "registration_status <> 'registered' OR registration_number IS NOT NULL",
            name="registered_requires_number",
        ),
        CheckConstraint(
            "(NOT print_address OR address_line1 IS NOT NULL) AND "
            "(NOT print_phone OR phone IS NOT NULL) AND "
            "(NOT print_email OR email IS NOT NULL) AND "
            "(NOT print_tpin OR tpin IS NOT NULL) AND "
            "(NOT print_vat OR vat_number IS NOT NULL)",
            name="print_requires_value",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    trading_name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(300))
    registration_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=RegistrationStatus.NOT_CONFIRMED.value
    )
    registration_number: Mapped[str | None] = mapped_column(String(100))
    headquarters_city: Mapped[str | None] = mapped_column(String(120))
    headquarters_country_code: Mapped[str | None] = mapped_column(String(2))
    functional_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="MWK"
    )
    # Contact and tax identity (Stage 16). Each item prints on documents only
    # after the Director approves it for print; tax numbers are never shown
    # on the strength of an unconfirmed value.
    address_line1: Mapped[str | None] = mapped_column(String(200))
    address_line2: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(200))
    tpin: Mapped[str | None] = mapped_column(String(40))
    vat_number: Mapped[str | None] = mapped_column(String(40))
    print_address: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    print_phone: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    print_email: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    print_tpin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    print_vat: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
