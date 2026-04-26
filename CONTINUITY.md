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

- **BDD Branch Coverage built (Feature 3 of 3)** — branch `feat/bdd-branch-coverage`, ~25 commits since master, +4322/-71 LOC. Python tool at `backend/tools/branch_coverage/`: reflective FastAPI route enumeration → pyan3 call-graph → BFS reachability → coverage.py instrumentation with per-endpoint contexts via `CoverageContextMiddleware` → line-granularity grader + audit reconciliation → JSON/HTML emitter. Augments Feature 2 dashboard with new "Code coverage" card + LLM rubric criterion D7 ("Missed coverage opportunity"). Full workflow: PRD v1.0 + research brief + design spec v1.0, **plan-review loop PASSED in 16 iterations** (~30 P1 + ~25 P2 patched, 5 codebase-grounding fixes, source-line-vs-arc-id pivot, middleware route-matching, branch-line filtering), subagent-driven TDD (17 tasks; A3 spike caught 2 P1 API drifts; H1 live smoke caught 2 production bugs), /simplify (-36 LOC: 2 P1 efficiency wins + 1 P2 dedup + 2 P3 nits), **code-review loop PASSED in 7 iterations** (Codex + PR Toolkit verdict-agree clean). 303 unit tests + 67 integration tests + 33/33 BDD scenarios under instrumentation. Audit: coverage.py=36 / enumerated=22 / reconciled=True / 97.2% (35/36 branches covered). Smoke-tested with synthetic uncovered branch — Feature 3 correctly flagged 0/2 reached + file:line + condition_text.
- **BDD Dashboard shipped (Feature 2 of 3)** — PR #3 merged to master via `0bfe6ba` (2026-04-24). 23 commits, +10885/-3 LOC. Python tool at `backend/tools/dashboard/`: parses `cucumber.ndjson`, packages 33 scenarios + 11 features into ~44 LLM calls (Anthropic SDK, forced `ReportFindings` tool use, prompt caching ~90%), renders single-file HTML via Jinja2. 12 modules / 99 tests / 13-criterion rubric (D1–D6 domain + H1–H7 hygiene). Default `claude-sonnet-4-6` (~$0.74/run measured; configurable to Haiku $0.37 or Opus $1.86 via `MODEL=`). Full workflow: PRD v2.0 + research brief + 13-section design + 14-task plan, **plan-review loop PASSED in 3 iterations**, subagent-driven TDD (9 dispatch waves), /simplify (1×P1 + 6×P2 + 4×P3 fixed), **code-review loop PASSED in 2 iterations** (Codex + PR Review Toolkit verdict-agree clean), live integration verified twice ($0.74, 90→93% cache hit). 4 real bugs caught + fixed in-flight.
- **BDD suite shipped (Feature 1 of 3)** — PR #2 merged to master via `a811d67` (2026-04-23). 37 commits, +5953/-173. Pure `@cucumber/cucumber` v12.8.1 + `playwright` 1.59 + `tsx` 4.19. 33 scenarios / 287 steps across 11 `.feature` files. Backend gains `HANGMAN_WORDS_FILE` env-var + `backend/words.test.txt` for determinism. Full workflow: PRD v1.2 + 11-section design + 23-task plan, plan-review 6 iters, subagent-driven TDD, /simplify, code-review 2 iters. 2 latent cucumber-js bugs caught + fixed in-flight.

### Now

**Feature 3 build complete; awaiting push + PR.** Branch `feat/bdd-branch-coverage` is green: 303 unit + 67 integration tests pass; ruff + mypy clean; 33/33 BDD scenarios under instrumentation; audit reconciled=True. Live in worktree at `.worktrees/bdd-branch-coverage`. Playable via `make install && make backend && make frontend`; new commands: `make backend-coverage` (T1) + `make frontend` (T2) + `make bdd-coverage` (T3) regenerates `tests/bdd/reports/coverage.{json,html}` and triggers Feature 2's augmented dashboard via `make bdd-dashboard`.

### Next

`git push -u origin feat/bdd-branch-coverage` → `gh pr create` to main. After PR merge, run `/finish-branch` to clean up worktree + delete remote branch + restart dev servers from main. The 3-feature BDD plan (suite + dashboard + branch coverage) is then complete.

---

## Workflow

> Updated automatically by `/new-feature` and `/fix-bug` commands.
> The Stop hook reminds you of the current phase on every response.
> The PreToolUse hook blocks commit/push/PR if quality gates are incomplete.
> Delete this section when no workflow is active (or set Command to `none`).

