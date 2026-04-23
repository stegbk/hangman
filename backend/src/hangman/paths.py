"""Shared filesystem paths for the backend package.

`BACKEND_ROOT` is the directory containing `pyproject.toml`, `words.txt`,
and the default `hangman.db` — i.e., the `backend/` folder itself. Both
`db.py` (for the SQLite file fallback) and `main.py` (for the word-list
fallback + HANGMAN_WORDS_FILE relative-path resolution) need it, so it
lives here rather than being duplicated.
"""

from pathlib import Path

BACKEND_ROOT: Path = Path(__file__).resolve().parent.parent.parent
