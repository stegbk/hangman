"""Tests for DashboardRenderer."""

from __future__ import annotations

from pathlib import Path

from tools.branch_coverage.renderer import DashboardRenderer

from tests.unit.tools.branch_coverage.test_json_emitter import _fixture_report


class TestRender:
    def test_writes_html_file(self, tmp_path: Path) -> None:
        out = tmp_path / "coverage.html"
        DashboardRenderer().render(_fixture_report(), out)
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_contains_totals_section(self, tmp_path: Path) -> None:
        out = tmp_path / "coverage.html"
        DashboardRenderer().render(_fixture_report(), out)
        html = out.read_text()
        assert "Total coverage" in html
        assert "0.0%" in html  # fixture has 0/1 covered

    def test_contains_endpoint_card(self, tmp_path: Path) -> None:
        out = tmp_path / "coverage.html"
        DashboardRenderer().render(_fixture_report(), out)
        html = out.read_text()
        assert "POST /api/v1/games" in html
        assert "hangman.routes.start_game" in html

    def test_reconciled_true_shows_no_warning_banner(self, tmp_path: Path) -> None:
        out = tmp_path / "coverage.html"
        DashboardRenderer().render(_fixture_report(), out)
        html = out.read_text()
        assert "Audit reconciliation FAILED" not in html

    def test_autoescapes_condition_text(self, tmp_path: Path) -> None:
        # Inject a condition text with <script> to verify autoescape.
        from tools.branch_coverage.models import (
            AuditReport,
            CoveragePerEndpoint,
            CoverageReport,
            Endpoint,
            FunctionCoverage,
            ReachableBranch,
            Tone,
            Totals,
        )

        poisoned = ReachableBranch(
            file="x.py",
            line=1,
            branch_id="1->2",
            condition_text="<script>alert(1)</script>",
            not_taken_to_line=2,
            function_qualname="x.fn",
        )
        fc = FunctionCoverage(
            file="x.py",
            qualname="x.fn",
            total_branches=1,
            covered_branches=0,
            pct=0.0,
            reached=False,
            uncovered_branches=(poisoned,),
        )
        ep_cov = CoveragePerEndpoint(
            endpoint=Endpoint(method="GET", path="/x", handler_qualname="x.handler"),
            reachable_functions=(fc,),
            total_branches=1,
            covered_branches=0,
            pct=0.0,
            tone=Tone.ERROR,
        )
        report = CoverageReport(
            version=1,
            timestamp="2026-04-24T20:00:00Z",
            cucumber_ndjson="x.ndjson",
            instrumented=True,
            thresholds={"red": 50.0, "yellow": 80.0},
            totals=Totals(total_branches=1, covered_branches=0, pct=0.0, tone=Tone.ERROR),
            endpoints=(ep_cov,),
            extra_coverage=(),
            audit=AuditReport(
                total_branches_per_coverage_py=1,
                total_branches_enumerated_via_reachability=1,
                extra_coverage_branches=0,
                unattributed_branches=(),
                reconciled=True,
            ),
        )
        out = tmp_path / "coverage.html"
        DashboardRenderer().render(report, out)
        html = out.read_text()
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


class TestGoldenFile:
    def test_matches_golden(self, tmp_path: Path, fixtures_dir: Path) -> None:
        out = tmp_path / "coverage.html"
        DashboardRenderer().render(_fixture_report(), out)
        golden = (fixtures_dir / "golden_coverage.html").read_text()
        assert out.read_text() == golden
