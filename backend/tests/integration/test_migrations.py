from __future__ import annotations

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.db.migration_state import read_migration_state
from app.db.models import Base
from app.db.session import get_engine


def test_upgrade_downgrade_roundtrip(alembic_config: Config) -> None:
    engine = get_engine()
    command.downgrade(alembic_config, "base")
    assert "organisation_profile" not in inspect(engine).get_table_names()
    assert not read_migration_state(engine).up_to_date

    command.upgrade(alembic_config, "head")
    assert "organisation_profile" in inspect(engine).get_table_names()
    assert read_migration_state(engine).up_to_date


def test_models_match_migrations(migrated: None) -> None:
    with get_engine().connect() as connection:
        diff = compare_metadata(
            MigrationContext.configure(connection, opts={"compare_type": True}), Base.metadata
        )
    assert diff == [], f"models and migrations differ: {diff}"


def test_organisation_profile_constraints(migrated: None) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "INSERT INTO organisation_profile (trading_name) VALUES ('DEV-ONLY test') "
                "RETURNING registration_status, functional_currency, id"
            )
        ).one()
        assert row.registration_status == "not_confirmed"
        assert row.functional_currency == "MWK"
        conn.execute(text("DELETE FROM organisation_profile WHERE id = :id"), {"id": row.id})

    insert = "INSERT INTO organisation_profile (trading_name, {col}) VALUES ('x', '{val}')"
    bad_statements = [
        insert.format(col="registration_status", val="registered"),  # registered needs a number
        insert.format(col="functional_currency", val="EUR"),  # unsupported currency
        insert.format(col="registration_status", val="done"),  # unknown status
    ]
    for statement in bad_statements:
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(text(statement))
