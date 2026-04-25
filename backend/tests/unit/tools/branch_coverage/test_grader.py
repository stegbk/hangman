"""Tests for Grader — the correctness core of Feature 3."""

from __future__ import annotations

import pytest
from tools.branch_coverage.grader import Grader
from tools.branch_coverage.models import (
    Endpoint,
    LoadedCoverage,
    ReachableBranch,
    Tone,
)


def _branch(file: str, line: int, func: str) -> ReachableBranch:
    """Construct a fixture ReachableBranch.

    Per plan-review iter 5 P1 (Codex): all `file` values in this test
    module use the canonical runtime path format `src/hangman/<module>.py`
    (matching what coverage.py with `relative_files = true` and
    Reachability with absolute source_root both produce — see iter 4
    patches (a) and `.coveragerc`). Tests that hand-construct paths
    must use the same shape so they exercise the production
    equivalence between the two sides; otherwise they hide path-
    normalization bugs.
    """
    return ReachableBranch(
        file=file,
        line=line,
        branch_id=f"{line}->{line + 1}",
        condition_text=f"if x_{line}:",
        not_taken_to_line=line + 1,
        function_qualname=func,
    )


def _ep(path: str, handler: str) -> Endpoint:
    return Endpoint(method="POST", path=path, handler_qualname=handler)


class TestPerEndpointIntersection:
    def test_endpoint_with_all_branches_covered_is_green(self) -> None:
        ep = _ep("/a", "hangman.routes.handler_a")
        branch1 = _branch("src/hangman/a.py", 10, "hangman.a.fn")
        branch2 = _branch("src/hangman/a.py", 20, "hangman.a.fn")
        reachability = {ep: [branch1, branch2]}
        hits = LoadedCoverage(
            hits_by_context={
                "POST /a": frozenset(
                    {("src/hangman/a.py", "10->11"), ("src/hangman/a.py", "20->21")}
                )
            },
            total_branches_per_file={"src/hangman/a.py": 2},
            all_hits=frozenset({("src/hangman/a.py", "10->11"), ("src/hangman/a.py", "20->21")}),
        )
        report = Grader().grade(reachability, hits)
        ep_cov = report.endpoints[0]
        assert ep_cov.tone == Tone.SUCCESS
        assert ep_cov.pct == 100.0

    def test_endpoint_with_no_branches_covered_is_red(self) -> None:
        ep = _ep("/b", "hangman.routes.handler_b")
        reachability = {ep: [_branch("src/hangman/b.py", 10, "hangman.b.fn")]}
        hits = LoadedCoverage(
            hits_by_context={"POST /b": frozenset()},
            total_branches_per_file={"src/hangman/b.py": 1},
            all_hits=frozenset(),
        )
        report = Grader().grade(reachability, hits)
        assert report.endpoints[0].tone == Tone.ERROR
        assert report.endpoints[0].pct == 0.0

    def test_endpoint_with_zero_reachable_branches_is_na(self) -> None:
        ep = _ep("/c", "hangman.routes.handler_c")
        reachability = {ep: []}
        hits = LoadedCoverage(
            hits_by_context={},
            total_branches_per_file={},
            all_hits=frozenset(),
        )
        report = Grader().grade(reachability, hits)
        assert report.endpoints[0].tone == Tone.NA
        assert report.endpoints[0].total_branches == 0

    @pytest.mark.parametrize(
        "pct, expected_tone",
        [
            (49.9, Tone.ERROR),
            (50.0, Tone.WARNING),
            (79.9, Tone.WARNING),
            (80.0, Tone.SUCCESS),
            (100.0, Tone.SUCCESS),
        ],
    )
    def test_threshold_resolution(self, pct: float, expected_tone: Tone) -> None:
        # Generate N branches, mark the right proportion as hit.
        ep = _ep("/x", "hangman.routes.handler_x")
        total = 100
        covered_count = int(pct)  # 50.0 → 50 covered out of 100
        branches = [_branch("src/hangman/x.py", i, "hangman.x.fn") for i in range(total)]
        hit_set = frozenset(("src/hangman/x.py", f"{i}->{i + 1}") for i in range(covered_count))
        reachability = {ep: branches}
        hits = LoadedCoverage(
            hits_by_context={"POST /x": hit_set},
            total_branches_per_file={"src/hangman/x.py": total},
            all_hits=hit_set,
        )
        report = Grader().grade(reachability, hits)
        assert report.endpoints[0].tone == expected_tone


