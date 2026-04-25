"""Tests for CoverageContextMiddleware.

We can't easily test `coverage.Coverage.current()` without actually
running coverage; these tests mock it via monkeypatch and assert the
middleware calls `switch_context` with the right label.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import coverage
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tools.branch_coverage.middleware import CoverageContextMiddleware


class _CovSpy:
    """Records every switch_context call.

    Per the post-D1 follow-up (coverage.py 7.13.5 buffer-flush bug — see
    middleware.py docstring "Reset trade-off"): the middleware does NOT
    call switch_context("") after each request. So `contexts_set` no
    longer requires a trailing "" reset; it just collects every non-empty
    label that was set.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []

    def switch_context(self, label: str) -> None:
        self.calls.append(label)

    @property
    def contexts_seen(self) -> set[str]:
        return {label for label in self.calls if label}


@pytest.fixture
def fake_coverage(monkeypatch) -> MagicMock:
    """Replace coverage.Coverage.current() with a MagicMock."""
    mock = MagicMock()
    mock.switch_context = MagicMock()
    monkeypatch.setattr(
        "coverage.Coverage.current",
        classmethod(lambda cls: mock),
    )
    return mock


@pytest.fixture
def instrumented_app(fake_coverage: MagicMock) -> TestClient:
    app = FastAPI()

    @app.get("/items/{item_id}")
    def read_item(item_id: str) -> dict:
        return {"id": item_id}

    @app.post("/items")
    def create_item() -> dict:
        return {"id": "new"}

    app.add_middleware(CoverageContextMiddleware)
    return TestClient(app)


class TestContextSwitching:
    def test_get_request_switches_context(
        self, instrumented_app: TestClient, fake_coverage: MagicMock
    ) -> None:
        instrumented_app.get("/items/abc123")
        calls = [call.args[0] for call in fake_coverage.switch_context.call_args_list]
        assert "GET /items/{item_id}" in calls  # matched route template

    def test_post_request_switches_context(
        self, instrumented_app: TestClient, fake_coverage: MagicMock
    ) -> None:
        instrumented_app.post("/items")
        calls = [call.args[0] for call in fake_coverage.switch_context.call_args_list]
        assert "POST /items" in calls

    def test_path_template_normalizes_across_concrete_paths(
        self, instrumented_app: TestClient, fake_coverage: MagicMock
    ) -> None:
        instrumented_app.get("/items/abc")
        instrumented_app.get("/items/xyz")
        calls = [call.args[0] for call in fake_coverage.switch_context.call_args_list]
        # Both requests should produce identical context labels.
        assert calls.count("GET /items/{item_id}") == 2

    def test_path_param_route_resolves_to_template(self, monkeypatch) -> None:
        """A request to /items/abc123 must trigger switch_context("GET /items/{item_id}")
        — the path TEMPLATE — not switch_context("GET /items/abc123").
        Per plan-review iter 6 P1: this was systematically broken before
        the route-matching fix."""
        test_app = FastAPI()

        @test_app.get("/items/{item_id}")
        async def _get_item(item_id: str) -> dict[str, str]:
            return {"id": item_id}

        spy = _CovSpy()
        monkeypatch.setattr(coverage.Coverage, "current", classmethod(lambda _cls: spy))

        test_app.add_middleware(CoverageContextMiddleware)
        client = TestClient(test_app)
        client.get("/items/abc123")

        assert "GET /items/{item_id}" in spy.contexts_seen, (
            f"Expected template, got {spy.contexts_seen!r}"
        )
        assert "GET /items/abc123" not in spy.contexts_seen, (
            "Concrete path leaked into switch_context — route matching broken."
        )


class TestDegradedPath:
    def test_no_coverage_active_is_noop(self, monkeypatch) -> None:
        """When Coverage.current() returns None, middleware must not
        raise — still call next(), still return the response."""
        monkeypatch.setattr(
            "coverage.Coverage.current",
            classmethod(lambda cls: None),
        )
        app = FastAPI()

        @app.get("/ping")
        def ping() -> dict:
            return {"ok": True}

        app.add_middleware(CoverageContextMiddleware)
        client = TestClient(app)
        resp = client.get("/ping")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}


class TestErrorHandling:
    def test_handler_exception_still_records_context(self, fake_coverage: MagicMock) -> None:
        """Even if the route handler raises, the middleware records its
        context label BEFORE the call_next — so the failed request's
        partial work is correctly attributed.

        Per the post-D1 follow-up (coverage.py 7.13.5 buffer-flush bug):
        the middleware no longer calls switch_context("") in a finally
        block. The exception path must still set the context label
        (which happens before call_next), and that label persists until
        the next request's switch_context() overrides it.
        """
        app = FastAPI()

        @app.get("/boom")
        def boom() -> dict:
            raise RuntimeError("handler failure")

        app.add_middleware(CoverageContextMiddleware)
        client = TestClient(app)
        # TestClient propagates the exception; wrap in pytest.raises.
        with pytest.raises(RuntimeError, match="handler failure"):
            client.get("/boom")
        calls = [call.args[0] for call in fake_coverage.switch_context.call_args_list]
        assert "GET /boom" in calls, f"Expected GET /boom in switch_context calls, got {calls}"
