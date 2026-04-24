"""Analyzer orchestrator — wires the dashboard pipeline."""

from __future__ import annotations

import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from tools.dashboard.llm.cost import compute_cost
from tools.dashboard.models import (
    AnalysisContext,
    CostReport,
    Finding,
    Outcome,
    RunSummary,
    Severity,
)

_LOG = logging.getLogger(__name__)
_SEVERITY_ORDER = {Severity.P0: 0, Severity.P1: 1, Severity.P2: 2, Severity.P3: 3}


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    def key(f: Finding) -> tuple[int, str, str, int]:
        line = f.scenario.line if f.scenario else (f.feature.line if f.feature else 0)
        file = f.scenario.feature_file if f.scenario else (f.feature.file if f.feature else "")
        return (_SEVERITY_ORDER[f.severity], f.criterion_id, file, line)

    return sorted(findings, key=key)


class Analyzer:
    def __init__(
        self,
        parser: Any,
        grader: Any,
        packager: Any,
        llm: Any,
        history: Any,
        renderer: Any,
    ) -> None:
        self.parser = parser
        self.grader = grader
        self.packager = packager
        self.llm = llm
        self.history = history
        self.renderer = renderer

    def run(
        self,
        ndjson_path: Path,
        output_path: Path,
        history_dir: Path,
        features_glob: Path,
    ) -> None:
        parse_result = self.parser.parse(ndjson_path)
        self._warn_on_orphans(features_glob, parse_result.gherkin_document_uris)

        endpoint_index, uc_index, grades = self.grader.grade(parse_result.features)
        context = AnalysisContext(
            features=parse_result.features,
            scenarios=parse_result.scenarios,
            endpoint_index=endpoint_index,
            uc_index=uc_index,
            timestamp=parse_result.timestamp,
        )

        packages = self.packager.make_packages(parse_result.features)
        results, skipped = self.llm.evaluate(packages)
        findings = [f for r in results if r.succeeded for f in r.findings]
        findings = _sort_findings(findings)
        cost = compute_cost(list(results))

        summary = self._summarize(context, findings, cost, skipped)
        self.history.append(summary, history_dir)
        history_entries = self.history.read_all(history_dir)

        self.renderer.render(
            context,
            findings,
            list(grades),
            history_entries,
            skipped,
            summary,
            output_path,
        )
        self._print_cost_report(cost, skipped)

    def _warn_on_orphans(self, features_glob: Path, known_uris: frozenset[str]) -> None:
        if not features_glob.is_dir():
            return
        on_disk = {p.name for p in features_glob.rglob("*.feature")}
        ran = {uri.rsplit("/", 1)[-1] for uri in known_uris}
        orphans = on_disk - ran
        for o in sorted(orphans):
            _LOG.warning("Feature file on disk but not in NDJSON (orphan): %s", o)

    def _summarize(
        self,
        context: AnalysisContext,
        findings: list[Finding],
        cost: CostReport,
        skipped: tuple[str, ...],
    ) -> RunSummary:
        outcomes = Counter(sc.outcome for sc in context.scenarios)
        finding_counts: dict[Severity, int] = dict.fromkeys(Severity, 0)
        for f in findings:
            finding_counts[f.severity] = finding_counts.get(f.severity, 0) + 1
        return RunSummary(
            timestamp=context.timestamp,
            total_scenarios=len(context.scenarios),
            passed=outcomes.get(Outcome.PASSED, 0),
            failed=outcomes.get(Outcome.FAILED, 0),
            skipped=outcomes.get(Outcome.SKIPPED, 0),
            finding_counts=finding_counts,
            model=cost.model,
            cost=cost,
            skipped_packages=skipped,
        )

    def _print_cost_report(self, cost: CostReport, skipped: tuple[str, ...]) -> None:
        print(
            f"Model: {cost.model} · "
            f"Input: {cost.total_input_tokens} tokens · "
            f"Output: {cost.total_output_tokens} tokens · "
            f"Cache hit: {cost.cache_hit_rate * 100:.0f}% · "
            f"Total: ${cost.total_usd:.2f}",
            file=sys.stderr,
        )
        if skipped:
            print(
                f"Skipped packages ({len(skipped)}): {', '.join(skipped)}",
                file=sys.stderr,
            )
