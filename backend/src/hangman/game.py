"""Pure hangman game logic — state machine + scoring.

No FastAPI, no SQLAlchemy imports. 100% unit-testable without mocks.
"""

from dataclasses import dataclass
from typing import Literal

Difficulty = Literal["easy", "medium", "hard"]
GameState = Literal["IN_PROGRESS", "WON", "LOST"]

DIFFICULTY_LIVES: dict[Difficulty, int] = {"easy": 8, "medium": 6, "hard": 4}
MAX_FIGURE_STAGE = 8

_LETTER_A = ord("a")
_LETTER_Z = ord("z")


class AlreadyGuessed(ValueError):  # noqa: N818
    """Raised when the letter was already guessed in this game."""


class InvalidLetter(ValueError):  # noqa: N818
    """Raised when the letter is not a single a-z character."""


@dataclass(frozen=True)
class GuessResult:
    new_guessed: str  # sorted lowercase letters
    new_wrong_guesses: int
    correct_reveal: bool  # True if the letter appeared in the word
    new_state: GameState


def _normalize_letter(letter: str) -> str:
    if len(letter) != 1:
        raise InvalidLetter(f"expected single character, got len={len(letter)}")
    lowered = letter.lower()
    if not (_LETTER_A <= ord(lowered) <= _LETTER_Z):
        raise InvalidLetter(f"letter must be a-z, got {letter!r}")
    return lowered


def mask_word(word: str, guessed: str) -> str:
    """Return `word` with unguessed letters replaced by `_`."""
    guessed_set = set(guessed)
    return "".join(ch if ch in guessed_set else "_" for ch in word)


def apply_guess(
    *,
    word: str,
    guessed: str,
    wrong: int,
    allowed: int,
    letter: str,
) -> GuessResult:
    """Apply a single letter guess, returning the next state."""
    normalized = _normalize_letter(letter)
    if normalized in guessed:
        raise AlreadyGuessed(f"{normalized!r} was already guessed")

    new_guessed = "".join(sorted(set(guessed) | {normalized}))
    correct_reveal = normalized in word

    if correct_reveal:
        new_wrong = wrong
        if all(ch in new_guessed for ch in word):
            new_state: GameState = "WON"
        else:
            new_state = "IN_PROGRESS"
    else:
        new_wrong = wrong + 1
        new_state = "LOST" if new_wrong >= allowed else "IN_PROGRESS"

    return GuessResult(
        new_guessed=new_guessed,
        new_wrong_guesses=new_wrong,
        correct_reveal=correct_reveal,
        new_state=new_state,
    )


def figure_stage(wrong_guesses: int, wrong_guesses_allowed: int) -> int:
    """Map (wrong, allowed) → ASCII hangman stage 0..8.

    All difficulties terminate at stage 8 (fully hanged). Harder difficulties
    start the figure further along so the stages used equal the lives allowed.
    """
    start = MAX_FIGURE_STAGE - wrong_guesses_allowed
    return start + wrong_guesses


def streak_multiplier(streak: int) -> int:
    """Multiplier for round score based on resulting streak."""
    if streak >= 3:
        return 3
    if streak == 2:
        return 2
    return 1


def compute_round_score(
    *,
    correct_reveals: int,
    lives_remaining: int,
    streak_after_win: int,
) -> int:
    """Score = (reveals × 10 + lives × 5) × streak_multiplier. Loss = 0 (caller responsibility)."""
    base = correct_reveals * 10 + lives_remaining * 5
    return base * streak_multiplier(streak_after_win)
