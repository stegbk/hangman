# BDD Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install pure `@cucumber/cucumber` v12 infrastructure in `frontend/`, express every backend endpoint + every UI use case as 33 `.feature` scenarios across 11 feature files, and wire the test-mode word pool so Easy/Medium/Hard WIN+LOSS are all deterministic.

**Architecture:** Cucumber-js drives the Playwright `playwright` library (not `@playwright/test`) against already-running backend + frontend servers. Backend is started with `HANGMAN_WORDS_FILE=words.test.txt` so the word pool collapses to `"cat"` in every production category, giving one deterministic source of truth for all guess outcomes. Hooks own the browser lifecycle (shared browser, per-scenario context+page). Dual Cucumber reporters (JSON legacy + NDJSON Messages) produce machine-readable output for Feature 2's analyzer later.

**Tech Stack:**

- `@cucumber/cucumber@^12.8.1` — test runner + reporters
- `playwright@^1.59.0` — browser driver (lockstep with the already-installed `@playwright/test`)
- `tsx@~4.19` — on-the-fly TypeScript loader for step defs (not `ts-node` — research brief P1-1)
- `cucumber.cjs` config (CommonJS, zero ESM-loader hassle)
- Node ≥ 20 (cucumber-js 12 floor — research P1-3)
- Backend: Python 3.12 + FastAPI (existing scaffold; 5-LOC lifespan patch for test-mode pool)

**Spec reference:** `docs/plans/2026-04-23-bdd-suite-design.md`
**PRD:** `docs/prds/bdd-suite.md`
**Research:** `docs/research/2026-04-23-bdd-suite.md`

---

## File Structure

### Created by this plan

```
backend/
├── words.test.txt                           # BDD test-mode word pool (3 production
│                                             categories, each collapsed to "cat")
└── tests/unit/test_words_file_env.py        # pytest coverage of HANGMAN_WORDS_FILE

frontend/
├── cucumber.cjs                             # cucumber-js config
└── tests/bdd/
    ├── features/                            # 11 .feature files, 33 scenarios
    │   ├── categories.feature
    │   ├── session.feature
    │   ├── games.feature
    │   ├── games-current.feature
    │   ├── guesses.feature
    │   ├── history.feature
    │   ├── play-round.feature
    │   ├── loss-resets-streak.feature
    │   ├── forfeit.feature
    │   ├── mid-game-reload.feature
    │   └── difficulty-levels.feature
    ├── steps/
    │   ├── api.ts                           # 12 API step registrations
    │   ├── ui.ts                            # 15 UI step registrations
    │   └── shared.ts                        # 1 no-op + @dialog-tracked Before hook
    └── support/
        ├── world.ts                         # HangmanWorld custom World class
        └── hooks.ts                         # BeforeAll/Before/After/AfterAll

docs/solutions/2026-04-23-bdd-suite.md       # Learning snapshot (Phase 6)
```

### Modified by this plan

```
backend/src/hangman/main.py                  # + HANGMAN_WORDS_FILE env var (lifespan)
frontend/package.json                        # + deps, + engines.node, + scripts.bdd
frontend/.gitignore                          # + test-results/ (or repo-root .gitignore)
Makefile                                     # + make backend-test, + make bdd
.claude/rules/testing.md                     # + "BDD suite passed" vocabulary entry
README.md                                    # + one-paragraph "Running BDD locally" section
CONTINUITY.md                                # + Phase state updates (per task)
```

### Deleted by this plan

```
frontend/tests/e2e/specs/play-round.spec.ts          # replaced by play-round.feature
frontend/tests/e2e/specs/no-forfeit-terminal.spec.ts # replaced by forfeit.feature scenario 2
```

### Untouched (verified preserved)

```
frontend/tests/e2e/use-cases/hangman-scaffold.md   # verify-e2e agent input
frontend/tests/e2e/fixtures/auth.ts                # Playwright fixtures stub
frontend/playwright.config.ts                      # Feature 3 will reuse
backend/words.txt                                  # Production pool, unchanged
backend/tests/conftest.py                          # pytest fixtures, unchanged
```

---

## E2E classification (Phase 3.2b)

**E2E: N/A — test infrastructure.** The 33 BDD scenarios in `frontend/tests/bdd/features/` are themselves the E2E coverage for this feature. There is no user-facing surface to exercise with the `verify-e2e` agent beyond "does the BDD suite run green," and that's already the feature's acceptance criterion.

Phase 5 checklist entry:

```
- [x] E2E verified — N/A: Feature IS the E2E infrastructure; the 33 BDD scenarios in frontend/tests/bdd/features/ are its verification. `make bdd` green = feature verified.
```

---

## Task 1: Backend `HANGMAN_WORDS_FILE` env var + `words.test.txt`

**Files:**

- Create: `backend/words.test.txt`
- Create: `backend/tests/unit/test_words_file_env.py`
- Modify: `backend/src/hangman/main.py` (lifespan)

This task extends the backend's startup so the word pool can be sourced from a caller-specified file when `HANGMAN_WORDS_FILE` is set. Without this, Easy/Medium WIN+LOSS UI scenarios cannot be made deterministic (design §2b).

- [ ] **Step 1: Create `backend/words.test.txt` with the test-mode pool**

Write exactly this content to `backend/words.test.txt`:

```
# BDD test-mode word pool. Loaded when HANGMAN_WORDS_FILE points at this file.
#
# Category names match production (animals/food/tech) so scenarios that assert
# the category list keep passing. Contents collapse to one word ("cat") so:
#   WIN  -> guess c, a, t (3 correct, 0 mistakes, difficulty-invariant)
#   LOSS -> guess any 4/6/8 letters NOT in "cat" (hard/medium/easy lives_total)
animals,cat
food,cat
tech,cat
```

- [ ] **Step 2: Write the failing pytest test**

Create `backend/tests/unit/test_words_file_env.py` with:

```python
"""Tests for the HANGMAN_WORDS_FILE env-var override in the FastAPI lifespan."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _write_pool(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "words.test.txt"
    p.write_text(body, encoding="utf-8")
    return p


def test_env_var_unset_loads_production_pool(monkeypatch):
    monkeypatch.delenv("HANGMAN_WORDS_FILE", raising=False)
    from hangman.main import app

    with TestClient(app) as client:
        # Public API surface exposes category names only, not per-category
        # word counts. Production pool has multiple words per category, so
        # we verify via direct state inspection.
        names = client.get("/api/v1/categories").json()["categories"]
        pool = client.app.state.word_pool

    assert set(names) == {"animals", "food", "tech"}
    assert len(pool.categories["animals"]) > 1


def test_env_var_absolute_path_loads_caller_pool(monkeypatch, tmp_path):
    pool_file = _write_pool(tmp_path, "animals,cat\nfood,cat\ntech,cat\n")
    monkeypatch.setenv("HANGMAN_WORDS_FILE", str(pool_file))
    from hangman.main import app

    with TestClient(app) as client:
        names = client.get("/api/v1/categories").json()["categories"]
        pool = client.app.state.word_pool

    assert set(names) == {"animals", "food", "tech"}
    # All three categories collapsed to exactly one word under the test pool.
    assert all(len(words) == 1 for words in pool.categories.values())


def test_env_var_relative_path_resolves_against_backend_root(monkeypatch):
    # Depends on backend/words.test.txt existing (shipped in Step 1).
    monkeypatch.setenv("HANGMAN_WORDS_FILE", "words.test.txt")
    from hangman.main import app

    with TestClient(app) as client:
        pool = client.app.state.word_pool

    assert all(len(words) == 1 for words in pool.categories.values())


def test_env_var_missing_file_raises_at_startup(monkeypatch):
    monkeypatch.setenv("HANGMAN_WORDS_FILE", "/does/not/exist.txt")
    from hangman.main import app

    with pytest.raises(FileNotFoundError):
        with TestClient(app):
            pass  # lifespan startup should raise before the context yields
```

- [ ] **Step 3: Run the test, expect FAIL**

```bash
cd backend && uv run pytest tests/unit/test_words_file_env.py -v
```

Expected: 3 of 4 tests FAIL — the current lifespan ignores `HANGMAN_WORDS_FILE` entirely and always loads `backend/words.txt`, so:

- `test_env_var_unset_loads_production_pool` — PASSES (lifespan already loads production when unset).
- `test_env_var_absolute_path_loads_caller_pool` — FAILS (pool still has >1 word per category).
- `test_env_var_relative_path_resolves_against_backend_root` — FAILS (same reason).
- `test_env_var_missing_file_raises_at_startup` — FAILS (no `FileNotFoundError` raised; lifespan continues).

- [ ] **Step 4: Patch `backend/src/hangman/main.py` lifespan**

Replace the existing file content with:

```python
"""FastAPI app assembly + lifespan."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from hangman.db import engine
from hangman.errors import RequestIdMiddleware, install_error_handlers
from hangman.models import Base
from hangman.routes import router
from hangman.words import load_words


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


app = FastAPI(lifespan=lifespan, title="Hangman API", version="0.1.0")
app.add_middleware(RequestIdMiddleware)
install_error_handlers(app)
app.include_router(router)
```

- [ ] **Step 5: Run the test, expect PASS**

```bash
cd backend && uv run pytest tests/unit/test_words_file_env.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 6: Run full backend suite to verify no regressions**

```bash
cd backend && uv run pytest
```

Expected: full green. The existing 172 tests don't set `HANGMAN_WORDS_FILE`, so they fall through to the production-pool branch — same behavior as before.

- [ ] **Step 7: Commit**

```bash
git add backend/words.test.txt backend/tests/unit/test_words_file_env.py backend/src/hangman/main.py
git commit -m "feat(backend): HANGMAN_WORDS_FILE env var for BDD test-mode pool

