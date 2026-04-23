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


def test_history_page_zero_returns_empty_or_clamped(client) -> None:
    # Current impl clamps page<1 to 1. Accept either clamp or 422.
    res = client.get("/api/v1/history?page=0")
    assert res.status_code == 200
    body = res.json()
    assert body["page"] == 1 or body["page"] == 0
    assert isinstance(body["items"], list)


def test_history_page_size_zero_clamped_to_one(client) -> None:
    res = client.get("/api/v1/history?page_size=0")
    assert res.status_code == 200
    assert res.json()["page_size"] == 1


def test_history_page_size_max_capped(client) -> None:
    res = client.get("/api/v1/history?page_size=10000")
    assert res.status_code == 200
    assert res.json()["page_size"] == 100


def test_history_past_end_page_returns_empty(client) -> None:
    # Create 2 finished games, request page 99 with page_size=20
    client.post("/api/v1/games", json={"category": "animals", "difficulty": "easy"})
    client.post("/api/v1/games", json={"category": "food", "difficulty": "easy"})
    client.post("/api/v1/games", json={"category": "test", "difficulty": "easy"})  # forfeit chain
    res = client.get("/api/v1/history?page=99&page_size=20")
    assert res.status_code == 200
    body = res.json()
    assert body["items"] == []
    assert body["total"] >= 2
    assert body["page"] == 99
