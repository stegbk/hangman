"""Tests for the HANGMAN_WORDS_FILE env-var override in the FastAPI lifespan."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _write_pool(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "words.test.txt"
    p.write_text(body, encoding="utf-8")
    return p


def test_env_var_unset_loads_production_pool(monkeypatch):
    monkeypatch.delenv("HANGMAN_WORDS_FILE", raising=False)
    from hangman.main import app

    # Verify via app.state.word_pool (the authoritative source of loaded pool
    # contents). We deliberately do NOT hit /api/v1/categories here: the
    # module-global SQLite engine is pinned to sqlite:///:memory: by
    # conftest.py for safety, and a bare TestClient(app) without the
    # dependency-override fixture yields a fresh (empty) per-connection DB.
    # That DB concern is unrelated to what this test validates (env-var →
    # pool-source wiring), so we read the pool directly.
    with TestClient(app) as client:
        pool = client.app.state.word_pool

    assert set(pool.category_names()) == {"animals", "food", "tech"}
    assert len(pool.categories["animals"]) > 1


def test_env_var_absolute_path_loads_caller_pool(monkeypatch, tmp_path):
    pool_file = _write_pool(tmp_path, "animals,cat\nfood,cat\ntech,cat\n")
    monkeypatch.setenv("HANGMAN_WORDS_FILE", str(pool_file))
    from hangman.main import app

    with TestClient(app) as client:
        pool = client.app.state.word_pool

    assert set(pool.category_names()) == {"animals", "food", "tech"}
    # All three categories collapsed to exactly one word under the test pool.
    assert all(len(words) == 1 for words in pool.categories.values())


def test_env_var_relative_path_resolves_against_backend_root(monkeypatch, tmp_path):
    # Prove the lifespan resolves HANGMAN_WORDS_FILE against BACKEND_ROOT,
    # NOT against the current working directory. Change CWD to tmp_path so
    # a CWD-relative resolution would fail (tmp_path has no words.test.txt),
    # then verify the pool still loads from backend/words.test.txt.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HANGMAN_WORDS_FILE", "words.test.txt")
    from hangman.main import app

    with TestClient(app) as client:
        pool = client.app.state.word_pool

    # Pin the exact category set — an empty pool would satisfy the
    # "all categories have 1 word" check vacuously.
    assert set(pool.categories.keys()) == {"animals", "food", "tech"}
    assert all(len(words) == 1 for words in pool.categories.values())


def test_env_var_missing_file_raises_at_startup(monkeypatch):
    monkeypatch.setenv("HANGMAN_WORDS_FILE", "/does/not/exist.txt")
    from hangman.main import app

    with pytest.raises(FileNotFoundError), TestClient(app):
        pass  # lifespan startup should raise before the context yields
