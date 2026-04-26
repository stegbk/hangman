# PRD: BDD Branch Coverage

**Version:** 1.0
**Status:** Draft
**Author:** Claude + KC
**Created:** 2026-04-24
**Last Updated:** 2026-04-24

---

## 1. Overview

A developer-only tool that measures **what app code paths the BDD suite actually exercises**, not what the BDD scenarios say they cover. Walks the static call-graph of `backend/src/hangman/` from each FastAPI route handler to enumerate reachable branches, runs the BDD suite under `coverage.py --branch` instrumentation to record which of those branches actually executed, and reports per-endpoint code-path coverage with red/yellow/green thresholds. Replaces Feature 2's regex-based endpoint scrape (which produced "Endpoint coverage 0/0 Full") with a route-table-driven, app-code-centric view of test coverage. Augments Feature 2's dashboard with a new "Code coverage" card and feeds per-endpoint uncovered-branch data into Feature 2's LLM evaluator so its findings can be coverage-aware. Standalone HTML report also produced for direct viewing.

## 2. Goals & Success Metrics

### Goals

- **Primary:** Surface code paths in `backend/src/hangman/` that no BDD scenario exercises, so developers can write missing scenarios.
- **Secondary:** Replace Feature 2's regex-scraped endpoint enumeration with the authoritative route table from `routes.py`.
- **Tertiary:** Make Feature 2's LLM evaluator coverage-aware so it can flag scenarios that hit an endpoint without exercising key branches.

### Success Metrics

| Metric                               | Target                                                               | How Measured                                                                                         |
| ------------------------------------ | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Endpoint enumeration accuracy        | 100% of routes in `routes.py` listed                                 | Count `app.include_router` + `@router.<method>` decorations vs. coverage report's endpoint count     |
| Per-endpoint coverage report renders | All 7+ endpoints show red/yellow/green                               | Open `coverage.html`, every endpoint has a tone-tagged card                                          |
| Uncovered-branch drill-down works    | Click endpoint → see branch list                                     | Manual smoke; report has expandable sections per endpoint                                            |
| Feature 2 augmentation lands         | New "Code coverage" card appears                                     | Run `make bdd-coverage` then `make bdd-dashboard`; verify `dashboard.html` has the new card          |
| LLM evaluator receives coverage data | Each scenario package mentions covered endpoint's uncovered branches | Inspect Feature 2's `Packager` output; coverage data appears in `prompt_content`                     |
| Instrumented runs distinctly flagged | Filename + banner present                                            | `cucumber.coverage.ndjson` exists; `coverage.html` shows the banner                                  |
| BDD suite runs with instrumentation  | `make bdd-coverage` exits 0                                          | Run on the existing 33-scenario suite; cucumber.coverage.ndjson + coverage.json + coverage.html emit |
| Slowdown vs. uninstrumented          | ≤ 50% wall-clock increase                                            | `time make bdd` vs. `time make bdd-coverage`; targeting ≤ 50% (10-30% typical for coverage.py)       |

### Non-Goals (Explicitly Out of Scope)

- ❌ **Frontend (TypeScript/Playwright) coverage.** Backend Python only. The data model + dashboard surface anticipates frontend attaching later.
- ❌ **Per-scenario branch attribution.** Aggregate coverage only — "the BDD suite covered branch X" not "scenario Y covered branch X." Per-scenario contexts may be a future feature.
- ❌ **100% accurate static call-graph.** Best-effort. FastAPI's decorator-based dynamic dispatch makes perfect static analysis costly; `coverage.py` is the source of truth for what actually executed.
- ❌ **Coverage of SQLAlchemy ORM internals, stdlib, FastAPI internals.** Walk stops at any non-`backend/src/hangman/` import.
- ❌ **Replacing Feature 2's tag-based "Endpoint coverage" card.** Augment with a new "Code coverage" card; the tag-based card stays as a separate signal.
- ❌ **Always-on instrumentation in `make bdd`.** Opt-in via `make bdd-coverage`. Default `make bdd` stays fast and uninstrumented.
- ❌ **CI/CD integration, scheduled coverage reports, Slack/Teams push.** Local developer tool only.
- ❌ **Coverage trend tracking over time.** Feature 2 already has a history mechanism; if needed, Feature 3 can later append to that. Not in MVP.
- ❌ **Test suite recommendation engine.** This tool reports gaps; it does not generate scenarios. (LLM evaluation in Feature 2 surfaces the gaps to developers in plain language; Feature 4 might generate.)

