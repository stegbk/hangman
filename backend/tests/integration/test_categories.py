from hangman.sessions import COOKIE_MAX_AGE, COOKIE_NAME


def test_categories_endpoint_returns_loaded_pool(client) -> None:
    res = client.get("/api/v1/categories")
    assert res.status_code == 200
    body = res.json()
    # test_word_pool has animals + food + test (one-word deterministic category).
    assert set(body["categories"]) == {"animals", "food", "test"}
    assert [d["id"] for d in body["difficulties"]] == ["easy", "medium", "hard"]
    assert [d["wrong_guesses_allowed"] for d in body["difficulties"]] == [8, 6, 4]


def test_categories_sets_session_cookie_on_first_call(client) -> None:
    """PRD US-004: cookie is set on ANY no-cookie request — including /categories."""
    # Fresh client has no cookie yet.
    client.cookies.clear()
    res = client.get("/api/v1/categories")
    assert res.status_code == 200
    set_cookie = res.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie
    assert "lax" in set_cookie.lower()
    assert str(COOKIE_MAX_AGE) in set_cookie
