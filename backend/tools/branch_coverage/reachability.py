"""Reachability: BFS from each endpoint's handler through the call graph
+ AST-based branch enumeration for each reachable function.

Boundary enforcement: only traverses into functions whose source file
lives under `source_root` (design spec §4.4, Q6 boundary).
"""

from __future__ import annotations

import ast
import importlib.util
import logging
from collections import deque
from pathlib import Path

from tools.branch_coverage.callgraph import CallGraph
from tools.branch_coverage.models import Endpoint, ReachableBranch

_LOG = logging.getLogger(__name__)


class Reachability:
    def compute(
        self,
        endpoints: tuple[Endpoint, ...],
        graph: CallGraph,
        source_root: Path,
    ) -> dict[Endpoint, list[ReachableBranch]]:
        """For each endpoint, BFS the call graph from its handler; for
        each reachable function whose file is under source_root,
        enumerate branches via AST."""
        result: dict[Endpoint, list[ReachableBranch]] = {}
        for ep in endpoints:
            reachable_qualnames = self._bfs(ep.handler_qualname, graph)
            branches: list[ReachableBranch] = []
            for qualname in reachable_qualnames:
                branches.extend(self._branches_for(qualname, source_root))
            result[ep] = branches
        return result

    def _bfs(self, start: str, graph: CallGraph) -> set[str]:
        visited: set[str] = set()
        queue: deque[str] = deque([start])
        while queue:
            name = queue.popleft()
            if name in visited:
                continue
            visited.add(name)
            for callee in graph.adjacency.get(name, frozenset()):
                if callee not in visited:
                    queue.append(callee)
        return visited

    def _branches_for(self, qualname: str, source_root: Path) -> list[ReachableBranch]:
        """Enumerate branches in the function identified by `qualname`.
        Boundary filter: only inspects functions whose source file lives
        under source_root."""
        source_file = self._resolve_source_file(qualname, source_root)
        if source_file is None:
            return []
        try:
            tree = ast.parse(source_file.read_text())
        except (OSError, SyntaxError) as exc:
            _LOG.warning("Failed to parse %s: %s", source_file, exc)
            return []

        func_def = self._find_function(tree, qualname)
        if func_def is None:
            return []

        rel_file = self._format_path(source_file, source_root)
        branches: list[ReachableBranch] = []
        for node in ast.walk(func_def):
            if isinstance(node, ast.If | ast.While | ast.For):
                line = node.lineno
                cond_text = self._condition_text(node)
                branches.append(
                    ReachableBranch(
                        file=rel_file,
                        line=line,
                        branch_id=f"{line}->{line + 1}",
                        condition_text=cond_text,
                        not_taken_to_line=line + 1,
                        function_qualname=qualname,
                    )
                )
            elif isinstance(node, ast.Try):
                # Each except clause is a branch arc.
                for handler in node.handlers:
                    line = handler.lineno
                    branches.append(
                        ReachableBranch(
                            file=rel_file,
                            line=line,
                            branch_id=f"{line}->{line + 1}",
                            condition_text=f"except {self._exception_type(handler)}",
                            not_taken_to_line=line + 1,
                            function_qualname=qualname,
                        )
                    )
        return branches

    @staticmethod
    def _format_path(source_file: Path, source_root: Path) -> str:
        """Emit a path matching coverage.py's `relative_files = true` output.

        For source_root = /<repo>/backend/src/hangman, source_root.parent.parent
        = /<repo>/backend, so emitted paths look like `src/hangman/game.py`.
        Falls back to absolute path when source_file is not under that anchor.
        """
        anchor = source_root.parent.parent
        if source_file.is_relative_to(anchor):
            return str(source_file.relative_to(anchor))
        return str(source_file)

    def _resolve_source_file(self, qualname: str, source_root: Path) -> Path | None:
        """Map a qualified name (module.path.func) to a source file path.
        Uses importlib to locate the module; returns None if the module
        is not under source_root (boundary filter)."""
        module_path = qualname.rsplit(".", 1)[0] if "." in qualname else qualname
        try:
            spec = importlib.util.find_spec(module_path)
        except (ImportError, ModuleNotFoundError, ValueError):
            return None
        if spec is None or spec.origin is None:
            return None
        source_file = Path(spec.origin)
        try:
            source_file.relative_to(source_root)
        except ValueError:
            return None  # not under source_root
        return source_file

    @staticmethod
    def _find_function(
        tree: ast.AST, qualname: str
    ) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        target_name = qualname.rsplit(".", 1)[-1]
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
                and node.name == target_name
            ):
                return node
        return None

    @staticmethod
    def _condition_text(node: ast.AST) -> str:
        try:
            return ast.unparse(node).split("\n")[0].strip() or "(conditional arc)"
        except Exception:  # noqa: BLE001
            return "(conditional arc)"

    @staticmethod
    def _exception_type(handler: ast.ExceptHandler) -> str:
        if handler.type is None:
            return "Exception"
        try:
            return ast.unparse(handler.type)
        except Exception:  # noqa: BLE001
            return "Exception"
