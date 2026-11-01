"""Offline regression defaults; collection tests explicitly opt into fake sources."""
import pytest


@pytest.fixture(autouse=True)
def disable_background_disclosure_collection(monkeypatch, tmp_path):
    # API imports load .env. A developer's real DATABASE_URL must not enable a
    # network-backed background job when a test exercises application lifespan.
    monkeypatch.setenv("MARKET_TAPE_ENABLED", "false")
    monkeypatch.setenv("DISCLOSURE_COLLECTION_ENABLED", "false")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("ALLOW_LEGACY_FILE_AUTH", "true")
    monkeypatch.setenv("STOCKSCOPE_DATA_DIR", str(tmp_path / "data"))
