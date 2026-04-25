"""Analyzer orchestrator — wires the branch coverage pipeline."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from tools.branch_coverage.models import AuditReport

_LOG = logging.getLogger(__name__)


class Analyzer:
    """Wires routes → callgraph → reachability → coverage_data → grader → emit/render."""

    def __init__(
        self,
        routes: Any,
        callgraph: Any,
        reachability: Any,
        coverage_data: Any,
        grader: Any,
        json_emitter: Any,
        renderer: Any,
    ) -> None:
        self.routes = routes
        self.callgraph = callgraph
        self.reachability = reachability
        self.coverage_data = coverage_data
        self.grader = grader
        self.json_emitter = json_emitter
        self.renderer = renderer

    def run(
        self,
        app: Any,
        coverage_file: Path,
        source_root: Path,
        json_output: Path,
        html_output: Path,
    ) -> None:
        endpoints = self.routes.enumerate(app)
        graph = self.callgraph.build(source_root)
        reach = self.reachability.compute(endpoints, graph, source_root)
        hits = self.coverage_data.load(coverage_file)
        report = self.grader.grade(reach, hits)
        self.json_emitter.emit(report, json_output)
        self.renderer.render(report, html_output)
        self._print_audit(report.audit)

    @staticmethod
    def _print_audit(audit: AuditReport) -> None:
        reconciled = "OK" if audit.reconciled else "MISMATCH"
        print(
            f"{reconciled} Audit: "
            f"coverage.py={audit.total_branches_per_coverage_py} - "
            f"enumerated={audit.total_branches_enumerated_via_reachability} - "
            f"unattributed={len(audit.unattributed_branches)} - "
            f"reconciled={audit.reconciled}",
            file=sys.stderr,
        )
        if not audit.reconciled:
            print(
                "WARNING: audit reconciliation failed - see coverage.html "
                "for the unattributed-branch list.",
                file=sys.stderr,
            )