| Field     | Value                                                              |
| --------- | ------------------------------------------------------------------ |
| Command   | /new-feature bdd-branch-coverage                                   |
| Phase     | 5 → 6 — Code review loop PASSED at iter 7; running /simplify next  |
| Next step | Push branch → create PR (review loop + simplify + verify all PASS) |

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
- [x] Plan review loop (16 iterations) — **PASSED at iter 16: Claude CLEAN + Codex CLEAN on same pass.** Total: ~30 P1s + ~25 P2s patched across 16 iterations. Major findings included: source-line vs arc-id matching pivot (iter 6); audit math + extra_coverage line-granularity consistency (iter 4-7); D1 middleware route-matching via `request.app.router.routes` (iter 6); D3 branch-line filtering at loader (iter 8); H1 Step 7b path-format invariant + positive/negative attribution checks (iter 5, 8); 5 codebase-grounding fixes (iters 10-11, 15) replacing fictitious symbols (`hangman.routes.create_game`, `new_game`, `_by_category`, `/forfeit` route, `features_glob: str`) with real ones (`start_game`, `WordPool.random_word`, `self.categories`, `features_glob: Path`); design spec §14 supersedes appendix (iter 7).
- [ ] TDD execution complete
- [x] Code review loop (7 iterations) — PASSED. Iter 1 (Codex + code-reviewer + silent-failure-hunter): 4 P1 + 5 P2 patched in `31c7824` (Reachability class-method resolution; `_build_coverage_context` schema-mismatch; Makefile `coverage combine` wrapper; bad-timestamp logging; RouteEnumerator framework-route filter; log-additions across middleware/reachability/callgraph/**main**). Iter 2: 1 P1 in `2e8cdcf` (scalar coercion). Iter 3: 1 P2 in `005a868` (`_strict_bool`). Iter 4: documentation in `e5d0325` (refuted Codex's `context=base` proposal with empirical evidence). Iter 5: 1 P1 in `762b36e` (`uncovered_branches_flat` element validation). Iter 6: 1 P2 in `f225c2c` (`_walk_skip_nested` for nested-def isolation). Iter 7: BOTH reviewers CLEAN.
- [x] Simplified (commit `aa7647d`) — 3 reviewers (code-reuse, code-quality, efficiency) ran post-Phase-5. Applied 2 P1 efficiency wins (Reachability per-qualname memoization eliminates O(E×R) re-parsing → O(R+E); CoverageDataLoader lifts `set_query_contexts` out of inner loop O(F·C) → O(C)) + 1 P2 dedup (Grader.grade computes `enumerated_reachable_lines` + `in_scope_files` + `all_hit_lines_in_scope` ONCE, passes into `_extra_coverage`/`_audit`/`_totals`) + 2 P3 nits (lazy datetime import → module-level; TOCTOU `if exists()` → try/except FileNotFoundError). Deleted dead `_arcs_for_context` helper. Net -36 LOC.
- [x] Verified (tests/lint/types) — 303 unit pass, 67 integration pass, ruff clean, mypy clean (28 source files). Verdict: APPROVED via verify-app agent.
- [x] E2E use cases designed — N/A: Feature 3 is a developer-only analyzer tool (`make bdd-coverage`); no end-user-facing UI/API changes. The BDD suite IS the input to the tool, not a UC the tool exposes. Verified by H1 live smoke (33/33 BDD scenarios under instrumentation).
- [x] E2E verified — N/A: developer-only tool (no user-facing surface). H1 commit `87837ab` ran the existing 33-scenario BDD suite under instrumentation against a real backend, asserted 4 load-bearing checks: path-format invariant, positive `/guesses` credits apply_guess, negative `/categories` doesn't reach apply_guess, audit reconciled=True.
- [x] E2E regression passed — N/A: same justification (no user-facing surface; existing BDD suite still 33/33 under instrumentation).
- [x] E2E use cases graduated to tests/e2e/use-cases/ — N/A
- [x] E2E specs graduated to tests/e2e/specs/ — N/A: Playwright framework not installed for this project's BDD-driven model.
- [x] Learnings documented (if any) — coverage.py 7.13.5 buffer-flush bug + workaround documented in `middleware.py` module docstring (Reset trade-off section); A3 spike pyan3/coverage.py API findings documented in design spec §14 Plan-Review Pivots appendix; symbol-name codebase grounding documented in design spec §14.5.
- [x] State files updated — CONTINUITY.md (this file) + docs/CHANGELOG.md (commit `35baa7b` + H1 commit `87837ab`).
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
