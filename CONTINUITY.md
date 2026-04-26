# CONTINUITY

## Goal

A local HTTP hangman game with category picker, score/streak tracking, difficulty levels, and per-session game history. **Also: a methodology test bed for a larger high-stakes system** — the BDD-suite → LLM-graded-dashboard → branch-coverage arc is itself the artifact under test.

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

- **BDD Branch Coverage shipped (Feature 3 of 3)** — PR #4 merged to master via `0f2bac7` (2026-04-26). 49 commits, +11533/-28 LOC across 61 files. Python tool at `backend/tools/branch_coverage/` (13 modules): reflective FastAPI route enumeration → pyan3 call-graph → BFS reachability → coverage.py instrumentation with per-endpoint contexts via `CoverageContextMiddleware` → line-granularity grader + audit reconciliation → JSON/HTML emitter. Augments Feature 2 dashboard with new "Code coverage" card + LLM rubric criterion D7 ("Missed coverage opportunity"). Full workflow: PRD v1.0 + research brief + design spec v1.0 + 16-task plan, **plan-review loop PASSED in 16 iterations** (~30 P1 + ~25 P2 patched), subagent-driven TDD (17 tasks; A3 spike + H1 live smoke caught 4 production bugs in-flight), /simplify (-36 LOC: 2 P1 efficiency wins), **code-review loop PASSED in 7 iterations** (Codex + PR Toolkit verdict-agree clean). 303 unit + 67 integration tests; ruff + mypy clean; 33/33 BDD scenarios under instrumentation; audit reconciled=True at 97.2% (35/36). D7 demo on Haiku ($0.17 / 93% cache) emitted 22 findings citing the orphan-cookie gap — but missed the `routes.py:173` `IntegrityError` over-broad-catch bug, exposing the next blind spot (semantic correctness in covered code → mutation testing).
- **BDD Dashboard shipped (Feature 2 of 3)** — PR #3 merged to master via `0bfe6ba` (2026-04-24). 23 commits, +10885/-3 LOC. Python tool at `backend/tools/dashboard/`: parses `cucumber.ndjson`, packages 33 scenarios + 11 features into ~44 LLM calls (Anthropic SDK, forced `ReportFindings` tool use, prompt caching ~90%), renders single-file HTML via Jinja2. 12 modules / 99 tests / 13-criterion rubric (D1–D6 domain + H1–H7 hygiene). Default `claude-sonnet-4-6` (~$0.74/run; configurable to Haiku $0.37 or Opus $1.86 via `MODEL=`). Plan-review 3 iters; code-review 2 iters; live integration verified twice. 4 real bugs caught + fixed in-flight.
- **BDD suite shipped (Feature 1 of 3)** — PR #2 merged to master via `a811d67` (2026-04-23). 37 commits, +5953/-173. Pure `@cucumber/cucumber` v12.8.1 + `playwright` 1.59 + `tsx` 4.19. 33 scenarios / 287 steps across 11 `.feature` files. Backend gains `HANGMAN_WORDS_FILE` env-var + `backend/words.test.txt` for determinism. Plan-review 6 iters; code-review 2 iters. 2 latent cucumber-js bugs caught + fixed in-flight.

### Now

**Three-feature BDD methodology arc complete on master.** All artifacts shippable end-to-end:

```bash
make install && make backend && make frontend            # play locally
make backend-test && make frontend && make bdd          # 33/33 scenarios
make bdd-coverage                                        # branch coverage artifacts
make bdd-dashboard                                       # LLM-graded HTML w/ coverage context (needs ANTHROPIC_API_KEY)
```

No active feature. Worktree cleaned; on `master` at `0f2bac7`.

### Next

**Methodology arc continues.** Per the test-bed framing (memory: `project_test_bed.md`), Feature 4 candidates in priority order:

1. **`bdd-typed-domain` (Layer 0 — types eliminate)** — Pydantic-strict + narrow exception hierarchy + exhaustive `match` on session state. Refactor `routes.py:168-200` so the `IntegrityError` catch is provably correct (raise typed `RaceConflict` only). Cheap (~30 min) and directly closes the "D7-missed semantic bug" gap. Measure: branch count delta, route validation LOC deleted.
2. **`bdd-property-invariants` (Layer 2 — properties verify)** — Hypothesis invariants for game logic (`score >= 0`, `len(guessed) <= 26`) + `RuleBasedStateMachine` for full session journey (random `start/guess/forfeit/reload/start-new` sequences). Measure: invariants caught, shrunk repros.
3. **`bdd-mutation-dashboard` (Layer 6 — mutations validate)** — `mutmut run` on `backend/src/hangman/`. Surviving mutants flow into Feature 2 dashboard as new criterion **D8** ("mutant survived — intentional flexibility or missing test?"). Measure: mutation kill rate per file. **This is the methodology centerpiece** — validates Layers 0-5 aren't lying.

Pick via `/new-feature bdd-typed-domain` (or whichever).

---

## Open Questions

- What domain is the larger high-stakes system? (financial / medical / safety / security) — once known, fold domain-specific rubric criteria into the LLM grader (D9: invariant unspecified, D10: missing audit log, D11: missing recovery path).

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
