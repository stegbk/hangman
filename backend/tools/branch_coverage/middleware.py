"""CoverageContextMiddleware: per-endpoint attribution for coverage.py.

Calls coverage.Coverage.current().switch_context(f"{method} {route_template}")
on each request start. NO finally-reset to "" — empirically verified that
on coverage.py 7.13.5, calling `switch_context("")` between request labels
silently drops every context AFTER the first. See "Reset trade-off" below.

Concurrency constraint: switch_context is process-global. Instrumented
runs MUST use a single uvicorn worker + sequential cucumber. See design
spec §12 risk #6.

Reset trade-off (D3 implementer + post-D1 follow-up, 2026-04-24):
    coverage.py 7.13.5's switch_context() exhibits a buffer-flush bug where
    calling `switch_context("")` between distinct labels causes subsequent
    `switch_context("X")` calls to be silently ignored — only the FIRST
    label's arcs are recorded; later labels' arcs are mis-attributed (e.g.,
    the "" reset itself, or absorbed into the next-next label).

    Production has many sequential requests against the same handlers, so
    a finally-reset would silently break per-endpoint attribution for all
    requests after the first.

    This middleware therefore does NOT reset. Trade-off: any code that
    runs between requests (background tasks, lifespan hooks, idle work)
    gets attributed to the PREVIOUS request's context. For Hangman's
    sequential BDD suite this is an acceptable accuracy cost.

    H1 live-smoke checks (positive `/guesses` credits apply_guess +
    negative `/categories` doesn't reach apply_guess) will catch any
    practical breakage from this trade-off.

Phase 5 iter 4 follow-up (coverage.py 7.13.5 deeper limitations):
    Codex iter-4 review flagged that the D3 fixture's docstring suggested
    `Coverage(..., context="base")` was needed for multi-context recording.
    Re-tested empirically:
        - Coverage(context="base") + 3 switch_context calls (no resets) →
          STILL drops middle labels AND each context returns all arcs (the
          per-context filter stops partitioning under static context).
        - Coverage() (no base) + 3 switch_context calls (no resets) →
          drops middle labels with the lag-attribution bug, BUT correctly
          partitions arcs per recorded label.
        - Coverage() + N switch_context calls of the SAME label →
          works correctly (no lag with same-label sequences).
    The Hangman BDD suite's pattern (many requests per endpoint, same label
    repeating) is the working case. Rapid endpoint-switching shows
    lag-attribution. H1's positive-/guesses + negative-/categories checks
    pass in practice because /categories doesn't call apply_guess
    statically (so /categories is structurally correct regardless of
    runtime attribution), and /guesses' many same-label requests anchor
    the per-endpoint context recording.

    Accepted limitation: rapid context-switching at the lag boundary may
    show inaccurate per-endpoint attribution for endpoints invoked just
    once or twice. Not blocking for the Hangman BDD suite. A future
    upgrade to coverage.py >7.13.5 may resolve this; until then, the
    pinned dep `coverage>=7.13,<7.14` keeps behavior stable.
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
        if cov is not None:
            context_label = self._resolve_context(request)
            try:
                cov.switch_context(context_label)
            except Exception as exc:  # noqa: BLE001 — coverage.py should never fail the request
                _LOG.warning("switch_context(%r) failed: %s", context_label, exc)
        # No finally-reset — see module docstring "Reset trade-off".
        return await call_next(request)

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
            except Exception as exc:  # noqa: BLE001
                _LOG.debug("route %r raised during matches: %s", route, exc)
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
