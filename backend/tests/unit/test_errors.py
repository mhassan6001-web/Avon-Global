from app.core.errors import (
    AppError,
    NotFoundError,
    PermissionDeniedError,
    code_for_status,
    error_envelope,
    sanitize_validation_errors,
)


def test_error_defaults() -> None:
    err = NotFoundError()
    assert (err.status_code, err.code) == (404, "not_found")
    assert PermissionDeniedError().status_code == 403


def test_error_overrides() -> None:
    err = AppError(
        "Quotation is locked.", code="quotation_locked", status_code=409, details={"id": 1}
    )
    assert (err.message, err.code, err.status_code, err.details) == (
        "Quotation is locked.",
        "quotation_locked",
        409,
        {"id": 1},
    )


def test_envelope_shape() -> None:
    body = error_envelope(code="not_found", message="Missing.", request_id="r1")
    assert body == {"error": {"code": "not_found", "message": "Missing.", "request_id": "r1"}}
    with_details = error_envelope(code="x", message="y", request_id=None, details=[1])
    assert with_details["error"]["details"] == [1]


def test_status_code_mapping() -> None:
    assert code_for_status(404) == "not_found"
    assert code_for_status(429) == "rate_limited"
    assert code_for_status(502) == "internal_error"
    assert code_for_status(418) == "error"


def test_validation_errors_never_echo_input() -> None:
    raw = [
        {
            "loc": ("body", "bank_account"),
            "msg": "invalid",
            "type": "value_error",
            "input": "12345678",
            "ctx": {"secret": True},
        }
    ]
    cleaned = sanitize_validation_errors(raw)
    assert cleaned == [{"loc": ["body", "bank_account"], "msg": "invalid", "type": "value_error"}]
    assert "12345678" not in str(cleaned)
