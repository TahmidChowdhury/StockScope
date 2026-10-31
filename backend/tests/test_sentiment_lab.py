"""The tone lab is read-only and unavailable data never becomes neutral."""

import copy
import json
import sys
import threading
from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.auth import verify_password_with_role
from backend.routers import sentiment_lab
from backend.sentiment import lab


@pytest.fixture
def news(monkeypatch):
    records = [{"title": "Debt and expenses declined after the company repaid its loan.",
                "description": "Quarterly operating profit increased.", "url": "https://example.test/story", "language": "en"}]
    monkeypatch.setattr(lab, "saved_news", lambda symbol, limit: records[:limit])
    monkeypatch.setattr(lab, "model_status", lambda spec: {"key": spec.key, "status": "not_cached"})
    return records


@pytest.fixture
def api(news):
    app = FastAPI()
    app.include_router(sentiment_lab.router, prefix="/api/sentiment-lab")
    app.dependency_overrides[verify_password_with_role] = lambda: "demo"
    with TestClient(app) as client:
        yield client


def test_preview_uses_actual_saved_text_without_mutation_or_model_loading(news, monkeypatch):
    before = copy.deepcopy(news)
    monkeypatch.setattr(lab, "_load_model", lambda key: pytest.fail("Preview must not load challengers"))
    result = lab.benchmark("aapl", 12)
    assert news == before
    assert result["symbol"] == "AAPL" and result["saved_scores_changed"] is False
    assert result["sample"]["eligible"] == 1 and result["sample"]["returned"] == 1
    row = result["rows"][0]
    assert row["text"] == news[0]["title"] + "\n" + news[0]["description"]
    assert row["coverage"] == "title+description"
    assert row["predictions"]["vader"]["status"] == "scored"
    assert row["predictions"]["finsense"]["label"] is None
    assert result["evaluation"]["status"] == "not_evaluated"
    assert all(item["status"] == "not_evaluated" for item in result["evaluation"]["models"].values())


def test_empty_unknown_and_unsupported_text_never_become_neutral(news, monkeypatch):
    news[:] = [{"title": "", "language": "en"}, {"title": "收益增长", "language": "zh"},
               {"title": "Short ambiguous text"}]
    def language(text, declared=None):
        return ("empty_text", None) if not text else ("unsupported_language", declared) if declared else ("unknown_language", None)
    monkeypatch.setattr(lab, "_language", language)
    monkeypatch.setattr(lab, "_vader", lambda text: pytest.fail("Ineligible text must not be scored"))
    result = lab.benchmark("AAPL", compare=True)
    assert result["sample"]["eligible"] == 0
    for row in result["rows"]:
        assert all(value["label"] is None for value in row["predictions"].values())


def test_company_releases_excluded_and_description_duplicates_removed(news):
    news[0].update(source_type="company_release", description=news[0]["title"])
    result = lab.benchmark("AAPL")
    assert result["sample"]["company_release_excluded"] == 1
    assert result["rows"][0]["coverage"] == "title"
    assert result["rows"][0]["predictions"]["vader"]["label"] is None


def test_explicit_language_and_empty_handling():
    assert lab._language("", "en") == ("empty_text", None)
    assert lab._language("Some text", "en-US") == ("eligible", "en")
    assert lab._language("Ein Text", "de") == ("unsupported_language", "de")


@pytest.mark.parametrize("limit", [0, 31])
def test_sample_bounds(news, limit):
    with pytest.raises(ValueError):
        lab.benchmark("AAPL", limit)


def test_label_template_contains_only_blank_labels_and_matching_hashes(news):
    template = lab.label_template("AAPL")
    preview = lab.benchmark("AAPL")
    assert template["labels"][0]["label"] is None
    assert template["labels"][0]["text_sha256"] == preview["rows"][0]["text_sha256"]
    assert "ground_truth" not in preview


def test_missing_models_are_not_neutral_predictions(news):
    result = lab.benchmark("AAPL", compare=True)
    assert result["rows"][0]["predictions"]["finsense"] == {"status": "not_cached", "label": None}


def test_local_cache_lookup_pins_revision_and_forbids_network(monkeypatch, tmp_path):
    calls = []
    def snapshot(**kwargs):
        calls.append(kwargs)
        return str(tmp_path)
    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(snapshot_download=snapshot))
    monkeypatch.setenv("STOCKSCOPE_HF_CACHE", str(tmp_path))
    for spec in lab.CHALLENGERS:
        assert lab._local_snapshot(spec) == tmp_path
        assert len(spec.revision) == 40 and spec.model_id.startswith(("AnkitAI/", "tabularisai/"))
    assert all(call["local_files_only"] is True and call["cache_dir"] == str(tmp_path) for call in calls)
    assert {call["revision"] for call in calls} == {spec.revision for spec in lab.CHALLENGERS}


