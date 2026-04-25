# PRD Discussion: bdd-branch-coverage

**Status:** In Progress
**Started:** 2026-04-24
**Participants:** KC, Claude

## Original user stories

None provided — feature was scoped during the Feature 2 (bdd-dashboard) PRD discussion as a follow-on. CONTINUITY.md captures the goal as:

> "call graph + per-branch coverage contexts + gap detection ... will replace Feature 2's tag-based coverage with call-graph-based branch coverage"

Feature 2's live smoke run revealed concrete pain points that motivate Feature 3:

- **Endpoint coverage card showed 0/0 Full** because the regex looked for `GET /api/...` literal strings but BDD scenarios use phrasing like `I request "/api/v1/categories"` — the HTTP method and path are rarely on the same line. Tag-based coverage misses real coverage signal.
- **No authoritative endpoint list.** Feature 2 scrapes Gherkin step text for endpoints; the actual route table from `backend/src/hangman/routes.py` is the ground truth and should drive coverage grading.
- **No per-line attribution.** A scenario that says "I POST /games and verify the response" doesn't surface which Python lines / branches / functions actually executed.
- **No gap detection.** "Which endpoints have ZERO scenarios touching them?" is currently impossible to answer because coverage grading treats absence of mention as the same as untested.

## Hypothesized user stories (to refine in this discussion)

- **US-001 (gap detection):** As a developer, I want to see which endpoints + functions in `backend/src/hangman/` have **zero BDD coverage** so I can write missing scenarios.
- **US-002 (per-scenario attribution):** As a developer, I want each BDD scenario card on the dashboard to show **which backend lines/branches/functions** that scenario actually executed, so I can understand what's tested and what's not.
- **US-003 (branch coverage):** As a developer, I want **per-branch** coverage (not just per-line) — `if/else`, `try/except` branches — from the BDD run, so I can identify untested paths inside otherwise-touched functions.
- **US-004 (call graph):** As a developer, I want to see the **call graph** for each endpoint handler — which functions get called, transitively — so I can reason about whether my scenario actually covered the interesting code paths.
- **US-005 (dashboard integration):** As a developer, I want this coverage data **merged into the Feature 2 dashboard** so I have one place to review BDD quality. Specifically: replace Feature 2's tag-based "Endpoint coverage 0/0" card with real route-table-based coverage.

## Discussion log

### Round 1 — 2026-04-24

**Q1 (coverage approach):** **(c) Both** — static call-graph for endpoint enumeration + reachability; dynamic `coverage.py --contexts` for actual hits.

**Q2 (scope):** **(c) Backend now** with structured forward-compat for frontend later (so the data model + dashboard surface anticipates frontend coverage attaching).

**Q3 (attribution):** **REFRAMED — I had the unit wrong.**

> User: "Don't evaluate the coverage based on the BDD files. Analyze the call graph of the hangman application code at each route and make sure the BDD tests cover the code paths."

The unit of analysis is **app code paths**, not BDD scenarios. The pipeline is:

