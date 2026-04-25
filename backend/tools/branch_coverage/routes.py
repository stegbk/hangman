"""RouteEnumerator: reflective FastAPI route enumeration.

Imports the provided FastAPI app (caller's responsibility) and lists its
routes. AST-parsing routes.py rejected — reflective handles prefix=,
app.include_router(), and add_api_route() for free.
"""

from __future__ import annotations

from typing import Any

from tools.branch_coverage.models import Endpoint


class RouteEnumerator:
    def enumerate(self, app: Any) -> tuple[Endpoint, ...]:
        """Return all routes registered on `app` as Endpoint tuples.

        Filters to routes that have HTTP methods (excludes WebSockets,
        static mounts, etc.). Sorts by (path, method) for determinism.
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
