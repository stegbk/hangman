"""Session cookie dependency — hand-rolled, not Starlette SessionMiddleware."""

import logging
from uuid import uuid4

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session as OrmSession

from hangman.db import get_session
from hangman.models import Session, _now_utc

COOKIE_NAME = "session_id"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days

logger = logging.getLogger("hangman.sessions")


def get_or_create_session(
    request: Request,
    response: Response,
    db: OrmSession = Depends(get_session),  # noqa: B008
) -> Session:
    """Load the session tied to the request cookie, or create a new one. Sets / refreshes the cookie."""
    cookie_value = request.cookies.get(COOKIE_NAME)
    session: Session | None = db.get(Session, cookie_value) if cookie_value else None
    if session is None:
        if cookie_value:
            # Cookie was present but no matching Session row — stale cookie.
            logger.info("session_miss cookie=%s...", cookie_value[:8])
        session = Session(id=str(uuid4()))
        db.add(session)
        db.flush()
    session.updated_at = _now_utc()

    response.set_cookie(
        key=COOKIE_NAME,
        value=session.id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return session
