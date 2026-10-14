"""Optional PostgreSQL persistence. Run Alembic explicitly before enabling writes."""

from backend.db.engine import get_repository
from backend.db.repository import ResearchRepository

__all__ = ["get_repository", "ResearchRepository"]