Lifespan now honors HANGMAN_WORDS_FILE (optional absolute or relative path;
relative values resolve against backend/). Default behavior unchanged when
unset — production words.txt loads as before.

Ships backend/words.test.txt: same category names (animals/food/tech) as
production but each collapsed to one word (\"cat\") so Easy/Medium/Hard
WIN+LOSS UI scenarios become deterministic under cucumber.

Covered by tests/unit/test_words_file_env.py (4 tests: unset, absolute,
relative, missing-file)."
```

---

## Task 2: Frontend BDD dependencies + `cucumber.cjs` + `package.json`

**Files:**

- Modify: `frontend/package.json`
- Create: `frontend/cucumber.cjs`
- Create: `frontend/tests/bdd/features/.gitkeep`
- Create: `frontend/tests/bdd/steps/.gitkeep`
- Create: `frontend/tests/bdd/support/.gitkeep`

- [ ] **Step 1: Edit `frontend/package.json`**

Add the `engines` field (or merge with existing), add `bdd` script, add three devDependencies. Final state of the affected regions:

```jsonc
{
  // ...existing fields unchanged...
  "engines": {
    "node": ">=20",
  },
  "scripts": {
    // ...existing scripts unchanged...
    "bdd": "cucumber-js",
  },
  "devDependencies": {
    // ...existing devDependencies unchanged...
    "@cucumber/cucumber": "^12.8.1",
    "playwright": "^1.59.0",
    "tsx": "~4.19",
  },
}
```

- [ ] **Step 2: Install the new dependencies**

```bash
cd frontend && pnpm install
```

Expected: the 3 new deps resolve and install cleanly. The lockfile is updated. `pnpm-lock.yaml` shows new entries under `devDependencies`.

- [ ] **Step 3: Create `frontend/cucumber.cjs`**

Write exactly this content:

```js
module.exports = {
  default: {
    paths: ["tests/bdd/features/**/*.feature"],
    import: ["tsx/esm"],
    require: ["tests/bdd/steps/**/*.ts", "tests/bdd/support/**/*.ts"],
    format: [
      "progress-bar",
      "json:test-results/cucumber.json",
      "message:test-results/cucumber.ndjson",
    ],
    formatOptions: { snippetInterface: "async-await" },
    strict: true,
    failFast: false,
    parallel: 0,
  },
};
```

- [ ] **Step 4: Create the BDD directory structure**

```bash
cd frontend && mkdir -p tests/bdd/features tests/bdd/steps tests/bdd/support
touch tests/bdd/features/.gitkeep tests/bdd/steps/.gitkeep tests/bdd/support/.gitkeep
```

- [ ] **Step 5: Add `test-results/` to frontend `.gitignore`**

If `frontend/.gitignore` exists, append `test-results/`. Otherwise edit the repo-root `.gitignore` and add:

```
frontend/test-results/
```

Verify it's ignored:

```bash
cd frontend && mkdir -p test-results && touch test-results/cucumber.json && git status --porcelain test-results/
```

Expected: no output (file ignored).

```bash
rm -rf frontend/test-results
```

- [ ] **Step 6: Smoke-run cucumber to confirm the runner starts**

```bash
cd frontend && pnpm bdd --dry-run
```

Expected output includes "0 scenarios" and exits 0. No `.feature` files yet = no scenarios to dry-run, which is correct.

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml frontend/cucumber.cjs \
        frontend/tests/bdd/features/.gitkeep \
        frontend/tests/bdd/steps/.gitkeep \
        frontend/tests/bdd/support/.gitkeep \
        .gitignore
[ -f frontend/.gitignore ] && git add frontend/.gitignore
git commit -m "feat(bdd): scaffold cucumber-js + playwright + tsx deps

- @cucumber/cucumber ^12.8.1, playwright ^1.59.0 (lockstep with
  @playwright/test), tsx ~4.19 (not ts-node; research brief P1-1).
- cucumber.cjs with dual JSON+NDJSON reporters, strict mode, serial.
- Node >=20 engines pin (cucumber-js 12 floor; research P1-3).
- Empty tests/bdd/{features,steps,support} dirs; test-results/ gitignored."
```

---

## Task 3: Makefile `make backend-test` + `make bdd`

**Files:**

- Modify: `Makefile`

- [ ] **Step 1: Edit `Makefile`**

Find the `.PHONY: ...` line at the top and append `backend-test bdd` to the list. Then append two new targets at the end of the file.

After `.PHONY:` line edit:

```makefile
.PHONY: install backend backend-test frontend bdd test lint typecheck verify clean
```

Append at the end of the file (after the existing `clean` target):

```makefile
# BDD test-mode backend: isolated SQLite file (so BDD runs never touch the
# production hangman.db) + test-mode word pool (one-word "cat" per category).
backend-test:
	cd backend && \
	HANGMAN_WORDS_FILE=words.test.txt \
	HANGMAN_DB_URL=sqlite:///$(CURDIR)/backend/hangman.test.db \
	uv run uvicorn hangman.main:app --reload --host 127.0.0.1 --port $(HANGMAN_BACKEND_PORT)

bdd:
	cd frontend && \
	HANGMAN_BACKEND_PORT=$(HANGMAN_BACKEND_PORT) \
	HANGMAN_FRONTEND_PORT=$(HANGMAN_FRONTEND_PORT) \
	pnpm bdd
```

Add `backend/hangman.test.db*` to `.gitignore` (root) so SQLite `-wal` / `-shm` sidecar files don't get committed either:

```bash
grep -qxF 'backend/hangman.test.db*' .gitignore || echo 'backend/hangman.test.db*' >> .gitignore
```

**Port conflict note:** `make backend` and `make backend-test` both bind `$(HANGMAN_BACKEND_PORT)`. You cannot run both simultaneously on the same port — stop `make backend` before running `make backend-test`, or override the port on one of them (e.g., `make backend-test HANGMAN_BACKEND_PORT=8001`).

- [ ] **Step 2: Dry-run both targets to verify they expand correctly**

```bash
make -n backend-test
make -n bdd
```

Expected output for `backend-test` (line-continuations normalized — shape matters, not whitespace):

```
cd backend && HANGMAN_WORDS_FILE=words.test.txt HANGMAN_DB_URL=sqlite:///<repo-root>/backend/hangman.test.db uv run uvicorn hangman.main:app --reload --host 127.0.0.1 --port 8000
```

Expected output for `bdd`:

```
cd frontend && HANGMAN_BACKEND_PORT=8000 HANGMAN_FRONTEND_PORT=3000 pnpm bdd
```

- [ ] **Step 3: Run `make backend-test` briefly to verify the backend starts with the test pool**

Open a second terminal. In the worktree root:

```bash
make backend-test
```

In the first terminal:

```bash
sleep 2 && curl -s http://localhost:8000/api/v1/categories | python -m json.tool
```

Expected: JSON with exactly 3 items (`animals`, `food`, `tech`) each with `word_count: 1`.

Stop the backend with `Ctrl+C` in the second terminal.

- [ ] **Step 4: Commit**

```bash
git add Makefile
git commit -m "feat(make): add backend-test + bdd targets

- 'make backend-test' boots backend with HANGMAN_WORDS_FILE=words.test.txt
  so the BDD suite gets the deterministic one-word pool.
- 'make bdd' runs the cucumber-js suite with port env-var pass-through.
- Both targets honor HANGMAN_BACKEND_PORT / HANGMAN_FRONTEND_PORT
  overrides (SSH-tunnel users etc.)."
```

---

## Task 4: `HangmanWorld` class (`frontend/tests/bdd/support/world.ts`)

**Files:**

- Create: `frontend/tests/bdd/support/world.ts`

- [ ] **Step 1: Write `world.ts`**

```ts
/**
 * HangmanWorld — custom World shared across every scenario's steps.
 *
 * Each scenario gets a fresh context+page+apiRequest (see hooks.ts), so this
 * is where per-scenario state — the last API response, the last parsed body —
 * lives. Lifecycle rules: `browser` is shared (BeforeAll/AfterAll);
 * `context`, `page`, and `apiRequest` are per-scenario (Before/After).
 */
import {
  World,
  type IWorldOptions,
  setWorldConstructor,
} from "@cucumber/cucumber";
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

  public dialogCount = 0;

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

- [ ] **Step 2: Typecheck**

```bash
cd frontend && pnpm exec tsc --noEmit
```

Expected: no errors. (The `!` definite-assignment on `browser`/`context`/`page`/`apiRequest` is intentional — they're assigned in the `Before` hook before any step runs.)

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/bdd/support/world.ts
git commit -m "feat(bdd): HangmanWorld custom World class

Per-scenario state carrier (lastApiResponse, lastApiBody, dialogCount).
Shared browser, per-scenario context/page/apiRequest. Reads
HANGMAN_{BACKEND,FRONTEND}_PORT env vars for URL composition."
```

---

## Task 5: Browser-lifecycle hooks (`frontend/tests/bdd/support/hooks.ts`)

**Files:**

- Create: `frontend/tests/bdd/support/hooks.ts`

- [ ] **Step 1: Write `hooks.ts`**

```ts
/**
 * Browser lifecycle + per-scenario isolation for the BDD suite.
 *
 * Lifecycle choice (design §3, browser-lifecycle A):
 *   - Shared browser (BeforeAll/AfterAll)            — fast
 *   - Per-scenario context+page (Before/After)       — isolates cookies
 *
 * BeforeAll pings both servers once so the suite fails fast with a clear
 * "did you run make backend-test / make frontend?" message instead of a
 * cryptic ECONNREFUSED deep inside a scenario. Once per run is enough —
 * the servers don't come and go mid-suite.
 */
import { BeforeAll, Before, After, AfterAll, Status } from "@cucumber/cucumber";
import { chromium, request, type Browser } from "playwright";
import type { HangmanWorld } from "./world";

let sharedBrowser: Browser;

function backendUrl(): string {
  return `http://localhost:${process.env.HANGMAN_BACKEND_PORT ?? "8000"}`;
}

