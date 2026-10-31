"""Read-only, local sentiment research. Never changes saved production scores.

The API may only use these exact cached model revisions. Downloading weights is
an explicit environment setup step, never an effect of reading saved news.
"""

import hashlib
import importlib.metadata
import json
import math
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from backend.services.research import normalized_symbol, saved_news

LABELS = ("negative", "neutral", "positive")
MAX_SAMPLE = 30
MAX_TEXT_CHARS = 6000
_comparison_lock = threading.Lock()


@dataclass(frozen=True)
class ModelSpec:
    key: str
    model_id: str
    revision: str
    license: str
    provenance: str
    caveat: str
    max_tokens: int

    @property
    def source_url(self):
        return f"https://huggingface.co/{self.model_id}/tree/{self.revision}"


CHALLENGERS = (
    ModelSpec("finsense", "AnkitAI/FinSense-ModernBERT-Financial-News-Sentiment-Analysis",
              "921d56cd002e2074c02f0440ef5d9b68bcc084aa", "Apache-2.0 (author-declared weights)",
              "ModernBERT-base fine-tuned on Financial PhraseBank; published held-out split.",
              "Financial PhraseBank has noncommercial terms. Commercial rights are not cleared. News sentence model, not a return predictor.", 128),
    ModelSpec("modernfinbert", "tabularisai/ModernFinBERT",
              "6c6de8332ea7f6824c0f8917358dce1e669c1710", "Apache-2.0 (author-declared weights)",
              "ModernBERT-base; author describes synthetic and real financial training text.",
              "Named training sources and split methodology are not disclosed. Independent StockScope accuracy is not evaluated.", 256),
)


class BenchmarkBusy(RuntimeError):
    pass


def package_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _local_snapshot(spec):
    """Hub cache lookup is explicitly offline, even when network is available."""
    from huggingface_hub import snapshot_download
    return Path(snapshot_download(repo_id=spec.model_id, revision=spec.revision,
                                 cache_dir=os.getenv("STOCKSCOPE_HF_CACHE") or str(Path(__file__).resolve().parents[2] / ".cache" / "huggingface"),
                                 local_files_only=True))


def model_status(spec):
    result = {**asdict(spec), "source_url": spec.source_url, "research_only": True,
              "status": "not_installed", "message": "Install optional sentiment dependencies to use cached challengers."}
    if not all(package_version(name) for name in ("torch", "transformers", "huggingface-hub", "safetensors")):
        return result
    try:
        path = _local_snapshot(spec)
        if not (path / "model.safetensors").is_file():
            raise FileNotFoundError("Safetensors weights missing")
        result.update(status="cached", message="Pinned local weights available; comparison has not run.")
    except Exception:
        result.update(status="not_cached", message="Pinned weights are not in the local cache. This request will not download them.")
    return result


def _language(text, declared=None):
    if not text.strip():
        return "empty_text", None
    if declared:
        language = str(declared).strip().lower().replace("_", "-").split("-")[0]
        return ("eligible" if language in {"en", "eng", "english"} else "unsupported_language"), language
    try:
        from langdetect import DetectorFactory, detect_langs
        DetectorFactory.seed = 0
        probabilities = detect_langs(text)
        if not probabilities or probabilities[0].prob < 0.85:
            return "unknown_language", None
        language = probabilities[0].lang
        return ("eligible" if language == "en" else "unsupported_language"), language
    except Exception:
        return "unknown_language", None


def sample_news(symbol, limit=12):
    symbol = normalized_symbol(symbol)
    if not 1 <= limit <= MAX_SAMPLE:
        raise ValueError(f"Sample size must be between 1 and {MAX_SAMPLE}")
    rows = []
    for record in saved_news(symbol, limit):
        title = record.get("title") if isinstance(record.get("title"), str) else ""
        description = record.get("description") if isinstance(record.get("description"), str) else ""
        title, description = title.strip(), description.strip()
        if description == title:
            description = ""
        original_text = "\n".join(part for part in (title, description) if part)
        text = original_text[:MAX_TEXT_CHARS]
        status, language = _language(text, record.get("language") or record.get("lang"))
        if record.get("source_type") == "company_release":
            status = "company_release_excluded"
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        identity = f"{symbol}\0{record.get('url') or ''}\0{title}"
        rows.append({"sample_id": hashlib.sha256(identity.encode()).hexdigest()[:24],
                     "text_sha256": text_hash, "title": title, "description": description[:MAX_TEXT_CHARS],
                     "text": text, "url": record.get("url"), "source": record.get("source"),
                     "published_at": record.get("publishedAt"), "language": language, "status": status,
                     "coverage": "title+description" if title and description else "title" if title else "description" if description else "empty",
                     "input_characters": len(original_text), "character_truncated": len(original_text) > len(text),
                     "predictions": {}})
    return rows


