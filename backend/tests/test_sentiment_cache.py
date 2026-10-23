"""Deployment cache checks never turn verification into a network download."""

import json
import sys
from types import SimpleNamespace

import pytest

from scripts import cache_sentiment_models as cache


@pytest.fixture
def snapshot(monkeypatch, tmp_path):
    model = cache.CHALLENGERS[0]
    path = tmp_path / model.revision
    path.mkdir()
    config = {"id2label": {"0": "bearish", "1": "neutral", "2": "bullish"}}
    (path / "config.json").write_text(json.dumps(config))
    (path / "tokenizer_config.json").write_text("{}")
    (path / "tokenizer.json").write_text("{}")
    (path / "model.safetensors").write_bytes(b"fixture")
    calls = []

    def download(**kwargs):
        calls.append(kwargs)
        return str(path)

    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(snapshot_download=download))
    return model, path, calls


def test_verification_checks_exact_revision_and_is_always_offline(snapshot, tmp_path):
    model, path, calls = snapshot
    assert cache.verify_snapshot(model, tmp_path) == path
    assert calls == [{"repo_id": model.model_id, "revision": model.revision,
                      "cache_dir": str(tmp_path), "token": False, "local_files_only": True}]


@pytest.mark.parametrize("name", cache.REQUIRED_FILES)
def test_verification_rejects_incomplete_cache(snapshot, tmp_path, name):
    model, path, _ = snapshot
    (path / name).unlink()
    with pytest.raises(ValueError, match="missing or empty"):
        cache.verify_snapshot(model, tmp_path)


def test_verification_rejects_different_snapshot(snapshot, tmp_path, monkeypatch):
    model, _, _ = snapshot
    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(
        snapshot_download=lambda **kwargs: str(tmp_path / "main")))
    with pytest.raises(ValueError, match="pinned revision"):
        cache.verify_snapshot(model, tmp_path)


def test_verification_rejects_missing_label_class(snapshot, tmp_path):
    model, path, _ = snapshot
    (path / "config.json").write_text(json.dumps({"id2label": {"0": "LABEL_0"}}))
    with pytest.raises(ValueError, match="three declared sentiment labels"):
        cache.verify_snapshot(model, tmp_path)


def test_default_cli_is_inspection_only(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["cache_sentiment_models"])
    monkeypatch.setattr(cache, "verify_snapshot", lambda *args: pytest.fail("Inspection must not verify/load"))
    monkeypatch.setattr(cache, "smoke_test", lambda *args: pytest.fail("Inspection must not infer"))
    cache.main()
    assert "No downloads requested" in capsys.readouterr().out


def test_smoke_cli_verifies_selected_model_without_download(monkeypatch):
    model = cache.CHALLENGERS[0]
    calls = []
    monkeypatch.setattr(sys, "argv", ["cache_sentiment_models", "--model", model.key, "--smoke-test"])
    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(
        snapshot_download=lambda **kwargs: pytest.fail("Smoke CLI must not download")))
    monkeypatch.setattr(cache, "verify_snapshot", lambda item, directory: calls.append(("verify", item.key)))
    monkeypatch.setattr(cache, "smoke_test", lambda item: calls.append(("smoke", item.key)))
    monkeypatch.setattr(cache, "report_peak_memory", lambda: calls.append(("memory", None)))
    cache.main()
    assert calls == [("verify", model.key), ("smoke", model.key), ("memory", None)]


def test_download_cli_explicitly_allowlists_pinned_safetensors(snapshot, monkeypatch):
    model, _, calls = snapshot
    monkeypatch.setattr(sys, "argv", ["cache_sentiment_models", "--download", "--model", model.key])
    cache.main()
    assert len(calls) == 1
    assert calls[0]["revision"] == model.revision and calls[0]["token"] is False
    patterns = calls[0]["allow_patterns"]
    assert "*.safetensors" in patterns and not any(".bin" in pattern or ".py" in pattern for pattern in patterns)


def test_smoke_test_rejects_unscored_model_output(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(
        get_num_threads=lambda: 8, set_num_threads=lambda value: None))
    monkeypatch.setattr(cache.lab, "_load_model", lambda key: None)
    monkeypatch.setattr(cache.lab, "_transformer_batch", lambda *args: [{"status": "failed"}])
    with pytest.raises(ValueError, match="CPU inference smoke test failed"):
        cache.smoke_test(cache.CHALLENGERS[0])
