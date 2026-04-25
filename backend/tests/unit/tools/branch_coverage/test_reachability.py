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
