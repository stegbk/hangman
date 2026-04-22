def test_history_empty_on_fresh_session(client) -> None:
    res = client.get("/api/v1/history")
    assert res.status_code == 200
    body = res.json()
    assert body == {"items": [], "total": 0, "page": 1, "page_size": 20}


def test_history_excludes_in_progress(client) -> None:
    client.post("/api/v1/games", json={"category": "animals", "difficulty": "easy"})
    body = client.get("/api/v1/history").json()
    assert body["items"] == []


def test_history_includes_finished_games_newest_first(client) -> None:
    first = client.post("/api/v1/games", json={"category": "animals", "difficulty": "easy"}).json()
    # forfeit -> first is LOST
    second = client.post("/api/v1/games", json={"category": "food", "difficulty": "medium"}).json()
    # forfeit second as well
    client.post("/api/v1/games", json={"category": "animals", "difficulty": "hard"}).json()

    body = client.get("/api/v1/history").json()
    assert body["total"] == 2
    ids = [item["id"] for item in body["items"]]
    # newest-first: the more recently forfeited one first (second, then first).
    assert ids == [second["id"], first["id"]]


def test_history_pagination(client) -> None:
    # Create several finished games via forfeit chain.
    for _ in range(5):
        client.post("/api/v1/games", json={"category": "animals", "difficulty": "easy"})

    body = client.get("/api/v1/history?page=1&page_size=2").json()
    assert body["page_size"] == 2
    assert len(body["items"]) == 2
    assert body["total"] == 4  # 5 starts, 4 forfeited + 1 still IN_PROGRESS (excluded)
