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
