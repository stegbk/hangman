"""CoverageContextMiddleware: per-endpoint attribution for coverage.py.

Calls coverage.Coverage.current().switch_context(f"{method} {route_template}")
on each request start; resets to "" on response end (even if the handler
raises). No-op when coverage.py is not running.

Concurrency constraint: switch_context is process-global. Instrumented
runs MUST use a single uvicorn worker + sequential cucumber. See design
spec §12 risk #6.
"""

from __future__ import annotations

import logging

import coverage
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match
from starlette.types import ASGIApp

_LOG = logging.getLogger(__name__)


class CoverageContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cov = coverage.Coverage.current()
        context_label = self._resolve_context(request)
        if cov is not None:
            try:
                cov.switch_context(context_label)
            except Exception as exc:  # noqa: BLE001 — coverage.py should never fail the request
                _LOG.warning("switch_context(%r) failed: %s", context_label, exc)
        try:
            response = await call_next(request)
        finally:
            if cov is not None:
                try:
                    cov.switch_context("")  # reset
                except Exception as exc:  # noqa: BLE001
                    _LOG.warning("switch_context('') failed: %s", exc)
        return response

    @staticmethod
    def _resolve_context(request: Request) -> str:
        """Return f"{method} {route_template}" via active route matching.

        Per plan-review iter 6 P1 (Codex): `request.scope["route"]` is
        populated by Starlette's Router AFTER middleware dispatch, so the
        previous fallback to `request.url.path` was always taken — every
        path-param endpoint silently lost attribution.

        Fix: do our own route matching against `request.app.router.routes`
        using each Route's `matches(scope)` method.
        """
        app = request.scope.get("app")
        if app is None:
            return f"{request.method} {request.url.path}"
        for route in getattr(app.router, "routes", []):
            try:
                result = route.matches(request.scope)
            except Exception:  # noqa: BLE001
                continue
            match = result[0] if isinstance(result, tuple) else result
            if match == Match.FULL:
                template = getattr(route, "path", None) or getattr(route, "path_format", None)
                if template:
                    return f"{request.method} {template}"
        _LOG.warning(
            "No route template matched %s %s — using concrete path. "
            "This will not match Grader's lookup.",
            request.method,
            request.url.path,
        )
        return f"{request.method} {request.url.path}"