## 3. User Personas

### Developer (single persona, shared with Feature 2)

- **Role:** Local developer working on the Hangman backend or BDD suite.
- **Permissions:** Full read/write on the worktree.
- **Goals:**
  - Identify endpoints + functions whose code paths aren't exercised by the BDD suite.
  - Write missing scenarios to close coverage gaps.
  - See coverage data alongside Feature 2's quality findings in one dashboard.

## 4. User Stories

### US-001: See per-endpoint code-path coverage at a glance

**As a** developer
**I want** the standalone coverage report to show every endpoint with a red/yellow/green tag based on how much of its reachable code is covered by the BDD suite
**So that** I can spot at a glance which endpoints have under-tested code paths

**Scenario:**

```gherkin
Given the BDD suite has run with coverage instrumentation
When I open tests/bdd/reports/coverage.html
Then every endpoint registered in backend/src/hangman/routes.py appears as a card
And each card shows a coverage percentage with a red/yellow/green tone
And the threshold is red < 50%, yellow 50-80%, green ≥ 80% of reachable branches covered
```

**Acceptance Criteria:**

- [ ] Every route registered via `@app.get/post/...` or `@router.get/post/...` in `backend/src/hangman/routes.py` produces one card.
- [ ] Each card shows: HTTP method + path, percentage of reachable branches covered, and a tone class (`success` / `warning` / `error`).
- [ ] Thresholds: `< 50%` → red, `50% to < 80%` → yellow, `≥ 80%` → green.
- [ ] An endpoint with zero reachable branches (degenerate handler) shows "N/A" rather than 0% red — distinguish "untestable" from "untested."

**Edge Cases:**
| Condition | Expected Behavior |
|---|---|
| Route handler is a one-line `return {...}` (no branches) | Render "N/A — no branches to cover" |
| Route includes a path parameter that's never exercised in tests | Still enumerate; show 0% red if its handler has branches |
| Route is dynamically registered (impossible to detect statically) | Best-effort; absence is not a fatal error — log a warning |

**Priority:** Must Have

---

### US-002: Drill down to specific uncovered branches and functions

**As a** developer
**I want** to expand each endpoint card and see the exact functions and branches that no scenario exercises
**So that** I can write a scenario targeted at the gap

**Scenario:**

```gherkin
Given coverage.html has rendered for the current BDD run
When I click an endpoint card with yellow status
Then I see a list of functions called transitively from that route handler
And each function shows percentage covered + line numbers of uncovered branches
And uncovered branches are quoted from source with file:line references
```

**Acceptance Criteria:**

