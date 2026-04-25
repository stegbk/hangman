"""ASGI entrypoint used ONLY by instrumented runs via
`coverage run -m tools.branch_coverage.serve --host ... --port ...`.

Imports the Hangman FastAPI app, adds CoverageContextMiddleware, and
runs uvicorn single-worker.

Production runs continue to invoke `uvicorn hangman.main:app` directly
(unchanged) — this module is dev tooling only.
"""

from __future__ import annotations

import argparse

import uvicorn

from hangman.main import app
from tools.branch_coverage.middleware import CoverageContextMiddleware

# Attach the middleware at import time. Safe to do repeatedly (idempotent
# in principle) but this module is normally imported once by
# `coverage run -m tools.branch_coverage.serve`.
app.add_middleware(CoverageContextMiddleware)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m tools.branch_coverage.serve")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()
    # workers=1 is load-bearing: switch_context is process-global; a
    # multi-worker config would silently corrupt per-endpoint attribution.
    uvicorn.run(app, host=args.host, port=args.port, workers=1, log_level="info")


if __name__ == "__main__":
    main()
