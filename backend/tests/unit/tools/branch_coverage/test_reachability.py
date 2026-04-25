"""Tests for Reachability."""

from pathlib import Path

from tools.branch_coverage.models import Endpoint, ReachableBranch
from tools.branch_coverage.reachability import Reachability

from tests.fixtures.branch_coverage.fake_adjacency import fake_graph_for_minimal_app


def _endpoint(path: str, handler: str) -> Endpoint:
    return Endpoint(method="POST", path=path, handler_qualname=handler)


class TestBFSReachability:
    def test_handler_with_no_calls_yields_only_its_own_branches(
        self, minimal_app_source_root: Path
    ) -> None:
        ep = _endpoint(
            "/api/v1/games",
            "tests.fixtures.branch_coverage.minimal_app.main.create_game",
        )
        result = Reachability().compute(
            (ep,), fake_graph_for_minimal_app(), minimal_app_source_root
        )
        assert ep in result
        # create_game has no branches; expect empty
        assert result[ep] == []

    def test_handler_with_transitive_call_reaches_validate_letter_branches(
        self, minimal_app_source_root: Path
    ) -> None:
        ep = _endpoint(
            "/api/v1/games/{game_id}/guesses",
            "tests.fixtures.branch_coverage.minimal_app.main.make_guess",
        )
        result = Reachability().compute(
            (ep,), fake_graph_for_minimal_app(), minimal_app_source_root
        )
        branches = result[ep]
        assert len(branches) >= 3, (
            f"expected >= 3 branches from validate_letter; got {len(branches)}"
        )
        assert all(isinstance(b, ReachableBranch) for b in branches)
        # At least one branch should be from validate_letter.
        assert any("validate_letter" in b.function_qualname for b in branches)

    def test_handler_not_in_graph_returns_empty_list(self, minimal_app_source_root: Path) -> None:
        ep = _endpoint("/nowhere", "hangman.nonexistent.handler")
        result = Reachability().compute(
            (ep,), fake_graph_for_minimal_app(), minimal_app_source_root
        )
        # Not in graph → empty; should not raise.
        assert result[ep] == []

    def test_cycle_handling(self, minimal_app_source_root: Path) -> None:
        # Hand-build a cyclic graph (a→b→a) and make sure BFS terminates.
        from tools.branch_coverage.callgraph import CallGraph

        cyclic = CallGraph(
            adjacency={
                "pkg.a": frozenset({"pkg.b"}),
                "pkg.b": frozenset({"pkg.a"}),
            }
        )
        ep = _endpoint("/x", "pkg.a")
        # Source files don't exist for pkg.a/pkg.b — Reachability should
        # skip them (boundary filter). Must not loop.
        result = Reachability().compute((ep,), cyclic, minimal_app_source_root)
        assert result[ep] == []


class TestBranchEnumeration:
    def test_parses_if_elif_else_chain(self, minimal_app_source_root: Path) -> None:
        # validate_letter has 3 if statements — each is one branch arc.
        ep = _endpoint(
            "/api/v1/games/{game_id}/guesses",
            "tests.fixtures.branch_coverage.minimal_app.main.make_guess",
        )
        result = Reachability().compute(
            (ep,), fake_graph_for_minimal_app(), minimal_app_source_root
        )
        branches = result[ep]
        condition_texts = [b.condition_text for b in branches]
        # Condition text is best-effort; accept any non-empty string.
        assert all(ct for ct in condition_texts)

    def test_nested_def_branches_belong_to_nested_scope_not_outer(self, tmp_path: Path) -> None:
        """Per Phase 5 iter 6 P2 (Codex): `_branches_for` previously used
        `ast.walk` which traversed into nested function/class bodies,
        counting their branches as the enclosing function's. That
        inflates per-endpoint totals when the helper is never called and
        breaks audit reconciliation.

        This test builds an outer function with ONE direct `if` branch
        plus a nested helper containing TWO `if` branches that should
        NOT count toward the outer function. Reachability with the call
        graph hitting only `outer` must return EXACTLY 1 branch.
        """
        import sys

        from tools.branch_coverage.callgraph import CallGraph

        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "mod.py").write_text(
            "def outer(x):\n"
            "    if x > 0:\n"  # outer's only branch — line 2
            "        return 1\n"
            "    def _helper(y):\n"  # nested def
            "        if y < 0:\n"  # phantom branch (line 5) — should NOT count
            "            return -1\n"
            "        if y == 0:\n"  # phantom branch (line 7) — should NOT count
            "            return 0\n"
            "        return 1\n"
            "    return 0\n"
        )

        sys.path.insert(0, str(tmp_path))
        try:
            import importlib

            importlib.invalidate_caches()

            graph = CallGraph(adjacency={"pkg.mod.outer": frozenset()})
            ep = _endpoint("/x", "pkg.mod.outer")
            result = Reachability().compute((ep,), graph, tmp_path)

            assert len(result[ep]) == 1, (
                f"Expected exactly 1 branch (outer's `if x > 0` at line 2); "
                f"got {len(result[ep])}: "
                f"{[(b.line, b.condition_text) for b in result[ep]]}. "
                f"Nested-def branches must NOT count toward the outer function."
            )
            assert result[ep][0].line == 2, (
                f"Expected branch at line 2 (outer's `if`), got line {result[ep][0].line}"
            )
        finally:
            sys.path.remove(str(tmp_path))
            for mod_name in [m for m in list(sys.modules) if m == "pkg" or m.startswith("pkg.")]:
                sys.modules.pop(mod_name, None)

    def test_except_handlers_are_not_enumerated_as_branches(self, tmp_path: Path) -> None:
        """Per H1 live-smoke audit reconciliation: coverage.py 7.13.5 with
        `branch = true` does NOT classify `except` clauses as branch
        source-lines (verified via `Analysis.branch_stats()` on the real
        Hangman codebase). Reachability must mirror coverage.py's branch
        semantics — enumerating `ast.Try.handlers` over-counts and breaks
        the audit invariant.
        """
        from tools.branch_coverage.callgraph import CallGraph

        # Build a minimal source tree with a single try/except function
        # that has NO if/while/for branches — only an except clause.
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "mod.py").write_text(
            "def f(x):\n    try:\n        return int(x)\n    except ValueError:\n        return 0\n"
        )

        graph = CallGraph(adjacency={"pkg.mod.f": frozenset()})
        ep = _endpoint("/x", "pkg.mod.f")
        result = Reachability().compute((ep,), graph, tmp_path)
        # Function has no if/while/for, only an except handler.
        # Expected: 0 branches (except clauses are NOT branch source-lines).
        assert result[ep] == [], (
            f"except handlers must not be enumerated as branches; got {result[ep]}"
        )


