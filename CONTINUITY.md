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

- **BDD Dashboard shipped (Feature 2 of 3)** — PR #3 merged to master via `0bfe6ba` (2026-04-24). 23 commits, +10885/-3 LOC. Python tool at `backend/tools/dashboard/`: parses `cucumber.ndjson`, packages 33 scenarios + 11 features into ~44 LLM calls (Anthropic SDK, forced `ReportFindings` tool use, prompt caching ~90%), renders single-file HTML via Jinja2. 12 modules / 99 tests / 13-criterion rubric (D1–D6 domain + H1–H7 hygiene). Default `claude-sonnet-4-6` (~$0.74/run measured; configurable to Haiku $0.37 or Opus $1.86 via `MODEL=`). Full workflow: PRD v2.0 + research brief + 13-section design + 14-task plan, **plan-review loop PASSED in 3 iterations**, subagent-driven TDD (9 dispatch waves), /simplify (1×P1 + 6×P2 + 4×P3 fixed), **code-review loop PASSED in 2 iterations** (Codex + PR Review Toolkit verdict-agree clean), live integration verified twice ($0.74, 90→93% cache hit). 4 real bugs caught + fixed in-flight (3 in cost/cache logic during H1 smoke; 1 cosmetic Severity.value rendering).
- **BDD suite shipped (Feature 1 of 3)** — PR #2 merged to master via `a811d67` (2026-04-23). 37 commits, +5953/-173. Pure `@cucumber/cucumber` v12.8.1 + `playwright` 1.59 (library) + `tsx` 4.19. 33 scenarios / 287 steps across 11 `.feature` files covering every backend endpoint + 5 UI use cases (UC1–UC4 + per-difficulty WIN/LOSS). Backend gains `HANGMAN_WORDS_FILE` env-var support + `backend/words.test.txt` for determinism. Full workflow ceremony: PRD v1.2 + research brief + 11-section design + 23-task plan, **plan-review loop PASSED in 6 iterations**, subagent-driven TDD (3 subagents per task), /simplify (4 P2 fixes), **code-review loop PASSED in 2 iterations**. `make bdd` 33/33 / 10 smoke; `make verify` clean. 2 latent cucumber-js bugs caught + fixed in-flight (Cucumber Expression escape, `require:` hook-order).

### Now

No active feature. Scaffold + BDD suite + BDD dashboard all on master. Playable locally via `make install && make backend && make frontend`. BDD: `make backend-test` + `make frontend` + `make bdd` (33/33 green from Feature 1's last live run). Dashboard: `make bdd-dashboard` (requires `ANTHROPIC_API_KEY` in `.env`).

### Next

Ready for **Feature 3: bdd-branch-coverage** (call graph + per-branch coverage contexts + gap detection) per the three-feature BDD plan. Will replace Feature 2's tag-based coverage with call-graph-based branch coverage. Pick via `/new-feature bdd-branch-coverage`.

---

## Workflow

> Updated automatically by `/new-feature` and `/fix-bug` commands.
> The Stop hook reminds you of the current phase on every response.
> The PreToolUse hook blocks commit/push/PR if quality gates are incomplete.
> Delete this section when no workflow is active (or set Command to `none`).

| Field     | Value                            |
| --------- | -------------------------------- |
| Command   | /new-feature bdd-branch-coverage |
| Phase     | 3 — Design                       |
| Next step | `/superpowers:brainstorming`     |

### Checklist

- [x] Worktree created (`.worktrees/bdd-branch-coverage` on feat/bdd-branch-coverage, base bf1b2df)
- [x] Project state read
- [x] Plugins verified (superpowers + pr-review-toolkit + prd:discuss/create exercised through Features 1 + 2 this session)
- [x] PRD created (`docs/prds/bdd-branch-coverage.md` v1.0 — 8 user stories, 9 non-goals, 8 success metrics, 7 open questions for design/research)
- [x] Research artifact produced (`docs/research/2026-04-24-bdd-branch-coverage.md` — 5 libs, 5 design-changing findings, 8 open risks. Headline: **pyan3 over pycg** (pycg archived 2023; pyan3 revived 2026-02 with 3.10-3.14 support, 91% self-coverage, latest 2.5.0 on 2026-04-21). Resolves PRD Q1 + Q4. Use `coverage run --branch --parallel-mode -m uvicorn` subprocess approach.)
- [ ] Design guidance loaded (if UI)
- [ ] Brainstorming complete
- [ ] Approach comparison filled
- [ ] Contrarian gate passed (skip | spike | council)
- [ ] Council verdict (if triggered): [approach chosen]
- [ ] Plan written
- [ ] Plan review loop (0 iterations) — iterate until no P0/P1/P2
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
