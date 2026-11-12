"""Database engine and session management (SQLAlchemy 2.x, psycopg 3)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def build_engine(settings: Settings) -> Engine:
    connect_args: dict[str, object] = {"application_name": "aven-global-api"}
    if settings.database_statement_timeout_ms:
        connect_args["options"] = f"-c statement_timeout={settings.database_statement_timeout_ms}"
    return create_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def get_engine() -> Engine:
    global _engine, _session_factory
    if _engine is None:
        _engine = build_engine(get_settings())
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session that is always closed.

    Transactions are committed explicitly by the service layer; anything left
    uncommitted is rolled back when the session closes.
    """
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def ping_database(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