def _vader(text):
    from sentiment.analyzer import analyze_sentiment
    started = time.perf_counter()
    scores = analyze_sentiment(text)
    compound = float(scores["compound"])
    return {"status": "scored", "label": "positive" if compound >= 0.05 else "negative" if compound <= -0.05 else "neutral",
            "score": compound, "probabilities": None, "score_kind": "VADER compound, not probability",
            "latency_ms": round((time.perf_counter() - started) * 1000, 3), "token_truncated": False}


@lru_cache(maxsize=2)
def _load_model(key):
    spec = next(item for item in CHALLENGERS if item.key == key)
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, PreTrainedTokenizerFast
    path = str(_local_snapshot(spec))
    tokenizer_config = json.loads((Path(path) / "tokenizer_config.json").read_text())
    # FinSense stores a Transformers 5 tokenizer class; its standard tokenizer
    # JSON also works with the supported Python 3.9 / Transformers 4 runtime.
    tokenizer_class = PreTrainedTokenizerFast if tokenizer_config.get("tokenizer_class") == "TokenizersBackend" else AutoTokenizer
    tokenizer = tokenizer_class.from_pretrained(path, local_files_only=True, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        path, local_files_only=True, trust_remote_code=False, use_safetensors=True,
        attn_implementation="eager")
    model.to("cpu").eval()
    aliases = {"bearish": "negative", "bullish": "positive"}
    labels = {int(key): aliases.get(str(value).lower(), str(value).lower()) for key, value in model.config.id2label.items()}
    if set(labels.values()) != set(LABELS):
        raise ValueError("Model must declare all three sentiment labels")
    return tokenizer, model, labels


def _transformer_batch(spec, texts, loaded):
    import torch
    tokenizer, model, labels = loaded
    started = time.perf_counter()
    token_counts = [len(tokenizer.encode(text, add_special_tokens=True, truncation=False)) for text in texts]
    inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=spec.max_tokens)
    with torch.inference_mode():
        batch_values = torch.softmax(model(**inputs).logits, dim=-1).tolist()
    elapsed = round((time.perf_counter() - started) * 1000, 3)
    results = []
    for values, token_count in zip(batch_values, token_counts):
        probabilities = {labels[index]: float(value) for index, value in enumerate(values)}
        if not all(math.isfinite(value) and 0 <= value <= 1 for value in probabilities.values()):
            raise ValueError("Invalid model probabilities")
        label = max(probabilities, key=probabilities.get)
        results.append({"status": "scored", "label": label, "score": probabilities["positive"] - probabilities["negative"],
                        "probabilities": probabilities, "score_kind": "positive minus negative softmax (uncalibrated)",
                        "batch_latency_ms": elapsed, "batch_size": len(texts),
                        "input_tokens": token_count, "max_tokens": spec.max_tokens, "token_truncated": token_count > spec.max_tokens})
    from backend.core.resources import usage_event
    usage_event('local_model_usage', model=spec.key, batch_size=len(texts),
                input_tokens=sum(token_counts), processed_tokens=int(inputs['attention_mask'].sum().item()),
                truncated_inputs=sum(count > spec.max_tokens for count in token_counts), latency_ms=elapsed)
    return results


def evaluation_metrics(rows, labels):
    """Labels are caller-supplied annotations, never model-generated truth."""
    current = {row["sample_id"]: row for row in rows}
    truth = {}
    for annotation in labels:
        key = annotation.get("sample_id")
        row = current.get(key)
        if key in truth or row is None or annotation.get("text_sha256") != row["text_sha256"]:
            raise ValueError("Annotations must uniquely match the current sample and text hash")
        if annotation.get("label") not in LABELS:
            raise ValueError("Each supplied annotation needs an explicit positive, neutral, or negative label")
        truth[key] = annotation["label"]
    metrics = {}
    for model in ("vader", *(spec.key for spec in CHALLENGERS)):
        pairs = [(truth[row["sample_id"]], row["predictions"][model]["label"]) for row in rows
                 if row["sample_id"] in truth and row["predictions"][model].get("status") == "scored"]
        if not pairs:
            metrics[model] = {"status": "not_evaluated", "evaluated_count": 0}
            continue
        confusion = {actual: {predicted: 0 for predicted in LABELS} for actual in LABELS}
        for actual, predicted in pairs:
            confusion[actual][predicted] += 1
        f1 = []
        for label in LABELS:
            tp = confusion[label][label]
            fp = sum(confusion[other][label] for other in LABELS if other != label)
            fn = sum(confusion[label][other] for other in LABELS if other != label)
            f1.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0)
        metrics[model] = {"status": "evaluated", "evaluated_count": len(pairs),
                          "accuracy": sum(actual == predicted for actual, predicted in pairs) / len(pairs),
                          "macro_f1": sum(f1) / len(LABELS), "confusion_matrix": confusion,
                          "all_three_classes_present": set(actual for actual, _ in pairs) == set(LABELS)}
    return {"status": "evaluated" if truth else "not_evaluated", "annotation_count": len(truth),
            "label_source": "Explicit caller-supplied annotations; not independently verified.",
            "annotations": [{"sample_id": key, "text_sha256": current[key]["text_sha256"], "label": label}
                            for key, label in truth.items()],
            "metric_policy": "Macro-F1 uses all three fixed classes; absent classes contribute zero. Small self-labelled samples do not establish generalization.",
            "models": metrics}


