#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run python -m tools.check_no_comments
uv run python -m tools.check_lookahead
uv run pytest
echo "verify: all checks passed"
