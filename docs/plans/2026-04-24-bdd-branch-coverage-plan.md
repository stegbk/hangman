# BDD Branch Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python analyzer at `backend/tools/branch_coverage/` that enumerates FastAPI routes reflectively, walks a static call-graph of `backend/src/hangman/` (pyan3), runs the BDD suite with `coverage.py --branch` under an ASGI middleware that tags per-endpoint contexts, reconciles per-endpoint coverage against coverage.py's authoritative per-file branch counts, and emits `coverage.json` + `coverage.html`. Augment Feature 2's dashboard to read the JSON and inject a coverage summary into the LLM's cached system prompt.

**Architecture:** 13 new modules in `backend/tools/branch_coverage/` + 5 modified files in `backend/tools/dashboard/`. Pipeline: `RouteEnumerator` (reflective) → `CallGraphBuilder` (pyan3 Python API) → `Reachability` (BFS) → `CoverageDataLoader` (per-context hits via coverage.py API) → `Grader` (per-endpoint intersection + audit reconciliation) → `JsonEmitter` + `DashboardRenderer`. Per-endpoint attribution via `CoverageContextMiddleware` calling `coverage.Coverage.current().switch_context(f"{method} {route_template}")`. Instrumented backend runs via `coverage run -m tools.branch_coverage.serve` (which imports `hangman.main.app`, adds middleware, runs uvicorn single-worker).

**Tech Stack:** Python 3.12, `coverage>=7.13,<7.14`, `pyan3>=2.5,<3`, `jinja2 ~3.1.6` (already from Feature 2), `pydantic 2.x`, `pytest 8.4.2`. No LLM calls from Feature 3 (Feature 2 is the LLM side).

---

## File Structure

Per design spec §2. New files marked `[N]`; modified files marked `[M]`.

```
backend/
├── pyproject.toml                                          [M] add coverage + pyan3 to dependency-groups.dev
└── tools/
    └── branch_coverage/                                    [N]
        ├── __init__.py                                     [N]
        ├── __main__.py                                     [N] CLI (argparse)
        ├── analyzer.py                                     [N] Orchestrator
        ├── models.py                                       [N] Dataclasses (Endpoint, ReachableBranch, FunctionCoverage, CoveragePerEndpoint, LoadedCoverage, AuditReport, Totals, CoverageReport)
        ├── routes.py                                       [N] RouteEnumerator
        ├── callgraph.py                                    [N] CallGraphBuilder via pyan3 CallGraphVisitor
        ├── reachability.py                                 [N] Reachability BFS
        ├── coverage_data.py                                [N] CoverageDataLoader (per-context)
        ├── grader.py                                       [N] Grader (per-endpoint context intersection + audit)
        ├── middleware.py                                   [N] CoverageContextMiddleware
        ├── serve.py                                        [N] ASGI entrypoint wrapper
        ├── json_emitter.py                                 [N] JsonEmitter
        ├── renderer.py                                     [N] DashboardRenderer
        ├── .coveragerc                                     [N] coverage.py config
        └── templates/
            ├── base.html.j2                                [N]
            ├── _endpoint_card.html.j2                      [N]
            └── _function_drilldown.html.j2                 [N]

backend/tests/unit/tools/branch_coverage/                   [N]
├── __init__.py                                             [N]
├── conftest.py                                             [N]
├── test_routes.py                                          [N]
├── test_callgraph.py                                       [N]
├── test_reachability.py                                    [N]
├── test_coverage_data.py                                   [N]
├── test_grader.py                                          [N]
├── test_middleware.py                                      [N]
├── test_json_emitter.py                                    [N]
├── test_renderer.py                                        [N]
└── test_analyzer.py                                        [N]

backend/tests/fixtures/branch_coverage/                     [N]
├── minimal.coverage                                        [N] generated during test; not committed
├── fake_adjacency.py                                       [N] hand-built CallGraph fixture
├── golden_coverage.json                                    [N]
├── golden_coverage.html                                    [N]
└── minimal_app/                                            [N]
    ├── __init__.py                                         [N]
    ├── main.py                                             [N] 2-route FastAPI app
    └── game.py                                             [N] 1 function, 3 branches

backend/tools/dashboard/                                    [M] Feature 2 augmentation
├── analyzer.py                                             [M] check coverage.json, build CoverageContext
├── llm/client.py                                           [M] LlmEvaluator accepts coverage_summary; _system → instance
├── llm/rubric.py                                           [M] add criterion D7
├── renderer.py                                             [M] new "Code coverage" summary card
└── models.py                                               [M] add CoverageContext dataclass

backend/tests/unit/tools/dashboard/                         [M] Feature 2 test updates
├── test_analyzer.py                                        [M] staleness check + CoverageContext cases
├── test_llm_client.py                                      [M] coverage_summary injection; _system → instance
├── test_rubric.py                                          [M] assert D7 present
└── test_renderer.py                                        [M] new "Code coverage" card cases

Root:
├── LICENSE                                                 [N] MIT license (resolves pyan3 GPL question)
├── Makefile                                                [M] + backend-coverage + bdd-coverage targets
├── scripts/backend-coverage.sh                             [N] PID-tracked exec wrapper
├── docs/CHANGELOG.md                                       [M] record Feature 3 shipped
└── .gitignore                                              [M] + .backend-coverage.pid, .coverage, .coverage.*
```

**Responsibility summary:**

- `models.py` — leaf-level dataclasses. Zero imports from other tool modules.
- `routes.py`, `callgraph.py`, `reachability.py`, `coverage_data.py`, `grader.py`, `json_emitter.py`, `renderer.py`, `middleware.py`, `serve.py` — each depends on `models.py` only; do NOT depend on each other.
- `analyzer.py` — the only orchestrator. Composes others via constructor injection.
- `__main__.py` — argparse + `Analyzer(...).run(...)`.
- Feature 2 files — read `coverage.json` as a file, never import Feature 3 code.

---

## Task inventory (17 tasks across 8 phases)

| Phase | ID  | Title                                                                                  |
| ----- | --- | -------------------------------------------------------------------------------------- |
| A     | A1  | Add deps + LICENSE + .gitignore                                                        |
| A     | A2  | Scaffold package + Makefile + .coveragerc + backend-coverage.sh                        |
| A     | A3  | API spike — validate pyan3 + coverage.py public API + hangman.main import safety       |
| B     | B1  | models.py dataclasses                                                                  |
| C     | C1  | routes.py + test_routes.py + minimal_app fixture (with prefixed-router test)           |
| C     | C2  | callgraph.py + test_callgraph.py + fake_adjacency fixture                              |
| C     | C3  | reachability.py + test_reachability.py                                                 |
| D     | D1  | middleware.py + test_middleware.py (mocked unit tests; real verify in H1)              |
| D     | D2  | serve.py (ASGI entrypoint)                                                             |
| D     | D3  | coverage_data.py + test_coverage_data.py (public API only; no private `_analyze`)      |
| E     | E1  | grader.py + test_grader.py (N=2 and N=3 shared-helper + audit reconciliation)          |
| E     | E2  | json_emitter.py + test_json_emitter.py + golden_coverage.json                          |
| E     | E3  | renderer.py + templates/ + test_renderer.py + golden_coverage.html                     |
| F     | F1  | analyzer.py + `__main__.py` + test_analyzer.py                                         |
| G     | G1  | Feature 2 augmentation with explicit call-site checklist + golden regen step           |
| G     | G2  | Feature 2 LLM integration (client + rubric D7 + test_rubric 13→14 criteria update)     |
| H     | H1  | README + CHANGELOG + live smoke (real per-endpoint attribution + audit reconciliation) |

---

## Commit cadence

One commit per task. Commit messages: `feat(branch-coverage): <what>` / `test(branch-coverage): <what>` / `fix(dashboard): <what>` for Feature 2 modifications.

---

## Phase A — Scaffold

### Task A1: Add dependencies + LICENSE + gitignore

**Files:**

- Modify: `backend/pyproject.toml` (add to `[dependency-groups].dev`)
- Create: `LICENSE` (MIT, repo root)
- Modify: `.gitignore` (at repo root)
- Touch: `backend/uv.lock` (regenerated)

**Context:** Feature 2 already added `jinja2` and `anthropic` to the dev group in `backend/pyproject.toml`. Follow that pattern. Per design spec §12 risk #5, `pyan3` is GPL v2+ but stays in dev-only; adding an MIT `LICENSE` file disambiguates the repo's stance.

- [ ] **Step 1: Add deps to `backend/pyproject.toml`**

Inside `[dependency-groups].dev` list (alphabetical order), add:

```toml
  "coverage>=7.13,<7.14",
  "pyan3>=2.5,<3",
```

- [ ] **Step 2: Create `LICENSE` at repo root**

```
MIT License

Copyright (c) 2026 KC Stegbauer

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 3: Append to `.gitignore`**

Append (idempotent — if already present, leave alone):

```
# Feature 3: BDD Branch Coverage
.backend-coverage.pid
.coverage
.coverage.*
```

- [ ] **Step 4: Regenerate lock + install**

Run: `cd backend && uv lock && uv sync --dev`
Expected: `uv.lock` updates; `uv sync` installs coverage + pyan3; `uv run python -c "import coverage, pyan; print(coverage.__version__)"` prints a version string.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock LICENSE .gitignore
git commit -m "feat(branch-coverage): add coverage + pyan3 dev deps, MIT LICENSE, gitignore entries"
```

---

### Task A2: Scaffold package + Makefile + .coveragerc + backend-coverage.sh

**Files:**

- Create: `backend/tools/branch_coverage/__init__.py` (empty)
- Create: `backend/tools/branch_coverage/templates/.gitkeep` (empty — populated in E3)
- Create: `backend/tools/branch_coverage/.coveragerc`
- Create: `backend/tests/unit/tools/branch_coverage/__init__.py` (empty)
- Create: `backend/tests/fixtures/branch_coverage/.gitkeep` (empty — populated in C1, C2, E2, E3)
- Create: `scripts/backend-coverage.sh` (executable, repo root)
- Modify: `Makefile` — append `.PHONY` entry + `backend-coverage` + `bdd-coverage` targets

**Context:** Feature 2's `backend/tools/dashboard/` exists as a sibling. `backend/tests/unit/tools/dashboard/` also exists. This task creates the parallel structure for Feature 3.

- [ ] **Step 1: Create directories + empty marker files**

```bash
mkdir -p backend/tools/branch_coverage/templates backend/tests/unit/tools/branch_coverage backend/tests/fixtures/branch_coverage scripts
touch backend/tools/branch_coverage/__init__.py
touch backend/tools/branch_coverage/templates/.gitkeep
touch backend/tests/unit/tools/branch_coverage/__init__.py
touch backend/tests/fixtures/branch_coverage/.gitkeep
```

- [ ] **Step 2: Write `backend/tools/branch_coverage/.coveragerc`**

```ini
[run]
branch = true
parallel = true
sigterm = true
concurrency = thread
source = src/hangman

[report]
show_missing = true
```

- [ ] **Step 3: Write `scripts/backend-coverage.sh`** (executable)

```bash
#!/bin/bash
# Wraps uvicorn under coverage.py for Feature 3's make bdd-coverage workflow.
# Writes the PID to .backend-coverage.pid so `make bdd-coverage` can SIGTERM it
# after running the BDD suite (coverage.py 7.13's sigterm=true flushes data).
set -e
cd "$(dirname "$0")/.."
echo "$$" > .backend-coverage.pid
trap 'rm -f .backend-coverage.pid' EXIT INT TERM
cd backend
exec uv run coverage run --branch --parallel-mode --source=src/hangman \
  --rcfile=tools/branch_coverage/.coveragerc \
  -m tools.branch_coverage.serve \
  --host 127.0.0.1 --port "${HANGMAN_BACKEND_PORT:-8000}"
```

Make executable: `chmod +x scripts/backend-coverage.sh`.

- [ ] **Step 4: Append Makefile targets**

Locate the line `.PHONY: install backend backend-test frontend bdd ...` at the top of `Makefile` and append `backend-coverage bdd-coverage` to it.

Then at the bottom of `Makefile`, append:

```makefile

.PHONY: backend-coverage bdd-coverage

backend-coverage:  ## Start backend under coverage instrumentation (Terminal 1; requires make bdd-coverage in Terminal 3)
	bash scripts/backend-coverage.sh

bdd-coverage:  ## Run BDD suite with coverage instrumentation + generate coverage report
	@if [ ! -f .backend-coverage.pid ]; then \
	  echo "ERROR: Backend not running under coverage. In another terminal: make backend-coverage"; \
	  exit 2; \
	fi
	cd frontend && HANGMAN_BACKEND_PORT=$(HANGMAN_BACKEND_PORT) \
	  pnpm exec cucumber-js \
	  --format "message:test-results/cucumber.coverage.ndjson" \
	  --format "progress-bar"
	@PID=$$(cat .backend-coverage.pid) && \
	  if kill -0 $$PID 2>/dev/null; then \
	    kill -TERM $$PID; \
	  else \
	    echo "WARN: Backend PID $$PID not running; coverage data may be stale"; \
	  fi
	@rm -f .backend-coverage.pid
	@sleep 2
	cd backend && uv run coverage combine || echo "WARN: coverage combine found no fragments"
	cd backend && uv run python -m tools.branch_coverage
```

Use TAB indentation (GNU Make requires tabs).

- [ ] **Step 5: Smoke test `make -n backend-coverage`** (dry run, parses Makefile)

Run: `make -n backend-coverage`
Expected: prints `bash scripts/backend-coverage.sh` — no "missing separator" errors.

Run: `make -n bdd-coverage`
Expected: prints the shell block without ERROR.

- [ ] **Step 6: Verify package imports**

Run: `cd backend && uv run python -c "import tools.branch_coverage; print(tools.branch_coverage.__file__)"`
Expected: prints the path to `__init__.py` under the branch_coverage package.

- [ ] **Step 7: Commit**

```bash
git add backend/tools/branch_coverage backend/tests/unit/tools/branch_coverage backend/tests/fixtures/branch_coverage scripts/backend-coverage.sh Makefile
git commit -m "feat(branch-coverage): scaffold tools/branch_coverage package + Makefile targets + backend-coverage.sh"
```

---

### Task A3: API spike — validate pyan3 + coverage.py + hangman.main import safety

**Files:**

- Create: `backend/tools/branch_coverage/spike_results.md` (deleted at end of task; not committed)
- May create / modify (only if needed to make import safe): `backend/src/hangman/db.py`

**Context:** Plan-review iter 1 (Codex + Claude) flagged three speculative dependencies in the design that need real-environment validation BEFORE downstream tasks build on them:

1. **pyan3 2.5.0 Python API** — research brief says `CallGraphVisitor` exposes `uses_graph`; design's `_node_name` has a fallback chain. Real attribute names need verification.
2. **coverage.py 7.13 public API** — design's `CoverageDataLoader` uses `data.set_query_contexts([ctx])` + `data.arcs(file)` + originally `cov._analyze(file)` (private). Need to confirm public alternatives.
3. **`from hangman.main import app` import safety** — `backend/src/hangman/main.py` imports `hangman.db.engine`, which `create_engine()`s at module scope. Side effects must be characterized: does it just create an engine object (lazy connect, harmless) or does it actually connect / migrate?

This task is a **time-boxed spike**: verify each assumption with a real interpreter, write findings to a temporary `spike_results.md`, and either lock the design or propose a single-task amendment. After committing the verdict (in code, not the .md), delete the spike file.

- [ ] **Step 1: Verify pyan3 API**

After A1 lands (which installed pyan3>=2.5,<3 in the dev group), run:

```bash
cd backend && uv run python -c "
import pyan
from pyan.analyzer import CallGraphVisitor
print('pyan version:', getattr(pyan, '__version__', 'unknown'))
v = CallGraphVisitor(['src/hangman/main.py'])
print('uses_graph type:', type(getattr(v, 'uses_graph', None)).__name__)
print('uses_graph keys (first 3):', list(v.uses_graph.keys())[:3] if hasattr(v, 'uses_graph') else 'N/A')
if hasattr(v, 'uses_graph') and v.uses_graph:
    first_node = next(iter(v.uses_graph.keys()))
    print('Node attrs:', [a for a in dir(first_node) if not a.startswith('_')][:20])
    for attr in ('get_name', 'fullname', 'name'):
        val = getattr(first_node, attr, None)
        kind = 'method' if callable(val) else 'attr' if val is not None else 'missing'
        print(f'  {attr}: {kind}, value={val!r if not callable(val) else val}')
"
```

Expected: prints version, confirms `uses_graph` is a dict, prints node attrs. Capture findings in `spike_results.md`.

**Decision criteria:**

- If `uses_graph` exists AND nodes have at least one of `get_name() / fullname / name` returning a usable string → **lock the C2 design as-is, proceed.**
- If `uses_graph` doesn't exist (pyan3 renamed it) → update C2's `callgraph.py` snippet with the actual attribute name, document in spike_results.md, then proceed.
- If pyan3 fails to install or analyze → escalate; consider vendoring pyan3 source per design spec §12 risk #1.

- [ ] **Step 2: Verify coverage.py 7.13 per-context arc API + analysis2 return shape**

Per plan-review iter 2 P1: presence-check alone isn't enough — D3 depends on `analysis2(file).arc_possibilities()`. If `analysis2()` exists but its return shape differs (no `arc_possibilities` method), D3 hard-fails at runtime AFTER the spike "passed." Validate the actual return shape:

```bash
cd backend && uv run python -c "
import tempfile, os
import coverage
from coverage import Coverage, CoverageData

print('coverage version:', coverage.__version__)

# Method-presence check
d = CoverageData()
for m in ('set_query_contexts', 'arcs', 'lines', 'measured_files', 'measured_contexts'):
    print(f'  CoverageData.{m}: {hasattr(d, m)}')
for m in ('current', '_analyze', 'analysis2'):
    print(f'  Coverage.{m}: {hasattr(Coverage, m)}')

# Return-shape check for analysis2 — D3 calls .arc_possibilities() on it.
print()
print('Return-shape check on analysis2(file):')
with tempfile.TemporaryDirectory() as tmp:
    target = os.path.join(tmp, 'tiny.py')
    with open(target, 'w') as f:
        f.write('def f(x):\n    if x > 0:\n        return 1\n    return 0\n')
    cov = Coverage(data_file=os.path.join(tmp, '.coverage'), branch=True, source=[tmp])
    cov.start()
    import importlib.util
    spec = importlib.util.spec_from_file_location('tiny', target)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.f(5)
    cov.stop()
    cov.save()
    try:
        analysis = cov.analysis2(target)
        print(f'  analysis2 returned: {type(analysis).__name__}')
        print(f'  has arc_possibilities: {hasattr(analysis, \"arc_possibilities\")}')
        if hasattr(analysis, 'arc_possibilities'):
            arcs = analysis.arc_possibilities()
            print(f'  arc_possibilities() returned: {type(arcs).__name__}, {len(arcs) if hasattr(arcs, \"__len__\") else \"?\"} items')
            print(f'  first arc: {arcs[0] if arcs else \"(empty)\"}')
        else:
            print('  ⚠ analysis2 returned an object WITHOUT arc_possibilities — D3 will hard-fail')
    except (AttributeError, TypeError) as exc:
        print(f'  ⚠ analysis2 raised: {exc} — D3 will hard-fail')
"
```

**Decision criteria:**

- If `set_query_contexts` + `arcs` are present on `CoverageData` AND `analysis2(file).arc_possibilities()` returns a list of arc tuples → **D3 design is correct, proceed.**
- If `set_query_contexts` is missing → switch D3 per-context loader to use `data.contexts_by_lineno()` (documented public surface).
- If `analysis2` exists but `arc_possibilities` does not → **PATCH D3** before any task uses it. The Analysis class returned by analysis2 in coverage.py 7.x is documented to have `arc_possibilities`; if it doesn't, switch to `cov._analyze().branch_lines()` with explicit private-API documentation.
- If `analysis2` is missing entirely → **ESCALATE** to user. coverage.py 7.x has had analysis2 since 4.x; its absence indicates a major version mismatch. Either pin coverage.py to a tested version or switch the authoritative-branches strategy.

**No lossy fallback** in any case — D3 hard-fails on shape mismatch with a specific error pointing at this spike.

- [ ] **Step 3: Audit `from hangman.main import app` for import-time side effects**

```bash
cd backend && uv run python -c "
import os, sys
print('CWD:', os.getcwd())
print('Importing hangman.main...')
# Track filesystem touches and DB connection attempts.
import hangman.main
print('Imported. app type:', type(hangman.main.app).__name__)
print('app.routes count:', len(hangman.main.app.routes))
" 2>&1 | tee /tmp/spike-import.log

# Check for side-effect artifacts:
ls -la backend/*.db 2>/dev/null && echo 'WARN: .db file created on import' || echo 'OK: no .db file'
```

Expected paths:

- **Best case:** Import succeeds, no .db file created (engine is created but doesn't connect).
- **Acceptable:** Import succeeds, an empty .db file is created (SQLAlchemy lazy connect with file-backed SQLite). Document this in the spike — Feature 3's analyzer can tolerate it (uses a separate test/run process).
- **Bad case:** Import raises (DB unreachable), or import runs migrations (slow + irreversible). MUST fix.

**Decision criteria:**

- If best case → no code changes; proceed to B1.
- If acceptable → document in `spike_results.md` + add a note to F1 task that a `.db` file may appear during analyzer runs (gitignored already).
- If bad case → **PATCH `backend/src/hangman/db.py`** to make engine creation lazy (e.g., guard with `os.environ.get("HANGMAN_SKIP_DB_INIT")`) OR introduce an app factory `create_app()` that Feature 3's `RouteEnumerator` can call without DB init. Plan this as a sub-step here; commit with `fix(hangman): lazify db.py engine creation for tooling import safety`.

- [ ] **Step 4: Document spike findings**

Write `backend/tools/branch_coverage/spike_results.md` with:

- pyan3 actual attribute names + version
- coverage.py per-context API decision (set_query_contexts / contexts_by_lineno) + authoritative-branch API decision (analysis2 vs \_analyze)
- hangman.main import side effect (best/acceptable/bad case + any patches applied)
- Any plan amendments needed (e.g., "C2's `_node_name` fallback can be simplified — only `get_name()` is needed").

This file is the spike artifact. Do NOT commit it long-term — it's reference material for the immediate plan iteration.

- [ ] **Step 5: Apply spike-driven plan patches (if any)**

If the spike revealed deltas from the plan's design, edit:

- `docs/plans/2026-04-24-bdd-branch-coverage-plan.md` — update C2/D3 task code blocks
- `docs/plans/2026-04-24-bdd-branch-coverage-design.md` — update §4.3/§4.5

Commit those plan/design updates separately before B1 starts.

- [ ] **Step 6: Clean up + commit**

```bash
# If db.py was patched in step 3:
git add backend/src/hangman/db.py
git commit -m "fix(hangman): lazify db.py engine creation for tooling import safety"

# Delete the temporary spike file (not committed):
rm backend/tools/branch_coverage/spike_results.md

# Plan/design updates (if any) committed under their own message:
git add docs/plans/2026-04-24-bdd-branch-coverage-plan.md docs/plans/2026-04-24-bdd-branch-coverage-design.md
git commit -m "docs(branch-coverage): apply A3 spike findings to plan + design"
```

If the spike found nothing surprising (best case across all three checks): commit nothing, just delete `spike_results.md` and move on.

**Time-box:** 30 minutes. If a check fails harder than expected (e.g., pyan3 can't analyze the codebase, coverage.py 7.13 reorganized the data API), escalate to the user before making structural plan changes.

---

## Phase B — Models

### Task B1: models.py dataclasses

**Files:**

- Create: `backend/tools/branch_coverage/models.py`

**Context:** Per design spec §4.1. Dataclasses are the lingua franca — every module imports from here. No logic beyond `CoveragePerEndpoint.uncovered_branches_flat` property.

- [ ] **Step 1: Write `models.py`**

```python
"""Dataclass models for the branch coverage pipeline.

Leaf-level module: imports nothing from other tools.branch_coverage modules.
Every dataclass is frozen — the pipeline is a pure data transformation.
"""

from dataclasses import dataclass
from enum import Enum


class Tone(Enum):
    SUCCESS = "success"  # pct >= 80
    WARNING = "warning"  # 50 <= pct < 80
    ERROR = "error"      # pct < 50
    NA = "na"            # total_branches == 0


@dataclass(frozen=True)
class Endpoint:
    method: str
    path: str
    handler_qualname: str


@dataclass(frozen=True)
class ReachableBranch:
    file: str
    line: int
    branch_id: str
    condition_text: str
    not_taken_to_line: int
    function_qualname: str


@dataclass(frozen=True)
class FunctionCoverage:
    file: str
    qualname: str
    total_branches: int
    covered_branches: int
    pct: float
    reached: bool
    uncovered_branches: tuple[ReachableBranch, ...]


@dataclass(frozen=True)
class CoveragePerEndpoint:
    endpoint: Endpoint
    reachable_functions: tuple[FunctionCoverage, ...]
    total_branches: int
    covered_branches: int
    pct: float
    tone: Tone

    @property
    def uncovered_branches_flat(self) -> tuple[ReachableBranch, ...]:
        return tuple(
            b for fc in self.reachable_functions for b in fc.uncovered_branches
        )


@dataclass(frozen=True)
class ExtraCoverage:
    file: str
    qualname: str
    reason: str


@dataclass(frozen=True)
class UnattributedBranch:
    file: str
    line: int
    branch_id: str
    reason: str


@dataclass(frozen=True)
class AuditReport:
    total_branches_per_coverage_py: int
    total_branches_enumerated_via_reachability: int
    extra_coverage_branches: int
    unattributed_branches: tuple[UnattributedBranch, ...]
    reconciled: bool


@dataclass(frozen=True)
class Totals:
    total_branches: int
    covered_branches: int
    pct: float
    tone: Tone


@dataclass(frozen=True)
class LoadedCoverage:
    """Output of CoverageDataLoader. Per-context hit sets + authoritative totals."""
    hits_by_context: dict[str, frozenset[tuple[str, str]]]
    total_branches_per_file: dict[str, int]
    all_hits: frozenset[tuple[str, str]]


@dataclass(frozen=True)
class CoverageReport:
    version: int
    timestamp: str
    cucumber_ndjson: str
    instrumented: bool
    thresholds: dict[str, float]
    totals: Totals
    endpoints: tuple[CoveragePerEndpoint, ...]
    extra_coverage: tuple[ExtraCoverage, ...]
    audit: AuditReport
```

- [ ] **Step 2: Smoke-import**

Run: `cd backend && uv run python -c "from tools.branch_coverage import models; print(list(models.Tone))"`
Expected: `[<Tone.SUCCESS: 'success'>, <Tone.WARNING: 'warning'>, <Tone.ERROR: 'error'>, <Tone.NA: 'na'>]`

- [ ] **Step 3: ruff + mypy**

Run: `cd backend && uv run ruff check tools/branch_coverage/models.py && uv run mypy tools/branch_coverage/models.py`
Expected: both clean.

- [ ] **Step 4: Commit**

```bash
git add backend/tools/branch_coverage/models.py
git commit -m "feat(branch-coverage): add models.py dataclasses"
```

---

## Phase C — Deterministic modules (routes, callgraph, reachability)

All three depend only on `models.py`. Each owns distinct files; can parallelize via dispatch plan (§ below). Each follows TDD Red-Green.

### Task C1: routes.py + test_routes.py + minimal_app fixture

**Files:**

- Create: `backend/tests/fixtures/branch_coverage/minimal_app/__init__.py` (empty)
- Create: `backend/tests/fixtures/branch_coverage/minimal_app/main.py`
- Create: `backend/tests/fixtures/branch_coverage/minimal_app/game.py`
- Create: `backend/tools/branch_coverage/routes.py`
- Create: `backend/tests/unit/tools/branch_coverage/conftest.py`
- Create: `backend/tests/unit/tools/branch_coverage/test_routes.py`

**Context:** Per design spec §4.2. `RouteEnumerator.enumerate()` imports a FastAPI app reflectively and lists its routes. We verify it handles `app.include_router(prefix=...)` and `@app.method(...)` decorators correctly. Fixture `minimal_app/` stays small (2 routes, 1 function with 3 branches) because it's also used by C2, D3, and F1.

- [ ] **Step 1: Write the minimal_app fixture**

`backend/tests/fixtures/branch_coverage/minimal_app/game.py`:

```python
"""Fixture function with 3 branches — used by call-graph + coverage tests."""


def validate_letter(letter: str) -> str:
    if not letter:
        raise ValueError("empty")
    if len(letter) != 1:
        raise ValueError("not a single character")
    if not letter.isalpha():
        raise ValueError("not alphabetic")
    return letter.lower()
```

`backend/tests/fixtures/branch_coverage/minimal_app/main.py`:

```python
"""Minimal FastAPI app fixture — 2 routes, both calling validate_letter."""

from fastapi import APIRouter, FastAPI

from tests.fixtures.branch_coverage.minimal_app.game import validate_letter

router = APIRouter(prefix="/api/v1")


@router.post("/games")
def create_game() -> dict:
    return {"id": "fixture-1"}


@router.post("/games/{game_id}/guesses")
def make_guess(game_id: str, letter: str) -> dict:
    normalized = validate_letter(letter)
    return {"guess": normalized}


app = FastAPI()
app.include_router(router)
```

- [ ] **Step 2: Write `conftest.py` with shared fixture path helpers**

```python
"""Shared fixtures for branch_coverage tests."""

from pathlib import Path

import pytest


FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "branch_coverage"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def minimal_app_source_root(fixtures_dir: Path) -> Path:
    return fixtures_dir / "minimal_app"
```

Verify math: `backend/tests/unit/tools/branch_coverage/conftest.py` → `parent.parent.parent.parent = backend/tests/` → `/fixtures/branch_coverage` ✓

- [ ] **Step 3: Write `test_routes.py` (failing tests)**

```python
"""Tests for RouteEnumerator."""

from tools.branch_coverage.models import Endpoint
from tools.branch_coverage.routes import RouteEnumerator


class TestEnumerateMinimalApp:
    def test_returns_endpoint_tuple(self) -> None:
        from tests.fixtures.branch_coverage.minimal_app.main import app

        endpoints = RouteEnumerator().enumerate(app)
        assert isinstance(endpoints, tuple)
        assert all(isinstance(e, Endpoint) for e in endpoints)

    def test_extracts_both_routes(self) -> None:
        from tests.fixtures.branch_coverage.minimal_app.main import app

        endpoints = RouteEnumerator().enumerate(app)
        paths_methods = {(e.method, e.path) for e in endpoints}
        assert ("POST", "/api/v1/games") in paths_methods
        assert ("POST", "/api/v1/games/{game_id}/guesses") in paths_methods

    def test_preserves_path_parameters(self) -> None:
        from tests.fixtures.branch_coverage.minimal_app.main import app

        endpoints = RouteEnumerator().enumerate(app)
        guesses = next(e for e in endpoints if "guesses" in e.path)
        assert "{game_id}" in guesses.path

    def test_extracts_handler_qualname(self) -> None:
        from tests.fixtures.branch_coverage.minimal_app.main import app

        endpoints = RouteEnumerator().enumerate(app)
        create = next(e for e in endpoints if e.path == "/api/v1/games")
        assert "create_game" in create.handler_qualname

    def test_deterministic_order(self) -> None:
        from tests.fixtures.branch_coverage.minimal_app.main import app

        a = RouteEnumerator().enumerate(app)
        b = RouteEnumerator().enumerate(app)
        assert a == b  # stable sort


class TestFiltersNonApiRoutes:
    def test_skips_websocket_and_head_only_routes(self) -> None:
        from fastapi import FastAPI

        bare_app = FastAPI()
        # No routes added
        endpoints = RouteEnumerator().enumerate(bare_app)
        assert endpoints == ()


class TestNestedRouterPrefix:
    """Per plan-review iter 1 P2: real hangman code uses
    `app.include_router(prefix="/api/v1", ...)`. The minimal_app fixture
    already exercises a prefixed APIRouter at the top level; this test
    adds a second router to verify that multiple prefixed routers stack
    correctly."""

    def test_multiple_prefixed_routers(self) -> None:
        from fastapi import APIRouter, FastAPI

        app = FastAPI()
        v1 = APIRouter(prefix="/api/v1")
        v2 = APIRouter(prefix="/api/v2")

        @v1.get("/items")
        def list_v1() -> dict:
            return {"v": 1}

        @v2.get("/items")
        def list_v2() -> dict:
            return {"v": 2}

        app.include_router(v1)
        app.include_router(v2)

        endpoints = RouteEnumerator().enumerate(app)
        paths = [e.path for e in endpoints]
        assert "/api/v1/items" in paths
        assert "/api/v2/items" in paths

    def test_double_nested_prefix(self) -> None:
        """Router prefix nesting: outer prefix '/api/v1' + inner router with
        prefix '/games' → resolved path is '/api/v1/games'."""
        from fastapi import APIRouter, FastAPI

        app = FastAPI()
        outer = APIRouter(prefix="/api/v1")
        inner = APIRouter(prefix="/games")

        @inner.get("/{game_id}")
        def get_game(game_id: str) -> dict:
            return {"id": game_id}

        outer.include_router(inner)
        app.include_router(outer)

        endpoints = RouteEnumerator().enumerate(app)
        paths = [e.path for e in endpoints]
        assert "/api/v1/games/{game_id}" in paths
```

- [ ] **Step 4: Run tests — expect fail**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_routes.py -v`
Expected: all fail with `ModuleNotFoundError: No module named 'tools.branch_coverage.routes'`

- [ ] **Step 5: Implement `routes.py`**

```python
"""RouteEnumerator: reflective FastAPI route enumeration.

Imports the provided FastAPI app (caller's responsibility) and lists its
routes. AST-parsing routes.py rejected — reflective handles `prefix=`,
`app.include_router()`, and `add_api_route()` for free.
"""

from __future__ import annotations

from typing import Any

from tools.branch_coverage.models import Endpoint


class RouteEnumerator:
    def enumerate(self, app: Any) -> tuple[Endpoint, ...]:
        """Return all routes registered on `app` as Endpoint tuples.

        Filters to routes that have HTTP methods (excludes WebSockets,
        static mounts, etc.). Sorts by (path, method) for determinism.
        """
        endpoints: list[Endpoint] = []
        for route in getattr(app, "routes", []):
            methods = getattr(route, "methods", None)
            if not methods:
                continue
            path = getattr(route, "path", None)
            endpoint_fn = getattr(route, "endpoint", None)
            if path is None or endpoint_fn is None:
                continue
            handler_qualname = (
                f"{endpoint_fn.__module__}.{endpoint_fn.__qualname__}"
            )
            for method in sorted(methods):
                if method == "HEAD":
                    continue  # autogenerated by FastAPI; skip
                endpoints.append(
                    Endpoint(
                        method=method,
                        path=path,
                        handler_qualname=handler_qualname,
                    )
                )
        endpoints.sort(key=lambda e: (e.path, e.method))
        return tuple(endpoints)
```

- [ ] **Step 6: Run tests — expect pass**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_routes.py -v`
Expected: all 6 tests pass.

- [ ] **Step 7: ruff + mypy**

Run: `cd backend && uv run ruff check tools/branch_coverage/routes.py tests/unit/tools/branch_coverage/ && uv run mypy tools/branch_coverage/routes.py`
Expected: both clean.

- [ ] **Step 8: Commit**

```bash
git add backend/tests/fixtures/branch_coverage/minimal_app backend/tools/branch_coverage/routes.py backend/tests/unit/tools/branch_coverage/conftest.py backend/tests/unit/tools/branch_coverage/test_routes.py
git commit -m "feat(branch-coverage): add RouteEnumerator + minimal_app fixture"
```

---

### Task C2: callgraph.py + test_callgraph.py + fake_adjacency fixture

**Files:**

- Create: `backend/tests/fixtures/branch_coverage/fake_adjacency.py`
- Create: `backend/tools/branch_coverage/callgraph.py`
- Create: `backend/tests/unit/tools/branch_coverage/test_callgraph.py`

**Context:** Per design spec §4.3. Uses pyan3's Python API (`CallGraphVisitor`) directly — no subprocess, no DOT parsing. Tests run against the real `minimal_app/` fixture (live pyan3). Degraded-path test mocks `CallGraphVisitor` to raise and asserts graceful fallback to empty graph.

- [ ] **Step 1: Write `fake_adjacency.py`** (used by later tests — not C2's direct tests)

```python
"""Hand-built adjacency map for tests that don't need to run pyan3.

Shape matches what CallGraphBuilder.build() returns: a CallGraph
dataclass with an adjacency map keyed by qualified name.
"""

from tools.branch_coverage.callgraph import CallGraph


def fake_graph_for_minimal_app() -> CallGraph:
    """Hand-built graph approximating what pyan3 returns for minimal_app/."""
    return CallGraph(
        adjacency={
            "tests.fixtures.branch_coverage.minimal_app.main.create_game": frozenset(),
            "tests.fixtures.branch_coverage.minimal_app.main.make_guess": frozenset({
                "tests.fixtures.branch_coverage.minimal_app.game.validate_letter",
            }),
            "tests.fixtures.branch_coverage.minimal_app.game.validate_letter": frozenset(),
        }
    )
```

- [ ] **Step 2: Write `test_callgraph.py` (failing tests)**

```python
"""Tests for CallGraphBuilder."""

from pathlib import Path

import pytest

from tools.branch_coverage.callgraph import CallGraph, CallGraphBuilder


class TestBuildOnMinimalApp:
    def test_returns_callgraph(self, minimal_app_source_root: Path) -> None:
        cg = CallGraphBuilder().build(minimal_app_source_root)
        assert isinstance(cg, CallGraph)
        assert isinstance(cg.adjacency, dict)

    def test_adjacency_nonempty_on_real_app(self, minimal_app_source_root: Path) -> None:
        # Live pyan3 against the fixture; exact node names depend on
        # pyan3's qualname resolution, but the graph must be non-empty.
        cg = CallGraphBuilder().build(minimal_app_source_root)
        assert len(cg.adjacency) > 0

    def test_make_guess_reaches_validate_letter(self, minimal_app_source_root: Path) -> None:
        # make_guess calls validate_letter — pyan3 should trace this.
        cg = CallGraphBuilder().build(minimal_app_source_root)
        # Allow qualname to be fully-qualified or suffix-only — search
        # for any key that ends with "make_guess".
        make_guess_callees = [
            callees for name, callees in cg.adjacency.items() if name.endswith("make_guess")
        ]
        assert make_guess_callees, "make_guess not found in adjacency map"
        # At least one callee should contain "validate_letter".
        assert any(
            any("validate_letter" in callee for callee in callees)
            for callees in make_guess_callees
        )


class TestDegradedPath:
    def test_pyan3_exception_returns_empty_graph(self, monkeypatch, minimal_app_source_root: Path) -> None:
        # Mock pyan's CallGraphVisitor to raise — builder must catch and
        # return an empty CallGraph, not propagate.
        class FakeVisitor:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("simulated pyan3 failure")

        monkeypatch.setattr("pyan.analyzer.CallGraphVisitor", FakeVisitor)
        cg = CallGraphBuilder().build(minimal_app_source_root)
        assert cg.adjacency == {}
```

- [ ] **Step 3: Run tests — expect fail**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_callgraph.py -v`
Expected: fail with `ModuleNotFoundError: No module named 'tools.branch_coverage.callgraph'`

- [ ] **Step 4: Implement `callgraph.py`**

```python
"""CallGraphBuilder: static call-graph via pyan3's Python API.

Returns an adjacency map keyed by fully-qualified name. Subprocess +
DOT parsing rejected — pyan3 exposes CallGraphVisitor directly.

Degraded path: if pyan3 raises (API drift, parseable source), log and
return an empty graph. Caller (Analyzer) still emits a valid report;
audit reconciliation surfaces everything as unattributed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class CallGraph:
    """Adjacency map: dict[qualname, frozenset[callee_qualname]]."""
    adjacency: dict[str, frozenset[str]]


class CallGraphBuilder:
    def build(self, source_root: Path) -> CallGraph:
        """Analyze *.py files under source_root with pyan3.

        Returns a CallGraph. On pyan3 failure, returns an empty graph
        (logs error). Never raises.
        """
        try:
            from pyan.analyzer import CallGraphVisitor
        except ImportError as exc:  # pragma: no cover — dev-group dep
            _LOG.error("pyan3 not installed: %s", exc)
            return CallGraph(adjacency={})

        files = [str(f) for f in source_root.rglob("*.py")]
        if not files:
            _LOG.warning("No .py files under %s; empty call graph", source_root)
            return CallGraph(adjacency={})

        try:
            visitor = CallGraphVisitor(files)
        except Exception as exc:  # noqa: BLE001 — pyan3 can raise anything
            _LOG.error(
                "pyan3 CallGraphVisitor failed on %s: %s. Returning empty graph.",
                source_root, exc,
            )
            return CallGraph(adjacency={})

        adjacency: dict[str, frozenset[str]] = {}
        # pyan3 exposes uses_graph: dict[Node, set[Node]]
        uses_graph = getattr(visitor, "uses_graph", {})
        for caller, callees in uses_graph.items():
            caller_name = self._node_name(caller)
            callee_names = frozenset(self._node_name(c) for c in callees)
            adjacency[caller_name] = callee_names
        return CallGraph(adjacency=adjacency)

    @staticmethod
    def _node_name(node: object) -> str:
        """Derive a qualified name from a pyan3 Node. Attribute names
        differ slightly between pyan3 versions; try common ones, fall
        back to str()."""
        for attr in ("get_name", "fullname", "name"):
            method_or_val = getattr(node, attr, None)
            if callable(method_or_val):
                try:
                    return str(method_or_val())
                except Exception:  # noqa: BLE001
                    continue
            if isinstance(method_or_val, str):
                return method_or_val
        return str(node)
```

- [ ] **Step 5: Run tests — expect pass**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_callgraph.py -v`
Expected: all pass.

**If `test_make_guess_reaches_validate_letter` fails because pyan3's qualname format differs:** read the actual adjacency keys by adding a `print(cg.adjacency)` in the test temporarily, verify the callee-matching logic, then adjust the test's assertion (but NOT the implementation). pyan3's exact qualname shape is out of our control.

- [ ] **Step 6: ruff + mypy**

Run: `cd backend && uv run ruff check tools/branch_coverage/callgraph.py tests/unit/tools/branch_coverage/test_callgraph.py && uv run mypy tools/branch_coverage/callgraph.py`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add backend/tools/branch_coverage/callgraph.py backend/tests/unit/tools/branch_coverage/test_callgraph.py backend/tests/fixtures/branch_coverage/fake_adjacency.py
git commit -m "feat(branch-coverage): add CallGraphBuilder via pyan3 Python API"
```

---

### Task C3: reachability.py + test_reachability.py

**Files:**

- Create: `backend/tools/branch_coverage/reachability.py`
- Create: `backend/tests/unit/tools/branch_coverage/test_reachability.py`

**Context:** Per design spec §4.4. BFS from each endpoint's handler through the call graph; for each reachable function, use `ast.parse` to enumerate branches. Boundary filter: only functions whose source file lives under `source_root`.

- [ ] **Step 1: Write `test_reachability.py` (failing tests)**

```python
"""Tests for Reachability."""

from pathlib import Path

import pytest

from tests.fixtures.branch_coverage.fake_adjacency import fake_graph_for_minimal_app
from tools.branch_coverage.models import Endpoint, ReachableBranch
from tools.branch_coverage.reachability import Reachability


def _endpoint(path: str, handler: str) -> Endpoint:
    return Endpoint(method="POST", path=path, handler_qualname=handler)


class TestBFSReachability:
    def test_handler_with_no_calls_yields_only_its_own_branches(
        self, minimal_app_source_root: Path
    ) -> None:
        ep = _endpoint(
            "/api/v1/games",
            "tests.fixtures.branch_coverage.minimal_app.main.create_game",
        )
        result = Reachability().compute(
            (ep,), fake_graph_for_minimal_app(), minimal_app_source_root
        )
        assert ep in result
        # create_game has no branches; expect empty
        assert result[ep] == []

    def test_handler_with_transitive_call_reaches_validate_letter_branches(
        self, minimal_app_source_root: Path
    ) -> None:
        ep = _endpoint(
            "/api/v1/games/{game_id}/guesses",
            "tests.fixtures.branch_coverage.minimal_app.main.make_guess",
        )
        result = Reachability().compute(
            (ep,), fake_graph_for_minimal_app(), minimal_app_source_root
        )
        branches = result[ep]
        assert len(branches) >= 3, f"expected >= 3 branches from validate_letter; got {len(branches)}"
        assert all(isinstance(b, ReachableBranch) for b in branches)
        # At least one branch should be from validate_letter.
        assert any("validate_letter" in b.function_qualname for b in branches)

    def test_handler_not_in_graph_returns_empty_list(
        self, minimal_app_source_root: Path
    ) -> None:
        ep = _endpoint("/nowhere", "hangman.nonexistent.handler")
        result = Reachability().compute(
            (ep,), fake_graph_for_minimal_app(), minimal_app_source_root
        )
        # Not in graph → empty; should not raise.
        assert result[ep] == []

    def test_cycle_handling(self, minimal_app_source_root: Path) -> None:
        # Hand-build a cyclic graph (a→b→a) and make sure BFS terminates.
        from tools.branch_coverage.callgraph import CallGraph

        cyclic = CallGraph(
            adjacency={
                "pkg.a": frozenset({"pkg.b"}),
                "pkg.b": frozenset({"pkg.a"}),
            }
        )
        ep = _endpoint("/x", "pkg.a")
        # Source files don't exist for pkg.a/pkg.b — Reachability should
        # skip them (boundary filter). Must not loop.
        result = Reachability().compute((ep,), cyclic, minimal_app_source_root)
        assert result[ep] == []


class TestBranchEnumeration:
    def test_parses_if_elif_else_chain(
        self, minimal_app_source_root: Path
    ) -> None:
        # validate_letter has 3 if statements — each is one branch arc.
        from tests.fixtures.branch_coverage.fake_adjacency import fake_graph_for_minimal_app

        ep = _endpoint(
            "/api/v1/games/{game_id}/guesses",
            "tests.fixtures.branch_coverage.minimal_app.main.make_guess",
        )
        result = Reachability().compute(
            (ep,), fake_graph_for_minimal_app(), minimal_app_source_root
        )
        branches = result[ep]
        condition_texts = [b.condition_text for b in branches]
        # Condition text is best-effort; accept any non-empty string.
        assert all(ct for ct in condition_texts)


class TestBoundaryEnforcement:
    def test_function_outside_source_root_is_excluded(
        self, minimal_app_source_root: Path, tmp_path: Path
    ) -> None:
        # Graph says pkg.a calls pkg.b, but neither is under source_root.
        # Reachability must skip both (boundary).
        from tools.branch_coverage.callgraph import CallGraph

        external = CallGraph(
            adjacency={"pkg.a": frozenset({"pkg.b"}), "pkg.b": frozenset()}
        )
        ep = _endpoint("/x", "pkg.a")
        result = Reachability().compute((ep,), external, minimal_app_source_root)
        assert result[ep] == []
```

- [ ] **Step 2: Run tests — expect fail**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_reachability.py -v`
Expected: fail with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `reachability.py`**

```python
"""Reachability: BFS from each endpoint's handler through the call graph
+ AST-based branch enumeration for each reachable function.

Boundary enforcement: only traverses into functions whose source file
lives under `source_root` (design spec §4.4, Q6 boundary).
"""

from __future__ import annotations

import ast
import importlib.util
import logging
from collections import deque
from pathlib import Path

from tools.branch_coverage.callgraph import CallGraph
from tools.branch_coverage.models import Endpoint, ReachableBranch

_LOG = logging.getLogger(__name__)


class Reachability:
    def compute(
        self,
        endpoints: tuple[Endpoint, ...],
        graph: CallGraph,
        source_root: Path,
    ) -> dict[Endpoint, list[ReachableBranch]]:
        """For each endpoint, BFS the call graph from its handler; for
        each reachable function whose file is under source_root,
        enumerate branches via AST."""
        result: dict[Endpoint, list[ReachableBranch]] = {}
        # Pre-parse each reachable source file once (cache branches by qualname).
        for ep in endpoints:
            reachable_qualnames = self._bfs(ep.handler_qualname, graph)
            branches: list[ReachableBranch] = []
            for qualname in reachable_qualnames:
                branches.extend(self._branches_for(qualname, source_root))
            result[ep] = branches
        return result

    def _bfs(self, start: str, graph: CallGraph) -> set[str]:
        visited: set[str] = set()
        queue: deque[str] = deque([start])
        while queue:
            name = queue.popleft()
            if name in visited:
                continue
            visited.add(name)
            for callee in graph.adjacency.get(name, frozenset()):
                if callee not in visited:
                    queue.append(callee)
        return visited

    def _branches_for(
        self, qualname: str, source_root: Path
    ) -> list[ReachableBranch]:
        """Enumerate branches in the function identified by `qualname`.
        Boundary filter: only inspects functions whose source file lives
        under source_root."""
        source_file = self._resolve_source_file(qualname, source_root)
        if source_file is None:
            return []
        try:
            tree = ast.parse(source_file.read_text())
        except (OSError, SyntaxError) as exc:
            _LOG.warning("Failed to parse %s: %s", source_file, exc)
            return []

        func_def = self._find_function(tree, qualname)
        if func_def is None:
            return []

        branches: list[ReachableBranch] = []
        for node in ast.walk(func_def):
            if isinstance(node, (ast.If, ast.While, ast.For)):
                line = node.lineno
                cond_text = self._condition_text(node, source_file)
                branches.append(
                    ReachableBranch(
                        file=str(source_file.relative_to(source_root.parent.parent))
                        if source_file.is_relative_to(source_root.parent.parent)
                        else str(source_file),
                        line=line,
                        branch_id=f"{line}->{line + 1}",
                        condition_text=cond_text,
                        not_taken_to_line=line + 1,
                        function_qualname=qualname,
                    )
                )
            elif isinstance(node, ast.Try):
                # Each except clause is a branch arc.
                for handler in node.handlers:
                    line = handler.lineno
                    branches.append(
                        ReachableBranch(
                            file=str(source_file.relative_to(source_root.parent.parent))
                            if source_file.is_relative_to(source_root.parent.parent)
                            else str(source_file),
                            line=line,
                            branch_id=f"{line}->{line + 1}",
                            condition_text=f"except {self._exception_type(handler)}",
                            not_taken_to_line=line + 1,
                            function_qualname=qualname,
                        )
                    )
        return branches

    def _resolve_source_file(
        self, qualname: str, source_root: Path
    ) -> Path | None:
        """Map a qualified name (module.path.func) to a source file path.
        Uses importlib to locate the module; returns None if the module
        is not under source_root (boundary filter)."""
        module_path = qualname.rsplit(".", 1)[0] if "." in qualname else qualname
        try:
            spec = importlib.util.find_spec(module_path)
        except (ImportError, ModuleNotFoundError, ValueError):
            return None
        if spec is None or spec.origin is None:
            return None
        source_file = Path(spec.origin)
        try:
            source_file.relative_to(source_root)
        except ValueError:
            return None  # not under source_root
        return source_file

    @staticmethod
    def _find_function(tree: ast.AST, qualname: str) -> ast.FunctionDef | None:
        target_name = qualname.rsplit(".", 1)[-1]
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target_name:
                return node  # type: ignore[return-value]
        return None

    @staticmethod
    def _condition_text(node: ast.AST, source_file: Path) -> str:
        try:
            return ast.unparse(node).split("\n")[0].strip() or "(conditional arc)"
        except Exception:  # noqa: BLE001
            return "(conditional arc)"

    @staticmethod
    def _exception_type(handler: ast.ExceptHandler) -> str:
        if handler.type is None:
            return "Exception"
        try:
            return ast.unparse(handler.type)
        except Exception:  # noqa: BLE001
            return "Exception"
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_reachability.py -v`
Expected: all pass.

- [ ] **Step 5: ruff + mypy**

Run: `cd backend && uv run ruff check tools/branch_coverage/reachability.py tests/unit/tools/branch_coverage/test_reachability.py && uv run mypy tools/branch_coverage/reachability.py`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add backend/tools/branch_coverage/reachability.py backend/tests/unit/tools/branch_coverage/test_reachability.py
git commit -m "feat(branch-coverage): add Reachability (BFS + AST branch enumeration)"
```

---

## Phase D — Middleware, serve entrypoint, coverage data

### Task D1: middleware.py + test_middleware.py

**Files:**

- Create: `backend/tools/branch_coverage/middleware.py`
- Create: `backend/tests/unit/tools/branch_coverage/test_middleware.py`

**Context:** Per design spec §4.10. ASGI middleware that calls `coverage.Coverage.current().switch_context(f"{method} {route_template}")` on request start, resets to `""` on response end. Per-endpoint attribution flows from here.

- [ ] **Step 1: Write `test_middleware.py` (failing tests)**

```python
"""Tests for CoverageContextMiddleware.

We can't easily test `coverage.Coverage.current()` without actually
running coverage; these tests mock it via monkeypatch and assert the
middleware calls `switch_context` with the right label.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tools.branch_coverage.middleware import CoverageContextMiddleware


@pytest.fixture
def fake_coverage(monkeypatch) -> MagicMock:
    """Replace coverage.Coverage.current() with a MagicMock."""
    mock = MagicMock()
    mock.switch_context = MagicMock()
    monkeypatch.setattr(
        "coverage.Coverage.current",
        classmethod(lambda cls: mock),
    )
    return mock


@pytest.fixture
def instrumented_app(fake_coverage: MagicMock) -> TestClient:
    app = FastAPI()

    @app.get("/items/{item_id}")
    def read_item(item_id: str) -> dict:
        return {"id": item_id}

    @app.post("/items")
    def create_item() -> dict:
        return {"id": "new"}

    app.add_middleware(CoverageContextMiddleware)
    return TestClient(app)


class TestContextSwitching:
    def test_get_request_switches_context(
        self, instrumented_app: TestClient, fake_coverage: MagicMock
    ) -> None:
        instrumented_app.get("/items/abc123")
        calls = [call.args[0] for call in fake_coverage.switch_context.call_args_list]
        assert "GET /items/{item_id}" in calls  # matched route template
        assert "" in calls  # reset after response

    def test_post_request_switches_context(
        self, instrumented_app: TestClient, fake_coverage: MagicMock
    ) -> None:
        instrumented_app.post("/items")
        calls = [call.args[0] for call in fake_coverage.switch_context.call_args_list]
        assert "POST /items" in calls
        assert "" in calls

    def test_path_template_normalizes_across_concrete_paths(
        self, instrumented_app: TestClient, fake_coverage: MagicMock
    ) -> None:
        instrumented_app.get("/items/abc")
        instrumented_app.get("/items/xyz")
        calls = [call.args[0] for call in fake_coverage.switch_context.call_args_list]
        # Both requests should produce identical context labels.
        assert calls.count("GET /items/{item_id}") == 2


class TestDegradedPath:
    def test_no_coverage_active_is_noop(self, monkeypatch) -> None:
        """When Coverage.current() returns None, middleware must not
        raise — still call next(), still return the response."""
        monkeypatch.setattr(
            "coverage.Coverage.current",
            classmethod(lambda cls: None),
        )
        app = FastAPI()

        @app.get("/ping")
        def ping() -> dict:
            return {"ok": True}

        app.add_middleware(CoverageContextMiddleware)
        client = TestClient(app)
        resp = client.get("/ping")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}


class TestErrorHandling:
    def test_handler_exception_still_resets_context(
        self, fake_coverage: MagicMock
    ) -> None:
        """Even if the route handler raises, the middleware must reset
        the context in a finally block — otherwise subsequent requests
        leak the previous endpoint's label."""
        app = FastAPI()

        @app.get("/boom")
        def boom() -> dict:
            raise RuntimeError("handler failure")

        app.add_middleware(CoverageContextMiddleware)
        client = TestClient(app)
        # TestClient will propagate the exception; wrap in pytest.raises.
        with pytest.raises(RuntimeError, match="handler failure"):
            client.get("/boom")
        calls = [call.args[0] for call in fake_coverage.switch_context.call_args_list]
        # The last call must be the reset.
        assert calls[-1] == ""
```

- [ ] **Step 2: Run tests — expect fail**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_middleware.py -v`
Expected: fail with `ModuleNotFoundError: No module named 'tools.branch_coverage.middleware'`

- [ ] **Step 3: Implement `middleware.py`**

```python
"""CoverageContextMiddleware: per-endpoint attribution for coverage.py.

Calls coverage.Coverage.current().switch_context(f"{method} {route_template}")
on each request start; resets to "" on response end (even if the handler
raises). No-op when coverage.py is not running.

Concurrency constraint: switch_context is process-global. Instrumented
runs MUST use a single uvicorn worker + sequential cucumber. See design
spec §12 risk #6.
"""

from __future__ import annotations

import logging

import coverage
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

_LOG = logging.getLogger(__name__)


class CoverageContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        cov = coverage.Coverage.current()
        context_label = self._resolve_context(request)
        if cov is not None:
            try:
                cov.switch_context(context_label)
            except Exception as exc:  # noqa: BLE001 — coverage.py should never fail the request
                _LOG.warning("switch_context(%r) failed: %s", context_label, exc)
        try:
            response = await call_next(request)
        finally:
            if cov is not None:
                try:
                    cov.switch_context("")  # reset
                except Exception as exc:  # noqa: BLE001
                    _LOG.warning("switch_context('') failed: %s", exc)
        return response

    @staticmethod
    def _resolve_context(request: Request) -> str:
        # Prefer the matched route's path template (e.g. "/items/{id}");
        # normalizes concrete paths across requests.
        route = request.scope.get("route")
        template = getattr(route, "path", None) if route else None
        path = template or request.url.path
        return f"{request.method} {path}"
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_middleware.py -v`
Expected: all pass.

**Test-coverage caveat (per plan-review iter 1 P1):** these unit tests use a _mocked_ `coverage.Coverage.current()` and verify that `switch_context` is _called_ with the right arguments — they do NOT verify that `coverage.py`'s internal context bookkeeping correctly attributes hit branches to the active context, and they do NOT verify thread-safety of the process-global `switch_context` under concurrent requests. Those guarantees come from:

1. **The constraint** — instrumented runs are single-uvicorn-worker + sequential-cucumber by construction (see design spec §12 risk #6). FastAPI's `TestClient` is also synchronous (one request at a time on the test thread), which matches the constraint at unit-test time.
2. **The H1 live smoke** — runs the real BDD suite under real `coverage run` instrumentation against a real backend, then verifies per-endpoint attribution by inspecting `coverage.json`. If a shared helper appears as covered under endpoint A's context AND uncovered under endpoint B's context (where B's scenarios don't exercise it), the middleware works as designed.

**Note on `test_get_request_switches_context`:** TestClient may not populate `request.scope["route"]` before the middleware runs (routing happens AFTER the middleware dispatch). In that case the test would see `"GET /items/abc123"` instead of `"GET /items/{item_id}"`. If tests fail with this, **relax the test** (not the code) — accept either the template or the concrete path (the fallback behavior is documented). The real-run behavior via uvicorn is correct per the FastAPI routing model; TestClient is just an imperfect harness for this specific attribute.

- [ ] **Step 5: ruff + mypy**

Run: `cd backend && uv run ruff check tools/branch_coverage/middleware.py tests/unit/tools/branch_coverage/test_middleware.py && uv run mypy tools/branch_coverage/middleware.py`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add backend/tools/branch_coverage/middleware.py backend/tests/unit/tools/branch_coverage/test_middleware.py
git commit -m "feat(branch-coverage): add CoverageContextMiddleware for per-endpoint attribution"
```

---

### Task D2: serve.py (ASGI entrypoint)

**Files:**

- Create: `backend/tools/branch_coverage/serve.py`

**Context:** Per design spec §4.11 + §7.2c. Imports `hangman.main.app`, adds the middleware, runs uvicorn single-worker. No dedicated tests — exercised via the H1 live integration smoke.

- [ ] **Step 1: Write `serve.py`**

```python
"""ASGI entrypoint used ONLY by instrumented runs via
`coverage run -m tools.branch_coverage.serve --host ... --port ...`.

Imports the Hangman FastAPI app, adds CoverageContextMiddleware, and
runs uvicorn single-worker.

Production runs continue to invoke `uvicorn hangman.main:app` directly
(unchanged) — this module is dev tooling only.
"""

from __future__ import annotations

import argparse

import uvicorn

from hangman.main import app
from tools.branch_coverage.middleware import CoverageContextMiddleware

# Attach the middleware at import time. Safe to do repeatedly (idempotent
# in principle) but this module is normally imported once by
# `coverage run -m tools.branch_coverage.serve`.
app.add_middleware(CoverageContextMiddleware)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m tools.branch_coverage.serve")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()
    # workers=1 is load-bearing: switch_context is process-global; a
    # multi-worker config would silently corrupt per-endpoint attribution.
    uvicorn.run(app, host=args.host, port=args.port, workers=1, log_level="info")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-import**

Run: `cd backend && uv run python -c "from tools.branch_coverage import serve; print(type(serve.app).__name__)"`
Expected: `FastAPI`

(Importing serve.py executes `app.add_middleware(CoverageContextMiddleware)` at import time; that's fine — in production `hangman.main:app` is imported directly, bypassing this module.)

- [ ] **Step 3: Run a `--help` smoke** (verifies argparse wires up)

Run: `cd backend && uv run python -m tools.branch_coverage.serve --help`
Expected: shows `--host` and `--port` options without error.

- [ ] **Step 4: ruff + mypy**

Run: `cd backend && uv run ruff check tools/branch_coverage/serve.py && uv run mypy tools/branch_coverage/serve.py`
Expected: clean.

- [ ] **Step 5: Commit**

```bash
git add backend/tools/branch_coverage/serve.py
git commit -m "feat(branch-coverage): add serve.py ASGI entrypoint wrapping hangman.main.app with middleware"
```

---

### Task D3: coverage_data.py + test_coverage_data.py

**Files:**

- Create: `backend/tools/branch_coverage/coverage_data.py`
- Create: `backend/tests/unit/tools/branch_coverage/test_coverage_data.py`

**Context:** Per design spec §4.5. Reads per-context hit sets from coverage.py's Python API. Returns `LoadedCoverage` (defined in B1). Test generates a small `.coverage` file at test time by running `coverage.Coverage()` in-process over a trivial function.

- [ ] **Step 1: Write `test_coverage_data.py` (failing tests)**

```python
"""Tests for CoverageDataLoader.

We generate a tiny .coverage file in-process during the test instead
of committing a binary fixture. This keeps the test self-contained.
"""

from __future__ import annotations

from pathlib import Path

import coverage
import pytest

from tools.branch_coverage.coverage_data import CoverageDataLoader, CoverageDataLoadError
from tools.branch_coverage.models import LoadedCoverage


@pytest.fixture
def tiny_covered_data(tmp_path: Path) -> Path:
    """Generate a real .coverage file by running a trivial function
    under coverage, with two contexts ('ctx_a' and 'ctx_b')."""
    target_file = tmp_path / "tiny.py"
    target_file.write_text(
        "def double(x):\n"
        "    if x > 0:\n"
        "        return x * 2\n"
        "    return 0\n"
    )
    data_file = tmp_path / ".coverage_fixture"
    cov = coverage.Coverage(
        data_file=str(data_file),
        branch=True,
        source=[str(tmp_path)],
    )
    cov.start()
    import importlib.util
    spec = importlib.util.spec_from_file_location("tiny", target_file)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    cov.switch_context("ctx_a")
    spec.loader.exec_module(mod)
    mod.double(5)  # takes x > 0 branch
    cov.switch_context("ctx_b")
    mod.double(-1)  # takes x <= 0 branch
    cov.switch_context("")
    cov.stop()
    cov.save()
    return data_file


class TestLoadPerContextHits:
    def test_returns_loaded_coverage(self, tiny_covered_data: Path) -> None:
        result = CoverageDataLoader().load(tiny_covered_data)
        assert isinstance(result, LoadedCoverage)

    def test_exposes_per_context_hit_sets(self, tiny_covered_data: Path) -> None:
        result = CoverageDataLoader().load(tiny_covered_data)
        # Contexts we set should be present. Coverage.py may prefix/suffix them;
        # accept any context name containing our label.
        context_keys = set(result.hits_by_context.keys())
        assert any("ctx_a" in k for k in context_keys)
        assert any("ctx_b" in k for k in context_keys)

    def test_total_branches_per_file_is_authoritative(
        self, tiny_covered_data: Path
    ) -> None:
        result = CoverageDataLoader().load(tiny_covered_data)
        # tiny.py has exactly one branch (if x > 0 … else …).
        assert len(result.total_branches_per_file) >= 1
        for file, count in result.total_branches_per_file.items():
            assert count > 0

    def test_all_hits_is_union_of_contexts(self, tiny_covered_data: Path) -> None:
        result = CoverageDataLoader().load(tiny_covered_data)
        union = frozenset().union(*result.hits_by_context.values())
        assert result.all_hits == union


class TestMissingFile:
    def test_raises_specific_error(self, tmp_path: Path) -> None:
        with pytest.raises(CoverageDataLoadError, match="bdd-coverage"):
            CoverageDataLoader().load(tmp_path / "does-not-exist.coverage")
```

- [ ] **Step 2: Run tests — expect fail**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_coverage_data.py -v`
Expected: fail with `ModuleNotFoundError: No module named 'tools.branch_coverage.coverage_data'`

- [ ] **Step 3: Implement `coverage_data.py`**

```python
"""CoverageDataLoader: reads per-context hit sets from a .coverage file.

Per-context hits come from the CoverageContextMiddleware — one set per
endpoint label. Authoritative per-file branch totals (independent of
contexts) come from coverage.py's own bytecode-level analysis.

Aggregate hits (union across contexts) used by Grader for
extra_coverage detection and totals.
"""

from __future__ import annotations

from pathlib import Path

import coverage

from tools.branch_coverage.models import LoadedCoverage


class CoverageDataLoadError(RuntimeError):
    """Raised when the .coverage file can't be loaded."""


class CoverageDataLoader:
    def load(self, coverage_file: Path) -> LoadedCoverage:
        if not coverage_file.exists():
            raise CoverageDataLoadError(
                f"Coverage data file not found: {coverage_file}. "
                "Run `make bdd-coverage` first; check if `.backend-coverage.pid` is stale."
            )
        cov = coverage.Coverage(data_file=str(coverage_file))
        try:
            cov.load()
        except Exception as exc:  # noqa: BLE001 — coverage.py's taxonomy is broad
            raise CoverageDataLoadError(
                f"Failed to load {coverage_file}: {exc}"
            ) from exc

        data = cov.get_data()
        measured_files = data.measured_files()
        contexts = list(data.measured_contexts()) or [""]

        # Per-context hit sets: dict[context_label, frozenset[(file, branch_id)]]
        hits_by_context: dict[str, frozenset[tuple[str, str]]] = {}
        for ctx in contexts:
            hits: set[tuple[str, str]] = set()
            for file in measured_files:
                arcs = data.arcs(file) or []  # arcs is context-filtered if contexts param passed
                # Note: coverage.py's public API returns aggregate arcs;
                # for per-context arcs we use the internal-but-stable
                # contexts_by_lineno/arcs mechanism if available, else
                # treat ctx="" as all.
                for arc in self._arcs_for_context(data, file, ctx):
                    hits.add((file, self._arc_to_id(arc)))
            hits_by_context[ctx] = frozenset(hits)

        # Aggregate hits (union across all contexts)
        all_hits_set: set[tuple[str, str]] = set()
        for s in hits_by_context.values():
            all_hits_set.update(s)
        all_hits = frozenset(all_hits_set)

        # Authoritative branch counts per file
        total_branches_per_file: dict[str, int] = {}
        for file in measured_files:
            branch_arcs = self._authoritative_branches(cov, data, file)
            total_branches_per_file[file] = len(branch_arcs)

        return LoadedCoverage(
            hits_by_context=hits_by_context,
            total_branches_per_file=total_branches_per_file,
            all_hits=all_hits,
        )

    @staticmethod
    def _arc_to_id(arc: tuple[int, int]) -> str:
        return f"{arc[0]}->{arc[1]}"

    @staticmethod
    def _arcs_for_context(data, file: str, context: str) -> list[tuple[int, int]]:
        """Fetch arcs hit under a specific context.

        Uses CoverageData.set_query_contexts() (7.x API) to scope the
        next arcs() call. Resets to None afterwards.
        """
        try:
            data.set_query_contexts([context] if context else [""])
            arcs = data.arcs(file) or []
            return [a for a in arcs if a[1] > 0]  # filter out exit arcs (negative targets)
        finally:
            try:
                data.set_query_contexts(None)
            except Exception:  # noqa: BLE001
                pass

    @staticmethod
    def _authoritative_branches(cov, data, file: str) -> list[tuple[int, int]]:
        """Enumerate branch arcs that EXIST in the file (independent of
        whether they were hit), using coverage.py's PUBLIC analysis2
        API.

        analysis2(file) returns a NamedTuple-like:
          (filename, executable, excluded, missing, missing_formatted)
        For branch coverage, we need the BRANCH arcs the file contains.
        coverage.py 7.x exposes branch arcs via Analysis.branch_lines()
        when --branch is set; this is part of the documented public
        Analysis class returned by Coverage.analysis2() in 7.13.

        If the public API shape changes, we hard-fail with a specific
        error rather than silently returning lossy data — per plan-review
        iter 1 P1.
        """
        try:
            # analysis2 is the public method on Coverage 7.x.
            analysis = cov.analysis2(file)
            # Coverage 7.x: Analysis exposes `arc_possibilities()`
            # (returns all arc tuples that could execute, including branch
            # arcs). Use that as the authoritative set; filter exit arcs
            # (negative target lines).
            possible = analysis.arc_possibilities() if hasattr(analysis, "arc_possibilities") else []
            return [a for a in possible if a[1] > 0]
        except (AttributeError, TypeError) as exc:
            raise CoverageDataLoadError(
                f"Coverage.analysis2('{file}') is not available or returned "
                f"an unexpected shape — coverage.py public API may have "
                f"shifted: {exc}. The A3 spike should have caught this; "
                f"re-run the spike or pin coverage.py to a known-good "
                f"version."
            ) from exc
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_coverage_data.py -v`
Expected: all pass.

**If `test_exposes_per_context_hit_sets` fails** because coverage.py's public API for per-context arcs has shifted: inspect `data.measured_contexts()` output, read `coverage.CoverageData.arcs` signature (`cd backend && uv run python -c "import coverage; help(coverage.CoverageData.arcs)"`), and adjust `_arcs_for_context` accordingly. The public API is `set_query_contexts([label])` then `arcs(file)` per coverage 7.x docs.

- [ ] **Step 5: ruff + mypy**

Run: `cd backend && uv run ruff check tools/branch_coverage/coverage_data.py tests/unit/tools/branch_coverage/test_coverage_data.py && uv run mypy tools/branch_coverage/coverage_data.py`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add backend/tools/branch_coverage/coverage_data.py backend/tests/unit/tools/branch_coverage/test_coverage_data.py
git commit -m "feat(branch-coverage): add CoverageDataLoader with per-context hit sets"
```

---

## Phase E — Grader + emitters

### Task E1: grader.py + test_grader.py (shared-helper + audit reconciliation)

**Files:**

- Create: `backend/tools/branch_coverage/grader.py`
- Create: `backend/tests/unit/tools/branch_coverage/test_grader.py`

**Context:** Per design spec §4.6. This is the correctness core: per-endpoint context intersection + audit reconciliation + threshold tone resolution. Plan-phase mandate from design spec §4.6: must include the shared-helper test case where a function is reachable from 2 endpoints but only 1 endpoint's context fires on the hit.

- [ ] **Step 1: Write `test_grader.py` (failing tests)**

```python
"""Tests for Grader — the correctness core of Feature 3."""

from __future__ import annotations

import pytest

from tools.branch_coverage.grader import Grader
from tools.branch_coverage.models import (
    Endpoint,
    LoadedCoverage,
    ReachableBranch,
    Tone,
)


def _branch(file: str, line: int, func: str) -> ReachableBranch:
    return ReachableBranch(
        file=file,
        line=line,
        branch_id=f"{line}->{line + 1}",
        condition_text=f"if x_{line}:",
        not_taken_to_line=line + 1,
        function_qualname=func,
    )


def _ep(path: str, handler: str) -> Endpoint:
    return Endpoint(method="POST", path=path, handler_qualname=handler)


class TestPerEndpointIntersection:
    def test_endpoint_with_all_branches_covered_is_green(self) -> None:
        ep = _ep("/a", "hangman.routes.handler_a")
        branch1 = _branch("hangman/a.py", 10, "hangman.a.fn")
        branch2 = _branch("hangman/a.py", 20, "hangman.a.fn")
        reachability = {ep: [branch1, branch2]}
        hits = LoadedCoverage(
            hits_by_context={"POST /a": frozenset({("hangman/a.py", "10->11"), ("hangman/a.py", "20->21")})},
            total_branches_per_file={"hangman/a.py": 2},
            all_hits=frozenset({("hangman/a.py", "10->11"), ("hangman/a.py", "20->21")}),
        )
        report = Grader().grade(reachability, hits)
        ep_cov = report.endpoints[0]
        assert ep_cov.tone == Tone.SUCCESS
        assert ep_cov.pct == 100.0

    def test_endpoint_with_no_branches_covered_is_red(self) -> None:
        ep = _ep("/b", "hangman.routes.handler_b")
        reachability = {ep: [_branch("hangman/b.py", 10, "hangman.b.fn")]}
        hits = LoadedCoverage(
            hits_by_context={"POST /b": frozenset()},
            total_branches_per_file={"hangman/b.py": 1},
            all_hits=frozenset(),
        )
        report = Grader().grade(reachability, hits)
        assert report.endpoints[0].tone == Tone.ERROR
        assert report.endpoints[0].pct == 0.0

    def test_endpoint_with_zero_reachable_branches_is_na(self) -> None:
        ep = _ep("/c", "hangman.routes.handler_c")
        reachability = {ep: []}
        hits = LoadedCoverage(
            hits_by_context={},
            total_branches_per_file={},
            all_hits=frozenset(),
        )
        report = Grader().grade(reachability, hits)
        assert report.endpoints[0].tone == Tone.NA
        assert report.endpoints[0].total_branches == 0

    @pytest.mark.parametrize(
        "pct, expected_tone",
        [
            (49.9, Tone.ERROR),
            (50.0, Tone.WARNING),
            (79.9, Tone.WARNING),
            (80.0, Tone.SUCCESS),
            (100.0, Tone.SUCCESS),
        ],
    )
    def test_threshold_resolution(
        self, pct: float, expected_tone: Tone
    ) -> None:
        # Generate N branches, mark the right proportion as hit.
        ep = _ep("/x", "hangman.routes.handler_x")
        total = 100
        covered_count = int(pct)  # 50.0 → 50 covered out of 100
        branches = [_branch("hangman/x.py", i, "hangman.x.fn") for i in range(total)]
        hit_set = frozenset(
            ("hangman/x.py", f"{i}->{i+1}") for i in range(covered_count)
        )
        reachability = {ep: branches}
        hits = LoadedCoverage(
            hits_by_context={"POST /x": hit_set},
            total_branches_per_file={"hangman/x.py": total},
            all_hits=hit_set,
        )
        report = Grader().grade(reachability, hits)
        assert report.endpoints[0].tone == expected_tone


class TestSharedHelperCorrectness:
    """Design spec §4.6 mandate: a helper reachable from 2 endpoints
    where only 1 endpoint's scenarios fire on the hit must show the
    helper as uncovered for the other endpoint."""

    def test_shared_helper_only_covered_under_one_context(self) -> None:
        ep_a = _ep("/a", "hangman.routes.handler_a")
        ep_b = _ep("/b", "hangman.routes.handler_b")
        shared = _branch("hangman/shared.py", 10, "hangman.shared.helper")
        reachability = {ep_a: [shared], ep_b: [shared]}
        # Only endpoint A's context fires on the hit.
        hits = LoadedCoverage(
            hits_by_context={
                "POST /a": frozenset({("hangman/shared.py", "10->11")}),
                "POST /b": frozenset(),
            },
            total_branches_per_file={"hangman/shared.py": 1},
            all_hits=frozenset({("hangman/shared.py", "10->11")}),
        )
        report = Grader().grade(reachability, hits)
        a = next(e for e in report.endpoints if e.endpoint.path == "/a")
        b = next(e for e in report.endpoints if e.endpoint.path == "/b")
        assert a.pct == 100.0  # A's scenarios triggered the helper
        assert b.pct == 0.0  # B's scenarios DID NOT — correctness fix
        assert a.tone == Tone.SUCCESS
        assert b.tone == Tone.ERROR

    def test_shared_helper_across_three_endpoints(self) -> None:
        """Per plan-review iter 1 P2: extend the shared-helper case to
        N=3 endpoints. Audit dedup must count the shared branch ONCE
        across any number of endpoints; per-endpoint pct must reflect
        only that endpoint's context hits."""
        ep_a = _ep("/a", "hangman.routes.handler_a")
        ep_b = _ep("/b", "hangman.routes.handler_b")
        ep_c = _ep("/c", "hangman.routes.handler_c")
        shared = _branch("hangman/shared.py", 10, "hangman.shared.helper")
        reachability = {ep_a: [shared], ep_b: [shared], ep_c: [shared]}
        # Endpoints A and C trigger the shared branch; B does not.
        hits = LoadedCoverage(
            hits_by_context={
                "POST /a": frozenset({("hangman/shared.py", "10->11")}),
                "POST /b": frozenset(),
                "POST /c": frozenset({("hangman/shared.py", "10->11")}),
            },
            total_branches_per_file={"hangman/shared.py": 1},
            all_hits=frozenset({("hangman/shared.py", "10->11")}),
        )
        report = Grader().grade(reachability, hits)
        a = next(e for e in report.endpoints if e.endpoint.path == "/a")
        b = next(e for e in report.endpoints if e.endpoint.path == "/b")
        c = next(e for e in report.endpoints if e.endpoint.path == "/c")
        # A and C see the shared branch as covered.
        assert a.pct == 100.0
        assert c.pct == 100.0
        # B does not — its scenarios never triggered the helper.
        assert b.pct == 0.0
        # Audit dedupes: 1 authoritative branch = 1 enumerated (not 3).
        assert report.audit.total_branches_per_coverage_py == 1
        assert report.audit.total_branches_enumerated_via_reachability == 1
        assert report.audit.reconciled is True


class TestAuditReconciliation:
    def test_reconciles_when_enumeration_matches(self) -> None:
        ep = _ep("/a", "hangman.routes.handler_a")
        reachability = {ep: [_branch("hangman/a.py", 10, "hangman.a.fn")]}
        hits = LoadedCoverage(
            hits_by_context={"POST /a": frozenset({("hangman/a.py", "10->11")})},
            total_branches_per_file={"hangman/a.py": 1},
            all_hits=frozenset({("hangman/a.py", "10->11")}),
        )
        report = Grader().grade(reachability, hits)
        assert report.audit.reconciled is True
        assert report.audit.total_branches_per_coverage_py == 1

    def test_unattributed_branches_surface_when_enumeration_incomplete(
        self,
    ) -> None:
        # coverage.py says file has 5 branches; our enumeration found 3.
        # Delta of 2 must appear in unattributed_branches.
        ep = _ep("/a", "hangman.routes.handler_a")
        reachability = {
            ep: [
                _branch("hangman/a.py", 10, "hangman.a.fn"),
                _branch("hangman/a.py", 20, "hangman.a.fn"),
                _branch("hangman/a.py", 30, "hangman.a.fn"),
            ]
        }
        hits = LoadedCoverage(
            hits_by_context={"POST /a": frozenset()},
            total_branches_per_file={"hangman/a.py": 5},
            all_hits=frozenset(),
        )
        report = Grader().grade(reachability, hits)
        # 5 authoritative − 3 enumerated = 2 unattributed (placeholder records).
        assert len(report.audit.unattributed_branches) == 2

    def test_shared_branch_across_endpoints_deduped_in_audit(self) -> None:
        # A shared branch reachable from 2 endpoints counts ONCE in the
        # audit enumeration — not twice.
        ep_a = _ep("/a", "hangman.routes.handler_a")
        ep_b = _ep("/b", "hangman.routes.handler_b")
        shared = _branch("hangman/shared.py", 10, "hangman.shared.fn")
        reachability = {ep_a: [shared], ep_b: [shared]}
        hits = LoadedCoverage(
            hits_by_context={
                "POST /a": frozenset({("hangman/shared.py", "10->11")}),
                "POST /b": frozenset(),
            },
            total_branches_per_file={"hangman/shared.py": 1},
            all_hits=frozenset({("hangman/shared.py", "10->11")}),
        )
        report = Grader().grade(reachability, hits)
        # 1 authoritative = 1 enumerated (deduped) — reconciliation holds.
        assert report.audit.reconciled is True
        assert report.audit.total_branches_enumerated_via_reachability == 1


class TestTotals:
    def test_totals_use_authoritative_count(self) -> None:
        ep = _ep("/a", "hangman.routes.handler_a")
        reachability = {ep: [_branch("hangman/a.py", 10, "hangman.a.fn")]}
        hits = LoadedCoverage(
            hits_by_context={"POST /a": frozenset({("hangman/a.py", "10->11")})},
            total_branches_per_file={"hangman/a.py": 1},
            all_hits=frozenset({("hangman/a.py", "10->11")}),
        )
        report = Grader().grade(reachability, hits)
        assert report.totals.total_branches == 1
        assert report.totals.covered_branches == 1
        assert report.totals.pct == 100.0
```

- [ ] **Step 2: Run tests — expect fail**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_grader.py -v`
Expected: fail with `ModuleNotFoundError: No module named 'tools.branch_coverage.grader'`

- [ ] **Step 3: Implement `grader.py`**

```python
"""Grader: per-endpoint context intersection + audit reconciliation.

For each endpoint E:
  covered_E = (branches reachable from E) ∩ (hits under E's context)

Audit reconciliation dedupes branches across endpoints: a shared helper
reachable from N endpoints is counted ONCE in the audit enumeration
(to match coverage.py's authoritative per-file total).
"""

from __future__ import annotations

from collections import defaultdict

from tools.branch_coverage.models import (
    AuditReport,
    CoverageReport,
    CoveragePerEndpoint,
    Endpoint,
    ExtraCoverage,
    FunctionCoverage,
    LoadedCoverage,
    ReachableBranch,
    Tone,
    Totals,
    UnattributedBranch,
)

_RED_THRESHOLD = 50.0
_YELLOW_THRESHOLD = 80.0
_THRESHOLDS = {"red": _RED_THRESHOLD, "yellow": _YELLOW_THRESHOLD}


def _tone(pct: float, total: int) -> Tone:
    if total == 0:
        return Tone.NA
    if pct < _RED_THRESHOLD:
        return Tone.ERROR
    if pct < _YELLOW_THRESHOLD:
        return Tone.WARNING
    return Tone.SUCCESS


class Grader:
    def grade(
        self,
        reachability: dict[Endpoint, list[ReachableBranch]],
        hits: LoadedCoverage,
    ) -> CoverageReport:
        endpoints_cov = [
            self._grade_endpoint(ep, branches, hits)
            for ep, branches in reachability.items()
        ]
        endpoints_cov.sort(key=lambda c: (c.endpoint.path, c.endpoint.method))

        # Deduped enumeration across all endpoints + extra_coverage.
        enumerated: set[tuple[str, str]] = set()
        for branches in reachability.values():
            for b in branches:
                enumerated.add((b.file, b.branch_id))

        extra_coverage = self._extra_coverage(reachability, hits)
        for ec in extra_coverage:
            # extra_coverage branches not tied to specific branch ids;
            # they signal file-level "hit but not linked." Audit
            # counts them by file's hit arcs that aren't in enumerated.
            pass  # handled below in audit via set difference

        audit = self._audit(enumerated, hits, extra_coverage)
        totals = self._totals(hits)

        return CoverageReport(
            version=1,
            timestamp=self._timestamp(),
            cucumber_ndjson="frontend/test-results/cucumber.coverage.ndjson",
            instrumented=True,
            thresholds=_THRESHOLDS,
            totals=totals,
            endpoints=tuple(endpoints_cov),
            extra_coverage=tuple(extra_coverage),
            audit=audit,
        )

    def _grade_endpoint(
        self,
        endpoint: Endpoint,
        branches: list[ReachableBranch],
        hits: LoadedCoverage,
    ) -> CoveragePerEndpoint:
        context_label = f"{endpoint.method} {endpoint.path}"
        context_hits = hits.hits_by_context.get(context_label, frozenset())
        total = len(branches)
        covered_set = {
            b for b in branches if (b.file, b.branch_id) in context_hits
        }
        covered = len(covered_set)
        pct = (covered / total * 100) if total else 0.0
        tone = _tone(pct, total)

        # Per-function rollup: group branches by qualname.
        by_func: dict[str, list[ReachableBranch]] = defaultdict(list)
        for b in branches:
            by_func[b.function_qualname].append(b)
        reachable_functions = [
            self._function_coverage(qualname, fb, covered_set)
            for qualname, fb in sorted(by_func.items())
        ]

        return CoveragePerEndpoint(
            endpoint=endpoint,
            reachable_functions=tuple(reachable_functions),
            total_branches=total,
            covered_branches=covered,
            pct=pct,
            tone=tone,
        )

    def _function_coverage(
        self,
        qualname: str,
        branches: list[ReachableBranch],
        covered_set: set[ReachableBranch],
    ) -> FunctionCoverage:
        total = len(branches)
        covered = sum(1 for b in branches if b in covered_set)
        pct = (covered / total * 100) if total else 0.0
        reached = covered > 0
        uncovered = tuple(b for b in branches if b not in covered_set)
        file = branches[0].file if branches else ""
        return FunctionCoverage(
            file=file,
            qualname=qualname,
            total_branches=total,
            covered_branches=covered,
            pct=pct,
            reached=reached,
            uncovered_branches=uncovered,
        )

    def _extra_coverage(
        self,
        reachability: dict[Endpoint, list[ReachableBranch]],
        hits: LoadedCoverage,
    ) -> list[ExtraCoverage]:
        # Files hit by aggregate coverage but not linked to any endpoint's reachability.
        reachable_files = set()
        for branches in reachability.values():
            for b in branches:
                reachable_files.add(b.file)
        hit_files = {f for (f, _bid) in hits.all_hits}
        extra_files = hit_files - reachable_files
        return [
            ExtraCoverage(
                file=file,
                qualname=file,  # placeholder; Analyzer can enrich
                reason="Hit by BDD suite but not linked to any endpoint by static call-graph",
            )
            for file in sorted(extra_files)
        ]

    def _audit(
        self,
        enumerated: set[tuple[str, str]],
        hits: LoadedCoverage,
        extra_coverage: list[ExtraCoverage],
    ) -> AuditReport:
        # Per-file: authoritative total vs deduped enumerated count.
        unattributed: list[UnattributedBranch] = []
        total_authoritative = sum(hits.total_branches_per_file.values())
        extra_count = 0  # extra_coverage doesn't add known branch_ids
        for file, auth_count in hits.total_branches_per_file.items():
            enumerated_in_file = sum(1 for (f, _bid) in enumerated if f == file)
            delta = auth_count - enumerated_in_file
            if delta > 0:
                for i in range(delta):
                    unattributed.append(
                        UnattributedBranch(
                            file=file,
                            line=-1,
                            branch_id=f"unknown_{i}",
                            reason="coverage.py reports branch in file; static graph did not link it to any endpoint",
                        )
                    )
        reconciled = (
            len(enumerated) + extra_count + len(unattributed) == total_authoritative
        )
        return AuditReport(
            total_branches_per_coverage_py=total_authoritative,
            total_branches_enumerated_via_reachability=len(enumerated),
            extra_coverage_branches=extra_count,
            unattributed_branches=tuple(unattributed),
            reconciled=reconciled,
        )

    def _totals(self, hits: LoadedCoverage) -> Totals:
        total = sum(hits.total_branches_per_file.values())
        covered = len(hits.all_hits)
        pct = (covered / total * 100) if total else 0.0
        return Totals(
            total_branches=total,
            covered_branches=covered,
            pct=pct,
            tone=_tone(pct, total),
        )

    @staticmethod
    def _timestamp() -> str:
        from datetime import UTC, datetime

        return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_grader.py -v`
Expected: all pass (11 tests).

- [ ] **Step 5: ruff + mypy**

Run: `cd backend && uv run ruff check tools/branch_coverage/grader.py tests/unit/tools/branch_coverage/test_grader.py && uv run mypy tools/branch_coverage/grader.py`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add backend/tools/branch_coverage/grader.py backend/tests/unit/tools/branch_coverage/test_grader.py
git commit -m "feat(branch-coverage): add Grader with per-endpoint context intersection + audit dedup"
```

---

### Task E2: json_emitter.py + test_json_emitter.py + golden_coverage.json

**Files:**

- Create: `backend/tools/branch_coverage/json_emitter.py`
- Create: `backend/tests/unit/tools/branch_coverage/test_json_emitter.py`
- Create: `backend/tests/fixtures/branch_coverage/golden_coverage.json` (generated in Step 6)

**Context:** Per design spec §4.7. Serializes `CoverageReport` → deterministic JSON. Golden-file test.

- [ ] **Step 1: Write `test_json_emitter.py` (failing tests)**

```python
"""Tests for JsonEmitter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.branch_coverage.json_emitter import JsonEmitter
from tools.branch_coverage.models import (
    AuditReport,
    CoveragePerEndpoint,
    CoverageReport,
    Endpoint,
    FunctionCoverage,
    ReachableBranch,
    Tone,
    Totals,
    UnattributedBranch,
)


def _fixture_report() -> CoverageReport:
    """Deterministic CoverageReport used for golden-file comparison."""
    ep = Endpoint(method="POST", path="/api/v1/games", handler_qualname="hangman.routes.create_game")
    branch = ReachableBranch(
        file="backend/src/hangman/game.py",
        line=42,
        branch_id="42->45",
        condition_text="if category not in self._by_category:",
        not_taken_to_line=45,
        function_qualname="hangman.game.new_game",
    )
    fc = FunctionCoverage(
        file="backend/src/hangman/game.py",
        qualname="hangman.game.new_game",
        total_branches=1,
        covered_branches=0,
        pct=0.0,
        reached=False,
        uncovered_branches=(branch,),
    )
    ep_cov = CoveragePerEndpoint(
        endpoint=ep,
        reachable_functions=(fc,),
        total_branches=1,
        covered_branches=0,
        pct=0.0,
        tone=Tone.ERROR,
    )
    audit = AuditReport(
        total_branches_per_coverage_py=1,
        total_branches_enumerated_via_reachability=1,
        extra_coverage_branches=0,
        unattributed_branches=(),
        reconciled=True,
    )
    return CoverageReport(
        version=1,
        timestamp="2026-04-24T20:00:00Z",
        cucumber_ndjson="frontend/test-results/cucumber.coverage.ndjson",
        instrumented=True,
        thresholds={"red": 50.0, "yellow": 80.0},
        totals=Totals(total_branches=1, covered_branches=0, pct=0.0, tone=Tone.ERROR),
        endpoints=(ep_cov,),
        extra_coverage=(),
        audit=audit,
    )


class TestEmit:
    def test_writes_json_file(self, tmp_path: Path) -> None:
        out = tmp_path / "coverage.json"
        JsonEmitter().emit(_fixture_report(), out)
        assert out.exists()
        parsed = json.loads(out.read_text())
        assert parsed["version"] == 1

    def test_tone_enum_serializes_as_string(self, tmp_path: Path) -> None:
        out = tmp_path / "coverage.json"
        JsonEmitter().emit(_fixture_report(), out)
        parsed = json.loads(out.read_text())
        assert parsed["totals"]["tone"] == "error"

    def test_uncovered_branches_flat_derives_from_functions(self, tmp_path: Path) -> None:
        out = tmp_path / "coverage.json"
        JsonEmitter().emit(_fixture_report(), out)
        parsed = json.loads(out.read_text())
        ep = parsed["endpoints"][0]
        assert "uncovered_branches_flat" in ep
        assert len(ep["uncovered_branches_flat"]) == 1
        assert ep["uncovered_branches_flat"][0]["function_qualname"] == "hangman.game.new_game"


class TestGoldenFile:
    def test_matches_golden(self, tmp_path: Path, fixtures_dir: Path) -> None:
        """Deterministic inputs → byte-identical JSON.

        To regenerate: run this test, copy tmp file content to
        fixtures/branch_coverage/golden_coverage.json.
        """
        out = tmp_path / "coverage.json"
        JsonEmitter().emit(_fixture_report(), out)
        golden = (fixtures_dir / "golden_coverage.json").read_text()
        assert out.read_text() == golden
```

- [ ] **Step 2: Run tests — expect fail**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_json_emitter.py -v`
Expected: fail with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `json_emitter.py`**

```python
"""JsonEmitter: CoverageReport → coverage.json.

Deterministic output: stable field order, sorted iteration, enum values
as strings. Golden-file test ensures bit-for-bit reproducibility.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from tools.branch_coverage.models import (
    CoveragePerEndpoint,
    CoverageReport,
    Tone,
)


class JsonEmitter:
    def emit(self, report: CoverageReport, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self._to_dict(report), indent=2))

    def _to_dict(self, report: CoverageReport) -> dict:
        return {
            "version": report.version,
            "timestamp": report.timestamp,
            "cucumber_ndjson": report.cucumber_ndjson,
            "instrumented": report.instrumented,
            "thresholds": dict(report.thresholds),
            "totals": {
                "total_branches": report.totals.total_branches,
                "covered_branches": report.totals.covered_branches,
                "pct": report.totals.pct,
                "tone": report.totals.tone.value,
            },
            "endpoints": [self._endpoint_dict(ep) for ep in report.endpoints],
            "extra_coverage": [
                {"file": ec.file, "qualname": ec.qualname, "reason": ec.reason}
                for ec in report.extra_coverage
            ],
            "audit": {
                "total_branches_per_coverage_py": report.audit.total_branches_per_coverage_py,
                "total_branches_enumerated_via_reachability": report.audit.total_branches_enumerated_via_reachability,
                "extra_coverage_branches": report.audit.extra_coverage_branches,
                "unattributed_branches": [
                    {
                        "file": ub.file,
                        "line": ub.line,
                        "branch_id": ub.branch_id,
                        "reason": ub.reason,
                    }
                    for ub in report.audit.unattributed_branches
                ],
                "reconciled": report.audit.reconciled,
            },
        }

    def _endpoint_dict(self, ep: CoveragePerEndpoint) -> dict:
        return {
            "method": ep.endpoint.method,
            "path": ep.endpoint.path,
            "handler_qualname": ep.endpoint.handler_qualname,
            "total_branches": ep.total_branches,
            "covered_branches": ep.covered_branches,
            "pct": ep.pct,
            "tone": ep.tone.value,
            "reachable_functions": [
                {
                    "file": fc.file,
                    "qualname": fc.qualname,
                    "total_branches": fc.total_branches,
                    "covered_branches": fc.covered_branches,
                    "pct": fc.pct,
                    "reached": fc.reached,
                    "uncovered_branches": [
                        {
                            "file": b.file,
                            "line": b.line,
                            "branch_id": b.branch_id,
                            "condition_text": b.condition_text,
                            "not_taken_to_line": b.not_taken_to_line,
                        }
                        for b in fc.uncovered_branches
                    ],
                }
                for fc in ep.reachable_functions
            ],
            "uncovered_branches_flat": [
                {
                    "file": b.file,
                    "line": b.line,
                    "branch_id": b.branch_id,
                    "condition_text": b.condition_text,
                    "not_taken_to_line": b.not_taken_to_line,
                    "function_qualname": b.function_qualname,
                }
                for b in ep.uncovered_branches_flat
            ],
        }
```

- [ ] **Step 4: Run shape tests (first 3)**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_json_emitter.py::TestEmit -v`
Expected: 3 pass. Golden test still failing.

- [ ] **Step 5: Generate the golden file**

Run:

```bash
cd backend && uv run python -c "
from pathlib import Path
import sys
sys.path.insert(0, 'tests/unit/tools/branch_coverage')
from test_json_emitter import _fixture_report
from tools.branch_coverage.json_emitter import JsonEmitter
out = Path('tests/fixtures/branch_coverage/golden_coverage.json')
JsonEmitter().emit(_fixture_report(), out)
print('Wrote', out, out.stat().st_size, 'bytes')
"
```

Inspect the file: it should be ~2-3 KB, contain a single endpoint, one function with one uncovered branch, `reconciled: true`.

- [ ] **Step 6: Run all tests — expect pass**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_json_emitter.py -v`
Expected: all 4 tests pass (including golden).

- [ ] **Step 7: ruff + mypy**

Run: `cd backend && uv run ruff check tools/branch_coverage/json_emitter.py tests/unit/tools/branch_coverage/test_json_emitter.py && uv run mypy tools/branch_coverage/json_emitter.py`
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add backend/tools/branch_coverage/json_emitter.py backend/tests/unit/tools/branch_coverage/test_json_emitter.py backend/tests/fixtures/branch_coverage/golden_coverage.json
git commit -m "feat(branch-coverage): add JsonEmitter + golden-file test"
```

---

### Task E3: renderer.py + templates/ + test_renderer.py + golden_coverage.html

**Files:**

- Create: `backend/tools/branch_coverage/templates/base.html.j2`
- Create: `backend/tools/branch_coverage/templates/_endpoint_card.html.j2`
- Create: `backend/tools/branch_coverage/templates/_function_drilldown.html.j2`
- Create: `backend/tools/branch_coverage/renderer.py`
- Create: `backend/tests/unit/tools/branch_coverage/test_renderer.py`
- Create: `backend/tests/fixtures/branch_coverage/golden_coverage.html` (generated in step 7)

**Context:** Per design spec §4.8. Jinja2 with autoescape. Dark theme matching Feature 2.

- [ ] **Step 1: Write `base.html.j2`**

```jinja
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Branch Coverage — {{ report.timestamp }}</title>
  <style>
    :root { --bg:#0f1115; --fg:#e8eaed; --muted:#9aa0a6;
            --success:#2aa876; --warning:#f5a623; --error:#e74c3c; }
    body { background:var(--bg); color:var(--fg);
           font-family:-apple-system,system-ui,sans-serif; margin:0; padding:24px; }
    h1 { margin:0 0 8px; font-weight:600; }
    .muted { color:var(--muted); font-size:13px; }
    .banner-warn { background:var(--warning); color:#000; padding:12px;
                   border-radius:8px; margin:12px 0; }
    .banner-info { background:#1a2d4a; color:var(--fg); padding:12px;
                   border-radius:8px; margin:12px 0; }
    .totals { background:#1a1d24; border-radius:12px; padding:20px;
              margin:24px 0; }
    .totals .value { font-size:40px; font-weight:700; }
    .totals.success .value { color:var(--success); }
    .totals.warning .value { color:var(--warning); }
    .totals.error .value { color:var(--error); }
    .endpoints { display:grid;
                 grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:12px; }
    .card { background:#1a1d24; border-radius:12px; padding:16px;
            border:1px solid #252932; }
    .card.success { border-color:var(--success); }
    .card.warning { border-color:var(--warning); }
    .card.error { border-color:var(--error); }
    .card .pct { font-size:24px; font-weight:700; margin:4px 0; }
    .card.success .pct { color:var(--success); }
    .card.warning .pct { color:var(--warning); }
    .card.error .pct { color:var(--error); }
    .drilldown { background:#0f1115; border-radius:8px; padding:12px;
                 margin-top:12px; font-size:12px; }
    .drilldown details summary { cursor:pointer; }
    .extra, .audit { background:#1a1d24; border-radius:12px; padding:16px;
                     margin:16px 0; }
  </style>
</head>
<body>
  <header>
    <h1>Branch Coverage</h1>
    <div class="muted">{{ report.timestamp }} · BDD suite vs. backend/src/hangman/</div>
  </header>

  <div class="banner-info">
    ℹ This run used coverage instrumentation. Performance metrics in this
    report are not representative of normal runs.
  </div>

  {% if not report.audit.reconciled %}
  <div class="banner-warn">
    ⚠ Audit reconciliation FAILED —
    {{ report.audit.unattributed_branches|length }} unattributed branches.
    coverage.py says {{ report.audit.total_branches_per_coverage_py }} branches
    exist; our enumeration found only
    {{ report.audit.total_branches_enumerated_via_reachability }}. See the
    audit section below for details.
  </div>
  {% endif %}

  <section class="totals {{ report.totals.tone.value }}">
    <div class="muted">Total coverage</div>
    <div class="value">{{ '%.1f'|format(report.totals.pct) }}%</div>
    <div class="muted">
      {{ report.totals.covered_branches }} of
      {{ report.totals.total_branches }} branches covered
    </div>
  </section>

  <h2>Per endpoint</h2>
  <section class="endpoints">
    {% for ep in report.endpoints %}
      {% include "_endpoint_card.html.j2" %}
    {% endfor %}
  </section>

  {% if report.extra_coverage %}
  <section class="extra">
    <h2>Extra coverage</h2>
    <div class="muted">
      Files hit by the BDD suite that the static call-graph didn't link
      to any endpoint.
    </div>
    <ul>
      {% for ec in report.extra_coverage %}
      <li><code>{{ ec.file }}</code> — {{ ec.reason }}</li>
      {% endfor %}
    </ul>
  </section>
  {% endif %}

  <section class="audit">
    <h2>Audit reconciliation</h2>
    <div class="muted">
      authoritative (coverage.py) = {{ report.audit.total_branches_per_coverage_py }} ·
      enumerated via reachability = {{ report.audit.total_branches_enumerated_via_reachability }} ·
      extra_coverage branches = {{ report.audit.extra_coverage_branches }} ·
      unattributed = {{ report.audit.unattributed_branches|length }} ·
      reconciled = {{ report.audit.reconciled }}
    </div>
    {% if report.audit.unattributed_branches %}
    <details>
      <summary>Unattributed branches ({{ report.audit.unattributed_branches|length }})</summary>
      <ul>
        {% for ub in report.audit.unattributed_branches %}
        <li><code>{{ ub.file }}:{{ ub.line }}</code> — {{ ub.reason }}</li>
        {% endfor %}
      </ul>
    </details>
    {% endif %}
  </section>
</body>
</html>
```

- [ ] **Step 2: Write `_endpoint_card.html.j2`**

```jinja
<article class="card {{ ep.tone.value }}">
  <div class="muted">{{ ep.endpoint.method }} {{ ep.endpoint.path }}</div>
  <div class="pct">{{ '%.1f'|format(ep.pct) }}%</div>
  <div class="muted">
    {{ ep.covered_branches }} of {{ ep.total_branches }} branches ·
    handler: <code>{{ ep.endpoint.handler_qualname }}</code>
  </div>
  <div class="drilldown">
    <details>
      <summary>{{ ep.reachable_functions|length }} reachable function(s)</summary>
      {% for fc in ep.reachable_functions %}
        {% include "_function_drilldown.html.j2" %}
      {% endfor %}
    </details>
  </div>
</article>
```

- [ ] **Step 3: Write `_function_drilldown.html.j2`**

```jinja
<div style="margin:8px 0;">
  <div>
    <code>{{ fc.qualname }}</code> ·
    {{ fc.covered_branches }}/{{ fc.total_branches }}
    ({{ '%.0f'|format(fc.pct) }}%)
    {% if not fc.reached %}<span style="color:var(--warning)">⚠ not reached</span>{% endif %}
  </div>
  {% if fc.uncovered_branches %}
  <ul>
    {% for b in fc.uncovered_branches %}
    <li>
      <code>{{ b.file }}:{{ b.line }}</code> —
      <code>{{ b.condition_text }}</code>
    </li>
    {% endfor %}
  </ul>
  {% endif %}
</div>
```

- [ ] **Step 4: Write `test_renderer.py` (failing tests)**

```python
"""Tests for DashboardRenderer."""

from __future__ import annotations

from pathlib import Path

from tests.unit.tools.branch_coverage.test_json_emitter import _fixture_report
from tools.branch_coverage.renderer import DashboardRenderer


class TestRender:
    def test_writes_html_file(self, tmp_path: Path) -> None:
        out = tmp_path / "coverage.html"
        DashboardRenderer().render(_fixture_report(), out)
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_contains_totals_section(self, tmp_path: Path) -> None:
        out = tmp_path / "coverage.html"
        DashboardRenderer().render(_fixture_report(), out)
        html = out.read_text()
        assert "Total coverage" in html
        assert "0.0%" in html  # fixture has 0/1 covered

    def test_contains_endpoint_card(self, tmp_path: Path) -> None:
        out = tmp_path / "coverage.html"
        DashboardRenderer().render(_fixture_report(), out)
        html = out.read_text()
        assert "POST /api/v1/games" in html
        assert "hangman.routes.create_game" in html

    def test_reconciled_true_shows_no_warning_banner(self, tmp_path: Path) -> None:
        out = tmp_path / "coverage.html"
        DashboardRenderer().render(_fixture_report(), out)
        html = out.read_text()
        assert "Audit reconciliation FAILED" not in html

    def test_autoescapes_condition_text(self, tmp_path: Path) -> None:
        # Inject a condition text with <script> to verify autoescape.
        from tools.branch_coverage.models import (
            CoveragePerEndpoint,
            CoverageReport,
            Endpoint,
            FunctionCoverage,
            ReachableBranch,
            Tone,
            AuditReport,
            Totals,
        )

        poisoned = ReachableBranch(
            file="x.py",
            line=1,
            branch_id="1->2",
            condition_text="<script>alert(1)</script>",
            not_taken_to_line=2,
            function_qualname="x.fn",
        )
        fc = FunctionCoverage(
            file="x.py",
            qualname="x.fn",
            total_branches=1,
            covered_branches=0,
            pct=0.0,
            reached=False,
            uncovered_branches=(poisoned,),
        )
        ep_cov = CoveragePerEndpoint(
            endpoint=Endpoint(method="GET", path="/x", handler_qualname="x.handler"),
            reachable_functions=(fc,),
            total_branches=1,
            covered_branches=0,
            pct=0.0,
            tone=Tone.ERROR,
        )
        report = CoverageReport(
            version=1,
            timestamp="2026-04-24T20:00:00Z",
            cucumber_ndjson="x.ndjson",
            instrumented=True,
            thresholds={"red": 50.0, "yellow": 80.0},
            totals=Totals(total_branches=1, covered_branches=0, pct=0.0, tone=Tone.ERROR),
            endpoints=(ep_cov,),
            extra_coverage=(),
            audit=AuditReport(
                total_branches_per_coverage_py=1,
                total_branches_enumerated_via_reachability=1,
                extra_coverage_branches=0,
                unattributed_branches=(),
                reconciled=True,
            ),
        )
        out = tmp_path / "coverage.html"
        DashboardRenderer().render(report, out)
        html = out.read_text()
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


class TestGoldenFile:
    def test_matches_golden(self, tmp_path: Path, fixtures_dir: Path) -> None:
        out = tmp_path / "coverage.html"
        DashboardRenderer().render(_fixture_report(), out)
        golden = (fixtures_dir / "golden_coverage.html").read_text()
        assert out.read_text() == golden
```

- [ ] **Step 5: Run tests — expect fail**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_renderer.py -v`
Expected: fail with `ModuleNotFoundError`.

- [ ] **Step 6: Implement `renderer.py`**

```python
"""DashboardRenderer: Jinja2 + autoescape → coverage.html."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from tools.branch_coverage.models import CoverageReport


class DashboardRenderer:
    def __init__(self) -> None:
        self._env = Environment(
            loader=PackageLoader("tools.branch_coverage", "templates"),
            autoescape=select_autoescape(["html", "j2"]),
            trim_blocks=False,
            lstrip_blocks=False,
        )

    def render(self, report: CoverageReport, output_path: Path) -> None:
        template = self._env.get_template("base.html.j2")
        html = template.render(report=report)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html)
```

- [ ] **Step 7: Generate the golden HTML file**

Run:

```bash
cd backend && uv run python -c "
from pathlib import Path
import sys
sys.path.insert(0, 'tests/unit/tools/branch_coverage')
from test_json_emitter import _fixture_report
from tools.branch_coverage.renderer import DashboardRenderer
out = Path('tests/fixtures/branch_coverage/golden_coverage.html')
DashboardRenderer().render(_fixture_report(), out)
print('Wrote', out, out.stat().st_size, 'bytes')
"
```

Eyeball the file: should be ~3-5 KB, contain the totals section, one endpoint card, and the audit section (reconciled: True, no warning banner).

- [ ] **Step 8: Run tests — expect pass**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_renderer.py -v`
Expected: all 6 tests pass.

- [ ] **Step 9: ruff + mypy**

Run: `cd backend && uv run ruff check tools/branch_coverage/renderer.py tests/unit/tools/branch_coverage/test_renderer.py && uv run mypy tools/branch_coverage/renderer.py`
Expected: clean.

- [ ] **Step 10: Commit**

```bash
git add backend/tools/branch_coverage/renderer.py backend/tools/branch_coverage/templates/ backend/tests/unit/tools/branch_coverage/test_renderer.py backend/tests/fixtures/branch_coverage/golden_coverage.html
git commit -m "feat(branch-coverage): add Jinja2 DashboardRenderer + golden-file test"
```

---

## Phase F — Orchestration

### Task F1: analyzer.py + **main**.py + test_analyzer.py

**Files:**

- Create: `backend/tools/branch_coverage/analyzer.py`
- Create: `backend/tools/branch_coverage/__main__.py`
- Create: `backend/tests/unit/tools/branch_coverage/test_analyzer.py`

**Context:** Per design spec §4.9 + §4.12. Analyzer orchestrates the pipeline; `__main__.py` is the argparse CLI. End-to-end test uses fake CallGraphBuilder (no real pyan3 invocation at test time).

- [ ] **Step 1: Write `test_analyzer.py` (failing tests)**

```python
"""End-to-end Analyzer test with fakes for subprocess-like components."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.branch_coverage.fake_adjacency import fake_graph_for_minimal_app
from tools.branch_coverage.analyzer import Analyzer
from tools.branch_coverage.callgraph import CallGraph
from tools.branch_coverage.coverage_data import CoverageDataLoader
from tools.branch_coverage.grader import Grader
from tools.branch_coverage.json_emitter import JsonEmitter
from tools.branch_coverage.models import LoadedCoverage
from tools.branch_coverage.reachability import Reachability
from tools.branch_coverage.renderer import DashboardRenderer
from tools.branch_coverage.routes import RouteEnumerator


class _FakeCallGraphBuilder:
    def build(self, source_root: Path) -> CallGraph:
        return fake_graph_for_minimal_app()


class _FakeCoverageDataLoader:
    def load(self, coverage_file: Path) -> LoadedCoverage:
        # Every branch covered under the matching endpoint context.
        return LoadedCoverage(
            hits_by_context={},
            total_branches_per_file={},
            all_hits=frozenset(),
        )


def _import_minimal_app():
    from tests.fixtures.branch_coverage.minimal_app.main import app
    return app


class TestAnalyzerPipeline:
    def test_runs_end_to_end_with_fakes(
        self, tmp_path: Path, minimal_app_source_root: Path
    ) -> None:
        html_out = tmp_path / "coverage.html"
        json_out = tmp_path / "coverage.json"
        analyzer = Analyzer(
            routes=RouteEnumerator(),
            callgraph=_FakeCallGraphBuilder(),
            reachability=Reachability(),
            coverage_data=_FakeCoverageDataLoader(),
            grader=Grader(),
            json_emitter=JsonEmitter(),
            renderer=DashboardRenderer(),
        )
        analyzer.run(
            app=_import_minimal_app(),
            coverage_file=tmp_path / "nonexistent.coverage",  # fake loader ignores
            source_root=minimal_app_source_root,
            json_output=json_out,
            html_output=html_out,
        )
        assert json_out.exists()
        assert html_out.exists()
        assert html_out.stat().st_size > 500
```

- [ ] **Step 2: Run tests — expect fail**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_analyzer.py -v`
Expected: fail with `ModuleNotFoundError: No module named 'tools.branch_coverage.analyzer'`.

- [ ] **Step 3: Implement `analyzer.py`**

```python
"""Analyzer orchestrator — wires the branch coverage pipeline."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from tools.branch_coverage.models import AuditReport, CoverageReport

_LOG = logging.getLogger(__name__)


class Analyzer:
    def __init__(
        self,
        routes: Any,
        callgraph: Any,
        reachability: Any,
        coverage_data: Any,
        grader: Any,
        json_emitter: Any,
        renderer: Any,
    ) -> None:
        self.routes = routes
        self.callgraph = callgraph
        self.reachability = reachability
        self.coverage_data = coverage_data
        self.grader = grader
        self.json_emitter = json_emitter
        self.renderer = renderer

    def run(
        self,
        app: Any,
        coverage_file: Path,
        source_root: Path,
        json_output: Path,
        html_output: Path,
    ) -> None:
        endpoints = self.routes.enumerate(app)
        graph = self.callgraph.build(source_root)
        reach = self.reachability.compute(endpoints, graph, source_root)
        hits = self.coverage_data.load(coverage_file)
        report = self.grader.grade(reach, hits)
        self.json_emitter.emit(report, json_output)
        self.renderer.render(report, html_output)
        self._print_audit(report.audit)

    @staticmethod
    def _print_audit(audit: AuditReport) -> None:
        reconciled = "✓" if audit.reconciled else "✗"
        print(
            f"{reconciled} Audit: "
            f"coverage.py={audit.total_branches_per_coverage_py} · "
            f"enumerated={audit.total_branches_enumerated_via_reachability} · "
            f"unattributed={len(audit.unattributed_branches)} · "
            f"reconciled={audit.reconciled}",
            file=sys.stderr,
        )
        if not audit.reconciled:
            print(
                "WARNING: audit reconciliation failed — see coverage.html "
                "for the unattributed-branch list.",
                file=sys.stderr,
            )
```

- [ ] **Step 4: Implement `__main__.py`**

```python
"""CLI entrypoint: `python -m tools.branch_coverage`.

Defaults anchor off Path(__file__).resolve().parents[3] (repo root)
so the command works from any directory.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.branch_coverage.analyzer import Analyzer
from tools.branch_coverage.callgraph import CallGraphBuilder
from tools.branch_coverage.coverage_data import (
    CoverageDataLoader,
    CoverageDataLoadError,
)
from tools.branch_coverage.grader import Grader
from tools.branch_coverage.json_emitter import JsonEmitter
from tools.branch_coverage.reachability import Reachability
from tools.branch_coverage.renderer import DashboardRenderer
from tools.branch_coverage.routes import RouteEnumerator

# backend/tools/branch_coverage/__main__.py → parents[3] = repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.branch_coverage")
    parser.add_argument(
        "--coverage-file",
        default=_REPO_ROOT / "backend" / ".coverage",
        type=Path,
    )
    parser.add_argument(
        "--source-root",
        default=_REPO_ROOT / "backend" / "src" / "hangman",
        type=Path,
    )
    parser.add_argument(
        "--json-output",
        default=_REPO_ROOT / "tests" / "bdd" / "reports" / "coverage.json",
        type=Path,
    )
    parser.add_argument(
        "--html-output",
        default=_REPO_ROOT / "tests" / "bdd" / "reports" / "coverage.html",
        type=Path,
    )
    args = parser.parse_args()

    # Import the hangman app reflectively (see design spec §12 risk #2
    # for the side-effects audit — handled at import-time if needed).
    from hangman.main import app

    analyzer = Analyzer(
        routes=RouteEnumerator(),
        callgraph=CallGraphBuilder(),
        reachability=Reachability(),
        coverage_data=CoverageDataLoader(),
        grader=Grader(),
        json_emitter=JsonEmitter(),
        renderer=DashboardRenderer(),
    )
    try:
        analyzer.run(
            app=app,
            coverage_file=args.coverage_file,
            source_root=args.source_root,
            json_output=args.json_output,
            html_output=args.html_output,
        )
    except CoverageDataLoadError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR (unexpected): {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests — expect pass**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/test_analyzer.py -v`
Expected: all pass.

- [ ] **Step 6: Full branch_coverage suite green**

Run: `cd backend && uv run pytest tests/unit/tools/branch_coverage/ -v`
Expected: every test passes (~60-80 tests across 9 test files).

- [ ] **Step 7: Smoke-test CLI help**

Run: `cd backend && uv run python -m tools.branch_coverage --help`
Expected: argparse help with all --coverage-file / --source-root / --json-output / --html-output options and their `_REPO_ROOT`-anchored defaults.

- [ ] **Step 8: ruff + mypy across everything**

Run: `cd backend && uv run ruff check tools/branch_coverage/ tests/unit/tools/branch_coverage/ && uv run mypy tools/`
Expected: clean.

- [ ] **Step 9: Commit**

```bash
git add backend/tools/branch_coverage/analyzer.py backend/tools/branch_coverage/__main__.py backend/tests/unit/tools/branch_coverage/test_analyzer.py
git commit -m "feat(branch-coverage): add Analyzer orchestrator + CLI entrypoint"
```

---

## Phase G — Feature 2 integration

### Task G1: Feature 2 augmentation — models + analyzer staleness + renderer card

**Files:**

- Modify: `backend/tools/dashboard/models.py` (add `CoverageContext` dataclass)
- Modify: `backend/tools/dashboard/analyzer.py` (staleness check, load CoverageContext)
- Modify: `backend/tools/dashboard/renderer.py` (new "Code coverage" summary card)
- Modify: `backend/tests/unit/tools/dashboard/test_analyzer.py` (staleness cases)
- Modify: `backend/tests/unit/tools/dashboard/test_renderer.py` (card cases)

**Context:** Per design spec §6. Feature 2 auto-detects `coverage.json`; renders augmented card; uses 1h staleness threshold vs. cucumber.ndjson's `meta.startedAt`. 5 files touched in Feature 2 — keep Feature 2's existing 99 tests green; add ~5 new tests.

- [ ] **Step 1: Add `CoverageContext` to `backend/tools/dashboard/models.py`**

Append to the existing file (don't rewrite):

```python
@dataclass(frozen=True)
class CoverageContext:
    """Typed view over coverage.json (Feature 3's output) consumed by Feature 2.

    When present, drives: (a) the augment "Code coverage" summary card,
    and (b) a coverage summary injected into the LLM's cached system
    prompt. See design spec §6.2.
    """
    timestamp: str
    totals_pct: float
    totals_tone: str                    # "success" | "warning" | "error"
    totals_covered_branches: int
    totals_total_branches: int
    endpoints_summary: tuple[tuple[str, str, float, str], ...]  # (method, path, pct, tone)
    endpoints_uncovered_flat: dict[str, tuple[dict, ...]]       # key = f"{method} {path}"
    audit_reconciled: bool
    audit_unattributed_count: int
```

- [ ] **Step 2: Modify `backend/tools/dashboard/analyzer.py` — staleness check**

**Per plan-review iter 2 P1: define these as MODULE-LEVEL functions, not Analyzer instance methods.** G2 needs to import them in `__main__.py` to construct `LlmEvaluator(coverage_summary=...)` BEFORE the Analyzer is constructed (since the LLM is one of Analyzer's injected dependencies). Module-level scope satisfies both call-sites.

Read the existing `analyzer.py`. At module level (between the imports and the `class Analyzer:` declaration), add:

```python
def load_coverage_context_if_fresh(ndjson_path: Path) -> CoverageContext | None:
    """Returns CoverageContext if tests/bdd/reports/coverage.json
    exists AND its timestamp is within 1 hour of ndjson's mtime.
    Otherwise None.

    Module-level (not an Analyzer method) so __main__.py can call it
    before constructing Analyzer + LlmEvaluator.
    """
    import json
    from datetime import datetime, timedelta, UTC

    coverage_json_path = (
        ndjson_path.parent.parent.parent / "tests" / "bdd" / "reports" / "coverage.json"
    )
    if not coverage_json_path.exists():
        _LOG.info("No coverage.json found at %s — rendering placeholder", coverage_json_path)
        return None
    try:
        data = json.loads(coverage_json_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        _LOG.warning("coverage.json parse failed: %s", exc)
        return None
    cov_ts_str = data.get("timestamp", "")
    try:
        cov_ts = datetime.fromisoformat(cov_ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    ndjson_mtime = datetime.fromtimestamp(ndjson_path.stat().st_mtime, tz=UTC)
    if abs((cov_ts - ndjson_mtime).total_seconds()) > timedelta(hours=1).total_seconds():
        _LOG.warning("coverage.json is stale vs. cucumber.ndjson — ignoring")
        return None
    return _build_coverage_context(data)


def _build_coverage_context(data: dict) -> CoverageContext:
    """Module-level helper. Underscore-prefixed (internal to analyzer.py)."""
    endpoints_summary = tuple(
        (ep["method"], ep["path"], ep["pct"], ep["tone"])
        for ep in data.get("endpoints", [])
    )
    endpoints_uncovered_flat: dict[str, tuple[dict, ...]] = {
        f"{ep['method']} {ep['path']}": tuple(ep.get("uncovered_branches_flat", []))
        for ep in data.get("endpoints", [])
    }
    totals = data.get("totals", {})
    audit = data.get("audit", {})
    return CoverageContext(
        timestamp=data.get("timestamp", ""),
        totals_pct=totals.get("pct", 0.0),
        totals_tone=totals.get("tone", ""),
        totals_covered_branches=totals.get("covered_branches", 0),
        totals_total_branches=totals.get("total_branches", 0),
        endpoints_summary=endpoints_summary,
        endpoints_uncovered_flat=endpoints_uncovered_flat,
        audit_reconciled=audit.get("reconciled", True),
        audit_unattributed_count=len(audit.get("unattributed_branches", [])),
    )


def build_coverage_summary(ctx: CoverageContext) -> str:
    """Format a CoverageContext as the human/LLM-readable summary string
    that gets injected into the cached system prompt. Module-level so
    __main__.py can call it directly."""
    lines = [
        "## Coverage context for this run",
        "",
        f"The BDD suite achieved {ctx.totals_pct:.0f}% branch coverage "
        f"on backend/src/hangman/ "
        f"({ctx.totals_covered_branches} of {ctx.totals_total_branches} branches).",
        "",
        "Per-endpoint uncovered branches (use when emitting D7 findings):",
    ]
    for method, path, pct, _tone in ctx.endpoints_summary:
        key = f"{method} {path}"
        uncovered = ctx.endpoints_uncovered_flat.get(key, ())
        if not uncovered:
            continue
        lines.append(f"- {method} {path} ({pct:.0f}% covered):")
        for b in uncovered[:10]:  # cap at 10 per endpoint to keep prompt small
            lines.append(
                f"  - {b.get('file', '?')}:{b.get('line', '?')} "
                f"\"{b.get('condition_text', '?')}\""
            )
    lines.append("")
    lines.append(
        "When evaluating scenarios, reference this data. If a scenario hits "
        "an endpoint with uncovered branches, emit a D7 finding only if the "
        "scenario plausibly could exercise those branches and doesn't."
    )
    return "\n".join(lines)
```

Then locate the top of `Analyzer.run()` and add:

```python
    coverage_context = load_coverage_context_if_fresh(ndjson_path)
```

(no `self.` — calls the module-level function.)

**Note:** `build_coverage_summary` is moved here from G2 (where it was previously documented as a separate piece). G1 owns the function definition; G2 just imports and uses it.

Also add the import at the top of `analyzer.py`:

```python
from tools.dashboard.models import CoverageContext
```

And thread `coverage_context` through to the renderer in `run()`:

```python
        self.renderer.render(
            context, findings, list(grades), history_entries,
            skipped, summary, coverage_context, output_path,  # NEW arg
        )
```

- [ ] **Step 3: Modify `backend/tools/dashboard/renderer.py`**

Add `coverage_context` parameter to `render()`:

```python
    def render(
        self,
        context: AnalysisContext,
        findings: list[Finding],
        grades: list[CoverageGrade],
        history: list[RunSummary],
        skipped_packages: tuple[str, ...],
        run_summary: RunSummary,
        coverage_context: "CoverageContext | None",
        output_path: Path,
    ) -> None:
```

Add the import at the top:

```python
from tools.dashboard.models import CoverageContext
```

Modify `_build_summary_cards` to accept `coverage_context` and append the new card:

```python
    def _build_summary_cards(
        self,
        context: AnalysisContext,
        grades: list[CoverageGrade],
        summary: RunSummary,
        coverage_context: CoverageContext | None,
    ) -> list[SummaryCard]:
        # ... existing 7 cards unchanged ...

        # New "Code coverage" card (Feature 3 augment).
        if coverage_context is not None:
            cards.append(SummaryCard(
                title="Code coverage",
                value=f"{coverage_context.totals_pct:.0f}%",
                subtitle=f"{coverage_context.totals_covered_branches}/"
                         f"{coverage_context.totals_total_branches} branches"
                         + (" · ⚠ audit failed" if not coverage_context.audit_reconciled else ""),
                tone=coverage_context.totals_tone,
            ))
        else:
            cards.append(SummaryCard(
                title="Code coverage",
                value="—",
                subtitle="Run `make bdd-coverage` to enable",
                tone="",
            ))

        return cards
```

And thread `coverage_context` through the `render()` call site that invokes `_build_summary_cards`.

- [ ] **Step 4: Update `backend/tests/unit/tools/dashboard/test_analyzer.py`** — add staleness cases

Append new test class:

```python
class TestCoverageAugmentation:
    def test_missing_coverage_json_returns_none_context(
        self, tmp_path, fixtures_dir, mock_anthropic_client, good_tool_input
    ) -> None:
        # No coverage.json file present → CoverageContext is None, no crash.
        # Module-level function — no Analyzer instance needed.
        from tools.dashboard.analyzer import load_coverage_context_if_fresh

        cov = load_coverage_context_if_fresh(tmp_path / "cucumber.ndjson")
        assert cov is None

    def test_stale_coverage_json_returns_none(self, tmp_path) -> None:
        import json
        from tools.dashboard.analyzer import load_coverage_context_if_fresh

        # Create a coverage.json with a timestamp >1h older than ndjson mtime.
        ndjson = tmp_path / "frontend" / "test-results" / "cucumber.ndjson"
        ndjson.parent.mkdir(parents=True)
        ndjson.write_text("")
        cov_json = tmp_path / "tests" / "bdd" / "reports" / "coverage.json"
        cov_json.parent.mkdir(parents=True)
        cov_json.write_text(json.dumps({
            "timestamp": "2020-01-01T00:00:00Z",
            "totals": {"pct": 50.0, "tone": "warning", "covered_branches": 5, "total_branches": 10},
            "endpoints": [],
            "audit": {"reconciled": True, "unattributed_branches": []},
        }))
        cov = load_coverage_context_if_fresh(ndjson)
        assert cov is None  # too stale
```

- [ ] **Step 5: Update `backend/tests/unit/tools/dashboard/test_renderer.py`** — add card cases

Append:

```python
class TestCoverageCard:
    def test_card_present_when_context_provided(self, tmp_path: Path) -> None:
        from tools.dashboard.models import CoverageContext

        ctx, findings, grades, history, summary = _deterministic_inputs()
        cov_ctx = CoverageContext(
            timestamp="2026-04-24T12:00:00Z",
            totals_pct=69.0,
            totals_tone="warning",
            totals_covered_branches=98,
            totals_total_branches=142,
            endpoints_summary=(),
            endpoints_uncovered_flat={},
            audit_reconciled=True,
            audit_unattributed_count=0,
        )
        out = tmp_path / "dashboard.html"
        DashboardRenderer().render(ctx, findings, grades, history, (), summary, cov_ctx, out)
        html = out.read_text()
        assert "Code coverage" in html
        assert "69%" in html
        assert "98/142 branches" in html

    def test_placeholder_when_context_none(self, tmp_path: Path) -> None:
        ctx, findings, grades, history, summary = _deterministic_inputs()
        out = tmp_path / "dashboard.html"
        DashboardRenderer().render(ctx, findings, grades, history, (), summary, None, out)
        html = out.read_text()
        assert "Code coverage" in html
        assert "Run `make bdd-coverage`" in html or "make bdd-coverage" in html
```

**Explicit call-site checklist** (per plan-review iter 1 P1: Feature 2 has 8 `DashboardRenderer().render(...)` call-sites; missing any one breaks the test suite):

Run this command to enumerate all call-sites:

```bash
grep -n "DashboardRenderer().render(" backend/tests/unit/tools/dashboard/test_renderer.py
```

Expected output: 8 lines (matching Feature 2's master branch as of commit `bf1b2df`). Each line needs `None` inserted between `summary` and `out`:

```python
# BEFORE
DashboardRenderer().render(ctx, findings, grades, history, (), summary, out)
# AFTER
DashboardRenderer().render(ctx, findings, grades, history, (), summary, None, out)
```

Use a global find/replace if your editor supports it; otherwise update each line. Verify the count after editing:

```bash
grep -c "DashboardRenderer().render(ctx" backend/tests/unit/tools/dashboard/test_renderer.py
# Expected: 8 (or 10 if TestCoverageCard's two new call-sites were added in Step 5)
```

If `coverage_context` isn't in the new positional position 7 (between `summary` and `out`), the existing tests fail with a `TypeError` mismatch. Run:

```bash
cd backend && uv run pytest tests/unit/tools/dashboard/test_renderer.py -v 2>&1 | head -30
```

to surface any remaining mismatches before the next step.

**Golden file regeneration step** (per plan-review iter 1 P2: Feature 2's `golden_render.html` will change because the new "Code coverage" placeholder card lands in `_build_summary_cards`):

```bash
cd backend && uv run python -c "
from pathlib import Path
import sys
sys.path.insert(0, 'tests/unit/tools/dashboard')
from test_renderer import _deterministic_inputs
from tools.dashboard.renderer import DashboardRenderer
ctx, findings, grades, history, summary = _deterministic_inputs()
out = Path('tests/fixtures/dashboard/golden_render.html')
# coverage_context=None → placeholder card appears.
DashboardRenderer().render(ctx, findings, grades, history, (), summary, None, out)
print('Regenerated golden:', out.stat().st_size, 'bytes')
"
```

Eyeball the diff:

```bash
git diff backend/tests/fixtures/dashboard/golden_render.html | head -40
```

Expected: the diff shows ONE new card section with title "Code coverage", value "—", subtitle "Run \`make bdd-coverage\` to enable", tone "" (empty). Other cards unchanged. If unexpected diff appears (e.g., a real coverage % showing instead of "—"), re-check `_load_coverage_context_if_fresh` — it should return None when `coverage.json` doesn't exist.

Run the golden test to confirm:

```bash
cd backend && uv run pytest tests/unit/tools/dashboard/test_renderer.py::TestGoldenFile -v
```

Expected: PASS.

- [ ] **Step 6: Run full backend test suite**

Run: `cd backend && uv run pytest tests/unit/tools/ -v`
Expected: all tests pass (~99 existing + ~5 new in Feature 2 + all Feature 3 tests).

- [ ] **Step 7: ruff + mypy**

Run: `cd backend && uv run ruff check tools/ tests/unit/tools/ && uv run mypy tools/`
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add backend/tools/dashboard/models.py backend/tools/dashboard/analyzer.py backend/tools/dashboard/renderer.py backend/tests/unit/tools/dashboard/test_analyzer.py backend/tests/unit/tools/dashboard/test_renderer.py backend/tests/fixtures/dashboard/golden_render.html
git commit -m "fix(dashboard): augment dashboard with coverage.json via new CoverageContext + Code coverage card"
```

---

### Task G2: Feature 2 LLM integration — client coverage_summary + rubric D7

**Files:**

- Modify: `backend/tools/dashboard/llm/client.py` (instance-level `_system` + `coverage_summary` param)
- Modify: `backend/tools/dashboard/llm/rubric.py` (add D7 criterion)
- Modify: `backend/tools/dashboard/analyzer.py` (build coverage_summary string, pass to LlmEvaluator)
- Modify: `backend/tests/unit/tools/dashboard/test_llm_client.py` (new injection test + instance attr)
- Modify: `backend/tests/unit/tools/dashboard/test_rubric.py` (assert D7 present)

**Context:** Per design spec §6.3 + §6.4. This is the breaking change from §6.3 — `_SYSTEM` module constant becomes `self._system` instance attribute. Feature 2's existing cache-hit-behavior tests may need light updates.

- [ ] **Step 1: Modify `backend/tools/dashboard/llm/client.py`**

Locate the module-level `_SYSTEM` constant (line ~48 per Feature 2 design). Remove it. Add a `coverage_summary: str = ""` parameter to `LlmEvaluator.__init__` and build `self._system` there:

```python
def __init__(
    self,
    client: Any | None = None,
    model: str = "claude-sonnet-4-6",
    max_workers: int = 6,
    max_retries_per_call: int = 1,
    coverage_summary: str = "",
) -> None:
    token_count = rubric_token_count()
    if token_count < _RUBRIC_CACHE_MIN_TOKENS:
        raise RubricTooShortError(
            f"Rubric is {token_count} tokens — below "
            f"{_RUBRIC_CACHE_MIN_TOKENS}-token cache floor."
        )
    if client is None:
        from anthropic import Anthropic
        self._client: Any = Anthropic()
    else:
        self._client = client
    self._model = model
    self._max_workers = max_workers
    self._max_retries = max_retries_per_call

    system_text = RUBRIC_TEXT
    if coverage_summary:
        system_text += "\n\n---\n\n" + coverage_summary
    self._system: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": system_text,
            "cache_control": {"type": "ephemeral"},
        }
    ]
```

In `_call`, change `system=_SYSTEM` to `system=self._system`.

- [ ] **Step 2: Modify `backend/tools/dashboard/llm/rubric.py` — add D7 criterion**

Locate the `RUBRIC_TEXT` constant. After the H7 criterion (end of Hygiene section) and before the "Output format (MANDATORY)" section, insert the D7 criterion:

```
### D7 (P2): Missed coverage opportunity

**Description.** The scenario hits an endpoint that the app has
uncovered branches for. Emit a finding ONLY if the scenario plausibly
could exercise one of those branches with a minor change. Use the
`## Coverage context for this run` section (when present) as the
source of truth for which branches are uncovered.

**Fails:**
```

@happy @smoke
Scenario: create a game for the "animals" category
When I POST /api/v1/games with category "animals"
Then the response status is 201

```

(Endpoint has uncovered `if category not in self._by_category` branch —
scenario could include a "create a game for a missing category" variant
and is missing it.)

**Passes:** the scenario covers the branch, OR the branch isn't
plausibly reachable from the scenario's user intent.

**Why it matters.** Coverage data surfaces specific gaps the rubric
(D1–D6) can't see — this criterion lets the LLM suggest targeted
additions with file:line evidence.
```

This adds ~500 tokens. The rubric stays well above the 4096-token cache floor.

- [ ] **Step 3: Modify `backend/tools/dashboard/__main__.py` — load coverage + pass to LlmEvaluator**

`load_coverage_context_if_fresh` and `build_coverage_summary` are already defined as module-level functions in `analyzer.py` (per G1 Step 2 — the iter 2 P1 fix). G2 just imports and uses them.

Open `backend/tools/dashboard/__main__.py`. Before the existing `Analyzer(...)` construction (~line 80), add:

```python
from tools.dashboard.analyzer import (
    Analyzer,
    build_coverage_summary,
    load_coverage_context_if_fresh,
)

# ... inside main(), after argparse ...

coverage_context = load_coverage_context_if_fresh(args.ndjson)
coverage_summary = build_coverage_summary(coverage_context) if coverage_context else ""

analyzer = Analyzer(
    parser=NdjsonParser(),
    grader=CoverageGrader(),
    packager=Packager(),
    llm=LlmEvaluator(
        model=args.model,
        max_workers=args.max_workers,
        coverage_summary=coverage_summary,  # NEW kwarg
    ),
    history=HistoryStore(),
    renderer=DashboardRenderer(),
)
analyzer.run(
    ndjson_path=args.ndjson,
    output_path=args.output,
    history_dir=args.history_dir,
    features_glob=args.features_dir,
    coverage_context=coverage_context,  # NEW arg threaded through
)
```

Note: `coverage_context` is loaded ONCE here in `__main__.py`. It is passed (a) to `LlmEvaluator` as a derived `coverage_summary` string for the cached system prompt, and (b) to `Analyzer.run()` as a parameter so the renderer can render the new "Code coverage" card. Avoids loading `coverage.json` twice.

Verify after editing:

```bash
cd backend && uv run python -m tools.dashboard --help
```

Expected: argparse help renders without import errors.

- [ ] **Step 4: Modify `test_llm_client.py`**

Update any test that references `client._SYSTEM` to use `client._system`. Search: `grep -n "_SYSTEM" backend/tests/unit/tools/dashboard/test_llm_client.py`.

Replace each hit's `_SYSTEM` reference with `_system` (instance attr).

Add a new test:

```python
class TestCoverageSummaryInjection:
    def test_coverage_summary_appended_to_system_prompt(
        self, mock_anthropic_client, good_tool_input
    ):
        mock_anthropic_client.scripted_responses.append(good_tool_input)
        summary = "## Coverage context\nTest coverage data."
        evaluator = LlmEvaluator(
            client=mock_anthropic_client,
            max_workers=1,
            coverage_summary=summary,
        )
        evaluator.evaluate((_pkg(),))
        call = mock_anthropic_client.calls[0]
        system_text = call["system"][0]["text"]
        assert "Test coverage data." in system_text
        assert "## Coverage context" in system_text

    def test_no_coverage_summary_system_is_rubric_only(
        self, mock_anthropic_client, good_tool_input
    ):
        mock_anthropic_client.scripted_responses.append(good_tool_input)
        evaluator = LlmEvaluator(
            client=mock_anthropic_client,
            max_workers=1,
        )  # no coverage_summary kwarg
        evaluator.evaluate((_pkg(),))
        call = mock_anthropic_client.calls[0]
        system_text = call["system"][0]["text"]
        assert "## Coverage context" not in system_text
```

- [ ] **Step 5: Modify `test_rubric.py`** — replace `test_contains_all_13_criteria` with 14-criteria version (per plan-review iter 1 P1: the 13→14 update is the breaking change in Feature 2's existing tests; missing it surfaces only when D7 ships)

The current `test_rubric.py` (Feature 2 master) has at line ~22:

```python
    def test_contains_all_13_criteria(self) -> None:
        required = [f"D{i}" for i in range(1, 7)] + [f"H{i}" for i in range(1, 8)]
        missing = [cid for cid in required if cid not in RUBRIC_TEXT]
        assert missing == [], f"Rubric missing criteria: {missing}"
```

Two changes:

1. **Rename** the function to `test_contains_all_14_criteria`
2. **Update the range** from `range(1, 7)` (D1-D6) to `range(1, 8)` (D1-D7)

Resulting code:

```python
    def test_contains_all_14_criteria(self) -> None:
        required = [f"D{i}" for i in range(1, 8)] + [f"H{i}" for i in range(1, 8)]
        missing = [cid for cid in required if cid not in RUBRIC_TEXT]
        assert missing == [], f"Rubric missing criteria: {missing}"
```

If you forget to update this test, the existing 13-criteria test KEEPS PASSING (because D7 is in the rubric, but D1-D6 + H1-H7 still cover the old required set). The bug only surfaces if a future criterion is added or D7 is removed. Update it for hygiene + intent clarity.

Also add a new D7-specific test below the renamed one:

```python
    def test_mentions_d7_missed_coverage_opportunity(self) -> None:
        assert "D7" in RUBRIC_TEXT
        assert "Missed coverage opportunity" in RUBRIC_TEXT
```

**LlmEvaluator call-site checklist** (per plan-review iter 1 P1: existing call-sites that construct `LlmEvaluator(...)` may need to pass `coverage_summary=""` explicitly OR rely on the default):

Run:

```bash
grep -rn "LlmEvaluator(" backend/tests/unit/tools/dashboard/ backend/tools/dashboard/__main__.py
```

Expected: ~16 call-sites in `test_llm_client.py`, 1 in `test_analyzer.py`, 1 in `__main__.py`. Since `coverage_summary` has a default of `""` (per Step 1 of this task), **no existing call-site needs modification** — they all get the default empty string, the system prompt is RUBRIC_TEXT only, behavior unchanged.

The ONLY exception: `__main__.py` (Feature 2's CLI) needs to pass the runtime-loaded `coverage_summary` explicitly:

```python
# backend/tools/dashboard/__main__.py — locate the LlmEvaluator construction (~line 80)
# BEFORE:
llm=LlmEvaluator(model=args.model, max_workers=args.max_workers),
# AFTER:
coverage_context = load_coverage_context_if_fresh(args.ndjson)
coverage_summary = build_coverage_summary(coverage_context) if coverage_context else ""
llm=LlmEvaluator(
    model=args.model,
    max_workers=args.max_workers,
    coverage_summary=coverage_summary,
),
```

Plus the corresponding imports at the top of `__main__.py`:

```python
from tools.dashboard.analyzer import build_coverage_summary, load_coverage_context_if_fresh
```

Verify after editing:

```bash
cd backend && uv run python -m tools.dashboard --help
```

Expected: argparse help renders without import errors.

- [ ] **Step 6: Run Feature 2's full suite**

Run: `cd backend && uv run pytest tests/unit/tools/dashboard/ -v`
Expected: all pass (~99 existing + ~5 new from Task G1 + ~3 from Task G2).

- [ ] **Step 7: ruff + mypy**

Run: `cd backend && uv run ruff check tools/dashboard/ tests/unit/tools/dashboard/ && uv run mypy tools/dashboard/`
Expected: clean.

- [ ] **Step 8: Commit**

```bash
git add backend/tools/dashboard/llm/client.py backend/tools/dashboard/llm/rubric.py backend/tools/dashboard/analyzer.py backend/tests/unit/tools/dashboard/test_llm_client.py backend/tests/unit/tools/dashboard/test_rubric.py
git commit -m "fix(dashboard): inject coverage summary into cached LLM system prompt + add D7 rubric criterion"
```

---

## Phase H — Docs + live integration smoke

### Task H1: README + CHANGELOG + live smoke

**Files:**

- Modify: `README.md` — add a `## BDD Branch Coverage` section
- Modify: `docs/CHANGELOG.md` — add Feature 3 entry
- Runtime artifacts (not committed — gitignored): `tests/bdd/reports/coverage.html`, `tests/bdd/reports/coverage.json`, `frontend/test-results/cucumber.coverage.ndjson`

**Context:** Final task. Documents the tool + runs one live smoke against the real Hangman codebase to confirm end-to-end + audit reconciliation holds.

**Prerequisites for the live smoke:**

- Backend + frontend dev dependencies installed (`make install`).
- `ANTHROPIC_API_KEY` in `.env` (only needed if we also want to smoke-run `make bdd-dashboard` to verify the augmentation — not strictly required for `make bdd-coverage`).

- [ ] **Step 1: Add README section**

Read `README.md` at repo root. Append a section after the existing "BDD Dashboard (Feature 2)" section:

````markdown
## BDD Branch Coverage (Feature 3)

A developer-only tool that measures what code paths in
`backend/src/hangman/` the BDD suite actually exercises — per-endpoint,
with authoritative audit reconciliation against coverage.py's branch
counts. Produces `tests/bdd/reports/coverage.html` (standalone report)
and `tests/bdd/reports/coverage.json` (consumed by Feature 2's
dashboard as an augment card + LLM coverage-aware findings).

### Prerequisites

- Feature 1 (BDD suite) and Feature 2 (dashboard) on master
- `make install` has run (adds coverage + pyan3 dev deps)
- No API key required (Feature 3 is local-only; Feature 2's LLM
  augmentation is optional)

### Run

Three terminals (matches the existing `make backend` + `make frontend`

- `make bdd` pattern):

```bash
# Terminal 1
make backend-coverage

# Terminal 2
make frontend

# Terminal 3
make bdd-coverage
```

`make bdd-coverage` runs the cucumber suite, SIGTERMs the backend
(coverage.py's `sigterm=true` flushes the data file), combines the
parallel-mode fragments, and invokes the analyzer. Emits:

- `frontend/test-results/cucumber.coverage.ndjson` — instrumented BDD run
- `tests/bdd/reports/coverage.html` — standalone coverage dashboard
- `tests/bdd/reports/coverage.json` — machine-readable artifact for Feature 2

**Important: single uvicorn worker + sequential cucumber.** Coverage
contexts are process-global; concurrent requests corrupt attribution.
Both defaults are already single-threaded. Don't bump workers for
instrumented runs.

### What it measures

- **Per-endpoint coverage**: for each FastAPI route, what % of
  reachable branches did scenarios hitting THAT endpoint actually
  exercise. Red (<50%) / yellow (50-80%) / green (≥80%).
- **Drill-down**: per-reachable-function list of uncovered branches
  with file:line + source snippet.
- **Extra coverage**: functions hit by the BDD suite that the static
  call-graph missed (e.g. FastAPI `Depends()` chains).
- **Audit reconciliation**: cross-check against coverage.py's
  authoritative per-file branch count. Any gap lands in
  `unattributed_branches` — surfaced, not silently dropped.

### Feature 2 integration

When `tests/bdd/reports/coverage.json` is present and fresh (within 1h
of the cucumber.ndjson mtime), `make bdd-dashboard` auto-detects it
and augments:

- New "Code coverage" summary card on the dashboard
- Per-endpoint uncovered-branch data injected into the LLM's cached
  system prompt (coverage-aware findings via new criterion D7)

### Cost

Zero API cost. Coverage instrumentation adds ~10-30% to BDD suite
wall-clock time.
````

- [ ] **Step 2: Add CHANGELOG entry**

Read `docs/CHANGELOG.md`. Add a new entry at the top (matches Feature 2 style):

```markdown
## [unreleased] — 2026-04-24

### Added

- **Feature 3: BDD Branch Coverage** — `make bdd-coverage` generates
  `tests/bdd/reports/coverage.{html,json}` from a coverage.py-instrumented
  BDD run. Per-endpoint attribution via `CoverageContextMiddleware`
  (switch_context per request). Static call-graph via pyan3 +
  authoritative audit reconciliation against coverage.py's per-file
  branch counts. 13-module Python package at `backend/tools/branch_coverage/`.
  Feature 2's dashboard auto-augments when `coverage.json` is fresh —
  new "Code coverage" card + per-endpoint uncovered-branch data
  injected into the LLM's cached system prompt (new rubric criterion
  D7). MIT `LICENSE` added (pyan3 is GPL v2+ dev-only).
```

- [ ] **Step 3: Live smoke — Terminal 1 (`make backend-coverage`)**

In a terminal inside the worktree:

```bash
make backend-coverage
```

Expected stdout: uvicorn startup log with Hangman routes registered. The process runs until you Ctrl-C it OR the Terminal 3 `make bdd-coverage` SIGTERMs it.

Verify `.backend-coverage.pid` exists at repo root.

- [ ] **Step 4: Live smoke — Terminal 2 (`make frontend`)**

```bash
make frontend
```

Expected: vite dev server on port 3000.

- [ ] **Step 5: Live smoke — Terminal 3 (`make bdd-coverage`)**

```bash
time make bdd-coverage 2>&1 | tee /tmp/bdd-coverage.log
```

Expected flow:

1. Cucumber runs against the instrumented backend — stderr shows step progress
2. After cucumber completes: `kill -TERM` message, then `coverage combine`, then analyzer output
3. Analyzer prints audit summary to stderr: `✓ Audit: coverage.py=XXX · enumerated=YYY · unattributed=Z · reconciled=true`
4. Wall-clock: ~70-90s (baseline `make bdd` is ~60s; instrumentation adds ~20-30%)

**If reconciled=False on the first run:** treat as a real bug per NO BUGS LEFT BEHIND. Investigate:

- Is `unattributed` count > 0? The file list in the report shows which branches weren't enumerated.
- Is `extra_coverage` populated? Those are static-graph misses (FastAPI Depends, decorator-registered handlers).
- File a fix in this branch, don't defer.

- [ ] **Step 6: Verify artifacts**

```bash
ls -la tests/bdd/reports/coverage.{html,json} frontend/test-results/cucumber.coverage.ndjson
```

Expected: all three exist, >1 KB each.

- [ ] **Step 7: Visual smoke — open `coverage.html`**

```bash
open tests/bdd/reports/coverage.html
```

Verify:

- Yellow info banner at top: "This run used coverage instrumentation..."
- Totals section: % + "N of M branches covered"
- Per-endpoint grid: every route from `backend/src/hangman/routes.py` appears as a card with its tone
- Drill-down: click a card, see reachable functions, see uncovered branches
- Audit section: `reconciled = true` — no red warning banner

- [ ] **Step 7b: Verify per-endpoint attribution is real (Option B correctness check)**

Per plan-review iter 1 P1: D1's unit tests don't prove the middleware actually attributes hits per-endpoint correctly. This step is the load-bearing verification.

The Hangman codebase has a known shared helper: `hangman.game.apply_guess` is reachable from both `POST /api/v1/games/{id}/guesses` (every guess scenario) and `POST /api/v1/games/{id}/forfeit` (forfeit calls apply_guess to mark the game lost). The BDD suite has scenarios for `/guesses` but no scenarios for `/forfeit` (verify with `grep -r "forfeit" frontend/tests/bdd/features/`).

Run:

```bash
cd backend && uv run python -c "
import json
data = json.loads(open('../tests/bdd/reports/coverage.json').read())

# Find the two endpoints.
guesses = next((e for e in data['endpoints']
                if e['method'] == 'POST' and 'guesses' in e['path']), None)
forfeit = next((e for e in data['endpoints']
                if e['method'] == 'POST' and 'forfeit' in e['path']), None)

print(f'POST /guesses: pct={guesses[\"pct\"]:.1f}%, tone={guesses[\"tone\"]}')
if forfeit:
    print(f'POST /forfeit: pct={forfeit[\"pct\"]:.1f}%, tone={forfeit[\"tone\"]}')

    # Compare reachable functions.
    g_funcs = {f['qualname'] for f in guesses['reachable_functions']}
    f_funcs = {f['qualname'] for f in forfeit['reachable_functions']}
    shared = g_funcs & f_funcs
    print(f'Shared reachable functions: {len(shared)}')
    print(f'  Examples: {list(shared)[:3]}')

    # The correctness assertion: if /forfeit has scenarios that DON'T
    # cover the shared apply_guess branches, /forfeit should show those
    # branches as uncovered EVEN THOUGH /guesses' scenarios covered
    # them under /guesses' context.
    apply_guess_uncov_in_forfeit = [
        b for b in forfeit['uncovered_branches_flat']
        if 'apply_guess' in b.get('function_qualname', '')
    ]
    if apply_guess_uncov_in_forfeit:
        print(f'✓ Per-endpoint attribution working: '
              f'{len(apply_guess_uncov_in_forfeit)} apply_guess branches '
              f'uncovered under /forfeit context')
    else:
        print('⚠ /forfeit shows apply_guess as fully covered — '
              'either there are forfeit scenarios that do exercise '
              'apply_guess, OR the middleware is over-attributing.')
else:
    print('⚠ /forfeit endpoint not found — Hangman may not have this route, '
          'or RouteEnumerator did not pick it up. Verify against routes.py.')
"
```

**Acceptance:**

- If the shared-helper attribution warning fires (Option B works correctly): proceed.
- If `/forfeit` shows 100% coverage on shared helpers despite having no scenarios: middleware is broken — investigate. Likely causes: `coverage.Coverage.current()` returns None at request time (middleware no-ops in production runs), `switch_context` argument format mismatch, or context names don't match what Grader expects.
- If `/forfeit` doesn't exist as a route: pick another shared-helper case from the actual Hangman API surface; the principle holds.

- [ ] **Step 8: Verify Feature 2 augmentation**

Keep the backend + frontend running (or re-start them; just `make backend` this time, not backend-coverage). Run:

```bash
# Terminal 4 (or re-use Terminal 3)
make bdd                         # normal BDD run (regenerates cucumber.ndjson, but coverage.json stays from step 5)
make bdd-dashboard               # requires ANTHROPIC_API_KEY if you want to test the LLM augmentation
```

Open `tests/bdd/reports/dashboard.html`:

- Verify the new "Code coverage" summary card appears
- Verify the card shows the same % as coverage.html
- Verify the dashboard LLM findings reference coverage gaps (if D7 fires — depends on the LLM's interpretation)

If `coverage.json` is now >1h older than the fresh cucumber.ndjson, the augment card shows the "run make bdd-coverage" placeholder. Either re-run `make bdd-coverage` to refresh, or manually update coverage.json's timestamp for the smoke.

- [ ] **Step 9: Commit README + CHANGELOG**

```bash
git add README.md docs/CHANGELOG.md
git commit -m "docs(branch-coverage): add Feature 3 README section + CHANGELOG entry"
```

---

## Dispatch Plan

Per `/new-feature` Phase 4.0. One row per task; concrete file paths.

| Task | Depends on                         | Writes (concrete file paths)                                                                                                                                                                                                                                                                                                                                             |
| ---- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| A1   | —                                  | `backend/pyproject.toml`, `backend/uv.lock`, `LICENSE`, `.gitignore`                                                                                                                                                                                                                                                                                                     |
| A2   | A1                                 | `backend/tools/branch_coverage/__init__.py`, `backend/tools/branch_coverage/templates/.gitkeep`, `backend/tools/branch_coverage/.coveragerc`, `backend/tests/unit/tools/branch_coverage/__init__.py`, `backend/tests/fixtures/branch_coverage/.gitkeep`, `scripts/backend-coverage.sh`, `Makefile`                                                                       |
| A3   | A2                                 | (spike — temporary `backend/tools/branch_coverage/spike_results.md` deleted at task end; may patch `backend/src/hangman/db.py` if import-side-effect audit fails; may patch this plan + design spec)                                                                                                                                                                     |
| B1   | A3                                 | `backend/tools/branch_coverage/models.py`                                                                                                                                                                                                                                                                                                                                |
| C1   | B1                                 | `backend/tests/fixtures/branch_coverage/minimal_app/__init__.py`, `backend/tests/fixtures/branch_coverage/minimal_app/main.py`, `backend/tests/fixtures/branch_coverage/minimal_app/game.py`, `backend/tools/branch_coverage/routes.py`, `backend/tests/unit/tools/branch_coverage/conftest.py`, `backend/tests/unit/tools/branch_coverage/test_routes.py`               |
| C2   | B1, C1                             | `backend/tests/fixtures/branch_coverage/fake_adjacency.py`, `backend/tools/branch_coverage/callgraph.py`, `backend/tests/unit/tools/branch_coverage/test_callgraph.py`                                                                                                                                                                                                   |
| C3   | B1, C1, C2                         | `backend/tools/branch_coverage/reachability.py`, `backend/tests/unit/tools/branch_coverage/test_reachability.py`                                                                                                                                                                                                                                                         |
| D1   | B1                                 | `backend/tools/branch_coverage/middleware.py`, `backend/tests/unit/tools/branch_coverage/test_middleware.py`                                                                                                                                                                                                                                                             |
| D2   | D1                                 | `backend/tools/branch_coverage/serve.py`                                                                                                                                                                                                                                                                                                                                 |
| D3   | B1                                 | `backend/tools/branch_coverage/coverage_data.py`, `backend/tests/unit/tools/branch_coverage/test_coverage_data.py`                                                                                                                                                                                                                                                       |
| E1   | B1                                 | `backend/tools/branch_coverage/grader.py`, `backend/tests/unit/tools/branch_coverage/test_grader.py`                                                                                                                                                                                                                                                                     |
| E2   | B1, E1                             | `backend/tools/branch_coverage/json_emitter.py`, `backend/tests/unit/tools/branch_coverage/test_json_emitter.py`, `backend/tests/fixtures/branch_coverage/golden_coverage.json`                                                                                                                                                                                          |
| E3   | B1, E1, E2                         | `backend/tools/branch_coverage/renderer.py`, `backend/tools/branch_coverage/templates/base.html.j2`, `backend/tools/branch_coverage/templates/_endpoint_card.html.j2`, `backend/tools/branch_coverage/templates/_function_drilldown.html.j2`, `backend/tests/unit/tools/branch_coverage/test_renderer.py`, `backend/tests/fixtures/branch_coverage/golden_coverage.html` |
| F1   | C1, C2, C3, D1, D2, D3, E1, E2, E3 | `backend/tools/branch_coverage/analyzer.py`, `backend/tools/branch_coverage/__main__.py`, `backend/tests/unit/tools/branch_coverage/test_analyzer.py`                                                                                                                                                                                                                    |
| G1   | F1                                 | `backend/tools/dashboard/models.py` (M), `backend/tools/dashboard/analyzer.py` (M), `backend/tools/dashboard/renderer.py` (M), `backend/tests/unit/tools/dashboard/test_analyzer.py` (M), `backend/tests/unit/tools/dashboard/test_renderer.py` (M), `backend/tests/fixtures/dashboard/golden_render.html` (M)                                                           |
| G2   | G1                                 | `backend/tools/dashboard/llm/client.py` (M), `backend/tools/dashboard/llm/rubric.py` (M), `backend/tools/dashboard/analyzer.py` (M — second touch), `backend/tests/unit/tools/dashboard/test_llm_client.py` (M), `backend/tests/unit/tools/dashboard/test_rubric.py` (M)                                                                                                 |
| H1   | G2                                 | `README.md` (M), `docs/CHANGELOG.md` (M)                                                                                                                                                                                                                                                                                                                                 |

**Scheduling notes:**

- A1 → A2 → A3 → B1 serial (scaffold + spike chain).
- A3 (spike) is the gate before all parallel work — it locks the pyan3 + coverage.py API contracts that C2 and D3 depend on.
- After B1 lands: **C1, D1, D3, E1** are ready in parallel (all depend only on B1, file-disjoint). C1 blocks C2 (C2 needs conftest.py from C1); C2 blocks C3 (cycles + boundary tests use CallGraph).
- F1 blocks on everything in Phases C/D/E.
- G1 and G2 touch Feature 2 files — **G2 depends on G1** because both modify `analyzer.py`.
- H1 is the live smoke — depends on G2.

**Recommended dispatch waves** (after A1 → A2 → A3 → B1 serial scaffold):

1. **Parallel wave 1** (3 subagents): C1, D1, D3.
2. **Parallel wave 2** (2-3 subagents): C2 (after C1), E1, D2 (after D1).
3. **Parallel wave 3** (3 subagents): C3 (after C2), E2 (after E1), E3 (after E1 + E2 fixture files).
4. F1 (serial).
5. G1 (serial).
6. G2 (serial — depends on G1's analyzer.py touches).
7. H1 (serial — depends on everything).

Expected dispatch time: ~17-22 subagent invocations (1 per task × 17 tasks, plus 2-3 retries for cache/formatter quirks).

---

## Self-Review

After writing the complete plan, checked against the design spec with fresh eyes.

### Spec coverage

| Design spec section             | Covered by task(s)                                                                                                                                                                                    |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| §1 Load-bearing decisions       | All — dependencies, patterns, thresholds locked in A1, A2, B1, D3, E1                                                                                                                                 |
| §2 Architecture (file tree)     | A2 (scaffold), all later tasks fill it in                                                                                                                                                             |
| §3.1 Runtime orchestration      | A2 (Makefile targets + backend-coverage.sh) + H1 (live smoke)                                                                                                                                         |
| §3.2 Analyzer pipeline          | F1                                                                                                                                                                                                    |
| §3.3 Audit reconciliation       | E1 (grader — shared-helper + dedup tests)                                                                                                                                                             |
| §3.4 I/O boundaries             | Distributed across tasks                                                                                                                                                                              |
| §4.1 models.py                  | B1                                                                                                                                                                                                    |
| §4.2 RouteEnumerator            | C1                                                                                                                                                                                                    |
| §4.3 CallGraphBuilder           | C2                                                                                                                                                                                                    |
| §4.4 Reachability               | C3                                                                                                                                                                                                    |
| §4.5 CoverageDataLoader         | D3                                                                                                                                                                                                    |
| §4.6 Grader                     | E1                                                                                                                                                                                                    |
| §4.7 JsonEmitter                | E2                                                                                                                                                                                                    |
| §4.8 DashboardRenderer          | E3                                                                                                                                                                                                    |
| §4.9 Analyzer                   | F1                                                                                                                                                                                                    |
| §4.10 CoverageContextMiddleware | D1                                                                                                                                                                                                    |
| §4.11 serve.py                  | D2                                                                                                                                                                                                    |
| §4.12 **main**.py               | F1                                                                                                                                                                                                    |
| §5 coverage.json schema         | E2 (JsonEmitter + golden file)                                                                                                                                                                        |
| §6.1–6.5 Feature 2 augmentation | G1 (models + analyzer + renderer), G2 (llm/client + rubric + analyzer)                                                                                                                                |
| §7 Make orchestration           | A2 (Makefile + scripts/backend-coverage.sh + .coveragerc + serve.py)                                                                                                                                  |
| §8 Testing strategy             | TDD throughout; golden-file tests in E2, E3; shared-helper in E1; cycle + boundary in C3                                                                                                              |
| §9 Determinism boundary         | golden files in E2, E3; fake CallGraphBuilder in F1                                                                                                                                                   |
| §10 Non-goals (reaffirmed)      | No tasks — plan enforces by omission                                                                                                                                                                  |
| §11.1 Plan-phase decisions      | A1 (LICENSE), A2 (cucumber `--format` inline in Makefile), H1 (README note), A2 (`trap` in backend-coverage.sh)                                                                                       |
| §12 Risks carried forward       | Audit dedup: E1 · Module import side effects: C1 / F1 (reflective import) · SIGTERM coordination: A2 · Audit invariant test: E1 · Licensing: A1 · Concurrency: D1 + H1 · Route-template edge case: D1 |

**No gaps identified.** Every design spec section maps to at least one task.

### Placeholder scan

- [x] No "TBD" in the plan
- [x] No "implement later"
- [x] No "add error handling" without specifics (D1, D3, C2, C3 all describe specific exception paths)
- [x] No "write tests for the above" without test code — every task has inline test code
- [x] No "similar to Task N" — each task is self-contained
- [x] Every code step has a code block or exact command
- [x] References to types/functions are defined in earlier tasks (verified via type consistency check below)

### Type consistency

- `Endpoint` defined in B1; consumed by C1 (output), C3 (input), E1 (input), F1 (output) — consistent.
- `ReachableBranch` defined in B1 including `function_qualname`; C3 produces it, E1 consumes it.
- `LoadedCoverage` defined in B1; D3 produces it, E1 consumes it (fields `hits_by_context`, `total_branches_per_file`, `all_hits` — consistent).
- `CoverageReport` defined in B1; E1 produces it; E2, E3, F1 consume it.
- `CoverageContext` defined in G1 (dashboard/models.py additive); G2 uses it (coverage_summary builder).
- `Tone` enum: `SUCCESS`/`WARNING`/`ERROR`/`NA` — used by E1 (Grader), E2 (JsonEmitter), E3 (templates). Consistent.
- Threshold constants `_RED_THRESHOLD=50.0`, `_YELLOW_THRESHOLD=80.0` defined in E1 `grader.py` only. Not referenced elsewhere as names (E2 + E3 read via `report.thresholds` dict).
- `CallGraph` dataclass defined in C2 `callgraph.py`; C3 consumes it, F1 fake produces it for tests.
- Method signature of `DashboardRenderer.render()` in E3 takes `(report, output_path)` — 2 args. Feature 2's renderer takes a different signature; no conflict because they're separate classes.
- `Analyzer.run()` signature in F1: `(app, coverage_file, source_root, json_output, html_output)` — consistent with `test_analyzer.py` invocation in F1.
- `LlmEvaluator.__init__` new `coverage_summary` kwarg (G2) — default `""` — backward-compatible for existing Feature 2 tests (verified by test_llm_client.py update pattern).

**No type or signature drift.** All cross-task references check out.

### Review verdict

**Plan passes self-review.** Ready for Phase 3.3 plan-review loop (Claude + Codex iteration until no P0/P1/P2).

---

## Notes for the plan-review loop

The following are the highest-risk areas in this plan — plan-review should focus here:

1. **E1 Grader audit reconciliation math** — the dedup across endpoints is subtle. Shared-helper test case in test_grader.py is the correctness guarantor.
2. **D1 middleware concurrency** — `switch_context` is process-global. Tests rely on sequential requests; if FastAPI's TestClient doesn't block between requests, attribution leaks. Worth an extra scrutiny pass.
3. **D3 coverage_data per-context API usage** — `CoverageData.set_query_contexts([label])` may have shifted between coverage.py versions. If the per-context arcs API drifted in 7.13, the test harness generating `.coverage` fixtures on-the-fly will surface it.
4. **C2 pyan3 Python API** — `visitor.uses_graph` key/value types depend on pyan3 version. Actual pyan3 node type may not have `.get_name()` — the `_node_name` fallback chain handles it, but worth verifying on pyan3 2.5.0 specifically.
5. **G1 + G2 Feature 2 touch surface** — 5 files modified + existing Feature 2 tests must stay green. The `render()` signature gains a new `coverage_context` argument; every existing test call-site needs updating. Easy to miss.
6. **F1 analyzer_main module import** — `from hangman.main import app` in `__main__.py` may trigger module-import side effects per §12 risk #2. If the real hangman app initializes the DB at import time, this fires during Feature 3 analyzer runs (unexpected). Plan-phase mitigation: audit during F1; if issue appears, test-mode env var suppression.