function frontendUrl(): string {
  return `http://localhost:${process.env.HANGMAN_FRONTEND_PORT ?? "3000"}`;
}

async function assertReachable(
  label: "backend" | "frontend",
  url: string,
  makeTarget: "make backend-test" | "make frontend",
  portEnvName: "HANGMAN_BACKEND_PORT" | "HANGMAN_FRONTEND_PORT",
): Promise<void> {
  try {
    const res = await fetch(url);
    // The frontend root may return 404 for some SPA configurations but the
    // TCP connect and HTTP response are both fine — that's reachable enough
    // for our purposes. We only fail on thrown errors (ECONNREFUSED etc).
    void res;
  } catch (err) {
    const portHint = process.env[portEnvName]
      ? ` (${portEnvName}=${process.env[portEnvName]})`
      : "";
    throw new Error(
      `${label[0].toUpperCase() + label.slice(1)} not reachable at ${url} — did you run ` +
        `\`${makeTarget}\`${portHint}? Underlying error: ${(err as Error).message}`,
    );
  }
}

BeforeAll(async function () {
  // Fail-fast BEFORE launching chromium; cheaper for CI if servers are down.
  await assertReachable(
    "backend",
    `${backendUrl()}/api/v1/categories`,
    "make backend-test",
    "HANGMAN_BACKEND_PORT",
  );
  await assertReachable(
    "frontend",
    frontendUrl(),
    "make frontend",
    "HANGMAN_FRONTEND_PORT",
  );
  sharedBrowser = await chromium.launch();
});

AfterAll(async function () {
  await sharedBrowser?.close();
});

Before(async function (this: HangmanWorld) {
  this.browser = sharedBrowser;
  this.context = await sharedBrowser.newContext();
  this.page = await this.context.newPage();
  this.apiRequest = await request.newContext({ baseURL: this.backendUrl });
  this.lastApiResponse = null;
  this.lastApiBody = null;
  this.dialogCount = 0;
});

After(async function (this: HangmanWorld, { result }) {
  if (result?.status === Status.FAILED && this.page) {
    const buf = await this.page.screenshot();
    this.attach(buf, "image/png");
  }
  await this.apiRequest?.dispose();
  await this.page?.close();
  await this.context?.close();
});
```

- [ ] **Step 2: Typecheck**

```bash
cd frontend && pnpm exec tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/bdd/support/hooks.ts
git commit -m "feat(bdd): browser-lifecycle hooks

- BeforeAll/AfterAll own the shared chromium browser.
- Before/After create fresh context+page+apiRequest per scenario.
- assertBackendReachable fires once per scenario — trades ~50ms for a
  clear 'did you run make backend-test?' error on ECONNREFUSED.
- Failure screenshots auto-attach to the cucumber NDJSON stream."
```

---

## Task 6: Shared steps + `@dialog-tracked` hook (`frontend/tests/bdd/steps/shared.ts`)

**Files:**

- Create: `frontend/tests/bdd/steps/shared.ts`

- [ ] **Step 1: Write `shared.ts`**

```ts
/**
 * Cross-cutting steps and hooks.
 *
 * Three dialog hooks are registered on mutually-exclusive tags:
 *
 *   @dialog-accept  → listener hits OK on every window.confirm / alert.
 *                     Use in UC3 forfeit (user confirms they want to
 *                     abandon the active game).
 *
 *   @dialog-reject  → listener hits Cancel. Use for the "user cancelled"
 *                     branch of any confirm flow.
 *
 *   @dialog-tracked → listener only counts dialogs without handling them.
 *                     Use when the scenario asserts that NO dialog fired
 *                     (e.g., UC3b where starting a new game after a loss
 *                     must skip the forfeit confirm entirely). An
 *                     unexpected dialog will also block subsequent
 *                     Playwright actions — the desired loud-failure.
 *
 * Scenarios must pick exactly one of the three tags if they interact
 * with any confirm()/alert(). `this.dialogCount` is reset in the
 * per-scenario Before hook in support/hooks.ts.
 */
import { Given, Then, Before } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import type { HangmanWorld } from "../support/world";

// A no-op, documentation-only step. The Before hook in support/hooks.ts
// has already asserted backend reachability; this just reads nicely in
// Gherkin scenarios ("Given the backend and frontend are running").
Given("the backend and frontend are running", function (this: HangmanWorld) {
  // intentionally empty
});

// Mutex guard: cucumber runs every matching Before hook, so a scenario
// accidentally tagged with two @dialog-* tags would register two listeners
// and behave unpredictably. Fail the scenario loudly instead.
Before(
  {
    tags: "(@dialog-accept and @dialog-reject) or (@dialog-accept and @dialog-tracked) or (@dialog-reject and @dialog-tracked)",
  },
  function () {
    throw new Error(
      "Scenario has multiple @dialog-* tags. Pick exactly one of @dialog-accept, @dialog-reject, @dialog-tracked.",
    );
  },
);

Before({ tags: "@dialog-accept" }, async function (this: HangmanWorld) {
  this.page.on("dialog", async (dialog) => {
    this.dialogCount += 1;
    await dialog.accept();
  });
});

Before({ tags: "@dialog-reject" }, async function (this: HangmanWorld) {
  this.page.on("dialog", async (dialog) => {
    this.dialogCount += 1;
    await dialog.dismiss();
  });
});

Before({ tags: "@dialog-tracked" }, async function (this: HangmanWorld) {
  this.page.on("dialog", async (_dialog) => {
    this.dialogCount += 1;
    // Deliberately unhandled — see module-level comment.
  });
});

Then("no dialog has fired", function (this: HangmanWorld) {
  expect(this.dialogCount).toBe(0);
});

Then("a dialog has fired", function (this: HangmanWorld) {
  expect(this.dialogCount).toBeGreaterThanOrEqual(1);
});
```

Because `Then no dialog has fired` and `Then a dialog has fired` now live here, remove the duplicate `Then no dialog has fired` registration from `ui.ts` (Task 8) — the single source of truth for dialog-count assertions is `shared.ts`.

- [ ] **Step 2: Typecheck**

```bash
cd frontend && pnpm exec tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/bdd/steps/shared.ts
git commit -m "feat(bdd): shared documentation step + @dialog-tracked hook

- 'Given the backend and frontend are running' is a no-op doc step; the
  Before hook in support/hooks.ts already asserted reachability.
- @dialog-tracked Before hook counts dialog events so forfeit scenarios
  can assert 'no dialog has fired' for UC3b."
```

---

## Task 7: API step definitions (`frontend/tests/bdd/steps/api.ts`)

**Files:**

- Create: `frontend/tests/bdd/steps/api.ts`

Step registrations cover the 12 API steps enumerated in the design §4.

- [ ] **Step 1: Write `api.ts`**

```ts
/**
 * API-layer step definitions.
 *
 * Default HTTP client is page.request (shares the browser's cookie jar),
 * so `Given I start a new game ...` on the UI side and `When I request
 * /api/v1/...` on the API side see the same session cookie. The apiRequest
 * client (no shared cookies) is used only by the "fresh session" variants
 * that need cross-session isolation (games-current.feature scenario 3).
 */
