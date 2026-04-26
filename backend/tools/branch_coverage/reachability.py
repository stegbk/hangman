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
from collections.abc import Iterator
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
        enumerate branches via AST.

        Per /simplify pass: shared helpers reachable from N endpoints
        are AST-parsed once and cached for the rest of `compute()`.
        Without the cache, `_branches_for(qualname)` would re-resolve
        + re-parse the same file once per endpoint that reaches it
        (O(E × R) work where R = unique reachable qualnames). With
        the cache, each qualname is resolved once (O(R + E)).
        """
        branches_cache: dict[str, list[ReachableBranch]] = {}
        result: dict[Endpoint, list[ReachableBranch]] = {}
        for ep in endpoints:
            reachable_qualnames = self._bfs(ep.handler_qualname, graph)
            branches: list[ReachableBranch] = []
            for qualname in reachable_qualnames:
                cached = branches_cache.get(qualname)
                if cached is None:
                    cached = self._branches_for(qualname, source_root)
                    branches_cache[qualname] = cached
                branches.extend(cached)
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
        resolved = self._resolve_source_file(qualname, source_root)
        if resolved is None:
            return []
        source_file, module_path = resolved
        try:
            tree = ast.parse(source_file.read_text())
        except (OSError, SyntaxError) as exc:
            _LOG.warning("Failed to parse %s: %s", source_file, exc)
            return []

        # Tail beyond the module portion identifies the (possibly
        # class-nested) function. e.g. for module=pkg.api and
        # qualname=pkg.api.Controller.create, tail=["Controller", "create"].
        tail_str = (
            qualname[len(module_path) :].lstrip(".") if qualname.startswith(module_path) else ""
        )
        tail = tail_str.split(".") if tail_str else []
        func_def = self._find_function(tree, tail)
        if func_def is None:
            return []

        rel_file = self._format_path(source_file, source_root)
        branches: list[ReachableBranch] = []
        # Per H1 live-smoke audit reconciliation: coverage.py's
        # `branch = true` does NOT classify `except` clauses as branch
        # source-lines (verified on 7.13.5 against the real Hangman
        # codebase: `Analysis.branch_stats()` returns only `if/elif/while/for`
        # source-lines). Enumerating `ast.Try.handlers` as branches
        # over-counts by 1 per except clause and breaks audit
        # reconciliation. Reachability must mirror coverage.py's branch
        # semantics for the audit invariant to hold.
        #
        # Per Phase 5 iter 6 P2 (Codex): we MUST stop the AST walk at
        # nested FunctionDef / AsyncFunctionDef / ClassDef bodies. A naïve
        # `ast.walk(func_def)` traverses into closures, local helper
        # functions, and class bodies — counting THEIR branches as the
        # enclosing function's. That inflates per-function totals,
        # creates phantom uncovered branches, and breaks audit
        # reconciliation when those nested helpers are never called.
        # `_walk_skip_nested` recurses through children but treats each
        # nested function/class as opaque (its own reachability concern).
        for node in self._walk_skip_nested(func_def):
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
        return branches

    @staticmethod
    def _walk_skip_nested(root: ast.AST) -> Iterator[ast.AST]:
        """Yield every descendant of ``root`` EXCEPT the bodies of nested
        FunctionDef / AsyncFunctionDef / ClassDef. The nested defs
        themselves are yielded (a caller may want to know they exist),
        but recursion stops at their boundaries — their branches belong
        to those nested scopes, not ``root``.

        Per Phase 5 iter 6 P2 (Codex): replaces a previous `ast.walk`
        that incorrectly counted nested-helper branches as the enclosing
        function's.
        """
        stack: list[ast.AST] = [root]
        while stack:
            node = stack.pop()
            yield node
            if node is not root and isinstance(
                node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
            ):
                # Stop here — don't descend into the nested scope.
                continue
            stack.extend(ast.iter_child_nodes(node))

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

    def _resolve_source_file(self, qualname: str, source_root: Path) -> tuple[Path, str] | None:
        """Map a qualified name (module.path[.Class].func) to (source_file, module_path).

        Some qualnames include class-nested functions (e.g.
        ``pkg.api.Controller.create``). The naive ``rsplit(".", 1)[0]``
        produces ``pkg.api.Controller``, which ``find_spec`` rejects with
        ModuleNotFoundError. To handle both cases, progressively shed
        trailing components from the right until ``find_spec`` succeeds
        or we run out of candidates.

        Returns ``(source_file, module_path)`` so the caller can compute
        the qualname tail (the "Class.func" portion) and walk it
        accurately. Returns None if the module isn't importable, has no
        origin, or lives outside ``source_root`` (boundary filter).
        """
        if "." not in qualname:
            return self._try_module(qualname, source_root)

        parts = qualname.split(".")
        # Try longest module candidates first (`pkg.api.Controller.create`
        # might genuinely be a submodule `Controller`); shed components
        # one at a time until something resolves.
        for end in range(len(parts) - 1, 0, -1):
            candidate = ".".join(parts[:end])
            resolved = self._try_module(candidate, source_root)
            if resolved is not None:
                return resolved
        return None

    @staticmethod
    def _try_module(module_path: str, source_root: Path) -> tuple[Path, str] | None:
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
        return source_file, module_path

    @staticmethod
    def _find_function(
        tree: ast.AST, tail: list[str]
    ) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        """Walk the qualname tail through nested ``ClassDef`` and
        ``FunctionDef`` bodies to locate the target function.

        For tail ``["Controller", "create"]``, descends into
        ``class Controller:`` then returns the nested ``def create``.
        For a bare tail ``["create"]`` (module-level function), matches
        the first module-level ``def create``. Walking explicit body
        children (not ``ast.walk``) prevents accidentally matching the
        first ``create`` in a sibling class with multiple ``create`` defs.
        """
        if not tail:
            return None

        def _walk(
            parent_body: list[ast.stmt], remaining: list[str]
        ) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
            if not remaining:
                return None
            head, *rest = remaining
            for node in parent_body:
                if not rest and isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    if node.name == head:
                        return node
                elif rest:
                    if isinstance(node, ast.ClassDef) and node.name == head:
                        found = _walk(node.body, rest)
                        if found is not None:
                            return found
                    elif (
                        isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
                        and node.name == head
                    ):
                        # Nested function (closure); descend into its body.
                        found = _walk(node.body, rest)
                        if found is not None:
                            return found
            return None

        if isinstance(tree, ast.Module):
            return _walk(tree.body, tail)
        return None

    @staticmethod
    def _condition_text(node: ast.AST) -> str:
        try:
            return ast.unparse(node).split("\n")[0].strip() or "(conditional arc)"
        except (ValueError, AttributeError, RecursionError) as exc:
            _LOG.debug("ast.unparse failed for %s: %s", type(node).__name__, exc)
            return "(conditional arc)"
