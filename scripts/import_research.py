"""Inspect legacy snapshots; --apply imports the validated batch in one transaction.

Never edits or removes input files. Unsupported legacy social snapshots are skipped.
Does not print connection strings, raw research payloads, or exception details.
"""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from backend.db.repository import SUPPORTED_SUFFIXES, digest, validate_snapshot


def inspect_directory(directory):
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError("The research input directory does not exist")
    snapshots, manifest = [], []
    targets = set()
    skipped = 0
    for path in sorted(directory.glob("*.json")):
        matched = next((suffix for suffix in sorted(SUPPORTED_SUFFIXES) if path.name.endswith(f"_{suffix}.json")), None)
        if matched is None:
            skipped += 1
            continue
        symbol = path.name[:-len(f"_{matched}.json")]
        # Reject duplicate JSON keys and NaN/Infinity instead of silently rewriting evidence.
        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate JSON object key")
                result[key] = value
            return result
        records = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
        symbol = validate_snapshot(symbol, matched, records)
        if (symbol, matched) in targets:
            raise ValueError("Duplicate snapshot target after symbol normalization")
        targets.add((symbol, matched))
        snapshots.append((symbol, matched, records))
        manifest.append([symbol, matched, digest(records)])
    return snapshots, digest(manifest), {
        "files": len(snapshots), "records": sum(len(rows) for _, _, rows in snapshots), "skipped_files": skipped,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--apply", action="store_true", help="Write the complete validated batch to the configured, migrated PostgreSQL database")
    args = parser.parse_args(argv)
    try:
        snapshots, manifest_hash, counts = inspect_directory(args.data_dir)
        if not args.apply:
            print(json.dumps({"mode": "dry_run", **counts, "writes": 0}))
            return 0
        load_dotenv()
        from backend.db import get_repository
        repository = get_repository()
        if repository is None:
            raise ValueError("DATABASE_URL is required for --apply")
        repository.check_ready()
        result = repository.import_snapshots(snapshots, manifest_hash)
        print(json.dumps({"mode": "apply", **counts, **result}))
        return 0
    except Exception:
        print("Import failed; no partial batch was committed. Check input JSON, database configuration, and migrations.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
