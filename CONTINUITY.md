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

## Workflow

> Updated automatically by `/new-feature` and `/fix-bug` commands.
> The Stop hook reminds you of the current phase on every response.
> The PreToolUse hook blocks commit/push/PR if quality gates are incomplete.
> Delete this section when no workflow is active (or set Command to `none`).

| Field     | Value                                                                |
| --------- | -------------------------------------------------------------------- |
| Command   | /new-feature bdd-suite                                               |
| Phase     | 3 — Design                                                           |
| Next step | Plan review loop iter-2 (re-run Claude + Codex against revised plan) |

### Checklist

- [x] Worktree created (`.worktrees/bdd-suite` on feat/bdd-suite, base 40d18f5)
- [x] Project state read
- [x] Plugins verified (superpowers + pr-review-toolkit + prd:discuss/create in skill list)
- [x] PRD created (`docs/prds/bdd-suite.md` v1.1 — post-research corrections: tsx not ts-node, json+ndjson dual output, Node ≥20 engines pin)
- [x] Research artifact produced (`docs/research/2026-04-23-bdd-suite.md` — 10 library sections, gate passed; 3 load-bearing findings patched into PRD v1.1)
- [x] Design guidance loaded — N/A (BDD is test infrastructure; no user-facing UI surface)
- [x] Brainstorming complete (`docs/plans/2026-04-23-bdd-suite-design.md` — 10 sections, approved by KC; Option A test-mode pool added on 2026-04-23 to unlock per-difficulty UI determinism)
- [x] Approach comparison filled (single-viable architecture; sub-variations resolved: browser lifecycle A + gate automation A)
- [x] Contrarian gate passed — VALIDATE (Codex auto-trigger confirmed default wins; research brief + PRD Q1/Q17 pre-resolved the design space)
- [x] Council verdict (if triggered): N/A (gate VALIDATED — no council fired)
- [x] Plan written (`docs/plans/2026-04-23-bdd-suite-plan.md` — 23 tasks, Gherkin inline, dispatch plan filled, self-reviewed)
- [ ] Plan review loop (2 iterations so far — iter-1: 12 P0/P1/P2 on API-shape/error-code/testid/score/dialog mismatches; iter-2: 4 P1/P2 on masked-word UI-vs-API format, session-scenario ordering, fail-fast frontend probe, dialog-tag mutex, step-def fold-in; iter-3 review pending)
- [ ] TDD execution complete
- [ ] Code review loop (0 iterations) — iterate until no P0/P1/P2
- [ ] Simplified
- [ ] Verified (tests/lint/types)
- [ ] E2E use cases designed (Phase 3.2b)
- [ ] E2E verified via verify-e2e agent (Phase 5.4)
- [ ] E2E regression passed (Phase 5.4b)
- [ ] E2E use cases graduated to tests/e2e/use-cases/ (Phase 6.2b)
- [ ] E2E specs graduated to tests/e2e/specs/ (Phase 6.2c — if Playwright framework installed)
- [ ] Learnings documented (if any)
- [ ] State files updated
- [ ] Committed and pushed
- [ ] PR created
- [ ] PR reviews addressed
- [ ] Branch finished

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
