"""Explicitly prepare pinned local research models; the app never downloads them.

python -m scripts.cache_sentiment_models                 # inspect candidates
python -m scripts.cache_sentiment_models --download      # populate local cache
python -m scripts.cache_sentiment_models --verify        # check cache, offline
python -m scripts.cache_sentiment_models --smoke-test    # check real CPU inference
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from backend.sentiment import lab

CHALLENGERS = lab.CHALLENGERS
REQUIRED_FILES = ("config.json", "tokenizer_config.json", "tokenizer.json", "model.safetensors")


def verify_snapshot(model, cache):
    """Fail closed on an incomplete/mismatched pinned local model snapshot."""
    from huggingface_hub import snapshot_download

    path = Path(snapshot_download(repo_id=model.model_id, revision=model.revision,
                                  cache_dir=str(cache), token=False, local_files_only=True))
    if path.name != model.revision:
        raise ValueError(f"{model.key}: snapshot does not match the pinned revision")
    for name in REQUIRED_FILES:
        file = path / name
        if not file.is_file() or file.stat().st_size == 0:
            raise ValueError(f"{model.key}: missing or empty {name}")
    config = json.loads((path / "config.json").read_text())
    aliases = {"bearish": "negative", "bullish": "positive"}
    labels = {aliases.get(str(value).lower(), str(value).lower())
              for value in config.get("id2label", {}).values()}
    if labels != set(lab.LABELS) or len(config["id2label"]) != 3:
        raise ValueError(f"{model.key}: expected the three declared sentiment labels")
    # All files used by the loader must be parseable without remote code.
    for name in ("tokenizer_config.json", "tokenizer.json"):
        json.loads((path / name).read_text())
    weight_mb = (path / "model.safetensors").stat().st_size / 1_000_000
    print(f"  Verified pinned local files; safetensors {weight_mb:.1f} MB", flush=True)
    return path


def smoke_test(model):
    """Exercise the actual offline loader, tokenizer, label map and CPU kernel."""
    import torch

    torch.set_num_threads(min(torch.get_num_threads(), 2))
    started = time.perf_counter()
    result = lab._transformer_batch(model, ["The company reported increased quarterly revenue."],
                                    lab._load_model(model.key))[0]
    if (result.get("status") != "scored" or result.get("label") not in lab.LABELS
            or set(result.get("probabilities", {})) != set(lab.LABELS)):
        raise ValueError(f"{model.key}: CPU inference smoke test failed")
    elapsed = time.perf_counter() - started
    print(f"  Offline CPU inference passed in {elapsed:.2f}s", flush=True)


def report_peak_memory():
    # Linux reports KiB; macOS reports bytes. This helps size the hosted service
    # after both real models have remained loaded in the same process as the API.
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mb = peak / (1024 * 1024 if sys.platform == "darwin" else 1024)
    print(f"Peak process resident memory: {peak_mb:.0f} MiB; allow additional RAM for the API and data jobs.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--verify", action="store_true", help="Verify only already-cached pinned files")
    parser.add_argument("--smoke-test", action="store_true", help="Verify cache and run one offline CPU input per model")
    parser.add_argument("--model", choices=[model.key for model in CHALLENGERS])
    args = parser.parse_args()
    candidates = [model for model in CHALLENGERS if args.model is None or model.key == args.model]
    cache = Path(os.getenv("STOCKSCOPE_HF_CACHE") or Path(__file__).resolve().parents[1] / ".cache" / "huggingface")
    for model in candidates:
        print(f"{model.key}: {model.model_id}@{model.revision}", flush=True)
        print(f"  {model.license}. {model.caveat}", flush=True)
        if args.download:
            from huggingface_hub import snapshot_download
            path = snapshot_download(
                repo_id=model.model_id, revision=model.revision, cache_dir=str(cache),
                token=False, max_workers=2,
                allow_patterns=["*.json", "*.safetensors", "README.md", "LICENSE*", "vocab.txt", "merges.txt"],
            )
            print(f"  Cached: {path}", flush=True)
        if args.verify or args.smoke_test:
            verify_snapshot(model, cache)
        if args.smoke_test:
            smoke_test(model)
    if args.smoke_test:
        report_peak_memory()
    if not (args.download or args.verify or args.smoke_test):
        print("No downloads requested. Use --download to prepare these research models.")


if __name__ == "__main__":
    main()
