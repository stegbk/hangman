# PRD: BDD Dashboard

**Version:** 1.1
**Status:** Draft
**Author:** Claude + KC
**Created:** 2026-04-23
**Last Updated:** 2026-04-23

---

## 1. Overview

A developer-only tool that generates a self-contained HTML dashboard for the Hangman BDD suite. Run `make bdd-dashboard` after `make bdd` — a Python analyzer parses the 11 `.feature` files (scraping) + the latest `cucumber.ndjson` (pass/fail) and emits `tests/bdd/reports/dashboard.html` with summary cards, Chart.js charts, and 33 per-scenario cards. A 13-rule opinion engine (6 domain-specific + 7 universal-hygiene) grades each scenario and attaches P0/P1/P2/P3 findings. Dashboard is **informational only** — no gates, no hook enforcement. Structurally modeled on the user's reference dashboard (`/Users/keithstegbauer/Downloads/bdd_dashboard_example.html`).

## 2. Goals & Success Metrics

### Goals

- **Primary:** Give a developer a single at-a-glance view of BDD suite health — pass/fail, coverage gaps per endpoint + per UC, opinion-engine findings per scenario, and trend over time.
- **Secondary:** Make scenario/feature additions zero-config — every `make bdd-dashboard` run rediscovers what's in `.feature` files and re-renders against the latest NDJSON without touching any manifest or allow-list.
- **Tertiary:** Keep the tool local-only and self-contained — one HTML file, Chart.js via CDN, no git-tracked artifacts.

### Success Metrics

| Metric                                          | Target                                                                                   | How Measured                                                                                                                                           |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Generation latency on 33-scenario suite         | ≤ 5 s wall-clock                                                                         | `time make bdd-dashboard` from clean                                                                                                                   |
| Opinion engine correctness on the current suite | All 13 rules produce deterministic, non-flaky findings                                   | Golden-file test snapshots findings; unit tests cover per-rule edge cases                                                                              |
| Rendering portability                           | HTML renders and all charts display correctly                                            | Open `dashboard.html` in Chrome, Firefox, Safari — every summary card, both charts, and a random sample of 3 scenario cards + modals visually verified |
| Dynamic discovery                               | Adding a new `.feature` file is reflected in the next run with zero config changes       | Manual check: add a dummy `.feature`, run `make bdd-dashboard`, confirm its scenarios appear as cards                                                  |
| History append                                  | Every run appends one NDJSON snapshot to `.bdd-history/` (timestamped), never overwrites | `ls .bdd-history/` grows by exactly 1 after each run                                                                                                   |
| Zero gating                                     | `make bdd-dashboard` exits 0 regardless of findings                                      | Explicit test with a seeded P0-triggering feature fixture                                                                                              |

### Non-Goals (Explicitly Out of Scope)

- ❌ **Gating** — does NOT block `git commit` / `git push` / `gh pr create` / `make bdd` / `make verify` on findings. No change to `.claude/hooks/check-workflow-gates.sh`.
- ❌ **Call-graph / per-branch coverage / gap detection against `routes.py`** — Feature 3 (`bdd-branch-coverage`) owns this.
- ❌ **Endpoint enumeration from `routes.py`** — Feature 3. This feature only scrapes endpoints that appear in Gherkin text.
- ❌ **Teams-channel push / Slack / webhook integration** — deferred.
- ❌ **CI/CD publishing** — this is a local-only tool; `tests/bdd/reports/dashboard.html` is gitignored.
- ❌ **Auto-invoke on `make bdd`** — explicit `make bdd-dashboard` only.
- ❌ **Git-tracked dashboard artifact** — the HTML regenerates per-run.
- ❌ **SPA / React dashboard** — single static HTML + inlined JSON data blob; only external dep is Chart.js via CDN.
- ❌ **Real-time / live-updating dashboard** — static snapshot; refresh by re-running the command.
- ❌ **Historical storage as shared artifact** — history is per-developer, local to `.bdd-history/`, never committed.

## 3. User Personas

### Developer

