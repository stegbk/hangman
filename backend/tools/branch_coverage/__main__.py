"""CLI entrypoint: ``python -m tools.branch_coverage``.

Defaults anchor off ``Path(__file__).resolve().parents[3]`` (repo root)
so the command works from any directory.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.branch_coverage.analyzer import Analyzer
from tools.branch_coverage.callgraph import CallGraphBuilder
from tools.branch_coverage.coverage_data import (
    CoverageDataLoader,
    CoverageDataLoadError,
)
from tools.branch_coverage.grader import Grader
from tools.branch_coverage.json_emitter import JsonEmitter
from tools.branch_coverage.reachability import Reachability
from tools.branch_coverage.renderer import DashboardRenderer
from tools.branch_coverage.routes import RouteEnumerator

# backend/tools/branch_coverage/__main__.py -> parents[3] = repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.branch_coverage")
    parser.add_argument(
        "--coverage-file",
        default=_REPO_ROOT / "backend" / ".coverage",
        type=Path,
    )
    parser.add_argument(
        "--source-root",
        default=_REPO_ROOT / "backend" / "src" / "hangman",
        type=Path,
    )
    parser.add_argument(
        "--json-output",
        default=_REPO_ROOT / "tests" / "bdd" / "reports" / "coverage.json",
        type=Path,
    )
    parser.add_argument(
        "--html-output",
        default=_REPO_ROOT / "tests" / "bdd" / "reports" / "coverage.html",
        type=Path,
    )
    args = parser.parse_args()

    # Import the hangman app reflectively (see design spec section 12 risk #2
    # for the side-effects audit — handled at import-time if needed).
    from hangman.main import app

    analyzer = Analyzer(
        routes=RouteEnumerator(),
        callgraph=CallGraphBuilder(),
        reachability=Reachability(),
        coverage_data=CoverageDataLoader(),
        grader=Grader(),
        json_emitter=JsonEmitter(),
        renderer=DashboardRenderer(),
    )
    try:
        analyzer.run(
            app=app,
            coverage_file=args.coverage_file,
            source_root=args.source_root,
            json_output=args.json_output,
            html_output=args.html_output,
        )
    except CoverageDataLoadError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR (unexpected): {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
