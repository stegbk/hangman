# PRD: BDD Suite

**Version:** 1.1
**Status:** Draft
**Author:** Claude + KC
**Created:** 2026-04-23
**Last Updated:** 2026-04-23

---

## 1. Overview

Install pure `@cucumber/cucumber` as a BDD test runner and express every API endpoint + every user-facing use case as `.feature` files. Gherkin becomes the single source of truth for user-observable behavior. `.feature` files double as living documentation and as regression tests executed locally via `make bdd`. This is Feature 1 of a three-feature plan (F2 = static analyzer + HTML dashboard; F3 = call graph + branch coverage gap detection); Feature 1 ships the BDD infrastructure alone — no dashboard, no coverage.

## 2. Goals & Success Metrics

### Goals

- **Primary:** `.feature` files express every endpoint (`GET /categories`, `GET /session`, `POST /games`, `GET /games/current`, `POST /games/{id}/guesses`, `GET /history`) and every existing UC (UC1, UC2, UC3, UC3b, UC4) with at minimum `@happy` + `@failure` + `@edge` coverage per endpoint.
- **Secondary:** `.feature` files read as living documentation — a new contributor can understand user-observable behavior by reading Gherkin without touching source.
- **Tertiary:** Tag conventions (`@happy` / `@failure` / `@edge` / `@smoke`) are committed from day one so Feature 2's dashboard analyzer has stable input.

### Success Metrics

| Metric                         | Target                                                                                                       | How Measured                                                                                            |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| Per-endpoint scenario coverage | Each of 6 endpoints has ≥ 1 `@happy` + ≥ 1 `@failure` + ≥ 1 `@edge` scenario                                 | Grep tags in `frontend/tests/bdd/features/*.feature`; ≥ 18 endpoint scenarios total                     |
| UC coverage                    | 5 UCs (UC1/2/3/3b/4) expressed as `.feature` scenarios                                                       | One scenario per UC in the appropriate flow feature; each tagged `@smoke` + happy/failure as applicable |
| BDD suite passes               | 100% of scenarios pass                                                                                       | `pnpm bdd` (and `make bdd`) against live backend + frontend returns exit 0                              |
| Local run time                 | < 60s end-to-end                                                                                             | `time make bdd`                                                                                         |
| `make verify` still fast       | Unchanged (~1.5s)                                                                                            | `make verify` does NOT invoke BDD                                                                       |
| Documentation quality          | 100% of `.feature` files have a `Feature:` description line + every scenario has `Given/When/Then` structure | Gherkin-lint pass                                                                                       |

### Non-Goals (Explicitly Out of Scope)

- ❌ HTML dashboard generation (Feature 2)
- ❌ Static analyzer that categorizes scenarios or detects anti-patterns (Feature 2)
- ❌ Call graph generation (Feature 3)
- ❌ `coverage.py --branch --contexts` integration (Feature 3)
- ❌ Gap detection ("branches not covered by any BDD scenario") (Feature 3)
- ❌ Migrating pytest parametrized tests into Gherkin (discussion Q5 — integration tests stay)
- ❌ `playwright-bdd` adapter (discussion Q1 — pure cucumber chosen for documentation purity)
- ❌ `@playwright/test` fixtures (`auth.ts` etc.) — not used by pure cucumber-js runner
- ❌ Replacing the verify-e2e agent or markdown UCs (Q9 — BDD gate is additive)
- ❌ Including BDD in `make verify` (Q7 — verify stays fast)
- ❌ CI/CD pipeline integration (local-only per user goals)
- ❌ Parallelism tuning beyond cucumber-js defaults (single-user scale)
- ❌ Authenticated scenarios (hangman has no auth)
- ❌ Visual regression / screenshot diffing in BDD

## 3. User Personas

### Developer (KC / future contributors)

- **Role:** Writes `.feature` scenarios as living documentation and runs them locally during Phase 5.4 E2E.
- **Permissions:** Full repo access; no auth on the app itself.
- **Goals:** Understand user-observable behavior by reading `.feature` files; validate changes don't break documented scenarios.

### Claude / implementation subagents (future feature work)

- **Role:** Reads `.feature` files to understand expected behavior when implementing changes. `.feature` files serve as tests-as-specification.
- **Permissions:** Read access during planning; Write access during implementation.
- **Goals:** Produce implementations that satisfy documented scenarios.

### Feature 2 dashboard analyzer (future)