- [ ] Each endpoint card expands to show all reachable functions in `backend/src/hangman/`.
- [ ] Functions are grouped by source file (e.g., `game.py`, `words.py`).
- [ ] For each uncovered branch: file path, line number, source snippet (the `if` condition + the not-taken arm).
- [ ] If a function is reachable per the static call-graph but never executed under any scenario, mark it as 0% covered — but distinguish from "not reachable" (which means the static graph couldn't link it).
- [ ] The drill-down is the same data that gets emitted as `coverage.json` for Feature 2 to consume.

**Edge Cases:**
| Condition | Expected Behavior |
|---|---|
| A function is reachable from multiple endpoints | Listed under each endpoint that reaches it |
| Static analysis missed a callee (e.g., FastAPI `Depends`) but coverage.py recorded it as hit | Show in drill-down only if the static graph linked it; otherwise it appears under "extra coverage" |
| Coverage data is missing for a function that the static graph claims reachable | Render as 0% (treated as uncovered) |

**Priority:** Must Have

---

### US-003: Authoritative endpoint enumeration

**As a** developer
**I want** endpoints enumerated from `routes.py` (the FastAPI route registration), not regex-scraped from Gherkin step text
**So that** coverage grading reflects the actual API surface, not how scenarios happen to phrase their URLs

**Scenario:**

```gherkin
Given backend/src/hangman/routes.py defines POST /api/v1/games and GET /api/v1/games/{id}
When I run make bdd-coverage
Then the report enumerates exactly those routes
And no route is omitted because the BDD scenarios use phrasing the regex doesn't recognize
```

**Acceptance Criteria:**

- [ ] Endpoints are extracted by static analysis of `routes.py` (AST or by importing the FastAPI app and reading `app.routes`).
- [ ] All HTTP methods (GET, POST, PATCH, PUT, DELETE) are detected.
- [ ] Path parameters (`{id}`, `{category}`) are preserved in the canonical endpoint label.
- [ ] No regex-scraping of Gherkin step text — that approach is out of scope (it's what Feature 2 does and Feature 3 replaces it for code-coverage purposes).

**Edge Cases:**
| Condition | Expected Behavior |
|---|---|
| Multiple routers (`app.include_router(...)`) | All routers are walked; their routes appear |
| WebSocket routes (`@app.websocket(...)`) | Out of scope for v1 (no WS in Hangman); document non-support and skip silently |
| `prefix=` argument on routers | Path prefix correctly prepended to each route |

**Priority:** Must Have

---

### US-004: Combined static call-graph + dynamic coverage data

**As a** developer
**I want** the tool to combine **static** reachability analysis (which functions could be called from each handler) with **dynamic** `coverage.py --branch` data (which branches actually executed)
**So that** I see both "this handler should call function X" and "scenario actually executed function X"

**Scenario:**

```gherkin
Given the static call-graph identifies game.guess_letter() as reachable from POST /api/v1/games/{id}/guesses
And the BDD suite ran with coverage instrumentation
When the report is generated
Then the endpoint card shows guess_letter() as a contributing function
And shows which branches of guess_letter() were executed (e.g., happy path) vs. not (e.g., INVALID_LETTER raise)
```

**Acceptance Criteria:**

- [ ] Tool runs static analysis on import (no run-time penalty for the BDD suite itself).
- [ ] Static call-graph tool is best-effort; if it fails on a function, log a warning and continue (don't block the report).
- [ ] `coverage.py --branch` is the source of truth for "did this execute"; static graph is the hypothesis for "should it have executed."
- [ ] If coverage.py records a hit on a function that the static graph DIDN'T link to any endpoint, report it as "extra coverage — not reachable per static analysis" with a soft warning. (This signals the static graph is incomplete or there's instrumentation overlap with non-BDD test code.)

**Edge Cases:**
| Condition | Expected Behavior |
|---|---|
| Static graph misses a callee, dynamic coverage hits it | Reported under "extra coverage" — the gap is in static analysis, not in tests |
| Static graph claims reachable, no coverage hits | 0% covered branch — surfaces the gap |
| FastAPI `Depends(...)` injection chains | Best-effort; if static analysis misses them, note in open questions for design phase |

**Priority:** Must Have

---

### US-005: Feature 2 dashboard augmentation

**As a** developer
**I want** a new "Code coverage" card on Feature 2's dashboard, populated from Feature 3's `coverage.json` artifact
**So that** I have one place to see both BDD quality findings (Feature 2) and code-coverage gaps (Feature 3)

**Scenario:**

```gherkin
Given Feature 2's dashboard has been built (`make bdd-dashboard`)
And Feature 3 has produced tests/bdd/reports/coverage.json from a prior `make bdd-coverage` run
When the dashboard renders
Then a new "Code coverage" card appears alongside the existing "Endpoint coverage" tag-based card
And the new card shows the overall percentage + endpoints that are red
And clicking the card opens the standalone coverage.html for the drill-down
```

**Acceptance Criteria:**

- [ ] If `coverage.json` exists at dashboard build time, Feature 2 reads it and renders the new card.
- [ ] If `coverage.json` is missing or stale (older than the cucumber.ndjson), Feature 2 shows a placeholder card: "Code coverage data not available — run `make bdd-coverage`."
- [ ] The existing tag-based "Endpoint coverage" card remains unchanged.
- [ ] The card links to the standalone `coverage.html` (Feature 2 dashboard remains a single-file artifact; the link is a `file://` reference relative to `tests/bdd/reports/`).

**Edge Cases:**
| Condition | Expected Behavior |
|---|---|
| `coverage.json` exists but cucumber.ndjson is from a different run | Show banner: "Coverage data may not match scenario run" |
| `coverage.json` schema mismatches (older Feature 3 version) | Render the placeholder; log a warning to stderr |
| `coverage.json` missing entirely | Render the placeholder with a "How to enable" link to README |

**Priority:** Should Have (depends on Feature 2 contract)

---

### US-006: LLM coverage-aware findings

**As a** developer
**I want** Feature 2's LLM evaluator to see per-endpoint uncovered-branch data when present
**So that** its findings can call out scenarios that hit an endpoint without exercising key branches (e.g., "scenario hits POST /guesses but never triggers the INVALID_LETTER raise path")

**Scenario:**

```gherkin
Given Feature 3 has produced coverage.json with per-endpoint uncovered branches
When Feature 2's LlmEvaluator builds a scenario package for a scenario that hits POST /guesses
Then the package's prompt_content includes a "Coverage data for hit endpoints" section
And the LLM may emit findings that reference specific uncovered branches by file:line
```

**Acceptance Criteria:**

- [ ] Feature 2's `Packager` reads `coverage.json` (when present) and embeds per-endpoint uncovered-branch lists into each scenario package's `prompt_content`.
- [ ] The rubric (Feature 2's `RUBRIC_TEXT`) gains a new criterion (D7?) that allows the LLM to surface coverage-driven findings.
- [ ] When `coverage.json` is missing, packages render without the coverage section — the LLM falls back to its non-coverage rubric (existing behavior).
- [ ] Coverage data is OPTIONAL; Feature 2 must continue to work without it.

**Edge Cases:**
| Condition | Expected Behavior |
|---|---|
| Scenario doesn't hit any endpoint with uncovered branches | No coverage section in the package |
| Multiple scenarios hit the same endpoint | All packages get the same uncovered-branch summary |
| `coverage.json` is large (e.g., 100+ uncovered branches) | Truncate to top-N most-egregious or top-level summary; document the limit |

**Priority:** Should Have

---

### US-007: Distinct flagging for instrumented runs

**As a** developer
**I want** instrumented BDD runs to produce distinctly-named artifacts AND a banner on rendered reports
**So that** I never confuse instrumented runs (slower, with coverage data) with regular `make bdd` runs

**Scenario:**

```gherkin
Given I ran make bdd-coverage
When I look at frontend/test-results/
Then I see cucumber.coverage.ndjson (NOT cucumber.ndjson)
And the standalone coverage.html shows a banner:
  "This run used coverage instrumentation. Performance metrics in this report are not representative of normal runs."
```

**Acceptance Criteria:**

- [ ] Instrumented BDD output goes to `frontend/test-results/cucumber.coverage.ndjson`, NOT `cucumber.ndjson`.
- [ ] The standalone `coverage.html` shows a yellow/info banner at the top calling out instrumentation.
- [ ] If a developer accidentally points Feature 2's dashboard at the instrumented NDJSON, Feature 2's dashboard shows the same banner ("This dashboard was built from instrumented data; cost numbers are still valid but timing data is not").
- [ ] `coverage.json` includes a `"instrumented": true` field as a machine-readable flag.

**Edge Cases:**
| Condition | Expected Behavior |
|---|---|
| Dev runs `make bdd-coverage` then `make bdd` (overwriting cucumber.ndjson) | The instrumented `cucumber.coverage.ndjson` is preserved (different filename) |
| Dev runs `make bdd-coverage` twice | The second run overwrites the first's coverage artifacts (acceptable; this is a dev tool) |
| Feature 2's dashboard reads `cucumber.coverage.ndjson` instead of `cucumber.ndjson` | Banner appears + dashboard still works |

**Priority:** Must Have

---

### US-008: Opt-in `make bdd-coverage` target

**As a** developer
**I want** instrumentation gated behind a separate Make target, not always-on in `make bdd`
**So that** my normal BDD iteration loop stays fast (10-30% slower with instrumentation is acceptable for an opt-in run, but unacceptable for the default loop)

**Scenario:**

```gherkin
Given I want to iterate quickly on a single scenario
When I run make bdd
Then the suite runs without coverage instrumentation
And cucumber.ndjson is produced as before
And no coverage artifacts are touched

Given I want a coverage report
When I run make bdd-coverage
Then the suite runs WITH coverage instrumentation
And cucumber.coverage.ndjson + coverage.json + coverage.html are produced
And cucumber.ndjson is unchanged
```

**Acceptance Criteria:**

- [ ] `make bdd-coverage` is added as a top-level target.
- [ ] `make bdd` is unchanged; it produces uninstrumented `cucumber.ndjson` only.
- [ ] `make bdd-coverage` may re-run the entire BDD suite under instrumentation; sharing output with `make bdd` is not required (and likely impossible without the per-target NDJSON path).
- [ ] `make bdd-coverage` requires no API key (Feature 3 is purely local — no Anthropic API calls). Distinct from `make bdd-dashboard` which does require the key.

**Edge Cases:**
| Condition | Expected Behavior |
|---|---|
| `make bdd-coverage` invoked without backend running | Same backend startup as `make bdd` (whatever Feature 1 does); failure modes match |
| Coverage instrumentation breaks a scenario | Treat as a bug — file at fix time. NO BUGS LEFT BEHIND policy applies. |
| Dev wants to compose: `make bdd-coverage && make bdd-dashboard` to get a coverage-augmented dashboard | Supported; the dashboard reads `coverage.json` if present |

**Priority:** Must Have

---

## 5. Technical Constraints

### Known Limitations

- **Static call-graph accuracy:** FastAPI uses decorator-based dynamic dispatch; some callees won't be statically resolvable. Tool must handle this gracefully (log warning, fall back to coverage.py-only data for those paths).
- **`pyan3`/`pycg` ecosystem:** Both tools have known limitations on async functions, generators, and `Depends()` injection. Research phase will assess current state.
- **Boundary enforcement:** Walking only `backend/src/hangman/` requires per-import path checks during graph construction. Some `from hangman.foo import bar` imports may be ambiguous in test contexts; resolve at the source-tree level.
- **Aggregate coverage:** Without per-scenario contexts, we can't say "scenario X didn't hit branch Y." Feature 2's LLM gets per-endpoint uncovered-branch summaries instead.
- **Coverage instrumentation overhead:** typically 10-30% wall-clock slowdown; targeting ≤ 50%.

### Dependencies

- **Requires:** Feature 1 (BDD suite — `make bdd` and `cucumber.ndjson` output) is on master.
- **Requires:** Feature 2 (BDD Dashboard — `backend/tools/dashboard/`) is on master. Feature 3 augments it but does not modify its core logic.
- **Blocked by:** Nothing.
- **Will be touched by:** Feature 2's `Packager` and `RUBRIC_TEXT` will be modified to surface coverage data when `coverage.json` is present (US-006). Feature 2's `Renderer` adds a new "Code coverage" card (US-005).

### Integration Points

- **`coverage.py` (PyPI library):** Used in `--branch` mode under the BDD-suite-driving uvicorn process. Outputs a `.coverage` data file consumed by Feature 3's analyzer.
- **`pyan3` or `pycg` (PyPI):** Static call-graph extractor; runs once per `make bdd-coverage` invocation against `backend/src/hangman/`. Tool choice deferred to Phase 2 research.
- **FastAPI `app.routes`:** Imported reflectively by Feature 3's analyzer to enumerate the canonical endpoint list. Avoids regex-scraping `routes.py` text.
- **Feature 2's dashboard:** Reads Feature 3's `coverage.json` via filesystem. Fully optional dependency: Feature 2 works without Feature 3's output (with a placeholder card).

## 6. Data Requirements

### New Data Models

- **`Endpoint`:** `method` (str), `path` (str, with FastAPI `{param}` placeholders), `handler_qualname` (str — e.g., `hangman.routes.create_game`).
- **`ReachableBranch`:** `file` (str, relative to repo), `line` (int), `branch_id` (str — coverage.py's `(line_from, line_to)` tuple as string), `condition_text` (str — the source snippet of the if/match condition), `taken` (bool — did dynamic coverage record this branch as taken).
- **`CoveragePerEndpoint`:** `endpoint` (Endpoint), `reachable_functions` (list[FunctionCoverage]), `total_branches` (int), `covered_branches` (int), `uncovered_branches` (list[ReachableBranch]), `coverage_pct` (float), `tone` (str — "success"/"warning"/"error"/"na").
- **`FunctionCoverage`:** `file` (str), `qualname` (str), `total_branches` (int), `covered_branches` (int), `uncovered_branches` (list[ReachableBranch]).
- **`CoverageReport`:** `timestamp` (str), `instrumented` (bool — always true for Feature 3), `endpoints` (list[CoveragePerEndpoint]), `extra_coverage` (list[FunctionCoverage] — functions hit but not statically reachable from any endpoint), `total_pct` (float).

### Data Validation Rules

- `coverage_pct` clamped to [0.0, 100.0].
- `path` must start with `/`.
- `method` must be one of `GET`, `POST`, `PATCH`, `PUT`, `DELETE`.
- `tone` derives strictly from `coverage_pct`: `< 50` → "error", `50 to < 80` → "warning", `≥ 80` → "success", `total_branches == 0` → "na".

### Data Migration

None. New data models, new artifacts. No existing data is touched.

### Artifacts Produced

- `frontend/test-results/cucumber.coverage.ndjson` — instrumented BDD run output (gitignored)
- `tests/bdd/reports/coverage.html` — standalone Feature 3 HTML report (gitignored)
- `tests/bdd/reports/coverage.json` — JSON artifact for Feature 2 to consume (gitignored)

All under existing gitignored `tests/bdd/reports/` and `frontend/test-results/` directories.

## 7. Security Considerations

- **No secrets:** Feature 3 is local-only, no API keys, no network calls. (Feature 2 uses `ANTHROPIC_API_KEY`; Feature 3 does not.)
- **No external data:** Feature 3 reads only the local NDJSON, the local `.coverage` file, and the local `backend/src/hangman/` source. No remote requests.
- **Source-code reading scope:** Feature 3 imports `backend/src/hangman/*` to extract the route table and walk the call graph. Source code stays local; nothing is uploaded.
- **HTML output safety:** `coverage.html` is rendered via Jinja2 with `select_autoescape(["html", "j2"])` (matching Feature 2's pattern). Source-code snippets in the drill-down (uncovered branch text) are HTML-escaped by default.
- **Audit:** No actions log required. Tool is read-only on source files; only writes to `tests/bdd/reports/` and `frontend/test-results/`.

## 8. Open Questions

> Questions to resolve in design / research phase

- [ ] **Static-analysis tool:** `pyan3` vs `pycg` vs alternative. Phase 2 `research-first` agent will compare current docs, accuracy on FastAPI, and Python 3.12+ compatibility.
- [ ] **`coverage.json` schema:** Exact JSON contract Feature 2 reads. Design phase will specify field names, nullability, versioning.
- [ ] **`coverage.py` context invocation:** Wrap `uvicorn` with `coverage run`? Use the `coverage` Python API directly? Subprocess vs in-process? Design phase decides.
- [ ] **Static-graph entry point:** Walk via FastAPI's `app.routes` (reflective) or AST-parse `routes.py` directly? Reflective is simpler and matches the running app; AST-parse avoids importing the whole backend.
- [ ] **Feature 2 augmentation contract:** When does Feature 2's `Packager` read `coverage.json`? Always-if-present (every `make bdd-dashboard` checks) or via a CLI flag? Design phase will spec.
- [ ] **Function-level rollup formula:** A function with 4 branches, 3 covered → 75% (yellow). But a function that's reachable but never called at all is 0% (red). Should we distinguish "function reached, partial branch coverage" from "function not reached at all"? Likely yes — design phase decides the visual.
- [ ] **Threshold customization:** Hardcoded red/yellow/green thresholds (50/80) or configurable via Make variable / config file? MVP says hardcoded; document for follow-up.

## 9. References

- **Discussion Log:** `docs/prds/bdd-branch-coverage-discussion.md`
- **Feature 1 (merged):** `docs/plans/2026-04-23-bdd-suite-design.md` — provides `make bdd` + `cucumber.ndjson` baseline
- **Feature 2 (merged):** `docs/prds/bdd-dashboard.md` (v2.0), `docs/plans/2026-04-24-bdd-dashboard-design.md`, `docs/plans/2026-04-24-bdd-dashboard-plan.md` — Feature 3 augments this
- **`coverage.py` docs:** https://coverage.readthedocs.io/ — `--branch` mode + data file format
- **`pyan3` PyPI:** https://pypi.org/project/pyan3/ — static call-graph candidate
- **`pycg` PyPI:** https://pypi.org/project/pycg/ — static call-graph alternative
- **FastAPI route enumeration:** https://fastapi.tiangolo.com/advanced/route-table/ — for the reflective approach to endpoint enumeration

---

## Appendix A: Revision History

| Version | Date       | Author      | Changes                                                      |
| ------- | ---------- | ----------- | ------------------------------------------------------------ |
| 1.0     | 2026-04-24 | Claude + KC | Initial PRD from refined discussion (15 Q's across 2 rounds) |

## Appendix B: Approval

- [ ] Product Owner approval (KC)
- [ ] Technical Lead approval (KC)
- [ ] Ready for technical design (Phase 2 research → Phase 3 brainstorming)
