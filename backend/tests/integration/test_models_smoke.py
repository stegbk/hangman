"""Smoke test that models + db fixtures work together."""

from hangman.models import Game, Session


def test_session_row_round_trips(db_session) -> None:
    s = Session(id="abc")
    db_session.add(s)
    db_session.flush()
    fetched = db_session.get(Session, "abc")
    assert fetched is not None
    assert fetched.current_streak == 0
    assert fetched.total_score == 0


def test_game_row_round_trips(db_session) -> None:
    db_session.add(Session(id="sess1"))
    g = Game(
        session_id="sess1",
        category="animals",
        difficulty="easy",
        word="cat",
        wrong_guesses_allowed=8,
    )
    db_session.add(g)
    db_session.flush()
    fetched = db_session.get(Game, g.id)
    assert fetched is not None
    assert fetched.state == "IN_PROGRESS"
    assert fetched.guessed_letters == ""
    assert fetched.score == 0
    assert fetched.finished_at is None