1. **Enumerate routes** from `backend/src/hangman/routes.py` (authoritative — replaces Feature 2's regex scrape).
2. For each route handler, **walk the static call graph** through `backend/src/hangman/` to enumerate every reachable function + branch.
3. Run the BDD suite with `coverage.py` instrumentation and **record which lines/branches got hit** during the run.
4. For each enumerated code path, ask: **"is there at least one BDD scenario that exercised this branch?"** Boolean.
5. Output: **gap list** — branches with zero BDD coverage. The dashboard shows "endpoint X has N branches, M covered, K uncovered (here they are)."

This is materially different from Feature 2's tag-based grading and from my Q3 framing of "per-scenario vs per-feature attribution." It's an APP-CODE-CENTRIC view, not a scenario-centric view.

**Q3-NEW (granularity):** **(d) Mix** — branch as the primary rigorous metric (`coverage.py --branch`); function-level rollup for the dashboard summary card so we don't drown in 200+ uncovered-branch findings.

**Q4 (output):** **(b) New tool at `backend/tools/branch_coverage/`** emitting its own report.

**Q5 (Make target):** **Opt-in.** Standalone `make bdd-coverage` (or similar) target. Default `make bdd` stays uninstrumented and fast.

**Q6 (boundary):** **`backend/src/hangman/` source files only.** Stop at any external import (SQLAlchemy ORM calls, stdlib, FastAPI internals are all out of scope).

**Q7 (threshold):** **Percentage with threshold.** Note: the percentage is "% of app code paths covered by the BDD suite as a whole" — an app-code-centric metric (not "scenario X covered Y%").

**Q8 (slowdown):** OK; **but instrumented vs non-instrumented runs MUST be flagged distinctly** — a coverage-instrumented `cucumber.ndjson` should not be confused with a regular `make bdd` artifact.

**Q9 (Feature 2 card):** **Augment.** Keep Feature 2's tag-based "Endpoint coverage" card; add a new "Code coverage" card sourced from Feature 3.

**Q10 (LLM coverage-aware):** **Yes.** The LLM evaluator should see per-endpoint uncovered-branch data so its findings can be coverage-aware ("scenario hits this endpoint but never exercises the `INVALID_LETTER` branch").

### Round 2 — 2026-04-24

**Q11 (attribution):** **(a) Aggregate.** `coverage.py` runs once over the whole BDD suite; we record "branches covered by SOMETHING in the BDD." No Cucumber→backend handshake. Per-scenario contexts deferred — aggregate is sufficient for endpoint-level gap detection and the LLM's per-endpoint coverage view.

**Q12 (threshold):** **Red / Yellow / Green at < 50% / 50-80% / ≥ 80%** code path coverage.

**Q13 (instrumented-run flag):** **(c) Both.** Distinct artifact filename (`cucumber.coverage.ndjson` for instrumented runs) AND a banner on the rendered report.

**Q14 (output format):** **(c) Both.** JSON artifact for Feature 2's dashboard to consume + standalone HTML for direct viewing of the coverage report.

**Q15 (static call-graph accuracy):** **Best effort for now.** The dynamic `coverage.py` data is the source of truth for what actually executed; static enumeration is the "what _should_ be reachable from this route" hypothesis. May tighten static accuracy later if the false-positive rate is a problem.

---

## Refined understanding

### Personas

- **Developer** (single persona, shared with Feature 2). Runs `make bdd-coverage`, opens the standalone HTML report or sees the augmented "Code coverage" card in Feature 2's dashboard.

### User stories (refined)

- **US-001 (gap detection):** As a developer, I want to see **per-endpoint** code-path coverage with red/yellow/green status so I can identify which endpoints have under-tested code paths.
- **US-002 (uncovered branches list):** As a developer, I want to see **the specific branches/functions** that no BDD scenario exercises, so I can write missing scenarios.
- **US-003 (route enumeration from source of truth):** As a developer, I want endpoints enumerated from `routes.py` (not regex-scraped from Gherkin), so coverage grading reflects the actual API surface.
- **US-004 (call graph + dynamic coverage):** As a developer, I want **static call-graph reachability** (best-effort) combined with **dynamic `coverage.py` --branch** data to identify uncovered code paths reachable from each route handler.
- **US-005 (Feature 2 dashboard augmentation):** As a developer, I want a new "Code coverage" card on Feature 2's dashboard, populated from Feature 3's JSON artifact, alongside the existing tag-based card.
- **US-006 (LLM coverage-awareness):** As a developer, I want Feature 2's LLM evaluator to see per-endpoint uncovered-branch data so its findings can flag scenarios that hit an endpoint without exercising key branches.
- **US-007 (instrumented run flagging):** As a developer, I want instrumented BDD runs to produce distinctly-named artifacts (`cucumber.coverage.ndjson`) AND a banner on the rendered report, so I never confuse instrumented runs with regular `make bdd` runs.
- **US-008 (opt-in target):** As a developer, I want `make bdd-coverage` to be a separate, opt-in target so the default `make bdd` stays fast.

### Non-goals

- ❌ Frontend (TypeScript/Playwright) coverage — deferred to a future feature; the data model and dashboard surface anticipates frontend attaching later (forward-compat per Q2c).
- ❌ Per-scenario branch attribution — only aggregate "BDD suite covered branch X" (Q11a). Per-scenario contexts may be added later if coverage-aware findings need to call out specific scenarios.
- ❌ 100% accurate static call-graph — best-effort only (Q15). FastAPI's decorator-based route registration + dynamic dispatch make perfect static analysis costly.
- ❌ Coverage of SQLAlchemy ORM internals, stdlib, FastAPI internals — boundary stops at non-`backend/src/hangman/` imports (Q6).
- ❌ Replacing Feature 2's tag-based "Endpoint coverage" card — augment, not replace (Q9).
- ❌ Always-on instrumentation in `make bdd` — opt-in via `make bdd-coverage` (Q5/Q8).

### Key decisions

- **Tool stack:** static call-graph analysis (likely `pyan3` or `pycg` — research phase will pick) + `coverage.py --branch` for dynamic line/branch hit tracking.
- **Output location:** `backend/tools/branch_coverage/` (separate package from Feature 2's `backend/tools/dashboard/`).
- **Make target:** opt-in `make bdd-coverage` (parallel to `make bdd-dashboard`).
- **Boundary:** walk only into `backend/src/hangman/`; stop at external imports.
- **Thresholds (red/yellow/green):** < 50% / 50-80% / ≥ 80% code-path coverage per endpoint.
- **Artifacts:**
  - `frontend/test-results/cucumber.coverage.ndjson` — instrumented BDD run output (distinct from `cucumber.ndjson`)
  - `tests/bdd/reports/coverage.html` — standalone Feature 3 HTML dashboard
  - `tests/bdd/reports/coverage.json` — JSON artifact consumed by Feature 2's augmented "Code coverage" card
  - All under existing gitignored `tests/bdd/reports/` directory
- **Banner on instrumented reports:** "This run used coverage instrumentation; performance metrics are not representative."
- **Granularity for dashboard:** function-level rollup as the summary metric; branch-level detail in drill-down.
- **Aggregate coverage:** the BDD suite as a whole produces one coverage profile; no per-scenario attribution.
- **Feature 2 integration mechanics:** Feature 2's `LlmEvaluator` reads `coverage.json` (when present) and embeds per-endpoint uncovered-branch data into each scenario package's prompt content.

### Open questions (remaining — to resolve in design / research phase)

- [ ] **Static-analysis tool choice** — `pyan3` vs `pycg` vs alternative. The Phase 2 `research-first` agent will compare current docs / accuracy on FastAPI codebases.
- [ ] **JSON schema for `coverage.json`** — design phase will specify the exact contract Feature 2 reads.
- [ ] **Whether `make bdd-coverage` re-runs the BDD suite or shares output with `make bdd`** — likely re-run since the cucumber.ndjson filename differs and instrumentation costs ~10-30%.

---

**Status: Complete.** Ready for `/prd:create bdd-branch-coverage`.

## Targeted questions

### Tooling

**Q1 — Coverage tool.** The Python ecosystem standard is `coverage.py` with `--contexts` (per-test attribution; each test labels coverage data). When Cucumber.js drives the BDD run, the backend is a separate process — `coverage.py` would need to be enabled in the backend's startup wrapper, and a mechanism exists to label hits with the current scenario. Two viable approaches:

- **(a) Dynamic via coverage.py contexts.** Wrap `uvicorn` with `coverage run --context=$SCENARIO_ID …`. Use a header / cookie to communicate the active scenario from the Cucumber side to the backend. Get true execution data — scenario X really did execute lines Y, Z.
- **(b) Static via call-graph analysis.** Use `pyan3` or `pycg` to build the static call graph of `backend/src/hangman/`. Map each scenario's URL to a route handler, then walk the call graph from that handler. Coarser — doesn't reflect actual branch outcomes — but fast and offline.
- **(c) Both.** Static call graph for endpoint enumeration + handler reachability; dynamic `coverage.py` contexts for actual per-scenario line/branch attribution.

Which direction? My instinct is **(c)** — static gives the authoritative endpoint list (replacing Feature 2's regex scrape); dynamic gives true per-scenario attribution (which is the load-bearing signal for the dashboard).

### Scope

**Q2 — Backend only or backend + frontend?** The BDD suite has both API scenarios (e.g., `categories.feature`) and UI scenarios (`play-round.feature` via Playwright). For frontend coverage you'd need V8/c8 instrumentation under Playwright, which is a separate stack. Backend-only is simpler. Options:

- **(a) Backend Python only.** Frontend coverage deferred to a future feature.
- **(b) Backend + frontend.** Cover both via separate tools (`coverage.py` + `c8`).
- **(c) Backend now + a structured story about how frontend would attach later** (so the data model and dashboard surface anticipates it).

**Q3 — Per-scenario or per-feature attribution?** Feature 2 packages BOTH scenarios and features for LLM evaluation. For coverage attribution: do we attribute lines/branches per **scenario** (33 contexts in this suite) or per **feature** (11 contexts) or both?

### Output / integration

**Q4 — Standalone tool or extension of Feature 2?** Two routes:

- **(a) Extend `backend/tools/dashboard/`** with a `coverage_grader.py` module that replaces the current tag-based `coverage.py`. The same `dashboard.html` shows real coverage. `make bdd-dashboard` runs the coverage instrumentation as a side-effect of `make bdd`.
- **(b) New top-level tool** at `backend/tools/branch_coverage/` that emits its own report (`tests/bdd/reports/coverage.html`?) — Feature 2's dashboard reads it as input.
- **(c) New tool that emits a JSON artifact**, Feature 2's dashboard consumes it.

**Q5 — Make target.** Always-on (every `make bdd` runs with coverage instrumentation, producing one artifact) vs. opt-in (`make bdd-coverage` is a separate target that re-runs the suite under instrumentation, accepting 2× time)?

### Gap definition

**Q6 — What counts as "uncovered"?** Multiple definitions are valid:

- **Endpoint level:** route in `routes.py` with zero scenarios hitting it.
- **Function level:** function in `backend/src/hangman/` with zero hits across all scenarios.
- **Line level:** lines never executed.
- **Branch level:** branch (if/else, try/except, raise paths) never taken.

Which of these does the dashboard surface? My suggestion: all four, with a layered drill-down (endpoint → function → line/branch).

**Q7 — Threshold.** Is "5% coverage" treated as covered or uncovered? Boolean (any-hit-counts) or percentage-with-threshold?

### Performance

**Q8 — Acceptable BDD slowdown.** `coverage.py` instrumentation typically adds 10-30% to Python execution time. For our suite (currently ~60s for `make bdd`), that's ~70-80s. Acceptable, or do we need a fast path that skips instrumentation by default?

### Feature 2 dashboard integration

**Q9 — Replace or augment Feature 2's coverage card?** Currently Feature 2's "Endpoint coverage" card shows 0/0 Full because the regex misses the BDD phrasing. If Feature 3 lands, do we:

- **(a) Replace** — Feature 3 owns the endpoint coverage card; Feature 2's regex code goes away.
- **(b) Augment** — Feature 2's tag-based grade stays as a high-level signal; Feature 3 adds a separate "Code coverage" card.
- **(c) Replace + add new sections** — endpoint coverage card uses Feature 3's data; a new "Per-function coverage" section appears.

**Q10 — LLM evaluation of coverage data?** Feature 2's LLM evaluator looks at scenario text only. Should it ALSO see the per-scenario coverage data ("this scenario only exercised the happy path of `validate_letter`, never hit the `INVALID_LETTER` branch") so its findings are coverage-aware?

---

## Refined understanding (will be filled in as we converge)

### Personas

(TBD)

### User Stories (Refined)

(TBD)

### Non-Goals

(TBD)

### Key Decisions

(TBD)

### Open Questions (Remaining)

(TBD)
