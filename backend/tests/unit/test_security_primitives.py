"""Pure security primitives: TOTP (RFC 6238 vectors), tokens, signing, catalogue."""

import base64

import pytest

from app.platform.authz.catalogue import (
    DIRECTOR_ONLY,
    PERMISSION_CODES,
    ROLE_PERMISSIONS,
    ROLES,
    SENSITIVE_CODES,
    effective_permissions,
)
from app.platform.security import tokens, totp

# RFC 6238 Appendix B, SHA-1 seed "12345678901234567890", 8 digits.
RFC_SECRET = base64.b32encode(b"12345678901234567890").decode()
RFC_VECTORS = [
    (59, "94287082"),
    (1111111109, "07081804"),
    (1111111111, "14050471"),
    (1234567890, "89005924"),
    (2000000000, "69279037"),
    (20000000000, "65353130"),
]


@pytest.mark.parametrize(("at", "expected"), RFC_VECTORS)
def test_totp_matches_rfc6238(at: int, expected: str) -> None:
    assert totp.totp_at(RFC_SECRET, at, digits=8) == expected


def test_totp_verify_window_and_replay_counter() -> None:
    secret = totp.new_secret()
    now = 1_800_000_000.0
    code = totp.totp_at(secret, now)
    assert totp.verify(secret, code, at=now) == int(now // 30)
    assert totp.verify(secret, code, at=now + 30) == int(now // 30)  # one step of drift
    assert totp.verify(secret, code, at=now + 120) is None
    assert totp.verify(secret, "12345", at=now) is None
    assert totp.verify(secret, "abcdef", at=now) is None


def test_provisioning_uri() -> None:
    uri = totp.provisioning_uri("JBSWY3DPEHPK3PXP", "director@example.test")
    assert uri.startswith("otpauth://totp/AVEN%20GLOBAL%3Adirector%40example.test?")
    assert "issuer=AVEN+GLOBAL" in uri


def test_tokens_are_random_and_hashed() -> None:
    a, b = tokens.new_token(), tokens.new_token()
    assert a != b and len(a) >= 43
    assert len(tokens.hash_token(a)) == 32
    assert tokens.tokens_equal(tokens.hash_token(a), tokens.hash_token(a))


def test_signed_values() -> None:
    signed = tokens.sign("file-123:user-9", "s3cret", ttl_seconds=60, now=1000)
    assert tokens.verify_signed(signed, "s3cret", now=1030) == "file-123:user-9"
    assert tokens.verify_signed(signed, "s3cret", now=1061) is None  # expired
    assert tokens.verify_signed(signed, "other", now=1030) is None  # wrong key
    tampered = signed.replace("file-123", "file-124")
    assert tokens.verify_signed(tampered, "s3cret", now=1030) is None
    assert tokens.verify_signed("garbage", "s3cret") is None
    with pytest.raises(ValueError):
        tokens.sign("a.b", "s", 10)


def test_catalogue_integrity() -> None:
    from app.platform.authz.catalogue import PERMISSIONS

    assert len(PERMISSION_CODES) == len(PERMISSIONS)  # no duplicate codes
    for role in ROLES:
        assert ROLE_PERMISSIONS[role.code] <= PERMISSION_CODES
    assert ROLE_PERMISSIONS["director"] == PERMISSION_CODES


@pytest.mark.parametrize("role", [r.code for r in ROLES if r.code != "director"])
def test_staff_roles_never_hold_director_only_or_cross_department(role: str) -> None:
    perms = ROLE_PERMISSIONS[role]
    assert not (perms & DIRECTOR_ONLY)
    assert "director.dashboard.view" not in perms
    assert "procurement.supplier_bank.view" not in perms  # Director only by default


def test_sensitive_data_matrix() -> None:
    """Payroll, finance and supplier-bank access per the Director's matrix."""
    who = {code: {r for r, p in ROLE_PERMISSIONS.items() if code in p} for code in SENSITIVE_CODES}
    assert who["hr.payroll.view"] == {"director", "hr_admin"}
    assert who["finance.ledger.view"] == {"director", "finance"}
    assert who["finance.records.view"] == {"director", "finance"}
    assert who["procurement.supplier_bank.view"] == {"director"}
    assert who["admin.audit.view"] == {"director"}


def test_overrides_grant_and_deny() -> None:
    base = effective_permissions("finance", set(), set())
    assert "procurement.supplier_bank.view" not in base
    granted = effective_permissions("finance", {"procurement.supplier_bank.view"}, set())
    assert "procurement.supplier_bank.view" in granted
    denied = effective_permissions("finance", set(), {"finance.ledger.view"})
    assert "finance.ledger.view" not in denied
    # Deny wins over grant; Director-only permissions can never be granted; unknown codes ignored.
    both = effective_permissions("logistics", {"crm.records.view"}, {"crm.records.view"})
    assert "crm.records.view" not in both
    assert "admin.users.manage" not in effective_permissions(
        "finance", {"admin.users.manage"}, set()
    )
    assert "made.up.code" not in effective_permissions("finance", {"made.up.code"}, set())
    assert effective_permissions(None, set(), set()) == frozenset()
