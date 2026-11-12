"""Request and response models for authentication and account endpoints."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")


def validate_email(value: str) -> str:
    value = value.strip().lower()
    if not _EMAIL.match(value):
        raise ValueError("Enter a valid email address.")
    return value


class LoginRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def _normalise(cls, value: str) -> str:
        return value.strip().lower()


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: str
    role_name: str
    department: str
    status: str
    is_dev_account: bool
    mfa_enabled: bool


class MeOut(BaseModel):
    user: UserOut
    session_state: str
    permissions: list[str]
    mfa_required_by_role: bool
    step_up_valid_until: datetime | None


class LoginOut(BaseModel):
    state: str  # active | mfa_pending | mfa_enrolment_required
    csrf_token: str
    user: UserOut


class MfaVerifyRequest(BaseModel):
    code: str | None = Field(default=None, max_length=12)
    recovery_code: str | None = Field(default=None, max_length=32)


class MfaSetupOut(BaseModel):
    secret: str
    otpauth_uri: str
    qr_svg: str


class MfaEnableRequest(BaseModel):
    code: str = Field(min_length=6, max_length=12)


class RecoveryCodesOut(BaseModel):
    recovery_codes: list[str]
    message: str = (
        "Store these codes somewhere safe. Each works once. They will not be shown again."
    )


class StepUpRequest(BaseModel):
    code: str | None = Field(default=None, max_length=12)
    password: str | None = Field(default=None, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class RedeemLinkRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=1, max_length=256)


class SessionOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    ip: str | None
    user_agent: str | None
    current: bool


class LoginEventOut(BaseModel):
    occurred_at: datetime
    email_attempted: str
    outcome: str
    ip: str | None
    user_agent: str | None
    user_id: uuid.UUID | None = None


class OkOut(BaseModel):
    ok: bool = True
