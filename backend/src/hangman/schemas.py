"""Pydantic v2 request/response DTOs. Response shapes are what clients see."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_serializer

from hangman.game import DIFFICULTY_LIVES, Difficulty, GameState, mask_word

# ---- Requests ----


class GameCreate(BaseModel):
    category: str = Field(min_length=1)
    difficulty: Difficulty

    @field_validator("category", mode="before")
    @classmethod
    def _normalize_category(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class GuessRequest(BaseModel):
    letter: str  # validated by apply_guess, which raises InvalidLetter


# ---- Responses ----


class DifficultyOption(BaseModel):
    id: Difficulty
    label: str
    wrong_guesses_allowed: int


class CategoriesResponse(BaseModel):
    categories: list[str]
    difficulties: list[DifficultyOption]


class SessionResponse(BaseModel):
    current_streak: int
    best_streak: int
    total_score: int


class GameResponse(BaseModel):
    id: int
    category: str
    difficulty: Difficulty
    wrong_guesses_allowed: int
    wrong_guesses: int
    guessed_letters: str
    state: GameState
    score: int
    started_at: datetime
    finished_at: datetime | None = None
    masked_word: str = ""
    lives_remaining: int = 0
    # Present ONLY when state is terminal. The serializer (below) removes the
    # key entirely during IN_PROGRESS so the response JSON has no `word` field —
    # not `"word": null` — per PRD US-001.
    word: str | None = None

    @model_serializer(mode="wrap")
    def _omit_word_in_progress(self, handler: Any) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        if self.state == "IN_PROGRESS":
            data.pop("word", None)
        return data

    @classmethod
    def from_game_row(cls, *, _word: str, **fields: Any) -> "GameResponse":
        """Build from ORM Game row fields. `word` is set internally but the
        serializer hides it while IN_PROGRESS."""
        state = fields["state"]
        masked = mask_word(_word, fields["guessed_letters"])
        lives = fields["wrong_guesses_allowed"] - fields["wrong_guesses"]
        return cls(
            **fields,
            masked_word=masked,
            lives_remaining=lives,
            word=_word if state != "IN_PROGRESS" else None,
        )


class CreateGameResponse(GameResponse):
    forfeited_game_id: int | None = None

    @classmethod
    def from_game_row(  # noqa: D102
        cls, *, _word: str, forfeited_game_id: int | None = None, **fields: Any
    ) -> "CreateGameResponse":
        base = GameResponse.from_game_row(_word=_word, **fields).model_dump()
        return cls(**base, forfeited_game_id=forfeited_game_id)


class HistoryResponse(BaseModel):
    items: list[GameResponse]
    total: int
    page: int
    page_size: int


# ---- Errors ----


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] = Field(default_factory=list)
    request_id: str | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


# ---- Utilities ----


def difficulty_options() -> list[DifficultyOption]:
    return [
        DifficultyOption(id="easy", label="Easy", wrong_guesses_allowed=DIFFICULTY_LIVES["easy"]),
        DifficultyOption(
            id="medium", label="Medium", wrong_guesses_allowed=DIFFICULTY_LIVES["medium"]
        ),
        DifficultyOption(id="hard", label="Hard", wrong_guesses_allowed=DIFFICULTY_LIVES["hard"]),
    ]
