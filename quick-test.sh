#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
exec venv/bin/python automated_smoke_test.py "$@"
