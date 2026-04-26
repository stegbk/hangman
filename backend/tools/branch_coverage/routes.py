"""RouteEnumerator: reflective FastAPI route enumeration.

Imports the provided FastAPI app (caller's responsibility) and lists its
routes. AST-parsing routes.py rejected — reflective handles prefix=,
app.include_router(), and add_api_route() for free.
"""

from __future__ import annotations

import logging
from typing import Any

from tools.branch_coverage.models import Endpoint

_LOG = logging.getLogger(__name__)

# FastAPI's built-in OpenAPI / Swagger / ReDoc routes are framework
# infrastructure, not user-defined application endpoints. Including them
# in the per-endpoint coverage report adds noise (no app-author cares
# whether `/docs` is "covered" by their BDD suite) and inflates the
# audit denominator. Filter them out at enumeration time.
_FASTAPI_BUILTIN_PATHS = frozenset(
    {
        "/docs",
        "/redoc",
        "/openapi.json",
        "/docs/oauth2-redirect",
    }
)


class RouteEnumerator:
    def enumerate(self, app: Any) -> tuple[Endpoint, ...]:
        """Return all routes registered on `app` as Endpoint tuples.

        Filters to routes that have HTTP methods (excludes WebSockets,
        static mounts, etc.). Skips FastAPI's built-in docs routes
        (/docs, /redoc, /openapi.json, /docs/oauth2-redirect). Sorts by
        (path, method) for determinism.
        """
        endpoints: list[Endpoint] = []
        for route in getattr(app, "routes", []):
            methods = getattr(route, "methods", None)
            if not methods:
                continue
            path = getattr(route, "path", None)
            endpoint_fn = getattr(route, "endpoint", None)
            if path is None or endpoint_fn is None:
                continue
            if path in _FASTAPI_BUILTIN_PATHS:
                _LOG.debug("Filtering FastAPI built-in route: %s", path)
                continue
            handler_qualname = f"{endpoint_fn.__module__}.{endpoint_fn.__qualname__}"
            for method in sorted(methods):
                if method == "HEAD":
                    continue
                endpoints.append(
                    Endpoint(
                        method=method,
                        path=path,
                        handler_qualname=handler_qualname,
                    )
                )
        endpoints.sort(key=lambda e: (e.path, e.method))
        return tuple(endpoints)