def test_loader_uses_safetensors_no_remote_code_and_vetted_fast_tokenizer(monkeypatch, tmp_path):
    calls = []
    (tmp_path / "tokenizer_config.json").write_text(json.dumps({"tokenizer_class": "TokenizersBackend"}))
    class Tokenizer:
        @classmethod
        def from_pretrained(cls, path, **kwargs):
            calls.append(("tokenizer", path, kwargs))
            return "tokenizer"
    class Model:
        config = SimpleNamespace(id2label={0: "bearish", 1: "neutral", 2: "bullish"})
        @classmethod
        def from_pretrained(cls, path, **kwargs):
            calls.append(("model", path, kwargs))
            return cls()
        def to(self, device):
            assert device == "cpu"
            return self
        def eval(self):
            return self
    class NoAutoTokenizer:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            pytest.fail("V5 TokenizersBackend needs the standard local fast-tokenizer fallback")
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(
        AutoTokenizer=NoAutoTokenizer, PreTrainedTokenizerFast=Tokenizer, AutoModelForSequenceClassification=Model))
    monkeypatch.setattr(lab, "_local_snapshot", lambda spec: tmp_path)
    lab._load_model.cache_clear()
    try:
        tokenizer, model, labels = lab._load_model("finsense")
        assert tokenizer == "tokenizer" and labels == {0: "negative", 1: "neutral", 2: "positive"}
        assert all(call[2]["local_files_only"] is True and call[2]["trust_remote_code"] is False for call in calls)
        assert calls[1][2]["use_safetensors"] is True
    finally:
        lab._load_model.cache_clear()


def test_explicit_annotations_evaluate_only_scored_rows(news):
    preview = lab.benchmark("AAPL")
    row = preview["rows"][0]
    annotation = {"sample_id": row["sample_id"], "text_sha256": row["text_sha256"], "label": row["predictions"]["vader"]["label"]}
    result = lab.benchmark("AAPL", labels=[annotation])
    assert result["evaluation"]["status"] == "evaluated"
    assert result["evaluation"]["models"]["vader"]["accuracy"] == 1
    assert result["evaluation"]["models"]["vader"]["all_three_classes_present"] is False
    assert result["evaluation"]["models"]["finsense"]["status"] == "not_evaluated"
    assert result["evaluation"]["annotations"] == [annotation]


def test_stale_and_duplicate_annotations_rejected_before_loading(news, monkeypatch):
    row = lab.benchmark("AAPL")["rows"][0]
    annotation = {"sample_id": row["sample_id"], "text_sha256": "0" * 64, "label": "positive"}
    monkeypatch.setattr(lab, "_load_model", lambda key: pytest.fail("Bad labels must fail before loading models"))
    with pytest.raises(ValueError, match="current sample"):
        lab.benchmark("AAPL", compare=True, labels=[annotation])
    annotation["text_sha256"] = row["text_sha256"]
    with pytest.raises(ValueError):
        lab.benchmark("AAPL", labels=[annotation, annotation])


def test_transformer_reports_truncation_and_batch_latency_without_confidence_claim(monkeypatch, caplog):
    caplog.set_level("INFO", logger="stockscope.usage")
    calls = []
    class Tokenizer:
        def encode(self, text, **kwargs):
            return list(range(200 if text == "long" else 3))
        def __call__(self, texts, **kwargs):
            calls.append((texts, kwargs))
            return {"input_ids": texts, "attention_mask": SimpleNamespace(sum=lambda: SimpleNamespace(item=lambda: 131))}
    model = lambda **kwargs: SimpleNamespace(logits="logits")
    values = SimpleNamespace(tolist=lambda: [[0.1, 0.2, 0.7], [0.8, 0.1, 0.1]])
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(
        inference_mode=nullcontext, softmax=lambda logits, dim: values))
    results = lab._transformer_batch(lab.CHALLENGERS[0], ["long", "short"],
                                    (Tokenizer(), model, {0: "negative", 1: "neutral", 2: "positive"}))
    assert [row["label"] for row in results] == ["positive", "negative"]
    assert results[0]["token_truncated"] and not results[1]["token_truncated"]
    assert results[0]["max_tokens"] == 128 and results[0]["input_tokens"] == 200
    assert results[0]["batch_size"] == 2 and results[0]["batch_latency_ms"] >= 0
    assert "uncalibrated" in results[0]["score_kind"]
    assert calls[0][1]["truncation"] is True and calls[0][1]["max_length"] == 128
    import json
    event = json.loads(next(record.message for record in caplog.records if record.name == 'stockscope.usage'))
    assert event['event'] == 'local_model_usage'
    assert event['input_tokens'] == 203
    assert event['processed_tokens'] == 131
    assert event['truncated_inputs'] == 1
    assert 'long' not in event and 'short' not in event


