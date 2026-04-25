"""End-to-end Analyzer test with mocked LLM client."""

from pathlib import Path

from tools.dashboard.analyzer import Analyzer
from tools.dashboard.coverage import CoverageGrader
from tools.dashboard.history import HistoryStore
from tools.dashboard.llm.client import LlmEvaluator
from tools.dashboard.packager import Packager
from tools.dashboard.parser import NdjsonParser
from tools.dashboard.renderer import DashboardRenderer


class TestAnalyzerPipeline:
    def test_runs_end_to_end_with_mock_llm(
        self,
        tmp_path: Path,
        minimal_ndjson_path: Path,
        mock_anthropic_client,
        good_tool_input,
    ) -> None:
        # Queue exactly enough responses for the packages the analyzer
        # will build from minimal.ndjson — 1 scenario package + 1 feature
        # package = 2 calls total.
        parse_result = NdjsonParser().parse(minimal_ndjson_path)
        package_count = len(Packager().make_packages(parse_result.features))
        for _ in range(package_count):
            mock_anthropic_client.scripted_responses.append(good_tool_input)

        out_html = tmp_path / "dashboard.html"
        hist = tmp_path / "bdd-history"
        features_dir = tmp_path / "features"
        features_dir.mkdir()

        analyzer = Analyzer(
            parser=NdjsonParser(),
            grader=CoverageGrader(),
            packager=Packager(),
            llm=LlmEvaluator(client=mock_anthropic_client, max_workers=1),
            history=HistoryStore(),
            renderer=DashboardRenderer(),
        )
        analyzer.run(
            ndjson_path=minimal_ndjson_path,
            output_path=out_html,
            history_dir=hist,
            features_glob=features_dir,
        )

        assert out_html.is_file()
        assert out_html.stat().st_size > 1000
        history_files = list(hist.glob("*.json"))
        assert len(history_files) == 1


class TestFindingSort:
    def test_findings_sorted_severity_first(self) -> None:
        from tools.dashboard.analyzer import _sort_findings
        from tools.dashboard.models import (
            Finding,
            Outcome,
            Scenario,
            Severity,
        )

        def _finding(sev: Severity, criterion: str, line: int) -> Finding:
            sc = Scenario(
                feature_file="f.feature",
                feature_name="F",
                name="n",
                line=line,
                tags=(),
                steps=(),
                outcome=Outcome.PASSED,
            )
            return Finding(
                criterion_id=criterion,
                severity=sev,
                scenario=sc,
                feature=None,
                problem="x",
                evidence="x",
                reason="x",
                fix_example="x",
                is_recognized_criterion=True,
            )

        findings = [
            _finding(Severity.P3, "D1", 10),
            _finding(Severity.P0, "H6", 5),
            _finding(Severity.P1, "H1", 3),
        ]
        sorted_ = _sort_findings(findings)
        assert [f.severity for f in sorted_] == [Severity.P0, Severity.P1, Severity.P3]


class TestCoverageAugmentation:
    def test_missing_coverage_json_returns_none_context(self, tmp_path: Path) -> None:
        # No coverage.json file present → CoverageContext is None, no crash.
        # Module-level function — no Analyzer instance needed.
        from tools.dashboard.analyzer import load_coverage_context_if_fresh

        # Construct a path that mirrors the expected layout
        # (parent.parent.parent / tests / bdd / reports / coverage.json must NOT exist).
        ndjson = tmp_path / "frontend" / "test-results" / "cucumber.ndjson"
        ndjson.parent.mkdir(parents=True)
        ndjson.write_text("")
        cov = load_coverage_context_if_fresh(ndjson)
        assert cov is None

    def test_stale_coverage_json_returns_none(self, tmp_path: Path) -> None:
        import json

        from tools.dashboard.analyzer import load_coverage_context_if_fresh

        # Create a coverage.json with a timestamp >1h older than ndjson mtime.
        ndjson = tmp_path / "frontend" / "test-results" / "cucumber.ndjson"
        ndjson.parent.mkdir(parents=True)
        ndjson.write_text("")
        cov_json = tmp_path / "tests" / "bdd" / "reports" / "coverage.json"
        cov_json.parent.mkdir(parents=True)
        cov_json.write_text(
            json.dumps(
                {
                    "timestamp": "2020-01-01T00:00:00Z",
                    "totals": {
                        "pct": 50.0,
                        "tone": "warning",
                        "covered_branches": 5,
                        "total_branches": 10,
                    },
                    "endpoints": [],
                    "audit": {"reconciled": True, "unattributed_branches": []},
                }
            )
        )
        cov = load_coverage_context_if_fresh(ndjson)
        assert cov is None  # too stale

    def test_fresh_coverage_json_returns_context(self, tmp_path: Path) -> None:
        import json
        from datetime import UTC, datetime

        from tools.dashboard.analyzer import load_coverage_context_if_fresh

        ndjson = tmp_path / "frontend" / "test-results" / "cucumber.ndjson"
        ndjson.parent.mkdir(parents=True)
        ndjson.write_text("")
        cov_json = tmp_path / "tests" / "bdd" / "reports" / "coverage.json"
        cov_json.parent.mkdir(parents=True)
        # Use the ndjson's mtime so the timestamps match within 1h.
        cov_ts = datetime.fromtimestamp(ndjson.stat().st_mtime, tz=UTC).isoformat()
        cov_json.write_text(
            json.dumps(
                {
                    "timestamp": cov_ts,
                    "totals": {
                        "pct": 75.0,
                        "tone": "warning",
                        "covered_branches": 75,
                        "total_branches": 100,
                    },
                    "endpoints": [
                        {
                            "method": "GET",
                            "path": "/api/v1/games",
                            "pct": 80.0,
                            "tone": "warning",
                            "uncovered_branches_flat": [],
                        }
                    ],
                    "audit": {"reconciled": True, "unattributed_branches": []},
                }
            )
        )
        cov = load_coverage_context_if_fresh(ndjson)
        assert cov is not None
        assert cov.totals_pct == 75.0
        assert cov.totals_covered_branches == 75
        assert cov.totals_total_branches == 100
        assert cov.audit_reconciled is True
        assert cov.endpoints_summary == (("GET", "/api/v1/games", 80.0, "warning"),)