- **Role:** Static + runtime consumer of `.feature` files + Cucumber JSON report.
- **Permissions:** Read-only on `.feature` tree and report output.
- **Goals:** Count scenarios per tag, detect anti-patterns, emit HTML dashboard.

## 4. User Stories

### US-BDD-001: Run the BDD suite locally

**As a** developer
**I want** to run `pnpm bdd` (or `make bdd`) and see every `.feature` scenario pass
**So that** I can validate the app's user-observable behavior in one command before shipping

**Scenario:**

```gherkin
Given the backend is running (make backend, default port or HANGMAN_BACKEND_PORT override)
And the frontend is running (make frontend, default port or HANGMAN_FRONTEND_PORT override)
When I run `make bdd` from the repo root
Then cucumber-js discovers every .feature file under frontend/tests/bdd/features/
And every scenario executes against the running backend + frontend
And the exit code is 0 when all scenarios pass
And the total run time is under 60 seconds on a dev laptop
```

**Acceptance Criteria:**

- [ ] `make bdd` at repo root delegates to `cd frontend && pnpm bdd`.
- [ ] `pnpm bdd` in `frontend/package.json` invokes `cucumber-js` with the right config (feature path, step-def glob, formatters).
- [ ] `cucumber-js` is configured via `frontend/cucumber.cjs` — explicit `paths` for `.feature` files, `import: ["tsx/esm", "tests/bdd/steps/**/*.ts"]` for TS step defs loaded via `tsx` (NOT `ts-node/register` — that's stale per research), `format` list including `json:test-results/cucumber.json`, `message:test-results/cucumber.ndjson` (Cucumber-Messages protobuf stream — future-proof for Feature 2's analyzer), and `progress-bar`.
- [ ] BDD run uses the live backend + frontend (from `HANGMAN_BACKEND_PORT`/`HANGMAN_FRONTEND_PORT` env vars — default 8000/3000). If servers aren't reachable, the suite fails fast with a clear error referencing `make backend` / `make frontend`.
- [ ] Browser lifecycle: one `playwright` browser shared across scenarios; a fresh `context` + `page` per scenario (isolation) via Cucumber `Before`/`After` hooks. Browser closed in `AfterAll`.
- [ ] The suite runs < 60s on a local dev laptop with existing servers.
- [ ] Exit code 0 on all-pass; non-zero on any failure, and the failing scenario is printed with step-level details.

**Edge Cases:**

| Condition                               | Expected Behavior                                                                                          |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Backend not running                     | Suite fails in the first `Before` hook with "Backend not reachable at <URL> — did you run `make backend`?" |
| Frontend not running                    | Same, for frontend URL                                                                                     |
| Malformed `.feature` file               | Cucumber-js fails to parse during load; error includes file + line number                                  |
| Step without a matching definition      | Cucumber reports "undefined step" and suite fails                                                          |
| Server port overridden (e.g. 8002/3001) | Env-var override is respected; step defs read `HANGMAN_BACKEND_PORT` / `HANGMAN_FRONTEND_PORT`             |

**Priority:** Must Have

---

### US-BDD-002: Read `.feature` files as behavioral documentation

**As a** developer or Claude subagent reading the repo for the first time
**I want** every backend endpoint and UI flow expressed as a Gherkin scenario
**So that** I understand user-observable behavior without reading source

**Scenario:**

```gherkin
Given I open frontend/tests/bdd/features/
When I list the files
Then I see one .feature per endpoint: categories.feature, session.feature,
    games.feature, games-current.feature, guesses.feature, history.feature
And I see one .feature per UI flow: play-round.feature (UC1),
    loss-resets-streak.feature (UC2), forfeit.feature (UC3 + UC3b),
    mid-game-reload.feature (UC4)
And each file starts with `Feature: <title>` + a prose description
And every scenario has Given/When/Then structure
And every scenario carries at least one tag from {@happy, @failure, @edge, @smoke}
```

**Acceptance Criteria:**

- [ ] Ten `.feature` files exist under `frontend/tests/bdd/features/`: 6 endpoint files + 4 UI-flow files (UC3 + UC3b may share `forfeit.feature`).
- [ ] Each file has a `Feature:` line + multi-line description explaining the endpoint/flow's user-observable purpose.
- [ ] Every scenario has explicit `Given` (precondition) + `When` (action) + `Then` (assertion) steps.
- [ ] No scenario uses a bare `And` without a preceding `Given/When/Then`.
- [ ] Tag set is exactly `{@happy, @failure, @edge, @smoke}` — no ad-hoc tags (we commit to this closed set so Feature 2 can rely on it).
- [ ] Every scenario carries exactly one of `@happy` / `@failure` / `@edge`; `@smoke` is orthogonal (added to critical fast scenarios).
- [ ] Scenarios are written from the user's perspective — no implementation details (no "SQL query", "FastAPI route", "React re-render") in step text.

