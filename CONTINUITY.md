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

- **BDD suite shipped (Feature 1 of 3)** — PR #2 merged to master via `a811d67` (2026-04-23). 37 commits, +5953/-173. Pure `@cucumber/cucumber` v12.8.1 + `playwright` 1.59 (library) + `tsx` 4.19. 33 scenarios / 287 steps across 11 `.feature` files covering every backend endpoint + 5 UI use cases (UC1–UC4 + per-difficulty WIN/LOSS). Backend gains `HANGMAN_WORDS_FILE` env-var support + `backend/words.test.txt` for determinism. Full workflow ceremony: PRD v1.2 + research brief + 11-section design + 23-task plan, **plan-review loop PASSED in 6 iterations**, subagent-driven TDD (3 subagents per task), /simplify (4 P2 fixes), **code-review loop PASSED in 2 iterations**. `make bdd` 33/33 / 10 smoke; `make verify` clean. 2 latent cucumber-js bugs caught + fixed in-flight (Cucumber Expression escape, `require:` hook-order).
- **Hangman scaffold shipped** — PR #1 merged to master via `b09458c` (2026-04-23). 45 commits, +15k LOC. Backend (FastAPI + SQLAlchemy 2.0 + SQLite), frontend (React 19 + Vite 8 + TypeScript), Playwright E2E. Full workflow ceremony: PRD v1.2, research brief, design spec, 27-task plan, 3-iter plan-review loop, subagent-driven TDD, 3-iter code-review loop, /simplify, 2 Playwright smokes passing, `make verify` clean. Backend 172 tests / Frontend 28 tests / 2 E2E specs.

### Now

No active feature. Both scaffold + BDD suite on master. Playable locally via `make install && make backend && make frontend`; BDD via `make backend-test` + `make frontend` + `make bdd` (33/33 green).

### Next

Ready for **Feature 2: bdd-dashboard** (static analyzer + HTML generator matching `bdd_dashboard_example.html`) per the three-feature BDD plan. Or any other feature. Pick via `/new-feature <name>`.

---

## Workflow

> Updated automatically by `/new-feature` and `/fix-bug` commands.
> The Stop hook reminds you of the current phase on every response.
> The PreToolUse hook blocks commit/push/PR if quality gates are incomplete.
> Delete this section when no workflow is active (or set Command to `none`).

| Field     | Value                      |
| --------- | -------------------------- |
| Command   | /new-feature bdd-dashboard |
| Phase     | 3 — Design                 |
| Next step | Brainstorm approaches      |

### Checklist

- [x] Worktree created (`.worktrees/bdd-dashboard` on feat/bdd-dashboard, base f96e857)
- [x] Project state read
- [x] Plugins verified (superpowers + pr-review-toolkit + prd:discuss/create all exercised successfully during Feature 1)
- [x] PRD created (`docs/prds/bdd-dashboard.md` v1.1 — 7 user stories, 10 non-goals, 13-rule starter opinion engine in Appendix B; v1.1 corrections: consume gherkinDocument from NDJSON, Chart.js pin 4.5.1 exact, scenario status rollup)
- [x] Research artifact produced (`docs/research/2026-04-23-bdd-dashboard.md` — 5 libs in depth + 1 breadth survey; 3 load-bearing findings patched into PRD v1.1; 7 open risks documented)
- [x] Design guidance loaded — N/A: this feature is a developer tool generating a single dashboard HTML; visual direction is pre-set by the user's reference example. Per PRD §2, no user-facing product surface.
- [x] Brainstorming complete (`docs/plans/2026-04-24-bdd-dashboard-design.md` — 13 sections, approved by KC)
- [x] Approach comparison filled (see § "Approach Comparison" below)
- [x] Contrarian gate passed — user-validated (Codex hung at 12min; fallback-to-user per protocol). User directed the v2 LLM pivot that made the original static-rules default the credible alternative, then explicitly rejected it. Approach comparison re-scored under v2 post-pivot.
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

## Approach Comparison (v2 — post-pivot)

### Chosen Default

**Python OO package at `backend/tools/dashboard/`** that performs **LLM-based evaluation** via the Anthropic SDK. NdjsonParser + CoverageGrader (procedural, deterministic) feed a Packager that produces 33 scenario-packages + 11 feature-packages per run. LlmEvaluator dispatches all 44 packages to the Anthropic Messages API (default `claude-sonnet-4-6`, configurable) with a 13-criterion rubric in the system prompt + forced `ReportFindings` tool use + prompt caching. Results + procedural coverage grades + history flow into a Jinja-rendered single-file HTML dashboard. Golden-file tests scoped to deterministic modules only (Renderer, CoverageGrader); LLM-adjacent code tested with a MockAnthropicClient.

### Best Credible Alternative

**Static rule engine** (what was designed as v1 of this spec — the original "13 Rule classes implementing a `Rule` Protocol" design). Fully deterministic. No LLM cost. No network dependency. Faster (local-only). But no semantic judgment — cannot catch anti-patterns like "scenario says forfeit but only tests the happy path."

### Scoring (fixed axes)

| Axis                  | Default (v2 LLM)                                                         | Alternative (v1 static)                                       |
| --------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------- |
| Complexity            | **M** (add Packager + LlmEvaluator + Rubric + cost mgmt + mocking infra) | **M** (9 modules, 13 rule classes)                            |
| Blast Radius          | **L** (new dev tooling; API key side-channel)                            | **L** (new dev tooling)                                       |
| Reversibility         | **M** (refactoring LLM layer is not trivial)                             | **M** (refactoring 9 files)                                   |
| Time to Validate      | **M** (mocked unit + 1 live integration run per iteration at ~$1/run)    | **L** (fully unit-testable)                                   |
| User/Correctness Risk | **M** — but captures semantic-quality findings static rules cannot       | **M** — deterministic but catches only pre-hardcoded patterns |

### Cheapest Falsifying Test

**User direction.** The user explicitly directed the LLM pivot mid-design ("we're asking the LLM to evaluate the code... segment and package the tests in a way that they can be evaluated by an LLM, not just undergo inspection with static procedural rules"). The alternative (static rules) was the pre-pivot design; user rejected it on semantic-coverage grounds.

### Contrarian verdict

**VALIDATED by user direction** — Codex contrarian gate hung for 12+ minutes on an earlier attempt; fallback per council-skill protocol is user-validates. User's Q1-Q8 answers in the PRD discussion + the explicit pivot challenge constitute the user's validation of the LLM path. The alternative (static rules) was explicitly rejected.

**Cost trade-off acknowledged by user:** default Sonnet 4.6 at ~$1.11/run, configurable to Haiku 4.5 ($0.37/run) for cheap iteration or Opus 4.7 ($1.86/run) for deep review.

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
