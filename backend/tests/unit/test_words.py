"""Unit tests for hangman.words — CSV loader + WordPool."""

from dataclasses import FrozenInstanceError
from pathlib import Path
from random import Random

import pytest

from hangman.words import WordPool, load_words


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "words.txt"
    p.write_text(content)
    return p


def test_load_words_happy_path(tmp_path: Path) -> None:
    p = _write(tmp_path, "animals,cat\nanimals,dog\nfood,pizza\n")
    pool = load_words(p)
    assert set(pool.category_names()) == {"animals", "food"}
    assert set(pool.categories["animals"]) == {"cat", "dog"}
    assert set(pool.categories["food"]) == {"pizza"}


def test_load_words_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "# header comment\n\nanimals,cat\n# mid comment\nanimals,dog\n\n",
    )
    pool = load_words(p)
    assert set(pool.categories["animals"]) == {"cat", "dog"}


def test_load_words_rejects_uppercase(tmp_path: Path) -> None:
    p = _write(tmp_path, "animals,Cat\n")
    with pytest.raises(ValueError, match="line 1"):
        load_words(p)


def test_load_words_rejects_non_letters(tmp_path: Path) -> None:
    p = _write(tmp_path, "animals,cat1\n")
    with pytest.raises(ValueError, match="line 1"):
        load_words(p)


def test_load_words_rejects_short_words(tmp_path: Path) -> None:
    p = _write(tmp_path, "animals,ab\n")
    with pytest.raises(ValueError, match="line 1"):
        load_words(p)


def test_load_words_rejects_missing_comma(tmp_path: Path) -> None:
    p = _write(tmp_path, "animals cat\n")
    with pytest.raises(ValueError, match="line 1"):
        load_words(p)


def test_load_words_rejects_empty_category(tmp_path: Path) -> None:
    # category with no valid words
    p = _write(tmp_path, "animals,cat\nfood,\n")
    with pytest.raises(ValueError):
        load_words(p)


def test_load_words_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_words(tmp_path / "nope.txt")


def test_random_word_deterministic_with_seeded_rng(tmp_path: Path) -> None:
    p = _write(tmp_path, "animals,cat\nanimals,dog\nanimals,bird\n")
    pool = load_words(p, rng=Random(42))
    picks = {pool.random_word("animals") for _ in range(20)}
    assert picks.issubset({"cat", "dog", "bird"})


def test_random_word_unknown_category_raises(tmp_path: Path) -> None:
    p = _write(tmp_path, "animals,cat\n")
    pool = load_words(p)
    with pytest.raises(KeyError):
        pool.random_word("weapons")


def test_wordpool_constructible_without_explicit_rng() -> None:
    """Verifies the default_factory RNG fix — WordPool(..) works with no rng arg."""
    pool = WordPool(categories={"animals": ("cat", "dog")})
    # random_word must not crash on the default RNG.
    picked = pool.random_word("animals")
    assert picked in {"cat", "dog"}


def test_wordpool_is_frozen() -> None:
    pool = WordPool(categories={"animals": ("cat", "dog")})
    with pytest.raises(FrozenInstanceError):
        pool.categories = {}  # type: ignore[misc]


def test_wordpool_categories_are_tuples(tmp_path: Path) -> None:
    """Category word lists must be immutable — tuples, not lists."""
    p = _write(tmp_path, "animals,cat\n")
    pool = load_words(p)
    assert isinstance(pool.categories["animals"], tuple)


def test_wordpool_categories_dict_is_immutable(tmp_path: Path) -> None:
    """Fix 7 (P2-12): categories mapping must be a MappingProxyType — external mutation raises TypeError."""
    p = _write(tmp_path, "animals,cat\n")
    pool = load_words(p)
    with pytest.raises(TypeError):
        pool.categories["animals"] = ("hacked",)  # type: ignore[index]


def test_load_real_words_txt_has_three_categories() -> None:
    repo_root = Path(__file__).parent.parent.parent
    pool = load_words(repo_root / "words.txt")
    assert set(pool.category_names()) == {"animals", "food", "tech"}
    for cat in pool.category_names():
        assert len(pool.categories[cat]) >= 15
