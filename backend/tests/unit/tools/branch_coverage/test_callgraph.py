"""Tests for CallGraphBuilder."""

from pathlib import Path

from tools.branch_coverage.callgraph import CallGraph, CallGraphBuilder


class TestBuildOnMinimalApp:
    def test_returns_callgraph(self, minimal_app_source_root: Path) -> None:
        cg = CallGraphBuilder().build(minimal_app_source_root)
        assert isinstance(cg, CallGraph)
        assert isinstance(cg.adjacency, dict)

    def test_adjacency_nonempty_on_real_app(self, minimal_app_source_root: Path) -> None:
        # Live pyan3 against the fixture; exact node names depend on
        # pyan3's qualname resolution, but the graph must be non-empty.
        cg = CallGraphBuilder().build(minimal_app_source_root)
        assert len(cg.adjacency) > 0

    def test_make_guess_reaches_validate_letter(self, minimal_app_source_root: Path) -> None:
        # make_guess calls validate_letter — pyan3 should trace this.
        cg = CallGraphBuilder().build(minimal_app_source_root)
        # Allow qualname to be fully-qualified or suffix-only — search
        # for any key that ends with "make_guess".
        make_guess_callees = [
            callees for name, callees in cg.adjacency.items() if name.endswith("make_guess")
        ]
        assert make_guess_callees, "make_guess not found in adjacency map"
        # At least one callee should contain "validate_letter".
        assert any(
            any("validate_letter" in callee for callee in callees) for callees in make_guess_callees
        )


class TestDegradedPath:
    def test_pyan3_exception_returns_empty_graph(
        self, monkeypatch, minimal_app_source_root: Path
    ) -> None:
        # Mock pyan's CallGraphVisitor to raise — builder must catch and
        # return an empty CallGraph, not propagate.
        class FakeVisitor:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("simulated pyan3 failure")

        monkeypatch.setattr("pyan.analyzer.CallGraphVisitor", FakeVisitor)
        cg = CallGraphBuilder().build(minimal_app_source_root)
        assert cg.adjacency == {}
