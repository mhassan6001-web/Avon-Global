import pytest

from app.core.config import (
    DEV_FIELD_KEY,
    DEV_SIGNING_SECRET,
    ConfigurationError,
    Environment,
    LogFormat,
    Settings,
)

PROD_OK = {
    "APP_ENV": "production",
    "DATABASE_URL": "postgresql+psycopg://aven:s3cure@db.internal.example:5432/aven_global",
    "REDIS_URL": "rediss://:pw@cache.internal.example:6380/0",
    "CORS_ORIGINS": "https://app.avenglobal.example",
    "LOG_FORMAT": "json",
    "FIELD_ENCRYPTION_KEYS": "cHJvZC1maWVsZC1rZXktZm9yLXRlc3RzLW9ubHktMDA=",
    "SIGNING_SECRET": "a-production-signing-secret-of-sufficient-length",
    "PUBLIC_BASE_URL": "https://app.avenglobal.example",
}


def test_defaults_are_development() -> None:
    settings = Settings.from_env({})
    assert settings.app_env is Environment.DEVELOPMENT
    assert settings.app_name == "AVEN GLOBAL"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.expose_error_details is True


def test_cors_origins_parse_from_csv() -> None:
    settings = Settings.from_env({"CORS_ORIGINS": "http://a.test, http://b.test ,"})
    assert settings.cors_origins == ["http://a.test", "http://b.test"]


def test_log_level_normalised() -> None:
    assert Settings.from_env({"LOG_LEVEL": "warning"}).log_level == "WARNING"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("LOG_LEVEL", "LOUD"),
        ("DATABASE_URL", "postgresql://u:p@h/db"),
        ("DATABASE_URL", "sqlite:///x.db"),
        ("REDIS_URL", "http://redis:6379"),
        ("API_V1_PREFIX", "api/v1"),
        ("APP_ENV", "qa"),
        ("DATABASE_POOL_SIZE", "0"),
    ],
)
def test_invalid_values_rejected(key: str, value: str) -> None:
    with pytest.raises(ConfigurationError):
        Settings.from_env({key: value})


def test_valid_production_configuration() -> None:
    settings = Settings.from_env(PROD_OK)
    assert settings.is_production
    assert settings.log_format is LogFormat.JSON
    assert settings.expose_error_details is False


@pytest.mark.parametrize(
    ("override", "fragment"),
    [
        ({"DATABASE_URL": "postgresql+psycopg://a:b@localhost:5432/x"}, "DATABASE_URL"),
        ({"REDIS_URL": "redis://127.0.0.1:6379/0"}, "REDIS_URL"),
        (
            {"DATABASE_URL": "postgresql+psycopg://aven:aven_dev_password@db.example/x"},
            "development password",
        ),
        ({"CORS_ORIGINS": "http://localhost:3000"}, "CORS origin"),
        ({"CORS_ORIGINS": "http://app.example"}, "CORS origin"),
        ({"LOG_FORMAT": "console"}, "LOG_FORMAT"),
        ({"LOG_LEVEL": "DEBUG"}, "DEBUG"),
        ({"FIELD_ENCRYPTION_KEYS": DEV_FIELD_KEY}, "development key"),
        ({"SIGNING_SECRET": DEV_SIGNING_SECRET}, "SIGNING_SECRET"),
        ({"SIGNING_SECRET": "short"}, "SIGNING_SECRET"),
        ({"COOKIE_SECURE": "false"}, "COOKIE_SECURE"),
        ({"PUBLIC_BASE_URL": "http://app.example"}, "PUBLIC_BASE_URL"),
    ],
)
def test_unsafe_production_configuration_rejected(override: dict[str, str], fragment: str) -> None:
    with pytest.raises(ConfigurationError, match=fragment):
        Settings.from_env({**PROD_OK, **override})


def test_settings_are_immutable() -> None:
    settings = Settings.from_env({})
    with pytest.raises(Exception):
        settings.app_name = "changed"  # type: ignore[misc]


def test_secure_cookies_default_by_environment() -> None:
    assert Settings.from_env({}).secure_cookies is False  # development
    assert Settings.from_env(PROD_OK).secure_cookies is True
