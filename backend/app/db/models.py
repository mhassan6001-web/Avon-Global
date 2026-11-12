"""Import every module's models so Alembic sees the full metadata."""

from app.db.base import Base
from app.modules.organisation.models import OrganisationProfile

__all__ = ["Base", "OrganisationProfile"]
