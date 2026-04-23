# Hangman

A local HTTP hangman game with category picker, score/streak tracking, difficulty levels, and per-session game history. Single-player, runs entirely on your machine — no accounts, no network calls beyond localhost.

**Tech:** FastAPI + SQLite + Pydantic v2 backend · React 19 + Vite 8 + TypeScript frontend · Playwright for E2E.

## Prerequisites

- **Python 3.12+**
- **Node 22+** (pnpm 10 dropped Node 20 support)
- **pnpm 10+** (pnpm 9 reached EOL 2026-04-30)
- **[uv](https://docs.astral.sh/uv/)** — fast Python package manager

## Setup

One command installs everything (backend deps + frontend deps + Playwright chromium):

```bash
make install
```

Under the hood that runs:

```bash
cd backend  && uv sync && uv pip install -e .
cd frontend && pnpm install
cd frontend && pnpm exec playwright install chromium
```

The editable `uv pip install -e .` step is required so `uvicorn` can resolve the `hangman` package on `PYTHONPATH`.

## Run

Open two terminals:

**Terminal A — backend (default `http://localhost:8000`):**

```bash
make backend
```

**Terminal B — frontend (default `http://localhost:3000`):**

```bash
make frontend
```

Open <http://localhost:3000> in a browser to play. Vite proxies `/api/*` to the backend so there's no CORS dance.

### Port overrides

If something else is holding port 8000 or 3000 (SSH tunnels, another dev server, etc.), pass env vars:

```bash
# Backend on 8002, frontend on 3001
make backend HANGMAN_BACKEND_PORT=8002
make frontend HANGMAN_BACKEND_PORT=8002 HANGMAN_FRONTEND_PORT=3001
```

`vite.config.ts` and `playwright.config.ts` read the same two variables, so the frontend proxy + Playwright `webServer` stay aligned automatically.

## Test

```bash
make test        # pytest (backend) + vitest (frontend) — unit + integration
make lint        # ruff (backend) + eslint (frontend)
make typecheck   # mypy (backend) + tsc --noEmit (frontend)
make verify      # lint + typecheck + test
```

### End-to-end (Playwright)

```bash
cd frontend && pnpm exec playwright test --grep @smoke
```

With the same port overrides if needed:

```bash
cd frontend && HANGMAN_BACKEND_PORT=8002 HANGMAN_FRONTEND_PORT=3001 \
  pnpm exec playwright test --grep @smoke
```

Playwright's `webServer` config boots both servers automatically when they aren't already running (`reuseExistingServer: true`).

## Gameplay

1. **Pick a category and difficulty.**
   - Categories: Animals, Food, Tech (15 words each, randomized per game).
   - Difficulties: Easy (8 wrong guesses allowed), Medium (6), Hard (4).
2. **Guess letters.** Click a keyboard button. Correct letters reveal in the masked word; wrong letters advance the ASCII hangman figure.
3. **Win → score + streak.** Base score = `(correct_reveals × 10) + (lives_remaining × 5)`. Streak multiplier kicks in at 2 consecutive wins (2×) and 3+ (3×). Example: 3 reveals + 8 lives at streak 2 = `(30 + 40) × 2 = 140`.
4. **Lose → score = 0, streak resets to 0.** `best_streak` is preserved.
5. **Session persists.** A 30-day `HttpOnly` + `SameSite=Lax` cookie keeps your score, streak, and history across reloads and return visits. Clearing cookies resets everything.
6. **One game at a time.** Starting a new game while one is IN_PROGRESS prompts a forfeit confirmation. A terminal (WON/LOST) game doesn't — just click Start New Game to continue.

## Layout

```
hangman/
├── backend/              # FastAPI + SQLAlchemy 2.0 + SQLite, uv-managed
│   ├── src/hangman/      # game.py, routes.py, schemas.py, models.py, ...
│   ├── tests/unit/       # pure logic (no DB)
│   ├── tests/integration/# TestClient + in-memory SQLite
│   ├── words.txt         # CSV seed (category,word)
│   └── pyproject.toml
├── frontend/             # React 19 + Vite 8 + TypeScript, pnpm-managed
│   ├── src/components/   # GameBoard, Keyboard, ScorePanel, HistoryList, ...
│   ├── src/api/          # typed fetch wrappers
│   ├── src/App.tsx       # state owner (prop-drilling)
│   ├── tests/e2e/
│   │   ├── specs/        # Playwright specs (smoke)
│   │   ├── use-cases/    # markdown regression suite
│   │   └── fixtures/     # auth fixture (no-op; no auth in scaffold)
│   └── package.json
├── Makefile              # install / backend / frontend / test / lint / typecheck / verify
├── docs/
│   ├── prds/             # PRD + discussion log
│   ├── plans/            # design spec + implementation plan
│   ├── research/         # dated research briefs
│   ├── solutions/        # compounded learnings (populated as bugs are solved)
│   └── CHANGELOG.md
└── tests/e2e/reports/    # verify-e2e agent reports (gitignored)
```

For the full architectural design see [`docs/plans/2026-04-22-hangman-scaffold-design.md`](docs/plans/2026-04-22-hangman-scaffold-design.md); for the PRD see [`docs/prds/hangman-scaffold.md`](docs/prds/hangman-scaffold.md).
