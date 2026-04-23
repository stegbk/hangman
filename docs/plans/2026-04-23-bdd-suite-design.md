# Design: BDD Suite

**Date:** 2026-04-23
**Status:** Approved (sections 1–7)
**PRD:** `docs/prds/bdd-suite.md` (v1.1)
**Research brief:** `docs/research/2026-04-23-bdd-suite.md`

This is the technical design for Feature 1 of the three-feature BDD plan — install pure `@cucumber/cucumber` infrastructure, express every endpoint + every UC as `.feature` files with typed step definitions, and delete the two existing `@playwright/test` specs they replace. Features 2 (dashboard) and 3 (branch coverage) are separate PRDs and out of scope here.

---

## Summary of load-bearing decisions

Locked by PRD v1.1 + research + brainstorming, restated here so the design reads cold:

- **Pure `@cucumber/cucumber` v12.8.1** — not `playwright-bdd`, not `@playwright/test`. Chosen for documentation quality (KC explicit, PRD discussion Q1).
- **`playwright` library v1.59** (not `@playwright/test`) — drives browsers. Lockstepped with the already-installed `@playwright/test` version.
- **`tsx` v4.19** (not `ts-node`) — cucumber-js loads TypeScript step defs via `import: ["tsx/esm", ...]`. Research brief P1-1.
- **Dual reporters** — `json:test-results/cucumber.json` (legacy, human-browsable) + `message:test-results/cucumber.ndjson` (Cucumber-Messages NDJSON, future-proof for Feature 2 analyzer). Research brief P1-2.
- **Node ≥ 20 engines pin** — cucumber-js 12 floor. Research brief P1-3.
- **File structure C** — one `.feature` per endpoint (6 files) + one per UI flow (4 files). PRD Q2.
- **Scenarios are fullstack** — `Given` API setup + `When/Then` UI work in the same scenario. PRD Q4.
- **Tag set frozen at `{@happy, @failure, @edge, @smoke}`** — primary tags mutually exclusive; `@smoke` orthogonal. PRD Q3.
- **Edge coverage at BDD is representative** — full parametric malicious-input coverage stays in pytest. PRD Q5.
- **Reuse running servers** — BDD suite does NOT spawn backend/frontend. Step defs read `HANGMAN_BACKEND_PORT` / `HANGMAN_FRONTEND_PORT` env vars; `Before` hook fails fast if unreachable. PRD Q-pre + brainstorming §3.
- **Browser lifecycle: shared browser, per-scenario context+page** (clarifying Q option A). Fresh context per scenario = fresh cookies = session isolation.
- **Gate automation: manual checklist in Feature 1** (clarifying Q option A). `rules/testing.md` adds a new canonical entry; hook enforcement deferred to Feature 2 when there's a dashboard artifact to evidence against.
- **Delete `frontend/tests/e2e/specs/play-round.spec.ts` + `no-forfeit-terminal.spec.ts`** — replaced by `play-round.feature` + `forfeit.feature`. Keep `playwright.config.ts` + the markdown UC file + the `auth.ts` stub (Feature 3 + verify-e2e agent still use them).
- **Single viable architecture** — the PRD + research brief pre-determined it. Brainstorming surfaced the two sub-variations (browser lifecycle + gate scope). Contrarian gate will validate we didn't miss a third option.

---

## 1. Architecture

