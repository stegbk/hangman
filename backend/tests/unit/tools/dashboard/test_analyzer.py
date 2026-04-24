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
        # Queue enough responses for all packages the analyzer builds.
        for _ in range(10):
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
