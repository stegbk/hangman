from hangman.sessions import COOKIE_MAX_AGE, COOKIE_NAME


def test_session_endpoint_returns_zeros_on_fresh_session(client) -> None:
    res = client.get("/api/v1/session")
    assert res.status_code == 200
    body = res.json()
    assert body == {"current_streak": 0, "best_streak": 0, "total_score": 0}


def test_session_endpoint_sets_cookie_with_required_attributes(client) -> None:
    res = client.get("/api/v1/session")
    set_cookie = res.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie
    assert "lax" in set_cookie.lower()
    assert str(COOKIE_MAX_AGE) in set_cookie


def test_session_endpoint_is_idempotent(client) -> None:
    r1 = client.get("/api/v1/session")
    r2 = client.get("/api/v1/session")
    assert r1.json() == r2.json()


def test_cookie_max_age_is_30_days() -> None:
    """Locks the 30-day TTL contract from PRD US-004."""
    from hangman.sessions import COOKIE_MAX_AGE

    assert COOKIE_MAX_AGE == 30 * 24 * 60 * 60  # 2592000
