"""Grader: per-endpoint context intersection + audit reconciliation.

For each endpoint E:
  covered_E = (branches reachable from E) ∩ (hits under E's context)

Audit reconciliation dedupes branches across endpoints: a shared helper
reachable from N endpoints is counted ONCE in the audit enumeration
(to match coverage.py's authoritative per-file branch count).
"""

from __future__ import annotations

from collections import defaultdict

from tools.branch_coverage.models import (
    AuditReport,
    CoveragePerEndpoint,
    CoverageReport,
    Endpoint,
    ExtraCoverage,
    FunctionCoverage,
    LoadedCoverage,
    ReachableBranch,
    Tone,
    Totals,
    UnattributedBranch,
)

_RED_THRESHOLD = 50.0
_YELLOW_THRESHOLD = 80.0
_THRESHOLDS = {"red": _RED_THRESHOLD, "yellow": _YELLOW_THRESHOLD}


def _tone(pct: float, total: int) -> Tone:
    if total == 0:
        return Tone.NA
    if pct < _RED_THRESHOLD:
        return Tone.ERROR
    if pct < _YELLOW_THRESHOLD:
        return Tone.WARNING
    return Tone.SUCCESS


def _arc_source_line(branch_id: str) -> int:
    """Extract the source line from an arc-id like '10->11' or '10->-1'.

    Per plan-review iter 6 P1 (Codex): Reachability emits synthetic
    `f"{line}->{line+1}"` IDs while coverage.py emits real arc IDs from
    bytecode (else-arms point to non-consecutive lines, exception arcs
    target handler lines, etc.). Direct equality on `(file, branch_id)`
    misses every match where the targets differ. Projection to source
    line `(file, src_line)` gives line-granularity matching that is
    robust to representational differences — coverage.py's
    `Analysis.branch_lines()` is also source-line-keyed, so the audit
    invariant stays consistent.

    Defensive: if the format ever changes (e.g. coverage.py emits a
    bare line as `"10"` rather than `"10->11"`), fall through to int().
    """
    return int(branch_id.split("->", 1)[0])


