"""Error envelope, typed domain errors, request-id middleware, exception handlers."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class HangmanError(Exception):
    """Typed domain error that the handler renders as the standard envelope."""

    def __init__(
        self,
        *,
        code: str,
        http_status: int,
        message: str,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.message = message
        self.details = details or []


def build_error_envelope(
    *,
    code: str,
    message: str,
    request_id: str | None,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "request_id": request_id,
        }
    }


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:16]}"
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def handle_hangman_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HangmanError)
    return JSONResponse(
        status_code=exc.http_status,
        content=build_error_envelope(
            code=exc.code,
            message=exc.message,
            request_id=_request_id(request),
            details=exc.details,
        ),
    )


async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return JSONResponse(
        status_code=422,
        content=build_error_envelope(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            request_id=_request_id(request),
            details=[{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()],
        ),
    )


async def handle_uncaught(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=build_error_envelope(
            code="INTERNAL_ERROR",
            message="Internal server error",
            request_id=_request_id(request),
        ),
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HangmanError, handle_hangman_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_uncaught)
