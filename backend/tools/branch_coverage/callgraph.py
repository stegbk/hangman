"""CallGraphBuilder: static call-graph via pyan3's Python API.

Returns an adjacency map keyed by fully-qualified name. Subprocess +
DOT parsing rejected — pyan3 exposes CallGraphVisitor directly.

Degraded path: if pyan3 raises (API drift, parseable source), log and
return an empty graph. Caller (Analyzer) still emits a valid report;
audit reconciliation surfaces everything as unattributed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class CallGraph:
    """Adjacency map: dict[qualname, frozenset[callee_qualname]]."""

    adjacency: dict[str, frozenset[str]]


class CallGraphBuilder:
    def build(self, source_root: Path) -> CallGraph:
        """Analyze *.py files under source_root with pyan3.

        Returns a CallGraph. On pyan3 failure, returns an empty graph
        (logs error). Never raises.
        """
        try:
            from pyan.analyzer import CallGraphVisitor  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover — dev-group dep
            _LOG.error("pyan3 not installed: %s", exc)
            return CallGraph(adjacency={})

        files = [str(f) for f in source_root.rglob("*.py")]
        if not files:
            _LOG.warning("No .py files under %s; empty call graph", source_root)
            return CallGraph(adjacency={})

        try:
            visitor = CallGraphVisitor(files)
        except Exception as exc:  # noqa: BLE001 — pyan3 can raise anything
            _LOG.error(
                "pyan3 CallGraphVisitor failed on %s: %s. Returning empty graph.",
                source_root,
                exc,
            )
            return CallGraph(adjacency={})

        adjacency: dict[str, frozenset[str]] = {}
        # pyan3 2.5.0 exposes the call graph in `uses_edges`:
        # dict[Node, set[Node]]. The instance attribute `uses_graph`
        # exists too but is None on instances — A3 spike (2026-04-24)
        # verified: only `uses_edges` is populated. Use it as the source
        # of truth. `getattr(..., {})` keeps the degraded path safe if a
        # future pyan release ever drops `uses_edges`.
        uses_edges = getattr(visitor, "uses_edges", {})
        for caller, callees in uses_edges.items():
            caller_name = self._node_name(caller)
            callee_names = frozenset(self._node_name(c) for c in callees)
            adjacency[caller_name] = callee_names
        return CallGraph(adjacency=adjacency)

    @staticmethod
    def _node_name(node: object) -> str:
        """Derive a qualified name from a pyan3 Node. Attribute names
        differ slightly between pyan3 versions; try common ones, fall
        back to str()."""
        for attr in ("get_name", "fullname", "name"):
            method_or_val = getattr(node, attr, None)
            if callable(method_or_val):
                try:
                    return str(method_or_val())
                except Exception:  # noqa: BLE001
                    continue
            if isinstance(method_or_val, str):
                return method_or_val
        return str(node)
