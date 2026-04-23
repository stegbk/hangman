# Changelog

All notable changes to Hangman will be documented in this file.

## [Unreleased]

### Added

- **2026-04-22 — hangman-scaffold feature (Phase 4 nearly complete):**
  - Backend: FastAPI 0.136 + Pydantic 2.13 + SQLAlchemy 2.0.49 + SQLite + uvicorn 0.45. Sync Python stack per research brief. Six endpoints under `/api/v1/` (categories, session, games [POST], games/current [GET], games/{id}/guesses [POST], history). 108 tests passing (unit + integration), 100% branch coverage on `game.py`, ruff + mypy strict clean.
  - Frontend: React 19.2 + Vite 8.0.9 + TypeScript 5.7 + Vitest 3 + ESLint 9 flat config + Prettier 3. Six presentational components (HangmanFigure ASCII, Keyboard, ScorePanel, HistoryList, CategoryPicker, GameBoard) + App.tsx state owner (prop-drilling, no Context/Redux). 23 tests passing, `pnpm build` clean (196 kB JS / 62 kB gzipped).
  - Data: 45 seed words across 3 categories (Animals, Food, Tech); CSV parser in `words.py` validates before lowercasing. Session cookie: 30-day opaque UUID, HttpOnly, SameSite=Lax.
  - Playwright: framework installed, chromium downloaded, `webServer: [backend, frontend]` config, auth fixture stub (no-op since no auth).
  - Full plan review loop ran (3 iterations) via Claude + Codex; all 11 P1/P2 findings fixed before execution.
- PRD: `docs/prds/hangman-scaffold.md` (v1.2 — 5 user stories, acceptance criteria, edge cases, 13 non-goals, scoring formula, cookie semantics).
- Research brief: `docs/research/2026-04-22-hangman-scaffold.md` (20 libs researched, load-bearing decisions: sync Python stack, hand-rolled cookie dependency, Node 22+/pnpm 10+).
- Design spec: `docs/plans/2026-04-22-hangman-scaffold-design.md` (8 sections: architecture, module breakdown, data flow, testing strategy).
- Implementation plan: `docs/plans/2026-04-22-hangman-scaffold-plan.md` (27 tasks, ~4850 lines, Dispatch Plan + 4 E2E Use Cases).

### Changed

- `Makefile`: `install` target now also runs `uv pip install -e .` so `make backend` can import the local `hangman` package (bug discovered during Task 24 smoke-check — `uv sync` alone doesn't install the editable project).

### Fixed

- `.claude/hooks/check-workflow-gates.sh`: removed `git commit` from the ship-action matcher. The hook's comment said "Only gate ship actions" but the matcher included `git commit` alongside push/PR, which blocked Phase-4 per-task commits (TDD + subagent-driven-development). Only `git push` and `gh pr create` are real ship boundaries. Commits are local and reversible.
- `.claude/agents/verify-e2e.md`: enumerated the 21 `mcp__playwright__browser_*` tools explicitly. The bare `mcp__playwright` entry granted no tools at runtime, forcing the agent to classify UI verification as FAIL_INFRA.
- **Phase 5.1 code-review loop iteration 1** — 6 P1 + 12 P2 findings across 4 commits:
  - **Backend** (eb57d92): `GameCreate.category` accepts capitalized input (PRD uses `Animals/Food/Tech`); invalid-letter guesses return `INVALID_LETTER` (was `VALIDATION_ERROR` — route-level handler was unreachable); error handlers log at warn/info/exception level with `request_id`; partial unique index on `games(session_id) WHERE state='IN_PROGRESS'` enforces PRD US-005 two-tab case at DB level with IntegrityError-retry path; `Difficulty`/`GameState` import from `game.py` in `schemas.py` (single source of truth); `sessions.py` logs stale-cookie misses; `routes.py` logs forfeit events; `WordPool.categories` wrapped in `MappingProxyType` for read-only access. 111 → 116 tests.
  - **Frontend** (cc0d2dc): `guessPending` state disables keyboard during in-flight guess (prevents double-click races); `humanError` maps 9 error codes to user-friendly messages + surfaces `request_id` for INTERNAL_ERROR + detects network failures; boot effect now sequential (`getCategories` first to establish cookie, then parallel remaining three) to avoid creating 4 orphan Session rows on fresh-browser load; `ScorePanel` switched to `<dl>/<dt><dd>` semantic HTML (was `<label>` without `htmlFor`, invalid HTML).
  - **Tests + build** (49fe7a5): non-flaky UC3b spec via hard-difficulty + 4 guaranteed-miss letters (j/q/x/z) — was 20% flake on easy; `Makefile test` target uses `pnpm test:run` (was `pnpm test -- --run` which left watch mode on); `conftest.py` sets `HANGMAN_DB_URL=sqlite:///:memory:` before importing `hangman.*` (TestClient lifespan no longer touches `backend/hangman.db`); weak-tautology test replaced with hermetic test-category assertion; 4 history pagination bounds tests; `frontend/src/App.test.tsx` (5 unit tests) covering the UC3b forfeit-scope regression at unit level + mount-error path; numeric `COOKIE_MAX_AGE == 2592000` assertion. 23 → 28 frontend tests.
  - **Playwright sync barrier** (5a6553c): replaced `if (await btn.isDisabled()) continue;` with `await expect(btn).toBeEnabled({ timeout: 3000 })`. The iter-1 `guessPending` state disables the whole keyboard during each in-flight guess; the old pattern incorrectly skipped every letter while pending. Both specs pass in 1.1s + 1.8s against live backend.

### Removed

---

## Format

Each entry should include:

- Date (YYYY-MM-DD)
- Brief description
- Related issue/PR if applicable
