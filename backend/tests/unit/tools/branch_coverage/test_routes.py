"""Tests for RouteEnumerator."""

from tools.branch_coverage.models import Endpoint
from tools.branch_coverage.routes import RouteEnumerator


class TestEnumerateMinimalApp:
    def test_returns_endpoint_tuple(self) -> None:
        from tests.fixtures.branch_coverage.minimal_app.main import app

        endpoints = RouteEnumerator().enumerate(app)
        assert isinstance(endpoints, tuple)
        assert all(isinstance(e, Endpoint) for e in endpoints)

    def test_extracts_both_routes(self) -> None:
        from tests.fixtures.branch_coverage.minimal_app.main import app

        endpoints = RouteEnumerator().enumerate(app)
        paths_methods = {(e.method, e.path) for e in endpoints}
        assert ("POST", "/api/v1/games") in paths_methods
        assert ("POST", "/api/v1/games/{game_id}/guesses") in paths_methods

    def test_preserves_path_parameters(self) -> None:
        from tests.fixtures.branch_coverage.minimal_app.main import app

        endpoints = RouteEnumerator().enumerate(app)
        guesses = next(e for e in endpoints if "guesses" in e.path)
        assert "{game_id}" in guesses.path

    def test_extracts_handler_qualname(self) -> None:
        from tests.fixtures.branch_coverage.minimal_app.main import app

        endpoints = RouteEnumerator().enumerate(app)
        create = next(e for e in endpoints if e.path == "/api/v1/games")
        assert "create_game" in create.handler_qualname

    def test_deterministic_order(self) -> None:
        from tests.fixtures.branch_coverage.minimal_app.main import app

        a = RouteEnumerator().enumerate(app)
        b = RouteEnumerator().enumerate(app)
        assert a == b


class TestFiltersNonApiRoutes:
    def test_skips_websocket_and_head_only_routes(self) -> None:
        from fastapi import FastAPI

        # FastAPI's built-in /docs, /redoc, /openapi.json are filtered
        # via openapi_url=None + docs_url=None + redoc_url=None so the
        # bare app exposes zero HTTP routes — this isolates the
        # enumerator's "skip routes without HTTP methods" behavior.
        bare_app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
        endpoints = RouteEnumerator().enumerate(bare_app)
        assert endpoints == ()

    def test_default_fastapi_docs_routes_are_filtered(self) -> None:
        """Per Phase 5 code-review iter 1 P2: a default FastAPI() app
        registers /docs, /redoc, and /openapi.json. These are framework
        infrastructure (not user endpoints) and inflate the audit
        denominator. RouteEnumerator must filter them out."""
        from fastapi import FastAPI

        # Default FastAPI app — docs/redoc/openapi.json all enabled.
        app = FastAPI()

        @app.get("/api/v1/things")
        def list_things() -> dict:
            return {"things": []}

        endpoints = RouteEnumerator().enumerate(app)
        paths = {e.path for e in endpoints}
        # The user route is present.
        assert "/api/v1/things" in paths
        # The framework routes are filtered.
        assert "/docs" not in paths
        assert "/redoc" not in paths
        assert "/openapi.json" not in paths
        assert "/docs/oauth2-redirect" not in paths


class TestNestedRouterPrefix:
    """Per plan-review iter 1 P2: real hangman code uses
    app.include_router(prefix="/api/v1", ...). The minimal_app fixture
    already exercises a prefixed APIRouter at the top level; this test
    adds a second router to verify multiple prefixed routers stack
    correctly."""

    def test_multiple_prefixed_routers(self) -> None:
        from fastapi import APIRouter, FastAPI

        app = FastAPI()
        v1 = APIRouter(prefix="/api/v1")
        v2 = APIRouter(prefix="/api/v2")

        @v1.get("/items")
        def list_v1() -> dict:
            return {"v": 1}

        @v2.get("/items")
        def list_v2() -> dict:
            return {"v": 2}

        app.include_router(v1)
        app.include_router(v2)

        endpoints = RouteEnumerator().enumerate(app)
        paths = [e.path for e in endpoints]
        assert "/api/v1/items" in paths
        assert "/api/v2/items" in paths

    def test_double_nested_prefix(self) -> None:
        """Router prefix nesting: outer prefix '/api/v1' + inner router
        with prefix '/games' → resolved path is '/api/v1/games'."""
        from fastapi import APIRouter, FastAPI

        app = FastAPI()
        outer = APIRouter(prefix="/api/v1")
        inner = APIRouter(prefix="/games")

        @inner.get("/{game_id}")
        def get_game(game_id: str) -> dict:
            return {"id": game_id}

        outer.include_router(inner)
        app.include_router(outer)

        endpoints = RouteEnumerator().enumerate(app)
        paths = [e.path for e in endpoints]
        assert "/api/v1/games/{game_id}" in paths