class TestSharedHelperCorrectness:
    """Design spec §4.6 mandate: a helper reachable from 2 endpoints
    where only 1 endpoint's scenarios fire on the hit must show the
    helper as uncovered for the other endpoint."""

    def test_shared_helper_only_covered_under_one_context(self) -> None:
        ep_a = _ep("/a", "hangman.routes.handler_a")
        ep_b = _ep("/b", "hangman.routes.handler_b")
        shared = _branch("src/hangman/shared.py", 10, "hangman.shared.helper")
        reachability = {ep_a: [shared], ep_b: [shared]}
        # Only endpoint A's context fires on the hit.
        hits = LoadedCoverage(
            hits_by_context={
                "POST /a": frozenset({("src/hangman/shared.py", "10->11")}),
                "POST /b": frozenset(),
            },
            total_branches_per_file={"src/hangman/shared.py": 1},
            all_hits=frozenset({("src/hangman/shared.py", "10->11")}),
        )
        report = Grader().grade(reachability, hits)
        a = next(e for e in report.endpoints if e.endpoint.path == "/a")
        b = next(e for e in report.endpoints if e.endpoint.path == "/b")
        assert a.pct == 100.0  # A's scenarios triggered the helper
        assert b.pct == 0.0  # B's scenarios DID NOT — correctness fix
        assert a.tone == Tone.SUCCESS
        assert b.tone == Tone.ERROR

    def test_shared_helper_across_three_endpoints(self) -> None:
        """Per plan-review iter 1 P2: extend the shared-helper case to
        N=3 endpoints. Audit dedup must count the shared branch ONCE
        across any number of endpoints; per-endpoint pct must reflect
        only that endpoint's context hits."""
        ep_a = _ep("/a", "hangman.routes.handler_a")
        ep_b = _ep("/b", "hangman.routes.handler_b")
        ep_c = _ep("/c", "hangman.routes.handler_c")
        shared = _branch("src/hangman/shared.py", 10, "hangman.shared.helper")
        reachability = {ep_a: [shared], ep_b: [shared], ep_c: [shared]}
        # Endpoints A and C trigger the shared branch; B does not.
        hits = LoadedCoverage(
            hits_by_context={
                "POST /a": frozenset({("src/hangman/shared.py", "10->11")}),
                "POST /b": frozenset(),
                "POST /c": frozenset({("src/hangman/shared.py", "10->11")}),
            },
            total_branches_per_file={"src/hangman/shared.py": 1},
            all_hits=frozenset({("src/hangman/shared.py", "10->11")}),
        )
        report = Grader().grade(reachability, hits)
        a = next(e for e in report.endpoints if e.endpoint.path == "/a")
        b = next(e for e in report.endpoints if e.endpoint.path == "/b")
        c = next(e for e in report.endpoints if e.endpoint.path == "/c")
        # A and C see the shared branch as covered.
        assert a.pct == 100.0
        assert c.pct == 100.0
        # B does not — its scenarios never triggered the helper.
        assert b.pct == 0.0
        # Audit dedupes: 1 authoritative branch = 1 enumerated (not 3).
        assert report.audit.total_branches_per_coverage_py == 1
        assert report.audit.total_branches_enumerated_via_reachability == 1
        assert report.audit.reconciled is True


