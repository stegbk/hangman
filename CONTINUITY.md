# CONTINUITY

## Goal

A local HTTP hangman game with category picker, score/streak tracking, difficulty levels, and per-session game history.

## Key Decisions

| Decision          | Choice                              | Why                                                   |
| ----------------- | ----------------------------------- | ----------------------------------------------------- |
| Backend framework | Python 3.12 + FastAPI               | Matches project rules (uv / pytest / ruff / Pydantic) |
| Frontend          | React + TypeScript + Vite           | Rich interactive UI, standard tooling                 |
| Persistence       | SQLite + session cookie             | Per-browser history, zero-setup local storage         |
| Word source       | Bundled `words.txt` with categories | Offline, deterministic, no external API dependency    |
| Features          | Score + streaks + difficulty        | Replayability beyond one-and-done games               |

---

## State

### Done (recent 2-3 only)

- **Hangman scaffold shipped** — PR #1 merged to master via `b09458c` (2026-04-23). 45 commits, +15k LOC. Backend (FastAPI + SQLAlchemy 2.0 + SQLite), frontend (React 19 + Vite 8 + TypeScript), Playwright E2E. Full workflow ceremony: PRD v1.2, research brief, design spec, 27-task plan, 3-iter plan-review loop, subagent-driven TDD, 3-iter code-review loop, /simplify, 2 Playwright smokes passing, `make verify` clean. Backend 172 tests / Frontend 28 tests / 2 E2E specs.
- **Hook fix** (shipped with scaffold): `.claude/hooks/check-workflow-gates.sh` stopped gating local `git commit` — only `git push` / `gh pr create` are ship actions.

### Now

No active feature. Scaffold is on master and playable locally via `make install && make backend && make frontend`.

### Next

Ready for the next feature. Candidates: visual polish (SVG hangman + animations), more categories, additional difficulty tuning, session sweeper, leaderboard, multiplayer. Pick any via `/new-feature <name>`.

---


## Open Questions

- [Question needing resolution]

## Blockers

- [None currently]

---

## Update Rules

> **IMPORTANT:** You (Claude) are responsible for updating this file. The Stop hook will remind you, but YOU must make the edits.

**On task completion:**

1. Add to Done (keep only 2-3 recent items)
2. Move top of Next → Now
3. Add to CHANGELOG.md if significant

**On new feature:**
Clear Done section, start fresh

**Where detailed progress lives:**

- Feature subtasks → `docs/plans/[feature].md`
- Historical record → `docs/CHANGELOG.md`
- Learnings → `docs/solutions/`

---

## Session Start

Claude should say:

> "Loaded project state. Current focus: [Now]. Ready to continue or start something new?"
