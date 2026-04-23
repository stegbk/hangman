# Research Brief: hangman-scaffold

**Date:** 2026-04-22
**Agent:** research-first
**PRD:** docs/prds/hangman-scaffold.md
**Feature:** scaffold FastAPI backend + React/Vite frontend + SQLite persistence

## Summary

- **20 research targets** covered across backend (10), frontend (8), and cross-cutting (2) concerns.
- **Key discovery:** Node 20 is no longer supported by current pnpm 10.x (pure-ESM requires Node 22+). PRD/CLAUDE.md say "Node 20+, pnpm 9+" — this still works but pnpm 9 reaches EOL 2026-04-30 (8 days from now). The scaffold should either (a) pin pnpm 9.x explicitly via `packageManager` in `package.json` for short-term correctness, or (b) require Node 22+ and pnpm 10.x. Recommend (b).

## Libraries

### FastAPI

- **Current stable version (April 2026):** 0.136.0 (released 2026-04-16).
- **Recommended pin:** `fastapi>=0.136,<0.137` (tiangolo ships minor-as-feature, so pin with a narrow range).
- **Sources:**
  - [FastAPI release notes](https://fastapi.tiangolo.com/release-notes/) — accessed 2026-04-22
  - [FastAPI Lifespan Events docs](https://fastapi.tiangolo.com/advanced/events/) — accessed 2026-04-22
- **Key patterns / current idiom:**
  - Use `lifespan` async context manager via `@asynccontextmanager` and `FastAPI(lifespan=...)`. `@app.on_event("startup"/"shutdown")` is deprecated and has been for years — do not use.
  - Since 0.135.2, FastAPI requires `pydantic>=2.9.0` — no v1 fallback.
  - `src/` layout is fine; FastAPI has no opinion. The CLAUDE.md file-structure already specifies `backend/src/hangman/...` which is idiomatic.
  - `fastapi[standard]` extras pull in uvicorn + httpx + pydantic — use it for the dev dep group, or split for prod.
- **Pitfalls / breaking changes since 0.110:**
  - `on_event` deprecation still warns; must migrate to `lifespan`.
  - Some response-validation behaviors tightened with Pydantic v2 strict mode — respect schema separation per `rules/api-design.md` (separate `*Create`, `*Response`).
- **Design impact:** Write `db.py` `create_all` inside a `lifespan` context manager attached to `FastAPI(lifespan=...)`. No `@app.on_event`. Use dependency-injected `Depends(get_session)` for request-scoped DB sessions.
- **Test implication:** Async tests that rely on startup side-effects must either trigger `lifespan` via `httpx.AsyncClient` + `asgi-lifespan.LifespanManager` OR use the sync `TestClient` (which triggers lifespan automatically). Pick one and stick with it.

### Pydantic v2

- **Current stable version (April 2026):** 2.13.3 (released 2026-04-20).
- **Recommended pin:** `pydantic>=2.13,<3` (FastAPI 0.136 requires `pydantic>=2.9`; latest minor is safest).
- **Sources:**
  - [Pydantic docs — Configuration](https://docs.pydantic.dev/latest/api/config/) — accessed 2026-04-22
  - [Pydantic Migration Guide](https://docs.pydantic.dev/latest/migration/) — accessed 2026-04-22
  - [PyPI: pydantic 2.13.3](https://pypi.org/project/pydantic/) — accessed 2026-04-22
- **Key patterns / current idiom:**
  - `model_config = ConfigDict(...)` — `class Config:` is deprecated.
  - `@field_validator("name")` — `@validator` is deprecated.
  - `.model_dump()` / `.model_dump_json()` — `.dict()` / `.json()` are deprecated.
  - `.model_validate(obj)` — `.parse_obj` is deprecated.
  - Use `Annotated[str, Field(min_length=1, max_length=1, pattern=r"^[a-z]$")]` for the guess-letter constraint instead of a custom validator if possible.
- **Pitfalls / breaking changes since Pydantic v1:**
  - v1-style code will import-succeed but emit `DeprecationWarning`. Lint should promote those to errors (`W` / `DeprecationWarning`-to-error) to prevent creep.
  - JSON serialization of `datetime` is now ISO-8601 with timezone — ensure `started_at`/`finished_at` stored as UTC.
- **Design impact:** Define `Literal["easy", "medium", "hard"]` for difficulty; let Pydantic reject bad values with a 422 automatically. Use `field_validator` with `mode="before"` for the guess-letter lowercasing so `"A"` normalizes to `"a"` before length/pattern checks fire.
- **Test implication:** Tests assert the 422 `VALIDATION_ERROR` envelope shape for bad category/difficulty/letter — map Pydantic's default `ValidationError` to the project's error envelope in an exception handler.

### SQLAlchemy 2.0

- **Current stable version (April 2026):** 2.0.49 (released 2026-04-03). 2.1 is in beta (2.1.0b2 on 2026-04-16) — do not use for scaffold.
- **Recommended pin:** `sqlalchemy>=2.0.49,<2.1`.
- **Sources:**
  - [SQLAlchemy 2.0 — What's New](https://docs.sqlalchemy.org/en/20/changelog/whatsnew_20.html) — accessed 2026-04-22
  - [Declarative Tables docs](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html) — accessed 2026-04-22
  - [PyPI: sqlalchemy 2.0.49](https://pypi.org/project/sqlalchemy/) — accessed 2026-04-22
- **Key patterns / current idiom:**
  - `class Base(DeclarativeBase): pass` — `declarative_base()` is legacy.
  - `id: Mapped[int] = mapped_column(primary_key=True)` — not `Column(Integer, primary_key=True)`.
  - Queries via `session.execute(select(Game).where(...))` and `.scalars().all()` — not `session.query(Game)`.
  - For SQLite URLs: `sqlite:///./backend/hangman.db` (three slashes + relative path).
  - Sync engine is sufficient for single-user local SQLite (see "Sync vs async SQLite" under cross-cutting).
- **Pitfalls / breaking changes since 1.4:**
  - `Query` API still works but is legacy — do not use in new code.
  - Implicit-autocommit is gone; must commit explicitly or use `session.begin()` context manager.
- **Design impact:** `models.py` uses `DeclarativeBase` subclass `Base`, `Mapped[...]` annotations, and `mapped_column`. `db.py` returns a sync `Session` factory. Composite index on `(session_id, state)` via `__table_args__ = (Index("ix_games_session_state", "session_id", "state"),)`.
- **Test implication:** Integration tests create tables via `Base.metadata.create_all(engine)` against an `sqlite:///:memory:` engine with `StaticPool` + `connect_args={"check_same_thread": False}`. Use transaction-rollback fixtures per `rules/testing.md` mocking rules.

### Uvicorn

- **Current stable version (April 2026):** 0.45.0 (released 2026-04-21).
- **Recommended pin:** `uvicorn[standard]>=0.45,<0.46`.
- **Sources:**
  - [Uvicorn settings docs](https://www.uvicorn.org/settings/) — accessed 2026-04-22
  - [PyPI: uvicorn 0.45.0](https://pypi.org/project/uvicorn/) — accessed 2026-04-22
- **Key patterns / current idiom:**
  - `uvicorn hangman.main:app --reload` for dev. `--reload` and `--workers` are mutually exclusive.
  - `--lifespan auto` is the default; FastAPI's lifespan context manager runs automatically.
  - `[standard]` extras include `watchfiles`, `httptools`, `uvloop` — fine for local dev.
- **Pitfalls:** `--reload` can double-fire lifespan on Windows; not relevant for macOS dev here.
- **Design impact:** Makefile `make backend` target runs `uv run uvicorn hangman.main:app --reload --host 127.0.0.1 --port 8000`. Bind to loopback only for a local-only app.
- **Test implication:** Tests do not invoke uvicorn; they use the ASGI app directly via `TestClient` or `httpx.AsyncClient`.

### pytest + pytest-asyncio

- **Current stable versions (April 2026):** pytest 8.3.x; pytest-asyncio 1.x (1.0 released 2025-05-25, now at 1.x).
- **Recommended pin:** `pytest>=8.3,<9`, `pytest-asyncio>=1.0,<2`.
- **Sources:**
  - [pytest-asyncio modes docs](https://pytest-asyncio.readthedocs.io/en/latest/reference/configuration.html) — accessed 2026-04-22
  - [pytest-asyncio migration to 1.0](https://thinhdanggroup.github.io/pytest-asyncio-v1-migrate/) — accessed 2026-04-22
- **Key patterns / current idiom:**
  - `asyncio_mode = "strict"` is the safe default (must decorate with `@pytest.mark.asyncio` explicitly).
  - Configure in `pyproject.toml` under `[tool.pytest.ini_options]`:
    ```toml
    [tool.pytest.ini_options]
    asyncio_mode = "strict"
    testpaths = ["tests"]
    ```
- **Pitfalls:** `auto` mode promotes every async fixture — conflicts with sync fixtures imported from other libs. Stick with `strict`.
- **Design impact:** `conftest.py` at `backend/tests/conftest.py` provides `engine`, `session`, `client` fixtures. If we use sync FastAPI routes (recommended for scaffold, see cross-cutting), pytest-asyncio can be skipped entirely — only add it if we end up with async route handlers.
- **Test implication:** Decision point in plan: pick sync OR async routes; don't mix. Scaffold should default to sync for SQLite single-user (see cross-cutting section).

### httpx

- **Current stable version (April 2026):** 0.28.1 (released 2024-12-06; 1.0 still in dev as of 1.0.dev3 2025-09-15).
- **Recommended pin:** `httpx>=0.28,<1` (in dev-deps only — FastAPI's `[standard]` already pulls it).
- **Sources:**
  - [HTTPX transports docs](https://www.python-httpx.org/advanced/transports/) — accessed 2026-04-22
  - [PyPI: httpx 0.28.1](https://pypi.org/project/httpx/) — accessed 2026-04-22
- **Key patterns / current idiom:**
  - `AsyncClient(transport=ASGITransport(app=app), base_url="http://test")` — the `app=app` shortcut was deprecated in 0.27.
  - `AsyncClient` is needed only for async route tests. `TestClient` (sync) wraps httpx under the hood.
- **Pitfalls:** The FastAPI/httpx ASGI type mismatch (MutableMapping vs Dict) is a known typing nuisance — add `# type: ignore[arg-type]` on the ASGITransport call if mypy complains.
- **Design impact:** Prefer `TestClient` for this scaffold — sync routes, simpler fixtures, automatic lifespan.
- **Test implication:** Integration tests use `TestClient(app)` as a context manager so startup/shutdown lifespan fires once per test module.

### SQLAlchemy + SQLite connection

- **Current stable (April 2026):** covered by SQLAlchemy 2.0.49 above.
- **Recommended pattern:**
  ```python
  engine = create_engine(
      "sqlite:///./backend/hangman.db",
      connect_args={"check_same_thread": False},
      echo=False,
  )
  ```
  For in-memory tests: add `poolclass=StaticPool` so all connections see the same in-memory DB.
- **Sources:**
  - [SQLAlchemy SQLite dialect docs](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html) — accessed 2026-04-22
  - [FastAPI SQL Databases tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/) — accessed 2026-04-22
- **Key patterns:** `check_same_thread=False` is still required in 2026 because FastAPI serves each request on a different thread from a thread pool (for sync routes). SQLAlchemy sets this automatically for `QueuePool`, but FastAPI's official example still passes it explicitly — do the same for clarity.
- **Pitfalls:** SQLite writes across threads must be serialized by the connection pool — `QueuePool` (default for file DBs) handles this. Do not share a single `Session` across threads.
- **Design impact:** `db.py` creates one engine module-scoped, exposes `SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)`, and `get_session()` yields a session per request. File path resolved relative to a module constant so CWD doesn't matter.
- **Test implication:** Each test gets a fresh in-memory SQLite + StaticPool. Never reuse the prod DB file in tests.

### FastAPI cookie handling

- **Current pattern (April 2026):** For a single opaque UUID session cookie with no signed payload, **roll-your-own** via a FastAPI dependency that reads `request.cookies.get("session_id")` and a response middleware that sets the cookie. Do not use Starlette's `SessionMiddleware` — it is for signed key/value session stores and would add an itsdangerous secret for no benefit here.
- **Sources:**
  - [FastAPI Response Cookies docs](https://fastapi.tiangolo.com/advanced/response-cookies/) — accessed 2026-04-22
  - [Starlette Middleware — SessionMiddleware](https://starlette.dev/middleware/) — accessed 2026-04-22
- **Key patterns:**
  ```python
  response.set_cookie(
      key="session_id",
      value=str(session.id),
      max_age=30 * 24 * 60 * 60,
      httponly=True,
      samesite="lax",
      secure=False,   # local HTTP per PRD §7
  )
  ```
- **Pitfalls:** `samesite` value is lowercase `"lax"`, not `"Lax"` (Starlette normalizes but keep it consistent). Do not set `domain` for localhost — browsers reject it on some configs.
- **Design impact:** `sessions.py` exposes `get_or_create_session(request, response, db)` as a FastAPI `Depends()` that: (1) reads cookie, (2) looks up session row, (3) creates new if missing/stale, (4) sets the `session_id` cookie on `response`. Wire it on every route that needs session scope.
- **Test implication:** E2E and integration tests assert `Set-Cookie` header on first request has `HttpOnly`, `SameSite=Lax`, and `Max-Age=2592000`. Playwright test reloads and confirms the cookie survives.

### ruff

- **Current stable version (April 2026):** 0.15.11 (released 2026-04-16).
- **Recommended pin:** `ruff>=0.15,<0.16` (dev-dep only).
- **Sources:**
  - [Ruff configuration docs](https://docs.astral.sh/ruff/configuration/) — accessed 2026-04-22
  - [PyPI: ruff 0.15.11](https://pypi.org/project/ruff/) — accessed 2026-04-22
- **Key patterns / current idiom:**
  - `ruff format` replaces `black` entirely — do not install black.
  - Configure via `[tool.ruff]` / `[tool.ruff.lint]` / `[tool.ruff.format]` in `pyproject.toml`.
  - Recommended rule selection for a FastAPI project: `E`, `F`, `W`, `I` (imports), `B` (bugbear), `UP` (pyupgrade), `N` (naming), `ASYNC` (async-safety), `SIM` (simplify).
- **Pitfalls:** `target-version = "py312"` must be set to let Ruff use 3.12 syntax in fixups.
- **Design impact:** One `pyproject.toml` section configures both lint and format. CI/commands: `ruff check . && ruff format --check .` (per PRD §2 success metric).
- **Test implication:** Add a smoke test that runs `ruff check` in CI-equivalent mode so style drift is caught.

### uv

- **Current stable (April 2026):** latest Astral `uv` (0.7.x range per docs) — exact version not critical, tool is self-updating.
- **Recommended pattern:** `uv init` to bootstrap, commit `pyproject.toml` + `uv.lock`. Run everything through `uv run` (e.g. `uv run pytest`, `uv run uvicorn ...`).
- **Sources:**
  - [uv — Working on projects](https://docs.astral.sh/uv/guides/projects/) — accessed 2026-04-22
  - [uv — Locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/) — accessed 2026-04-22
- **Key patterns / current idiom:**
  - Minimal `pyproject.toml` needs only `[project]` (name, version, requires-python, dependencies) and `[project.optional-dependencies]` or `[dependency-groups]` for dev.
  - `[tool.uv]` section is **optional** — only needed for `index-url`, `resolution` tweaks, or workspace members. Scaffold does not need it.
  - Dev deps via PEP 735 `[dependency-groups]` is the modern choice; `uv sync --group dev` installs them.
  - Commit `uv.lock` — it's cross-platform and reproducible.
- **Pitfalls:** `uv run` regenerates `.venv/` if the lockfile changed — don't be surprised by auto-sync on first run.
- **Design impact:** `backend/pyproject.toml` lists runtime deps (`fastapi`, `uvicorn[standard]`, `sqlalchemy`, `pydantic`), a `[dependency-groups] dev = [...]` section for `pytest`, `httpx` (for AsyncClient if needed), `ruff`, `mypy`. No `[tool.uv]` section needed.
- **Test implication:** `make test` invokes `uv run pytest`; CI lockfile check runs `uv sync --frozen` to detect drift.

### React

- **Current stable version (April 2026):** 19.2.1 (released 2025-12-11). No 19.3 yet.
- **Recommended pin:** `react@^19.2.0`, `react-dom@^19.2.0`.
- **Sources:**
  - [React Versions page](https://react.dev/versions) — accessed 2026-04-22
  - [React 19.2 release notes](https://react.dev/blog/2025/10/01/react-19-2) — accessed 2026-04-22
  - [React 19 Upgrade Guide](https://react.dev/blog/2024/04/25/react-19-upgrade-guide) — accessed 2026-04-22
- **Key patterns / current idiom:**
  - New JSX transform is required — no need to `import React from "react"` in every file (the `react-jsx` compiler runtime handles it).
  - `ref` is a regular prop on function components (no `forwardRef` wrapper needed).
  - `useEffectEvent` (19.2) — stable event handlers inside effects without triggering re-runs.
  - `StrictMode` double-invokes effects and now double-invokes ref callbacks — dev-only; keep enabled.
- **Pitfalls / breaking changes since 18:**
  - Errors thrown during render are not re-thrown; uncaught errors go to `window.reportError`.
  - Legacy `propTypes` and `defaultProps` for function components are removed.
  - `@testing-library/react` peer-dep-pinned to `^18` in some older versions — need `@testing-library/react@^16` which officially supports React 19.
- **Design impact:** Wrap `<App />` in `<React.StrictMode>`. Do not import React just for JSX. Function components only — no class components needed for scaffold.
- **Test implication:** `@testing-library/react@^16.x` is required; older versions (13–15) break on React 19. Override peer deps with pnpm's `pnpm.overrides` if any transitive dep still wants React 18.

### Vite

- **Current stable version (April 2026):** 8.0.9 (released 2026-04-20). Vite 8.0 shipped 2026-03-12.
- **Recommended pin:** `vite@^8.0` (and `@vitejs/plugin-react@^5` — check latest compatible minor).
- **Sources:**
  - [Vite config — Server Options](https://vite.dev/config/server-options) — accessed 2026-04-22
  - [Vite 7 announcement](https://vite.dev/blog/announcing-vite7) — accessed 2026-04-22
  - [Vite GitHub releases](https://github.com/vitejs/vite/releases) — accessed 2026-04-22
- **Key patterns / current idiom:**
  - Scaffold with `pnpm create vite@latest frontend -- --template react-ts` then adjust.
  - `defineConfig()` with `plugins: [react()]`.
  - Dev server default port is 5173 — **override to 3000 in config** to match `CLAUDE.md` and PRD.
  - Vite 8 bundles Rolldown + Lightningcss as normal deps (~15 MB larger install vs Vite 7).
- **Pitfalls:** Vite 8 sets `optimizeDeps` differently from Vite 5 — legacy `cjs` deps may need `optimizeDeps.include`. Not a concern for a greenfield scaffold.
- **Design impact:** `vite.config.ts`:
  ```ts
  export default defineConfig({
    plugins: [react()],
    server: {
      port: 3000,
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
  });
  ```
  No `rewrite` needed — backend already serves `/api/v1/...`, so pass-through is correct.
- **Test implication:** Playwright `webServer.url` = `http://localhost:3000`. Backend must be up first (Playwright's `webServer` array can start both, or use `baseURL` + manual start).

### TypeScript

- **Current stable version (April 2026):** 5.7.x range (5.6 shipped 2024, 5.7 in 2025; 5.8 likely current by April 2026).
- **Recommended pin:** `typescript@^5.7`.
- **Sources:**
  - [TypeScript TSConfig Reference](https://www.typescriptlang.org/tsconfig/) — accessed 2026-04-22
  - [Vite with TypeScript guide (2026)](https://medium.com/@robinviktorsson/complete-guide-to-setting-up-react-with-typescript-and-vite-2025-468f6556aaf2) — accessed 2026-04-22
- **Key patterns / current idiom:**
  - Split `tsconfig.app.json` (app code) from `tsconfig.node.json` (vite.config.ts) via `references` in root `tsconfig.json`. This is the Vite `react-ts` template default.
  - `"jsx": "react-jsx"`, `"moduleResolution": "bundler"`, `"isolatedModules": true`, `"strict": true`, `"noUnusedLocals": true`, `"noUnusedParameters": true`, `"noFallthroughCasesInSwitch": true`, `"allowImportingTsExtensions": true`.
- **Pitfalls:** `"moduleResolution": "bundler"` requires TypeScript 5.0+. Do not mix with `"node"` / `"node16"` — pick `bundler` for Vite.
- **Design impact:** Ship the three-file tsconfig split exactly as Vite's `react-ts` template outputs. Add `// @ts-check` not necessary — strict mode is enough.
- **Test implication:** `tsc --noEmit -p tsconfig.app.json` is the typecheck gate. Add to Makefile / package.json scripts.

### Vitest

- **Current stable version (April 2026):** 3.x (Vitest 3 shipped early 2025, stable through 2026).
- **Recommended pin:** `vitest@^3.0`.
- **Sources:**
  - [Vitest config docs](https://vitest.dev/config/) — accessed 2026-04-22
  - [Vitest features](https://vitest.dev/guide/features) — accessed 2026-04-22
  - [happy-dom vs jsdom (2026)](https://www.pkgpulse.com/blog/happy-dom-vs-jsdom-2026) — accessed 2026-04-22
- **Key patterns / current idiom:**
  - Vitest reads `vite.config.ts` automatically; define a `test:` key there or use a separate `vitest.config.ts`. A separate config is cleaner when Vite config gets complex.
  - `environment: "jsdom"` for React component tests — more battle-tested than happy-dom. happy-dom is 2–4× faster but has edge-case gaps; for a scaffold with small test volume, choose jsdom for maturity.
  - Coverage via `provider: "v8"` (2–3× faster than istanbul).
- **Pitfalls:** Vitest 3 v8-coverage remapping is more accurate than v2 — coverage numbers may look different from old projects. No issue for greenfield.
- **Design impact:** `vitest.config.ts` with `environment: "jsdom"`, `setupFiles: ["./src/test/setup.ts"]` (imports `@testing-library/jest-dom/vitest` to register matchers), globals `true` for `describe/it/expect` without imports.
- **Test implication:** Component tests use `render()` from `@testing-library/react` and matchers from `@testing-library/jest-dom`. Keep tests colocated with components (`Button.test.tsx` beside `Button.tsx`).

### @testing-library/react + @testing-library/jest-dom

- **Current stable versions (April 2026):** `@testing-library/react@^16.x` (required for React 19), `@testing-library/jest-dom@^6.6.x`.
- **Recommended pin:** `@testing-library/react@^16`, `@testing-library/jest-dom@^6`, `@testing-library/user-event@^14`.
- **Sources:**
  - [@testing-library/react on npm](https://www.npmjs.com/package/@testing-library/react) — accessed 2026-04-22
  - [React Testing Library intro](https://testing-library.com/docs/react-testing-library/intro/) — accessed 2026-04-22
- **Key patterns:**
  - Import `@testing-library/jest-dom/vitest` (not `/jest-dom` plain) in setup file — this is the Vitest-specific entry that registers matchers with `expect.extend`.
  - Use `screen.getByRole(...)`, `screen.getByTestId(...)`. Avoid CSS selectors per `rules/testing.md`.
- **Pitfalls:** Peer-dep conflicts with React 19 on older @testing-library/react versions (<16). pnpm will error out — use `pnpm.overrides` in `package.json` only if a transitive dep pins React 18.
- **Design impact:** `frontend/src/test/setup.ts` imports jest-dom matchers. Components expose stable `data-testid` hooks for E2E (e.g. `data-testid="keyboard-letter-a"`, `data-testid="history-item-{id}"` per PRD US-003).
- **Test implication:** Tests for `Keyboard`, `ScorePanel`, `HistoryList` use `getByRole`/`getByTestId`. No `querySelector` or CSS class selectors.

### Playwright

- **Current stable version (April 2026):** 1.59.x (1.56 released 2025-Q4, 1.58/1.59 in 2026).
- **Recommended pin:** `@playwright/test@^1.59`.
- **Sources:**
  - [Playwright webServer docs](https://playwright.dev/docs/test-webserver) — accessed 2026-04-22
  - [Playwright release notes](https://playwright.dev/docs/release-notes) — accessed 2026-04-22
- **Key patterns / current idiom:**
  - `playwright.config.ts` with `testDir: "./tests/e2e/specs"`, `use: { baseURL: "http://localhost:3000" }`.
  - `webServer` can be **an array** to boot backend + frontend simultaneously:
    ```ts
    webServer: [
      {
        command: "cd ../backend && uv run uvicorn hangman.main:app --port 8000",
        url: "http://localhost:8000/api/v1/categories",
        reuseExistingServer: !process.env.CI,
      },
      {
        command: "pnpm dev",
        url: "http://localhost:3000",
        reuseExistingServer: !process.env.CI,
      },
    ];
    ```
  - Install browsers once: `pnpm exec playwright install chromium` (only need chromium for this scaffold).
  - Fixtures at `tests/e2e/fixtures/auth.ts` per `rules/testing.md` — this project has no auth, so the fixture is a no-op / minimal test-extension that simply re-exports `test` from `@playwright/test`. The skeleton file must still exist because `rules/testing.md` references it.
- **Pitfalls:** `webServer.timeout` defaults to 60s; increase to 120s for cold-start on CI (not activated here, but template).
- **Design impact:** Monorepo layout (frontend/ subdir). Place `playwright.config.ts` inside `frontend/` per the `rules/testing.md` "monorepo layout" note. `cd frontend && pnpm exec playwright test`.
- **Test implication:** One smoke spec `play-round.spec.ts` tagged `@smoke` for CI on-PR runs. Use `data-testid` selectors exclusively. First run should use Playwright MCP via verify-e2e agent to discover selectors (Phase 5.4 pattern), then graduate to a spec file in Phase 6.2c.

### ESLint

- **Current stable version (April 2026):** ESLint 9.x (flat config is now the default and required). `typescript-eslint` at 8.x.
- **Recommended pin:** `eslint@^9`, `typescript-eslint@^8`, `eslint-plugin-react-hooks@^5`, `eslint-plugin-react-refresh@^0.4`.
- **Sources:**
  - [ESLint Configuration Files (flat config)](https://eslint.org/docs/latest/use/configure/configuration-files) — accessed 2026-04-22
  - [typescript-eslint docs](https://typescript-eslint.io/) — accessed 2026-04-22
  - [ESLint + Prettier Setup (2026)](https://dev.to/_d7eb1c1703182e3ce1782/eslint-prettier-setup-the-complete-developer-configuration-guide-2026-4p8k) — accessed 2026-04-22
- **Key patterns / current idiom:**
  - `eslint.config.js` flat config (ESM or CJS). Legacy `.eslintrc.*` is unsupported in v9.
  - Compose with `tseslint.config(...)`:

    ```js
    import js from "@eslint/js";
    import tseslint from "typescript-eslint";
    import reactHooks from "eslint-plugin-react-hooks";
    import reactRefresh from "eslint-plugin-react-refresh";

    export default tseslint.config(
      { ignores: ["dist"] },
      {
        extends: [js.configs.recommended, ...tseslint.configs.recommended],
        files: ["**/*.{ts,tsx}"],
        plugins: { "react-hooks": reactHooks, "react-refresh": reactRefresh },
        rules: {
          ...reactHooks.configs.recommended.rules,
          "react-refresh/only-export-components": "warn",
        },
      },
    );
    ```

- **Pitfalls:** Many Vite templates still ship old `.eslintrc.cjs` — ensure the scaffold uses flat config. `@typescript-eslint/eslint-plugin` + parser are rolled into the `typescript-eslint` meta-package (drop the separate packages).
- **Design impact:** Ship `eslint.config.js` (not `.eslintrc`) in `frontend/`. Include `eslint-config-prettier` last to disable style rules (see Prettier).
- **Test implication:** `pnpm exec eslint .` passes as part of `make verify` / pre-commit equivalent. Scaffold's success metric (PRD §2) requires clean ESLint.

### Prettier

- **Current stable version (April 2026):** Prettier 3.x (3.5+).
- **Recommended pin:** `prettier@^3`, `eslint-config-prettier@^10`.
- **Sources:**
  - [Prettier install docs](https://prettier.io/docs/install) — accessed 2026-04-22
  - [eslint-config-prettier](https://github.com/prettier/eslint-config-prettier) — accessed 2026-04-22
- **Key patterns / current idiom:**
  - Run Prettier and ESLint as **separate tools**. Do NOT use `eslint-plugin-prettier` (slows ESLint, confusing errors).
  - Import `eslint-config-prettier/flat` (note the `/flat` suffix for ESLint 9) and put it LAST in the config array.
  - `.prettierrc.json` or `"prettier"` key in `package.json`. Minimal config: `{ "semi": true, "singleQuote": false, "trailingComma": "all" }`.
- **Pitfalls:** `eslint-plugin-prettier` is discouraged in 2026 docs.
- **Design impact:** `frontend/.prettierrc.json` + `eslint.config.js` ends with the flat-config import of `eslint-config-prettier/flat`. Scripts: `pnpm format` (writes), `pnpm format:check` (CI).
- **Test implication:** Add `prettier --check .` to the verify target so formatting drift fails the scaffold's success-metrics gate.

## Cross-cutting findings

### FastAPI + Vite dev proxy

- **Canonical pattern:** Vite `server.proxy["/api"] = { target: "http://localhost:8000", changeOrigin: true }`. No `rewrite` needed — FastAPI routes already live at `/api/v1/...` and we want the `/api` prefix preserved.
- **Source:** [Vite server options](https://vite.dev/config/server-options) — accessed 2026-04-22.
- `changeOrigin: true` is technically optional for localhost-to-localhost but recommended as hygiene (rewrites Host header to match target, avoids surprises if backend ever validates it).
- **Why this matters:** avoids CORS entirely in dev. Browser hits `http://localhost:3000/api/v1/games`, Vite proxies to `http://localhost:8000/api/v1/games`, same-origin from the browser's POV.
- **Pitfall:** If the backend reads `request.headers["host"]` to build absolute URLs (e.g. `Location` header for 201), `changeOrigin: true` means host will be `localhost:8000`, not `localhost:3000`. For `Location: /api/v1/games/{id}` relative URLs this is a non-issue — always use relative Locations.

### SQLite thread safety in FastAPI (2026)

- **Recommendation:** Sync SQLAlchemy + `connect_args={"check_same_thread": False}`.
- **Source:** [SQLAlchemy SQLite dialect](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html), [FastAPI SQL Databases tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/) — accessed 2026-04-22.
- **Why sync over async for this scaffold:**
  - Single-user local app; zero concurrent requests in the steady state.
  - Sync is simpler: fewer deps (no `aiosqlite`), simpler fixtures, no event-loop gymnastics in tests, `TestClient` works out of the box.
  - Async FastAPI + sync SQLAlchemy is a performance trap (slower than sync-sync per benchmarks) — don't accidentally land there by using `async def` routes with sync DB calls.
  - Benchmark data point: sync-sync ~600 req/s, async-async ~1400 req/s, but local single-user never touches these numbers.
- **Design impact:** All route handlers are `def` (sync), not `async def`. DB operations use sync `Session`. This also means we don't need `pytest-asyncio` at all (strong simplification).
- **Test implication:** Tests use sync `TestClient` from `fastapi.testclient`. No async fixtures. Lifespan fires automatically when `TestClient` is used as a context manager (`with TestClient(app) as client:`).

## Open Risks

- **Node 22 vs Node 20:** CLAUDE.md / PRD mention "Node 20+", but pnpm 10 dropped Node 20 support and pnpm 9 reaches EOL 2026-04-30 (8 days from now). **Scaffold should require Node 22+ and pnpm 10.x** — update the README/CLAUDE.md prerequisites. Otherwise a future dev on Node 20 will hit pnpm install errors after April 30.
- **Pydantic 2.13 was released 2 days ago (2026-04-20):** Unlikely to have unknown regressions for basic schemas, but worth allowing a narrow fallback (`pydantic>=2.9,<3` rather than `>=2.13`) so 2.13-specific issues don't block the scaffold.
- **Vite 8 is newer (March 2026):** Some React plugins / Storybook / testing adapters may still lag. For this scaffold (only `@vitejs/plugin-react` + Vitest), both track Vite 8, so low risk.
- **React 19 peer-dep conflicts** with any unlisted frontend dep that pins `react@^18`. Scaffold intentionally has no such deps, but monitor in future feature PRs.
- **Ruff 0.15.x:** New rule additions occasionally re-flag previously-clean code on upgrade. Pin narrowly (`<0.16`) so a `uv sync` doesn't silently introduce new lint failures.
- **SQLAlchemy 2.1 beta:** Tempting to skip ahead, but stay on 2.0.49 stable for scaffold. Revisit in 3–6 months.

## Not Researched (explicit triage)

- **`python-multipart`:** not touched — no form uploads in this scaffold.
- **`bcrypt` / `passlib`:** not touched — no auth, no passwords. `rules/security.md` covers them for other projects.
- **`itsdangerous`:** not touched — we're not using Starlette `SessionMiddleware` (see FastAPI cookie handling above).
- **`aiosqlite`:** not touched — scaffold uses sync SQLAlchemy.
- **`alembic`:** explicitly out of scope per PRD §5 ("no Alembic in the scaffold"). `Base.metadata.create_all()` at startup is sufficient.
- **Tailwind / styled-components / CSS-in-JS:** out of scope per PRD §2 non-goals.
- **Storybook:** not in stack.
- **CORS middleware:** not needed when using Vite's `server.proxy` — same-origin in dev. Production is out of scope (local-only per PRD).
- **`orjson` / custom JSON encoders:** Pydantic v2's default JSON serialization is already fast and handles `datetime` correctly; no need.
- **React Router:** PRD has a single-page scaffold (no routing yet). If history/game/category views become separate routes in a future feature, research React Router 7 then.
- **State management (Zustand / Redux / TanStack Query):** PRD scope is a single-page app with plain `fetch` wrappers + `useState`. No external state lib.
- **`concurrently` / `honcho`:** explicitly out of scope per PRD §2 ("two-terminal dev flow documented instead").
- **`mypy`:** mentioned in PRD §2 success metrics but not in research-target list. Standard setup: `mypy>=1.13`, `[tool.mypy]` in `pyproject.toml` with `strict = true`. Low risk, well-understood.

## Sources index (flat list of all URLs consulted)

- https://fastapi.tiangolo.com/release-notes/
- https://fastapi.tiangolo.com/advanced/events/
- https://fastapi.tiangolo.com/tutorial/sql-databases/
- https://fastapi.tiangolo.com/tutorial/testing/
- https://fastapi.tiangolo.com/advanced/async-tests/
- https://fastapi.tiangolo.com/advanced/response-cookies/
- https://docs.pydantic.dev/latest/api/config/
- https://docs.pydantic.dev/latest/migration/
- https://docs.pydantic.dev/latest/concepts/validators/
- https://pypi.org/project/pydantic/
- https://docs.sqlalchemy.org/en/20/changelog/whatsnew_20.html
- https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html
- https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html
- https://docs.sqlalchemy.org/en/20/dialects/sqlite.html
- https://pypi.org/project/sqlalchemy/
- https://www.uvicorn.org/
- https://www.uvicorn.org/settings/
- https://pypi.org/project/uvicorn/
- https://pytest-asyncio.readthedocs.io/en/latest/reference/configuration.html
- https://thinhdanggroup.github.io/pytest-asyncio-v1-migrate/
- https://www.python-httpx.org/advanced/transports/
- https://www.python-httpx.org/async/
- https://pypi.org/project/httpx/
- https://starlette.dev/middleware/
- https://docs.astral.sh/ruff/configuration/
- https://docs.astral.sh/ruff/settings/
- https://pypi.org/project/ruff/
- https://docs.astral.sh/uv/guides/projects/
- https://docs.astral.sh/uv/concepts/projects/sync/
- https://react.dev/versions
- https://react.dev/blog/2025/10/01/react-19-2
- https://react.dev/blog/2024/04/25/react-19-upgrade-guide
- https://vite.dev/guide/
- https://vite.dev/config/server-options
- https://vite.dev/blog/announcing-vite7
- https://github.com/vitejs/vite/releases
- https://www.typescriptlang.org/tsconfig/
- https://vitest.dev/config/
- https://vitest.dev/guide/features
- https://www.pkgpulse.com/blog/happy-dom-vs-jsdom-2026
- https://www.npmjs.com/package/@testing-library/react
- https://testing-library.com/docs/react-testing-library/intro/
- https://playwright.dev/docs/test-webserver
- https://playwright.dev/docs/release-notes
- https://playwright.dev/docs/test-configuration
- https://eslint.org/docs/latest/use/configure/configuration-files
- https://typescript-eslint.io/
- https://prettier.io/docs/install
- https://github.com/prettier/eslint-config-prettier
- https://pnpm.io/installation
- https://github.com/pnpm/pnpm/releases
