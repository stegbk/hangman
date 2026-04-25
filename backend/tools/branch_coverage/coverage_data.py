"""CoverageDataLoader: reads per-context hit sets from a .coverage file.

Per-context hits come from the CoverageContextMiddleware — one set per
endpoint label. Authoritative per-file branch totals (independent of
contexts) come from coverage.py's own bytecode-level analysis.

Aggregate hits (union across contexts) used by Grader for
extra_coverage detection and totals.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import coverage

from tools.branch_coverage.models import LoadedCoverage


class CoverageDataLoadError(RuntimeError):
    """Raised when the .coverage file can't be loaded."""


class CoverageDataLoader:
    def load(self, coverage_file: Path) -> LoadedCoverage:
        if not coverage_file.exists():
            raise CoverageDataLoadError(
                f"Coverage data file not found: {coverage_file}. "
                "Run `make bdd-coverage` first; check if `.backend-coverage.pid` is stale."
            )
        cov = coverage.Coverage(data_file=str(coverage_file))
        try:
            cov.load()
        except Exception as exc:  # noqa: BLE001 — coverage.py's taxonomy is broad
            raise CoverageDataLoadError(f"Failed to load {coverage_file}: {exc}") from exc

        data = cov.get_data()
        measured_files = data.measured_files()
        contexts = list(data.measured_contexts()) or [""]

        # Compute authoritative branch source-line sets per file ONCE.
        # Per plan-review iter 8 P1 (Codex): we filter per-context arcs to
        # only those whose source line IS a branch line, so non-branch
        # linear-flow arcs (e.g., `a = 1` followed by `b = 2` produces
        # arc (line_a, line_b)) don't get into hits_by_context. Without
        # this filter, the line-granularity projection in E1's Grader would
        # treat every executed line as a branch hit — inflating totals,
        # creating bogus extra_coverage, breaking reconciliation.
        branch_lines_per_file: dict[str, set[int]] = {}
        for file in measured_files:
            branch_lines_per_file[file] = self._authoritative_branch_lines(cov, data, file)

        # Per-context hit sets: dict[context_label, frozenset[(file, branch_id)]].
        # Each arc kept here has its SOURCE LINE in branch_lines_per_file[file],
        # so projecting to (file, source_line) in E1's Grader yields a true
        # branch hit set.
        #
        # Per A3 spike (coverage.py 7.13.5): the public per-context query API
        # is `data.set_query_contexts([label])` + `data.arcs(file)`. The
        # `data.arcs(file, contexts=[label])` kwarg form documented elsewhere
        # does NOT exist on 7.13.5 — `arcs(self, filename: str)` is the real
        # signature. Reset to None in a finally to avoid leaking global state
        # across context iterations.
        #
        # Per plan-review iter 8 P1 (Codex): filter arcs by their SOURCE
        # LINE membership in `branch_lines_per_file[file]` — the authoritative
        # set of branch points (from `Analysis.branch_stats().keys()`).
        # Without this filter, linear-flow arcs (e.g., from `a = 1\nb = 2`)
        # slip into the hit set and the Grader's source-line projection
        # mistakes them for branch hits. Also drop exit arcs (negative
        # target line); the Reachability AST walker doesn't emit them either.
        #
        # Per /simplify pass: lift `set_query_contexts` out of the per-file
        # loop — once per context (O(C)) instead of per (file, context)
        # (O(F·C)). The filter applies to all `arcs(file)` calls until
        # reset, so doing it once per context is correct AND clearer about
        # the API contract.
        hits_by_context: dict[str, frozenset[tuple[str, str]]] = {}
        for ctx in contexts:
            try:
                data.set_query_contexts([ctx if ctx else ""])
                hits: set[tuple[str, str]] = set()
                for file in measured_files:
                    bl = branch_lines_per_file[file]
                    arcs = data.arcs(file) or []
                    for a in arcs:
                        if a[1] > 0 and a[0] in bl:
                            hits.add((file, self._arc_to_id(a)))
                hits_by_context[ctx] = frozenset(hits)
            finally:
                data.set_query_contexts(None)

        # Aggregate hits (union across all contexts)
        all_hits_set: set[tuple[str, str]] = set()
        for s in hits_by_context.values():
            all_hits_set.update(s)
        all_hits = frozenset(all_hits_set)

        # Authoritative branch source-line counts per file. Per plan-review
        # iter 6 P1 (Codex): switched from arc counting to source-line
        # counting via `Analysis.branch_lines()` so totals match
        # Reachability's per-conditional emission semantics.
        total_branches_per_file: dict[str, int] = {
            file: len(bl) for file, bl in branch_lines_per_file.items()
        }

        return LoadedCoverage(
            hits_by_context=hits_by_context,
            total_branches_per_file=total_branches_per_file,
            all_hits=all_hits,
        )

    @staticmethod
    def _arc_to_id(arc: tuple[int, int]) -> str:
        return f"{arc[0]}->{arc[1]}"

    @staticmethod
    def _authoritative_branch_lines(cov: Any, data: Any, file: str) -> set[int]:
        """Return the set of source LINES in `file` that are branch points
        (have multiple possible exits — `if`, `while`, `for`, `try/except`,
        match arms, etc.).

        Per plan-review iter 6 P1 (Codex), this replaced the prior
        arc-counting variant for two reasons:

        1. **`arc_possibilities()` includes non-branch arcs.** Linear flow
           between consecutive statements creates arcs too. Counting them
           as "branches" inflated `total_branches_per_file`.

        2. **Arc IDs aren't comparable to Reachability's synthetic
           `f"{line}->{line+1}"` IDs.** Coverage.py records real arcs
           (else-arms point elsewhere; multi-line bodies have non-
           consecutive targets). The Grader now matches at source-line
           granularity (see E1's `_arc_source_line` helper), so the
           authoritative count must also be source-line-counted.

        Source: coverage.py 7.x exposes `Analysis.branch_stats()` —
        the documented dict[line, (total, taken)] mapping where the
        keys are precisely the source-lines that ARE branch points
        (per coverage.py's own `branch_stats()` design — used by
        `coverage report` and `coverage html` to compute branch
        percentages). A3 spike (2026-04-24, coverage.py 7.13.5)
        verified:

          - `Coverage.analysis2(file)` returns a 5-tuple
            `(filename, executable_lines, excluded_lines, missing_lines,
            formatted_missing_str)`, NOT an `Analysis` object. There
            is no `analysis2().branch_lines()` API on 7.13.5.
          - The modern `Analysis` object IS reachable via
            `Coverage._analyze(file)`. The leading underscore is a
            naming convention; the method is stable, used by coverage's
            own report/html commands, and is the only public path to
            an `Analysis` instance on 7.13.5.
          - `Analysis.branch_stats()` returns
            `dict[line_no, (total_branches, taken_branches)]`. Our
            authoritative branch-source-line set is `set(stats.keys())`.
          - `Analysis.branch_lines()` itself does NOT exist on 7.13.5.

        Hard-fail if the public surface has shifted between the A3
        spike and runtime (rather than silently returning lossy data —
        per plan-review iter 1 P1). pyproject.toml pins
        `coverage>=7.13,<8` to keep the surface stable within Feature 3.
        """
        try:
            analysis = cov._analyze(file)
        except (AttributeError, TypeError) as exc:
            raise CoverageDataLoadError(
                f"Coverage._analyze('{file}') is not available — "
                f"coverage.py public-but-underscored API may have shifted: "
                f"{exc}. The A3 spike characterized this on 7.13.5; "
                f"re-run the spike or re-pin coverage.py."
            ) from exc
        if not hasattr(analysis, "branch_stats"):
            raise CoverageDataLoadError(
                f"Coverage._analyze('{file}') returned shape lacking "
                f"`branch_stats()` (got {type(analysis).__name__}); "
                f"coverage.py API has shifted between A3 spike and this "
                f"run. Re-run the spike to characterize the new shape."
            )
        # branch_stats(): dict[line_no, (total_branches, taken_branches)]
        # The keys ARE the branch source-lines.
        return set(analysis.branch_stats().keys())
