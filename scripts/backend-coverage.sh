#!/bin/bash
# Wraps uvicorn under coverage.py for Feature 3's make bdd-coverage workflow.
# Writes the PID to .backend-coverage.pid so `make bdd-coverage` can SIGTERM it
# after running the BDD suite (coverage.py 7.13's sigterm=true flushes data).
set -e
cd "$(dirname "$0")/.."
echo "$$" > .backend-coverage.pid
trap 'rm -f .backend-coverage.pid' EXIT INT TERM
cd backend
exec uv run coverage run --branch --parallel-mode --source=src/hangman \
  --rcfile=tools/branch_coverage/.coveragerc \
  -m tools.branch_coverage.serve \
  --host 127.0.0.1 --port "${HANGMAN_BACKEND_PORT:-8000}"
