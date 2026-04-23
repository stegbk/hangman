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
