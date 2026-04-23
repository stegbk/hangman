# PRD Discussion: BDD Suite

**Status:** Complete
**Started:** 2026-04-23
**Completed:** 2026-04-23
**Participants:** User (KC), Claude

## Original User Stories

From user in chat (2026-04-23):

> I would like to run an integration/e2e test suite using cucumber. The goal is that I have BDD testing for project documentation and that I can evaluate the coverage and generate coverage reports like: `/Users/keithstegbauer/Downloads/bdd_dashboard_example.html` to monitor the progress.
>
> Use playwright. Build a custom analyzer, it should involve generating a call graph and ensuring that every branch and edge case is covered in the BDDs.

Scope split into **three sequential features**:

- **Feature 1 (this PRD):** `bdd-suite` — cucumber infrastructure + convert existing UCs + per-endpoint coverage. **No dashboard, no call graph.**
- **Feature 2:** `bdd-dashboard` — static analyzer + HTML generator matching KC's dashboard example.
- **Feature 3:** `bdd-branch-coverage` — call graph + `coverage.py --branch --contexts` + gap detection.

Pre-settled decisions (from chat, pre-discussion):

| #   | Decision                                                                        | Value                                                             |
| --- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| 1   | `.feature` files location                                                       | `frontend/tests/bdd/features/`                                    |
| 2   | Existing Playwright specs (`play-round.spec.ts`, `no-forfeit-terminal.spec.ts`) | **Convert to `.feature` form** (replace, not augment)             |
| 3   | Scenario tags                                                                   | `@happy`, `@failure`, `@edge`, `@smoke` — committed from day one  |
| 4   | Step definition language                                                        | TypeScript                                                        |
| 5   | Test run — server strategy                                                      | Reuse running backend/frontend (same as current Playwright setup) |

## Phase 0 — Discovery Research

Sources:

- [Tudip — Playwright + Cucumber + TypeScript Setup](https://tudip.com/blog_post/playwright-cucumber-typescript-setup/)
- [Tallyb/cucumber-playwright](https://github.com/Tallyb/cucumber-playwright) — reference repo, pure cucumber-js + `playwright` library
- [Shaun English — Modern E2E with Cucumber + Playwright + TS](https://medium.com/@english87/modern-e2e-testing-with-cucumber-playwright-typescript-7a7ab6cd3d54)
- [ortoniKC/Playwright_Cucumber_TS](https://github.com/ortoniKC/Playwright_Cucumber_TS)
- [playwright-bdd (third-party Playwright runner for Cucumber)](https://vitalets.github.io/playwright-bdd/)

Two architectural options surfaced by the research:

### Option A — Pure `@cucumber/cucumber` (cucumber-js runner)

- `@cucumber/cucumber` is the test runner; it discovers `.feature` files and dispatches to step definitions.
- `playwright` (the library, not `@playwright/test`) provides browser automation inside step defs.
- Step defs use Cucumber's `Given / When / Then` registration API.
- Custom hooks (`Before` / `After`) manage browser lifecycle.
- **Loss vs current setup:** no `@playwright/test` fixtures, no automatic `webServer` start, no parallelism out of the box (cucumber-js has its own parallelism but configured separately), no Playwright HTML report.
- **Gain:** pure Gherkin test runner; clean separation of scenarios from driver code; standard Cucumber reporters (JSON, pretty, HTML).

### Option B — `playwright-bdd` adapter

- Third-party package (`playwright-bdd`, ~240 GitHub stars, active maintenance, recent 2026 compatibility).
- **Compiles `.feature` files into generated Playwright spec files at build time.** These generated specs are run by `@playwright/test`.
- Step definitions written in TS using Cucumber's expressions.
- **Keeps everything we already have:** `@playwright/test` runner, fixtures (`auth.ts`), `webServer` array, HTML reporter, trace/screenshot on failure, parallelism.
- **Cost:** extra build step (`bddgen`) before each run; an extra dependency with a narrower community than canonical cucumber-js.

### Recommendation

**Option B (`playwright-bdd`)** fits this project's existing investment. We already have `@playwright/test` + webServer config + auth fixture stub, and the 2 existing Playwright specs were just landed in Feature 0 (the scaffold). Replacing them means rewriting infrastructure; extending them via `playwright-bdd` preserves the sync barriers we just perfected.

Option A is cleaner architecturally but would force us to re-solve: server auto-start, fixture composition, parallelism, trace/screenshot, the `guessPending` sync-barrier pattern. That's ~4 hours of rework before we even start writing `.feature` files.

I'll propose Option B as the default and surface Option A in the Contrarian gate.

## Discussion Log

### Round 1 — Targeted Questions (2026-04-23)

The big 5 pre-settled; these fill in the remaining gaps.

**Architecture**

1. **`playwright-bdd` vs pure `@cucumber/cucumber` (research finding above)?** Recommendation: `playwright-bdd` to preserve the webServer + fixture + parallelism investment. Agree?
2. **`.feature` file organization.** Three possible structures under `frontend/tests/bdd/features/`:
   - **A (by layer):** `api/categories.feature`, `api/games.feature`, `ui/play-round.feature`, `ui/forfeit.feature`. Step defs under `frontend/tests/bdd/steps/{api,ui}/*.ts`.
   - **B (by user story):** `us-001-pick-and-play.feature`, `us-002-score-streak.feature`, etc. Mirrors PRD structure.
   - **C (by endpoint/flow hybrid):** `categories.feature`, `session.feature`, `games.feature`, `guesses.feature`, `history.feature`, `play-round.feature` (the UI flow UCs). Groups scenarios by the endpoint or UI area they exercise.
     My lean: **C** — matches how Feature 2's dashboard will analyze coverage ("is there a scenario for every endpoint's happy+failure+edge path?"). Agree, or different?

**Scope / coverage**

3. **Per-endpoint coverage target:** for each of the 6 endpoints, we'd aim for minimum `@happy` + `@failure` (one failure/error-path scenario) + `@edge` (one boundary or malicious input). Is 3 scenarios per endpoint the baseline? Or do you want a richer matrix (happy + multiple failures + multiple edges)?
4. **Existing UC1-UC4 + UC3b conversion scope.** Should these stay as full fullstack scenarios (API setup + UI interaction + UI verification), or should we split each into "API-only" and "UI-only" `.feature` scenarios? My lean: **keep them as fullstack** scenarios with `Given` steps calling the API (setup) and `When/Then` steps doing UI work. More natural Gherkin reading; matches the PRD UC definitions.
5. **Parametrized/tabular scenarios.** Your P2 plan-review fix for Phase 5.1 added 28 malicious-letter parametrized tests. Cucumber's equivalent is `Scenario Outline` with `Examples:` tables. Should the `.feature` files mirror that (one `Scenario Outline` per invalid-letter family with an Examples table of 20+ bad letters), or should those stay as `pytest.mark.parametrize` integration tests and not be duplicated in Gherkin?
   My lean: **don't duplicate.** Integration tests already lock the validation contract at speed; `.feature` files should express _user-observable_ behavior, not Pydantic-layer shape testing. One `@edge` scenario per endpoint with a few canonical invalid inputs is enough at the BDD layer.

**Tooling**

6. **Runner command.** `pnpm bdd` (new top-level script) or nested under `pnpm test:bdd`? Should `make bdd` exist at the root? My lean: `pnpm bdd` in the frontend package + a `make bdd` target that delegates (matches existing `make backend` / `make frontend` pattern).
7. **CI / PR ceremony hook.** Feature 2 adds dashboard generation to the PR ceremony. For Feature 1, should `make verify` include `pnpm bdd` (slowing down verify from ~1.5s to maybe ~30s), or should BDD stay as a separate `make bdd` target invoked only in Phase 5.4? My lean: keep `make verify` fast (unit + lint + type only); add BDD to Phase 5.4 E2E phase.
8. **Report format for local viewing.** Playwright-bdd inherits `@playwright/test`'s HTML reporter by default. Fine, or do you want Cucumber's native JSON + pretty output for Feature 2's analyzer to consume directly?

**Gate semantics**

9. **Should this feature update the E2E gate in `rules/testing.md`?** Currently the gate says "E2E verified via verify-e2e agent (Phase 5.4)." With `.feature` files as the authoritative UC format, should the gate evolve to "BDD suite passed"? Or does the BDD suite become _additional_ coverage on top of the existing markdown UC + verify-e2e gate?
   My lean: **add, don't replace, in Feature 1.** The verify-e2e agent + markdown UCs stay for exploratory verification. Feature 1 just adds `.feature` files as a parallel artifact. We can consolidate later once Feature 2's dashboard proves the `.feature` files are authoritative.

**Success metrics**

10. **What does "done" look like for Feature 1?**
    - All 6 endpoints have ≥1 `@happy` + ≥1 `@failure` scenario in `.feature` files?
    - All 5 existing UCs (UC1/UC2/UC3/UC3b/UC4) expressed as `.feature` scenarios?
    - `pnpm bdd` passes against live servers?
    - Coverage for each scenario tag asserted (e.g. count `@happy` = 6+, `@failure` ≥ 6, etc.)?
    - Anything else?

---

### Round 1 — Answers (2026-04-23)

| Q   | Decision                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Source                               |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| 1   | **Pure `@cucumber/cucumber` runner** (NOT `playwright-bdd`). Reason: documentation quality — `.feature` files are first-class artifacts consumed by standard Cucumber tooling (reports, IDE plugins, future BDD coverage analyzer in Feature 2).                                                                                                                                                                                                                            | User explicit, overrides Claude lean |
| 2   | Structure **C** — endpoint/flow hybrid. One `.feature` per backend endpoint or UI flow: `categories.feature`, `session.feature`, `games.feature`, `games-current.feature`, `guesses.feature`, `history.feature`, `play-round.feature` (UC1), `forfeit.feature` (UC3/3b), `mid-game-reload.feature` (UC4), `loss-resets-streak.feature` (UC2).                                                                                                                               | User explicit                        |
| 3   | Per-endpoint baseline: **≥1 `@happy` + ≥1 `@failure` + ≥1 `@edge`** scenario.                                                                                                                                                                                                                                                                                                                                                                                               | User explicit                        |
| 4   | Existing UCs (UC1, UC2, UC3, UC3b, UC4) stay as **fullstack scenarios** — API setup in `Given`, UI interactions in `When/Then`.                                                                                                                                                                                                                                                                                                                                             | User explicit                        |
| 5   | **Do NOT duplicate** the pytest parametrized malicious-letter tests into Gherkin. BDD expresses user-observable behavior; Pydantic shape validation stays in integration tests. `@edge` in Gherkin = one representative case per endpoint.                                                                                                                                                                                                                                  | User explicit                        |
| 6   | **Both** `pnpm bdd` (frontend package script) and `make bdd` (root Makefile target delegating).                                                                                                                                                                                                                                                                                                                                                                             | User explicit                        |
| 7   | `make verify` does NOT include `pnpm bdd`. Keeps verify fast (~1.5s lint+types+units); BDD runs in Phase 5.4 E2E gate via `make bdd`.                                                                                                                                                                                                                                                                                                                                       | User explicit                        |
| 8   | Report format for Feature 1: Cucumber's native output — `json` + `pretty` formatters. Feature 2's analyzer will consume the JSON directly. No Playwright-bdd HTML reporter (since we're on pure cucumber-js).                                                                                                                                                                                                                                                               | Claude default (accepted)            |
| 9   | New BDD gate **ADDS** to existing E2E gate. Both stay green: verify-e2e agent + markdown UCs continue for exploratory work; `.feature` files become the authoritative regression artifact. `rules/testing.md` updated to reference both.                                                                                                                                                                                                                                    | User explicit                        |
| 10  | Done-definition (Claude proposed, user implicit-accept by advancing past): (a) all 6 endpoints have ≥1 `@happy` + `@failure` + `@edge`; (b) UC1/2/3/3b/4 expressed as `.feature` scenarios; (c) `pnpm bdd` + `make bdd` pass against live servers on env-override ports; (d) existing `play-round.spec.ts` + `no-forfeit-terminal.spec.ts` deleted (converted to `.feature`); (e) CONTINUITY + CHANGELOG + README updated; (f) `rules/testing.md` gate vocabulary extended. | Claude proposed                      |

## Implication of Q1 (pure cucumber-js)

Choosing pure `@cucumber/cucumber` over `playwright-bdd` means we **do not inherit** the `@playwright/test` infrastructure we landed in Feature 0. Specifically:

- **No automatic `webServer` array** — cucumber-js doesn't start servers. Either: (a) require servers already running (reuse), or (b) start them in `BeforeAll` hooks. Per Q (pre-discussion), we're going with **reuse**: `make bdd` assumes `make backend` + `make frontend` are already running on whatever ports (canonical 8000/3000 or env-override 8002/3001).
- **No `@playwright/test` fixtures** (`auth.ts` etc.). Replaced with Cucumber's `Before` / `After` hooks that construct `browser`/`context`/`page` per scenario using the `playwright` library directly (not `@playwright/test`).
- **Different parallelism model** — cucumber-js has `--parallel N` flag; no shared-state gotchas at single-user scale.
- **Different reporter ecosystem** — native `json` + `pretty`; HTML reporters exist (`@cucumber/pretty-formatter`, `cucumber-html-reporter`) but are separate from Playwright's.
- **Existing `.spec.ts` files are deleted** — `play-round.spec.ts` and `no-forfeit-terminal.spec.ts` are re-expressed as `.feature` scenarios; the old `@playwright/test` specs go away. `playwright.config.ts` stays for future use (and for Feature 3's coverage hook) but has no specs to run.

This is more invasive than `playwright-bdd` would have been but gives us **pure Gherkin as the single source of truth for E2E/UC regression** — aligns with KC's stated goal of BDD-as-documentation.

## Refined Understanding

### Personas

- **Developer (KC, or future contributors)** — writes `.feature` scenarios as living documentation of user-observable behavior. Runs `make bdd` locally during Phase 5.4 E2E to validate regressions.
- **Claude / implementation subagents** — read `.feature` files to understand expected behavior when implementing changes. Tests-as-documentation.
- **Future Feature 2 dashboard analyzer** — parses `.feature` files statically and consumes Cucumber's JSON report for runtime metrics.

### User Stories (Refined)

- **US-BDD-001** As a developer, I can run `pnpm bdd` (or `make bdd`) and see every `.feature` scenario pass against the live backend+frontend.
- **US-BDD-002** As a developer, I can read any `.feature` file and understand what a user can do with that endpoint or flow — Gherkin serves as documentation.
- **US-BDD-003** As a developer, I can grep scenario tags (`@happy` / `@failure` / `@edge` / `@smoke`) to see coverage for any dimension.
- **US-BDD-004** As a Feature 2 maintainer, I can consume the `.feature` files' structure (features, scenarios, tags) to generate a coverage dashboard.
- **US-BDD-005** As a developer running CI locally (Phase 5.4), the BDD suite passing is part of the ship gate alongside the existing verify-e2e agent.

### Non-Goals

- ❌ Dashboard generation (that's Feature 2)
- ❌ Branch coverage / call graph / gap detection (that's Feature 3)
- ❌ Migrating pytest integration tests to Gherkin (Q5)
- ❌ Replacing or gating the verify-e2e agent (Q9 — additive, not replacement)
- ❌ `playwright-bdd` adapter (Q1 — we chose pure cucumber-js)
- ❌ CI/CD pipeline integration (local-only per user stated goals)
- ❌ Parallelism tuning beyond defaults (single-user scale doesn't need it)

### Key Decisions

1. **Pure `@cucumber/cucumber` + `playwright` library** — not `@playwright/test`, not `playwright-bdd`.
2. **One `.feature` per endpoint or UI flow** (structure C). ~10 `.feature` files expected.
3. **Scenarios are fullstack** — `Given` calls the API for setup; `When/Then` drive the UI via `playwright`.
4. **Tags from day one**: `@happy` / `@failure` / `@edge` / `@smoke`. Future dashboard relies on these.
5. **Edge cases stay representative at the BDD layer** — full parametric coverage stays in pytest.
6. **Servers reused, not spawned** — `make bdd` requires `make backend` + `make frontend` already running.
7. **`make verify` stays fast** — no BDD in the pre-commit speed loop.
8. **Report format: Cucumber JSON + pretty**.
9. **BDD gate is additive** — doesn't replace verify-e2e or markdown UCs.
10. **Existing `.spec.ts` files deleted** — Gherkin is the single E2E source of truth going forward.

### Open Questions (Remaining)

- [ ] **Browser lifecycle in hooks** — single browser shared across scenarios (faster) vs per-scenario browser (cleaner isolation)? Claude default: per-scenario `context` from a shared `browser` — matches Playwright best practice.
- [ ] **Server port detection** — should `Given` steps read `HANGMAN_BACKEND_PORT` / `HANGMAN_FRONTEND_PORT` env vars (matches current Makefile), or hardcode canonical `localhost:8000`/`:3000`? Claude default: env-var read with canonical defaults — mirrors `vite.config.ts` + `playwright.config.ts` pattern.

Both are implementation-layer; resolve in the plan.

---

Ready for `/prd:create bdd-suite`.
