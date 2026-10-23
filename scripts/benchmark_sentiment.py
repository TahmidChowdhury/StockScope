"""Compare cached sentiment models against saved news without modifying it.

python -m scripts.benchmark_sentiment AAPL --limit 12 --template /tmp/aapl-labels.json
python -m scripts.benchmark_sentiment AAPL --compare --labels /tmp/labels.json --output /tmp/report.json

No command downloads models. Blank template labels are omitted from evaluation.
"""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from backend.sentiment.lab import benchmark, label_template


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol")
    parser.add_argument("--limit", type=int, default=12, choices=range(1, 31))
    parser.add_argument("--compare", action="store_true", help="Run allowlisted models from local cache only")
    parser.add_argument("--template", type=Path, help="Export an unlabelled template and exit")
    parser.add_argument("--labels", type=Path, help="JSON template containing explicit annotations")
    parser.add_argument("--output", type=Path, help="Save report JSON instead of stdout")
    args = parser.parse_args()
    load_dotenv()
    if args.template:
        args.template.write_text(json.dumps(label_template(args.symbol, args.limit), indent=2))
        print(f"Unlabelled template saved to {args.template}")
        return
    labels = []
    if args.labels:
        payload = json.loads(args.labels.read_text())
        if payload.get("symbol") != args.symbol.upper() or payload.get("limit") != args.limit:
            parser.error("Label template symbol and limit must match this saved-news sample")
        labels = [item for item in payload.get("labels", []) if item.get("label") is not None]
    report = benchmark(args.symbol, args.limit, args.compare, labels)
    serialized = json.dumps(report, indent=2, allow_nan=False)
    if args.output:
        args.output.write_text(serialized)
        print(f"Read-only comparison saved to {args.output}")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
