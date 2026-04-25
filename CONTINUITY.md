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
| Phase     | 3 — Design (plan review)         |
| Next step | Phase 3.3 plan review loop       |

### Checklist

- [x] Worktree created (`.worktrees/bdd-branch-coverage` on feat/bdd-branch-coverage, base bf1b2df)
- [x] Project state read
- [x] Plugins verified (superpowers + pr-review-toolkit + prd:discuss/create exercised through Features 1 + 2 this session)
- [x] PRD created (`docs/prds/bdd-branch-coverage.md` v1.0 — 8 user stories, 9 non-goals, 8 success metrics, 7 open questions for design/research)
- [x] Research artifact produced (`docs/research/2026-04-24-bdd-branch-coverage.md` — 5 libs, 5 design-changing findings, 8 open risks. Headline: **pyan3 over pycg** (pycg archived 2023; pyan3 revived 2026-02 with 3.10-3.14 support, 91% self-coverage, latest 2.5.0 on 2026-04-21). Resolves PRD Q1 + Q4. Use `coverage run --branch --parallel-mode -m uvicorn` subprocess approach.)
- [ ] Design guidance loaded (if UI)
- [x] Brainstorming complete (`docs/plans/2026-04-24-bdd-branch-coverage-design.md` v1.0 — 13 sections, ~890 lines; all 7 PRD open questions + 5 plan-phase details resolved; approved by KC)
- [x] Approach comparison filled (see § "Approach Comparison" below — default = full static + dynamic + audit reconciliation; alternative = pure dynamic, falsified at PRD-requirement level)
- [x] Contrarian gate passed (Codex VALIDATE — narrow-scope prompt returned clean with 4 flags; 2 already addressed, 2 new P1/P2 patched inline in commit `75a7708`: audit dedup across endpoints + switch pyan3 from subprocess+DOT to Python API via CallGraphVisitor)
- [ ] Council verdict (if triggered): [approach chosen]
- [x] Plan written (`docs/plans/2026-04-24-bdd-branch-coverage-plan.md` — 16 tasks across 8 phases, ~3950 lines after formatter, dispatch plan with 3 parallel waves after scaffold, self-review pass with 6 highest-risk areas flagged for plan-review loop)
- [ ] Plan review loop (10 iterations) — Iter 1-9: see prior commits. Iter 10 (Claude CLEAN, Codex 1 P1): H1 Step 7b's "shared-helper correctness check" was built on FALSE codebase assumptions: claimed `apply_guess` is shared between `POST /games/{id}/guesses` AND `POST /games/{id}/forfeit` AND that there were no `/forfeit` scenarios. Reality (verified by Codex against actual repo): no `/games/{id}/forfeit` route exists (forfeit is part of `POST /api/v1/games`); `apply_guess` only called from `/guesses`; `forfeit.feature` exists with multiple scenarios. The check was unprovable. Replaced with three checks against real codebase facts: (1) POSITIVE — `/guesses` credits apply_guess branches (catches Grader regression to exact arc-id); (2) NEGATIVE — `/categories` MUST NOT reach apply_guess (catches Reachability over-following or middleware over-attributing); (3) updated acceptance criteria. Iter 11 next.
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

## Approach Comparison

### Chosen Default

**Python OO package at `backend/tools/branch_coverage/`** combining:

1. **Reflective FastAPI route enumeration** (`from hangman.main import app; app.routes`) — authoritative endpoint list, replacing Feature 2's regex scrape.
2. **Static call-graph via pyan3** (subprocess) — best-effort reachability from each route handler through `backend/src/hangman/`.
3. **Dynamic `coverage.py --branch`** (subprocess under uvicorn via `coverage run`) — records which branches the BDD suite actually exercises.
4. **Audit reconciliation** against coverage.py's authoritative per-file branch count — any gap lands in `unattributed_branches`; ensures we never silently over-report.
5. **`coverage.json` single source of truth** consumed by Feature 2's dashboard (new "Code coverage" card + coverage summary injected into the cached LLM system prompt for coverage-aware findings via new rubric criterion D7).

### Best Credible Alternative

**Pure dynamic coverage — no static call-graph, no per-endpoint attribution.** Run `coverage.py --branch` over the BDD suite, emit a standard `coverage html` report, treat "which endpoints have uncovered branches" as outside scope. ~200 LOC instead of ~1000-1500. Keeps the same Make target shape. Loses: per-endpoint reachability attribution, audit reconciliation, integration with Feature 2's dashboard beyond "here's a link to the standard coverage report."

### Scoring (fixed axes)

| Axis                  | Default (full: static + dynamic + audit)                             | Alternative (pure dynamic)                                                                   |
| --------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Complexity            | **M** (11 modules, pyan3 subprocess, reconciliation logic)           | **L** (coverage.py + a thin wrapper)                                                         |
| Blast Radius          | **L** (new dev tool + 5 files modified in Feature 2)                 | **L** (new dev tool, minimal Feature 2 changes)                                              |
| Reversibility         | **M** (pyan3 dep + dashboard augmentation are additive)              | **L** (just a coverage report)                                                               |
| Time to Validate      | **M** (integration test + audit invariant checks)                    | **L** (standard coverage.py validation)                                                      |
| User/Correctness Risk | **M** — pyan3 is best-effort; audit reconciliation is the safety net | **M** — no endpoint attribution means PRD US-001 / US-003 / US-005 / US-006 aren't satisfied |

### Cheapest Falsifying Test

**Already falsified by the PRD.** US-001 ("per-endpoint code-path coverage"), US-003 ("endpoints enumerated from routes.py"), US-005 ("Feature 2 dashboard augmentation"), and US-006 ("LLM coverage-aware") all require per-endpoint attribution. The pure-dynamic alternative delivers a coverage.html file but no endpoint-centric view — it fails the PRD at the requirements level, not at the implementation level. No spike needed; the PRD is the falsifying test.

A secondary validation: the research brief's "pyan3 ratified" finding (2.5.0 revived 2026-02, 3 days ago; pycg archived) means the default's static-analysis leg has a maintained tool. That was the risk that might have forced us toward the pure-dynamic fallback — it's no longer load-bearing.

### Contrarian verdict

**Expected: VALIDATE.** The default is the only approach that satisfies the PRD's per-endpoint attribution requirement. The alternative exists in the comparison to prove we considered a simpler path and rejected it for a specific, documented reason (PRD scope). Codex contrarian gate should confirm no alternative was missed.

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
