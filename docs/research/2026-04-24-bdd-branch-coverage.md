# Research: bdd-branch-coverage

**Date:** 2026-04-24
**Feature:** Developer-only Python tool that walks the FastAPI route table + static call graph for `backend/src/hangman/` and reports per-endpoint branch coverage of the BDD suite under `coverage.py --branch` instrumentation.
**Researcher:** research-first agent

---

## Libraries Touched

| Library       | Our Version (manifest)                     | Latest Stable (PyPI 2026-04-24) | Breaking Changes vs Ours                                                                            | Source                                                                                                                  |
| ------------- | ------------------------------------------ | ------------------------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `coverage.py` | (transitive via `pytest-cov>=5,<6`) ~7.6.x | 7.13.5 (2026-03-17)             | None breaking — additive (subprocess patches, JSON branch arcs, sigterm fix, function-level totals) | [PyPI](https://pypi.org/project/coverage/) (2026-04-24)                                                                 |
| `pyan3`       | NOT CURRENTLY INSTALLED                    | 2.5.0 (2026-04-21)              | N/A (new dep)                                                                                       | [PyPI pyan3](https://pypi.org/project/pyan3/), [Technologicat/pyan](https://github.com/Technologicat/pyan) (2026-04-24) |
| `pycg`        | NOT CURRENTLY INSTALLED                    | 0.0.7 (archived 2023-11-26)     | N/A (new dep, but ARCHIVED upstream)                                                                | [vitsalis/PyCG](https://github.com/vitsalis/PyCG) (2026-04-24)                                                          |
| `fastapi`     | `fastapi[standard]>=0.136,<0.137`          | 0.136.1 (2026-04-23)            | None — already on latest line                                                                       | [PyPI fastapi](https://pypi.org/project/fastapi/) (2026-04-24)                                                          |
| `Jinja2`      | `jinja2>=3.1.6,<3.2`                       | 3.1.6                           | None — already on latest minor                                                                      | [Snyk Jinja2](https://security.snyk.io/package/pip/jinja2) (2026-04-24)                                                 |

---

## Per-Library Analysis

### coverage.py

**Versions:** ours=transitively 7.6.x via `pytest-cov>=5,<6`; latest=7.13.5 (2026-03-17). Recommend pinning explicitly in `[dependency-groups] dev` (e.g., `coverage[toml]>=7.13,<7.14`) so Feature 3 is not at the mercy of `pytest-cov`'s lower bound.

**Breaking changes since ours:** None. The 7.6 → 7.13 delta is purely additive on the surfaces Feature 3 needs:

- **7.10.0** added `[run] patch = subprocess` (auto-instrument Python subprocesses), `patch = _exit` (write data on `os._exit`), and the first per-function/per-class JSON sections.
- **7.12.0** added separate statement vs branch totals to the JSON summary.
- **7.13.0** added `.coveragerc.toml` support; **7.13.1** added a `start_line` key on function/class regions; **7.13.5** is current.
- Earlier (7.x) the JSON report grew `executed_branches` and `missing_branches` arrays per file — the data Feature 3 needs to map dynamic branch hits back to the static reachable set.

**Deprecations relevant to this feature:** None. Branch mode (`--branch`, `Coverage(branch=True)`), the JSON reporter (`json_report()`), the data-file API (`load`, `combine`), and contexts are all stable.

**Recommended pattern (current best practice for what this feature does):**

1. **Subprocess-safe instrumentation of `uvicorn`.** Two viable approaches:
   - **A — `coverage run` wrapper + `[run] patch = subprocess, _exit`** (added 7.10.0). Launch the BDD-driving uvicorn as `uv run coverage run --branch --parallel-mode --rcfile=... -m uvicorn hangman.main:app ...`. The `parallel-mode` flag emits per-PID `.coverage.<host>.<pid>.<rand>` files; `coverage combine` merges them; `coverage json` produces the report. Works without ANY app-side cooperation. **This is the simplest path for an opt-in Make target.**
   - **B — Programmatic API in a wrapper script** (`coverage.Coverage(branch=True, data_file=..., source=["src/hangman"]).start()` → run uvicorn in-process or via subprocess → `.stop()` + `.save()`). More control but more moving parts; loses subprocess auto-capture unless `patch=subprocess` is also set.
   - **Recommend A.** It maps cleanly onto the existing `make bdd` shape (start backend, run cucumber, kill backend) by replacing the backend launcher one-liner.
2. **Long-running uvicorn lifetime.** uvicorn does not exit naturally during BDD; the BDD runner kills it. Use `[run] sigterm = true` (fixed in 7.13 via Lewis Gaul's PR #1599) so coverage flushes data on TERM rather than relying on graceful shutdown. Alternative: `coverage run --save-signal=SIGUSR1` and have the BDD harness send SIGUSR1 before SIGTERM.
3. **Branch-arc data extraction.** The 7.13 JSON schema per file:
   ```jsonc
   {
     "files": {
       "src/hangman/game.py": {
         "executed_lines":   [1,2,5,...],
         "missing_lines":    [10,12],
         "excluded_lines":   [],
         "executed_branches": [[5,6], [5,7], [12,-12], ...],
         "missing_branches":  [[5,8]],
         "summary": { "covered_lines": ..., "num_branches": ..., "covered_branches": ..., "missing_branches": ..., "percent_covered": ... },
         "functions": { "guess_letter": { "start_line": 42, "executed_lines":..., "missing_branches":... } },
         "classes":   { ... }
       }
     },
     "totals": { ... },
     "format": 2
   }
   ```
   Each branch is `[from_line, to_line]`; an exit branch uses **negative** target line numbers (e.g., `[12, -12]` = "exit from the function that starts at line 12"), preserved for round-trip with internal arc data. Feature 3's `ReachableBranch` model must accept negative target lines.
4. **Aggregate-only contexts.** PRD says aggregate, not per-scenario. Do NOT enable `[run] dynamic_context = test_function` (it's pytest-targeted anyway and useless here). Skip contexts entirely — simpler data shape, smaller `.coverage` file.

**Sources:**

1. [PyPI coverage 7.13.5](https://pypi.org/project/coverage/) — accessed 2026-04-24
2. [Coverage 7.13.5 changelog](https://coverage.readthedocs.io/en/latest/changes.html) — accessed 2026-04-24
3. [Coverage subprocess docs](https://coverage.readthedocs.io/en/latest/subprocess.html) — accessed 2026-04-24
4. [Coverage Python API](https://coverage.readthedocs.io/en/latest/api_coverage.html) — accessed 2026-04-24
5. [PR #1438 — branch details to JSON](https://github.com/coveragepy/coveragepy/pull/1438) — accessed 2026-04-24

**Design impact:**

- **Pin `coverage>=7.13,<7.14` directly in dev deps.** Don't rely on `pytest-cov`'s transitive constraint — Feature 3 needs `patch = subprocess` (≥7.10) and `sigterm` fix (7.13).
- **Choose the subprocess-wrapper approach (Approach A above)** for the `make bdd-coverage` target. Implementation is `coverage run --branch --parallel-mode --rcfile=tools/branch_coverage/.coveragerc -m uvicorn hangman.main:app` + `coverage combine` + `coverage json`.
- **Schema mapper must handle negative target lines** in `executed_branches` / `missing_branches` (exit arcs). The `ReachableBranch.branch_id` (PRD §6) should store `(from_line, to_line)` verbatim — do not coerce sign.
- **Configure `[run] sigterm = true` and `parallel = true` in `.coveragerc`** so the long-running uvicorn flushes data on the BDD harness's TERM and per-PID files don't collide.
- **Do not enable contexts.** PRD says aggregate; simpler data file.

**Test implication:**

- Unit-test the JSON-schema parser against a fixture `coverage.json` containing both positive and **negative** target lines — easiest path to wrong code is treating `to_line < 0` as "invalid" instead of "exit arc".
- Integration test: spin up a tiny FastAPI app under `coverage run --branch --parallel-mode`, hit one endpoint, send SIGTERM, run `coverage combine + json`, and assert the data file has at least one `executed_branches` entry. This guards against silently-broken instrumentation (e.g., `sigterm` config not applied → empty data file → all-red report).

---

### pyan3 vs pycg (static call-graph) — **DECISION: pyan3**

**Versions:** pyan3=2.5.0 (released 2026-04-21, three days ago); pycg=0.0.7 (archived 2023-11-26, "no further development improvements are planned").

**Breaking changes since ours:** N/A — both are new dependencies.

**Deprecations relevant to this feature:** **pycg is archived** (read-only repo, owner Vitalis Salis stated "due to limited availability, no further development improvements are planned"). Not a deprecation per se, but functionally equivalent: no Python-3.13/3.14 maintenance, no fix for any FastAPI-decorator edge case discovered during Feature 3 development.

**Comparison:**

| Axis                       | pyan3 (2.5.0)                                                                                                                                                                                                                                           | pycg (0.0.7, archived)                                    |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Maintenance                | Actively maintained — revived Feb 2026 by Technologicat, 19 releases, latest 2026-04-21                                                                                                                                                                 | **Archived 2023-11-26**, no future work                   |
| Python 3.12 / 3.13 / 3.14  | Explicitly tested on 3.10–3.14 (PEP 695 type aliases, `match`, walrus, `async with`)                                                                                                                                                                    | Targets ≥3.4; no recent verification on 3.12+             |
| Modern syntax              | Yes — including type aliases, `match`, walrus, `async with`                                                                                                                                                                                             | Older AST handling; risk of failure on 3.12+ syntax       |
| Internal test coverage     | "200+ tests, 91% branch coverage"                                                                                                                                                                                                                       | Limited                                                   |
| Speed / memory             | Faster + lower memory than pycg per published benchmarks (≤3.5k LoC: subsecond, 2× faster)                                                                                                                                                              | ~2× slower, ~2.8× more memory                             |
| Programmatic API           | Yes — `pyan.create_callgraph(...)` and direct `CallGraphVisitor(["pkg/mod.py"])` with `.get_node()`, `.find_paths(src, tgt)`, plus a sans-IO `from_sources([(src, modname), ...])` mode                                                                 | Yes — JSON adjacency list output (callable, but archived) |
| FastAPI decorator handling | **Not perfect.** Decorator-based registration (`@router.get("/x")`) is dynamic dispatch; pyan3 will see the route handler as a top-level callable and trace its body, but `Depends(...)` injection chains are not statically resolvable by either tool. | Same fundamental limitation; no improvements coming       |
| Async function support     | Explicit `async with` + async function support documented                                                                                                                                                                                               | Not documented; older codebase                            |
| Output formats             | DOT, SVG, HTML, plain text, TGF, yEd; programmatic graph access via `CallGraphVisitor`                                                                                                                                                                  | JSON adjacency list, FASTEN format                        |
| License                    | GPL v2+                                                                                                                                                                                                                                                 | BSD                                                       |

**License caveat (MUST flag for design phase):** pyan3 is **GPL v2+**. The Hangman project does not yet ship under any license file (no LICENSE in repo root). For a developer-only, never-distributed dev tool that imports pyan3 _at dev time only_, GPL is generally not viral onto the application code being analyzed (we run pyan3 as a tool against our source, not link it into our deployment). Still — flag for the design phase to confirm the legal model and to make sure `pyan3` lands in `[dependency-groups] dev` (NOT `dependencies`) so the runtime app remains GPL-clean.

**Recommended pattern:**

```python
from pyan.analyzer import CallGraphVisitor

# Build visitor against backend/src/hangman/*.py only — boundary enforcement
visitor = CallGraphVisitor([
    "src/hangman/main.py",
    "src/hangman/routes.py",
    "src/hangman/game.py",
    # ... etc
])

# For each route handler discovered via FastAPI's app.routes, walk reachable callees
handler_node = visitor.get_node("hangman.routes", "create_game")
# find_paths(src, tgt) requires a target — we don't have one; instead BFS visitor.uses_edges
# from handler_node, filter out nodes whose namespace is not in {hangman.*}.
```

The published `find_paths(src, tgt)` API expects a known source and target. For our walk (handler → all reachable internal callees), we BFS the visitor's internal `uses_edges` dict starting at the handler node and prune edges that leave the `hangman.*` namespace. This is the boundary-enforcement strategy from PRD §5.

**Sources:**

1. [PyPI pyan3 2.5.0](https://pypi.org/project/pyan3/) — accessed 2026-04-24
2. [Technologicat/pyan GitHub](https://github.com/Technologicat/pyan) — accessed 2026-04-24
3. [vitsalis/PyCG GitHub (archived)](https://github.com/vitsalis/PyCG) — accessed 2026-04-24
4. [PyCG academic paper (Salis et al., 2021)](https://arxiv.org/pdf/2103.00587) — accessed 2026-04-24

**Design impact:**

- **Pick pyan3.** Open question Q1 in the PRD is closed. pycg is archived; using a dead dependency for a feature we expect to live for years is a known liability.
- **Add `pyan3>=2.5,<3` to `[dependency-groups] dev`** (NOT `dependencies`) — keeps the GPL boundary at dev tooling.
- **Use the `CallGraphVisitor` programmatic API**, not the CLI. Walk `visitor.uses_edges` BFS from each route-handler node; prune at the `hangman.*` namespace boundary (PRD §5 "boundary enforcement").
- **Document that `Depends(...)` chains and other dynamic dispatch are NOT statically resolvable** — this is _by design_ (PRD §4 Acceptance for US-004: "If coverage.py records a hit on a function that the static graph DIDN'T link to any endpoint, report it as 'extra coverage'"). The "extra coverage" bucket is the safety valve; it's not a bug, it's the architecture.
- **Plan for a LICENSE decision:** before merging, the team should add a top-level LICENSE file for the project so the GPL-tool-vs-app-code boundary is unambiguous in the repo.

**Test implication:**

- **Fixture-based unit tests on a pyan3 quirk corpus.** Build small `tests/fixtures/sample_pkg/` modules covering: `@app.get` decorator, `async def` handlers, lambda inside handler, `Depends()` injection, calls into another module. Assert the CallGraphVisitor edges match expected sets — and **document expected misses** (Depends, dynamic dispatch) as XFAIL with explanatory comments. These tests guard against pyan3 upstream regressions.
- **Integration test on the real `backend/src/hangman/`:** assert the visitor finds at least one edge from each route handler to `game.py`, `words.py`, `sessions.py`, etc. — sanity bound, not exact set.

---

### FastAPI route enumeration via `app.routes`

**Versions:** ours=`fastapi[standard]>=0.136,<0.137`; latest=0.136.1 (2026-04-23, one day ago). We're effectively on latest.

**Breaking changes since ours:** None — already on the latest line.

**Deprecations relevant to this feature:** None. `app.routes` is a stable Starlette-inherited attribute, and FastAPI's `APIRoute` (subclass of `BaseRoute`) is documented as the canonical introspection surface.

**Recommended pattern:**

```python
from fastapi.routing import APIRoute
from starlette.routing import Mount, WebSocketRoute

# Import the app WITHOUT triggering its lifespan
from hangman.main import app    # FastAPI() construction runs; lifespan does NOT fire on import

endpoints: list[Endpoint] = []
for route in app.routes:
    if isinstance(route, APIRoute):
        # `route.path` keeps {param} placeholders, e.g., "/api/v1/games/{game_id}"
        # `route.methods` is a set, e.g., {"POST"}
        # `route.endpoint` is the handler callable; route.endpoint.__module__ + .__qualname__
        for method in sorted(route.methods or []):
            if method == "HEAD":
                continue
            endpoints.append(Endpoint(
                method=method,
                path=route.path,
                handler_qualname=f"{route.endpoint.__module__}.{route.endpoint.__qualname__}",
            ))
    elif isinstance(route, WebSocketRoute):
        # PRD §4 US-003 edge case: WebSocket out of scope; skip silently
        continue
    elif isinstance(route, Mount):
        # Sub-applications mounted via app.mount — out of scope for v1; warn
        continue
```

**Confirmed: importing `hangman.main:app` does NOT trigger startup events.** Per FastAPI docs (also explicit in the framework's design): the `lifespan` context manager / `on_startup` handlers fire only when the ASGI server starts the app — not at import time. This is exactly what Feature 3 needs to introspect routes without spinning up SQLAlchemy/SQLite.

**Caveat — module-import side effects.** `app.routes` is built via decorator side effects, which means `routes.py` is imported as part of constructing `app`. If `routes.py` (or anything it imports) does work at import time other than registering routes (e.g., creating DB engines at module scope, opening files), that work _will_ run on `from hangman.main import app`. Quick scan of the project's stated structure (`db.py`, `models.py`, `sessions.py`) suggests these may construct engines at import time. The design phase should: (a) inspect `db.py` for module-scope side effects, (b) if any, decide whether to gate them behind a lazy factory or accept the cost of one engine creation per `make bdd-coverage` static-analysis pass.

**Sources:**

1. [FastAPI APIRouter reference](https://fastapi.tiangolo.com/reference/apirouter/) — accessed 2026-04-24
2. [FastAPI routing.py source](https://github.com/fastapi/fastapi/blob/master/fastapi/routing.py) — accessed 2026-04-24
3. [FastAPI lifespan / on_startup events docs (via fastapi.tiangolo.com reference)](https://fastapi.tiangolo.com/reference/fastapi/) — accessed 2026-04-24

**Design impact:**

- **Use the reflective `app.routes` approach, NOT AST-parsing `routes.py`.** Open question Q4 in the PRD is closed: reflective wins because (a) it correctly handles `app.include_router(prefix="/api/v1")` prefix concatenation for free; (b) Starlette/FastAPI does the path-param normalization for us; (c) any future `add_api_route()` programmatic registrations are picked up automatically.
- **Filter by `isinstance(route, APIRoute)`** to skip `Mount` and `WebSocketRoute`. PRD §4 US-003 already declares WebSocket out of scope; the implementation should silently skip + log a debug message.
- **Iterate `sorted(route.methods)` and emit one `Endpoint` per (method, path) pair.** Skip `HEAD` (auto-added by Starlette for GET routes; not user-defined).
- **Audit module-import side effects in `db.py` / `sessions.py` / `models.py`** during design phase. If `db.py` opens an engine at module scope, decide between (a) lazy-init refactor or (b) accept one extra engine creation per static pass.

**Test implication:**

- Unit test the enumerator against a fixture `FastAPI()` app that includes a router with `prefix="/api/v1"`, two `APIRoute`s, one `WebSocketRoute`, and one mounted sub-app. Assert exactly the expected `(method, path, handler_qualname)` set is returned, and Mount + WebSocket are excluded.
- Add a regression test that imports `hangman.main:app` and asserts `app.routes` is non-empty without any DB file being created in the working directory — guards against future module-scope side-effect drift.

---

### `coverage.py` programmatic JSON output (schema confirmation)

Covered above under coverage.py's "Recommended pattern" §3; no separate section needed. Schema is stable since 7.6 and progressively richer through 7.13. `format: 2` field at the top level lets Feature 3's parser version-gate.

---

### Jinja2

**Versions:** ours=`jinja2>=3.1.6,<3.2`; latest=3.1.6. We're current.

**Breaking changes since ours:** None.

**Deprecations relevant to this feature:** None.

**Security advisories relevant:** No CVEs against Jinja2 3.1.6 itself as of 2026-04-24. Multiple 2026 CVEs exist in _applications_ that use Jinja2 unsafely (Home Assistant CLI, BentoML, Giskard, dynaconf — all SSTI/RCE via unsandboxed user-supplied templates). None affect our usage: Feature 3 renders developer-controlled templates against developer-controlled data, no user-supplied template strings.

**Recommended pattern:** Reuse Feature 2's existing pattern — `Environment(loader=FileSystemLoader(...), autoescape=select_autoescape(["html", "j2"]))`. Source-code snippets in the drill-down (uncovered branch text from `routes.py`) ARE rendered into HTML and ARE escaped by default via `select_autoescape` — confirmed safe.

**Sources:**

1. [Snyk Jinja2 vulnerability list](https://security.snyk.io/package/pip/jinja2) — accessed 2026-04-24
2. PRD §7 Security Considerations — referenced

**Design impact:** No impact — reuse Feature 2's Renderer setup verbatim. Feature 3's `coverage.html` is a sibling artifact, not a dashboard fork.

**Test implication:** Standard coverage sufficient. Worth one assertion that an uncovered-branch snippet containing `<` / `>` / `&` (e.g., a `if x < 0:` from source) renders HTML-escaped in the output.

---

## Not Researched (with justification)

- **Anthropic SDK** — Feature 3 does not call the LLM. Feature 2 already integrates it; Feature 3 only writes a `coverage.json` artifact that Feature 2's Packager reads. Per the prompt's NOT-to-research list.
- **Chart.js** — Feature 2's choice; Feature 3 may or may not use a chart in `coverage.html` (design decision). Even if used, it's a CDN-loaded `<script>` tag with no version-conflict surface in our backend.
- **`@cucumber/cucumber` / `cucumber-messages`** — Feature 1 + Feature 2 already cover. Feature 3 produces a distinctly-named NDJSON (`cucumber.coverage.ndjson`) but the format is unchanged.
- **`pytest-cov`** — Feature 3 is BDD-driven, not pytest-driven. We pin coverage.py directly (recommended above) so pytest-cov's transitive bound becomes irrelevant for this feature.
- **`uvicorn`** — Already pinned `>=0.45,<0.46`; Feature 3 wraps it via `coverage run -m uvicorn`, no API surface change.
- **`Starlette`** — Transitive via FastAPI; `BaseRoute` / `Mount` / `WebSocketRoute` are stable interfaces inherited via `app.routes`. No independent research needed.

---

## Open Risks

1. **pyan3 GPL v2+ license boundary.** GPL is generally non-viral when used as a build/dev tool against your own code (we don't link or distribute it), but the Hangman repo currently ships without a LICENSE file. **Action: design phase should add a top-level LICENSE before merging Feature 3,** and confirm pyan3 is added to `dev` deps only — never to runtime `dependencies`. Low-likelihood ship-blocker; should not surprise the team at PR-review time.

2. **pyan3 + FastAPI `Depends()` injection chains are not statically resolvable.** This is _expected_ (PRD §4 US-004 acceptance accommodates this via "extra coverage" bucket), but the user-visible report will likely show non-trivial "extra coverage" cardinality. Surface this in the report's banner/legend so developers don't read it as a bug.

3. **Module-import side effects in `backend/src/hangman/`.** `from hangman.main import app` triggers all module-scope code in `db.py`, `models.py`, `sessions.py`. If these construct an engine or open the SQLite file at import time, Feature 3's static analysis pass will pay the cost and may pollute the test environment. **Action: audit during design phase; refactor to lazy if found.**

4. **Coverage instrumentation of long-running uvicorn requires correct termination signaling.** If the BDD harness (`Makefile` or wrapper script) sends `SIGKILL` instead of `SIGTERM`, coverage.py's `[run] sigterm = true` doesn't help — data file ends up empty and the report shows 0% everywhere. **Action: Feature 3's Make target must explicitly send SIGTERM (or the documented `--save-signal=SIGUSR1`) and wait for clean exit before invoking `coverage combine`.**

5. **PRD success-metric: ≤ 50% slowdown vs `make bdd`.** Coverage.py branch mode typically adds 10–30% on Python 3.12 with the C tracer, but BDD scenarios that exercise the SQLite write path may amplify that. **Action: design phase should add one early "instrumentation budget" smoke test (run all 33 scenarios under instrumentation, time it, record baseline) so the team can spot regression early — not at code-review time.**

6. **pyan3 was released 3 days ago (2.5.0 — 2026-04-21) and revived only Feb 2026.** While the 200+ test suite + 91% self-branch-coverage is reassuring, "1 month of revived activity" is not "5 years stable." The Feb-2026 revival was carried out with Claude as pair-programmer per the maintainer's notes. **Action: pin tightly (`pyan3>=2.5,<2.6`) and treat the dependency as moderate-risk for the next 6 months; have a fallback plan to vendor the relevant CallGraphVisitor code if upstream goes dormant again.** Note: pycg, the only static-call-graph alternative on PyPI with Python 3 support, is itself archived — there is no second-source escape hatch other than vendoring or rolling our own AST walker.

7. **`coverage.json` schema versioning.** The JSON reporter emits `format: 2` at the top level. A future coverage.py 8.x could bump this. **Action: Feature 3's parser should assert `format == 2` and emit a clear error ("upgrade Feature 3 for new coverage.py format") rather than silently mis-parse.**

8. **Negative target lines in branch arcs are easy to mishandle.** `executed_branches: [[12, -12]]` means "exit from the function starting at line 12." A naive parser that filters `to_line >= 0` will silently drop all exit arcs from the report, distorting per-function rollups. **Action: parser test fixture must include negative target lines; parser should preserve them as-is in `ReachableBranch.branch_id`.**

---

## Recommendation Summary

- **pyan3 wins over pycg** for static call-graph extraction (open question Q1 closed). pycg archived 2023-11-26; pyan3 actively maintained as of 2026-04-21 with explicit 3.10–3.14 support.
- **Pin `coverage>=7.13,<7.14` directly** in `[dependency-groups] dev` — don't rely on `pytest-cov`'s transitive bound. Need 7.10's `patch = subprocess` and 7.13's `sigterm` fix.
- **Approach A (`coverage run --branch --parallel-mode -m uvicorn ...`) for the `make bdd-coverage` target.** Simpler than the in-process API approach; correctly handles uvicorn worker subprocesses.
- **Reflective `app.routes` enumeration** beats AST-parsing `routes.py` (open question Q4 closed). Importing `hangman.main:app` does NOT fire lifespan events.
- **GPL license boundary** for pyan3 needs design-phase attention; add LICENSE to repo root and keep pyan3 in dev deps only.