def benchmark(symbol, limit=12, compare=False, labels=None):
    if compare and not _comparison_lock.acquire(blocking=False):
        raise BenchmarkBusy("Another local sentiment comparison is running. Try again shortly.")
    try:
        started = time.perf_counter()
        rows = sample_news(symbol, limit)
        statuses = [model_status(spec) for spec in CHALLENGERS]
        for row in rows:
            eligible = row["status"] == "eligible"
            row["predictions"]["vader"] = _vader(row["text"]) if eligible else {"status": row["status"], "label": None}
            for spec in CHALLENGERS:
                row["predictions"][spec.key] = {"status": "not_run" if eligible else row["status"], "label": None}
        if labels:
            # Reject stale/invalid annotations before loading or running models.
            evaluation_metrics(rows, labels)
        if compare:
            for spec, status in zip(CHALLENGERS, statuses):
                eligible_rows = [row for row in rows if row["status"] == "eligible"]
                if status["status"] != "cached" or not eligible_rows:
                    for row in eligible_rows:
                        row["predictions"][spec.key]["status"] = status["status"]
                    continue
                load_started = time.perf_counter()
                try:
                    import torch
                    # The research worker must leave CPU capacity for normal app requests.
                    torch.set_num_threads(min(torch.get_num_threads(), 2))
                    loaded = _load_model(spec.key)
                    status["load_latency_ms"] = round((time.perf_counter() - load_started) * 1000, 3)
                    inference_started = time.perf_counter()
                    for offset in range(0, len(eligible_rows), 4):
                        batch = eligible_rows[offset:offset + 4]
                        predictions = _transformer_batch(spec, [row["text"] for row in batch], loaded)
                        for row, prediction in zip(batch, predictions):
                            row["predictions"][spec.key] = prediction
                    status["inference_latency_ms"] = round((time.perf_counter() - inference_started) * 1000, 3)
                    status.update(status="compared", message="Local comparison completed. Accuracy has not been established.")
                except Exception:
                    status.update(status="unavailable", message="Cached model could not run. Check optional runtime and pinned cache files.")
                    for row in eligible_rows:
                        row["predictions"][spec.key] = {"status": "unavailable", "label": None}
        counts = {status: sum(row["status"] == status for row in rows) for status in
                  ("eligible", "empty_text", "unknown_language", "unsupported_language", "company_release_excluded")}
        return {"symbol": normalized_symbol(symbol), "generated_at": datetime.now(timezone.utc).isoformat(),
                "research_only": True, "production_model": "vader", "saved_scores_changed": False,
                "text_scope": "Saved title + description only; no full article bodies or new source collection.",
                "language_policy": "English only; language detection can be wrong. Unknown/unsupported text stays unscored.",
                "sample": {"requested": limit, "returned": len(rows), **counts},
                "baseline": {"key": "vader", "model_id": "vaderSentiment", "revision": package_version("vaderSentiment"),
                             "license": "MIT", "source_url": "https://github.com/cjhutto/vaderSentiment", "production_baseline": True},
                "challengers": statuses, "rows": rows,
                "evaluation": evaluation_metrics(rows, labels or []),
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3)}
    finally:
        if compare:
            _comparison_lock.release()


def label_template(symbol, limit=12):
    rows = sample_news(symbol, limit)
    return {"symbol": normalized_symbol(symbol), "limit": limit,
            "instructions": "Supply your own company-relevant tone labels. Leave uncertain or mixed rows unlabelled; submit only explicit labels. Tone is not a price forecast.",
            "allowed_labels": list(LABELS), "text_scope": "Saved title + description only",
            "labels": [{key: row[key] for key in ("sample_id", "text_sha256", "title", "text", "url", "status")} | {"label": None}
                       for row in rows]}
