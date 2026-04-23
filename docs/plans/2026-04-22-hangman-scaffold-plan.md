# Hangman Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold a playable end-to-end local hangman game (FastAPI + SQLite backend, React 19 + Vite 8 frontend) with score, streak, difficulty, category picker, per-session history, and Playwright E2E framework installed.

**Architecture:** Monorepo (`backend/` + `frontend/` + root `Makefile`). Backend uses sync Python (SQLAlchemy 2.0, Pydantic v2, FastAPI `def` routes, hand-rolled cookie dependency). Frontend uses React 19 with prop-drilled state from `App.tsx`, plain CSS, ASCII hangman figure. Dev flow: two terminals (`make backend` / `make frontend`), Vite proxies `/api/*` to `:8000`.

**Tech Stack:** Python 3.12 · FastAPI 0.136 · Pydantic v2.13 · SQLAlchemy 2.0.49 · Uvicorn 0.45 · pytest 8.3 · httpx 0.28 · ruff 0.15 · mypy · uv · Node 22 · pnpm 10 · React 19.2 · TypeScript 5.7 · Vite 8 · Vitest 3 · @testing-library/react 16 · ESLint 9 flat · Prettier 3 · Playwright 1.59 · chromium only.

**Source spec:** `docs/plans/2026-04-22-hangman-scaffold-design.md` (authoritative; this plan references it for module internals).
**PRD:** `docs/prds/hangman-scaffold.md` (v1.2)
**Research:** `docs/research/2026-04-22-hangman-scaffold.md`

---

## Task 1: Root monorepo scaffolding

**Files:**

- Create: `backend/` (directory)
- Create: `frontend/` (directory)
- Create: `.gitignore` (append lines)
- Create: `Makefile`

- [ ] **Step 1: Verify toolchain prerequisites**

Run: `python3 --version` — expect `Python 3.12.x` or higher.
Run: `node --version` — expect `v22.x` or higher (Node 20 is not supported per PRD §5).
Run: `pnpm --version` — expect `10.x` or higher.
Run: `uv --version` — expect `uv 0.7.x` or similar.

If any check fails, install the tool before proceeding.

- [ ] **Step 2: Create directories**

```bash
mkdir -p backend/src/hangman backend/tests/unit backend/tests/integration
mkdir -p frontend
```

- [ ] **Step 3: Extend .gitignore**

Read existing `.gitignore`. It currently contains `.worktrees/`. Append:

```gitignore

# Python
.venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Node
node_modules/
dist/
*.log
.vite/

# Playwright
playwright-report/
test-results/
blob-report/
playwright/.cache/

# App
backend/hangman.db
.env
.env.*
!.env.example
```

- [ ] **Step 4: Create root Makefile (skeleton — final in Task 27)**

```makefile
.PHONY: install backend frontend test lint typecheck verify clean

install:
	cd backend && uv sync
	cd frontend && pnpm install
	cd frontend && pnpm exec playwright install chromium

backend:
	cd backend && uv run uvicorn hangman.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	cd frontend && pnpm dev

test:
	cd backend && uv run pytest
	cd frontend && pnpm test -- --run

lint:
	cd backend && uv run ruff check .
	cd frontend && pnpm lint

typecheck:
	cd backend && uv run mypy src/hangman
	cd frontend && pnpm tsc --noEmit -p tsconfig.app.json

verify: lint typecheck test

clean:
	rm -rf backend/.venv backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache
	rm -rf frontend/node_modules frontend/dist frontend/playwright-report
	rm -f backend/hangman.db
```

- [ ] **Step 5: Commit**

```bash
git add .gitignore Makefile backend/ frontend/
git commit -m "chore: add monorepo directory structure + Makefile skeleton"
```

---

## Task 2: Backend `pyproject.toml` with pinned deps

**Files:**

- Create: `backend/pyproject.toml`
- Create: `backend/README.md`

- [ ] **Step 1: Write pyproject.toml**

```toml
[project]
name = "hangman"
version = "0.1.0"
description = "Local HTTP hangman game — FastAPI backend."
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.136,<0.137",
    "pydantic>=2.13,<3",
    "sqlalchemy>=2.0.49,<2.1",
    "uvicorn[standard]>=0.45,<0.46",
]

[dependency-groups]
dev = [
    "pytest>=8.3,<9",
    "pytest-cov>=5,<6",
    "httpx>=0.28,<1",
    "ruff>=0.15,<0.16",
    "mypy>=1.13,<2",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/hangman"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-ra --strict-markers --strict-config"

[tool.ruff]
target-version = "py312"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "N", "SIM"]
ignore = ["E501"]  # line-length handled by format

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.12"
strict = true
packages = ["hangman"]
mypy_path = "src"
```

- [ ] **Step 2: Run `uv sync` to create lockfile + venv**

```bash
cd backend && uv sync
```

Expected: `Resolved ... packages in ...` and `.venv/` created. `uv.lock` generated.

- [ ] **Step 3: Verify ruff + mypy + pytest are callable**

```bash
cd backend && uv run ruff --version && uv run mypy --version && uv run pytest --version
```

All three should print version strings.

- [ ] **Step 4: Write minimal backend/README.md**

````markdown
# Hangman — Backend

FastAPI + SQLAlchemy 2.0 + SQLite.

## Dev

```bash
uv sync                          # install deps
uv run uvicorn hangman.main:app --reload --port 8000
uv run pytest                    # tests
uv run ruff check . && uv run ruff format --check .
uv run mypy src/hangman
```
````

````

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/README.md
git commit -m "chore(backend): add pyproject.toml with pinned deps + ruff + mypy + pytest config"
````

---

## Task 3: Backend package skeleton + `conftest.py` bootstrap

**Files:**

- Create: `backend/src/hangman/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Write `src/hangman/__init__.py`**

```python
"""Hangman backend package."""

__version__ = "0.1.0"
```

- [ ] **Step 2: Write `tests/__init__.py`**

```python
"""Backend test suite."""
```

- [ ] **Step 3: Write `tests/conftest.py` (will be extended in later tasks)**

```python
"""Shared pytest fixtures.

Extended incrementally per task:
  - Task 6 adds the `engine` / `db_session` fixtures.
  - Task 9 adds the `client` fixture (TestClient with DB override).
"""

import pytest
```

- [ ] **Step 4: Verify pytest discovers zero tests without error**

```bash
cd backend && uv run pytest
```

Expected: `collected 0 items` + exit code 5 (pytest's "no tests collected") or 0 depending on version. No import errors.

- [ ] **Step 5: Commit**

```bash
git add backend/src/hangman/__init__.py backend/tests/__init__.py backend/tests/conftest.py
git commit -m "chore(backend): add package skeleton + empty conftest"
```

---

## Task 4: `game.py` — pure state machine + scoring (TDD)

**Files:**

- Create: `backend/tests/unit/__init__.py`
- Create: `backend/tests/unit/test_game.py`
- Create: `backend/src/hangman/game.py`

**Design reference:** `docs/plans/2026-04-22-hangman-scaffold-design.md` §2 `game.py`.

- [ ] **Step 1: Write `tests/unit/__init__.py`**

```python
"""Unit tests — pure logic, no DB, no FastAPI."""
```

- [ ] **Step 2: Write the complete failing test suite at `tests/unit/test_game.py`**

```python
"""Unit tests for hangman.game — pure state machine + scoring."""

import pytest