```
frontend/
├── cucumber.cjs                          # cucumber-js config (CommonJS for zero-ESM-loader hassle)
├── tests/
│   └── bdd/
│       ├── features/                     # 10 .feature files
│       │   ├── categories.feature        # GET /categories
│       │   ├── session.feature           # GET /session
│       │   ├── games.feature             # POST /games + forfeit transactions
│       │   ├── games-current.feature     # GET /games/current
│       │   ├── guesses.feature           # POST /games/{id}/guesses
│       │   ├── history.feature           # GET /history + pagination bounds
│       │   ├── play-round.feature        # UC1 — happy-path end-to-end UI
│       │   ├── loss-resets-streak.feature # UC2
│       │   ├── forfeit.feature           # UC3 + UC3b (forfeit IN_PROGRESS + no-confirm-on-terminal)
│       │   ├── mid-game-reload.feature   # UC4
│       │   └── difficulty-levels.feature # Per-difficulty WIN/LOSS mistake counts (requires test word pool)
│       ├── steps/
│       │   ├── api.ts                    # Given/When/Then API steps
│       │   ├── ui.ts                     # Given/When/Then UI steps (Playwright page)
│       │   └── shared.ts                 # cross-cutting steps + @dialog-tracked Before hook
│       └── support/
│           ├── world.ts                  # HangmanWorld custom World class
│           └── hooks.ts                  # BeforeAll/Before/After/AfterAll — browser lifecycle
├── package.json                          # + scripts.bdd, + deps, + engines.node
├── tests/e2e/
│   ├── specs/                            # EMPTY after deletion
│   ├── use-cases/hangman-scaffold.md     # STAYS — verify-e2e agent consumes it
│   └── fixtures/auth.ts                  # STAYS — template extension point
└── playwright.config.ts                  # STAYS — Feature 3 will reuse for coverage wiring
```

Root changes:

```
Makefile                                  # + make bdd target (passes HANGMAN_WORDS_FILE through)
.claude/rules/testing.md                  # + "BDD suite passed" entry (additive)
backend/words.test.txt                    # NEW — one-word "test" pool for per-difficulty BDD determinism
backend/src/hangman/main.py               # + HANGMAN_WORDS_FILE env var support (~5 LOC in lifespan)
```

**Why `tests/bdd/` is separate from `tests/e2e/`**: additive gates. The markdown UC file is consumed by the `verify-e2e` agent for exploratory regression; unifying would orphan it. Two test trees, two gates, parallel coverage.

---

## 2. `cucumber.cjs` + `package.json`

### `frontend/cucumber.cjs`

```js
module.exports = {
  default: {
    paths: ["tests/bdd/features/**/*.feature"],
    import: ["tsx/esm"], // tsx, NOT ts-node (research P1-1)
    require: ["tests/bdd/steps/**/*.ts", "tests/bdd/support/**/*.ts"],
    format: [
      "progress-bar",
      "json:test-results/cucumber.json", // legacy — human browsable
      "message:test-results/cucumber.ndjson", // future-proof NDJSON for Feature 2
    ],
    formatOptions: { snippetInterface: "async-await" },
    strict: true, // undefined steps fail the run
    failFast: false, // collect all failures per run
    parallel: 0, // serial; single-user scale
  },
};
```

### `frontend/package.json` additions

```jsonc
{
  "engines": { "node": ">=20" }, // cucumber-js 12 floor
  "scripts": {
    // ...existing...
    "bdd": "cucumber-js",
  },
  "devDependencies": {
    // ...existing...
    "@cucumber/cucumber": "^12.8.1",
    "playwright": "^1.59.0", // lockstep with @playwright/test
    "tsx": "~4.19", // tilde: tsx ships frequently
  },
}
```

### Root `Makefile` addition

```makefile
bdd:
	cd frontend && HANGMAN_BACKEND_PORT=$(HANGMAN_BACKEND_PORT) HANGMAN_FRONTEND_PORT=$(HANGMAN_FRONTEND_PORT) pnpm bdd
```

`make verify` deliberately does NOT invoke `bdd` (PRD Q7).

---

## 2b. Backend test-mode word file support

**Problem:** The current `words.txt` has 45 production words across animals/food/tech. Only 5 letters (`j`, `v`, `w`, `x`, `z`) never appear in any `animals/easy` seed word, which gives us deterministic coverage for **hard-difficulty LOSS only** (4 mistakes). Medium (6) and Easy (8) LOSS scenarios can't be tested deterministically against production words — too few "always-miss" letters.

**Fix:** Let the backend load a caller-specified word file when `HANGMAN_WORDS_FILE` is set in the environment. BDD sets it to `backend/words.test.txt` — a file with the **same category names** as production (`animals`, `food`, `tech`) but each containing the single word `cat`. Against that pool, any letter except `c`/`a`/`t` is a guaranteed miss regardless of category, so per-difficulty LOSS at any mistake count is deterministic AND `categories.feature` scenarios that assert the production category set continue to pass.

### `backend/words.test.txt`

