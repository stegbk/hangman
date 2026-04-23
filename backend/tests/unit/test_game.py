"""Unit tests for hangman.game — pure state machine + scoring."""

import pytest

from hangman.game import (
    DIFFICULTY_LIVES,
    MAX_FIGURE_STAGE,
    AlreadyGuessed,
    InvalidLetter,
    apply_guess,
    compute_round_score,
    figure_stage,
    mask_word,
    streak_multiplier,
)

# ---- mask_word ----


@pytest.mark.parametrize(
    "word,guessed,expected",
    [
        ("hello", "", "_____"),
        ("hello", "h", "h____"),
        ("hello", "hl", "h_ll_"),
        ("hello", "helo", "hello"),
        ("abc", "abc", "abc"),
        ("zzzz", "z", "zzzz"),
    ],
)
def test_mask_word_covers_all_cases(word: str, guessed: str, expected: str) -> None:
    assert mask_word(word, guessed) == expected


# ---- apply_guess — happy paths ----


def test_apply_guess_correct_letter_reveals_without_losing_lives() -> None:
    result = apply_guess(word="hello", guessed="", wrong=0, allowed=6, letter="l")
    assert result.new_guessed == "l"
    assert result.new_wrong_guesses == 0
    assert result.correct_reveal is True
    assert result.new_state == "IN_PROGRESS"


def test_apply_guess_wrong_letter_decrements_lives() -> None:
    result = apply_guess(word="hello", guessed="", wrong=0, allowed=6, letter="z")
    assert result.new_guessed == "z"
    assert result.new_wrong_guesses == 1
    assert result.correct_reveal is False
    assert result.new_state == "IN_PROGRESS"


def test_apply_guess_winning_letter_transitions_to_won() -> None:
    # word "hi" with "h" already guessed, remaining letter "i"
    result = apply_guess(word="hi", guessed="h", wrong=0, allowed=6, letter="i")
    assert result.new_guessed == "hi"
    assert result.correct_reveal is True
    assert result.new_state == "WON"


def test_apply_guess_losing_guess_transitions_to_lost() -> None:
    # 5 wrong guesses already, allowed=6; this wrong guess is the 6th → LOST
    result = apply_guess(word="hello", guessed="abcdf", wrong=5, allowed=6, letter="z")
    assert result.new_wrong_guesses == 6
    assert result.correct_reveal is False
    assert result.new_state == "LOST"


def test_apply_guess_normalizes_uppercase() -> None:
    result = apply_guess(word="hello", guessed="", wrong=0, allowed=6, letter="H")
    assert result.new_guessed == "h"
    assert result.correct_reveal is True


def test_apply_guess_sorts_guessed_letters() -> None:
    result = apply_guess(word="hello", guessed="oh", wrong=0, allowed=6, letter="e")
    assert result.new_guessed == "eho"  # sorted


# ---- apply_guess — error cases ----


def test_apply_guess_already_guessed_raises() -> None:
    with pytest.raises(AlreadyGuessed):
        apply_guess(word="hello", guessed="h", wrong=0, allowed=6, letter="h")


def test_apply_guess_uppercase_already_guessed_also_raises() -> None:
    with pytest.raises(AlreadyGuessed):
        apply_guess(word="hello", guessed="h", wrong=0, allowed=6, letter="H")


@pytest.mark.parametrize("letter", ["", "ab", "1", "!", " ", "é"])
def test_apply_guess_invalid_letter_raises(letter: str) -> None:
    with pytest.raises(InvalidLetter):
        apply_guess(word="hello", guessed="", wrong=0, allowed=6, letter=letter)


# ---- figure_stage ----


@pytest.mark.parametrize(
    "wrong,allowed,expected",
    [
        # Easy (8 lives): stages 0..8 map 1:1
        (0, 8, 0),
        (1, 8, 1),
        (8, 8, 8),
        # Medium (6 lives): start at stage 2, end at 8
        (0, 6, 2),
        (1, 6, 3),
        (6, 6, 8),
        # Hard (4 lives): start at stage 4, end at 8
        (0, 4, 4),
        (1, 4, 5),
        (4, 4, 8),
    ],
)
def test_figure_stage_all_difficulties_end_at_stage_8(
    wrong: int, allowed: int, expected: int
) -> None:
    assert figure_stage(wrong, allowed) == expected


# ---- streak_multiplier ----


@pytest.mark.parametrize(
    "streak,expected",
    [
        (0, 1),  # no streak
        (1, 1),
        (2, 2),  # 2x at exactly 2
        (3, 3),  # 3x at 3
        (4, 3),  # stays 3x
        (10, 3),
    ],
)
def test_streak_multiplier_boundaries(streak: int, expected: int) -> None:
    assert streak_multiplier(streak) == expected


# ---- compute_round_score ----


def test_compute_round_score_basic_win_no_streak() -> None:
    # 4 reveals × 10 + 3 lives × 5 = 55, streak=1 → multiplier 1 → 55
    assert compute_round_score(correct_reveals=4, lives_remaining=3, streak_after_win=1) == 55


def test_compute_round_score_streak_2_doubles() -> None:
    # base 55, streak=2 → 110
    assert compute_round_score(correct_reveals=4, lives_remaining=3, streak_after_win=2) == 110


def test_compute_round_score_streak_3_triples() -> None:
    # base 55, streak=3 → 165
    assert compute_round_score(correct_reveals=4, lives_remaining=3, streak_after_win=3) == 165


def test_compute_round_score_streak_higher_still_triples() -> None:
    assert compute_round_score(correct_reveals=1, lives_remaining=0, streak_after_win=10) == 30


# ---- constants ----


def test_difficulty_lives_mapping() -> None:
    assert DIFFICULTY_LIVES == {"easy": 8, "medium": 6, "hard": 4}


def test_max_figure_stage_is_8() -> None:
    assert MAX_FIGURE_STAGE == 8