def test_cached_challengers_batch_bounded_inputs_and_never_set_accuracy_without_labels(news, monkeypatch):
    news[:] = [{**news[0], "title": f"English saved headline {index}", "url": f"https://example.test/{index}"} for index in range(9)]
    monkeypatch.setattr(lab, "model_status", lambda spec: {"key": spec.key, "status": "cached"})
    monkeypatch.setattr(lab, "_load_model", lambda key: None)
    batches = []
    def batch(spec, texts, loaded):
        batches.append(len(texts))
        return [{"status": "scored", "label": "positive", "score": 0.5} for text in texts]
    monkeypatch.setattr(lab, "_transformer_batch", batch)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(get_num_threads=lambda: 8, set_num_threads=lambda number: None))
    result = lab.benchmark("AAPL", compare=True)
    assert batches == [4, 4, 1, 4, 4, 1]
    assert all(model["status"] == "compared" and model["inference_latency_ms"] >= 0 for model in result["challengers"])
    assert result["evaluation"]["status"] == "not_evaluated"


def test_comparison_lock_returns_busy_instead_of_queuing_cpu_work(news):
    lab._comparison_lock.acquire()
    try:
        with pytest.raises(lab.BenchmarkBusy):
            lab.benchmark("AAPL", compare=True)
        assert lab.benchmark("AAPL")["sample"]["returned"] == 1
    finally:
        lab._comparison_lock.release()


def test_authenticated_preview_template_and_limits(api):
    assert api.get("/api/sentiment-lab/AAPL").status_code == 200
    assert api.get("/api/sentiment-lab/AAPL/labels").json()["labels"][0]["label"] is None
    assert api.get("/api/sentiment-lab/AAPL?limit=31").status_code == 422
    assert api.get("/api/sentiment-lab/AAPL!").status_code == 422
    assert api.post("/api/sentiment-lab/AAPL/evaluate", json={"labels": [{"label": "neutral"}]}).status_code == 422


def test_api_accepts_explicit_reference_label_and_rejects_changed_sample(api):
    row = api.get("/api/sentiment-lab/AAPL").json()["rows"][0]
    annotation = {"sample_id": row["sample_id"], "text_sha256": row["text_sha256"], "label": "positive"}
    response = api.post("/api/sentiment-lab/AAPL/evaluate", json={"labels": [annotation]})
    assert response.status_code == 200
    result = response.json()
    assert result["evaluation"]["annotation_count"] == 1
    assert result["evaluation"]["annotations"] == [annotation]
    assert result["evaluation"]["models"]["vader"]["evaluated_count"] == 1
    annotation["text_sha256"] = "0" * 64
    assert api.post("/api/sentiment-lab/AAPL/evaluate", json={"labels": [annotation]}).status_code == 422


def test_router_requires_auth_before_reading_saved_news(news, monkeypatch):
    app = FastAPI()
    app.include_router(sentiment_lab.router, prefix="/api/sentiment-lab")
    monkeypatch.setattr(lab, "saved_news", lambda *args: pytest.fail("Must authenticate before reading saved news"))
    with TestClient(app) as client:
        assert client.get("/api/sentiment-lab/AAPL").status_code == 401
        assert client.get("/api/sentiment-lab/AAPL/labels").status_code == 401
        assert client.post("/api/sentiment-lab/AAPL/evaluate", json={"labels": []}).status_code == 401


def test_comparison_runs_off_event_loop(api, monkeypatch):
    threads = []
    async def user():
        threads.append(threading.get_ident())
        return "demo"
    api.app.dependency_overrides[verify_password_with_role] = user
    def benchmark(*args):
        threads.append(threading.get_ident())
        return {"sample": {"returned": 0}}
    monkeypatch.setattr(sentiment_lab, "benchmark", benchmark)
    assert api.get("/api/sentiment-lab/AAPL?compare=true").status_code == 200
    assert len(threads) == 2 and threads[0] != threads[1]