```
# BDD test-mode word pool. Loaded when HANGMAN_WORDS_FILE points at this file.
#
# Category names match production (animals/food/tech) so scenarios that assert
# the category list keep passing. Contents collapse to one word ("cat") so:
#   WIN  → guess c, a, t (3 correct, 0 mistakes, difficulty-invariant)
#   LOSS → guess any 4/6/8 letters NOT in "cat" (hard/medium/easy lives_total)
animals,cat
food,cat
tech,cat
```

### `backend/src/hangman/main.py` — lifespan change

Existing lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(engine)
    words_path = Path(__file__).resolve().parent.parent.parent / "words.txt"
    app.state.word_pool = load_words(words_path)
    yield
```

New lifespan (deliberately minimal — 5 effective LOC added):

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(engine)
    backend_root = Path(__file__).resolve().parent.parent.parent
    override = os.environ.get("HANGMAN_WORDS_FILE")
    words_path = Path(override) if override else backend_root / "words.txt"
    if not words_path.is_absolute():
        words_path = (backend_root / words_path).resolve()
    app.state.word_pool = load_words(words_path)
    yield
```

**Contract points:**

- Relative `HANGMAN_WORDS_FILE` values resolve against `backend/` (the file's conceptual root). Absolute values pass through untouched.
- `load_words()` already raises `FileNotFoundError` if the path doesn't exist → fails fast at startup with a clear error.
- When unset, behavior is byte-for-byte identical to today (production read of `backend/words.txt`).
- The env var is **documented as a test-mode knob** in the PRD `§5 Technical Constraints` — not a production surface. No runtime toggle, no endpoint flip.

### `Makefile` — pass-through

```makefile
bdd:
	cd frontend && HANGMAN_BACKEND_PORT=$(HANGMAN_BACKEND_PORT) HANGMAN_FRONTEND_PORT=$(HANGMAN_FRONTEND_PORT) pnpm bdd

backend-test:
	cd backend && HANGMAN_WORDS_FILE=words.test.txt uv run uvicorn hangman.main:app --reload --port $(or $(HANGMAN_BACKEND_PORT),8000)
```

BDD operators start the backend with `make backend-test` (test-mode pool) instead of `make backend` (production pool) before running `make bdd`. The README + CONTRIBUTING docs get a one-paragraph note: "when running the BDD suite, start the backend with `make backend-test`."

### Why this is safe

- **ARRANGE-allowed:** `HANGMAN_WORDS_FILE` is a **public, documented configuration knob** (PRD §5) — not an internal endpoint, not a DB write, not a file injection. It's exactly the pattern `rules/testing.md` ARRANGE allows under "documented seed/bootstrap commands."
- **VERIFY unaffected:** Scenarios still assert through user-facing API responses and UI state. No backdoor assertions.
- **No production coupling:** Default path unchanged; if the env var is unset or empty, zero behavior differs.
- **Already grep-clean:** no competing env var names in the repo; `HANGMAN_BACKEND_PORT` / `HANGMAN_FRONTEND_PORT` / `HANGMAN_DB_URL` is the established `HANGMAN_*` convention.

---

## 3. World class + hooks (browser lifecycle A)

One shared browser (launched in `BeforeAll`, closed in `AfterAll`). Fresh `context` + `page` per scenario — the Playwright-idiomatic isolation primitive. Critical for session-cookie isolation: UC2 must not see UC1's cookie.

### `frontend/tests/bdd/support/world.ts`

```ts
import { World, IWorldOptions, setWorldConstructor } from "@cucumber/cucumber";
import type {
  Browser,
  BrowserContext,
  Page,
  APIRequestContext,
  APIResponse,
} from "playwright";

export class HangmanWorld extends World {
  public browser!: Browser;
  public context!: BrowserContext;
  public page!: Page;
  public apiRequest!: APIRequestContext;

  public lastApiResponse: APIResponse | null = null;
  public lastApiBody: unknown = null;

  get backendUrl(): string {
    const port = process.env.HANGMAN_BACKEND_PORT ?? "8000";
    return `http://localhost:${port}`;
  }

  get frontendUrl(): string {
    const port = process.env.HANGMAN_FRONTEND_PORT ?? "3000";
    return `http://localhost:${port}`;
  }

  constructor(options: IWorldOptions) {
    super(options);
  }
}

