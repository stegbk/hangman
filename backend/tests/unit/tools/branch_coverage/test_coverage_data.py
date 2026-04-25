"""Tests for CoverageDataLoader.

We generate a tiny .coverage file in-process during the test instead
of committing a binary fixture. This keeps the test self-contained.
"""

from __future__ import annotations

from pathlib import Path

import coverage
import pytest
from tools.branch_coverage.coverage_data import CoverageDataLoader, CoverageDataLoadError
from tools.branch_coverage.models import LoadedCoverage


@pytest.fixture
def tiny_covered_data(tmp_path: Path) -> Path:
    """Generate a real .coverage file by running a trivial function
    under coverage, with two contexts ('ctx_a' and 'ctx_b')."""
    target_file = tmp_path / "tiny.py"
    target_file.write_text("def double(x):\n    if x > 0:\n        return x * 2\n    return 0\n")
    data_file = tmp_path / ".coverage_fixture"
    # Note: coverage.py 7.13.5 requires a base `context=` kwarg for
    # `switch_context()` to record subsequent context switches reliably.
    # Without it, only the first switched-to context gets persisted
    # (a quirk verified by inspecting `data.measured_contexts()` on 7.13.5).
    # The test assertion below uses substring matching ("ctx_a" in k)
    # which already anticipated coverage.py prefixing context names.
    cov = coverage.Coverage(
        data_file=str(data_file),
        branch=True,
        source=[str(tmp_path)],
        context="base",
    )
    cov.start()
    import importlib.util

    spec = importlib.util.spec_from_file_location("tiny", target_file)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    cov.switch_context("ctx_a")
    spec.loader.exec_module(mod)
    mod.double(5)  # takes x > 0 branch
    cov.switch_context("ctx_b")
    mod.double(-1)  # takes x <= 0 branch
    cov.stop()
    cov.save()
    return data_file


class TestLoadPerContextHits:
    def test_returns_loaded_coverage(self, tiny_covered_data: Path) -> None:
        result = CoverageDataLoader().load(tiny_covered_data)
        assert isinstance(result, LoadedCoverage)

    def test_exposes_per_context_hit_sets(self, tiny_covered_data: Path) -> None:
        result = CoverageDataLoader().load(tiny_covered_data)
        # Contexts we set should be present. Coverage.py may prefix/suffix them;
        # accept any context name containing our label.
        context_keys = set(result.hits_by_context.keys())
        assert any("ctx_a" in k for k in context_keys)
        assert any("ctx_b" in k for k in context_keys)

    def test_total_branches_per_file_is_authoritative(self, tiny_covered_data: Path) -> None:
        # Per plan-review iter 6 P2 (Codex): assert exact count, not just
        # > 0. The fixture's tiny.py has exactly ONE branch line (`if x > 0`).
        # The previous `count > 0` would still pass if `_authoritative_branch_lines`
        # over-counted (e.g., counted all arcs instead of branch-source-lines)
        # — exactly the bug iter 6 patch (b) fixed.
        result = CoverageDataLoader().load(tiny_covered_data)
        assert len(result.total_branches_per_file) == 1, (
            f"Expected exactly one measured file (tiny.py); got "
            f"{list(result.total_branches_per_file.keys())}"
        )
        ((tiny_file, count),) = result.total_branches_per_file.items()
        assert count == 1, (
            f"Expected exactly 1 branch line in tiny.py (the `if x > 0`), "
            f"got {count}. If this is >1, check that _authoritative_branch_lines "
            f"is using `Analysis.branch_lines()` not `arc_possibilities()` — "
            f"the latter counts all arcs including non-branch linear flow."
        )

    def test_all_hits_is_union_of_contexts(self, tiny_covered_data: Path) -> None:
        result = CoverageDataLoader().load(tiny_covered_data)
        union = frozenset().union(*result.hits_by_context.values())
        assert result.all_hits == union

    def test_hits_exclude_non_branch_linear_flow_arcs(self, tmp_path: Path) -> None:
        # Per plan-review iter 8 P1 (Codex): a file with linear flow
        # between non-branch statements (e.g., `a = 1\nb = 2`) generates
        # arcs in coverage.py's data even though no branching happened.
        # Without filtering, those arcs would project to source-line tuples
        # that the Grader treats as branch hits — inflating totals,
        # creating bogus extra_coverage. This test proves they are filtered
        # at the loader layer.
        import coverage as cov_mod

        target = tmp_path / "linear.py"
        # Two functions: one with linear flow only (no branches), one with
        # exactly one `if`. Total branch lines = 1 (only `if x > 0`).
        target.write_text(
            "def linear_only():\n"
            "    a = 1\n"
            "    b = 2\n"
            "    c = a + b\n"
            "    return c\n"
            "\n"
            "def with_branch(x):\n"
            "    if x > 0:\n"
            "        return 1\n"
            "    return 0\n"
        )
        cov_path = tmp_path / ".coverage"
        c = cov_mod.Coverage(data_file=str(cov_path), branch=True, source=[str(tmp_path)])
        c.start()
        c.switch_context("ctx_a")
        import importlib.util

        spec = importlib.util.spec_from_file_location("linear", target)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # Execute BOTH functions: linear_only (5 lines of linear flow) and
        # with_branch with x=5 (taken branch).
        mod.linear_only()
        mod.with_branch(5)
        c.stop()
        c.save()

        result = CoverageDataLoader().load(cov_path)
        # Total branch lines: exactly 1 (the `if x > 0`). If unfiltered,
        # `all_hits` would contain the 4+ linear-flow arcs from
        # linear_only() too — the assertion below would catch it.
        ((_file, count),) = result.total_branches_per_file.items()
        assert count == 1, (
            f"Expected 1 branch line in linear.py (only `if x > 0`), got {count}. "
            f"_authoritative_branch_lines may be over-counting."
        )
        # Each hit in all_hits must have its source line == the branch line.
        # If linear-flow arcs leaked in, their source lines would be the
        # linear statement lines, not the `if` line.
        # The fixture's `if x > 0` is at line 8; with x=5 the taken arc is
        # 8->9 (or whatever coverage.py records). The KEY assertion: every
        # arc's source-line must be IN the branch_lines set (line 8).
        for f, bid in result.all_hits:
            src_line = int(bid.split("->", 1)[0])
            # Branch line 8 is the only valid source-line for branch hits.
            assert src_line == 8, (
                f"Hit ({f}, {bid}) has source-line {src_line} which is NOT a "
                f"branch line. Linear-flow arc leaked through filter — "
                f"iter 8 P1 Codex regression."
            )


class TestMissingFile:
    def test_raises_specific_error(self, tmp_path: Path) -> None:
        with pytest.raises(CoverageDataLoadError, match="bdd-coverage"):
            CoverageDataLoader().load(tmp_path / "does-not-exist.coverage")
