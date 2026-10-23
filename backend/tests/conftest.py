"""Offline regression defaults; collection tests explicitly opt into fake sources."""
import pytest


@pytest.fixture(autouse=True)
def disable_background_disclosure_collection(monkeypatch):
    # API imports load .env. A developer's real DATABASE_URL must not enable a
    # network-backed background job when a test exercises application lifespan.
    monkeypatch.setenv("DISCLOSURE_COLLECTION_ENABLED", "false")