class TestBoundaryEnforcement:
    def test_function_outside_source_root_is_excluded(
        self, minimal_app_source_root: Path, tmp_path: Path
    ) -> None:
        # Graph says pkg.a calls pkg.b, but neither is under source_root.
        # Reachability must skip both (boundary).
        from tools.branch_coverage.callgraph import CallGraph

        external = CallGraph(adjacency={"pkg.a": frozenset({"pkg.b"}), "pkg.b": frozenset()})
        ep = _endpoint("/x", "pkg.a")
        result = Reachability().compute((ep,), external, minimal_app_source_root)
        assert result[ep] == []


class TestClassMethodQualnameResolution:
    """Per Phase 5 code-review iter 1 P1: class-method qualnames like
    ``pkg.api.Controller.create`` were silently dropped because
    ``rsplit(".", 1)[0]`` produced ``pkg.api.Controller`` (not a module),
    and ``find_function`` matched the first ``create`` it saw via
    ``ast.walk`` — both bugs masked branches in real handlers."""

    def test_class_method_qualname_resolves_to_method_branches(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        # Arrange: build a source tree that mimics ``pkg.api`` with a
        # class ``Controller`` containing a method ``create`` that has
        # branches, plus a SIBLING ``create`` method on a different class
        # to verify the walker descends into the right class (not just
        # the first ``def create`` it finds).
        import sys

        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "api.py").write_text(
            "class Other:\n"
            "    def create(self, x):\n"  # decoy — must NOT be matched
            "        return x\n"
            "\n"
            "class Controller:\n"
            "    def create(self, x):\n"
            "        if x > 0:\n"
            "            return 'pos'\n"
            "        if x < 0:\n"
            "            return 'neg'\n"
            "        return 'zero'\n"
        )

        # Insert tmp_path at the front of sys.path so importlib.find_spec
        # can locate ``pkg.api``. Use monkeypatch via a context manager so
        # we restore sys.path on test exit.
        sys.path.insert(0, str(tmp_path))
        try:
            # Invalidate any cached import state from a sibling test.
            import importlib

            importlib.invalidate_caches()

            from tools.branch_coverage.callgraph import CallGraph

            graph = CallGraph(adjacency={"pkg.api.Controller.create": frozenset()})
            ep = _endpoint("/x", "pkg.api.Controller.create")

            # Act
            result = Reachability().compute((ep,), graph, tmp_path)

            # Assert: 2 branches (the two `if` statements in Controller.create);
            # zero branches from Other.create (which has none). The presence
            # of >= 1 branch proves the resolver handled `Controller.create`
            # qualname AND the walker found Controller.create specifically.
            branches = result[ep]
            assert len(branches) == 2, (
                f"expected 2 branches from Controller.create, got {len(branches)}: "
                f"{[b.condition_text for b in branches]}"
            )
            assert all(b.function_qualname == "pkg.api.Controller.create" for b in branches)
            # Sanity: condition text reflects the Controller body, not Other.
            condition_texts = [b.condition_text for b in branches]
            assert any("x > 0" in ct for ct in condition_texts)
            assert any("x < 0" in ct for ct in condition_texts)
        finally:
            sys.path.remove(str(tmp_path))
            # Drop cached ``pkg`` so other tests using tmp_path-based
            # ``pkg`` packages don't collide.
            for mod_name in [m for m in list(sys.modules) if m == "pkg" or m.startswith("pkg.")]:
                sys.modules.pop(mod_name, None)
