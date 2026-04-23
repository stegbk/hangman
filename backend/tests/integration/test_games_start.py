def test_start_game_returns_201_with_location_and_masked_word(client) -> None:
    res = client.post("/api/v1/games", json={"category": "animals", "difficulty": "easy"})
    assert res.status_code == 201
    assert res.headers["location"].startswith("/api/v1/games/")
    body = res.json()
    assert body["category"] == "animals"
    assert body["difficulty"] == "easy"
    assert body["wrong_guesses_allowed"] == 8
    assert body["lives_remaining"] == 8
    assert body["state"] == "IN_PROGRESS"
    # PRD US-001: `word` key MUST be absent mid-game (not null). Enforce strictly.
    assert "word" not in body
    assert set(body["masked_word"]) == {"_"}
    assert body["forfeited_game_id"] is None


def test_start_game_422_on_unknown_category(client) -> None:
    res = client.post("/api/v1/games", json={"category": "weapons", "difficulty": "easy"})
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "UNKNOWN_CATEGORY"


def test_start_game_422_on_bad_difficulty(client) -> None:
    res = client.post("/api/v1/games", json={"category": "animals", "difficulty": "godlike"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_start_game_accepts_capitalized_category(client) -> None:
    """Fix 1 (P1-2): PRD uses 'Animals'/'Food'/'Tech'; GameCreate must normalize to lowercase."""
    res = client.post("/api/v1/games", json={"category": "Animals", "difficulty": "easy"})
    assert res.status_code == 201
    assert res.json()["category"] == "animals"


def test_partial_unique_index_prevents_two_in_progress(db_session, engine) -> None:
    """Fix 5 (P2-5): partial unique index enforces one IN_PROGRESS game per session at DB level."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    from hangman.models import Game, Session

    # Arrange: create a session and one IN_PROGRESS game.
    sess = Session(id="test-session-idx")
    db_session.add(sess)
    db_session.flush()

    game1 = Game(
        session_id="test-session-idx",
        category="animals",
        difficulty="easy",
        word="cat",
        wrong_guesses_allowed=8,
        state="IN_PROGRESS",
    )
    db_session.add(game1)
    db_session.flush()

    # Act: inserting a second IN_PROGRESS game for the same session must raise IntegrityError.
    game2 = Game(
        session_id="test-session-idx",
        category="animals",
        difficulty="easy",
        word="dog",
        wrong_guesses_allowed=8,
        state="IN_PROGRESS",
    )
    db_session.add(game2)

    with pytest.raises(IntegrityError):
        db_session.flush()