class TestAuditReconciliation:
    def test_reconciles_when_enumeration_matches(self) -> None:
        ep = _ep("/a", "hangman.routes.handler_a")
        reachability = {ep: [_branch("src/hangman/a.py", 10, "hangman.a.fn")]}
        hits = LoadedCoverage(
            hits_by_context={"POST /a": frozenset({("src/hangman/a.py", "10->11")})},
            total_branches_per_file={"src/hangman/a.py": 1},
            all_hits=frozenset({("src/hangman/a.py", "10->11")}),
        )
        report = Grader().grade(reachability, hits)
        assert report.audit.reconciled is True
        assert report.audit.total_branches_per_coverage_py == 1

    def test_unattributed_branches_surface_when_enumeration_incomplete(
        self,
    ) -> None:
        # coverage.py says file has 5 branches; our enumeration found 3.
        # Delta of 2 must appear in unattributed_branches.
        ep = _ep("/a", "hangman.routes.handler_a")
        reachability = {
            ep: [
                _branch("src/hangman/a.py", 10, "hangman.a.fn"),
                _branch("src/hangman/a.py", 20, "hangman.a.fn"),
                _branch("src/hangman/a.py", 30, "hangman.a.fn"),
            ]
        }
        hits = LoadedCoverage(
            hits_by_context={"POST /a": frozenset()},
            total_branches_per_file={"src/hangman/a.py": 5},
            all_hits=frozenset(),
        )
        report = Grader().grade(reachability, hits)
        # 5 authoritative − 3 enumerated = 2 unattributed (placeholder records).
        assert len(report.audit.unattributed_branches) == 2

    def test_shared_branch_across_endpoints_deduped_in_audit(self) -> None:
        # A shared branch reachable from 2 endpoints counts ONCE in the
        # audit enumeration — not twice.
        ep_a = _ep("/a", "hangman.routes.handler_a")
        ep_b = _ep("/b", "hangman.routes.handler_b")
        shared = _branch("src/hangman/shared.py", 10, "hangman.shared.fn")
        reachability = {ep_a: [shared], ep_b: [shared]}
        hits = LoadedCoverage(
            hits_by_context={
                "POST /a": frozenset({("src/hangman/shared.py", "10->11")}),
                "POST /b": frozenset(),
            },
            total_branches_per_file={"src/hangman/shared.py": 1},
            all_hits=frozenset({("src/hangman/shared.py", "10->11")}),
        )
        report = Grader().grade(reachability, hits)
        # 1 authoritative = 1 enumerated (deduped) — reconciliation holds.
        assert report.audit.reconciled is True
        assert report.audit.total_branches_enumerated_via_reachability == 1

    def test_extra_branch_hits_count_in_audit_enumeration(self) -> None:
        # Per plan-review iter 4 P1 (Codex): branches HIT by the BDD suite
        # but NOT linked to any endpoint via static reachability MUST count
        # toward the audit enumeration (E set), not be left as
        # `extra_count = 0`. This is the common shared-helper case where
        # pyan3 missed a callsite but coverage.py still saw the hit.
        ep = _ep("/a", "hangman.routes.handler_a")
        reachability = {ep: [_branch("src/hangman/a.py", 10, "hangman.a.fn")]}
        hits = LoadedCoverage(
            hits_by_context={
                "POST /a": frozenset(
                    {
                        ("src/hangman/a.py", "10->11"),
                        ("src/hangman/utils.py", "5->6"),  # hit via untagged context
                    }
                )
            },
            total_branches_per_file={"src/hangman/a.py": 1, "src/hangman/utils.py": 1},
            all_hits=frozenset(
                {
                    ("src/hangman/a.py", "10->11"),
                    ("src/hangman/utils.py", "5->6"),
                }
            ),
        )
        report = Grader().grade(reachability, hits)
        # 1 reachable + 1 extra = 2 enumerated. 2 authoritative. reconciled.
        assert report.audit.reconciled is True
        assert report.audit.extra_coverage_branches == 1
        assert report.audit.total_branches_enumerated_via_reachability == 1
        assert len(report.audit.unattributed_branches) == 0


class TestTotals:
    def test_totals_use_authoritative_count(self) -> None:
        ep = _ep("/a", "hangman.routes.handler_a")
        reachability = {ep: [_branch("src/hangman/a.py", 10, "hangman.a.fn")]}
        hits = LoadedCoverage(
            hits_by_context={"POST /a": frozenset({("src/hangman/a.py", "10->11")})},
            total_branches_per_file={"src/hangman/a.py": 1},
            all_hits=frozenset({("src/hangman/a.py", "10->11")}),
        )
        report = Grader().grade(reachability, hits)
        assert report.totals.total_branches == 1
        assert report.totals.covered_branches == 1
        assert report.totals.pct == 100.0

    def test_else_arm_arc_target_still_matches_branch_at_source_line(self) -> None:
        # Per plan-review iter 6 P1 (Codex): coverage.py's real arc IDs
        # for else-arms or multi-line bodies have non-`line+1` targets.
        # Reachability emits synthetic `f"{line}->{line+1}"`. Direct equality
        # on (file, branch_id) would miss every match where targets differ.
        # The Grader projects to (file, source_line) for matching, so an
        # else-arm hit ("10->15") still credits the branch at line 10.
        ep = _ep("/a", "hangman.routes.handler_a")
        branch = _branch("src/hangman/a.py", 10, "hangman.a.fn")
        # branch.branch_id == "10->11" (synthetic from Reachability)
        assert branch.branch_id == "10->11"
        reachability = {ep: [branch]}
        hits = LoadedCoverage(
            # Coverage.py recorded the ELSE arm: 10->15 (not 10->11)
            hits_by_context={"POST /a": frozenset({("src/hangman/a.py", "10->15")})},
            total_branches_per_file={"src/hangman/a.py": 1},
            all_hits=frozenset({("src/hangman/a.py", "10->15")}),
        )
        report = Grader().grade(reachability, hits)
        ep_cov = report.endpoints[0]
        # Source-line projection: ("src/hangman/a.py", 10) is in both sets.
        assert ep_cov.covered_branches == 1, (
            "Expected line-level match: branch at line 10 is hit by arc 10->15. "
            "If 0, the Grader is still doing exact (file, branch_id) match — "
            "iter 6 P1 Codex regression."
        )
        assert ep_cov.pct == 100.0
        assert report.totals.covered_branches == 1


