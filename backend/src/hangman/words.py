"""Word list loader + random picker."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from random import Random
from types import MappingProxyType

_MIN_WORD_LEN = 3


@dataclass(frozen=True)
class WordPool:
    categories: Mapping[str, tuple[str, ...]]
    # Dataclass default_factory — every WordPool has a working RNG on construction.
    # Excluded from equality/repr so it doesn't interfere with test assertions.
    _rng: Random = field(default_factory=Random, compare=False, repr=False)

    def category_names(self) -> list[str]:
        return sorted(self.categories.keys())

    def random_word(self, category: str) -> str:
        if category not in self.categories:
            raise KeyError(f"unknown category: {category!r}")
        return self._rng.choice(self.categories[category])


def _validate_word(word: str, lineno: int) -> None:
    """Validate the raw-stripped word BEFORE any case normalization.

    Contract: words in words.txt MUST be lowercase a-z; uppercase is an author
    error we want to flag, not silently normalize. This is why we do NOT lowercase
    before validation.
    """
    if not word:
        raise ValueError(f"line {lineno}: empty word")
    if len(word) < _MIN_WORD_LEN:
        raise ValueError(f"line {lineno}: word too short (<{_MIN_WORD_LEN}): {word!r}")
    for ch in word:
        if not ("a" <= ch <= "z"):
            raise ValueError(f"line {lineno}: word must be lowercase a-z: {word!r}")


def load_words(path: Path, rng: Random | None = None) -> WordPool:
    """Parse a words.txt file (CSV-like, one 'category,word' per line).

    Rules:
      - Lines starting with '#' are comments.
      - Blank lines are ignored.
      - Data lines: 'category,word' — single comma, leading/trailing whitespace stripped.
      - Word is validated AS-IS (after whitespace strip only) — must be a-z lowercase, length >= 3.
      - Category is normalized to lowercase (for case-insensitive category lookup) but the word is NOT.
      - Categories with zero valid words → ValueError at load time.
      - Raises ValueError on any bad line with the line number.
    """
    if not path.exists():
        raise FileNotFoundError(str(path))

    accum: dict[str, list[str]] = {}
    for lineno, raw in enumerate(path.read_text().splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "," not in line:
            raise ValueError(f"line {lineno}: expected 'category,word' format")
        category, word = line.split(",", 1)
        category = category.strip().lower()
        word = word.strip()  # ← NO lowercase; validate raw
        _validate_word(word, lineno)
        accum.setdefault(category, []).append(word)

    if not accum:
        raise ValueError("no valid word entries loaded")

    for cat, words in accum.items():
        if not words:
            raise ValueError(f"category {cat!r} has no words")

    frozen_cats: Mapping[str, tuple[str, ...]] = MappingProxyType(
        {cat: tuple(words) for cat, words in accum.items()}
    )
    return WordPool(
        categories=frozen_cats,
        _rng=rng if rng is not None else Random(),
    )
