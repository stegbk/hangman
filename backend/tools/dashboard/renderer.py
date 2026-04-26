"""DashboardRenderer: Jinja2 → single-file HTML.

render() is the I/O boundary: it builds the HTML and writes it to
output_path in one shot.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from tools.dashboard.models import (
    AnalysisContext,
    CoverageContext,
    CoverageGrade,
    CoverageState,
    Feature,
    Finding,
    Outcome,
    RunSummary,
    Severity,
    Step,
)

_OUTCOME_TONE: dict[Outcome, str] = {
    Outcome.PASSED: "success",
    Outcome.FAILED: "error",
    Outcome.SKIPPED: "warning",
    Outcome.NOT_RUN: "",
    Outcome.UNKNOWN: "warning",
}


# Chart.js 4.5.1 SRI hash (jsdelivr CDN). Pinned; update only on version bump.
# Obtained via: curl -sL https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js | openssl dgst -sha384 -binary | openssl base64 -A
_CHART_JS_SRI = "sha384-jb8JQMbMoBUzgWatfe6COACi2ljcDdZQ2OxczGA3bGNeWe+6DChMTBJemed7ZnvJ"


@dataclass(frozen=True)
class SummaryCard:
    title: str
    value: str
    subtitle: str
    tone: str


@dataclass(frozen=True)
class ScenarioView:
    id: str
    feature_file: str
    line: int
    name: str
    primary_tag: str
    is_smoke: bool
    outcome: str
    tone: str
    steps: tuple[Step, ...]
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class FeatureFindingsGroup:
    file: str
    name: str
    findings: tuple[Finding, ...]


class DashboardRenderer:
    def __init__(self) -> None:
        self._env = Environment(
            loader=PackageLoader("tools.dashboard", "templates"),
            autoescape=select_autoescape(["html", "j2"]),
            trim_blocks=False,
            lstrip_blocks=False,
        )

    def render(
        self,
        context: AnalysisContext,
        findings: list[Finding],
        grades: list[CoverageGrade],
        history: list[RunSummary],
        skipped_packages: tuple[str, ...],
        run_summary: RunSummary,
        coverage_context: CoverageContext | None,
        output_path: Path,
    ) -> None:
        template = self._env.get_template("base.html.j2")
        scenarios = self._build_scenario_views(context, findings)
        feature_findings = self._build_feature_finding_groups(context, findings)
        summary_cards = self._build_summary_cards(context, grades, run_summary, coverage_context)
        run_data = self._build_run_data(history, run_summary)

        html = template.render(
            context=context,
            run_summary=run_summary,
            summary_cards=summary_cards,
            scenarios=scenarios,
            feature_findings=feature_findings,
            skipped_packages=skipped_packages,
            run_data=run_data,
            chart_js_sri=_CHART_JS_SRI,
            cost_call_count=len(scenarios) + len(context.features),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html)

    def _build_scenario_views(
        self, context: AnalysisContext, findings: list[Finding]
    ) -> list[ScenarioView]:
        by_scenario: dict[tuple[str, int], list[Finding]] = {}
        for f in findings:
            if f.scenario is None:
                continue
            by_scenario.setdefault((f.scenario.feature_file, f.scenario.line), []).append(f)

        views: list[ScenarioView] = []
        for sc in context.scenarios:
            key = (sc.feature_file, sc.line)
            tone = self._outcome_tone(sc.outcome)
            views.append(
                ScenarioView(
                    id=f"{sc.feature_file.replace('/', '_').replace('.', '_')}_{sc.line}",
                    feature_file=sc.feature_file,
                    line=sc.line,
                    name=sc.name,
                    primary_tag=sc.primary_tag or "",
                    is_smoke=sc.is_smoke,
                    outcome=sc.outcome.value,
                    tone=tone,
                    steps=sc.steps,
                    findings=tuple(by_scenario.get(key, [])),
                )
            )
        return views

    def _outcome_tone(self, outcome: Outcome) -> str:
        return _OUTCOME_TONE[outcome]

    def _build_feature_finding_groups(
        self, context: AnalysisContext, findings: list[Finding]
    ) -> list[FeatureFindingsGroup]:
        by_file: dict[str, list[Finding]] = {}
        for f in findings:
            if f.feature is None:
                continue
            by_file.setdefault(f.feature.file, []).append(f)
        if not by_file:
            return []
        feature_by_file: dict[str, Feature] = {feat.file: feat for feat in context.features}
        groups: list[FeatureFindingsGroup] = []
        for file, fs in sorted(by_file.items()):
            feat = feature_by_file.get(file)
            groups.append(
                FeatureFindingsGroup(
                    file=file,
                    name=feat.name if feat else file,
                    findings=tuple(fs),
                )
            )
        return groups

    def _build_summary_cards(
        self,
        context: AnalysisContext,
        grades: list[CoverageGrade],
        summary: RunSummary,
        coverage_context: CoverageContext | None,
    ) -> list[SummaryCard]:
        total = summary.total_scenarios
        passed = summary.passed
        pct = f"{passed / total * 100:.0f}" if total else "0"

        endpoint_grades = [g for g in grades if g.kind == "endpoint"]
        uc_grades = [g for g in grades if g.kind == "uc"]

        def counts(grs: list[CoverageGrade]) -> tuple[int, int, int]:
            full = sum(1 for g in grs if g.state == CoverageState.FULL)
            partial = sum(1 for g in grs if g.state == CoverageState.PARTIAL)
            none = sum(1 for g in grs if g.state == CoverageState.NONE)
            return full, partial, none

        ef, ep, en = counts(endpoint_grades)
        uf, up, un = counts(uc_grades)

        smoke_scenarios = [s for s in context.scenarios if s.is_smoke]
        smoke_passed = sum(1 for s in smoke_scenarios if s.outcome == Outcome.PASSED)

        p0 = summary.finding_counts.get(Severity.P0, 0)
        p1 = summary.finding_counts.get(Severity.P1, 0)
        p2 = summary.finding_counts.get(Severity.P2, 0)

        cards = [
            SummaryCard(
                title="Total scenarios",
                value=str(total),
                subtitle=f"{len(context.features)} features",
                tone="",
            ),
            SummaryCard(
                title="Passing",
                value=f"{passed}/{total} ({pct}%)",
                subtitle=f"@smoke: {smoke_passed}/{len(smoke_scenarios)}",
                tone="success" if passed == total else "warning",
            ),
            SummaryCard(
                title="Endpoint coverage",
                value=f"{ef}/{len(endpoint_grades)} Full",
                subtitle=f"{ep} Partial · {en} None",
                tone="success" if ep == 0 and en == 0 else "warning",
            ),
            SummaryCard(
                title="UC coverage",
                value=f"{uf}/{len(uc_grades)} Full",
                subtitle=f"{up} Partial · {un} None",
                tone="success" if up == 0 and un == 0 else "warning",
            ),
            SummaryCard(
                title="P0 findings",
                value=str(p0),
                subtitle="Broken",
                tone="error" if p0 else "",
            ),
            SummaryCard(
                title="P1 findings",
                value=str(p1),
                subtitle="Wrong",
                tone="error" if p1 else "",
            ),
            SummaryCard(
                title="P2 findings",
                value=str(p2),
                subtitle="Poor",
                tone="warning" if p2 else "",
            ),
        ]

        # New "Code coverage" card (Feature 3 augment).
        if coverage_context is not None:
            audit_suffix = " · ⚠ audit failed" if not coverage_context.audit_reconciled else ""
            cards.append(
                SummaryCard(
                    title="Code coverage",
                    value=f"{coverage_context.totals_pct:.0f}%",
                    subtitle=(
                        f"{coverage_context.totals_covered_branches}/"
                        f"{coverage_context.totals_total_branches} branches"
                        f"{audit_suffix}"
                    ),
                    tone=coverage_context.totals_tone,
                )
            )
        else:
            cards.append(
                SummaryCard(
                    title="Code coverage",
                    value="—",
                    subtitle="Run `make bdd-coverage` to enable",
                    tone="",
                )
            )

        return cards

    def _build_run_data(self, history: list[RunSummary], current: RunSummary) -> dict[str, object]:
        hist = [
            {
                "timestamp": h.timestamp,
                "passed": h.passed,
                "failed": h.failed,
                "p0p1": h.finding_counts.get(Severity.P0, 0) + h.finding_counts.get(Severity.P1, 0),
            }
            for h in history
        ]
        severity_counts = [
            current.finding_counts.get(Severity.P0, 0),
            current.finding_counts.get(Severity.P1, 0),
            current.finding_counts.get(Severity.P2, 0),
            current.finding_counts.get(Severity.P3, 0),
        ]
        return {"history": hist, "severity_counts": severity_counts}
