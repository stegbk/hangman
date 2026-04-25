"""Hand-built adjacency map for tests that don't need to run pyan3.

Shape matches what CallGraphBuilder.build() returns: a CallGraph
dataclass with an adjacency map keyed by qualified name.
"""

from tools.branch_coverage.callgraph import CallGraph


def fake_graph_for_minimal_app() -> CallGraph:
    """Hand-built graph approximating what pyan3 returns for minimal_app/."""
    return CallGraph(
        adjacency={
            "tests.fixtures.branch_coverage.minimal_app.main.create_game": frozenset(),
            "tests.fixtures.branch_coverage.minimal_app.main.make_guess": frozenset(
                {
                    "tests.fixtures.branch_coverage.minimal_app.game.validate_letter",
                }
            ),
            "tests.fixtures.branch_coverage.minimal_app.game.validate_letter": frozenset(),
        }
    )
