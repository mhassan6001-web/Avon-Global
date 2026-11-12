"""Integration fixtures: real FastAPI app, real PostgreSQL, real Alembic.

Requires the full backend dependencies and ``TEST_DATABASE_URL`` pointing at a
disposable database (it is migrated down to base and back up). The whole
package is skipped otherwise, and the skip is reported in the test summary.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

for module in ("fastapi", "sqlalchemy", "alembic", "psycopg"):
    pytest.importorskip(module, reason=f"integration tests need '{module}'")

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    pytest.skip("TEST_DATABASE_URL not set", allow_module_level=True)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402
from app.db import session as db_session  # noqa: E402
from app.db.migration_state import ALEMBIC_INI, BACKEND_ROOT  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    os.environ["APP_ENV"] = "test"
    # Fast password hashing and small upload limit for tests only.
    os.environ["ARGON2_TIME_COST"] = "1"
    os.environ["ARGON2_MEMORY_KIB"] = "8192"
    os.environ["MAX_UPLOAD_MB"] = "1"
    os.environ["STORAGE_DIR"] = str(tmp_path_factory.mktemp("files"))
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL  # type: ignore[assignment]
    os.environ.setdefault("REDIS_URL", os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/0"))
    get_settings.cache_clear()
    db_session.dispose_engine()
    return get_settings()


@pytest.fixture(scope="session")
def alembic_config(settings: Settings) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return config


@pytest.fixture(scope="session")
def migrated(alembic_config: Config) -> Iterator[None]:
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    yield


@pytest.fixture
def client(settings: Settings, migrated: None) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _clean_rate_limits(settings: Settings) -> Iterator[None]:
    """Each test starts with empty rate-limit counters and lockouts."""
    from app.platform import ratelimit

    ratelimit.client.cache_clear()
    ratelimit.client().flushdb()
    yield


# Business-module tables are emptied before each test so counts and "No data yet"
# states are deterministic. Identity and the append-only audit log are kept.
BUSINESS_PREFIXES = ("crm_", "tnd_", "prc_", "fin_", "inv_", "lgx_", "hr_", "com_", "ai_", "doc_")


def _truncate_business_tables(session: Session) -> None:
    from sqlalchemy import text

    from app.db.models import Base

    names = [t.name for t in Base.metadata.sorted_tables if t.name.startswith(BUSINESS_PREFIXES)]
    names.append("sys_approval_requests")
    session.execute(text(f"TRUNCATE {', '.join(names)} RESTART IDENTITY CASCADE"))  # nosec B608
    session.commit()


@pytest.fixture
def db(settings: Settings, migrated: None) -> Iterator[Session]:
    from app.platform.authz.sync import sync_catalogue

    session = db_session.get_session_factory()()
    _truncate_business_tables(session)
    sync_catalogue(session)
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def app(settings: Settings, migrated: None, db: Session) -> FastAPI:
    return create_app(settings)