from hangman.game import (
    DIFFICULTY_LIVES,
    MAX_FIGURE_STAGE,
    AlreadyGuessed,
    GameState,
    GuessResult,
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
        (0, 1),   # no streak
        (1, 1),
        (2, 2),   # 2x at exactly 2
        (3, 3),   # 3x at 3
        (4, 3),   # stays 3x
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
```

- [ ] **Step 3: Run tests to confirm RED**

```bash
cd backend && uv run pytest tests/unit/test_game.py -v
```

Expected: ImportError / ModuleNotFoundError for `hangman.game`.

- [ ] **Step 4: Write `src/hangman/game.py` to make tests pass**

```python
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


class AlreadyGuessed(ValueError):
    """Raised when the letter was already guessed in this game."""


class InvalidLetter(ValueError):
    """Raised when the letter is not a single a-z character."""


@dataclass(frozen=True)
class GuessResult:
    new_guessed: str           # sorted lowercase letters
    new_wrong_guesses: int
    correct_reveal: bool       # True if the letter appeared in the word
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
```

- [ ] **Step 5: Run tests to confirm GREEN**

```bash
cd backend && uv run pytest tests/unit/test_game.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Run coverage check**

```bash
cd backend && uv run pytest tests/unit/test_game.py --cov=hangman.game --cov-report=term-missing
```

Expected: `game.py` coverage ≥ 95%. (If pytest-cov isn't installed, skip this step — it's aspirational.)

- [ ] **Step 7: Run ruff + mypy**

```bash
cd backend && uv run ruff check src/hangman/game.py tests/unit/test_game.py
cd backend && uv run mypy src/hangman/game.py
```

Both clean.

- [ ] **Step 8: Commit**

```bash
git add backend/src/hangman/game.py backend/tests/unit/__init__.py backend/tests/unit/test_game.py
git commit -m "feat(game): add pure state machine + scoring with full unit coverage"
```

---

## Task 5: `words.py` + `words.txt` seed + unit tests (TDD)

**Files:**

- Create: `backend/tests/unit/test_words.py`
- Create: `backend/src/hangman/words.py`
- Create: `backend/words.txt`

**Design reference:** `docs/plans/2026-04-22-hangman-scaffold-design.md` §2 `words.py`.

- [ ] **Step 1: Write failing tests at `tests/unit/test_words.py`**

```python
"""Unit tests for hangman.words — CSV loader + WordPool."""

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
        "# header comment\n"
        "\n"
        "animals,cat\n"
        "# mid comment\n"
        "animals,dog\n"
        "\n",
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
    with pytest.raises(Exception):  # dataclass frozen → FrozenInstanceError
        pool.categories = {}  # type: ignore[misc]


def test_wordpool_categories_are_tuples(tmp_path: Path) -> None:
    """Category word lists must be immutable — tuples, not lists."""
    p = _write(tmp_path, "animals,cat\n")
    pool = load_words(p)
    assert isinstance(pool.categories["animals"], tuple)
```

- [ ] **Step 2: Confirm RED**

```bash
cd backend && uv run pytest tests/unit/test_words.py -v
```

- [ ] **Step 3: Write `src/hangman/words.py`**

```python
"""Word list loader + random picker."""

from dataclasses import dataclass, field
from pathlib import Path
from random import Random

_MIN_WORD_LEN = 3


@dataclass(frozen=True)
class WordPool:
    categories: dict[str, tuple[str, ...]]
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

    return WordPool(
        categories={cat: tuple(words) for cat, words in accum.items()},
        _rng=rng if rng is not None else Random(),
    )
```

- [ ] **Step 4: Write the seed `backend/words.txt`**

```
# Hangman seed word list.
# Format: category,word — lowercase a-z only, length >= 3.
# Lines starting with # are comments. Blank lines ignored.

# Animals (15)
animals,cat
animals,dog
animals,elephant
animals,giraffe
animals,octopus
animals,penguin
animals,dolphin
animals,kangaroo
animals,rabbit
animals,squirrel
animals,butterfly
animals,hippopotamus
animals,crocodile
animals,chameleon
animals,flamingo

# Food (15)
food,pizza
food,burger
food,pasta
food,sushi
food,taco
food,sandwich
food,chocolate
food,pineapple
food,broccoli
food,spaghetti
food,pancake
food,avocado
food,strawberry
food,cheeseburger
food,quesadilla

# Tech (15)
tech,computer
tech,keyboard
tech,router
tech,server
tech,database
tech,algorithm
tech,python
tech,javascript
tech,terminal
tech,compiler
tech,encryption
tech,kubernetes
tech,microservice
tech,regression
tech,bandwidth
```

- [ ] **Step 5: Add an integration-style test that loads the real words.txt**

Append to `tests/unit/test_words.py`:

```python
def test_load_real_words_txt_has_three_categories() -> None:
    repo_root = Path(__file__).parent.parent.parent
    pool = load_words(repo_root / "words.txt")
    assert set(pool.category_names()) == {"animals", "food", "tech"}
    for cat in pool.category_names():
        assert len(pool.categories[cat]) >= 15
```

- [ ] **Step 6: Confirm GREEN + lint + types**

```bash
cd backend && uv run pytest tests/unit/test_words.py -v
cd backend && uv run ruff check src/hangman/words.py tests/unit/test_words.py
cd backend && uv run mypy src/hangman/words.py
```

- [ ] **Step 7: Commit**

```bash
git add backend/src/hangman/words.py backend/words.txt backend/tests/unit/test_words.py
git commit -m "feat(words): add CSV word-pool loader + 45-entry seed (animals/food/tech)"
```

---

## Task 6: `models.py` + `db.py` — SQLAlchemy 2.0 schema + engine

**Files:**

- Create: `backend/src/hangman/models.py`
- Create: `backend/src/hangman/db.py`
- Create: `backend/tests/integration/__init__.py`
- Modify: `backend/tests/conftest.py` (add DB fixtures)

**Design reference:** `docs/plans/2026-04-22-hangman-scaffold-design.md` §2 `models.py` + `db.py`.

- [ ] **Step 1: Write `src/hangman/models.py`**

```python
"""SQLAlchemy 2.0 ORM — Session + Game tables."""

from datetime import datetime, timezone
from typing import Final

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=_now_utc)
    updated_at: Mapped[datetime] = mapped_column(default=_now_utc, onupdate=_now_utc)
    current_streak: Mapped[int] = mapped_column(default=0)
    best_streak: Mapped[int] = mapped_column(default=0)
    total_score: Mapped[int] = mapped_column(default=0)


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    category: Mapped[str]
    difficulty: Mapped[str]  # 'easy' | 'medium' | 'hard' (enforced at API boundary)
    word: Mapped[str]
    wrong_guesses_allowed: Mapped[int]
    state: Mapped[str] = mapped_column(default="IN_PROGRESS", index=True)
    wrong_guesses: Mapped[int] = mapped_column(default=0)
    correct_reveals: Mapped[int] = mapped_column(default=0)
    guessed_letters: Mapped[str] = mapped_column(default="")
    score: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(default=_now_utc)
    finished_at: Mapped[datetime | None] = mapped_column(default=None, nullable=True)

    __table_args__ = (Index("ix_games_session_state", "session_id", "state"),)


STATE_IN_PROGRESS: Final = "IN_PROGRESS"
STATE_WON: Final = "WON"
STATE_LOST: Final = "LOST"
```

- [ ] **Step 2: Write `src/hangman/db.py`**

```python
"""SQLite engine + session factory + FastAPI dependency."""

import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker

_DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "hangman.db"
DATABASE_URL = os.environ.get("HANGMAN_DB_URL", f"sqlite:///{_DEFAULT_DB}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_session() -> Iterator[OrmSession]:
    """FastAPI dependency: yield an ORM session, rollback on exception, commit + close otherwise."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

- [ ] **Step 3: Write `tests/integration/__init__.py`**

```python
"""Integration tests — TestClient + in-memory SQLite."""
```

- [ ] **Step 4: Extend `tests/conftest.py` with DB fixtures**

Replace existing `conftest.py` content with:

```python
"""Shared pytest fixtures for the backend test suite."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from hangman.models import Base


@pytest.fixture
def engine():
    """Fresh in-memory SQLite engine with StaticPool (shared across connections)."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine) -> Iterator[OrmSession]:
    """Test-scoped ORM session. Commits land in the in-memory DB per-test."""
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Write a minimal integration smoke test at `tests/integration/test_models_smoke.py`**

```python
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
```

- [ ] **Step 6: Run tests + lint + types**

```bash
cd backend && uv run pytest tests/integration/test_models_smoke.py -v
cd backend && uv run ruff check src/hangman/models.py src/hangman/db.py tests/conftest.py
cd backend && uv run mypy src/hangman/models.py src/hangman/db.py
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/src/hangman/models.py backend/src/hangman/db.py \
        backend/tests/integration/__init__.py backend/tests/integration/test_models_smoke.py \
        backend/tests/conftest.py
git commit -m "feat(db): add SQLAlchemy 2.0 Session+Game models, engine/session factory, test fixtures"
```

---

## Task 7: `schemas.py` — Pydantic v2 DTOs

**Files:**

- Create: `backend/src/hangman/schemas.py`
- Create: `backend/tests/unit/test_schemas.py`

**Design reference:** `docs/plans/2026-04-22-hangman-scaffold-design.md` §2 `schemas.py`.

- [ ] **Step 1: Write tests at `tests/unit/test_schemas.py`**

```python
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
    gr = GuessRequest(letter=letter)
    assert gr.letter == letter.lower()  # normalized


@pytest.mark.parametrize("bad", ["", "ab", "1", "!", " "])
def test_guess_request_rejects_bad_letter(bad: str) -> None:
    with pytest.raises(ValidationError):
        GuessRequest(letter=bad)


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
```

- [ ] **Step 2: Confirm RED**

```bash
cd backend && uv run pytest tests/unit/test_schemas.py -v
```

- [ ] **Step 3: Write `src/hangman/schemas.py`**

```python
"""Pydantic v2 request/response DTOs. Response shapes are what clients see."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator, model_serializer

from hangman.game import DIFFICULTY_LIVES, mask_word

Difficulty = Literal["easy", "medium", "hard"]
GameState = Literal["IN_PROGRESS", "WON", "LOST"]


# ---- Requests ----

class GameCreate(BaseModel):
    category: str = Field(min_length=1)
    difficulty: Difficulty


class GuessRequest(BaseModel):
    letter: Annotated[str, Field(min_length=1, max_length=1)]

    @field_validator("letter", mode="before")
    @classmethod
    def _normalize(cls, v: Any) -> Any:
        if not isinstance(v, str) or len(v) != 1:
            return v  # let Field constraint fail
        lowered = v.lower()
        if not ("a" <= lowered <= "z"):
            raise ValueError("letter must be a-z")
        return lowered


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
    def _omit_word_in_progress(self, handler: Any) -> dict[str, Any]:  # type: ignore[misc]
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
    def from_game_row(  # type: ignore[override]
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
        DifficultyOption(id="medium", label="Medium", wrong_guesses_allowed=DIFFICULTY_LIVES["medium"]),
        DifficultyOption(id="hard", label="Hard", wrong_guesses_allowed=DIFFICULTY_LIVES["hard"]),
    ]
```

- [ ] **Step 4: Confirm GREEN + lint + types**

```bash
cd backend && uv run pytest tests/unit/test_schemas.py -v
cd backend && uv run ruff check src/hangman/schemas.py tests/unit/test_schemas.py
cd backend && uv run mypy src/hangman/schemas.py
```

- [ ] **Step 5: Commit**

```bash
git add backend/src/hangman/schemas.py backend/tests/unit/test_schemas.py
git commit -m "feat(schemas): add Pydantic v2 request/response DTOs + GameResponse word-reveal logic"
```

---

## Task 8: `errors.py` — error envelope + request-id middleware + handlers

**Files:**

- Create: `backend/src/hangman/errors.py`
- Create: `backend/tests/unit/test_errors.py`

**Design reference:** `docs/plans/2026-04-22-hangman-scaffold-design.md` §2 `errors.py`.

- [ ] **Step 1: Write tests at `tests/unit/test_errors.py`**

```python
"""Unit tests for HangmanError and helpers. Middleware/handler tests live in integration."""

from hangman.errors import HangmanError, build_error_envelope


def test_hangman_error_carries_fields() -> None:
    e = HangmanError(
        code="GAME_NOT_FOUND",
        http_status=404,
        message="no such game",
        details=[{"field": "id"}],
    )
    assert e.code == "GAME_NOT_FOUND"
    assert e.http_status == 404
    assert e.message == "no such game"
    assert e.details == [{"field": "id"}]


def test_hangman_error_defaults_details_to_empty_list() -> None:
    e = HangmanError(code="X", http_status=400, message="m")
    assert e.details == []


def test_build_error_envelope_shape() -> None:
    env = build_error_envelope(code="X", message="m", request_id="req_1")
    assert env == {
        "error": {
            "code": "X",
            "message": "m",
            "details": [],
            "request_id": "req_1",
        }
    }


def test_build_error_envelope_includes_details() -> None:
    env = build_error_envelope(code="X", message="m", request_id=None, details=[{"a": 1}])
    assert env["error"]["details"] == [{"a": 1}]
    assert env["error"]["request_id"] is None
```

- [ ] **Step 2: Confirm RED**

- [ ] **Step 3: Write `src/hangman/errors.py`**

```python
"""Error envelope, typed domain errors, request-id middleware, exception handlers."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class HangmanError(Exception):
    """Typed domain error that the handler renders as the standard envelope."""

    def __init__(
        self,
        *,
        code: str,
        http_status: int,
        message: str,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.message = message
        self.details = details or []


def build_error_envelope(
    *,
    code: str,
    message: str,
    request_id: str | None,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "request_id": request_id,
        }
    }


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:16]}"
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def handle_hangman_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HangmanError)
    return JSONResponse(
        status_code=exc.http_status,
        content=build_error_envelope(
            code=exc.code,
            message=exc.message,
            request_id=_request_id(request),
            details=exc.details,
        ),
    )


async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return JSONResponse(
        status_code=422,
        content=build_error_envelope(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            request_id=_request_id(request),
            details=[{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()],
        ),
    )


async def handle_uncaught(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=build_error_envelope(
            code="INTERNAL_ERROR",
            message="Internal server error",
            request_id=_request_id(request),
        ),
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HangmanError, handle_hangman_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_uncaught)
```

- [ ] **Step 4: Confirm GREEN + lint + types**

```bash
cd backend && uv run pytest tests/unit/test_errors.py -v
cd backend && uv run ruff check src/hangman/errors.py tests/unit/test_errors.py
cd backend && uv run mypy src/hangman/errors.py
```

- [ ] **Step 5: Commit**

```bash
git add backend/src/hangman/errors.py backend/tests/unit/test_errors.py
git commit -m "feat(errors): add HangmanError + request-id middleware + standard envelope handlers"
```

---

## Task 9: `sessions.py` — cookie dependency

**Files:**

- Create: `backend/src/hangman/sessions.py`
- Create: `backend/tests/integration/test_session_cookie.py`
- Modify: `backend/tests/conftest.py` (add `client` fixture scaffolding — will be finalized in Task 15)

**Design reference:** `docs/plans/2026-04-22-hangman-scaffold-design.md` §2 `sessions.py`.

- [ ] **Step 1: Write `src/hangman/sessions.py`**

```python
"""Session cookie dependency — hand-rolled, not Starlette SessionMiddleware."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session as OrmSession

from hangman.db import get_session
from hangman.models import Session

COOKIE_NAME = "session_id"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days


def get_or_create_session(
    request: Request,
    response: Response,
    db: OrmSession = Depends(get_session),
) -> Session:
    """Load the session tied to the request cookie, or create a new one. Sets / refreshes the cookie."""
    cookie_value = request.cookies.get(COOKIE_NAME)
    session: Session | None = db.get(Session, cookie_value) if cookie_value else None
    if session is None:
        session = Session(id=str(uuid4()))
        db.add(session)
        db.flush()
    session.updated_at = datetime.now(timezone.utc)

    response.set_cookie(
        key=COOKIE_NAME,
        value=session.id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return session
```

- [ ] **Step 2: Extend `tests/conftest.py` — add a `client` fixture scaffold**

Replace `conftest.py` with:

```python
"""Shared pytest fixtures for the backend test suite."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from hangman.db import get_session
from hangman.models import Base
from hangman.words import WordPool


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine) -> Iterator[OrmSession]:
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_word_pool() -> WordPool:
    # 'test' is a deterministic 1-word category used by scoring/win tests that
    # need a hermetic path: POST /games {category: "test"} → always pick "cat" →
    # guess c, a, t → win. Avoids nondeterministic "guess a-z exhaustively" flakes.
    return WordPool(
        categories={
            "animals": ("cat", "dog", "bird", "fish"),
            "food": ("pizza", "taco", "pasta"),
            "test": ("cat",),
        }
    )


@pytest.fixture
def client(engine, test_word_pool) -> Iterator[TestClient]:
    """TestClient with an in-memory DB + test word pool injected via dependency overrides + app.state."""
    # Import lazily so tasks before `main.py` exists can still run.
    from hangman.main import app

    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def _override_get_session() -> Iterator[OrmSession]:
        db = TestingSession()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_session] = _override_get_session
    with TestClient(app) as c:
        c.app.state.word_pool = test_word_pool  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()
```

> **Note to the subagent:** this `client` fixture imports `hangman.main`. Task 15 creates `main.py`. Tests that don't need the full app (e.g. `test_models_smoke.py`, `test_session_cookie.py` via direct DB manipulation) should use `db_session` instead. `test_session_cookie.py` below stands up a minimal FastAPI app in-test so it does not depend on Task 15.

- [ ] **Step 3: Write `tests/integration/test_session_cookie.py` (stands up a minimal app)**

```python
"""Integration test for get_or_create_session cookie behavior.

Uses a minimal in-test FastAPI app so the test does not depend on the full main.py assembly.
"""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker

from hangman.db import get_session
from hangman.models import Session
from hangman.sessions import COOKIE_MAX_AGE, COOKIE_NAME, get_or_create_session


def _make_app(engine) -> FastAPI:
    app = FastAPI()
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def _override_get_session():
        db = TestingSession()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_session] = _override_get_session

    @app.get("/whoami")
    def whoami(s: Session = Depends(get_or_create_session)) -> dict:
        return {"session_id": s.id, "current_streak": s.current_streak}

    return app


def test_first_request_sets_cookie(engine) -> None:
    client = TestClient(_make_app(engine))
    res = client.get("/whoami")
    assert res.status_code == 200
    body = res.json()
    assert len(body["session_id"]) > 0
    # Inspect Set-Cookie for attributes.
    set_cookie = res.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie.lower() or "samesite=lax" in set_cookie.lower()
    assert f"Max-Age={COOKIE_MAX_AGE}" in set_cookie or f"max-age={COOKIE_MAX_AGE}" in set_cookie.lower()


def test_subsequent_requests_reuse_session(engine) -> None:
    client = TestClient(_make_app(engine))
    first = client.get("/whoami")
    sid_first = first.json()["session_id"]
    second = client.get("/whoami")
    assert second.json()["session_id"] == sid_first


def test_stale_cookie_creates_fresh_session(engine) -> None:
    client = TestClient(_make_app(engine))
    client.cookies.set(COOKIE_NAME, "not-a-real-uuid")
    res = client.get("/whoami")
    assert res.status_code == 200
    assert res.json()["session_id"] != "not-a-real-uuid"
```

- [ ] **Step 4: Run just this test (don't run whole suite yet; client fixture depends on main.py)**

```bash
cd backend && uv run pytest tests/integration/test_session_cookie.py -v
```

- [ ] **Step 5: Lint + types**

```bash
cd backend && uv run ruff check src/hangman/sessions.py tests/integration/test_session_cookie.py tests/conftest.py
cd backend && uv run mypy src/hangman/sessions.py
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/hangman/sessions.py backend/tests/integration/test_session_cookie.py backend/tests/conftest.py
git commit -m "feat(sessions): add get_or_create_session cookie dependency + cookie-lifecycle test"
```

---

## Task 10: `routes.py` + `main.py` — build incrementally with integration tests per endpoint

**Files:**

- Create: `backend/src/hangman/routes.py`
- Create: `backend/src/hangman/main.py`
- Create: `backend/tests/integration/test_categories.py`
- Create: `backend/tests/integration/test_session_endpoint.py`
- Create: `backend/tests/integration/test_games_start.py`
- Create: `backend/tests/integration/test_games_forfeit.py`
- Create: `backend/tests/integration/test_guesses.py`
- Create: `backend/tests/integration/test_games_current.py`
- Create: `backend/tests/integration/test_history.py`

**Design reference:** `docs/plans/2026-04-22-hangman-scaffold-design.md` §2 `routes.py`, §2 `main.py`, §4 data flow (happy + forfeit + error paths).

This task is larger than others because routes + main.py + their tests are tightly coupled; splitting them across multiple tasks would create temporary broken states.

> **TDD protocol for this task.** Steps 1–2 show the **reference implementation** of `main.py` and `routes.py` so you have them in front of you when writing tests. **Do not type them into files yet.** Write all integration tests first (Steps 3–9), confirm they fail because the modules don't exist (Step 10 = RED). Then in Step 11 create `main.py` and `routes.py` using the reference code from Steps 1–2. Step 12 reruns the suite to confirm GREEN. This preserves the test-first discipline on a cohesive multi-endpoint task.

- [ ] **Step 1 (REFERENCE, do not type yet): `src/hangman/main.py` will look like this**

```python
"""FastAPI app assembly + lifespan."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from hangman.db import engine
from hangman.errors import RequestIdMiddleware, install_error_handlers
from hangman.models import Base
from hangman.routes import router
from hangman.words import load_words


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    words_path = Path(__file__).resolve().parent.parent.parent / "words.txt"
    app.state.word_pool = load_words(words_path)
    yield


app = FastAPI(lifespan=lifespan, title="Hangman API", version="0.1.0")
app.add_middleware(RequestIdMiddleware)
install_error_handlers(app)
app.include_router(router)
```

- [ ] **Step 2 (REFERENCE, do not type yet): `src/hangman/routes.py` will look like this**

```python
"""HTTP routes. One APIRouter at /api/v1."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from hangman.db import get_session
from hangman.errors import HangmanError
from hangman.game import (
    DIFFICULTY_LIVES,
    AlreadyGuessed,
    InvalidLetter,
    apply_guess,
    compute_round_score,
)
from hangman.models import STATE_IN_PROGRESS, STATE_LOST, STATE_WON, Game, Session
from hangman.schemas import (
    CategoriesResponse,
    CreateGameResponse,
    GameCreate,
    GameResponse,
    GuessRequest,
    HistoryResponse,
    SessionResponse,
    difficulty_options,
)
from hangman.sessions import get_or_create_session
from hangman.words import WordPool

router = APIRouter(prefix="/api/v1")


def _word_pool(request: Request) -> WordPool:
    return request.app.state.word_pool  # populated in main.lifespan


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _game_to_response(g: Game) -> GameResponse:
    return GameResponse.from_game_row(
        _word=g.word,
        id=g.id,
        category=g.category,
        difficulty=g.difficulty,
        wrong_guesses_allowed=g.wrong_guesses_allowed,
        wrong_guesses=g.wrong_guesses,
        guessed_letters=g.guessed_letters,
        state=g.state,
        score=g.score,
        started_at=g.started_at,
        finished_at=g.finished_at,
    )


def _game_to_create_response(g: Game, forfeited_game_id: int | None) -> CreateGameResponse:
    return CreateGameResponse.from_game_row(
        _word=g.word,
        forfeited_game_id=forfeited_game_id,
        id=g.id,
        category=g.category,
        difficulty=g.difficulty,
        wrong_guesses_allowed=g.wrong_guesses_allowed,
        wrong_guesses=g.wrong_guesses,
        guessed_letters=g.guessed_letters,
        state=g.state,
        score=g.score,
        started_at=g.started_at,
        finished_at=g.finished_at,
    )


def _assert_category_known(pool: WordPool, category: str) -> None:
    if category not in pool.categories:
        raise HangmanError(
            code="UNKNOWN_CATEGORY",
            http_status=422,
            message=f"Unknown category: {category!r}",
            details=[{"field": "category", "known": pool.category_names()}],
        )


# ---- GET /categories ----

@router.get("/categories", response_model=CategoriesResponse)
def list_categories(
    request: Request,
    # Cookie is created/refreshed on this route too — PRD US-004 requires a
    # session cookie on ANY first request. Callers typically hit /categories first.
    _session: Session = Depends(get_or_create_session),
) -> CategoriesResponse:
    pool = _word_pool(request)
    return CategoriesResponse(
        categories=pool.category_names(),
        difficulties=difficulty_options(),
    )


# ---- GET /session ----

@router.get("/session", response_model=SessionResponse)
def get_session_state(
    session: Session = Depends(get_or_create_session),
) -> SessionResponse:
    return SessionResponse(
        current_streak=session.current_streak,
        best_streak=session.best_streak,
        total_score=session.total_score,
    )


# ---- POST /games ----

@router.post(
    "/games",
    response_model=CreateGameResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_game(
    payload: GameCreate,
    request: Request,
    response: Response,
    session: Session = Depends(get_or_create_session),
    db: OrmSession = Depends(get_session),
) -> CreateGameResponse:
    pool = _word_pool(request)
    _assert_category_known(pool, payload.category)

    # Forfeit any existing IN_PROGRESS game in the same transaction.
    stmt = select(Game).where(Game.session_id == session.id, Game.state == STATE_IN_PROGRESS)
    prior = db.execute(stmt).scalar_one_or_none()
    forfeited_id: int | None = None
    if prior is not None:
        prior.state = STATE_LOST
        prior.score = 0
        prior.finished_at = _now_utc()
        session.current_streak = 0
        forfeited_id = prior.id

    word = pool.random_word(payload.category)
    allowed = DIFFICULTY_LIVES[payload.difficulty]
    new_game = Game(
        session_id=session.id,
        category=payload.category,
        difficulty=payload.difficulty,
        word=word,
        wrong_guesses_allowed=allowed,
        state=STATE_IN_PROGRESS,
    )
    db.add(new_game)
    db.flush()  # assign id

    response.headers["Location"] = f"/api/v1/games/{new_game.id}"
    return _game_to_create_response(new_game, forfeited_id)


# ---- GET /games/current ----

@router.get("/games/current", response_model=GameResponse)
def get_current_game(
    session: Session = Depends(get_or_create_session),
    db: OrmSession = Depends(get_session),
) -> GameResponse:
    stmt = select(Game).where(Game.session_id == session.id, Game.state == STATE_IN_PROGRESS)
    game = db.execute(stmt).scalar_one_or_none()
    if game is None:
        raise HangmanError(
            code="NO_ACTIVE_GAME",
            http_status=404,
            message="No active game.",
        )
    return _game_to_response(game)


# ---- POST /games/{game_id}/guesses ----

@router.post("/games/{game_id}/guesses", response_model=GameResponse)
def submit_guess(
    game_id: int,
    payload: GuessRequest,
    session: Session = Depends(get_or_create_session),
    db: OrmSession = Depends(get_session),
) -> GameResponse:
    game = db.get(Game, game_id)
    if game is None or game.session_id != session.id:
        raise HangmanError(code="GAME_NOT_FOUND", http_status=404, message="Game not found.")
    if game.state != STATE_IN_PROGRESS:
        raise HangmanError(
            code="GAME_ALREADY_FINISHED",
            http_status=409,
            message=f"Game is {game.state}.",
        )

    try:
        result = apply_guess(
            word=game.word,
            guessed=game.guessed_letters,
            wrong=game.wrong_guesses,
            allowed=game.wrong_guesses_allowed,
            letter=payload.letter,
        )
    except AlreadyGuessed as e:
        raise HangmanError(code="ALREADY_GUESSED", http_status=422, message=str(e)) from e
    except InvalidLetter as e:
        raise HangmanError(code="INVALID_LETTER", http_status=422, message=str(e)) from e

    game.guessed_letters = result.new_guessed
    game.wrong_guesses = result.new_wrong_guesses
    game.state = result.new_state
    if result.correct_reveal:
        game.correct_reveals += 1

    if result.new_state == STATE_WON:
        lives_remaining = game.wrong_guesses_allowed - game.wrong_guesses
        new_streak = session.current_streak + 1
        game.score = compute_round_score(
            correct_reveals=game.correct_reveals,
            lives_remaining=lives_remaining,
            streak_after_win=new_streak,
        )
        session.current_streak = new_streak
        session.best_streak = max(session.best_streak, new_streak)
        session.total_score = session.total_score + game.score
        game.finished_at = _now_utc()
    elif result.new_state == STATE_LOST:
        game.score = 0
        session.current_streak = 0
        game.finished_at = _now_utc()

    return _game_to_response(game)


# ---- GET /history ----

@router.get("/history", response_model=HistoryResponse)
def list_history(
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_or_create_session),
    db: OrmSession = Depends(get_session),
) -> HistoryResponse:
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100

    base_stmt = (
        select(Game)
        .where(Game.session_id == session.id, Game.state.in_([STATE_WON, STATE_LOST]))
        .order_by(Game.finished_at.desc())
    )

    # Count (cheap on SQLite for small tables)
    from sqlalchemy import func

    total = db.execute(
        select(func.count(Game.id)).where(
            Game.session_id == session.id, Game.state.in_([STATE_WON, STATE_LOST])
        )
    ).scalar_one()

    offset = (page - 1) * page_size
    games = db.execute(base_stmt.limit(page_size).offset(offset)).scalars().all()

    return HistoryResponse(
        items=[_game_to_response(g) for g in games],
        total=int(total),
        page=page,
        page_size=page_size,
    )
```

- [ ] **Step 3: Write `tests/integration/test_categories.py`**

```python
from hangman.sessions import COOKIE_MAX_AGE, COOKIE_NAME


def test_categories_endpoint_returns_loaded_pool(client) -> None:
    res = client.get("/api/v1/categories")
    assert res.status_code == 200
    body = res.json()
    # test_word_pool has animals + food + test (one-word deterministic category).
    assert set(body["categories"]) == {"animals", "food", "test"}
    assert [d["id"] for d in body["difficulties"]] == ["easy", "medium", "hard"]
    assert [d["wrong_guesses_allowed"] for d in body["difficulties"]] == [8, 6, 4]


def test_categories_sets_session_cookie_on_first_call(client) -> None:
    """PRD US-004: cookie is set on ANY no-cookie request — including /categories."""
    # Fresh client has no cookie yet.
    client.cookies.clear()
    res = client.get("/api/v1/categories")
    assert res.status_code == 200
    set_cookie = res.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie
    assert "lax" in set_cookie.lower()
    assert str(COOKIE_MAX_AGE) in set_cookie
```

- [ ] **Step 4: Write `tests/integration/test_session_endpoint.py`**

```python
from hangman.sessions import COOKIE_MAX_AGE, COOKIE_NAME


def test_session_endpoint_returns_zeros_on_fresh_session(client) -> None:
    res = client.get("/api/v1/session")
    assert res.status_code == 200
    body = res.json()
    assert body == {"current_streak": 0, "best_streak": 0, "total_score": 0}


def test_session_endpoint_sets_cookie_with_required_attributes(client) -> None:
    res = client.get("/api/v1/session")
    set_cookie = res.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie
    assert "lax" in set_cookie.lower()
    assert str(COOKIE_MAX_AGE) in set_cookie


def test_session_endpoint_is_idempotent(client) -> None:
    r1 = client.get("/api/v1/session")
    r2 = client.get("/api/v1/session")
    assert r1.json() == r2.json()
```

- [ ] **Step 5: Write `tests/integration/test_games_start.py`**

```python
def test_start_game_returns_201_with_location_and_masked_word(client) -> None:
    res = client.post("/api/v1/games", json={"category": "animals", "difficulty": "easy"})
    assert res.status_code == 201
    assert res.headers["location"].startswith("/api/v1/games/")
    body = res.json()
    assert body["category"] == "animals"
    assert body["difficulty"] == "easy"
    assert body["wrong_guesses_allowed"] == 8
    assert body["lives_remaining"] == 8
    assert body["state"] == "IN_PROGRESS"
    # PRD US-001: `word` key MUST be absent mid-game (not null). Enforce strictly.
    assert "word" not in body
    assert set(body["masked_word"]) == {"_"}
    assert body["forfeited_game_id"] is None


def test_start_game_422_on_unknown_category(client) -> None:
    res = client.post("/api/v1/games", json={"category": "weapons", "difficulty": "easy"})
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "UNKNOWN_CATEGORY"


def test_start_game_422_on_bad_difficulty(client) -> None:
    res = client.post("/api/v1/games", json={"category": "animals", "difficulty": "godlike"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
```

- [ ] **Step 6: Write `tests/integration/test_games_forfeit.py`**

```python
def test_starting_new_game_forfeits_prior_in_progress(client) -> None:
    first = client.post("/api/v1/games", json={"category": "animals", "difficulty": "easy"}).json()
    second = client.post("/api/v1/games", json={"category": "food", "difficulty": "medium"}).json()
    assert second["forfeited_game_id"] == first["id"]

    history = client.get("/api/v1/history").json()
    forfeited = next(item for item in history["items"] if item["id"] == first["id"])
    assert forfeited["state"] == "LOST"
    assert forfeited["score"] == 0
    # Streak reset
    assert client.get("/api/v1/session").json()["current_streak"] == 0


def test_starting_with_no_prior_game_has_null_forfeited(client) -> None:
    res = client.post("/api/v1/games", json={"category": "animals", "difficulty": "easy"})
    assert res.json()["forfeited_game_id"] is None
```

- [ ] **Step 7: Write `tests/integration/test_guesses.py`**

```python
def _start_game(client, category="animals", difficulty="easy") -> dict:
    res = client.post("/api/v1/games", json={"category": category, "difficulty": difficulty})
    assert res.status_code == 201
    return res.json()


def _guess(client, game_id: int, letter: str):
    return client.post(f"/api/v1/games/{game_id}/guesses", json={"letter": letter})


def test_correct_guess_reveals_letter(client) -> None:
    game = _start_game(client)
    # seed pool only has 'cat', 'dog', 'bird', 'fish'. Try guessing vowels until one reveals.
    res = _guess(client, game["id"], "a")
    assert res.status_code == 200
    body = res.json()
    # Either revealed (correct_reveal) or not — both are valid. If a reveal, masked_word has 'a'.
    assert body["state"] in {"IN_PROGRESS", "WON", "LOST"}


def test_wrong_guess_decrements_lives(client) -> None:
    game = _start_game(client)
    res = _guess(client, game["id"], "z")
    body = res.json()
    # 'z' is not in any seed word
    assert body["wrong_guesses"] == 1
    assert body["lives_remaining"] == game["lives_remaining"] - 1


def test_uppercase_guess_normalized(client) -> None:
    game = _start_game(client)
    res1 = _guess(client, game["id"], "A")
    res2 = _guess(client, game["id"], "a")
    assert res1.status_code == 200
    # second call should be ALREADY_GUESSED
    assert res2.status_code == 422
    assert res2.json()["error"]["code"] == "ALREADY_GUESSED"


def test_invalid_letter_422(client) -> None:
    game = _start_game(client)
    res = _guess(client, game["id"], "1")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_guess_on_nonexistent_game_404(client) -> None:
    res = _guess(client, 99999, "a")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "GAME_NOT_FOUND"


def test_cross_session_access_returns_404(client) -> None:
    game = _start_game(client)
    # Swap cookie to simulate different session.
    client.cookies.clear()
    res = _guess(client, game["id"], "a")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "GAME_NOT_FOUND"


def test_winning_updates_session_and_game_score_deterministic(client) -> None:
    """Hermetic win: `test` category has exactly one word ('cat').
    Guess c, a, t → WON. Assert exact score + streak update."""
    game = _start_game(client, category="test", difficulty="easy")  # 8 lives
    assert "word" not in game, "word must be absent mid-game"

    # Three correct guesses in a row.
    for letter in ("c", "a", "t"):
        res = _guess(client, game["id"], letter)
        assert res.status_code == 200

    final = res.json()  # noqa: F821 — last iteration's response
    assert final["state"] == "WON"
    assert final["word"] == "cat", "word revealed on WON"

    # correct_reveals = 3 (c, a, t each revealed >=1 letter).
    # lives_remaining = 8 (no wrong guesses).
    # Streak after win = 1 → multiplier = 1×.
    # Score = (3 * 10) + (8 * 5) = 70. × 1 = 70.
    assert final["score"] == 70

    session = client.get("/api/v1/session").json()
    assert session["current_streak"] == 1
    assert session["best_streak"] == 1
    assert session["total_score"] == 70

    history = client.get("/api/v1/history").json()
    assert history["total"] == 1
    assert history["items"][0]["state"] == "WON"
    assert history["items"][0]["score"] == 70


def test_losing_zeroes_streak_and_score(client) -> None:
    """Hermetic loss: start `test/hard` (4 lives, word='cat'), guess 4 wrong letters."""
    game = _start_game(client, category="test", difficulty="hard")
    for letter in ("z", "q", "x", "w"):  # 4 wrong guesses exhausts lives
        res = _guess(client, game["id"], letter)
        assert res.status_code == 200

    final = res.json()  # noqa: F821
    assert final["state"] == "LOST"
    assert final["word"] == "cat"
    assert final["score"] == 0

    session = client.get("/api/v1/session").json()
    assert session["current_streak"] == 0
    assert session["total_score"] == 0


def test_streak_multiplier_across_two_consecutive_wins(client) -> None:
    """Streak-after-win of 2 should trigger 2× multiplier on the second win."""
    # First win
    game1 = _start_game(client, category="test", difficulty="easy")
    for letter in ("c", "a", "t"):
        _guess(client, game1["id"], letter)
    # Second win — should apply 2× multiplier
    game2 = _start_game(client, category="test", difficulty="easy")
    for letter in ("c", "a", "t"):
        last = _guess(client, game2["id"], letter)
    final2 = last.json()
    assert final2["state"] == "WON"
    # Base = 3*10 + 8*5 = 70. Streak after this win = 2 → multiplier 2 → 140.
    assert final2["score"] == 140
    session = client.get("/api/v1/session").json()
    assert session["current_streak"] == 2
    assert session["best_streak"] == 2
    assert session["total_score"] == 70 + 140


def test_guess_on_finished_game_409(client) -> None:
    """Hermetic: win category=test (word=cat), then try to guess on the finished game."""
    game = _start_game(client, category="test", difficulty="easy")
    for letter in ("c", "a", "t"):
        _guess(client, game["id"], letter)
    # Game is now WON; any further guess must be 409 GAME_ALREADY_FINISHED.
    res = _guess(client, game["id"], "z")  # 'z' was not previously guessed
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "GAME_ALREADY_FINISHED"
```

- [ ] **Step 8: Write `tests/integration/test_games_current.py`**

```python
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
```

- [ ] **Step 9: Write `tests/integration/test_history.py`**

```python
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
```

- [ ] **Step 10: Confirm RED — run the suite with only test files on disk**

At this point `main.py` + `routes.py` still do not exist on disk (Steps 1–2 were reference only). Running pytest must fail with `ModuleNotFoundError: No module named 'hangman.main'` from `conftest.py`'s `client` fixture — or, if a test that doesn't use `client` runs first, the collection proceeds and the first HTTP-requiring test fails on import. This is the RED stage.

```bash
cd backend && uv run pytest -v 2>&1 | head -30
```

Expected: import errors or failing tests citing missing endpoints / routes. Do NOT proceed to Step 11 unless RED is confirmed.

- [ ] **Step 11: Create `src/hangman/main.py` + `src/hangman/routes.py` from the Step 1 / Step 2 reference code**

Write the files using the code blocks in Steps 1 and 2 verbatim. No ad-hoc changes.

- [ ] **Step 12: Confirm GREEN — full suite**

```bash
cd backend && uv run pytest -v
```

Expected: all unit + integration tests pass. If any test_history case fails because the forfeit chain doesn't produce the exact counts — read the failure carefully and reconcile (the "total=4" assertion expects 5 starts → 4 forfeited + 1 active).

- [ ] **Step 13: Lint + type check**

```bash
cd backend && uv run ruff check .
cd backend && uv run ruff format --check .
cd backend && uv run mypy src/hangman
```

All clean.

- [ ] **Step 14: Commit**

```bash
git add backend/src/hangman/main.py backend/src/hangman/routes.py backend/tests/integration/
git commit -m "feat(api): add 6 endpoints (categories, session, games CRUD, guesses, history) with full integration tests"
```

---

## Task 11: Frontend scaffold — manual file creation (no `pnpm create vite`)

Why not `pnpm create vite`? The interactive prompt surface in Vite 8 is unpredictable (may ask about Rolldown, TypeScript variants, etc.) and a background subagent can hang waiting for stdin. Tasks 12–14 overwrite almost everything a template would produce anyway, so we write the minimum set of files by hand here. This is deterministic and subagent-safe.

**Files (all created manually):**

- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx` (stub; replaced fully in Task 22)
- Create: `frontend/src/index.css` (empty; populated in Task 22)
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/.gitignore` (frontend-local; root `.gitignore` already covers most of it)

**Design reference:** `docs/plans/2026-04-22-hangman-scaffold-design.md` §1 (frontend tree).

- [ ] **Step 1: Write `frontend/package.json` with pinned versions**

```json
{
  "name": "hangman-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "packageManager": "pnpm@10.5.0",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:run": "vitest run",
    "lint": "eslint .",
    "format": "prettier --write .",
    "format:check": "prettier --check ."
  },
  "dependencies": {
    "react": "^19.2.0",
    "react-dom": "^19.2.0"
  },
  "devDependencies": {
    "@eslint/js": "^9.10.0",
    "@playwright/test": "^1.59.0",
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@types/node": "^22.0.0",
    "@types/react": "^19.2.0",
    "@types/react-dom": "^19.2.0",
    "@vitejs/plugin-react": "^5.0.0",
    "eslint": "^9.10.0",
    "eslint-config-prettier": "^10.0.0",
    "eslint-plugin-react-hooks": "^5.0.0",
    "eslint-plugin-react-refresh": "^0.4.0",
    "jsdom": "^25.0.0",
    "prettier": "^3.3.0",
    "typescript": "^5.7.0",
    "typescript-eslint": "^8.0.0",
    "vite": "^8.0.0",
    "vitest": "^3.0.0"
  }
}
```

- [ ] **Step 2: Write `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Hangman</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 3: Write `frontend/src/vite-env.d.ts`**

```ts
/// <reference types="vite/client" />
```

- [ ] **Step 4: Write placeholder `frontend/src/App.tsx` (fully replaced in Task 22)**

```tsx
export default function App() {
  return <div>Hangman scaffold — wiring in progress.</div>;
}
```

- [ ] **Step 5: Write placeholder `frontend/src/main.tsx` (fully replaced in Task 22)**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 6: Write empty placeholder `frontend/src/index.css` (populated in Task 22)**

```css
/* Populated in Task 22. */
```

- [ ] **Step 7: Write `frontend/.gitignore` (local overrides on top of root .gitignore)**

```gitignore
node_modules/
dist/
.vite/
playwright-report/
test-results/
blob-report/
```

- [ ] **Step 8: Install pinned versions**

```bash
cd frontend && pnpm install
```

If pnpm prompts to approve scripts (e.g. Playwright post-install), pass `--ignore-scripts` on first run — Playwright browsers are installed explicitly in Task 23.

- [ ] **Step 9: Verify the placeholder builds + types**

```bash
cd frontend && pnpm tsc --noEmit -p tsconfig.app.json 2>&1 | head -20 || true
```

`tsconfig.app.json` doesn't exist yet (Task 12 creates it). This step is expected to fail until Task 12 runs. Alternative sanity check:

```bash
cd frontend && pnpm exec vite --version
```

Should print `vite/8.x.x`.

- [ ] **Step 10: Commit**

```bash
cd .. && git add frontend/
git commit -m "chore(frontend): manual scaffold — package.json pinned to React 19 + Vite 8 + pnpm 10"
```

---

## Task 12: `vite.config.ts` with proxy + `tsconfig` split

**Files:**

- Modify: `frontend/vite.config.ts`
- Modify: `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, `frontend/tsconfig.node.json`

- [ ] **Step 1: Write `frontend/vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 2: `frontend/tsconfig.json` (project references root)**

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ],
  "compilerOptions": {
    "skipLibCheck": true
  }
}
```

- [ ] **Step 3: `frontend/tsconfig.app.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "resolveJsonModule": true,

    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"]
}
```

- [ ] **Step 4: `frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "target": "ES2023",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,

    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,

    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["vite.config.ts", "vitest.config.ts", "playwright.config.ts"]
}
```

- [ ] **Step 5: Verify `tsc --noEmit` passes**

```bash
cd frontend && pnpm tsc --noEmit -p tsconfig.app.json
```

May produce errors if App.tsx from the template still has extra imports — we'll fix in Task 17. For now, if there are errors only in `src/App.tsx` because we deleted App.css, that's expected.

- [ ] **Step 6: Commit**

```bash
cd .. && git add frontend/vite.config.ts frontend/tsconfig.json frontend/tsconfig.app.json frontend/tsconfig.node.json
git commit -m "chore(frontend): add Vite proxy to :8000 + tsconfig split (strict, bundler resolution)"
```

---

## Task 13: ESLint 9 flat config + Prettier 3

**Files:**

- Modify: `frontend/eslint.config.js`
- Create: `frontend/.prettierrc.json`
- Create: `frontend/.prettierignore`

- [ ] **Step 1: Write `frontend/eslint.config.js`**

```js
import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";
import prettier from "eslint-config-prettier/flat";

export default tseslint.config(
  { ignores: ["dist", "node_modules", "playwright-report", "test-results"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
    },
  },
  prettier,
);
```

- [ ] **Step 2: Write `frontend/.prettierrc.json`**

```json
{
  "semi": true,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100
}
```

- [ ] **Step 3: Write `frontend/.prettierignore`**

```
dist
node_modules
playwright-report
test-results
pnpm-lock.yaml
```

- [ ] **Step 4: Run ESLint + Prettier on current state**

```bash
cd frontend && pnpm lint
cd frontend && pnpm format:check
```

Expected: may warn on the default `App.tsx` template. Fixing in Task 17. For now: no ESLint crashes.

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/eslint.config.js frontend/.prettierrc.json frontend/.prettierignore
git commit -m "chore(frontend): add ESLint 9 flat config + Prettier 3 (separate tools, /flat suffix)"
```

---

## Task 14: Vitest config + `@testing-library` setup

**Files:**

- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/test/setup.ts`

- [ ] **Step 1: Write `frontend/vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
```

- [ ] **Step 2: Write `frontend/src/test/setup.ts`**

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 3: Write a smoke test at `frontend/src/test/smoke.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";

function Hello({ name }: { name: string }) {
  return <h1>Hello, {name}</h1>;
}

it("renders a greeting", () => {
  render(<Hello name="world" />);
  expect(
    screen.getByRole("heading", { name: /hello, world/i }),
  ).toBeInTheDocument();
});
```

- [ ] **Step 4: Run vitest**

```bash
cd frontend && pnpm test:run
```

Expected: 1 passing test.

- [ ] **Step 5: Delete the smoke test**

```bash
cd frontend && rm src/test/smoke.test.tsx
```

- [ ] **Step 6: Commit**

```bash
cd .. && git add frontend/vitest.config.ts frontend/src/test/setup.ts
git commit -m "chore(frontend): add Vitest + @testing-library/jest-dom setup (jsdom environment)"
```

---

## Task 15: `types.ts` + `api/client.ts`

**Files:**

- Create: `frontend/src/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/client.test.ts`

- [ ] **Step 1: Write `frontend/src/types.ts`**

```ts
export type Difficulty = "easy" | "medium" | "hard";
export type GameState = "IN_PROGRESS" | "WON" | "LOST";

export interface DifficultyOption {
  id: Difficulty;
  label: string;
  wrong_guesses_allowed: number;
}

export interface CategoriesDTO {
  categories: string[];
  difficulties: DifficultyOption[];
}

export interface SessionDTO {
  current_streak: number;
  best_streak: number;
  total_score: number;
}

export interface GameDTO {
  id: number;
  category: string;
  difficulty: Difficulty;
  wrong_guesses_allowed: number;
  wrong_guesses: number;
  guessed_letters: string;
  state: GameState;
  score: number;
  started_at: string;
  finished_at: string | null;
  masked_word: string;
  lives_remaining: number;
  // Absent (undefined) while IN_PROGRESS; present when state is WON or LOST.
  // Backend omits the key entirely mid-game — we model it as optional here, not
  // `string | null`, so `'word' in game` correctly reflects server intent.
  word?: string;
}

export interface CreateGameDTO extends GameDTO {
  forfeited_game_id: number | null;
}

export interface HistoryDTO {
  items: GameDTO[];
  total: number;
  page: number;
  page_size: number;
}

export interface GameCreateBody {
  category: string;
  difficulty: Difficulty;
}

export interface ErrorBody {
  error: {
    code: string;
    message: string;
    details: unknown[];
    request_id: string | null;
  };
}
```

- [ ] **Step 2: Write `frontend/src/api/client.ts`**

```ts
import type {
  CategoriesDTO,
  CreateGameDTO,
  ErrorBody,
  GameCreateBody,
  GameDTO,
  HistoryDTO,
  SessionDTO,
} from "../types";

const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: Partial<ErrorBody>,
  ) {
    super(body?.error?.message ?? `HTTP ${status}`);
    this.name = "ApiError";
  }

  get code(): string | undefined {
    return this.body?.error?.code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  getCategories: () => request<CategoriesDTO>("/categories"),
  getSession: () => request<SessionDTO>("/session"),
  getCurrentGame: () =>
    request<GameDTO>("/games/current").catch((e: unknown) => {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }),
  startGame: (body: GameCreateBody) =>
    request<CreateGameDTO>("/games", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  guess: (id: number, letter: string) =>
    request<GameDTO>(`/games/${id}/guesses`, {
      method: "POST",
      body: JSON.stringify({ letter }),
    }),
  getHistory: (page = 1, pageSize = 20) =>
    request<HistoryDTO>(`/history?page=${page}&page_size=${pageSize}`),
};
```

- [ ] **Step 3: Write `frontend/src/api/client.test.ts`**

```ts
import { ApiError, api } from "./client";

describe("api client", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("getCurrentGame returns null on 404", async () => {
    global.fetch = vi.fn(
      async () =>
        new Response(JSON.stringify({ error: { code: "NO_ACTIVE_GAME" } }), {
          status: 404,
        }),
    ) as typeof fetch;
    const res = await api.getCurrentGame();
    expect(res).toBeNull();
  });

  it("getCurrentGame throws ApiError on 500", async () => {
    global.fetch = vi.fn(
      async () =>
        new Response(JSON.stringify({ error: { code: "INTERNAL_ERROR" } }), {
          status: 500,
        }),
    ) as typeof fetch;
    await expect(api.getCurrentGame()).rejects.toBeInstanceOf(ApiError);
  });

  it("startGame posts JSON body with credentials include", async () => {
    const spy = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            id: 1,
            category: "animals",
            difficulty: "easy",
            wrong_guesses_allowed: 8,
            wrong_guesses: 0,
            guessed_letters: "",
            state: "IN_PROGRESS",
            score: 0,
            started_at: "2026-04-22T00:00:00Z",
            finished_at: null,
            masked_word: "___",
            lives_remaining: 8,
            // `word` is ABSENT (not null) mid-game — PRD US-001 + schemas.py serializer.
            forfeited_game_id: null,
          }),
          { status: 201 },
        ),
    );
    global.fetch = spy as typeof fetch;
    await api.startGame({ category: "animals", difficulty: "easy" });
    const [url, init] = spy.mock.calls[0];
    expect(url).toBe("/api/v1/games");
    expect(init?.method).toBe("POST");
    expect(init?.credentials).toBe("include");
  });

  it("ApiError exposes code via body", () => {
    const err = new ApiError(422, {
      error: {
        code: "ALREADY_GUESSED",
        message: "x",
        details: [],
        request_id: null,
      },
    });
    expect(err.code).toBe("ALREADY_GUESSED");
    expect(err.status).toBe(422);
  });
});
```

- [ ] **Step 4: Run vitest**

```bash
cd frontend && pnpm test:run
```

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/types.ts frontend/src/api/
git commit -m "feat(frontend): add DTO types + fetch client (ApiError, credentials include, 404→null)"
```

---

## Task 16: Component — `HangmanFigure` (TDD: test first)

**Files:**

- Create: `frontend/src/components/HangmanFigure.test.tsx` (FIRST)
- Create: `frontend/src/components/HangmanFigure.tsx` (SECOND)

- [ ] **Step 1: Write the failing test (RED)**

```tsx
import { render, screen } from "@testing-library/react";
import { HangmanFigure } from "./HangmanFigure";

describe("HangmanFigure", () => {
  it("renders stage 0 as empty gallows", () => {
    render(<HangmanFigure stage={0} />);
    const pre = screen.getByTestId("hangman-figure");
    expect(pre.textContent).toContain("+---+");
    expect(pre.textContent).not.toContain("O");
  });

  it("renders stage 1 with head", () => {
    render(<HangmanFigure stage={1} />);
    expect(screen.getByTestId("hangman-figure").textContent).toContain("O");
  });

  it("clamps stage > 8 to 8", () => {
    const { rerender } = render(<HangmanFigure stage={100} />);
    const text8 = screen.getByTestId("hangman-figure").textContent;
    rerender(<HangmanFigure stage={8} />);
    expect(screen.getByTestId("hangman-figure").textContent).toBe(text8);
  });

  it("clamps negative stage to 0", () => {
    render(<HangmanFigure stage={-5} />);
    expect(screen.getByTestId("hangman-figure").textContent).not.toContain("O");
  });
});
```

- [ ] **Step 2: Run test to confirm RED**

```bash
cd frontend && pnpm test:run src/components/HangmanFigure
```

Expected: test file fails with "Cannot find module './HangmanFigure'".

- [ ] **Step 3: Write the component (GREEN)**

```tsx
const STAGES: readonly string[] = [
  // Stage 0 — empty gallows
  `  +---+
  |   |
      |
      |
      |
      |
========`,
  // Stage 1 — head
  `  +---+
  |   |
  O   |
      |
      |
      |
========`,
  // Stage 2 — torso
  `  +---+
  |   |
  O   |
  |   |
      |
      |
========`,
  // Stage 3 — one arm
  `  +---+
  |   |
  O   |
 /|   |
      |
      |
========`,
  // Stage 4 — both arms
  `  +---+
  |   |
  O   |
 /|\\  |
      |
      |
========`,
  // Stage 5 — one leg
  `  +---+
  |   |
  O   |
 /|\\  |
 /    |
      |
========`,
  // Stage 6 — both legs
  `  +---+
  |   |
  O   |
 /|\\  |
 / \\  |
      |
========`,
  // Stage 7 — face expression
  `  +---+
  |   |
  X   |
 /|\\  |
 / \\  |
      |
========`,
  // Stage 8 — fully hanged + 'rope' strain
  `  +---+
  |   |
  X   |
 /|\\  |
 / \\  |
   .  |
========`,
];

interface HangmanFigureProps {
  stage: number;
}

export function HangmanFigure({ stage }: HangmanFigureProps) {
  const clamped = Math.max(0, Math.min(stage, STAGES.length - 1));
  return (
    <pre
      data-testid="hangman-figure"
      aria-label={`Hangman figure, stage ${clamped} of 8`}
    >
      {STAGES[clamped]}
    </pre>
  );
}
```

- [ ] **Step 4: Run tests — confirm GREEN**

```bash
cd frontend && pnpm test:run src/components/HangmanFigure
```

Expected: all 4 HangmanFigure tests pass.

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/components/HangmanFigure.tsx frontend/src/components/HangmanFigure.test.tsx
git commit -m "feat(frontend): add HangmanFigure component with 9 ASCII stages + tests"
```

---

## Task 17: Component — `Keyboard` (TDD: test first)

**Files:**

- Create: `frontend/src/components/Keyboard.test.tsx` (FIRST)
- Create: `frontend/src/components/Keyboard.tsx` (SECOND)

- [ ] **Step 1: Write the failing test (RED)**

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Keyboard } from "./Keyboard";

describe("Keyboard", () => {
  it("renders 26 buttons a-z", () => {
    render(<Keyboard guessedLetters="" disabled={false} onGuess={() => {}} />);
    for (const ch of "abcdefghijklmnopqrstuvwxyz") {
      expect(screen.getByTestId(`keyboard-letter-${ch}`)).toBeInTheDocument();
    }
  });

  it("disables guessed letters", () => {
    render(
      <Keyboard guessedLetters="ael" disabled={false} onGuess={() => {}} />,
    );
    expect(screen.getByTestId("keyboard-letter-a")).toBeDisabled();
    expect(screen.getByTestId("keyboard-letter-e")).toBeDisabled();
    expect(screen.getByTestId("keyboard-letter-l")).toBeDisabled();
    expect(screen.getByTestId("keyboard-letter-z")).not.toBeDisabled();
  });

  it("disables all when `disabled` prop is true", () => {
    render(<Keyboard guessedLetters="" disabled onGuess={() => {}} />);
    expect(screen.getByTestId("keyboard-letter-a")).toBeDisabled();
  });

  it("calls onGuess with the clicked letter", async () => {
    const user = userEvent.setup();
    const spy = vi.fn();
    render(<Keyboard guessedLetters="" disabled={false} onGuess={spy} />);
    await user.click(screen.getByTestId("keyboard-letter-h"));
    expect(spy).toHaveBeenCalledWith("h");
  });
});
```

- [ ] **Step 2: Run test — confirm RED**

```bash
cd frontend && pnpm test:run src/components/Keyboard
```

Expected: test file fails with "Cannot find module './Keyboard'".

- [ ] **Step 3: Write the component (GREEN)**

```tsx
interface KeyboardProps {
  guessedLetters: string;
  disabled: boolean;
  onGuess: (letter: string) => void;
}

const LETTERS = "abcdefghijklmnopqrstuvwxyz".split("");

export function Keyboard({ guessedLetters, disabled, onGuess }: KeyboardProps) {
  return (
    <div data-testid="keyboard" role="group" aria-label="Keyboard">
      {LETTERS.map((letter) => {
        const used = guessedLetters.includes(letter);
        return (
          <button
            key={letter}
            type="button"
            data-testid={`keyboard-letter-${letter}`}
            disabled={disabled || used}
            onClick={() => onGuess(letter)}
          >
            {letter}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Run tests — confirm GREEN**

```bash
cd frontend && pnpm test:run src/components/Keyboard
```

Expected: all 4 Keyboard tests pass.

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/components/Keyboard.tsx frontend/src/components/Keyboard.test.tsx
git commit -m "feat(frontend): add Keyboard component (26 buttons a-z, disables guessed) + tests"
```

---

## Task 18: Component — `ScorePanel` (TDD: test first)

**Files:**

- Create: `frontend/src/components/ScorePanel.test.tsx` (FIRST)
- Create: `frontend/src/components/ScorePanel.tsx` (SECOND)

- [ ] **Step 1: Write the failing test (RED)**

```tsx
import { render, screen } from "@testing-library/react";
import { ScorePanel } from "./ScorePanel";

describe("ScorePanel", () => {
  it("renders zeros on null session", () => {
    render(<ScorePanel session={null} />);
    expect(screen.getByTestId("score-total").textContent).toBe("0");
    expect(screen.getByTestId("streak-current").textContent).toBe("0");
    expect(screen.getByTestId("streak-best").textContent).toBe("0");
  });

  it("renders populated session values", () => {
    render(
      <ScorePanel
        session={{ current_streak: 3, best_streak: 7, total_score: 250 }}
      />,
    );
    expect(screen.getByTestId("score-total").textContent).toBe("250");
    expect(screen.getByTestId("streak-current").textContent).toBe("3");
    expect(screen.getByTestId("streak-best").textContent).toBe("7");
  });
});
```

- [ ] **Step 2: Run test — confirm RED**

```bash
cd frontend && pnpm test:run src/components/ScorePanel
```

Expected: test file fails with "Cannot find module './ScorePanel'".

- [ ] **Step 3: Write the component (GREEN)**

```tsx
import type { SessionDTO } from "../types";

interface ScorePanelProps {
  session: SessionDTO | null;
}

export function ScorePanel({ session }: ScorePanelProps) {
  const score = session?.total_score ?? 0;
  const current = session?.current_streak ?? 0;
  const best = session?.best_streak ?? 0;
  return (
    <div data-testid="score-panel" role="region" aria-label="Score panel">
      <div>
        <label>Total Score</label>
        <span data-testid="score-total">{score}</span>
      </div>
      <div>
        <label>Current Streak</label>
        <span data-testid="streak-current">{current}</span>
      </div>
      <div>
        <label>Best Streak</label>
        <span data-testid="streak-best">{best}</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests — confirm GREEN**

```bash
cd frontend && pnpm test:run src/components/ScorePanel
```

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/components/ScorePanel.tsx frontend/src/components/ScorePanel.test.tsx
git commit -m "feat(frontend): add ScorePanel with three data-testid tiles + null-session fallback"
```

---

## Task 19: Component — `HistoryList` (TDD: test first)

**Files:**

- Create: `frontend/src/components/HistoryList.test.tsx` (FIRST)
- Create: `frontend/src/components/HistoryList.tsx` (SECOND)

- [ ] **Step 1: Write the failing test (RED)**

```tsx
import { render, screen } from "@testing-library/react";
import { HistoryList } from "./HistoryList";
import type { GameDTO } from "../types";

function g(overrides: Partial<GameDTO> = {}): GameDTO {
  return {
    id: 1,
    category: "animals",
    difficulty: "easy",
    wrong_guesses_allowed: 8,
    wrong_guesses: 2,
    guessed_letters: "act",
    state: "WON",
    score: 65,
    started_at: "2026-04-22T00:00:00Z",
    finished_at: "2026-04-22T00:02:00Z",
    masked_word: "cat",
    lives_remaining: 6,
    word: "cat",
    ...overrides,
  };
}

describe("HistoryList", () => {
  it("shows empty state when no games", () => {
    render(<HistoryList games={[]} />);
    expect(screen.getByTestId("history-empty")).toHaveTextContent(/no games/i);
  });

  it("renders each game with an id-keyed testid", () => {
    render(<HistoryList games={[g({ id: 42 }), g({ id: 7 })]} />);
    expect(screen.getByTestId("history-item-42")).toBeInTheDocument();
    expect(screen.getByTestId("history-item-7")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test — confirm RED**

```bash
cd frontend && pnpm test:run src/components/HistoryList
```

- [ ] **Step 3: Write the component (GREEN)**

```tsx
import type { GameDTO } from "../types";

interface HistoryListProps {
  games: GameDTO[];
}

export function HistoryList({ games }: HistoryListProps) {
  if (games.length === 0) {
    return (
      <div data-testid="history-empty" role="region" aria-label="Game history">
        No games played yet.
      </div>
    );
  }
  return (
    <ol data-testid="history-list" aria-label="Game history">
      {games.map((g) => (
        <li key={g.id} data-testid={`history-item-${g.id}`}>
          <span>{g.category}</span>
          <span>{g.difficulty}</span>
          <span>{g.word ?? "—"}</span>
          <span>{g.state}</span>
          <span>{g.score}</span>
          <time>{g.finished_at ?? ""}</time>
        </li>
      ))}
    </ol>
  );
}
```

- [ ] **Step 4: Run tests — confirm GREEN**

```bash
cd frontend && pnpm test:run src/components/HistoryList
```

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/components/HistoryList.tsx frontend/src/components/HistoryList.test.tsx
git commit -m "feat(frontend): add HistoryList with per-item data-testid + empty state"
```

---

## Task 20: Component — `CategoryPicker` (TDD: test first)

**Files:**

- Create: `frontend/src/components/CategoryPicker.test.tsx` (FIRST)
- Create: `frontend/src/components/CategoryPicker.tsx` (SECOND)

- [ ] **Step 1: Write the failing test (RED)**

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CategoryPicker } from "./CategoryPicker";
import type { DifficultyOption } from "../types";

const DIFFS: DifficultyOption[] = [
  { id: "easy", label: "Easy", wrong_guesses_allowed: 8 },
  { id: "medium", label: "Medium", wrong_guesses_allowed: 6 },
  { id: "hard", label: "Hard", wrong_guesses_allowed: 4 },
];

describe("CategoryPicker", () => {
  it("renders categories and difficulties", () => {
    render(
      <CategoryPicker
        categories={["animals", "food"]}
        difficulties={DIFFS}
        disabled={false}
        onStartGame={() => {}}
      />,
    );
    expect(screen.getByTestId("category-select")).toHaveValue("animals");
    expect(screen.getByTestId("difficulty-easy")).toBeChecked();
  });

  it("start-game-btn disabled while loading", () => {
    render(
      <CategoryPicker
        categories={["animals"]}
        difficulties={DIFFS}
        disabled
        onStartGame={() => {}}
      />,
    );
    expect(screen.getByTestId("start-game-btn")).toBeDisabled();
  });

  it("calls onStartGame with selected values", async () => {
    const user = userEvent.setup();
    const spy = vi.fn();
    render(
      <CategoryPicker
        categories={["animals", "food"]}
        difficulties={DIFFS}
        disabled={false}
        onStartGame={spy}
      />,
    );
    await user.selectOptions(screen.getByTestId("category-select"), "food");
    await user.click(screen.getByTestId("difficulty-hard"));
    await user.click(screen.getByTestId("start-game-btn"));
    expect(spy).toHaveBeenCalledWith("food", "hard");
  });
});
```

- [ ] **Step 2: Run test — confirm RED**

```bash
cd frontend && pnpm test:run src/components/CategoryPicker
```

- [ ] **Step 3: Write the component (GREEN)**

```tsx
import { useState } from "react";
import type { Difficulty, DifficultyOption } from "../types";

interface CategoryPickerProps {
  categories: string[];
  difficulties: DifficultyOption[];
  disabled: boolean;
  onStartGame: (category: string, difficulty: Difficulty) => void;
}

export function CategoryPicker({
  categories,
  difficulties,
  disabled,
  onStartGame,
}: CategoryPickerProps) {
  const [category, setCategory] = useState<string>(categories[0] ?? "");
  const [difficulty, setDifficulty] = useState<Difficulty>(
    (difficulties[0]?.id ?? "easy") as Difficulty,
  );

  // Keep selections valid if props change.
  if (categories.length > 0 && !categories.includes(category)) {
    setCategory(categories[0]);
  }

  return (
    <div
      data-testid="category-picker"
      role="region"
      aria-label="Category picker"
    >
      <label>
        Category
        <select
          data-testid="category-select"
          value={category}
          disabled={disabled || categories.length === 0}
          onChange={(e) => setCategory(e.target.value)}
        >
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>
      <fieldset>
        <legend>Difficulty</legend>
        {difficulties.map((d) => (
          <label key={d.id}>
            <input
              type="radio"
              data-testid={`difficulty-${d.id}`}
              name="difficulty"
              value={d.id}
              checked={difficulty === d.id}
              disabled={disabled}
              onChange={() => setDifficulty(d.id)}
            />
            {d.label} ({d.wrong_guesses_allowed} lives)
          </label>
        ))}
      </fieldset>
      <button
        type="button"
        data-testid="start-game-btn"
        disabled={disabled || !category}
        onClick={() => onStartGame(category, difficulty)}
      >
        Start New Game
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Run tests — confirm GREEN**

```bash
cd frontend && pnpm test:run src/components/CategoryPicker
```

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/components/CategoryPicker.tsx frontend/src/components/CategoryPicker.test.tsx
git commit -m "feat(frontend): add CategoryPicker with category select + difficulty radios + start button"
```

---

## Task 21: Component — `GameBoard` (TDD: test first)

**Files:**

- Create: `frontend/src/components/GameBoard.test.tsx` (FIRST)
- Create: `frontend/src/components/GameBoard.tsx` (SECOND)

- [ ] **Step 1: Write the failing test (RED)**

```tsx
import { render, screen } from "@testing-library/react";
import { GameBoard } from "./GameBoard";
import type { GameDTO } from "../types";

function g(overrides: Partial<GameDTO> = {}): GameDTO {
  return {
    id: 1,
    category: "animals",
    difficulty: "easy",
    wrong_guesses_allowed: 8,
    wrong_guesses: 0,
    guessed_letters: "",
    state: "IN_PROGRESS",
    score: 0,
    started_at: "2026-04-22T00:00:00Z",
    finished_at: null,
    masked_word: "___",
    lives_remaining: 8,
    // `word` is OPTIONAL in the DTO; absent during IN_PROGRESS.
    // Override to `{ state: "WON", word: "cat", masked_word: "cat" }` for terminal tests.
    ...overrides,
  };
}

describe("GameBoard", () => {
  it("shows empty state when game is null", () => {
    render(<GameBoard game={null} />);
    expect(screen.getByTestId("game-board-empty")).toHaveTextContent(
      /pick a category/i,
    );
  });

  it("shows masked word + hangman figure + lives during IN_PROGRESS", () => {
    render(<GameBoard game={g()} />);
    expect(screen.getByTestId("hangman-figure")).toBeInTheDocument();
    expect(screen.getByTestId("masked-word").textContent).toBe("_ _ _");
    expect(screen.getByTestId("lives-remaining").textContent).toContain("8");
  });

  it("shows win banner on WON", () => {
    render(
      <GameBoard game={g({ state: "WON", word: "cat", masked_word: "cat" })} />,
    );
    expect(screen.getByTestId("game-won")).toHaveTextContent(/cat/i);
  });

  it("shows loss banner on LOST", () => {
    render(<GameBoard game={g({ state: "LOST", word: "cat" })} />);
    expect(screen.getByTestId("game-lost")).toHaveTextContent(/cat/i);
  });
});
```

- [ ] **Step 2: Run test — confirm RED**

```bash
cd frontend && pnpm test:run src/components/GameBoard
```

- [ ] **Step 3: Write the component (GREEN)**

```tsx
import { HangmanFigure } from "./HangmanFigure";
import type { GameDTO } from "../types";

interface GameBoardProps {
  game: GameDTO | null;
}

const MAX_STAGE = 8;

function computeStage(g: GameDTO): number {
  const start = MAX_STAGE - g.wrong_guesses_allowed;
  return start + g.wrong_guesses;
}

export function GameBoard({ game }: GameBoardProps) {
  if (game === null) {
    return (
      <div data-testid="game-board-empty" role="region" aria-label="Game board">
        Pick a category to start.
      </div>
    );
  }
  const stage = computeStage(game);
  return (
    <div data-testid="game-board" role="region" aria-label="Game board">
      <HangmanFigure stage={stage} />
      <div
        data-testid="masked-word"
        style={{ letterSpacing: "0.5em", fontSize: "1.5em" }}
      >
        {game.masked_word.split("").join(" ")}
      </div>
      <div data-testid="lives-remaining">Lives: {game.lives_remaining}</div>
      {game.state === "WON" && (
        <div data-testid="game-won">You won! The word was: {game.word}</div>
      )}
      {game.state === "LOST" && (
        <div data-testid="game-lost">You lost. The word was: {game.word}</div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests — confirm GREEN**

```bash
cd frontend && pnpm test:run src/components/GameBoard
```

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/components/GameBoard.tsx frontend/src/components/GameBoard.test.tsx
git commit -m "feat(frontend): add GameBoard (masked word, figure, lives, terminal banners)"
```

---

## Task 22: `App.tsx` + `main.tsx` + styles

**Files:**

- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/index.css` (rename as `styles.css` per spec — keep existing path to minimize Vite template impact)

- [ ] **Step 1: Overwrite `frontend/src/App.tsx`**

```tsx
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "./api/client";
import { CategoryPicker } from "./components/CategoryPicker";
import { GameBoard } from "./components/GameBoard";
import { HistoryList } from "./components/HistoryList";
import { Keyboard } from "./components/Keyboard";
import { ScorePanel } from "./components/ScorePanel";
import type {
  CategoriesDTO,
  Difficulty,
  DifficultyOption,
  GameDTO,
  SessionDTO,
} from "./types";

function humanError(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return "Unknown error";
}

export default function App() {
  const [categories, setCategories] = useState<string[]>([]);
  const [difficulties, setDifficulties] = useState<DifficultyOption[]>([]);
  const [session, setSession] = useState<SessionDTO | null>(null);
  const [currentGame, setCurrentGame] = useState<GameDTO | null>(null);
  const [history, setHistory] = useState<GameDTO[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refreshSessionAndHistory = useCallback(async () => {
    const [s, h] = await Promise.all([api.getSession(), api.getHistory()]);
    setSession(s);
    setHistory(h.items);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [cats, sess, cur, hist]: [
          CategoriesDTO,
          SessionDTO,
          GameDTO | null,
          { items: GameDTO[] },
        ] = await Promise.all([
          api.getCategories(),
          api.getSession(),
          api.getCurrentGame(),
          api.getHistory(),
        ]);
        if (cancelled) return;
        setCategories(cats.categories);
        setDifficulties(cats.difficulties);
        setSession(sess);
        setCurrentGame(cur);
        setHistory(hist.items);
      } catch (e) {
        if (!cancelled) setError(humanError(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const onStartGame = useCallback(
    async (category: string, difficulty: Difficulty) => {
      if (currentGame !== null) {
        const ok = window.confirm(
          "You have an active game. Starting a new one will forfeit it. Continue?",
        );
        if (!ok) return;
      }
      setLoading(true);
      setError(null);
      try {
        const created = await api.startGame({ category, difficulty });
        setCurrentGame(created);
        await refreshSessionAndHistory();
      } catch (e) {
        setError(humanError(e));
      } finally {
        setLoading(false);
      }
    },
    [currentGame, refreshSessionAndHistory],
  );

  const onGuess = useCallback(
    async (letter: string) => {
      if (currentGame === null) return;
      setError(null);
      try {
        const updated = await api.guess(currentGame.id, letter);
        setCurrentGame(updated);
        if (updated.state !== "IN_PROGRESS") {
          await refreshSessionAndHistory();
        }
      } catch (e) {
        setError(humanError(e));
      }
    },
    [currentGame, refreshSessionAndHistory],
  );

  const dismissError = useCallback(() => setError(null), []);

  return (
    <div className="app" data-testid="app">
      {error && (
        <div role="alert" data-testid="error-banner">
          <span>{error}</span>
          <button type="button" onClick={dismissError}>
            dismiss
          </button>
        </div>
      )}
      <ScorePanel session={session} />
      <CategoryPicker
        categories={categories}
        difficulties={difficulties}
        disabled={loading}
        onStartGame={onStartGame}
      />
      <GameBoard game={currentGame} />
      <Keyboard
        guessedLetters={currentGame?.guessed_letters ?? ""}
        disabled={
          loading || currentGame === null || currentGame.state !== "IN_PROGRESS"
        }
        onGuess={onGuess}
      />
      <HistoryList games={history} />
    </div>
  );
}
```

- [ ] **Step 2: Overwrite `frontend/src/main.tsx`**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 3: Overwrite `frontend/src/index.css`**

```css
:root {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  line-height: 1.5;
  color-scheme: light dark;
  color: #222;
  background-color: #f7f7f7;
}

* {
  box-sizing: border-box;
}

body,
#root {
  margin: 0;
  min-height: 100vh;
}

.app {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

[data-testid="error-banner"] {
  background: #ffdddd;
  border: 1px solid #c33;
  padding: 0.5rem 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

[data-testid="score-panel"] {
  display: flex;
  gap: 1.5rem;
  padding: 1rem;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 4px;
}

[data-testid="score-panel"] > div {
  display: flex;
  flex-direction: column;
}

[data-testid="category-picker"] {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 4px;
}

[data-testid="game-board"],
[data-testid="game-board-empty"] {
  padding: 1rem;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 4px;
  text-align: center;
}

[data-testid="keyboard"] {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  justify-content: center;
}

[data-testid="keyboard"] button {
  min-width: 2.5rem;
  padding: 0.5rem;
  font-family: inherit;
  font-size: 1rem;
  cursor: pointer;
}

[data-testid="keyboard"] button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

[data-testid="history-list"] {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

[data-testid="history-list"] li {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 0.5rem;
  padding: 0.5rem;
  background: #fff;
  border: 1px solid #eee;
  border-radius: 4px;
  font-size: 0.9rem;
}

pre[data-testid="hangman-figure"] {
  font-family: ui-monospace, monospace;
  font-size: 1rem;
  line-height: 1.1;
  margin: 0.5rem 0;
}
```

- [ ] **Step 4: Verify build + typecheck + lint**

```bash
cd frontend && pnpm tsc --noEmit -p tsconfig.app.json
cd frontend && pnpm lint
cd frontend && pnpm build
```

All must succeed.

- [ ] **Step 5: Verify unit tests still pass**

```bash
cd frontend && pnpm test:run
```

- [ ] **Step 6: Commit**

```bash
cd .. && git add frontend/src/App.tsx frontend/src/main.tsx frontend/src/index.css
git commit -m "feat(frontend): wire App.tsx (state + effects + handlers) + plain-CSS layout"
```

---

## Task 23: Playwright install + config + auth fixture stub

**Files:**

- Modify: `frontend/package.json` (Playwright already in devDependencies from Task 11)
- Create: `frontend/playwright.config.ts`
- Create: `frontend/tests/e2e/fixtures/auth.ts`
- Create: `frontend/tests/e2e/specs/.gitkeep`
- Create: `frontend/tests/e2e/use-cases/.gitkeep`
- Create: `.claude/playwright-dir` (marker file for setup scripts)

- [ ] **Step 1: Install Playwright browsers**

```bash
cd frontend && pnpm exec playwright install chromium
```

Expected: downloads ~170 MB, installs to pnpm's Playwright cache.

- [ ] **Step 2: Write `frontend/playwright.config.ts`**

```ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e/specs",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "cd ../backend && uv run uvicorn hangman.main:app --port 8000",
      url: "http://localhost:8000/api/v1/categories",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "pnpm dev",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
```

- [ ] **Step 3: Write `frontend/tests/e2e/fixtures/auth.ts`**

```ts
// The hangman scaffold has no authentication. This fixture is a no-op pass-through.
// rules/testing.md references this file; keeping it as the standard extension point
// so future auth-bearing specs don't need to restructure imports.
import { test as base, expect } from "@playwright/test";

export const test = base;
export { expect };
```

- [ ] **Step 4: Create empty placeholder dirs**

```bash
mkdir -p frontend/tests/e2e/specs frontend/tests/e2e/use-cases
touch frontend/tests/e2e/specs/.gitkeep frontend/tests/e2e/use-cases/.gitkeep
```

- [ ] **Step 5: Write `.claude/playwright-dir`**

```bash
echo 'frontend' > .claude/playwright-dir
```

- [ ] **Step 6: Verify Playwright picks up config (no specs yet, should exit cleanly)**

```bash
cd frontend && pnpm exec playwright test --list
```

Expected: "No tests found" or "Total: 0 tests in 0 files." — no errors.

- [ ] **Step 7: Commit**

```bash
cd .. && git add frontend/playwright.config.ts frontend/tests/e2e/ .claude/playwright-dir
git commit -m "feat(e2e): install Playwright framework (chromium, webServer array) + auth fixture stub"
```

---

## Task 24: Backend-to-frontend E2E validation script (manual verify)

**Files:** None created — this task is a checkpoint step.

- [ ] **Step 1: Start backend in one terminal**

```bash
make backend
```

- [ ] **Step 2: Start frontend in another terminal**

```bash
make frontend
```

- [ ] **Step 3: Hit the API directly to prove the backend is up**

```bash
curl -sS -i http://localhost:8000/api/v1/categories
```

Expected: 200 + JSON body with 3 categories and 3 difficulties + a `set-cookie: session_id=...; HttpOnly; SameSite=lax; Max-Age=2592000; Path=/` header.

- [ ] **Step 4: Open the frontend in a browser**

Navigate to `http://localhost:3000`. Verify:

- ScorePanel shows `0 / 0 / 0`.
- CategoryPicker shows 3 options + 3 difficulty radios + Start button.
- GameBoard shows "Pick a category to start."
- Keyboard is rendered but all letters disabled.
- HistoryList shows "No games played yet."
- No errors in browser console.

- [ ] **Step 5: Play a round manually**

Pick "animals" + "easy". Click Start. Guess letters. Observe:

- Masked word updates, keyboard letters disable, hangman figure advances on wrong guesses, score/streak update after WON/LOST, history grows.
- Reload. State persists (current game resumes; history remains; score remains).

- [ ] **Step 6: Stop servers; do NOT commit yet**

This is a checkpoint, not a code change. Proceed to Task 24a if the manual walkthrough is green. If broken, fix in-place (per NO BUGS LEFT BEHIND) by jumping back to the relevant prior task.

---

## Task 24a: Run verify-e2e + persist E2E report (Phase 5.4 bridge)

This task exists so the plan produces the artifacts the `/new-feature` Phase 5.4 evidence gate expects: a markdown report under `tests/e2e/reports/` whose mtime is later than the branch-off commit. Without it, the Stop hook would block `gh pr create` even after everything else passes.

**Files:**

- Create: `tests/e2e/reports/` (directory, at repo root — NOT inside `frontend/`)
- Create: `tests/e2e/reports/2026-04-22-hangman-scaffold-feature.md` (agent-written report)

- [ ] **Step 1: Ensure backend + frontend dev servers are running from this worktree**

If Task 24 was just completed, both servers are already up. If not:

```bash
make backend   # terminal A
make frontend  # terminal B
```

- [ ] **Step 2: Create the reports directory**

```bash
mkdir -p tests/e2e/reports
```

- [ ] **Step 3: Dispatch the verify-e2e subagent**

Via the Task tool (the main agent, NOT this subagent, invokes it):

```
Task tool → subagent_type: "verify-e2e", prompt: "Mode: feature. Plan file: docs/plans/2026-04-22-hangman-scaffold-plan.md. Project type: fullstack. Execute all 4 E2E use cases (UC1, UC2, UC3, UC4) defined in the plan file's '## E2E Use Cases' section and return a verification report."
```

- [ ] **Step 4: Persist the agent's report**

The agent's response begins with a header:

```
VERDICT: PASS | FAIL | PARTIAL
SUGGESTED_PATH: tests/e2e/reports/2026-04-22-hangman-scaffold-feature.md
---
<markdown body>
```

Parse the header, then `Write` the body (everything after `---`) to the suggested path.

- [ ] **Step 5: Act on the verdict**

- **PASS** → proceed to Task 24b.
- **FAIL** → at least one UC was classified `FAIL_BUG`. Fix the bug in code, re-dispatch verify-e2e. Do NOT proceed until PASS. (NO BUGS LEFT BEHIND applies here specifically.)
- **PARTIAL** → no `FAIL_BUG`, but `FAIL_STALE` or `FAIL_INFRA`:
  - `FAIL_STALE`: update the stale UC in this plan file + re-run.
  - `FAIL_INFRA`: retry once; if still infra, surface to user.

- [ ] **Step 6: Commit the report**

```bash
git add tests/e2e/reports/
git commit -m "test(e2e): persist verify-e2e report for hangman-scaffold feature"
```

---

## Task 24b: Graduate use cases + write Playwright smoke spec (Phase 6.2b + 6.2c bridge)

**Files:**

- Create: `frontend/tests/e2e/use-cases/hangman-scaffold.md` (graduated UCs — permanent regression)
- Create: `frontend/tests/e2e/specs/play-round.spec.ts` (deterministic smoke spec tagged `@smoke`)
- Modify: `frontend/tests/e2e/specs/.gitkeep` (delete once a real spec exists)
- Modify: `frontend/tests/e2e/use-cases/.gitkeep` (delete once a real UC file exists)

- [ ] **Step 1: Graduate use cases to `frontend/tests/e2e/use-cases/hangman-scaffold.md`**

Copy the entire `## E2E Use Cases (Phase 3.2b)` section from this plan file into `frontend/tests/e2e/use-cases/hangman-scaffold.md` verbatim (headings + bodies). This becomes the permanent regression suite.

```bash
# From the worktree root:
rm frontend/tests/e2e/use-cases/.gitkeep
```

Then `Write` the UC file with the graduated content. (The main agent performs this Write; content is a copy-paste from the plan's UC section with one preamble: "# E2E Use Cases — hangman-scaffold (graduated 2026-04-22 from docs/plans/2026-04-22-hangman-scaffold-plan.md)".)

- [ ] **Step 2: Write `frontend/tests/e2e/specs/play-round.spec.ts` (smoke — wiring-only, NOT deterministic-score)**

**Design rationale:** the Playwright `webServer` array boots the real dev backend, which loads `backend/words.txt` — a pool whose random word choice is non-deterministic. The smoke spec therefore validates **end-to-end wiring only** (start-game flow, keyboard interaction, masked-word visibility, terminal transition reachable within N guesses), not exact score or the terminal word. Deterministic scoring math is covered by backend integration tests (`tests/integration/test_guesses.py`) using the in-memory `test_word_pool`.

```ts
import { test, expect } from "../fixtures/auth";

test.describe("Hangman scaffold — end-to-end wiring", () => {
  test("UC1 smoke: start game, play, reach terminal state @smoke", async ({
    page,
  }) => {
    await page.goto("/");

    // Initial state: score zeros, no active game, empty history.
    await expect(page.getByTestId("score-panel")).toBeVisible();
    await expect(page.getByTestId("score-total")).toHaveText("0");
    await expect(page.getByTestId("game-board-empty")).toBeVisible();

    // Start a game via the UI (defaults: first category, easy difficulty).
    await page.getByTestId("start-game-btn").click();

    // Active game visible.
    await expect(page.getByTestId("game-board")).toBeVisible();
    await expect(page.getByTestId("hangman-figure")).toBeVisible();
    await expect(page.getByTestId("masked-word")).toBeVisible();
    await expect(page.getByTestId("lives-remaining")).toContainText("8");

    // Click a sequence of high-coverage letters. For any seed word (cat, dog,
    // elephant, giraffe, …), these 15 letters reliably force a terminal state
    // within the 8 wrong-guesses allowed.
    const letters = [
      "e",
      "a",
      "o",
      "i",
      "u",
      "t",
      "n",
      "r",
      "s",
      "l",
      "c",
      "d",
      "h",
      "p",
      "m",
    ];
    for (const letter of letters) {
      const btn = page.getByTestId(`keyboard-letter-${letter}`);
      if (await btn.isDisabled()) continue;
      await btn.click();
      // Bail as soon as terminal state is reached.
      if (
        (await page.getByTestId("game-won").count()) > 0 ||
        (await page.getByTestId("game-lost").count()) > 0
      ) {
        break;
      }
    }

    // Exactly one terminal banner must be visible.
    const wonCount = await page.getByTestId("game-won").count();
    const lostCount = await page.getByTestId("game-lost").count();
    expect(wonCount + lostCount).toBe(1);

    // History grew by 1.
    const historyItems = page.locator("[data-testid^='history-item-']");
    await expect(historyItems).toHaveCount(1);

    // Persistence: reload and confirm history + active terminal state survive.
    await page.reload();
    await expect(page.locator("[data-testid^='history-item-']")).toHaveCount(1);
  });
});
```

**Properties:**

- **Robust** — works against the production word pool (animals + food + tech), no fixture leakage required.
- **Wiring-focused** — asserts the full UI flow wires correctly: mount → start → keyboard → terminal → history → persist. Does NOT assert an exact score (integration tests own that).
- **Self-bounding** — 15-letter sequence + early-exit keeps the spec under ~5 seconds locally.

If a future feature adds an env-flag-gated deterministic backend word pool (e.g. `HANGMAN_WORDS_FILE=words.test.txt`), this spec can be rewritten for exact score + streak assertions.

- [ ] **Step 3: Remove the `.gitkeep` placeholders**

```bash
rm -f frontend/tests/e2e/specs/.gitkeep frontend/tests/e2e/use-cases/.gitkeep
```

- [ ] **Step 4: Run the smoke spec locally to confirm green**

```bash
cd frontend && pnpm exec playwright test --grep @smoke
```

Expected: 1 test passes. If it fails, fix the selector / backend state issue before committing (NO BUGS LEFT BEHIND — do not commit a broken spec).

- [ ] **Step 5: Commit**

```bash
git add frontend/tests/e2e/specs/play-round.spec.ts frontend/tests/e2e/use-cases/hangman-scaffold.md
git rm frontend/tests/e2e/specs/.gitkeep frontend/tests/e2e/use-cases/.gitkeep 2>/dev/null || true
git commit -m "test(e2e): graduate use cases + add Playwright smoke spec for hangman-scaffold"
```

---

## Task 25: Finalize Makefile + root README

**Files:**

- Modify: `Makefile` (no change from Task 1; verify targets still work)
- Create: `README.md`

- [ ] **Step 1: Write root `README.md`**

````markdown
# Hangman

Local HTTP hangman game with category picker, score, streak tracking, difficulty levels, and per-session game history.

**Tech:** FastAPI + SQLite + Pydantic v2 backend, React 19 + Vite 8 + TypeScript frontend, Playwright for E2E.

## Prerequisites

- Python 3.12+
- Node 22+
- pnpm 10+
- uv (https://docs.astral.sh/uv/)

## Setup

```bash
make install
```
````

Installs backend (via `uv sync`) + frontend (via `pnpm install`) + Playwright chromium.

## Run

Open two terminals:

**Terminal A — backend (http://localhost:8000):**

```bash
make backend
```

**Terminal B — frontend (http://localhost:3000):**

```bash
make frontend
```

Open http://localhost:3000 in a browser to play.

## Test

```bash
make test        # unit + integration on both backend + frontend
make lint        # ruff + eslint
make typecheck   # mypy + tsc
make verify      # lint + typecheck + test
```

End-to-end (Playwright):

```bash
cd frontend && pnpm exec playwright test
```

## Layout

See `docs/plans/2026-04-22-hangman-scaffold-design.md` for the full architectural design.

````

- [ ] **Step 2: Verify `make verify` passes**

```bash
make verify
````

If anything fails, fix at source. Do not skip.

- [ ] **Step 3: Commit**

```bash
git add README.md Makefile
git commit -m "docs: add root README with setup + run + test instructions"
```

---

## E2E Use Cases (Phase 3.2b)

These use cases belong in this plan file during execution. After Phase 5.4 passes, they graduate to `tests/e2e/use-cases/` (Phase 6.2b) and a `.spec.ts` (Phase 6.2c).

All use cases run against the Hangman fullstack app: API on :8000, UI on :3000 via Playwright MCP (for UI steps) + direct HTTP (for API steps).

### UC1 — Happy path: play a round end-to-end and persist (@smoke, covers US-001 + US-002 + US-004)

**Interface:** API + UI (API-first per `rules/testing.md`)

**Intent:** A fresh local player picks a category and difficulty, plays a round through to completion, and sees score + streak + history update. Reloading the page preserves state.

**Setup:** None (fresh session).

**Steps (API phase):**

1. `GET /api/v1/categories` — expect 200 + 3 categories (animals, food, tech) + 3 difficulties (easy/8, medium/6, hard/4). Capture `Set-Cookie` header; re-use cookie on all subsequent calls.
2. `GET /api/v1/session` — expect 200 + `{current_streak: 0, best_streak: 0, total_score: 0}`.
3. `GET /api/v1/games/current` — expect 404 `NO_ACTIVE_GAME`.
4. `POST /api/v1/games` with `{category: "animals", difficulty: "easy"}` — expect 201 + `Location: /api/v1/games/<id>` + game DTO with `masked_word` all underscores, `lives_remaining: 8`, `forfeited_game_id: null`, and **`word` key ABSENT** (PRD US-001 requires omission, not null).
5. Guess every letter a–z via `POST /api/v1/games/{id}/guesses` until state is WON or LOST. At each step assert 200 and state transitions match (IN_PROGRESS → WON or LOST on final guess).
6. `GET /api/v1/session` — if WON: `current_streak == 1`, `best_streak >= 1`, `total_score > 0`. If LOST: all zeros.
7. `GET /api/v1/history` — expect `items.length == 1`, item's `state` matches prior.

**Steps (UI phase):**

8. Navigate to `http://localhost:3000`.
9. Verify `ScorePanel` shows the same numbers as step 6.
10. Verify `HistoryList` shows the one played game with category, difficulty, word (revealed), and score.
11. Verify `GameBoard` shows the terminal banner (`data-testid="game-won"` with revealed word for a WON game, or `data-testid="game-lost"` for a LOST game). The terminal game remains in `currentGame` until the user starts a new one — the banner is the "what just happened" affordance, not an empty state. (`GameBoard` only shows "Pick a category to start." when there has never been a game this session.)
12. Reload the page (Ctrl+R). Verify the ScorePanel + HistoryList still show the same values (session cookie persisted).

**Verification (ARRANGE/VERIFY boundary):** API assertions via HTTP status + JSON body. UI assertions via `data-testid` selectors (`score-total`, `streak-current`, `streak-best`, `history-item-<id>`). No direct DB reads.

**Persistence:** Step 12 reload is the persistence check.

### UC2 — Loss resets streak to 0 (covers US-002 loss behavior)

**Interface:** API + UI

**Intent:** A player on a win streak loses a round; `current_streak` resets to 0, `best_streak` is unchanged, the game appears in history as LOST with score 0.

**Setup:**

1. Via `POST /api/v1/games` + sequential correct-letter guesses, achieve at least one WON game so `current_streak >= 1` and `best_streak >= 1`.

**Steps:**

2. `POST /api/v1/games` with a new category — should not forfeit because the prior is already WON.
3. Intentionally guess wrong letters (use letters not in common English: `q`, `x`, `z`, then continue with rarely-used letters) until `state == LOST`.
4. `GET /api/v1/session` — assert `current_streak == 0`, `best_streak` unchanged from pre-loss value.
5. `GET /api/v1/history` — assert the LOST game exists, `score == 0`.

**UI verification:**

6. Reload `http://localhost:3000`. `streak-current` shows 0, `streak-best` shows the pre-loss value, `history-item-<id>` shows the LOST game.

**Persistence:** UI reload in step 6.

### UC3 — Forfeit flow (covers US-005)

**Interface:** UI (primary — tests the `window.confirm` prompt) + API (for state inspection)

**Intent:** Starting a new game while one is in progress forfeits the active one.

**Setup:**

1. Start a game via UI: pick animals/easy, click Start. Guess 1 letter to confirm it's mid-play.

**Steps:**

2. In `CategoryPicker`, change category to "food" and difficulty to "medium". Click Start.
3. Browser shows `window.confirm` prompt: "You have an active game. Starting a new one will forfeit it. Continue?"
4. Accept the prompt.
5. Observe: a new game is in the `GameBoard` (masked word all underscores, 6 lives). `ScorePanel` shows `current_streak: 0` (reset from any prior streak).
6. `HistoryList` shows the forfeited game as LOST with score 0.

**API verification** (using same session cookie as browser):

7. `GET /api/v1/history` — assert the forfeited game is present with `state == LOST`, `score == 0`.

**Persistence:** 8. Reload the page. New game state is retained (`GET /games/current` returns the new game), history shows the forfeited one.

### UC4 — Mid-game reload persists IN_PROGRESS state (covers US-004)

**Interface:** UI

**Intent:** A reload mid-game brings back the exact game state: masked word, guessed letters, lives remaining.

**Setup:**

1. Start a game via UI: animals/easy.
2. Guess 3 letters (mix correct and wrong).
3. Capture the visible `masked_word`, `guessed_letters` keyboard disabled set, `lives-remaining`.

**Steps:**

4. Reload the page.
5. Verify:
   - `masked-word` shows the exact same revealed pattern.
   - In `Keyboard`, the same 3 letter buttons are disabled.
   - `lives-remaining` shows the exact same count.

**Persistence:** The reload itself is the persistence test.

### Regression on cookie edge cases (minor, part of UC1)

Not a separate UC. Covered inside UC1 step 1's cookie attribute assertions (HttpOnly + SameSite=Lax + Max-Age=2592000).

---

## Dispatch Plan

Per `/new-feature` §4.0.

| Task ID | Depends on                 | Writes (concrete file paths)                                                                                                                                                                                                                                                                                                                                                                                          |
| ------- | -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1       | —                          | `.gitignore`, `Makefile`, creates `backend/`, `frontend/` dirs                                                                                                                                                                                                                                                                                                                                                        |
| 2       | 1                          | `backend/pyproject.toml`, `backend/uv.lock`, `backend/README.md`                                                                                                                                                                                                                                                                                                                                                      |
| 3       | 2                          | `backend/src/hangman/__init__.py`, `backend/tests/__init__.py`, `backend/tests/conftest.py`                                                                                                                                                                                                                                                                                                                           |
| 4       | 3                          | `backend/tests/unit/__init__.py`, `backend/tests/unit/test_game.py`, `backend/src/hangman/game.py`                                                                                                                                                                                                                                                                                                                    |
| 5       | 4                          | `backend/tests/unit/test_words.py`, `backend/src/hangman/words.py`, `backend/words.txt`                                                                                                                                                                                                                                                                                                                               |
| 6       | 5                          | `backend/src/hangman/models.py`, `backend/src/hangman/db.py`, `backend/tests/integration/__init__.py`, `backend/tests/integration/test_models_smoke.py`, `backend/tests/conftest.py`                                                                                                                                                                                                                                  |
| 7       | 6                          | `backend/src/hangman/schemas.py`, `backend/tests/unit/test_schemas.py`                                                                                                                                                                                                                                                                                                                                                |
| 8       | 7                          | `backend/src/hangman/errors.py`, `backend/tests/unit/test_errors.py`                                                                                                                                                                                                                                                                                                                                                  |
| 9       | 6, 8                       | `backend/src/hangman/sessions.py`, `backend/tests/integration/test_session_cookie.py`, `backend/tests/conftest.py`                                                                                                                                                                                                                                                                                                    |
| 10      | 7, 8, 9                    | `backend/src/hangman/main.py`, `backend/src/hangman/routes.py`, `backend/tests/integration/test_categories.py`, `backend/tests/integration/test_session_endpoint.py`, `backend/tests/integration/test_games_start.py`, `backend/tests/integration/test_games_forfeit.py`, `backend/tests/integration/test_guesses.py`, `backend/tests/integration/test_games_current.py`, `backend/tests/integration/test_history.py` |
| 11      | 1                          | `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx` (stub, replaced in Task 22), `frontend/src/vite-env.d.ts`, `frontend/src/index.css` (empty, populated in Task 22), `frontend/.gitignore` — all written manually in this task; no `pnpm create vite` prompt                                                                                 |
| 12      | 11                         | `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, `frontend/tsconfig.node.json`                                                                                                                                                                                                                                                                                                      |
| 13      | 11                         | `frontend/eslint.config.js`, `frontend/.prettierrc.json`, `frontend/.prettierignore`                                                                                                                                                                                                                                                                                                                                  |
| 14      | 11                         | `frontend/vitest.config.ts`, `frontend/src/test/setup.ts`                                                                                                                                                                                                                                                                                                                                                             |
| 15      | 14                         | `frontend/src/types.ts`, `frontend/src/api/client.ts`, `frontend/src/api/client.test.ts`                                                                                                                                                                                                                                                                                                                              |
| 16      | 14                         | `frontend/src/components/HangmanFigure.tsx`, `frontend/src/components/HangmanFigure.test.tsx`                                                                                                                                                                                                                                                                                                                         |
| 17      | 14                         | `frontend/src/components/Keyboard.tsx`, `frontend/src/components/Keyboard.test.tsx`                                                                                                                                                                                                                                                                                                                                   |
| 18      | 15                         | `frontend/src/components/ScorePanel.tsx`, `frontend/src/components/ScorePanel.test.tsx`                                                                                                                                                                                                                                                                                                                               |
| 19      | 15                         | `frontend/src/components/HistoryList.tsx`, `frontend/src/components/HistoryList.test.tsx`                                                                                                                                                                                                                                                                                                                             |
| 20      | 15                         | `frontend/src/components/CategoryPicker.tsx`, `frontend/src/components/CategoryPicker.test.tsx`                                                                                                                                                                                                                                                                                                                       |
| 21      | 16                         | `frontend/src/components/GameBoard.tsx`, `frontend/src/components/GameBoard.test.tsx`                                                                                                                                                                                                                                                                                                                                 |
| 22      | 15, 16, 17, 18, 19, 20, 21 | `frontend/src/App.tsx`, `frontend/src/main.tsx`, `frontend/src/index.css`                                                                                                                                                                                                                                                                                                                                             |
| 23      | 22                         | `frontend/playwright.config.ts`, `frontend/tests/e2e/fixtures/auth.ts`, `frontend/tests/e2e/specs/.gitkeep`, `frontend/tests/e2e/use-cases/.gitkeep`, `.claude/playwright-dir`                                                                                                                                                                                                                                        |
| 24      | 10, 23                     | (no writes — manual checkpoint)                                                                                                                                                                                                                                                                                                                                                                                       |
| 24a     | 24                         | `tests/e2e/reports/` (dir), `tests/e2e/reports/2026-04-22-hangman-scaffold-feature.md`                                                                                                                                                                                                                                                                                                                                |
| 24b     | 24a                        | `frontend/tests/e2e/use-cases/hangman-scaffold.md`, `frontend/tests/e2e/specs/play-round.spec.ts` (and deletes the `.gitkeep` files in both dirs)                                                                                                                                                                                                                                                                     |
| 25      | 24b                        | `README.md`                                                                                                                                                                                                                                                                                                                                                                                                           |

**Scheduling guidance:**

- Tasks 1→10 are a strict sequential chain (backend bootstrap).
- Tasks 11 (frontend scaffold) can start in parallel with Task 2 in principle, but the single-session dev flow favors serializing. The dispatch plan supports either ordering.
- Tasks 16–21 (frontend components) share no `Writes` paths and are genuinely parallelizable once Tasks 14 and 15 complete — they can run concurrently (cap of 3 per `/new-feature` §4.0).
- Task 22 (`App.tsx` assembly) depends on all 6 components.
- Task 23 requires the UI exists; Task 24 is a checkpoint.

**Sequential mode:** This plan is tightly coupled across the backend (same `conftest.py`, shared import contracts), so I recommend **serial execution through Task 10**, then optional parallelism for Tasks 16–21.

---

## Success Metrics Reprise (from PRD §2)

- [ ] 1 Playwright spec + 1 markdown use case pass (Phase 5.4 / 6.2c)
- [ ] Unit coverage on `game.py` ≥ 95%
- [ ] Every endpoint exercised by ≥ 1 integration test
- [ ] `mypy hangman/` clean; `tsc --noEmit -p tsconfig.app.json` clean
- [ ] `ruff check . && ruff format --check .` clean; ESLint + Prettier clean
- [ ] `make install && make backend` + `make frontend` both boot
- [ ] `Set-Cookie` header correct (HttpOnly + SameSite=Lax + Max-Age=2592000)

---

## References

- Design spec: `docs/plans/2026-04-22-hangman-scaffold-design.md`
- PRD: `docs/prds/hangman-scaffold.md` (v1.2)
- Research brief: `docs/research/2026-04-22-hangman-scaffold.md`
- Rules: `.claude/rules/{api-design,testing,security,principles,critical-rules}.md`