class Grader:
    def grade(
        self,
        reachability: dict[Endpoint, list[ReachableBranch]],
        hits: LoadedCoverage,
    ) -> CoverageReport:
        endpoints_cov = [
            self._grade_endpoint(ep, branches, hits) for ep, branches in reachability.items()
        ]
        endpoints_cov.sort(key=lambda c: (c.endpoint.path, c.endpoint.method))

        # Deduped reachable enumeration as (file, source_line) tuples
        # across all endpoints. Per iter 6 P1: line-granularity matches
        # both coverage.py's `branch_lines()` semantics and the per-
        # endpoint intersection in `_grade_endpoint`. Multiple
        # ReachableBranches at the same (file, line) collapse to one entry
        # — that's correct because Reachability emits one branch per
        # conditional and coverage.py counts one branch-line per
        # conditional.
        enumerated_reachable_lines: set[tuple[str, int]] = set()
        for branches in reachability.values():
            for b in branches:
                enumerated_reachable_lines.add((b.file, b.line))

        # Per plan-review iter 7 P1 (Codex): extra_coverage MUST be derived
        # from the same line-granularity primitive as _audit, otherwise
        # intra-file unlinked hits (e.g., a Depends-injected helper in a
        # file that ALSO has endpoint-reachable branches) get silently
        # dropped from extra_coverage even though the audit counts them.
        extra_coverage = self._extra_coverage(enumerated_reachable_lines, hits)

        audit = self._audit(enumerated_reachable_lines, hits)
        totals = self._totals(hits)

        return CoverageReport(
            version=1,
            timestamp=self._timestamp(),
            cucumber_ndjson="frontend/test-results/cucumber.coverage.ndjson",
            instrumented=True,
            thresholds=_THRESHOLDS,
            totals=totals,
            endpoints=tuple(endpoints_cov),
            extra_coverage=tuple(extra_coverage),
            audit=audit,
        )

    def _grade_endpoint(
        self,
        endpoint: Endpoint,
        branches: list[ReachableBranch],
        hits: LoadedCoverage,
    ) -> CoveragePerEndpoint:
        context_label = f"{endpoint.method} {endpoint.path}"
        context_hits = hits.hits_by_context.get(context_label, frozenset())
        # Per plan-review iter 6 P1 (Codex): project context_hits to
        # (file, source_line). See `_arc_source_line` docstring.
        hit_source_lines = {(f, _arc_source_line(bid)) for (f, bid) in context_hits}
        total = len(branches)
        covered_set = {b for b in branches if (b.file, b.line) in hit_source_lines}
        covered = len(covered_set)
        pct = (covered / total * 100) if total else 0.0
        tone = _tone(pct, total)

        # Per-function rollup: group branches by qualname.
        by_func: dict[str, list[ReachableBranch]] = defaultdict(list)
        for b in branches:
            by_func[b.function_qualname].append(b)
        reachable_functions = [
            self._function_coverage(qualname, fb, covered_set)
            for qualname, fb in sorted(by_func.items())
        ]

        return CoveragePerEndpoint(
            endpoint=endpoint,
            reachable_functions=tuple(reachable_functions),
            total_branches=total,
            covered_branches=covered,
            pct=pct,
            tone=tone,
        )

    def _function_coverage(
        self,
        qualname: str,
        branches: list[ReachableBranch],
        covered_set: set[ReachableBranch],
    ) -> FunctionCoverage:
        total = len(branches)
        covered = sum(1 for b in branches if b in covered_set)
        pct = (covered / total * 100) if total else 0.0
        reached = covered > 0
        uncovered = tuple(b for b in branches if b not in covered_set)
        file = branches[0].file if branches else ""
        return FunctionCoverage(
            file=file,
            qualname=qualname,
            total_branches=total,
            covered_branches=covered,
            pct=pct,
            reached=reached,
            uncovered_branches=uncovered,
        )

    def _extra_coverage(
        self,
        enumerated_reachable_lines: set[tuple[str, int]],
        hits: LoadedCoverage,
    ) -> list[ExtraCoverage]:
        """Return one ExtraCoverage entry per file containing at least one
        branch line that was hit by the BDD suite but NOT linked to any
        endpoint by static reachability.

        Per plan-review iter 7 P1 (Codex): the previous version used
        file-granularity (`hit_files - reachable_files`). After iter 6's
        line-granularity pivot in `_audit`, the file-only check became
        inconsistent: if `src/hangman/game.py` had endpoint-reachable
        branches AND a separately-hit unlinked branch (Depends-injected
        helper, async background callback, etc.), the unlinked hit was
        invisible to extra_coverage even though `_audit` correctly counted
        it. Now both consume the same `enumerated_reachable_lines` set and
        report consistently.
        """
        all_hit_lines = {(f, _arc_source_line(bid)) for (f, bid) in hits.all_hits}
        extra_hit_lines = all_hit_lines - enumerated_reachable_lines
        # Restrict to in-scope files (defensive — out-of-scope hits don't
        # appear as extra_coverage; they're separate leakage handled by
        # _totals' in-scope filter).
        in_scope_files = set(hits.total_branches_per_file.keys())
        extra_files = sorted({f for (f, _line) in extra_hit_lines if f in in_scope_files})
        return [
            ExtraCoverage(
                file=file,
                qualname=file,  # placeholder; Analyzer can enrich
                reason="One or more branches hit by BDD suite but not linked to any endpoint by static call-graph",
            )
            for file in extra_files
        ]

    def _audit(
        self,
        enumerated_reachable_lines: set[tuple[str, int]],
        hits: LoadedCoverage,
    ) -> AuditReport:
        """Per plan-review iter 4 P1 (Codex) + iter 6 P1 (Codex) + design
        spec §4.6 step 4: audit enumeration is `reachable_lines ∪
        distinct(extra hit source-lines)`, both keyed at source-line
        granularity (not arc granularity).

        - R = enumerated_reachable_lines (deduped (file, src_line) across
              endpoints, from static graph)
        - E = projected_all_hits − R (source-lines hit by the BDD suite
              that the static graph did not link — typically shared helpers
              reached via untagged contexts, or callsites pyan3 missed)
        - Audit invariant: per file, `auth_branch_lines = R_in_file +
          E_in_file + unattributed_in_file`. `reconciled = True` iff this
          invariant holds across every in-scope file.

        See `_arc_source_line` for why we project to source-line tuples.
        """
        # Project all hits to source-line tuples, then immediately restrict
        # to in-scope files (keys of `total_branches_per_file`). Per
        # plan-review iter 9 P1 (Codex): the previous version filtered
        # out-of-scope hits when counting `per_file_enumerated` but NOT
        # when computing `extra_coverage_branches` — so any leakage
        # through coverage.py's source filter would inflate
        # `extra_coverage_branches` while leaving the rest of the audit
        # in-scope-only. Filter once, here, so all downstream audit
        # numbers (`extra_coverage_branches`, `per_file_enumerated`,
        # `unattributed_branches`) operate on the same scope as
        # `total_authoritative`.
        in_scope_files = set(hits.total_branches_per_file.keys())
        all_hit_lines = {
            (f, _arc_source_line(bid)) for (f, bid) in hits.all_hits if f in in_scope_files
        }
        extra_hit_lines = all_hit_lines - enumerated_reachable_lines
        enumerated_total = enumerated_reachable_lines | extra_hit_lines

        per_file_enumerated: dict[str, int] = {f: 0 for f in hits.total_branches_per_file}
        for f, _line in enumerated_total:
            if f in per_file_enumerated:
                per_file_enumerated[f] += 1
        # The `if f in per_file_enumerated` is now redundant given the
        # in-scope filter on all_hit_lines + the in-scope filter on
        # enumerated_reachable_lines (which derives from Reachability,
        # itself bounded by source_root). Kept as belt-and-suspenders.

        unattributed: list[UnattributedBranch] = []
        for file, auth_count in hits.total_branches_per_file.items():
            delta = auth_count - per_file_enumerated[file]
            if delta > 0:
                for i in range(delta):
                    unattributed.append(
                        UnattributedBranch(
                            file=file,
                            line=-1,
                            branch_id=f"unknown_{i}",
                            reason="coverage.py reports branch in file; neither static graph nor BDD hits identified it",
                        )
                    )

        total_authoritative = sum(hits.total_branches_per_file.values())
        reconciled = sum(per_file_enumerated.values()) + len(unattributed) == total_authoritative
        return AuditReport(
            total_branches_per_coverage_py=total_authoritative,
            total_branches_enumerated_via_reachability=len(enumerated_reachable_lines),
            extra_coverage_branches=len(extra_hit_lines),
            unattributed_branches=tuple(unattributed),
            reconciled=reconciled,
        )

    def _totals(self, hits: LoadedCoverage) -> Totals:
        """Per plan-review iter 4 P1 + iter 6 P1 (Codex) + design spec
        §4.6 step 5: project all_hits to (file, source_line) tuples,
        intersect with in-scope files (keys of `total_branches_per_file`),
        deduplicate, then count.

        Source-line projection matches `_grade_endpoint` and `_audit` so
        the totals are internally consistent with per-endpoint and audit
        numbers. Two arcs from the same source line (e.g., if-arm and
        else-arm) collapse to one branch-line, matching coverage.py's
        `branch_lines()` semantics.
        """
        total = sum(hits.total_branches_per_file.values())
        in_scope_files = set(hits.total_branches_per_file.keys())
        all_hit_lines = {(f, _arc_source_line(bid)) for (f, bid) in hits.all_hits}
        covered = sum(1 for (f, _line) in all_hit_lines if f in in_scope_files)
        pct = (covered / total * 100) if total else 0.0
        return Totals(
            total_branches=total,
            covered_branches=covered,
            pct=pct,
            tone=_tone(pct, total),
        )

    @staticmethod
    def _timestamp() -> str:
        from datetime import UTC, datetime

        return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
