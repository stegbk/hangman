"""Integration test for get_or_create_session cookie behavior.

Uses a minimal in-test FastAPI app so the test does not depend on the full main.py assembly.
"""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from hangman.db import get_session
from hangman.models import Session
from hangman.sessions import COOKIE_MAX_AGE, COOKIE_NAME, get_or_create_session


def _make_app(engine) -> FastAPI:
    app = FastAPI()
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def _override_get_session():
        db = testing_session()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_session] = _override_get_session

    @app.get("/whoami")
    def whoami(s: Session = Depends(get_or_create_session)) -> dict:  # noqa: B008
        return {"session_id": s.id, "current_streak": s.current_streak}

    return app


def test_first_request_sets_cookie(engine) -> None:
    client = TestClient(_make_app(engine))
    res = client.get("/whoami")
    assert res.status_code == 200
    body = res.json()
    assert len(body["session_id"]) > 0
    # Inspect Set-Cookie for attributes.
    set_cookie = res.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie.lower() or "samesite=lax" in set_cookie.lower()
    assert (
        f"Max-Age={COOKIE_MAX_AGE}" in set_cookie
        or f"max-age={COOKIE_MAX_AGE}" in set_cookie.lower()
    )


def test_subsequent_requests_reuse_session(engine) -> None:
    client = TestClient(_make_app(engine))
    first = client.get("/whoami")
    sid_first = first.json()["session_id"]
    second = client.get("/whoami")
    assert second.json()["session_id"] == sid_first


def test_stale_cookie_creates_fresh_session(engine) -> None:
    client = TestClient(_make_app(engine))
    client.cookies.set(COOKIE_NAME, "not-a-real-uuid")
    res = client.get("/whoami")
    assert res.status_code == 200
    assert res.json()["session_id"] != "not-a-real-uuid"
