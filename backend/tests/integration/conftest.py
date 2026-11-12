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
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402
from app.db import session as db_session  # noqa: E402
from app.db.migration_state import ALEMBIC_INI, BACKEND_ROOT  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def settings() -> Settings:
    os.environ["APP_ENV"] = "test"
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
