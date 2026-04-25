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
    CoverageContext,
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
        path = f.scenario.feature_file if f.scenario else (f.feature.file if f.feature else "")
        return (_SEVERITY_ORDER[f.severity], f.criterion_id, path, line)

    return sorted(findings, key=key)


def load_coverage_context_if_fresh(ndjson_path: Path) -> CoverageContext | None:
    """Returns CoverageContext if tests/bdd/reports/coverage.json
    exists AND its timestamp is within 1 hour of ndjson's mtime.
    Otherwise None.

    Module-level (not an Analyzer method) so __main__.py can call it
    before constructing Analyzer + LlmEvaluator.
    """
    import json
    from datetime import UTC, datetime, timedelta

    coverage_json_path = (
        ndjson_path.parent.parent.parent / "tests" / "bdd" / "reports" / "coverage.json"
    )
    if not coverage_json_path.exists():
        _LOG.info("No coverage.json found at %s — rendering placeholder", coverage_json_path)
        return None
    try:
        data = json.loads(coverage_json_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        _LOG.warning("coverage.json parse failed: %s", exc)
        return None
    cov_ts_str = data.get("timestamp", "")
    try:
        cov_ts = datetime.fromisoformat(cov_ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError) as exc:
        _LOG.warning("coverage.json timestamp %r unparseable: %s", cov_ts_str, exc)
        return None
    ndjson_mtime = datetime.fromtimestamp(ndjson_path.stat().st_mtime, tz=UTC)
    if abs((cov_ts - ndjson_mtime).total_seconds()) > timedelta(hours=1).total_seconds():
        _LOG.warning("coverage.json is stale vs. cucumber.ndjson — ignoring")
        return None
    return _build_coverage_context(data)


def _build_coverage_context(data: dict[str, Any]) -> CoverageContext | None:
    """Module-level helper. Underscore-prefixed (internal to analyzer.py).

    Returns None if ``data`` does not match the expected coverage.json
    schema (KeyError/TypeError on missing or wrong-typed fields). The
    caller treats None as "no coverage augmentation this run" and the
    dashboard renders without the coverage card. This keeps the
    dashboard robust against partial, hand-edited, or
    older-schema coverage.json artifacts.
    """
    try:
        # Per Phase 5 iter 2 P1 (Codex): coerce endpoint scalar types
        # (`float(ep["pct"])`) so a coverage.json with `pct: "80"` (string)
        # doesn't pass through here only to crash later in
        # `build_coverage_summary` at `f"{pct:.0f}"`. ValueError on type
        # mismatch is caught by the except below.
        endpoints_summary = tuple(
            (str(ep["method"]), str(ep["path"]), float(ep["pct"]), str(ep["tone"]))
            for ep in data.get("endpoints", [])
        )
        endpoints_uncovered_flat: dict[str, tuple[dict[str, Any], ...]] = {
            f"{ep['method']} {ep['path']}": tuple(ep.get("uncovered_branches_flat", []))
            for ep in data.get("endpoints", [])
        }
        totals = data.get("totals", {})
        audit = data.get("audit", {})
        # Per Phase 5 iter 2 P1 (Codex): coerce scalar types so that a
        # coverage.json with `pct: "75"` (string) doesn't pass through here
        # only to crash later in `build_coverage_summary` at
        # `f"{ctx.totals_pct:.0f}"`. float()/int()/str() raise ValueError
        # / TypeError on type mismatch — caught by the except below and
        # downgraded to a warning + None return (augmentation disabled).
        return CoverageContext(
            timestamp=str(data.get("timestamp", "")),
            totals_pct=float(totals.get("pct", 0.0)),
            totals_tone=str(totals.get("tone", "")),
            totals_covered_branches=int(totals.get("covered_branches", 0)),
            totals_total_branches=int(totals.get("total_branches", 0)),
            endpoints_summary=endpoints_summary,
            endpoints_uncovered_flat=endpoints_uncovered_flat,
            audit_reconciled=bool(audit.get("reconciled", True)),
            audit_unattributed_count=len(audit.get("unattributed_branches", [])),
        )
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        _LOG.warning("coverage.json schema mismatch — augmentation disabled: %s", exc)
        return None


def build_coverage_summary(ctx: CoverageContext) -> str:
    """Format a CoverageContext as the human/LLM-readable summary string
    that gets injected into the cached system prompt. Module-level so
    __main__.py can call it directly."""
    lines = [
        "## Coverage context for this run",
        "",
        f"The BDD suite achieved {ctx.totals_pct:.0f}% branch coverage "
        f"on backend/src/hangman/ "
        f"({ctx.totals_covered_branches} of {ctx.totals_total_branches} branches).",
        "",
        "Per-endpoint uncovered branches (use when emitting D7 findings):",
    ]
    for method, path, pct, _tone in ctx.endpoints_summary:
        key = f"{method} {path}"
        uncovered = ctx.endpoints_uncovered_flat.get(key, ())
        if not uncovered:
            continue
        lines.append(f"- {method} {path} ({pct:.0f}% covered):")
        for b in uncovered[:10]:  # cap at 10 per endpoint to keep prompt small
            lines.append(
                f'  - {b.get("file", "?")}:{b.get("line", "?")} "{b.get("condition_text", "?")}"'
            )
    lines.append("")
    lines.append(
        "When evaluating scenarios, reference this data. If a scenario hits "
        "an endpoint with uncovered branches, emit a D7 finding only if the "
        "scenario plausibly could exercise those branches and doesn't."
    )
    return "\n".join(lines)


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
        coverage_context: CoverageContext | None = None,
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
            coverage_context,
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
            finding_counts[f.severity] += 1
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