**Edge Cases:**

| Condition                                                 | Expected Behavior                                                                                                    |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Scenario needs shared setup across multiple tests         | Use `Background:` block at the top of the file                                                                       |
| Scenario has multiple slight input variations             | Use `Scenario Outline:` + `Examples:` table (but keep table small per Q5 — full parametric coverage stays in pytest) |
| Scenario describes a flow the current app doesn't support | Delete it (don't write aspirational scenarios); document the gap in CONTINUITY.md                                    |

**Priority:** Must Have

---

### US-BDD-003: Discover coverage by tag

**As a** developer
**I want** to grep or filter `.feature` files by tag
**So that** I can answer "do we have happy-path coverage for every endpoint?" or "run just smoke" in one command

**Scenario:**

```gherkin
Given the BDD suite exists with @happy / @failure / @edge / @smoke tags
When I run `pnpm bdd --tags @smoke`
Then only scenarios tagged @smoke execute
And the suite finishes faster than a full run
When I run `grep -rn '@happy' frontend/tests/bdd/features/ | wc -l`
Then I get the count of happy-path scenarios
```

**Acceptance Criteria:**

- [ ] `pnpm bdd -- --tags @smoke` runs only `@smoke` scenarios.
- [ ] `pnpm bdd -- --tags "@happy and not @smoke"` works (cucumber-js tag expression syntax).
- [ ] Tags are applied at the `Scenario` level; `Feature`-level tags apply to all scenarios in the file (acceptable for e.g. `@smoke` on `play-round.feature` critical UC1).
- [ ] The choice of scenario tag is binding per the coverage axes. A scenario is either `@happy`, `@failure`, or `@edge` — never multiple (prevents dashboard double-counting).
- [ ] `@smoke` is additive; any of the three primary tags can also carry `@smoke` to mark "critical path, run on fast regression."

**Edge Cases:**

| Condition                                                      | Expected Behavior                                                                                                    |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Scenario tagged with two primary tags (e.g. `@happy @failure`) | Feature 2 lint will flag this; Feature 1 doesn't enforce, but style guide says don't                                 |
| Scenario with no primary tag                                   | Untagged scenario passes but Feature 2 will later flag "uncategorized"                                               |
| Feature-level tag conflicts with scenario-level                | Cucumber merges (scenario inherits feature tags); documented in a `.feature`-authoring guide under `docs/solutions/` |

**Priority:** Must Have

---

### US-BDD-004: BDD gate added to Phase 5.4, does not replace existing gates

**As a** developer running `/new-feature` workflow
**I want** the BDD suite passing to be part of the Phase 5.4 E2E gate
**So that** regressions in documented behavior block ship, alongside the existing verify-e2e agent and markdown UC coverage

**Scenario:**

```gherkin
Given I am in Phase 5.4 of a /new-feature workflow
When the verify-e2e agent runs (existing gate)
Then it continues to execute markdown UCs and produce a report
And ALSO make bdd must pass
And both gates being green advances me to Phase 6
And either gate failing blocks commit/push/PR
```

**Acceptance Criteria:**

- [ ] `.claude/rules/testing.md` "Canonical E2E gate vocabulary" updated — the BDD gate adds an entry alongside `E2E verified` (something like `BDD suite passed (Phase 5.4)`).
- [ ] The check-workflow-gates.sh hook (or an adjacent hook) gains a check for the new marker, OR we document explicitly that BDD-suite-passed is a manual checklist item for Feature 1 and gate automation is deferred.
- [ ] Existing gates (`E2E verified`, `Code review loop`, `Simplified`, `Verified (tests)`) stay exactly as they are — purely additive.
- [ ] `/new-feature.md` workflow doc updated to mention `make bdd` in Phase 5.4 alongside the verify-e2e agent invocation.

**Edge Cases:**

