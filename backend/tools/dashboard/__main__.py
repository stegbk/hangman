"""CLI entrypoint: `python -m tools.dashboard --help`.

Defaults anchor off the module file location (Path(__file__).parents[3])
so the command works from repo root, from backend/, or from anywhere
else — not just when invoked from backend/.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from tools.dashboard.analyzer import Analyzer
from tools.dashboard.coverage import CoverageGrader
from tools.dashboard.history import HistoryStore
from tools.dashboard.llm.client import _RUBRIC_CACHE_MIN_TOKENS, LlmEvaluator
from tools.dashboard.llm.rubric import rubric_token_count
from tools.dashboard.packager import Packager
from tools.dashboard.parser import NdjsonParser
from tools.dashboard.renderer import DashboardRenderer

# backend/tools/dashboard/__main__.py → parents[3] = repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.dashboard")
    parser.add_argument(
        "--ndjson",
        default=_REPO_ROOT / "frontend" / "test-results" / "cucumber.ndjson",
        type=Path,
    )
    parser.add_argument(
        "--output",
        default=_REPO_ROOT / "tests" / "bdd" / "reports" / "dashboard.html",
        type=Path,
    )
    parser.add_argument("--history-dir", default=_REPO_ROOT / ".bdd-history", type=Path)
    parser.add_argument(
        "--features-dir",
        default=_REPO_ROOT / "frontend" / "tests" / "bdd" / "features",
        type=Path,
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-6",
        choices=["claude-sonnet-4-6", "claude-haiku-4-5", "claude-opus-4-7"],
    )
    parser.add_argument("--max-workers", default=6, type=int)
    args = parser.parse_args()

    # Presence-only check; let the Anthropic SDK validate the key format
    # on first call. Anthropic uses several prefixes (sk-ant-api03-...,
    # sk-ant-admin01-..., and may add more); locking to one would silently
    # reject valid keys after a future format change.
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "ERROR: ANTHROPIC_API_KEY env var is missing. Put it in .env "
            "(gitignored) or export it in your shell.",
            file=sys.stderr,
        )
        return 2

    token_count = rubric_token_count()
    if token_count < _RUBRIC_CACHE_MIN_TOKENS:
        print(
            f"ERROR: Rubric is {token_count} tokens — below "
            f"{_RUBRIC_CACHE_MIN_TOKENS}-token cache floor "
            "(caching stops paying off below this).",
            file=sys.stderr,
        )
        return 3

    analyzer = Analyzer(
        parser=NdjsonParser(),
        grader=CoverageGrader(),
        packager=Packager(),
        llm=LlmEvaluator(model=args.model, max_workers=args.max_workers),
        history=HistoryStore(),
        renderer=DashboardRenderer(),
    )
    analyzer.run(
        ndjson_path=args.ndjson,
        output_path=args.output,
        history_dir=args.history_dir,
        features_glob=args.features_dir,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
