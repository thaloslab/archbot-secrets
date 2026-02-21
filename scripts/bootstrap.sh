#!/usr/bin/env bash
set -euo pipefail

if [[ -d ".venv" ]]; then
  echo "Local .venv is not allowed. Remove .venv and use Poetry-managed central environments."
  exit 1
fi

IN_PROJECT="$(poetry config virtualenvs.in-project 2>/dev/null || echo "")"
if [[ "$IN_PROJECT" == "true" ]]; then
  echo "Poetry is configured for in-project virtualenvs (virtualenvs.in-project=true)."
  echo "Set it to false in your local Poetry config before continuing."
  exit 1
fi

poetry install
ENV_PATH="$(poetry env info --path)"

echo "Bootstrap complete."
echo "Poetry environment: $ENV_PATH"
echo "Run commands with: poetry run <command>"