import { Given, When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import type { APIResponse } from "playwright";
import type { HangmanWorld } from "../support/world";

async function storeResponse(
  world: HangmanWorld,
  res: APIResponse,
): Promise<void> {
  world.lastApiResponse = res;
  const text = await res.text();
  try {
    world.lastApiBody = text ? JSON.parse(text) : null;
  } catch {
    world.lastApiBody = text;
  }
}

function getPath(body: unknown, dotPath: string): unknown {
  const parts = dotPath.split(".");
  let cur: unknown = body;
  for (const part of parts) {
    if (cur === null || cur === undefined) return undefined;
    const idx = Number(part);
    if (Array.isArray(cur) && Number.isInteger(idx)) {
      cur = cur[idx];
    } else if (typeof cur === "object") {
      cur = (cur as Record<string, unknown>)[part];
    } else {
      return undefined;
    }
  }
  return cur;
}

function currentGameId(world: HangmanWorld): string {
  const id = getPath(world.lastApiBody, "id");
  // Backend Game.id is int (backend/src/hangman/models.py) — we accept
  // number | string and let the caller interpolate. Empty string / 0 /
  // null / undefined all fail this guard.
  if (
    (typeof id !== "number" || !Number.isFinite(id)) &&
    (typeof id !== "string" || id.length === 0)
  ) {
    throw new Error(
      "No current game id in lastApiBody — start a game before calling this step.",
    );
  }
  return String(id);
}

Given(
  "I start a new game with category {string} and difficulty {string}",
  async function (this: HangmanWorld, category: string, difficulty: string) {
    const res = await this.page.request.post(
      `${this.backendUrl}/api/v1/games`,
      { data: { category, difficulty } },
    );
    await storeResponse(this, res);
    expect(res.status()).toBe(201);
  },
);

Given(
  "I guess the letter {string}",
  async function (this: HangmanWorld, letter: string) {
    const id = currentGameId(this);
    const res = await this.page.request.post(
      `${this.backendUrl}/api/v1/games/${id}/guesses`,
      { data: { letter } },
    );
    await storeResponse(this, res);
  },
);

When("I request {string}", async function (this: HangmanWorld, path: string) {
  const res = await this.page.request.get(`${this.backendUrl}${path}`);
  await storeResponse(this, res);
});

When(
  "I request {string} from a fresh session",
  async function (this: HangmanWorld, path: string) {
    // apiRequest has its own baseURL + no shared cookie jar, giving us
    // cross-session isolation for the 'different session' scenarios.
    const res = await this.apiRequest.get(path);
    await storeResponse(this, res);
  },
);

When(
  "I POST to {string} with body:",
  async function (this: HangmanWorld, path: string, body: string) {
    const data = body.trim() ? JSON.parse(body) : {};
    const res = await this.page.request.post(`${this.backendUrl}${path}`, {
      data,
    });
    await storeResponse(this, res);
  },
);

When(
  "I POST to the current game's guesses endpoint with body:",
  async function (this: HangmanWorld, body: string) {
    const id = currentGameId(this);
    const data = body.trim() ? JSON.parse(body) : {};
    const res = await this.page.request.post(
      `${this.backendUrl}/api/v1/games/${id}/guesses`,
      { data },
    );
    await storeResponse(this, res);
  },
);

Then(
  "the response status is {int}",
  function (this: HangmanWorld, code: number) {
    if (!this.lastApiResponse) throw new Error("No API response recorded");
    expect(this.lastApiResponse.status()).toBe(code);
  },
);

Then(
  "the response error code is {string}",
  function (this: HangmanWorld, code: string) {
    const found = getPath(this.lastApiBody, "error.code");
    expect(found).toBe(code);
  },
);

Then(
  "the response body has {string} equal to {string}",
  function (this: HangmanWorld, dotPath: string, expected: string) {
    const found = getPath(this.lastApiBody, dotPath);
    // Coerce both sides to string for comparison — Gherkin args are always
    // strings; body values are whatever the API emits (number, string, bool).
    expect(String(found)).toBe(expected);
  },
);

Then(
  "the response body array {string} has length {int}",
  function (this: HangmanWorld, dotPath: string, expected: number) {
    const found = getPath(this.lastApiBody, dotPath);
    if (!Array.isArray(found)) {
      throw new Error(
        `Expected array at '${dotPath}', got ${typeof found}: ${JSON.stringify(found)}`,
      );
    }
    expect(found.length).toBe(expected);
  },
);

Then(
  "the response body field {string} is absent",
  function (this: HangmanWorld, dotPath: string) {
    const found = getPath(this.lastApiBody, dotPath);
    expect(found).toBeUndefined();
  },
);

Then(
  "the Set-Cookie header contains (case-insensitive) {string}",
  function (this: HangmanWorld, needle: string) {
    if (!this.lastApiResponse) throw new Error("No API response recorded");
    const headers = this.lastApiResponse.headers();
    const cookie = (headers["set-cookie"] ?? "").toLowerCase();
    expect(cookie).toContain(needle.toLowerCase());
  },
);

// Session idempotence steps — let a scenario snapshot the cookie value,
// do other API calls, and assert the value is unchanged. Used by
// session.feature. Cookie name is "session_id" (verified against
// backend/src/hangman/sessions.py:12 COOKIE_NAME on 2026-04-23).
When(
  "I remember the session cookie value",
  async function (this: HangmanWorld) {
    const cookies = await this.context.cookies(this.backendUrl);
    const sess = cookies.find((c) => c.name === "session_id");
    if (!sess) {
      throw new Error(
        "No session_id cookie set yet — call /api/v1/session first.",
      );
    }
    (
      this as unknown as { rememberedSessionValue: string }
    ).rememberedSessionValue = sess.value;
  },
);

Then(
  "the remembered session cookie value is unchanged",
  async function (this: HangmanWorld) {
    const remembered = (this as unknown as { rememberedSessionValue?: string })
      .rememberedSessionValue;
    if (!remembered) {
      throw new Error(
        "Nothing remembered — run 'I remember the session cookie value' first.",
      );
    }
    const cookies = await this.context.cookies(this.backendUrl);
    const sess = cookies.find((c) => c.name === "session_id");
    expect(sess?.value).toBe(remembered);
  },
);
```

- [ ] **Step 2: Typecheck**

```bash
cd frontend && pnpm exec tsc --noEmit
```

Expected: no errors. (We intentionally import `expect` from `@playwright/test` — it ships rich matchers. The `playwright` library alone only gives us `APIResponse`/etc. types.)

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/bdd/steps/api.ts
git commit -m "feat(bdd): API step definitions

12 step registrations covering every API surface referenced by the 33
scenarios: start game, guess letter, generic GET/POST, cross-session GET,
body dot-path assertions, array length, field absence, Set-Cookie header.
Default HTTP client is page.request (cookie-shared); apiRequest used only
for 'fresh session' variants."
```

---

## Task 8: UI step definitions (`frontend/tests/bdd/steps/ui.ts`)

**Files:**

- Create: `frontend/tests/bdd/steps/ui.ts`

- [ ] **Step 1: Write `ui.ts`**

```ts
/**
 * UI-layer step definitions.
 *
 * Every selector uses `data-testid` or role — never raw CSS classes
 * (rules/testing.md "Use stable selectors"). The keyboard-letter step
 * uses a real response-based sync barrier (page.waitForResponse on the
 * /guesses endpoint) rather than just polling disabled state, because
 * the keyboard is disabled SYNCHRONOUSLY on click (guessPending=true),
 * which races with the actual /guesses POST completing and the resulting
 * UI state update. The response wait guarantees the server has committed
 * the guess AND React has reconciled to the post-response state.
 */
import { Given, When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import type { HangmanWorld } from "../support/world";

Given("I open the app", async function (this: HangmanWorld) {
  await this.page.goto(this.frontendUrl);
  await expect(this.page.getByTestId("score-panel")).toBeVisible();
});

When(
  "I click the {string} button",
  async function (this: HangmanWorld, testid: string) {
    await this.page.getByTestId(testid).click();
  },
);

When(
  "I click the keyboard letter {string}",
  async function (this: HangmanWorld, letter: string) {
    const btn = this.page.getByTestId(`keyboard-letter-${letter}`);
    // Precondition: button is enabled (guessPending cleared from any
    // previous guess, letter not yet in guessedLetters).
    await expect(btn).toBeEnabled({ timeout: 3000 });
    // Register the response listener BEFORE click so we can't miss a
    // fast response. Matches POST /api/v1/games/{id}/guesses for either
    // success (200) or domain error (422/409) so test-of-error scenarios
    // still unblock here.
    const guessResponse = this.page.waitForResponse(
      (resp) =>
        /\/api\/v1\/games\/\d+\/guesses/.test(resp.url()) &&
        resp.request().method() === "POST",
      { timeout: 5000 },
    );
    await btn.click();
    await guessResponse;
    // After response + React commit, the clicked letter should now be in
    // guessedLetters and the button permanently disabled. This is the
    // post-response state, not the in-flight state.
    await expect(btn).toBeDisabled({ timeout: 3000 });
  },
);

When(
  "I select category {string}",
  async function (this: HangmanWorld, category: string) {
    await this.page.getByTestId("category-select").selectOption(category);
  },
);

When(
  "I select difficulty {string}",
  async function (this: HangmanWorld, difficulty: string) {
    await this.page.getByTestId(`difficulty-${difficulty}`).click();
  },
);

When("I reload the page", async function (this: HangmanWorld) {
  await this.page.reload();
  await expect(this.page.getByTestId("score-panel")).toBeVisible();
});

Then("I see the score panel", async function (this: HangmanWorld) {
  await expect(this.page.getByTestId("score-panel")).toBeVisible();
});

Then(
  "the total score is {string}",
  async function (this: HangmanWorld, expected: string) {
    await expect(this.page.getByTestId("score-total")).toHaveText(expected);
  },
);

Then(
  "the current streak is {string}",
  async function (this: HangmanWorld, expected: string) {
    await expect(this.page.getByTestId("streak-current")).toHaveText(expected);
  },
);

Then("I see a terminal game banner", async function (this: HangmanWorld) {
  const won = this.page.getByTestId("game-won");
  const lost = this.page.getByTestId("game-lost");
  await expect(won.or(lost)).toBeVisible();
});

Then(
  "I see the game-{word} banner",
  async function (this: HangmanWorld, outcome: string) {
    await expect(this.page.getByTestId(`game-${outcome}`)).toBeVisible();
  },
);

Then(
  "history contains {int} item(s)",
  async function (this: HangmanWorld, expected: number) {
    const items = this.page.locator('[data-testid^="history-item-"]');
    await expect(items).toHaveCount(expected);
  },
);

Then(
  "the masked word shows {string}",
  async function (this: HangmanWorld, expected: string) {
    await expect(this.page.getByTestId("masked-word")).toHaveText(expected);
  },
);

Then(
  "the keyboard letter {string} is disabled",
  async function (this: HangmanWorld, letter: string) {
    await expect(
      this.page.getByTestId(`keyboard-letter-${letter}`),
    ).toBeDisabled();
  },
);

Then(
  "the keyboard letter {string} is enabled",
  async function (this: HangmanWorld, letter: string) {
    await expect(
      this.page.getByTestId(`keyboard-letter-${letter}`),
    ).toBeEnabled();
  },
);
```

- [ ] **Step 2: Typecheck**

```bash
cd frontend && pnpm exec tsc --noEmit
```

- [ ] **Step 3: Verify the existing UI has the testids we're selecting**

Spot-check the components:

```bash
cd frontend && grep -rn 'data-testid' src/components/ src/App.tsx | \
  grep -E "score-panel|score-total|streak-current|category-select|difficulty-|keyboard-letter-|game-won|game-lost|history-item-|masked-word|start-game-btn" | \
  sort
```

Expected: ALL of the following testids present in the scaffold (verified 2026-04-23 — see design spec §5 and plan self-review):

- `score-panel` (`ScorePanel.tsx`)
- `score-total` (`ScorePanel.tsx`)
- `streak-current` (`ScorePanel.tsx`)
- `category-select` (`CategoryPicker.tsx`)
- `difficulty-easy` / `difficulty-medium` / `difficulty-hard` (`CategoryPicker.tsx`)
- `start-game-btn` (`CategoryPicker.tsx`) — **note: the feature-file steps use `I click the "start-game-btn" button`, NOT `start-new-game`. The button's real testid is `start-game-btn`.**
- `keyboard-letter-{a-z}` (`Keyboard.tsx`)
- `game-won` / `game-lost` (`GameBoard.tsx`)
- `masked-word` (`GameBoard.tsx`)
- `lives-remaining` (`GameBoard.tsx`) — used by mid-game-reload + some strengthened forfeit assertions
- `game-board-empty` (`GameBoard.tsx`) — used to assert "no active game" state after a fresh start-over from terminal
- `history-item-{id}` (`HistoryList.tsx`)

If the grep output is missing ANY of the above, the plan executor must investigate why before proceeding — the feature files assume every item above is present on master at this worktree's branch-point.

- [ ] **Step 4: Commit**

```bash
git add frontend/tests/bdd/steps/ui.ts
# Also add any component tweak if Step 3 required one:
git add frontend/src/components/
git commit -m "feat(bdd): UI step definitions

15 step registrations against stable data-testid/role selectors. The
'click keyboard letter' step encodes the Phase-5.1 guessPending sync
barrier (toBeEnabled before click, toBeDisabled after) so sequential
letter clicks don't race the in-flight /guesses POST. All selectors
documented in src/components/ testids."
```

---

## Task 9: `categories.feature`

**Files:**

- Create: `frontend/tests/bdd/features/categories.feature`

- [ ] **Step 1: Write the feature file**

```gherkin
Feature: GET /api/v1/categories

  The categories endpoint returns the list of word-category names and
  difficulty options available for the player to pick from. Under the BDD
  test-mode pool the category set is exactly {animals, food, tech}; the
  difficulty set is {easy, medium, hard} regardless of pool.

  Background:
    Given the backend and frontend are running

  @happy @smoke
  Scenario: Returns the list of categories
    When I request "/api/v1/categories"
    Then the response status is 200
    And the response body array "categories" has length 3

  @happy
  Scenario: Response exposes categories and difficulties
    When I request "/api/v1/categories"
    Then the response status is 200
    And the response body has "categories.0" equal to "animals"
    And the response body has "categories.1" equal to "food"
    And the response body has "categories.2" equal to "tech"
    And the response body array "difficulties" has length 3

  @edge
  Scenario: Categories are returned in stable alphabetical order
    When I request "/api/v1/categories"
    Then the response status is 200
    And the response body has "categories.0" equal to "animals"
    And the response body has "categories.1" equal to "food"
    And the response body has "categories.2" equal to "tech"
```

- [ ] **Step 2: Start backend-test + frontend in separate terminals**

Terminal A:

```bash
make backend-test
```

Terminal B:

```bash
make frontend
```

Wait ~3s for both to come up.

- [ ] **Step 3: Run the feature**

```bash
cd frontend && pnpm bdd tests/bdd/features/categories.feature
```

Expected: `3 scenarios (3 passed)` with green progress bar. Artifacts written to `test-results/cucumber.{json,ndjson}`.

- [ ] **Step 4: Commit**

```bash
git add frontend/tests/bdd/features/categories.feature
git commit -m "feat(bdd): categories.feature (3 scenarios, 1 smoke)"
```

---

## Task 10: `session.feature`

**Files:**

- Create: `frontend/tests/bdd/features/session.feature`

- [ ] **Step 1: Write the feature file**

```gherkin
Feature: GET /api/v1/session

  The session endpoint issues or echoes a browser-scoped session cookie
  used to key all game/history state. Idempotent — a second call from the
  same session reuses the cookie value.

  Background:
    Given the backend and frontend are running

  @happy @smoke
  Scenario: First call issues a session cookie
    When I request "/api/v1/session"
    Then the response status is 200
    And the Set-Cookie header contains (case-insensitive) "HttpOnly"
    And the Set-Cookie header contains (case-insensitive) "samesite=lax"

  @happy
  Scenario: Subsequent same-session calls reuse the cookie value
    When I request "/api/v1/session"
    And I remember the session cookie value
    When I request "/api/v1/session"
    Then the response status is 200
    And the remembered session cookie value is unchanged

  @edge
  Scenario: Session cookie sets a 30-day Max-Age
    When I request "/api/v1/session"
    Then the response status is 200
    And the Set-Cookie header contains (case-insensitive) "max-age=2592000"
```

**Step references:** The case-insensitive `Set-Cookie` matcher and the `remember`/`remembered-unchanged` steps live in Task 7's `api.ts` (see Task 7 Step 1 above). Cookie name is `session_id` (verified 2026-04-23 against `backend/src/hangman/sessions.py:12 COOKIE_NAME`).

- [ ] **Step 2: Run the feature**

```bash
cd frontend && pnpm bdd tests/bdd/features/session.feature
```

Expected: `3 scenarios (3 passed)`.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/bdd/features/session.feature
git commit -m "feat(bdd): session.feature (3 scenarios, 1 smoke)"
```

---

## Task 11: `games.feature`

**Files:**

- Create: `frontend/tests/bdd/features/games.feature`

- [ ] **Step 1: Write the feature file**

```gherkin
Feature: POST /api/v1/games (start and forfeit-chain)

  The games endpoint starts a new hangman game for the current session.
  Starting a game while another is IN_PROGRESS auto-forfeits the previous
  one. The response never leaks the target word.

  Background:
    Given the backend and frontend are running

  @happy @smoke
  Scenario: Valid start creates an IN_PROGRESS game
    When I POST to "/api/v1/games" with body:
      """
      { "category": "animals", "difficulty": "easy" }
      """
    Then the response status is 201
    And the response body has "state" equal to "IN_PROGRESS"
    And the response body has "category" equal to "animals"
    And the response body has "difficulty" equal to "easy"
    And the response body has "wrong_guesses_allowed" equal to "8"
    And the response body field "word" is absent

  @happy
  Scenario: Start on a medium difficulty reports 6 lives
    When I POST to "/api/v1/games" with body:
      """
      { "category": "food", "difficulty": "medium" }
      """
    Then the response status is 201
    And the response body has "wrong_guesses_allowed" equal to "6"
    And the response body field "word" is absent

  @failure
  Scenario: Unknown category is rejected
    When I POST to "/api/v1/games" with body:
      """
      { "category": "nonexistent", "difficulty": "easy" }
      """
    Then the response status is 422
    And the response error code is "UNKNOWN_CATEGORY"

  @edge
  Scenario: Starting a second game forfeits the first
    Given I start a new game with category "animals" and difficulty "easy"
    When I POST to "/api/v1/games" with body:
      """
      { "category": "tech", "difficulty": "hard" }
      """
    Then the response status is 201
    And the response body has "state" equal to "IN_PROGRESS"
    And the response body has "difficulty" equal to "hard"
```

- [ ] **Step 2: Run**

```bash
cd frontend && pnpm bdd tests/bdd/features/games.feature
```

Expected: `4 scenarios (4 passed)`.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/bdd/features/games.feature
git commit -m "feat(bdd): games.feature (4 scenarios, 1 smoke)"
```

---

## Task 12: `games-current.feature`

**Files:**

- Create: `frontend/tests/bdd/features/games-current.feature`

- [ ] **Step 1: Write the feature file**

```gherkin
Feature: GET /api/v1/games/current

  Returns the session's current IN_PROGRESS game, or 404 if none exists.
  Strictly session-scoped — a different session never sees this one's
  active game.

  Background:
    Given the backend and frontend are running

  @happy @smoke
  Scenario: Returns the active game for the session
    Given I start a new game with category "animals" and difficulty "hard"
    When I request "/api/v1/games/current"
    Then the response status is 200
    And the response body has "state" equal to "IN_PROGRESS"
    And the response body has "difficulty" equal to "hard"
    And the response body field "word" is absent

  @failure
  Scenario: No active game returns 404
    When I request "/api/v1/games/current"
    Then the response status is 404
    And the response error code is "NO_ACTIVE_GAME"

  @edge
  Scenario: A different session cannot see this session's game
    Given I start a new game with category "animals" and difficulty "easy"
    When I request "/api/v1/games/current" from a fresh session
    Then the response status is 404
    And the response error code is "NO_ACTIVE_GAME"
```

- [ ] **Step 2: Run**

```bash
cd frontend && pnpm bdd tests/bdd/features/games-current.feature
```

Expected: `3 scenarios (3 passed)`.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/bdd/features/games-current.feature
git commit -m "feat(bdd): games-current.feature (3 scenarios, 1 smoke)"
```

---

## Task 13: `guesses.feature`

**Files:**

- Create: `frontend/tests/bdd/features/guesses.feature`

- [ ] **Step 1: Write the feature file**

```gherkin
Feature: POST /api/v1/games/{id}/guesses

  Submits a letter guess. Correct letters appear in guessed_letters and
  reveal positions in masked_word; misses decrement lives_remaining. All
  domain violations (re-guessing, terminal game, malformed letter) return
  specific error codes via the backend's HangmanError envelope.

  Background:
    Given the backend and frontend are running
    And I start a new game with category "animals" and difficulty "easy"

  @happy @smoke
  Scenario: Correct letter reveals positions in masked_word
    When I POST to the current game's guesses endpoint with body:
      """
      { "letter": "c" }
      """
    Then the response status is 200
    And the response body has "state" equal to "IN_PROGRESS"
    And the response body has "guessed_letters" equal to "c"
    And the response body has "masked_word" equal to "c__"
    And the response body has "lives_remaining" equal to "8"

  @happy
  Scenario: Incorrect letter decrements lives
    When I POST to the current game's guesses endpoint with body:
      """
      { "letter": "z" }
      """
    Then the response status is 200
    And the response body has "guessed_letters" equal to "z"
    And the response body has "lives_remaining" equal to "7"

  @failure
  Scenario: Re-guessing the same letter is rejected
    When I POST to the current game's guesses endpoint with body:
      """
      { "letter": "c" }
      """
    Then the response status is 200
    When I POST to the current game's guesses endpoint with body:
      """
      { "letter": "c" }
      """
    Then the response status is 422
    And the response error code is "ALREADY_GUESSED"

  @failure
  Scenario: Guessing after terminal state is rejected
    When I guess the letter "c"
    And I guess the letter "a"
    And I guess the letter "t"
    And I POST to the current game's guesses endpoint with body:
      """
      { "letter": "b" }
      """
    Then the response status is 409
    And the response error code is "GAME_ALREADY_FINISHED"

  @edge
  Scenario: Multi-character letter is rejected by domain validation
    When I POST to the current game's guesses endpoint with body:
      """
      { "letter": "ab" }
      """
    Then the response status is 422
    And the response error code is "INVALID_LETTER"
```

- [ ] **Step 2: Run**

```bash
cd frontend && pnpm bdd tests/bdd/features/guesses.feature
```

Expected: `5 scenarios (5 passed)`.

**Error-code reference (verified 2026-04-23 against `backend/src/hangman/routes.py`):** `ALREADY_GUESSED` → 422 (game is still active, user just re-submitted); `GAME_ALREADY_FINISHED` → 409 (game is terminal, no further guesses possible); `INVALID_LETTER` → 422 (domain-layer validation raises `InvalidLetter` in `game.py`, caught in `routes.py:256`).

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/bdd/features/guesses.feature
git commit -m "feat(bdd): guesses.feature (5 scenarios, 1 smoke)"
```

---

## Task 14: `history.feature`

**Files:**

- Create: `frontend/tests/bdd/features/history.feature`

- [ ] **Step 1: Write the feature file**

```gherkin
Feature: GET /api/v1/history

  Returns the session's terminal (finalized) games ordered by finished_at
  DESC. Supports pagination via page/page_size.

  Background:
    Given the backend and frontend are running

  @happy @smoke
  Scenario: Finalized games appear in history
    Given I start a new game with category "animals" and difficulty "easy"
    And I guess the letter "c"
    And I guess the letter "a"
    And I guess the letter "t"
    When I request "/api/v1/history"
    Then the response status is 200
    And the response body array "items" has length 1
    And the response body has "items.0.state" equal to "WON"

  @happy
  Scenario: Most recent completion appears first
    Given I start a new game with category "animals" and difficulty "easy"
    And I guess the letter "c"
    And I guess the letter "a"
    And I guess the letter "t"
    And I start a new game with category "food" and difficulty "hard"
    And I guess the letter "b"
    And I guess the letter "d"
    And I guess the letter "e"
    And I guess the letter "f"
    When I request "/api/v1/history"
    Then the response status is 200
    And the response body array "items" has length 2
    And the response body has "items.0.state" equal to "LOST"
    And the response body has "items.1.state" equal to "WON"

  @edge
  Scenario: Empty history returns an empty items array
    When I request "/api/v1/history"
    Then the response status is 200
    And the response body array "items" has length 0

  @edge
  Scenario: Pagination honors page and page_size
    Given I start a new game with category "animals" and difficulty "easy"
    And I guess the letter "c"
    And I guess the letter "a"
    And I guess the letter "t"
    And I start a new game with category "food" and difficulty "easy"
    And I guess the letter "c"
    And I guess the letter "a"
    And I guess the letter "t"
    When I request "/api/v1/history?page=2&page_size=1"
    Then the response status is 200
    And the response body array "items" has length 1
    And the response body has "page" equal to "2"
    And the response body has "page_size" equal to "1"
    And the response body has "total" equal to "2"
```

- [ ] **Step 2: Run**

```bash
cd frontend && pnpm bdd tests/bdd/features/history.feature
```

Expected: `4 scenarios (4 passed)`.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/bdd/features/history.feature
git commit -m "feat(bdd): history.feature (4 scenarios, 1 smoke)"
```

---

## Task 15: `play-round.feature` (UC1)

**Files:**

- Create: `frontend/tests/bdd/features/play-round.feature`

- [ ] **Step 1: Write the feature file**

```gherkin
Feature: UC1 — Play a round to completion through the UI

  The happy-path fullstack flow: open the app, pick a category + difficulty,
  guess the word correctly, see the win banner, score panel updates,
  history records the game.

  @happy @smoke
  Scenario: Player guesses "cat" on animals/easy and wins
    Given the backend and frontend are running
    And I open the app
    When I select category "animals"
    And I select difficulty "easy"
    And I click the "start-game-btn" button
    And I click the keyboard letter "c"
    And I click the keyboard letter "a"
    And I click the keyboard letter "t"
    Then I see the game-won banner
    And the total score is "70"
    And the current streak is "1"
    And history contains 1 item
```

**Scoring math:** first win = `(correct_reveals × 10 + lives_remaining × 5) × streak_multiplier(1)` = `(3 × 10 + 8 × 5) × 1` = `70`. Formula lives at `backend/src/hangman/game.py:compute_round_score`.

- [ ] **Step 2: Run**

```bash
cd frontend && pnpm bdd tests/bdd/features/play-round.feature
```

Expected: `1 scenario (1 passed)`.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/bdd/features/play-round.feature
git commit -m "feat(bdd): play-round.feature (UC1, 1 scenario, smoke)"
```

---

## Task 16: `loss-resets-streak.feature` (UC2)

**Files:**

- Create: `frontend/tests/bdd/features/loss-resets-streak.feature`

- [ ] **Step 1: Write the feature file**

```gherkin
Feature: UC2 — A loss resets the current streak

  After winning a game the streak is 1 (score 70). Starting a second game
  and losing it must reset the current streak to 0 while keeping the total
  score at 70 (losses add zero; wins never decrement).

  @happy
  Scenario: Win then lose — streak resets, score preserved
    Given the backend and frontend are running
    And I open the app
    And I select category "animals"
    And I select difficulty "easy"
    When I click the "start-game-btn" button
    And I click the keyboard letter "c"
    And I click the keyboard letter "a"
    And I click the keyboard letter "t"
    Then I see the game-won banner
    And the total score is "70"
    And the current streak is "1"
    When I select difficulty "hard"
    And I click the "start-game-btn" button
    And I click the keyboard letter "b"
    And I click the keyboard letter "d"
    And I click the keyboard letter "e"
    And I click the keyboard letter "f"
    Then I see the game-lost banner
    And the total score is "70"
    And the current streak is "0"
    And history contains 2 items
```

- [ ] **Step 2: Run**

```bash
cd frontend && pnpm bdd tests/bdd/features/loss-resets-streak.feature
```

Expected: `1 scenario (1 passed)`.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/bdd/features/loss-resets-streak.feature
git commit -m "feat(bdd): loss-resets-streak.feature (UC2, 1 scenario)"
```

---

## Task 17: `forfeit.feature` (UC3 + UC3b)

**Files:**

- Create: `frontend/tests/bdd/features/forfeit.feature`

- [ ] **Step 1: Write the feature file**

```gherkin
Feature: UC3 + UC3b — Forfeit an in-progress game, but not a terminal one

  UC3: starting a new game while one is IN_PROGRESS must show a confirm
  dialog (the user is about to forfeit). On OK, the backend auto-forfeits
  the previous game and starts a fresh one.

  UC3b: after a game has already reached a terminal state (WON / LOST),
  clicking Start Game must NOT show a forfeit confirm — there's nothing
  active to forfeit. This is the bug caught in Phase 5.1 of the scaffold.

  @happy @smoke @dialog-accept
  Scenario: Starting a new game mid-play prompts forfeit confirm and starts fresh
    Given the backend and frontend are running
    And I open the app
    And I select category "animals"
    And I select difficulty "easy"
    When I click the "start-game-btn" button
    And I click the keyboard letter "c"
    # Prior game now has guessed_letters="c" and masked_word="c__".
    And I click the "start-game-btn" button
    # The @dialog-accept hook clicked OK on the window.confirm dialog.
    Then a dialog has fired
    # Fresh game rehydrated: masked word is back to three underscores and
    # 'c' is no longer marked as already-guessed on the keyboard.
    And the masked word shows "_ _ _"
    And the keyboard letter "c" is enabled

  @happy @smoke @dialog-tracked
  Scenario: Starting a new game after a loss does not prompt forfeit confirm
    Given the backend and frontend are running
    And I open the app
    And I select category "animals"
    And I select difficulty "hard"
    When I click the "start-game-btn" button
    And I click the keyboard letter "b"
    And I click the keyboard letter "d"
    And I click the keyboard letter "e"
    And I click the keyboard letter "f"
    Then I see the game-lost banner
    When I click the "start-game-btn" button
    # No forfeit confirm because the prior game was already LOST (terminal).
    Then no dialog has fired
    # Fresh game rehydrated: banner is gone, masked_word reset.
    And the masked word shows "_ _ _"
```

**Step reference:** The `Then the keyboard letter {string} is enabled` step is registered in Task 8's `ui.ts` (see Task 8 Step 1 above).

- [ ] **Step 2: Run**

```bash
cd frontend && pnpm bdd tests/bdd/features/forfeit.feature
```

Expected: `2 scenarios (2 passed)`.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/bdd/features/forfeit.feature
git commit -m "feat(bdd): forfeit.feature (UC3 + UC3b, 2 scenarios, 2 smoke)"
```

---

## Task 18: `mid-game-reload.feature` (UC4)

**Files:**

- Create: `frontend/tests/bdd/features/mid-game-reload.feature`

- [ ] **Step 1: Write the feature file**

```gherkin
Feature: UC4 — Mid-game reload restores the in-progress game

  The session cookie persists the player's active game server-side. After
  reloading the browser, the UI must rehydrate the same game, showing the
  masked word and which letters were already guessed.

  @happy
  Scenario: Reload mid-game keeps the active game and prior guess
    Given the backend and frontend are running
    And I open the app
    And I select category "animals"
    And I select difficulty "easy"
    When I click the "start-game-btn" button
    And I click the keyboard letter "c"
    And I reload the page
    Then I see the score panel
    And the masked word shows "c _ _"
    And the keyboard letter "c" is disabled
```

**Masked-word format — API vs UI:** The backend (`backend/src/hangman/game.py::mask_word`) returns the word with unrevealed positions as ASCII underscores and no inter-character spacing: for "cat" with only `c` guessed, the API string is `"c__"`. The frontend component (`frontend/src/components/GameBoard.tsx:32`) renders it as `{game.masked_word.split('').join(' ')}`, which INSERTS a literal space between every character. So the visible DOM text is `"c _ _"` (spaced). Feature files use:

- **API-level assertions** (response body): no spaces — `"c__"` / `"___"` (see Task 13 `guesses.feature`).
- **UI-level assertions** (`Then the masked word shows ...`): spaced — `"c _ _"` / `"_ _ _"` (see Tasks 17, 18, and forfeit scenarios).

- [ ] **Step 2: Run**

```bash
cd frontend && pnpm bdd tests/bdd/features/mid-game-reload.feature
```

Expected: `1 scenario (1 passed)`.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/bdd/features/mid-game-reload.feature
git commit -m "feat(bdd): mid-game-reload.feature (UC4, 1 scenario)"
```

---

## Task 19: `difficulty-levels.feature`

**Files:**

- Create: `frontend/tests/bdd/features/difficulty-levels.feature`

- [ ] **Step 1: Write the feature file**

```gherkin
Feature: Per-difficulty WIN and LOSS mistake counts

  Exercises the lives_total contract across all three difficulty levels in
  the UI. Under the test-mode pool ("cat" in every category), WIN is always
  3 correct guesses (c, a, t) and LOSS is exactly N non-cat misses where
  N = lives_total for the chosen difficulty (8 easy / 6 medium / 4 hard).

  Background:
    Given the backend and frontend are running
    And I open the app
    And I select category "animals"

  @happy
  Scenario: Easy WIN
    When I select difficulty "easy"
    And I click the "start-game-btn" button
    And I click the keyboard letter "c"
    And I click the keyboard letter "a"
    And I click the keyboard letter "t"
    Then I see the game-won banner

  @happy
  Scenario: Easy LOSS after 8 misses
    When I select difficulty "easy"
    And I click the "start-game-btn" button
    And I click the keyboard letter "b"
    And I click the keyboard letter "d"
    And I click the keyboard letter "e"
    And I click the keyboard letter "f"
    And I click the keyboard letter "g"
    And I click the keyboard letter "h"
    And I click the keyboard letter "i"
    And I click the keyboard letter "j"
    Then I see the game-lost banner

  @happy
  Scenario: Medium WIN
    When I select difficulty "medium"
    And I click the "start-game-btn" button
    And I click the keyboard letter "c"
    And I click the keyboard letter "a"
    And I click the keyboard letter "t"
    Then I see the game-won banner

  @happy
  Scenario: Medium LOSS after 6 misses
    When I select difficulty "medium"
    And I click the "start-game-btn" button
    And I click the keyboard letter "b"
    And I click the keyboard letter "d"
    And I click the keyboard letter "e"
    And I click the keyboard letter "f"
    And I click the keyboard letter "g"
    And I click the keyboard letter "h"
    Then I see the game-lost banner

  @happy @smoke
  Scenario: Hard WIN
    When I select difficulty "hard"
    And I click the "start-game-btn" button
    And I click the keyboard letter "c"
    And I click the keyboard letter "a"
    And I click the keyboard letter "t"
    Then I see the game-won banner

  @happy
  Scenario: Hard LOSS after 4 misses
    When I select difficulty "hard"
    And I click the "start-game-btn" button
    And I click the keyboard letter "b"
    And I click the keyboard letter "d"
    And I click the keyboard letter "e"
    And I click the keyboard letter "f"
    Then I see the game-lost banner
```

- [ ] **Step 2: Run**

```bash
cd frontend && pnpm bdd tests/bdd/features/difficulty-levels.feature
```

Expected: `6 scenarios (6 passed)`.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/bdd/features/difficulty-levels.feature
git commit -m "feat(bdd): difficulty-levels.feature (6 scenarios, 1 smoke)

Per-difficulty WIN+LOSS against the test-mode pool. Easy = 8 misses,
Medium = 6, Hard = 4 to lose. All WIN on c/a/t. Unlocked by Task 1's
HANGMAN_WORDS_FILE lifespan patch."
```

---

## Task 20: Delete replaced Playwright specs

**Files:**

- Delete: `frontend/tests/e2e/specs/play-round.spec.ts`
- Delete: `frontend/tests/e2e/specs/no-forfeit-terminal.spec.ts`

- [ ] **Step 1: Delete the two specs**

```bash
rm frontend/tests/e2e/specs/play-round.spec.ts
rm frontend/tests/e2e/specs/no-forfeit-terminal.spec.ts
```

- [ ] **Step 2: Confirm Playwright discovers zero specs but config still loads**

```bash
cd frontend && pnpm exec playwright test --list
```

Expected: lists 0 specs, exits cleanly. `playwright.config.ts` stays in place for Feature 3 to reuse.

- [ ] **Step 3: Confirm vitest still excludes e2e tree (no accidental pickup)**

```bash
cd frontend && pnpm test:run
```

Expected: 28 vitest tests pass (the same count the scaffold ships with). No .spec.ts files picked up.

- [ ] **Step 4: Commit**

```bash
git add -A frontend/tests/e2e/specs/
git commit -m "chore(bdd): delete playwright specs replaced by .feature files

- play-round.spec.ts  -> play-round.feature (UC1)
- no-forfeit-terminal.spec.ts -> forfeit.feature scenario 2 (UC3b)

playwright.config.ts + tests/e2e/{use-cases,fixtures}/ untouched: Feature 3
will reuse the config for coverage wiring; the markdown UC file stays for
the verify-e2e agent's exploratory regression path."
```

---

## Task 21: `.claude/rules/testing.md` — BDD vocabulary block

**Files:**

- Modify: `.claude/rules/testing.md` (appended block only; existing content untouched)

- [ ] **Step 1: Locate the insertion point**

Find the heading `## Canonical E2E gate vocabulary` in `.claude/rules/testing.md`. Insert the new block immediately after that heading's table (before the `### Evidence-based gate` subsection). This keeps the two gate vocabularies side-by-side.

Append this block:

```markdown
## BDD suite vocabulary (additive, 2026-04-23 — Feature bdd-suite)

The BDD suite adds a second gate marker alongside `E2E verified`. **Not hook-enforced in Feature 1** — manual checklist only. Feature 2 (`bdd-dashboard`) will add hook enforcement once there's a dashboard artifact to evidence against.

| Gate element     | Canonical form                                      |
| ---------------- | --------------------------------------------------- |
| Marker stem      | `BDD suite passed`                                  |
| Checklist entry  | ``- [ ] BDD suite passed (Phase 5.4 — `make bdd`)`` |
| Checked (passed) | ``- [x] BDD suite passed (Phase 5.4 — `make bdd`)`` |
| Checked as N/A   | `- [x] BDD suite passed — N/A: <reason>`            |

**Scope in Feature 1:** documentation only. `check-workflow-gates.sh` / `.ps1` are NOT modified. PR reviewers enforce the marker by inspection.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/rules/testing.md
git commit -m "docs(rules): add BDD suite vocabulary to testing.md

Sibling marker to 'E2E verified' — 'BDD suite passed'. Feature 1
scope: documentation only; Feature 2 adds hook enforcement."
```

---

## Task 22: `README.md` — "Running the BDD suite" section

**Files:**

- Modify: `README.md`

- [ ] **Step 1: Check current README state**

```bash
cat README.md | head -40
```

If there is no README, create one with at minimum the BDD section. If one exists, append the BDD block near the existing "Running locally" / "Development" section.

- [ ] **Step 2: Append the BDD instructions**

Add this section (adjust placement to fit the existing README's structure):

````markdown
## Running the BDD suite

The BDD suite is separate from `make verify` and requires the backend + frontend running in test-mode.

```bash
# Terminal A — backend with test-mode word pool (one-word 'cat' per category)
make backend-test

# Terminal B — frontend dev server
make frontend

# Terminal C — run all 33 scenarios across 11 feature files
make bdd
```

Port overrides work the same way as `make backend` / `make frontend`:

```bash
make backend-test HANGMAN_BACKEND_PORT=8002
make frontend     HANGMAN_BACKEND_PORT=8002 HANGMAN_FRONTEND_PORT=3001
make bdd          HANGMAN_BACKEND_PORT=8002 HANGMAN_FRONTEND_PORT=3001
```

Artifacts land in `frontend/test-results/cucumber.{json,ndjson}` (gitignored).

**Why `make backend-test` and not `make backend`?** Production `words.txt` has 45 words; only a handful of letters are guaranteed misses, which isn't enough to deterministically test Easy (8 misses) and Medium (6 misses) LOSS scenarios. `make backend-test` sets `HANGMAN_WORDS_FILE=words.test.txt` so every category collapses to `"cat"`, giving every scenario one deterministic source of truth for guess outcomes. See `docs/plans/2026-04-23-bdd-suite-design.md` §2b for the full rationale.
````

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): document 'make backend-test' + 'make bdd' workflow"
```

---

## Task 23: Full-suite green run + report sanity check

**Files:**

- No file writes. This is the acceptance gate.

- [ ] **Step 1: Ensure both servers are running**

Terminal A: `make backend-test` (running).
Terminal B: `make frontend` (running).

- [ ] **Step 2: Run the full suite**

```bash
cd frontend && pnpm bdd
```

Expected: `33 scenarios (33 passed)` green. Suite runtime < 60s (per PRD §2 success metric).

If any scenario fails, fix the scenario OR the step definition — never bypass by removing the scenario. NO BUGS LEFT BEHIND (`rules/critical-rules.md`).

- [ ] **Step 3: Verify report artifacts**

```bash
ls -la frontend/test-results/
cat frontend/test-results/cucumber.ndjson | head -3
```

Expected:

- `cucumber.json` exists (legacy format)
- `cucumber.ndjson` exists, each line is valid JSON (Cucumber Messages schema)
- First line parses with `head -1 frontend/test-results/cucumber.ndjson | python -m json.tool`

- [ ] **Step 4: Smoke-tag filter sanity check**

```bash
cd frontend && pnpm bdd --tags @smoke
```

Expected: exactly 10 scenarios run (per design §5 table) and all pass.

- [ ] **Step 5: Run the full backend + frontend unit suites to confirm no regressions**

```bash
make verify
```

Expected: full green. The BDD suite is intentionally NOT part of `make verify` (PRD Q7).

- [ ] **Step 6: Update CONTINUITY.md**

Advance the workflow state:

- `Phase`: `5 — Quality Gates`
- `Next step`: `Run code review loop (Codex + pr-review-toolkit)`
- Check off in the Checklist:
  - `- [x] Plan written (\`docs/plans/2026-04-23-bdd-suite-plan.md\`)`
  - `- [x] Plan review loop (N iterations) — PASS` (count filled after Phase 3.3)
  - `- [x] TDD execution complete`

- [ ] **Step 7: Final commit for this phase**

```bash
git add CONTINUITY.md
git commit -m "docs(continuity): mark BDD Phase 4 complete

Full 33-scenario suite green via make bdd. make verify still green.
Advancing to Phase 5 (code review loop)."
```

---

## Dispatch Plan

> For parallel subagent execution (Phase 4, `superpowers:subagent-driven-development`). Serial execution ignores this and runs tasks 1→23 in order.

| Task ID | Depends on  | Writes (concrete file paths)                                                                                                 |
| ------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------- |
| T1      | —           | `backend/words.test.txt`, `backend/tests/unit/test_words_file_env.py`, `backend/src/hangman/main.py`                         |
| T2      | —           | `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/cucumber.cjs`, `frontend/tests/bdd/**/.gitkeep`, `.gitignore`  |
| T3      | T1, T2      | `Makefile`                                                                                                                   |
| T4      | T2          | `frontend/tests/bdd/support/world.ts`                                                                                        |
| T5      | T4          | `frontend/tests/bdd/support/hooks.ts`                                                                                        |
| T6      | T5          | `frontend/tests/bdd/steps/shared.ts`                                                                                         |
| T7      | T5          | `frontend/tests/bdd/steps/api.ts`                                                                                            |
| T8      | T5          | `frontend/tests/bdd/steps/ui.ts` (no component edits — all testids verified present on master 2026-04-23; see Task 8 Step 3) |
| T9      | T6, T7      | `frontend/tests/bdd/features/categories.feature`                                                                             |
| T10     | T6, T7      | `frontend/tests/bdd/features/session.feature`                                                                                |
| T11     | T6, T7      | `frontend/tests/bdd/features/games.feature`                                                                                  |
| T12     | T6, T7      | `frontend/tests/bdd/features/games-current.feature`                                                                          |
| T13     | T6, T7      | `frontend/tests/bdd/features/guesses.feature`                                                                                |
| T14     | T6, T7      | `frontend/tests/bdd/features/history.feature`                                                                                |
| T15     | T6, T7, T8  | `frontend/tests/bdd/features/play-round.feature`                                                                             |
| T16     | T6, T7, T8  | `frontend/tests/bdd/features/loss-resets-streak.feature`                                                                     |
| T17     | T6, T7, T8  | `frontend/tests/bdd/features/forfeit.feature`                                                                                |
| T18     | T6, T7, T8  | `frontend/tests/bdd/features/mid-game-reload.feature`                                                                        |
| T19     | T6, T7, T8  | `frontend/tests/bdd/features/difficulty-levels.feature`                                                                      |
| T20     | T15, T17    | (deletions only — `frontend/tests/e2e/specs/play-round.spec.ts`, `no-forfeit-terminal.spec.ts`)                              |
| T21     | —           | `.claude/rules/testing.md`                                                                                                   |
| T22     | T3          | `README.md`                                                                                                                  |
| T23     | T9-T19, T20 | `CONTINUITY.md` (no code writes — this is the acceptance gate)                                                               |

**Concurrency cap:** 3 (practitioner default). Tasks T9–T14 (API-only feature files) can run as a wave of up to 3 after T6+T7 complete. T15–T19 (UI feature files) can run as a wave after T8 completes. T20/T21 are independent of each other and the features. T22 depends only on T3.

**Serial-mode fallback:** for a solo session, just execute T1 → T23 in numeric order. That's the expected path for `superpowers:subagent-driven-development` with a single fresh subagent per task.

---

## Self-Review

### 1. Spec coverage

| Design-spec section                | Implemented by                           |
| ---------------------------------- | ---------------------------------------- |
| §1 Architecture (file tree)        | Tasks 2, 4–8 (scaffold), 9–19 (features) |
| §2 `cucumber.cjs` + `package.json` | Task 2                                   |
| §2b Backend test-mode word file    | Task 1                                   |
| §3 World + hooks                   | Tasks 4, 5                               |
| §4 Step definitions (3 files)      | Tasks 6, 7, 8                            |
| §5 11 feature files / 33 scenarios | Tasks 9–19                               |
| §6 Deletions + integration         | Tasks 20, 21, 22                         |
| §7 Testing strategy (Phase 5 exit) | Task 23                                  |
| §8 Non-goals                       | N/A — documented only                    |
| §9 Open questions                  | N/A — resolved pre-plan                  |
| §10 References                     | N/A — doc-only                           |

No gaps.

### 2. Placeholder scan

- No "TBD", "TODO", or "implement later" strings in task bodies.
- No "add appropriate error handling" vagueness — error paths are either in a specific scenario (`@failure` tag) or explicitly deferred to pytest (PRD Q5).
- No "similar to Task N" — feature-file content is spelled out in full for every `.feature` task.
- No un-bodied code steps — every implementation step has a complete code block or exact command.

### 3. Type consistency

- `HangmanWorld` (Task 4) declares `browser`, `context`, `page`, `apiRequest`, `lastApiResponse`, `lastApiBody`, `dialogCount`, `backendUrl`, `frontendUrl`. All other tasks (5–8) reference exactly these names.
- Step signatures in Tasks 7/8 match the patterns used by Tasks 9–19's Gherkin (e.g., `Given I start a new game with category {string} and difficulty {string}` is registered once in api.ts and called from games.feature, games-current.feature, guesses.feature, history.feature).
- The `assertBackendReachable` helper (Task 5) is referenced nowhere else by name — scoped to `hooks.ts`.
- `getPath` + `storeResponse` helpers (Task 7) are file-local to `api.ts` — no cross-file name collision.

### Notes for the executor

- **If a component-level testid doesn't exist** (most likely: `masked-word`), adding it is in-scope for the UI-step task (Task 8) — don't punt it.
- **If a backend error code string differs** from the plan's assumption (e.g., the step for `GAME_FINALIZED` is actually `GAME_OVER`), update the `.feature` file to match the real contract — do NOT change the backend. The scenarios document the real contract.
- **Running the dev servers between tasks:** Tasks 9–19 each run against live servers. Keep `make backend-test` + `make frontend` running across the whole Phase 4 arc — don't restart between tasks.
