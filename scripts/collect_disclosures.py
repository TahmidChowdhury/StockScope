"""Run one due disclosure collection and exit; suitable for an external cron.

Use --force to bypass the persisted due time, never the active-worker lease.
The same configuration and durable storage are shared with the API scheduler.
"""
import argparse
import json

from dotenv import load_dotenv


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Refresh now even if the next scheduled check is not due")
    args = parser.parse_args(argv)
    load_dotenv()
    from backend.services import research
    from backend.trading import disclosure_collector
    repository = None
    try:
        repository = research.repository()
        if repository is not None:
            repository.check_ready()
        result = disclosure_collector.collect(force=args.force)
        print(json.dumps(result, allow_nan=False))
        return 1 if result["state"] in {"failed", "interrupted"} else 0
    except Exception as exc:
        print(json.dumps({"state": "failed", "error_type": type(exc).__name__,
                          "message": "Collection could not access configured storage. No fallback storage was used."}))
        return 1
    finally:
        if repository is not None:
            repository.engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
