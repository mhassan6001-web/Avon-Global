"""Compare the database's Alembic revision with the code's head revision.

Readiness fails while migrations are pending, so a new release never serves
traffic against an outdated schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"


@dataclass(frozen=True)
class MigrationState:
    current: tuple[str, ...]
    heads: tuple[str, ...]

    @property
    def up_to_date(self) -> bool:
        return set(self.current) == set(self.heads)


def code_heads() -> tuple[str, ...]:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return tuple(ScriptDirectory.from_config(config).get_heads())


def read_migration_state(engine: Engine) -> MigrationState:
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_heads()
    return MigrationState(current=tuple(current), heads=code_heads())
