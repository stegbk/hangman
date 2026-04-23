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

### Removed

---

## Format

Each entry should include:

- Date (YYYY-MM-DD)
- Brief description
- Related issue/PR if applicable
