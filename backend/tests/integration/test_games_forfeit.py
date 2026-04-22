def test_starting_new_game_forfeits_prior_in_progress(client) -> None:
    first = client.post("/api/v1/games", json={"category": "animals", "difficulty": "easy"}).json()
    second = client.post("/api/v1/games", json={"category": "food", "difficulty": "medium"}).json()
    assert second["forfeited_game_id"] == first["id"]

    history = client.get("/api/v1/history").json()
    forfeited = next(item for item in history["items"] if item["id"] == first["id"])
    assert forfeited["state"] == "LOST"
    assert forfeited["score"] == 0
    # Streak reset
    assert client.get("/api/v1/session").json()["current_streak"] == 0


def test_starting_with_no_prior_game_has_null_forfeited(client) -> None:
    res = client.post("/api/v1/games", json={"category": "animals", "difficulty": "easy"})
    assert res.json()["forfeited_game_id"] is None
