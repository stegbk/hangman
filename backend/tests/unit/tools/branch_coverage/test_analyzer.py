"""End-to-end Analyzer test with fakes for subprocess-like components."""

from __future__ import annotations

from pathlib import Path

from tools.branch_coverage.analyzer import Analyzer
from tools.branch_coverage.callgraph import CallGraph
from tools.branch_coverage.coverage_data import CoverageDataLoader  # noqa: F401
from tools.branch_coverage.grader import Grader
from tools.branch_coverage.json_emitter import JsonEmitter
from tools.branch_coverage.models import LoadedCoverage
from tools.branch_coverage.reachability import Reachability
from tools.branch_coverage.renderer import DashboardRenderer
from tools.branch_coverage.routes import RouteEnumerator

from tests.fixtures.branch_coverage.fake_adjacency import fake_graph_for_minimal_app


class _FakeCallGraphBuilder:
    def build(self, source_root: Path) -> CallGraph:
        return fake_graph_for_minimal_app()


class _FakeCoverageDataLoader:
    def load(self, coverage_file: Path) -> LoadedCoverage:
        # Empty coverage — no branches hit.
        return LoadedCoverage(
            hits_by_context={},
            total_branches_per_file={},
            all_hits=frozenset(),
        )


def _import_minimal_app() -> object:
    from tests.fixtures.branch_coverage.minimal_app.main import app

    return app


class TestAnalyzerPipeline:
    def test_runs_end_to_end_with_fakes(
        self, tmp_path: Path, minimal_app_source_root: Path
    ) -> None:
        # Arrange
        html_out = tmp_path / "coverage.html"
        json_out = tmp_path / "coverage.json"
        analyzer = Analyzer(
            routes=RouteEnumerator(),
            callgraph=_FakeCallGraphBuilder(),
            reachability=Reachability(),
            coverage_data=_FakeCoverageDataLoader(),
            grader=Grader(),
            json_emitter=JsonEmitter(),
            renderer=DashboardRenderer(),
        )

        # Act
        analyzer.run(
            app=_import_minimal_app(),
            coverage_file=tmp_path / "nonexistent.coverage",  # fake loader ignores
            source_root=minimal_app_source_root,
            json_output=json_out,
            html_output=html_out,
        )

        # Assert
        assert json_out.exists()
        assert html_out.exists()
        assert html_out.stat().st_size > 500
