#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

echo "Checking formatting..."
uv run ruff format --check .

echo "Running Ruff..."
uv run ruff check .

echo "Running mypy..."
uv run mypy src

echo "Running Bandit..."
uv run bandit --recursive src --severity-level all

echo "Running tests..."
uv run pytest

echo "All checks passed."