class TestArcSourceLine:
    """Forward-looking regression guards on the `_arc_source_line` helper's
    documented contract.

    Per plan-review iter 7 P2 (Codex) + iter 8 P2 follow-up: the helper's
    docstring lists three supported input formats (normal arc, negative-
    target exit arc, bare-line fallback). Each test below pins one of those
    formats so a future refactor — e.g., switching to a regex parser, or
    inlining `int(...)` somewhere that breaks one path — gets caught
    immediately at unit-test time instead of producing silent off-by-one
    errors in coverage.json.

    Note: the iter-6 BEHAVIORAL fix (line-granularity matching across
    Reachability and coverage.py) is regression-tested by
    `test_else_arm_arc_target_still_matches_branch_at_source_line`,
    which lives in `TestTotals` above (it asserts both the per-endpoint
    intersection AND the totals projection through one fixture). These
    helper-contract tests are forward-looking guards, distinct from
    that behavioral fix.
    """

    def test_extracts_source_line_from_normal_arc(self) -> None:
        from tools.branch_coverage.grader import _arc_source_line

        assert _arc_source_line("10->11") == 10

    def test_extracts_source_line_from_negative_target_arc(self) -> None:
        # coverage.py uses negative target lines for function-exit arcs.
        # _arcs_for_context already filters these out before they reach
        # the Grader, but _arc_source_line is defensive: even if one
        # leaks through, the source line extracts cleanly.
        from tools.branch_coverage.grader import _arc_source_line

        assert _arc_source_line("42->-1") == 42

    def test_falls_through_on_bare_line_format(self) -> None:
        # If coverage.py changes its arc-id encoding to a bare line number,
        # the helper still extracts the source line via int() coercion.
        from tools.branch_coverage.grader import _arc_source_line

        assert _arc_source_line("10") == 10

    def test_extra_coverage_includes_intra_file_unlinked_hits(self) -> None:
        # Per plan-review iter 7 P1 (Codex): if a file has BOTH endpoint-
        # reachable branches AND separately-hit unlinked branches (e.g.,
        # via Depends or background tasks), extra_coverage MUST report the
        # file. The previous file-granularity dedup (`hit_files -
        # reachable_files`) silently dropped the unlinked branch because
        # the file appeared in reachable_files.
        ep = _ep("/a", "hangman.routes.handler_a")
        # Endpoint reaches line 10 in game.py.
        reachable_branch = _branch("src/hangman/game.py", 10, "hangman.game.fn_a")
        reachability = {ep: [reachable_branch]}
        hits = LoadedCoverage(
            hits_by_context={
                "POST /a": frozenset(
                    {
                        ("src/hangman/game.py", "10->11"),
                        # ALSO hit: line 99 in the SAME file, but unreachable from
                        # any endpoint via static analysis (e.g., FastAPI Depends).
                        ("src/hangman/game.py", "99->100"),
                    }
                )
            },
            total_branches_per_file={"src/hangman/game.py": 2},
            all_hits=frozenset(
                {
                    ("src/hangman/game.py", "10->11"),
                    ("src/hangman/game.py", "99->100"),
                }
            ),
        )
        report = Grader().grade(reachability, hits)
        # extra_coverage MUST include game.py (line 99 hit, not reachable),
        # even though line 10 in the same file IS reachable.
        extra_files = {ec.file for ec in report.extra_coverage}
        assert "src/hangman/game.py" in extra_files, (
            f"Expected game.py in extra_coverage (line 99 unlinked hit), "
            f"got {extra_files}. The file-granularity bug is back — "
            f"iter 7 P1 Codex regression."
        )
        # Audit also counts it (line 99 is the extra branch).
        assert report.audit.extra_coverage_branches == 1
        assert report.audit.reconciled is True

    def test_totals_excludes_out_of_scope_hits(self) -> None:
        # Per plan-review iter 4 P1 (Codex): hits in files not in
        # total_branches_per_file (out-of-scope leakage) MUST NOT count
        # toward `covered`. The design says
        # `covered = |hits.all_hits ∩ all branches in backend/src/hangman/|`;
        # using `len(hits.all_hits)` over-reports if any leakage gets through
        # coverage.py's source filter.
        ep = _ep("/a", "hangman.routes.handler_a")
        reachability = {ep: [_branch("src/hangman/a.py", 10, "hangman.a.fn")]}
        hits = LoadedCoverage(
            hits_by_context={
                "POST /a": frozenset(
                    {
                        ("src/hangman/a.py", "10->11"),  # in scope
                        ("third_party/lib.py", "5->6"),  # out of scope
                    }
                )
            },
            total_branches_per_file={"src/hangman/a.py": 1},  # only in-scope file
            all_hits=frozenset(
                {
                    ("src/hangman/a.py", "10->11"),
                    ("third_party/lib.py", "5->6"),
                }
            ),
        )
        report = Grader().grade(reachability, hits)
        assert report.totals.total_branches == 1
        assert report.totals.covered_branches == 1  # NOT 2 — leakage filtered
        assert report.totals.pct == 100.0
