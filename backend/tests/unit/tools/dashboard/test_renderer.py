"""Tests for DashboardRenderer — autoescape + golden file."""

from pathlib import Path

from tools.dashboard.models import (
    AnalysisContext,
    CostReport,
    CoverageGrade,
    CoverageState,
    Feature,
    Finding,
    Outcome,
    RunSummary,
    Scenario,
    Severity,
    Step,
)
from tools.dashboard.renderer import DashboardRenderer


def _deterministic_inputs() -> tuple[
    AnalysisContext, list[Finding], list[CoverageGrade], list[RunSummary], RunSummary
]:
    sc = Scenario(
        feature_file="features/minimal.feature",
        feature_name="UC1 — Minimal",
        name="trivial pass",
        line=3,
        tags=("@happy", "@smoke"),
        steps=(Step(keyword="Given ", text="a setup", outcome=Outcome.PASSED),),
        outcome=Outcome.PASSED,
    )
    feat = Feature(file="features/minimal.feature", name="UC1 — Minimal", scenarios=(sc,), line=1)
    context = AnalysisContext(
        features=(feat,),
        scenarios=(sc,),
        endpoint_index={},
        uc_index={"UC1": (sc,)},
        timestamp="2026-04-24T12:00:00Z",
    )
    findings = [
        Finding(
            criterion_id="D1",
            severity=Severity.P2,
            scenario=sc,
            feature=None,
            problem="Trivial pass",
            evidence="<script>alert(1)</script>",  # injection canary
            reason="No body check",
            fix_example="And body.x == 1",
            is_recognized_criterion=True,
        ),
    ]
    grades = [
        CoverageGrade(
            subject="UC1",
            kind="uc",
            state=CoverageState.PARTIAL,
            contributing_scenarios=(sc,),
            missing_tags=("@edge", "@failure"),
        ),
    ]
    history: list[RunSummary] = []
    summary = RunSummary(
        timestamp="2026-04-24T12:00:00Z",
        total_scenarios=1,
        passed=1,
        failed=0,
        skipped=0,
        finding_counts={Severity.P0: 0, Severity.P1: 0, Severity.P2: 1, Severity.P3: 0},
        model="claude-sonnet-4-6",
        cost=CostReport(
            model="claude-sonnet-4-6",
            total_input_tokens=1000,
            total_cache_read_tokens=800,
            total_cache_creation_tokens=200,
            total_output_tokens=300,
            total_usd=0.01,
            cache_hit_rate=0.8,
        ),
        skipped_packages=(),
    )
    return context, findings, grades, history, summary


class TestAutoescape:
    def test_html_tags_in_evidence_are_escaped(self, tmp_path: Path) -> None:
        out = tmp_path / "dashboard.html"
        ctx, findings, grades, history, summary = _deterministic_inputs()
        DashboardRenderer().render(ctx, findings, grades, history, (), summary, None, out)
        html = out.read_text()
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


class TestGoldenFile:
    def test_render_matches_golden(self, tmp_path: Path, fixtures_dir: Path) -> None:
        """Deterministic inputs → byte-identical HTML.

        To regenerate the golden (after an intentional template change):
        manually re-run the generator snippet and copy the output file.
        """
        out = tmp_path / "dashboard.html"
        ctx, findings, grades, history, summary = _deterministic_inputs()
        DashboardRenderer().render(ctx, findings, grades, history, (), summary, None, out)
        golden = (fixtures_dir / "golden_render.html").read_text()
        assert out.read_text() == golden


class TestWarningBanner:
    def test_banner_rendered_when_skipped(self, tmp_path: Path) -> None:
        out = tmp_path / "dashboard.html"
        ctx, findings, grades, history, summary = _deterministic_inputs()
        DashboardRenderer().render(
            ctx,
            findings,
            grades,
            history,
            ("feature:features/x.feature",),
            summary,
            None,
            out,
        )
        html = out.read_text()
        assert "warning-banner" in html
        assert "feature:features/x.feature" in html

    def test_no_banner_when_nothing_skipped(self, tmp_path: Path) -> None:
        out = tmp_path / "dashboard.html"
        ctx, findings, grades, history, summary = _deterministic_inputs()
        DashboardRenderer().render(ctx, findings, grades, history, (), summary, None, out)
        html = out.read_text()
        assert "warning-banner" not in html


