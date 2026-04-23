def test_get_current_404_when_no_active_game(client) -> None:
    res = client.get("/api/v1/games/current")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NO_ACTIVE_GAME"


def test_get_current_returns_active_game(client) -> None:
    started = client.post(
        "/api/v1/games", json={"category": "animals", "difficulty": "easy"}
    ).json()
    res = client.get("/api/v1/games/current")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == started["id"]
    assert body["state"] == "IN_PROGRESS"
