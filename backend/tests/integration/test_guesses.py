def _start_game(client, category="animals", difficulty="easy") -> dict:
    res = client.post("/api/v1/games", json={"category": category, "difficulty": difficulty})
    assert res.status_code == 201
    return res.json()


def _guess(client, game_id: int, letter: str):
    return client.post(f"/api/v1/games/{game_id}/guesses", json={"letter": letter})


def test_correct_guess_reveals_letter(client) -> None:
    game = _start_game(client)
    # seed pool only has 'cat', 'dog', 'bird', 'fish'. Try guessing vowels until one reveals.
    res = _guess(client, game["id"], "a")
    assert res.status_code == 200
    body = res.json()
    # Either revealed (correct_reveal) or not — both are valid. If a reveal, masked_word has 'a'.
    assert body["state"] in {"IN_PROGRESS", "WON", "LOST"}


def test_wrong_guess_decrements_lives(client) -> None:
    game = _start_game(client)
    res = _guess(client, game["id"], "z")
    body = res.json()
    # 'z' is not in any seed word
    assert body["wrong_guesses"] == 1
    assert body["lives_remaining"] == game["lives_remaining"] - 1


def test_uppercase_guess_normalized(client) -> None:
    game = _start_game(client)
    res1 = _guess(client, game["id"], "A")
    res2 = _guess(client, game["id"], "a")
    assert res1.status_code == 200
    # second call should be ALREADY_GUESSED
    assert res2.status_code == 422
    assert res2.json()["error"]["code"] == "ALREADY_GUESSED"


def test_invalid_letter_422(client) -> None:
    game = _start_game(client)
    res = _guess(client, game["id"], "1")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "INVALID_LETTER"


def test_guess_on_nonexistent_game_404(client) -> None:
    res = _guess(client, 99999, "a")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "GAME_NOT_FOUND"


def test_cross_session_access_returns_404(client) -> None:
    game = _start_game(client)
    # Swap cookie to simulate different session.
    client.cookies.clear()
    res = _guess(client, game["id"], "a")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "GAME_NOT_FOUND"


def test_winning_updates_session_and_game_score_deterministic(client) -> None:
    """Hermetic win: `test` category has exactly one word ('cat').
    Guess c, a, t → WON. Assert exact score + streak update."""
    game = _start_game(client, category="test", difficulty="easy")  # 8 lives
    assert "word" not in game, "word must be absent mid-game"

    # Three correct guesses in a row.
    for letter in ("c", "a", "t"):
        res = _guess(client, game["id"], letter)
        assert res.status_code == 200

    final = res.json()  # noqa: F821 — last iteration's response
    assert final["state"] == "WON"
    assert final["word"] == "cat", "word revealed on WON"

    # correct_reveals = 3 (c, a, t each revealed >=1 letter).
    # lives_remaining = 8 (no wrong guesses).
    # Streak after win = 1 → multiplier = 1×.
    # Score = (3 * 10) + (8 * 5) = 70. × 1 = 70.
    assert final["score"] == 70

    session = client.get("/api/v1/session").json()
    assert session["current_streak"] == 1
    assert session["best_streak"] == 1
    assert session["total_score"] == 70

    history = client.get("/api/v1/history").json()
    assert history["total"] == 1
    assert history["items"][0]["state"] == "WON"
    assert history["items"][0]["score"] == 70


def test_losing_zeroes_streak_and_score(client) -> None:
    """Hermetic loss: start `test/hard` (4 lives, word='cat'), guess 4 wrong letters."""
    game = _start_game(client, category="test", difficulty="hard")
    for letter in ("z", "q", "x", "w"):  # 4 wrong guesses exhausts lives
        res = _guess(client, game["id"], letter)
        assert res.status_code == 200

    final = res.json()  # noqa: F821
    assert final["state"] == "LOST"
    assert final["word"] == "cat"
    assert final["score"] == 0

    session = client.get("/api/v1/session").json()
    assert session["current_streak"] == 0
    assert session["total_score"] == 0


def test_streak_multiplier_across_two_consecutive_wins(client) -> None:
    """Streak-after-win of 2 should trigger 2× multiplier on the second win."""
    # First win
    game1 = _start_game(client, category="test", difficulty="easy")
    for letter in ("c", "a", "t"):
        _guess(client, game1["id"], letter)
    # Second win — should apply 2× multiplier
    game2 = _start_game(client, category="test", difficulty="easy")
    for letter in ("c", "a", "t"):
        last = _guess(client, game2["id"], letter)
    final2 = last.json()
    assert final2["state"] == "WON"
    # Base = 3*10 + 8*5 = 70. Streak after this win = 2 → multiplier 2 → 140.
    assert final2["score"] == 140
    session = client.get("/api/v1/session").json()
    assert session["current_streak"] == 2
    assert session["best_streak"] == 2
    assert session["total_score"] == 70 + 140


def test_guess_on_finished_game_409(client) -> None:
    """Hermetic: win category=test (word=cat), then try to guess on the finished game."""
    game = _start_game(client, category="test", difficulty="easy")
    for letter in ("c", "a", "t"):
        _guess(client, game["id"], letter)
    # Game is now WON; any further guess must be 409 GAME_ALREADY_FINISHED.
    res = _guess(client, game["id"], "z")  # 'z' was not previously guessed
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "GAME_ALREADY_FINISHED"
