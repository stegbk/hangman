"""Unit tests for Pydantic DTOs."""

import pytest
from pydantic import ValidationError

from hangman.schemas import (
    CategoriesResponse,
    CreateGameResponse,
    DifficultyOption,
    ErrorEnvelope,
    GameCreate,
    GameResponse,
    GuessRequest,
    HistoryResponse,
    SessionResponse,
)

# GameCreate


def test_game_create_valid() -> None:
    gc = GameCreate(category="animals", difficulty="medium")
    assert gc.difficulty == "medium"


def test_game_create_bad_difficulty_raises() -> None:
    with pytest.raises(ValidationError):
        GameCreate(category="animals", difficulty="impossible")  # type: ignore[arg-type]


# GuessRequest


@pytest.mark.parametrize("letter", ["a", "Z", "m"])
def test_guess_request_accepts_single_letter(letter: str) -> None:
    # Pydantic no longer normalizes — letter is stored verbatim; apply_guess normalizes.
    gr = GuessRequest(letter=letter)
    assert gr.letter == letter


@pytest.mark.parametrize("bad", ["", "ab", "1", "!", " "])
def test_guess_request_accepts_any_string_validation_deferred(bad: str) -> None:
    # Validation is deferred to apply_guess (raises InvalidLetter); Pydantic accepts any str.
    gr = GuessRequest(letter=bad)
    assert gr.letter == bad


# GameResponse — word is hidden mid-game, revealed when terminal


def _base_game_response_kwargs() -> dict:
    return {
        "id": 1,
        "category": "animals",
        "difficulty": "easy",
        "wrong_guesses_allowed": 8,
        "wrong_guesses": 0,
        "guessed_letters": "",
        "state": "IN_PROGRESS",
        "score": 0,
        "started_at": "2026-04-22T00:00:00+00:00",
        "finished_at": None,
        "_word": "cat",
    }


def test_game_response_omits_word_key_when_in_progress() -> None:
    """PRD US-001: the `word` field must be ABSENT (not null) during IN_PROGRESS."""
    g = GameResponse.from_game_row(**_base_game_response_kwargs())
    dumped = g.model_dump()
    assert "word" not in dumped
    assert dumped["masked_word"] == "___"
    assert dumped["lives_remaining"] == 8


def test_game_response_reveals_word_when_won() -> None:
    kwargs = _base_game_response_kwargs()
    kwargs["state"] = "WON"
    kwargs["guessed_letters"] = "act"
    g = GameResponse.from_game_row(**kwargs)
    dumped = g.model_dump()
    assert dumped["word"] == "cat"
    assert dumped["masked_word"] == "cat"


# CreateGameResponse carries forfeited_game_id


def test_create_game_response_has_forfeited_game_id() -> None:
    kwargs = _base_game_response_kwargs()
    g = CreateGameResponse.from_game_row(forfeited_game_id=42, **kwargs)
    assert g.forfeited_game_id == 42
    g2 = CreateGameResponse.from_game_row(forfeited_game_id=None, **kwargs)
    assert g2.forfeited_game_id is None


# SessionResponse


def test_session_response_defaults() -> None:
    s = SessionResponse(current_streak=0, best_streak=0, total_score=0)
    assert s.total_score == 0


# HistoryResponse pagination shape


def test_history_response_shape() -> None:
    h = HistoryResponse(items=[], total=0, page=1, page_size=20)
    assert h.total == 0


# ErrorEnvelope


def test_error_envelope_shape() -> None:
    e = ErrorEnvelope(
        error={
            "code": "VALIDATION_ERROR",
            "message": "bad input",
            "details": [],
            "request_id": "req_abc",
        }
    )
    assert e.error.code == "VALIDATION_ERROR"


# DifficultyOption


def test_difficulty_option_shape() -> None:
    d = DifficultyOption(id="easy", label="Easy", wrong_guesses_allowed=8)
    assert d.wrong_guesses_allowed == 8


def test_categories_response_shape() -> None:
    cr = CategoriesResponse(
        categories=["animals"],
        difficulties=[DifficultyOption(id="easy", label="Easy", wrong_guesses_allowed=8)],
    )
    assert cr.categories == ["animals"]
