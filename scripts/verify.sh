#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
ignored=$(git ls-files --cached --others --ignored --exclude-standard -- quant tools tests scripts | grep -v -e __pycache__ -e '\.pyc$' || true)
if [ -n "$ignored" ]; then echo "source files ignored by .gitignore:"; echo "$ignored"; exit 1; fi
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run python -m tools.check_no_comments
uv run python -m tools.check_lookahead
uv run pytest
echo "verify: all checks passed"