setWorldConstructor(HangmanWorld);
```

### `frontend/tests/bdd/support/hooks.ts`

```ts
import { BeforeAll, Before, After, AfterAll, Status } from "@cucumber/cucumber";
import { chromium, request, type Browser } from "playwright";
import type { HangmanWorld } from "./world";

let sharedBrowser: Browser;

async function assertBackendReachable(backendUrl: string): Promise<void> {
  try {
    const res = await fetch(`${backendUrl}/api/v1/categories`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch (err) {
    throw new Error(
      `Backend not reachable at ${backendUrl}/api/v1/categories — did you run ` +
        `\`make backend\`${process.env.HANGMAN_BACKEND_PORT ? ` (HANGMAN_BACKEND_PORT=${process.env.HANGMAN_BACKEND_PORT})` : ""}? ` +
        `Underlying error: ${(err as Error).message}`,
    );
  }
}

BeforeAll(async function () {
  sharedBrowser = await chromium.launch();
});

AfterAll(async function () {
  await sharedBrowser?.close();
});

Before(async function (this: HangmanWorld) {
  await assertBackendReachable(this.backendUrl);
  this.browser = sharedBrowser;
  this.context = await sharedBrowser.newContext();
  this.page = await this.context.newPage();
  this.apiRequest = await request.newContext({ baseURL: this.backendUrl });
  this.lastApiResponse = null;
  this.lastApiBody = null;
});

After(async function (this: HangmanWorld, { result }) {
  if (result?.status === Status.FAILED && this.page) {
    const buf = await this.page.screenshot();
    this.attach(buf, "image/png"); // embedded in NDJSON stream
  }
  await this.apiRequest?.dispose();
  await this.page?.close();
  await this.context?.close();
});
```

**Design notes:**

- `apiRequest` and `page.request` coexist: `apiRequest` is isolated (fresh baseURL context, doesn't share UI cookies). `page.request` shares the UI's cookie jar. Scenarios choose per-step which they need; default is `page.request` for cookie-shared API calls; `apiRequest` for hooks + health checks.
- `assertBackendReachable` fires in `Before` (per-scenario), not `BeforeAll`. Trade-off: ~50ms added per scenario for a clear "did you `make backend`?" error the FIRST time something breaks instead of a cryptic `ECONNREFUSED` inside a step.
- Screenshot on failure via `this.attach()` → lands in NDJSON stream. Feature 2 can surface these inline in the dashboard.

---

## 4. Step definitions (three files, ~30 step registrations total)

Step text is written from the user's perspective — no implementation details (no "SQL query," "FastAPI route," "React re-render").

### `frontend/tests/bdd/steps/api.ts`

- `Given I start a new game with category {string} and difficulty {string}` — `POST /api/v1/games`, stores response on `this.lastApiResponse`/`this.lastApiBody`
- `Given I guess the letter {string}` — `POST /api/v1/games/{id}/guesses` using the id from `this.lastApiBody`
- `When I request {string}` — generic `GET`
- `When I POST to the current game's guesses endpoint with body:` — doc-string body; uses current game id from `lastApiBody` (**NOT the `{id}` URL-template form** — cleaner Gherkin)
- `When I POST to {string} with body:` — generic `POST` for non-game endpoints
- `Then the response status is {int}`
- `Then the response error code is {string}` — asserts `body.error.code`
- `Then the response body has {string} equal to {string}` — dot-path traversal for nested fields
- `Then the response body field {string} is absent` — PRD US-001 `word`-key-absent enforcement
- `Then the Set-Cookie header contains {string}` — for cookie-attribute assertions

### `frontend/tests/bdd/steps/ui.ts`

- `Given I open the app` — `page.goto(frontendUrl)` + wait for `score-panel` testid
- `When I click the {string} button` — `getByTestId(testid).click()`
- `When I click the keyboard letter {string}` — `getByTestId("keyboard-letter-<letter>").click()` (implements the Phase-5.1 `guessPending` sync barrier: wait for re-enable before next click; terminal check before)
- `When I select category {string}` — `getByTestId("category-select").selectOption(...)`
- `When I select difficulty {string}` — clicks `difficulty-<easy|medium|hard>` radio
- `When I reload the page` — `page.reload()`
- `Then I see the score panel` — visibility on `score-panel` testid
- `Then the total score is {string}` — `getByTestId("score-total").toHaveText(...)`
- `Then the current streak is {string}` — `getByTestId("streak-current").toHaveText(...)`
- `Then I see a terminal game banner` — `or()`-locator on `game-won` | `game-lost`
- `Then I see the game-{string} banner` — specific terminal state
- `Then history contains {int} item(s)` — count `[data-testid^='history-item-']`
- `Then no dialog has fired` — asserts `this.dialogCount === 0` (set up in shared.ts `@dialog-tracked` hook)

### `frontend/tests/bdd/steps/shared.ts`

- `Given the backend and frontend are running` — documentation step (no-op; `Before` hook already verified)
- `Before({ tags: '@dialog-tracked' })` — attaches `page.on('dialog', ...)` handler + `this.dialogCount` counter; used by UC3b

**Vocabulary discipline:** ~30 step registrations total. If scenario authors need a 31st step for one specific scenario, refactor — either make it reusable or compose from existing steps. The PRD's "user-observable behavior" principle rules the vocabulary.

---

## 5. `.feature` files (33 scenarios across 11 files)

### Scenario distribution

| File                         | `@happy` | `@failure`               | `@edge`               | `@smoke` (overlap) | Total  |
| ---------------------------- | -------- | ------------------------ | --------------------- | ------------------ | ------ |
| `categories.feature`         | 2        | 0                        | 1                     | 1                  | 3      |
| `session.feature`            | 2        | 0                        | 1                     | 1                  | 3      |
| `games.feature`              | 2        | 1 (bad category)         | 1 (forfeit chain)     | 1                  | 4      |
| `games-current.feature`      | 1        | 1 (404 no active)        | 1 (cross-session 404) | 1                  | 3      |
| `guesses.feature`            | 2        | 2 (already-guessed, 409) | 1 (invalid letter)    | 1                  | 5      |
| `history.feature`            | 2        | 0                        | 2 (empty, pagination) | 1                  | 4      |
| `play-round.feature`         | 1        | 0                        | 0                     | 1                  | 1      |
| `loss-resets-streak.feature` | 1        | 0                        | 0                     | 0                  | 1      |
| `forfeit.feature`            | 2        | 0                        | 0                     | 2                  | 2      |
| `mid-game-reload.feature`    | 1        | 0                        | 0                     | 0                  | 1      |
| `difficulty-levels.feature`  | 6        | 0                        | 0                     | 1                  | 6      |
| **Total**                    | **22**   | **4**                    | **6**                 | **10**             | **33** |

Meets PRD §2 success metrics: per-endpoint ≥ 1 of each primary tag; per UC ≥ 1 scenario.

### Per-difficulty determinism (`difficulty-levels.feature`)

Six scenarios cover the mistake-counter contract across all three difficulties in the UI, using the test-mode word pool (§2b). Structure:

| Scenario                 | Difficulty | lives_total | Guesses                           | Expected outcome |
| ------------------------ | ---------- | ----------- | --------------------------------- | ---------------- |
| `@happy` Easy WIN        | easy       | 8           | `c, a, t`                         | GAME_WON         |
| `@happy` Easy LOSS       | easy       | 8           | `b, d, e, f, g, h, i, j` (8 miss) | GAME_LOST        |
| `@happy` Medium WIN      | medium     | 6           | `c, a, t`                         | GAME_WON         |
| `@happy` Medium LOSS     | medium     | 6           | `b, d, e, f, g, h` (6 miss)       | GAME_LOST        |
| `@happy @smoke` Hard WIN | hard       | 4           | `c, a, t`                         | GAME_WON         |
| `@happy` Hard LOSS       | hard       | 4           | `b, d, e, f` (4 miss)             | GAME_LOST        |

All six scenarios use category `"animals"` against the test-mode pool (§2b). Because every production category in `words.test.txt` collapses to the single word `"cat"`, the category name doesn't affect determinism — we standardize on `"animals"` for readability and to mirror the scaffold's Phase-5.1 UC patterns. This exercises:

- The API contract for `lives_total` across all three difficulty values (API-layer assertion via `Then the response body has "lives_total" equal to "<N>"`)
- The UI's displayed mistake counter ticking up per miss (via `Then I see "<N> mistakes remaining"` on the `score-panel` testid)
- The terminal-state banner rendering correctly for both WIN and LOSS at each difficulty

Hard WIN gets `@smoke` overlap — it's the minimum per-file coverage and the cheapest sanity check that the test-mode pool + difficulty wiring is live.

**Why no `@failure` or `@edge` here:** the six scenarios are happy-path verifications of the game's core difficulty mechanics. Mistake-count validation at the API layer (422 on malformed `difficulty`) already lives in `guesses.feature`/`games.feature`. Adding failure scenarios here would duplicate coverage.

### Style guide (encoded per-file)

- Every file opens with `Feature: <title>` + 2-4 line prose description of the endpoint or flow's user-observable purpose.
- Every scenario has `Given` (precondition) + `When` (action) + `Then` (assertion). `And`/`But` allowed only after one of these.
- Every scenario carries exactly one primary tag (`@happy` | `@failure` | `@edge`). `@smoke` is orthogonal and optional.
- `Background:` used when all scenarios in a file share setup (e.g., `guesses.feature` uses `Given I start a new game with category "animals" and difficulty "easy"` as Background — "cat" under the test-mode pool).
- `Scenario Outline:` used SPARINGLY — only when user-observable inputs genuinely vary in a way that'd be documented as "a class of inputs" (e.g., pagination bounds). Full parametric validation stays in pytest (PRD Q5).

### Hermetic determinism

The entire BDD suite runs against the §2b test-mode pool (`HANGMAN_WORDS_FILE=words.test.txt`). Every category collapses to the word `"cat"`, which gives the suite a single source of truth for guess outcomes:

- **WIN in any category / any difficulty:** guess `c, a, t` → 3 correct, 0 mistakes → GAME_WON
- **LOSS in any category at difficulty D:** guess `lives_total(D)` letters from the 23-letter set `alphabet \ {c, a, t}` → GAME_LOST
- **Partial progress:** any letter in `{c, a, t}` → correct; any other letter → miss

This removes the 15-letter marathon that `play-round.feature` (UC1) would otherwise need against the production `animals/easy` pool — UC1 now wins in 3 clicks. UC2 (loss-resets-streak) loses in 4 clicks against `animals/hard`. UC3b (forfeit LOSS) uses the same 4-letter `b, d, e, f` miss set as `difficulty-levels.feature` Hard LOSS — consistent pattern across files.

The one trade-off: UC1's scenario prose reads "guess c, a, t" instead of documenting the full 15-letter happy-path against a realistic animals seed. This is intentional — BDD is the **contract** layer, and the contract is "happy path wins"; word-content realism lives in the verify-e2e agent's markdown UC against production data. Parallel coverage (§7 Layer 4).

**Conftest compatibility:** The scaffold's pytest `test_word_pool` fixture (in-memory `"test": ("cat",)`) is unchanged — it remains the pytest-layer source of truth for unit/integration tests. `words.test.txt` is the BDD-layer equivalent, serving the same word through the real HTTP surface.

---

## 6. Deletion + integration

### Files deleted

- `frontend/tests/e2e/specs/play-round.spec.ts` → replaced by `play-round.feature`
- `frontend/tests/e2e/specs/no-forfeit-terminal.spec.ts` → replaced by UC3b scenario in `forfeit.feature`

### Files kept (additive-gates posture)

- `frontend/tests/e2e/use-cases/hangman-scaffold.md` — verify-e2e agent's input
- `frontend/tests/e2e/fixtures/auth.ts` — stub, extension point
- `frontend/playwright.config.ts` — Feature 3 reuses for coverage wiring

### `.claude/rules/testing.md` — additive gate vocabulary

Add a new block alongside `E2E verified`:

```markdown
### BDD suite vocabulary (additive, 2026-04-23 — Feature bdd-suite)

| Gate element     | Canonical form                                      |
| ---------------- | --------------------------------------------------- |
| Marker stem      | `BDD suite passed`                                  |
| Checklist entry  | `- [ ] BDD suite passed (Phase 5.4 — \`make bdd\`)` |
| Checked (passed) | `- [x] BDD suite passed (Phase 5.4 — \`make bdd\`)` |
| Checked as N/A   | `- [x] BDD suite passed — N/A: <reason>`            |

**Feature 1 scope:** manual checklist only. `check-workflow-gates.sh` is NOT modified. Feature 2's dashboard artifact enables hook enforcement.
```

### `/new-feature.md` workflow doc

Phase 5.4 gets a sibling `5.4bdd` step documenting `make bdd` (side-by-side with the verify-e2e subagent invocation). Manual checkbox update on green.

### Artifact shape

- `frontend/test-results/cucumber.json` and `cucumber.ndjson` — runtime artifacts, gitignored.
- Failure screenshots embedded in NDJSON stream via `this.attach()` — no separate directory.

---

## 7. Testing strategy

### Layer 1 — Step-def unit tests

**Default: none.** Step defs are thin. If a step def's helper grows (e.g., a non-trivial JSON-path DSL), extract to `frontend/src/bdd-helpers/` + add vitest. Not anticipated in v1.

### Layer 2 — BDD scenarios (the feature itself)

27 scenarios × 10 feature files. These ARE the tests. Run via `make bdd` against the live backend+frontend. Acceptance for Phase 5 exit: all 27 green, suite < 60s, no `undefined step` errors (cucumber strict mode catches these).

### Layer 3 — Pytest + Vitest untouched

- Backend: 172 tests (108 unit + 64 integration after Phase-5.1's edge-case expansion). No changes.
- Frontend: 28 vitest. No changes.

### Layer 4 — verify-e2e agent untouched

Continues running markdown UCs in `tests/e2e/use-cases/`. Parallel coverage.

### Phase 3.2b E2E classification

**E2E: N/A — test infrastructure.** The feature's success criterion IS that the BDD suite runs green. The 27 scenarios are the E2E coverage, not the E2E _target_. The Phase 5 checklist will mark:

```
- [x] E2E verified — N/A: Feature IS the E2E infrastructure; the 27 BDD scenarios in frontend/tests/bdd/features/ are its verification. `make bdd` green = feature verified.
```

### Quality gates summary

| Gate                       | Command                                   | Phase                     |
| -------------------------- | ----------------------------------------- | ------------------------- |
| Backend unit + integration | `make verify` → `uv run pytest`           | 5.3                       |
| Backend lint + types       | `make verify` → `ruff + mypy`             | 5.3                       |
| Frontend unit              | `make verify` → `pnpm test:run`           | 5.3                       |
| Frontend lint + types      | `make verify` → `eslint + prettier + tsc` | 5.3                       |
| **BDD suite**              | **`make bdd` (requires live servers)**    | **5.4bdd (new)**          |
| verify-e2e agent           | Task tool → `verify-e2e` subagent         | 5.4 (parallel, unchanged) |

All gates must be green before PR.

---

## 8. Non-goals / deferred

Reaffirming PRD non-goals + design-specific deferrals:

- No dashboard (Feature 2)
- No call graph / branch coverage / gap detection (Feature 3)
- No `playwright-bdd` adapter (PRD Q1 — pure cucumber-js chosen)
- No `@playwright/test` fixtures (`auth.ts` stays as stub)
- No pytest-bdd or Python BDD runner
- No parallelism tuning
- No CI/CD integration (local-only)
- No hook enforcement in Feature 1 (manual checklist; Feature 2 adds teeth)
- No migration of pytest parametrized edge tests to Gherkin (PRD Q5)
- No replacement of verify-e2e agent (PRD Q9 — additive)
- No step-def unit tests unless a helper grows

---

## 9. Open questions

None. Both PRD §8 items resolved in brainstorming:

- Browser lifecycle → option A (shared browser, per-scenario context+page)
- Gate automation → manual in F1, hook enforcement in F2

---

## 10. References

- **PRD:** `docs/prds/bdd-suite.md` (v1.1)
- **PRD discussion:** `docs/prds/bdd-suite-discussion.md`
- **Research brief:** `docs/research/2026-04-23-bdd-suite.md`
- **Scaffold context:** `docs/prds/hangman-scaffold.md` + `docs/plans/2026-04-22-hangman-scaffold-design.md`
- **Phase 5.1 patterns carried forward:** `guessPending` sync barrier, `j/v/x/z` rare-miss set, `test` deterministic category, dialog-count for UC3b
- **Project rules:** `.claude/rules/{api-design,testing,principles}.md`
