"""JsonEmitter: CoverageReport -> coverage.json.

Deterministic output: stable field order, sorted iteration, enum values
as strings. Golden-file test ensures bit-for-bit reproducibility.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.branch_coverage.models import (
    CoveragePerEndpoint,
    CoverageReport,
)


class JsonEmitter:
    def emit(self, report: CoverageReport, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self._to_dict(report), indent=2))

    def _to_dict(self, report: CoverageReport) -> dict[str, Any]:
        return {
            "version": report.version,
            "timestamp": report.timestamp,
            "cucumber_ndjson": report.cucumber_ndjson,
            "instrumented": report.instrumented,
            "thresholds": dict(report.thresholds),
            "totals": {
                "total_branches": report.totals.total_branches,
                "covered_branches": report.totals.covered_branches,
                "pct": report.totals.pct,
                "tone": report.totals.tone.value,
            },
            "endpoints": [self._endpoint_dict(ep) for ep in report.endpoints],
            "extra_coverage": [
                {"file": ec.file, "qualname": ec.qualname, "reason": ec.reason}
                for ec in report.extra_coverage
            ],
            "audit": {
                "total_branches_per_coverage_py": report.audit.total_branches_per_coverage_py,
                "total_branches_enumerated_via_reachability": report.audit.total_branches_enumerated_via_reachability,
                "extra_coverage_branches": report.audit.extra_coverage_branches,
                "unattributed_branches": [
                    {
                        "file": ub.file,
                        "line": ub.line,
                        "branch_id": ub.branch_id,
                        "reason": ub.reason,
                    }
                    for ub in report.audit.unattributed_branches
                ],
                "reconciled": report.audit.reconciled,
            },
        }

    def _endpoint_dict(self, ep: CoveragePerEndpoint) -> dict[str, Any]:
        return {
            "method": ep.endpoint.method,
            "path": ep.endpoint.path,
            "handler_qualname": ep.endpoint.handler_qualname,
            "total_branches": ep.total_branches,
            "covered_branches": ep.covered_branches,
            "pct": ep.pct,
            "tone": ep.tone.value,
            "reachable_functions": [
                {
                    "file": fc.file,
                    "qualname": fc.qualname,
                    "total_branches": fc.total_branches,
                    "covered_branches": fc.covered_branches,
                    "pct": fc.pct,
                    "reached": fc.reached,
                    "uncovered_branches": [
                        {
                            "file": b.file,
                            "line": b.line,
                            "branch_id": b.branch_id,
                            "condition_text": b.condition_text,
                            "not_taken_to_line": b.not_taken_to_line,
                        }
                        for b in fc.uncovered_branches
                    ],
                }
                for fc in ep.reachable_functions
            ],
            "uncovered_branches_flat": [
                {
                    "file": b.file,
                    "line": b.line,
                    "branch_id": b.branch_id,
                    "condition_text": b.condition_text,
                    "not_taken_to_line": b.not_taken_to_line,
                    "function_qualname": b.function_qualname,
                }
                for b in ep.uncovered_branches_flat
            ],
        }