| Condition                                                                 | Expected Behavior                                                                |
| ------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| BDD suite is empty (rare — only if Feature 1's scenarios all get deleted) | Gate still passes (0 of 0); CI / Feature 2 catches this                          |
| No `.feature` files yet                                                   | `make bdd` exits 0 with "no features" message (cucumber-js default); gate passes |
| Some scenarios pending (annotated `@wip`)                                 | Cucumber marks them as skipped; suite exits 0; Feature 2 can flag                |

**Priority:** Should Have (the gate-vocabulary change is polish; manual checklist is acceptable for Feature 1 ship)

---

### US-BDD-005: Feature 2 consumes the BDD output

**As a** future Feature 2 maintainer
**I want** Feature 1 to produce machine-readable output Feature 2 can consume
**So that** I don't have to retrofit the `.feature` tree or runner output

**Scenario:**

```gherkin
Given the BDD suite produces cucumber JSON output at test-results/cucumber.json
When Feature 2's analyzer is implemented
Then it parses features/scenarios/tags from the JSON directly
And also parses the `.feature` file tree (for static analysis of anti-patterns)
And both sources align 1:1 — no retrofit needed
```

**Acceptance Criteria:**

- [ ] `pnpm bdd` emits **both** `test-results/cucumber.json` (legacy JSON formatter, human-browsable) **and** `test-results/cucumber.ndjson` (Cucumber-Messages NDJSON — future-proof, maintained formatter). Feature 2's analyzer picks its parser without forcing a Feature 1 rewrite.
- [ ] `test-results/` is gitignored (it's a runtime artifact).
- [ ] `.feature` file structure is consistent enough that a Gherkin parser can walk the tree without per-file special cases (no weird indentation; UTF-8; LF line endings).
- [ ] File/scenario naming is stable — no duplicate scenario titles across files (Feature 2 may key on them).

**Priority:** Nice to Have (Feature 2 can define its own parser; alignment is a courtesy)

---

## 5. Technical Constraints

### Known Limitations

- **Servers reused, not spawned.** The BDD suite does NOT start backend/frontend. Caller is responsible for `make backend` + `make frontend` running on canonical or env-override ports.
- **No `@playwright/test` infrastructure.** Cucumber-js uses the `playwright` library directly; no access to `@playwright/test` fixtures, no `webServer` auto-start, no Playwright HTML reporter (Cucumber's own JSON/pretty + optional HTML reporter adapter).
- **Browser lifecycle is our responsibility.** Hooks (`BeforeAll` / `Before` / `After` / `AfterAll`) construct + tear down browser/context/page. Per-scenario context for isolation; shared browser for speed.
- **Existing 2 `.spec.ts` files will be deleted.** `frontend/tests/e2e/specs/play-round.spec.ts` and `no-forfeit-terminal.spec.ts` are re-expressed as `.feature` scenarios. `playwright.config.ts` stays (Feature 3 may reuse it for coverage wiring) but will have no specs to run.
- **No parallelism tuning.** `cucumber-js --parallel N` left at default (1). Single-user scale; no shared-state gotchas.
- **Edge-case coverage at BDD layer is representative, not exhaustive.** Full parametric malicious-input coverage stays in pytest (per discussion Q5).
- **BDD backend runs with test-mode word pool.** The backend exposes a `HANGMAN_WORDS_FILE` env var (documented test-mode knob, not a production surface) pointing at `backend/words.test.txt`. The test pool uses production category names (`animals`, `food`, `tech`) but collapses each to the word `"cat"`, which makes Easy/Medium/Hard WIN+LOSS scenarios deterministic across all three difficulties. Operators start the BDD backend with `make backend-test` (or set the env var themselves) before running `make bdd`. Default behavior (env var unset) is unchanged — production pool loads as before. See design spec §2b.

### Dependencies

- **Requires:** Hangman scaffold (Feature 0) on master. Backend + frontend runnable locally.
- **Blocked by:** None.

### Integration Points

- **`playwright`** library (not `@playwright/test`) — pin `^1.59.0` in lockstep with the already-installed `@playwright/test` to avoid browser-version drift. Driver for UI steps.
- **`@cucumber/cucumber`** — pin `^12.8.1` (current stable, cucumber-js 12.x line). Requires Node ≥ 20 — matches our Node 22 pin.
- **`tsx`** (NOT `ts-node`) — transpiles TS step defs at runtime via cucumber-js's `import` option. Pin `~4.19` (tsx ships frequently; narrow tilde pin protects against churn).
- **Backend HTTP API** — reached from step defs via Playwright's `APIRequestContext` (no separate `node-fetch` / `axios` dependency needed).
- **Node `engines` pin** — `"engines": {"node": ">=20"}` in `frontend/package.json` to prevent silent drift below cucumber-js 12's floor.

## 6. Data Requirements

### New Data Models

None. `.feature` files are plain-text Gherkin; step definitions are TS modules; `test-results/cucumber.json` is cucumber-js's standard output schema.

### Data Validation Rules

- `.feature` files MUST be UTF-8, LF line endings, valid Gherkin.
- Every scenario MUST have at least one primary tag (`@happy` | `@failure` | `@edge`).
- No scenario MAY carry two primary tags simultaneously (style guide; Feature 2 enforces; Feature 1 documents).

### Data Migration

- **`tests/e2e/use-cases/hangman-scaffold.md` (the markdown UC file from Feature 0)** stays in place. Feature 1 adds `.feature` expressions of the same UCs but doesn't delete the markdown. Rationale: the markdown UCs are consumed by the verify-e2e agent for exploratory regression (Q9 — gates are additive).
- **`frontend/tests/e2e/specs/play-round.spec.ts` + `no-forfeit-terminal.spec.ts`** are DELETED after the `.feature` equivalents pass.

## 7. Security Considerations

- **Authentication:** N/A (hangman has no auth).
- **Authorization:** N/A.
- **Data Protection:** No new secrets. Step defs read `HANGMAN_BACKEND_PORT` / `HANGMAN_FRONTEND_PORT` env vars only.
- **Audit:** N/A.
- **Test data:** No fixtures; scenarios ARRANGE via the public API per `rules/testing.md` ARRANGE boundary. No raw DB writes, no internal/undocumented endpoints.

## 8. Open Questions

- [ ] **Shared vs per-scenario browser context.** Lean: per-scenario context from a shared browser. Final decision in Phase 3 brainstorming.
- [ ] **Gate-automation scope.** Do we add `BDD suite passed` to `check-workflow-gates.sh` in Feature 1, or leave as manual checklist? Lean: manual in F1, automate in F2 when the dashboard artifact provides the evidence.

Both resolve at plan-writing time; neither blocks PRD approval.

## 9. References

- **Discussion Log:** `docs/prds/bdd-suite-discussion.md`
- **Three-feature split context:** chat conversation 2026-04-23 (features 1/2/3 split)
- **Feature 0 (scaffold) PRD:** `docs/prds/hangman-scaffold.md`
- **Existing Playwright specs being converted:** `frontend/tests/e2e/specs/play-round.spec.ts`, `frontend/tests/e2e/specs/no-forfeit-terminal.spec.ts`
- **Existing markdown UCs:** `frontend/tests/e2e/use-cases/hangman-scaffold.md`
- **Rules to update:** `.claude/rules/testing.md` (add BDD gate entry alongside `E2E verified`)
- **Dashboard target (Feature 2 scope, not this PRD):** `/Users/keithstegbauer/Downloads/bdd_dashboard_example.html`
- **Discovery research:**
  - [Tudip — Playwright + Cucumber + TypeScript Setup](https://tudip.com/blog_post/playwright-cucumber-typescript-setup/)
  - [Tallyb/cucumber-playwright](https://github.com/Tallyb/cucumber-playwright)
  - [Shaun English — Modern E2E with Cucumber + Playwright + TS](https://medium.com/@english87/modern-e2e-testing-with-cucumber-playwright-typescript-7a7ab6cd3d54)
  - [ortoniKC/Playwright_Cucumber_TS](https://github.com/ortoniKC/Playwright_Cucumber_TS)
  - [playwright-bdd](https://vitalets.github.io/playwright-bdd/) — surveyed, rejected in Q1

---

## Appendix A: Revision History

| Version | Date       | Author      | Changes                                                                                                                                                                                                                                                                                                                                                                                            |
| ------- | ---------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.0     | 2026-04-23 | Claude + KC | Initial PRD                                                                                                                                                                                                                                                                                                                                                                                        |
| 1.1     | 2026-04-23 | Claude + KC | Post-research corrections: (a) `ts-node/register` → `tsx` via cucumber-js `import` option (ts-node is stale; cucumber docs recommend tsx in 2026); (b) emit BOTH legacy `json` + modern `message` NDJSON formatters (legacy is maintenance mode; NDJSON is future-proof); (c) Node `engines: ">=20"` pin added (cucumber-js 12 dropped Node 18). Sources: `docs/research/2026-04-23-bdd-suite.md`. |

## Appendix B: Approval

- [ ] Product Owner approval
- [ ] Technical Lead approval
- [ ] Ready for technical design
