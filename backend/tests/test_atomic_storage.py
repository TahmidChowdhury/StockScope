"""Failed local writes must leave only the last committed document."""

import os

import pytest

from backend.services.research import save_records
from backend.trading import storage


def test_invalid_research_record_preserves_snapshot_and_cleans_up(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCKSCOPE_DATA_DIR", str(tmp_path))
    save_records("AAPL", "news_sentiment", [{"title": "Saved"}])
    path = tmp_path / "AAPL_news_sentiment.json"
    original = path.read_bytes()

    with pytest.raises(ValueError):
        save_records("AAPL", "news_sentiment", [{"score": float("nan")}])

    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_failed_trading_sync_preserves_document_and_cleans_up(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCKSCOPE_DATA_DIR", str(tmp_path))
    document = {"kind": "congress", "revision": 1}
    storage.mutate("congress", lambda previous: document)
    directory = tmp_path / "trading"
    original_files = set(directory.iterdir())

    def fail_sync(fd):
        raise OSError("sync failed")

    monkeypatch.setattr(os, "fsync", fail_sync)
    with pytest.raises(OSError, match="sync failed"):
        storage.mutate("congress", lambda previous: {**previous, "revision": 2})

    assert storage.read("congress") == document
    assert set(directory.iterdir()) == original_files