class TestLlmInventedBadge:
    def test_unrecognized_criterion_gets_badge(self, tmp_path: Path) -> None:
        out = tmp_path / "dashboard.html"
        ctx, findings, grades, history, summary = _deterministic_inputs()
        invented = Finding(
            criterion_id="L1",
            severity=Severity.P3,
            scenario=ctx.scenarios[0],
            feature=None,
            problem="LLM-original",
            evidence="x",
            reason="x",
            fix_example="x",
            is_recognized_criterion=False,
        )
        DashboardRenderer().render(
            ctx, findings + [invented], grades, history, (), summary, None, out
        )
        html = out.read_text()
        assert "LLM-invented" in html or "⚠" in html


class TestFeatureLevelFindings:
    def test_feature_findings_rendered_in_section(self, tmp_path: Path) -> None:
        out = tmp_path / "dashboard.html"
        ctx, findings, grades, history, summary = _deterministic_inputs()
        feat_finding = Finding(
            criterion_id="H7",
            severity=Severity.P2,
            scenario=None,
            feature=ctx.features[0],
            problem="All scenarios share @happy",
            evidence="only happy-path scenarios present",
            reason="Feature lacks failure coverage",
            fix_example="Add a @failure scenario for invalid input",
            is_recognized_criterion=True,
        )
        DashboardRenderer().render(
            ctx, findings + [feat_finding], grades, history, (), summary, None, out
        )
        html = out.read_text()
        assert "Feature-level findings" in html
        assert "H7" in html
        assert "All scenarios share @happy" in html

    def test_no_feature_section_when_empty(self, tmp_path: Path) -> None:
        out = tmp_path / "dashboard.html"
        ctx, findings, grades, history, summary = _deterministic_inputs()
        DashboardRenderer().render(ctx, findings, grades, history, (), summary, None, out)
        html = out.read_text()
        assert "Feature-level findings" not in html


class TestRunDataJsSafety:
    def test_script_breakout_in_history_is_escaped(self, tmp_path: Path) -> None:
        out = tmp_path / "dashboard.html"
        ctx, findings, grades, history, summary = _deterministic_inputs()
        poisoned_history = [
            RunSummary(
                timestamp="</script><script>alert(1)</script>",
                total_scenarios=1,
                passed=1,
                failed=0,
                skipped=0,
                finding_counts={Severity.P0: 0, Severity.P1: 0, Severity.P2: 0, Severity.P3: 0},
                model="claude-sonnet-4-6",
                cost=summary.cost,
                skipped_packages=(),
            )
        ]
        DashboardRenderer().render(ctx, findings, grades, poisoned_history, (), summary, None, out)
        html = out.read_text()
        # tojson escapes '/' so </script> cannot appear verbatim inside the
        # JSON island.
        assert "</script><script>alert(1)</script>" not in html


class TestCoverageCard:
    def test_card_present_when_context_provided(self, tmp_path: Path) -> None:
        from tools.dashboard.models import CoverageContext

        ctx, findings, grades, history, summary = _deterministic_inputs()
        cov_ctx = CoverageContext(
            timestamp="2026-04-24T12:00:00Z",
            totals_pct=69.0,
            totals_tone="warning",
            totals_covered_branches=98,
            totals_total_branches=142,
            endpoints_summary=(),
            endpoints_uncovered_flat={},
            audit_reconciled=True,
            audit_unattributed_count=0,
        )
        out = tmp_path / "dashboard.html"
        DashboardRenderer().render(ctx, findings, grades, history, (), summary, cov_ctx, out)
        html = out.read_text()
        assert "Code coverage" in html
        assert "69%" in html
        assert "98/142 branches" in html

    def test_placeholder_when_context_none(self, tmp_path: Path) -> None:
        ctx, findings, grades, history, summary = _deterministic_inputs()
        out = tmp_path / "dashboard.html"
        DashboardRenderer().render(ctx, findings, grades, history, (), summary, None, out)
        html = out.read_text()
        assert "Code coverage" in html
        assert "make bdd-coverage" in html

    def test_audit_failed_subtitle(self, tmp_path: Path) -> None:
        from tools.dashboard.models import CoverageContext

        ctx, findings, grades, history, summary = _deterministic_inputs()
        cov_ctx = CoverageContext(
            timestamp="2026-04-24T12:00:00Z",
            totals_pct=50.0,
            totals_tone="error",
            totals_covered_branches=5,
            totals_total_branches=10,
            endpoints_summary=(),
            endpoints_uncovered_flat={},
            audit_reconciled=False,
            audit_unattributed_count=3,
        )
        out = tmp_path / "dashboard.html"
        DashboardRenderer().render(ctx, findings, grades, history, (), summary, cov_ctx, out)
        html = out.read_text()
        assert "audit failed" in html
