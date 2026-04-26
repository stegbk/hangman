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

## BDD Dashboard (Feature 2)

A developer-only tool that evaluates the BDD suite's Gherkin quality using
the Anthropic API. Produces `tests/bdd/reports/dashboard.html` — a single
self-contained HTML file with coverage grades, LLM-evaluated findings,
trend chart, and per-scenario modal.

### Prerequisites

- `ANTHROPIC_API_KEY` in your environment (starts with `sk-ant-`). Place
  it in `.env` at the repo root (gitignored; `make bdd-dashboard`
  auto-loads it).
- A prior `make bdd` run (produces `frontend/test-results/cucumber.ndjson`).

### Run

```bash
make bdd-dashboard                                # claude-sonnet-4-6, ~$1.11/run
make bdd-dashboard MODEL=claude-haiku-4-5         # cheaper, ~$0.37/run
make bdd-dashboard MODEL=claude-opus-4-7          # deepest, ~$1.86/run
```

Output: `tests/bdd/reports/dashboard.html`. Open in a browser.

### What it evaluates

- **Coverage:** per-endpoint (`POST /api/v1/games/{id}/guesses`, etc.)
  and per-UC (UC1, UC2, ...) — Full / Partial / None based on
  `@happy` + `@failure` + `@edge` mix.
- **Quality:** 13-criterion rubric covering domain concerns
  (trivial-pass, missing error codes, missing state assertions) and
  hygiene (duplicate titles, missing primary tags, long scenarios).
- **Trend:** per-run history under `.bdd-history/` (gitignored).

### Cost

Runs at ~$1.11 Sonnet / ~$0.37 Haiku / ~$1.86 Opus per invocation. The
rubric is cached; cache hit rate runs ~90% after the first call.

## BDD Branch Coverage (Feature 3)

A developer-only tool that measures what code paths in
`backend/src/hangman/` the BDD suite actually exercises — per-endpoint,
with authoritative audit reconciliation against coverage.py's branch
counts. Produces `tests/bdd/reports/coverage.html` (standalone report)
and `tests/bdd/reports/coverage.json` (consumed by Feature 2's
dashboard as an augment card + LLM coverage-aware findings).

### Prerequisites

- Feature 1 (BDD suite) and Feature 2 (dashboard) on master
- `make install` has run (adds coverage + pyan3 dev deps)
- No API key required (Feature 3 is local-only; Feature 2's LLM
  augmentation is optional)

### Run

Three terminals (matches the existing `make backend` + `make frontend`

- `make bdd` pattern):

```bash
# Terminal 1
make backend-coverage

# Terminal 2
make frontend

# Terminal 3
make bdd-coverage
```

`make bdd-coverage` runs the cucumber suite, SIGTERMs the backend
(coverage.py's `sigterm=true` flushes the data file), combines the
parallel-mode fragments, and invokes the analyzer. Emits:

- `frontend/test-results/cucumber.coverage.ndjson` — instrumented BDD run
- `tests/bdd/reports/coverage.html` — standalone coverage dashboard
- `tests/bdd/reports/coverage.json` — machine-readable artifact for Feature 2

**Important: single uvicorn worker + sequential cucumber.** Coverage
contexts are process-global; concurrent requests corrupt attribution.
Both defaults are already single-threaded. Don't bump workers for
instrumented runs.

### What it measures

- **Per-endpoint coverage**: for each FastAPI route, what % of
  reachable branches did scenarios hitting THAT endpoint actually
  exercise. Red (<50%) / yellow (50-80%) / green (≥80%).
- **Drill-down**: per-reachable-function list of uncovered branches
  with file:line + source snippet.
- **Extra coverage**: functions hit by the BDD suite that the static
  call-graph missed (e.g. FastAPI `Depends()` chains).
- **Audit reconciliation**: cross-check against coverage.py's
  authoritative per-file branch count. Any gap lands in
  `unattributed_branches` — surfaced, not silently dropped.

### Feature 2 integration

When `tests/bdd/reports/coverage.json` is present and fresh (within 1h
of the cucumber.ndjson mtime), `make bdd-dashboard` auto-detects it
and augments:

- New "Code coverage" summary card on the dashboard
- Per-endpoint uncovered-branch data injected into the LLM's cached
  system prompt (coverage-aware findings via new criterion D7)

### Cost

Zero API cost. Coverage instrumentation adds ~10-30% to BDD suite
wall-clock time.

## Running the BDD suite

The BDD suite (pure `@cucumber/cucumber` v12 + `playwright`) runs separately from `make verify` and requires the backend + frontend running in test-mode.

```bash
# Terminal A — backend with test-mode word pool (one-word "cat" per category)
make backend-test

# Terminal B — frontend dev server
make frontend

# Terminal C — run all 33 scenarios across 11 feature files
make bdd
```

Port overrides work the same as `make backend` / `make frontend`:

```bash
make backend-test HANGMAN_BACKEND_PORT=8002
make frontend     HANGMAN_BACKEND_PORT=8002 HANGMAN_FRONTEND_PORT=3001
make bdd          HANGMAN_BACKEND_PORT=8002 HANGMAN_FRONTEND_PORT=3001
```

Artifacts land in `frontend/test-results/cucumber.{json,ndjson}` (gitignored).

**Why `make backend-test` and not `make backend`?** Production `words.txt` has 45 words across 3 categories; only a handful of letters never appear in any easy-animals seed, which isn't enough to deterministically test Easy (8 misses) and Medium (6 misses) LOSS scenarios. `make backend-test` sets `HANGMAN_WORDS_FILE=words.test.txt` so every category collapses to `"cat"`, giving every scenario one deterministic source of truth for guess outcomes. It also isolates the DB (`HANGMAN_DB_URL=sqlite:///...hangman.test.db`) so BDD runs never touch your local production `hangman.db`. See [`docs/plans/2026-04-23-bdd-suite-design.md`](docs/plans/2026-04-23-bdd-suite-design.md) §2b for the full rationale.