- **Role:** Engineer authoring or maintaining BDD scenarios for the Hangman project.
- **Permissions:** Full local repo access; no authentication required for the tool itself.
- **Goals:**
  - Triage scenario quality after a BDD run (what passed, what failed, what's missing).
  - Find coverage gaps — which endpoints or UCs don't have the full `@happy`/`@failure`/`@edge` tag mix.
  - Catch anti-patterns (trivial passes, missing error-code assertions, malformed tags) before code review.
  - See whether the suite is trending up or down in quality over recent runs.

## 4. User Stories

### US-001: Generate the dashboard on demand

**As a** developer
**I want** to run `make bdd-dashboard` after `make bdd`
**So that** I get a single self-contained HTML report of the suite's current state

**Scenario:**

```gherkin
Given I have just run `make bdd` and `frontend/test-results/cucumber.ndjson` exists
When I run `make bdd-dashboard`
Then the command exits with code 0
And `tests/bdd/reports/dashboard.html` exists
And the HTML is self-contained (no external assets beyond Chart.js CDN)
And opening it in a browser renders the full page without errors
```

**Acceptance Criteria:**

- [ ] `make bdd-dashboard` exits 0 after successful HTML emission.
- [ ] Output path is exactly `tests/bdd/reports/dashboard.html`.
- [ ] The HTML file is a single file; all CSS is inline or in a `<style>` block, and Chart.js is loaded via a public CDN URL.
- [ ] If `cucumber.ndjson` is missing, the command errors with a clear message pointing the user at `make bdd`.
- [ ] If `cucumber.ndjson` is present but malformed, the command errors with the parse error and a line number.

**Edge Cases:**

| Condition                                       | Expected Behavior                                                                   |
| ----------------------------------------------- | ----------------------------------------------------------------------------------- |
| `cucumber.ndjson` missing                       | Error: `Run \`make bdd\` first — no cucumber.ndjson at <path>.` Exit non-zero.      |
| `cucumber.ndjson` empty (0-byte)                | Error: `Empty NDJSON — BDD suite likely crashed during setup.` Exit non-zero.       |
| `frontend/tests/bdd/features/` missing or empty | Error: `No .feature files found under frontend/tests/bdd/features/.` Exit non-zero. |
| `tests/bdd/reports/` doesn't exist              | Created automatically.                                                              |

**Priority:** Must Have

---

### US-002: See coverage grade per endpoint

**As a** developer
**I want** the dashboard to grade each API endpoint referenced in Gherkin as Full / Partial / None
**So that** I can spot endpoints missing `@happy`, `@failure`, or `@edge` coverage

**Scenario:**

```gherkin
Given `guesses.feature` has 5 scenarios (2 @happy, 2 @failure, 1 @edge) all referencing `/api/v1/games/{id}/guesses`
When I open the dashboard
Then the "Endpoint coverage" section shows `/api/v1/games/{id}/guesses` as **Full**
And if I remove the @edge scenario and regenerate, the same endpoint now shows as **Partial**
```

**Acceptance Criteria:**

- [ ] Endpoints are extracted by scraping `"/api/v1/..."` strings from scenario step text (no routes.py read; out of scope per non-goals).
- [ ] Grading per endpoint: **Full** = ≥1 @happy + ≥1 @failure + ≥1 @edge. **Partial** = ≥1 scenario but missing one of the three. **None** = endpoint string nowhere in scenarios.
- [ ] The dashboard shows a coverage-grade badge next to each endpoint in a dedicated section.
- [ ] Endpoints with identical path templates (e.g., `/api/v1/games/1/guesses` and `/api/v1/games/2/guesses`) are normalized to a single template (`/api/v1/games/{id}/guesses`) via regex substitution of numeric path params.

**Edge Cases:**

| Condition                                               | Expected Behavior                                                        |
| ------------------------------------------------------- | ------------------------------------------------------------------------ |
| No endpoints found in Gherkin                           | Section renders "No API endpoints referenced in Gherkin" (not an error). |
| Scenario references an endpoint without any primary tag | Endpoint shows as Partial; the tagless scenario is also flagged by H2.   |
| Duplicate endpoint template                             | Listed once, all matching scenarios aggregated.                          |

**Priority:** Must Have

---

### US-003: See coverage grade per Use Case

**As a** developer
**I want** the dashboard to grade each UC (e.g., UC1, UC3b) with the same Full/Partial/None rubric
**So that** I can spot use cases missing `@happy`/`@failure`/`@edge` scenarios

**Scenario:**

```gherkin
Given `forfeit.feature` has 2 scenarios titled including "UC3" and "UC3b", both @happy
When I open the dashboard
Then the "UC coverage" section shows UC3 as **Partial** (only @happy; no @failure or @edge scenarios)
And UC3b also as **Partial** for the same reason
```

**Acceptance Criteria:**

- [ ] UC names extracted from `Feature:` line text via regex matching `UC\d+[a-z]?` (e.g., `UC1`, `UC3`, `UC3b`, `UC12a`).
- [ ] Grading rubric: identical to US-002.
- [ ] Dashboard shows each discovered UC with its grade + the scenarios that comprise it.
- [ ] If a Feature file has no UC in its title (e.g., `Feature: GET /api/v1/categories`), it is not counted in the UC section.

**Edge Cases:**

| Condition                                                | Expected Behavior                                                     |
| -------------------------------------------------------- | --------------------------------------------------------------------- |
| No UCs detected                                          | Section renders "No UCs identified in Feature titles" (not an error). |
| UC appears in multiple Feature files                     | Aggregated; scenarios from all files combined.                        |
| UC name ambiguity (e.g., "UC3" matches "UC3b" as prefix) | Regex anchors on word boundary; `UC3` and `UC3b` are distinct.        |

**Priority:** Must Have

---

### US-004: See opinion-engine findings per scenario

**As a** developer
**I want** each scenario card to list P0/P1/P2/P3 findings from the opinion engine
**So that** I can spot anti-patterns without reading every `.feature` file

**Scenario:**

```gherkin
Given I add a new scenario tagged @failure that only asserts `Then the response status is 422` (no error-code assertion)
When I run `make bdd-dashboard`
Then the scenario card shows a D2 (P2) finding: "@failure scenario doesn't assert error.code"
And clicking the card opens a modal with the rule's description, reason, and suggested fix
```

**Acceptance Criteria:**

- [ ] 13 rules shipped at v1: D1–D6 (domain) + H1–H7 (hygiene). See Appendix for full definitions.
- [ ] Each finding includes: rule ID, severity, scenario location (file + line), short problem statement, suggested fix.
- [ ] Severities map to P0/P1/P2/P3 per `.claude/rules/workflow.md`.
- [ ] Findings are **informational only** — presence does not affect exit code.
- [ ] Findings are deterministic — running the analyzer twice on the same inputs produces identical output.

**Edge Cases:**

| Condition                                                                   | Expected Behavior                                |
| --------------------------------------------------------------------------- | ------------------------------------------------ |
| Scenario triggers multiple rules                                            | All findings listed; severity-sorted (P0 first). |
| Scenario triggers zero rules                                                | Card shows "No findings" in the issues slot.     |
| Rule ambiguity (e.g., `Scenario Outline` with 1 example also has 15+ steps) | Both H4 and H5 fire.                             |

**Priority:** Must Have

---

### US-005: See trend over recent runs

**As a** developer
**I want** a trend chart over the last N runs of `make bdd-dashboard`
**So that** I can see whether the suite's quality is drifting up or down over time

**Scenario:**

```gherkin
Given I have run `make bdd-dashboard` 10 times over a week
When I open the latest dashboard
Then a trend chart shows 10 data points
And each point includes: total scenarios, passing, failing, total P0/P1 findings
```

**Acceptance Criteria:**

- [ ] Each `make bdd-dashboard` run appends one compact summary file to `.bdd-history/` named `YYYY-MM-DD-HH-MM.json` (or similar unique timestamp).
- [ ] `.bdd-history/` is gitignored.
- [ ] The trend chart reads the last N files (N = all available, no cap; retention is "keep forever" per discussion Q22).
- [ ] When `.bdd-history/` contains < 5 entries, the trend chart section shows a placeholder: "Run `make bdd-dashboard` at least 5 times to see trends" (no broken chart).
- [ ] Chart type: line chart, one series per metric (total / passing / failing / P0+P1 count), dates on x-axis.

**Edge Cases:**

| Condition                                | Expected Behavior                                                                                                              |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Empty `.bdd-history/`                    | Placeholder text, no chart.                                                                                                    |
| Corrupt history entry (unparseable JSON) | Skipped with a one-line warning in terminal; chart still renders from remaining entries.                                       |
| Many entries (e.g., 1000+)               | All entries read but only last 90 shown on the chart for readability (oldest points truncated in UI, never deleted from disk). |

**Priority:** Must Have

---

### US-006: Click a scenario card for full detail

**As a** developer
**I want** to click any of the 33 scenario cards to open a modal with full scenario detail
**So that** I can see the scenario's Gherkin source, its steps' pass/fail outcomes, and the opinion-engine findings in one place

**Scenario:**

```gherkin
Given the dashboard is open in my browser
When I click the card for "UC1 — Play a round to completion"
Then a modal opens showing the Feature name, scenario title, primary + smoke tags, the Gherkin step list with pass/fail status from NDJSON, and each finding with rule ID, description, reason, and fix example
And clicking outside the modal (or pressing Esc) closes it
```

**Acceptance Criteria:**

- [ ] One card per Scenario = 33 cards on the current suite.
- [ ] Card content (short form): scenario name, primary tag badge, @smoke badge (if present), pass/fail indicator, finding count by severity.
- [ ] Modal content (click-through): full Gherkin steps, NDJSON-derived pass/fail per step, complete findings list with all rule metadata (id, severity, description, reason, fix example).
- [ ] Modal dismiss: click-outside + Esc key.
- [ ] No network activity after initial page load (Chart.js CDN is the only external fetch; all scenario data inlined in a `<script>` blob).

**Edge Cases:**

| Condition                                                | Expected Behavior                                                            |
| -------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Scenario skipped (e.g., filtered by `--tags` mismatch)   | Card rendered, pass/fail indicator shows "skipped"; findings still computed. |
| Scenario has no steps in NDJSON (unlikely parse failure) | Card shows "No outcome" indicator; opinion-engine findings still shown.      |

**Priority:** Must Have

---

### US-007: Zero-config behavior when scenarios or features are added

**As a** developer
**I want** adding a new `.feature` file or scenario to be automatically reflected in the next dashboard run
**So that** I never have to update a manifest, allow-list, or scenario-count constant

**Scenario:**

```gherkin
Given I am working in a branch and I add `tests/bdd/features/new-capability.feature` with 2 scenarios
When I run `make bdd-dashboard` (without any other changes)
Then the dashboard shows 35 scenario cards (was 33, now 33+2)
And "new-capability.feature" appears in the Features breakdown with its 2 scenarios counted
And the opinion engine has evaluated the 2 new scenarios and attached findings if any rules fired
```

**Acceptance Criteria:**

- [ ] No scenario count, feature count, endpoint list, or UC list is hardcoded in the Python source.
- [ ] The analyzer discovers `.feature` files via glob `frontend/tests/bdd/features/*.feature`.
- [ ] The analyzer discovers UCs from Feature titles, endpoints from step text — both per-run.
- [ ] Running twice on an unchanged tree produces byte-identical output (aside from the timestamp header).
- [ ] Golden-file test guards against accidental hardcoding (if the test fixture grows a new scenario, the golden snapshot updates without code changes to the analyzer).

**Edge Cases:**

| Condition                                                     | Expected Behavior                                                                                   |
| ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| New scenario has an unknown primary tag (typo like `@happpy`) | H2 rule fires; scenario shows as "missing primary tag" + card shows unknown tag as a warning badge. |
| New Feature file has no Feature-block header (malformed)      | Parser raises a clear error pointing at the file + line.                                            |
| New scenario happens to be `Scenario Outline:` with 1 row     | H5 rule fires; card shows P3 finding.                                                               |

**Priority:** Must Have

---

## 5. Technical Constraints

### Known Limitations

- **Python-only analyzer** lives in `backend/tools/dashboard/` — NOT part of the installable `hangman` package. Invoked via `uv run python -m tools.dashboard` from `backend/`. This keeps the app package runtime-lean.
- **Gherkin AST from the NDJSON, not regex on `.feature` text** (research brief 2026-04-23 finding #2). cucumber-js 12.8.1 already emits `gherkinDocument` envelopes in `cucumber.ndjson` — the typed AST is free. The analyzer consumes `gherkinDocument` for scenario inventory + tags + step text, so no `gherkin-official` dependency is required and no regex-fragility risk exists for core parsing. Regex is used ONLY for endpoint-template normalization within step text (e.g., collapsing `/games/1/guesses` → `/games/{id}/guesses` for coverage bucketing).
- **Chart.js via CDN** — matches the reference dashboard's implementation; the HTML will fail to render charts if the user is offline. Acceptable trade-off for a local dev tool; self-hosting Chart.js is a follow-up if offline use becomes a real need.
- **NDJSON parsing is version-pinned** — this feature targets cucumber-js 12.x / Cucumber Messages schema v32.2.0 (what Feature 1 ships). Schema version must be checked from the NDJSON header; a mismatch errors with a clear message.
- **No concurrent-run safety** — `make bdd-dashboard` writes `tests/bdd/reports/dashboard.html` and appends to `.bdd-history/` atomically enough for a single user, but no locking if invoked concurrently.

### Dependencies

- **Requires:** Hangman BDD suite (Feature 1) merged to master. `frontend/tests/bdd/features/*.feature` must exist. Successful `make bdd` run has produced `frontend/test-results/cucumber.ndjson`.
- **Blocked by:** None.

### Integration Points

- **Cucumber Messages NDJSON** (`frontend/test-results/cucumber.ndjson`) — input for pass/fail + timestamp + per-step outcomes.
- **Gherkin `.feature` files** (`frontend/tests/bdd/features/*.feature`) — input for scenario inventory, tags, step text (coverage + rules).
- **Chart.js 4.x via CDN** — pin exact version `4.5.1` (research brief finding #1; free bugfix bump over the reference dashboard's 4.4.0, no breaking changes in the 4.x line). URL: `https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js`. Exact pin (not `@4` or `@latest`) preserves US-007's byte-identical-output guarantee across runs on unchanged input.
- **Makefile** — new `bdd-dashboard` target that invokes the Python analyzer.
- **`.gitignore`** — new entries for `tests/bdd/reports/` and `.bdd-history/`.

## 6. Data Requirements

### New Data Models (in-memory, not persisted)

- **`Scenario`** — represents one parsed scenario: name, primary tag, smoke tag, step list, source file, line, NDJSON outcome (pass/fail/skipped). Outcome is a **rollup** over all `testStepFinished.testStepResult.status` values for that scenario (the NDJSON `testCaseFinished` envelope does not carry a `status` field directly — research brief finding #3). The rollup function is named and unit-tested against all 7 Cucumber Messages status enum values: `UNKNOWN`, `PASSED`, `SKIPPED`, `PENDING`, `UNDEFINED`, `AMBIGUOUS`, `FAILED`. `testCaseFinished.willBeRetried=true` is treated as "ignore, wait for retry."
- **`Feature`** — one parsed Feature block: name, file path, scenarios, UCs detected.
- **`Finding`** — one opinion-engine finding: rule ID, severity (P0/P1/P2/P3), scenario ref, problem, reason, fix example.
- **`CoverageGrade`** — per-endpoint and per-UC: state (Full/Partial/None), scenarios contributing, missing tags.
- **`RunSummary`** — one row in `.bdd-history/<timestamp>.json`: timestamp, total/passing/failing, P0/P1/P2/P3 finding counts. Used to build the trend chart.

### Data Validation Rules

- `.feature` files must parse as valid Gherkin. Malformed files raise with file + line.
- NDJSON must declare Cucumber Messages protocol version; `meta.protocolVersion` is checked and a mismatch against the expected major version (32.x) is a hard error.
- Timestamps in `.bdd-history/` filenames must be sortable (ISO-ish format) so reading "last N" is a simple `sorted()`.

### Data Migration

- None. Dashboard is a new tool; no existing data to migrate.

## 7. Security Considerations

- **Authentication:** N/A — local developer tool, no network service, no user auth.
- **Authorization:** N/A — developer has full local repo access.
- **Data Protection:** No sensitive data. `.feature` files + NDJSON don't contain secrets; `.bdd-history/` is developer-local.
- **Supply chain:** Chart.js is loaded from jsdelivr CDN. The specific version URL is pinned in the generated HTML; the CDN is a public trust-boundary already accepted by the reference dashboard.
- **No new secrets required.** No new environment variables. No new external service calls beyond the Chart.js CDN fetch at HTML load time (from the developer's browser, not the analyzer).
- **Audit:** N/A. Local tool; no audit surface.

## 8. Open Questions

None blocking. All significant decisions were resolved in the discussion log (`docs/prds/bdd-dashboard-discussion.md` Rounds 1–4).

## 9. References

- **Discussion log:** `docs/prds/bdd-dashboard-discussion.md`
- **Reference dashboard (visual target):** `/Users/keithstegbauer/Downloads/bdd_dashboard_example.html` (user-authored external asset, not in repo)
- **Related PRDs:**
  - `docs/prds/bdd-suite.md` (Feature 1, merged) — provides the `.feature` files + NDJSON this feature consumes.
  - Feature 3 (`bdd-branch-coverage`, pending) — will extend coverage analysis with call-graph + routes.py enumeration. This PRD intentionally defers that scope.
- **Sibling gate vocabulary:** `.claude/rules/testing.md` § "BDD suite vocabulary" — no new hook gate is introduced by this feature (see Non-Goals).

---

## Appendix A: Revision History

| Version | Date       | Author      | Changes                                                                                                                                                                                                                                                            |
| ------- | ---------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1.0     | 2026-04-23 | Claude + KC | Initial PRD from `bdd-dashboard-discussion.md`                                                                                                                                                                                                                     |
| 1.1     | 2026-04-23 | Claude + KC | Post-research corrections from `docs/research/2026-04-23-bdd-dashboard.md`: (1) consume `gherkinDocument` envelopes from NDJSON (drop "regex scrape" framing); (2) Chart.js pin 4.4.0 → 4.5.1 exact; (3) clarify Scenario pass/fail as a typed step-status rollup. |

## Appendix B: Starter Opinion-Engine Ruleset

13 rules = 6 domain-specific (D1–D6) + 7 universal Gherkin-hygiene (H1–H7). All severities use the P0–P3 rubric from `.claude/rules/workflow.md`.

### Domain-specific (Hangman BDD)

| ID  | Severity | Rule                                                                                                     | Rationale                                         |
| --- | -------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| D1  | P2       | Scenario asserts `response status is {int}` but no body-path assertion                                   | Trivial-pass: passing without verifying behavior. |
| D2  | P2       | `@failure` scenario doesn't assert `error.code`                                                          | Our error envelope IS the contract.               |
| D3  | P2       | `@failure` scenario doesn't assert a specific non-2xx status                                             | "Failed somehow" ≠ "failed the right way".        |
| D4  | P3       | UI scenario asserts no persisted side-effect (no history/masked-word/banner/score-total assertion)       | Weak but not wrong.                               |
| D5  | P2       | `/guesses`-hitting scenario doesn't verify one of `guessed_letters`, `masked_word`, or `lives_remaining` | Every guess MUST change one of these.             |
| D6  | P3       | Endpoint referenced in Gherkin but no `@smoke` scenario for it                                           | Smoke-coverage gap.                               |

### Universal Gherkin hygiene

| ID  | Severity | Rule                                                        | Rationale                                            |
| --- | -------- | ----------------------------------------------------------- | ---------------------------------------------------- |
| H1  | P1       | Duplicate Scenario title within a Feature file              | Cucumber accepts; results become ambiguous.          |
| H2  | P1       | Scenario has zero primary tag (`@happy`/`@failure`/`@edge`) | Our tag vocabulary contract.                         |
| H3  | P1       | Scenario has multiple primary tags                          | Same contract — primary tags are mutually exclusive. |
| H4  | P3       | Scenario > 15 steps (excluding Background)                  | Should probably be split.                            |
| H5  | P3       | `Scenario Outline` with only 1 `Examples` row               | Should be a plain `Scenario`.                        |
| H6  | P0       | Feature file with zero scenarios                            | Broken.                                              |
| H7  | P2       | Feature file where all scenarios share one primary tag      | File-level coverage gap.                             |

## Appendix C: Approval

- [ ] Product Owner approval (KC)
- [ ] Technical Lead approval (KC)
- [ ] Ready for Phase 2 (Research) — triggered by `/new-feature` Phase 2 dispatching the `research-first` agent
