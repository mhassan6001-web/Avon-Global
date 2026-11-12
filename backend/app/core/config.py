"""Application configuration.

All configuration is read from environment variables (optionally loaded from a
``.env`` file in development). Settings are validated once at startup; an
invalid configuration stops the application instead of running half-configured.

The loader deliberately depends only on Pydantic so it can be unit-tested
without the web framework or database driver installed.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from enum import StrEnum
from functools import lru_cache
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

# Hosts that must never appear in production URLs. Matched only, never bound.
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})  # noqa: S104  # nosec B104


# Development-only secrets. Production configuration is rejected if it uses them.
DEV_FIELD_KEY = "ZGV2LW9ubHktZmllbGQta2V5LWF2ZW4tZ2xvYmFsLTA="  # nosec B105
DEV_SIGNING_SECRET = "dev-only-signing-secret-aven-global-do-not-use"  # noqa: S105  # nosec B105


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class LogFormat(StrEnum):
    JSON = "json"
    CONSOLE = "console"


class ConfigurationError(RuntimeError):
    """Raised when the environment does not describe a valid configuration."""


def _split_csv(value: object) -> object:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class Settings(BaseModel):
    """Validated runtime settings. Field names map to upper-case env vars."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    app_name: str = "AVEN GLOBAL"
    app_version: str = "0.1.0"
    app_env: Environment = Environment.DEVELOPMENT

    api_v1_prefix: str = "/api/v1"

    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.CONSOLE

    database_url: str = Field(
        default="postgresql+psycopg://aven:aven_dev_password@postgres:5432/aven_global",
        description="SQLAlchemy URL. Must use the psycopg (v3) driver.",
    )
    database_pool_size: Annotated[int, Field(ge=1, le=100)] = 5
    database_max_overflow: Annotated[int, Field(ge=0, le=100)] = 10
    database_pool_timeout_seconds: Annotated[float, Field(gt=0, le=120)] = 10.0
    database_statement_timeout_ms: Annotated[int, Field(ge=0)] = 15_000

    redis_url: str = "redis://redis:6379/0"
    redis_required: bool = True
    readiness_check_timeout_seconds: Annotated[float, Field(gt=0, le=30)] = 2.0

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- identity and security (Stage 2) ---------------------------------
    public_base_url: str = "http://localhost:3000"
    session_idle_minutes: Annotated[int, Field(ge=5, le=24 * 60)] = 30
    session_absolute_hours: Annotated[int, Field(ge=1, le=72)] = 12
    step_up_minutes: Annotated[int, Field(ge=1, le=30)] = 5
    cookie_secure: bool | None = None  # default: True outside development/test
    invitation_valid_hours: Annotated[int, Field(ge=1, le=24 * 14)] = 72
    reset_link_valid_minutes: Annotated[int, Field(ge=5, le=24 * 60)] = 60
    # Comma-separated Fernet keys; the first encrypts, all decrypt (rotation).
    field_encryption_keys: list[str] = Field(default_factory=lambda: [DEV_FIELD_KEY])
    signing_secret: str = DEV_SIGNING_SECRET
    storage_dir: str = "/tmp/aven-files"  # noqa: S108  # nosec B108 - dev default only
    max_upload_mb: Annotated[int, Field(ge=1, le=200)] = 25
    argon2_time_cost: Annotated[int, Field(ge=1, le=10)] = 3
    argon2_memory_kib: Annotated[int, Field(ge=8 * 1024, le=1024 * 1024)] = 64 * 1024

    # --- validators -------------------------------------------------------

    @field_validator("cors_origins", "field_encryption_keys", mode="before")
    @classmethod
    def _parse_csv_lists(cls, value: object) -> object:
        return _split_csv(value)

    @field_validator("log_level")
    @classmethod
    def _valid_log_level(cls, value: str) -> str:
        level = value.upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"unsupported log level {value!r}")
        return level

    @field_validator("database_url")
    @classmethod
    def _valid_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use the 'postgresql+psycopg://' scheme")
        return value

    @field_validator("redis_url")
    @classmethod
    def _valid_redis_url(cls, value: str) -> str:
        if urlsplit(value).scheme not in {"redis", "rediss"}:
            raise ValueError("REDIS_URL must use the redis:// or rediss:// scheme")
        return value

    @field_validator("api_v1_prefix")
    @classmethod
    def _valid_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/"):
            raise ValueError("API_V1_PREFIX must start with '/' and not end with '/'")
        return value

    @model_validator(mode="after")
    def _production_guards(self) -> Settings:
        if self.app_env is not Environment.PRODUCTION:
            return self
        problems: list[str] = []
        if urlsplit(self.database_url).hostname in LOCAL_HOSTS:
            problems.append("DATABASE_URL points at a local host")
        if urlsplit(self.redis_url).hostname in LOCAL_HOSTS:
            problems.append("REDIS_URL points at a local host")
        if "aven_dev_password" in self.database_url:
            problems.append("DATABASE_URL uses the development password")
        for origin in self.cors_origins:
            parts = urlsplit(origin)
            if parts.scheme != "https" or parts.hostname in LOCAL_HOSTS:
                problems.append(f"CORS origin {origin!r} must be a non-local https origin")
        if self.log_format is not LogFormat.JSON:
            problems.append("LOG_FORMAT must be 'json' in production")
        if self.log_level == "DEBUG":
            problems.append("LOG_LEVEL must not be DEBUG in production")
        if DEV_FIELD_KEY in self.field_encryption_keys:
            problems.append("FIELD_ENCRYPTION_KEYS uses the development key")
        if self.signing_secret == DEV_SIGNING_SECRET or len(self.signing_secret) < 32:
            problems.append("SIGNING_SECRET must be set (32+ characters, not the dev value)")
        if self.cookie_secure is False:
            problems.append("COOKIE_SECURE cannot be false in production")
        if not self.public_base_url.startswith("https://"):
            problems.append("PUBLIC_BASE_URL must be https in production")
        if problems:
            raise ValueError("unsafe production configuration: " + "; ".join(problems))
        return self

    # --- helpers ----------------------------------------------------------

    @property
    def is_production(self) -> bool:
        return self.app_env is Environment.PRODUCTION

    @property
    def secure_cookies(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.app_env not in {Environment.DEVELOPMENT, Environment.TEST}

    @property
    def expose_error_details(self) -> bool:
        """Whether unexpected-error responses may include exception details."""
        return self.app_env in {Environment.DEVELOPMENT, Environment.TEST}

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if environ is None else environ
        values = {name: source[name.upper()] for name in cls.model_fields if name.upper() in source}
        try:
            return cls.model_validate(values)
        except ValidationError as exc:
            raise ConfigurationError(f"Invalid configuration:\n{exc}") from exc


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - optional in production images
        return
    load_dotenv(override=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings (cached)."""
    _load_dotenv()
    return Settings.from_env()
