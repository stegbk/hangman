# Design: BDD Branch Coverage

**Date:** 2026-04-24
**Version:** 1.0
**Status:** Draft (awaiting KC review)
**PRD:** `docs/prds/bdd-branch-coverage.md` v1.0
**Research brief:** `docs/research/2026-04-24-bdd-branch-coverage.md`

Technical design for **Feature 3 of the three-feature BDD plan** — a Python analyzer that replaces Feature 2's regex-based endpoint scrape with authoritative route-table-driven branch coverage. Pipeline:

1. Enumerate routes reflectively via `from hangman.main import app; app.routes`
2. Build a static call-graph of `backend/src/hangman/` using `pyan3` (subprocess)
3. Walk reachability from each route handler → enumerate reachable functions + branches
4. Run the BDD suite under `coverage run --branch --parallel-mode -m uvicorn ...`
5. Merge static reachability + dynamic hit set → per-endpoint percentages
6. Reconcile against `coverage.py`'s authoritative branch count (self-audit)
7. Emit `coverage.json` (single source of truth) + `coverage.html` (standalone Jinja2 report)
8. Feature 2's dashboard reads `coverage.json` (when fresh) to augment with a "Code coverage" card + inject a coverage summary into the LLM's cached system prompt

No gates. No hooks. Opt-in via `make bdd-coverage`. Developer-only tool.

---

## 1. Summary of load-bearing decisions

All resolved during PRD discussion + research + brainstorming:

- **Static call-graph tool:** `pyan3` v2.5+. `pycg` archived 2023-11, off the table.
- **Dynamic coverage:** `coverage.py >= 7.13, < 7.14` (pinned directly; don't rely on pytest-cov's transitive bound). `--branch` mode, `--parallel-mode` for subprocess workers, `sigterm=true` config for clean SIGTERM flushes.
- **Route enumeration:** reflective `from hangman.main import app`; walk `app.routes`. AST-parsing `routes.py` rejected — reflective handles `prefix=` and `app.include_router(...)` for free.
- **Output location:** `backend/tools/branch_coverage/` (sibling to `backend/tools/dashboard/` from Feature 2).
- **Make target pattern:** two targets matching Feature 1's shape — `make backend-coverage` (Terminal 1, runs wrapped uvicorn) + `make bdd-coverage` (Terminal 3, runs cucumber + analyzer).
- **JSON schema scope:** full single source of truth (~30-60KB). Feature 2 reads subsets; standalone HTML reads the same file.
- **Per-endpoint percentage formula:** branch-weighted (`sum(covered) / sum(total)` across reachable functions). Function-averaged rejected as math-distorted.
- **Thresholds:** hardcoded red/yellow/green at `< 50% / 50-80% / ≥ 80%`.
- **Feature 2 augmentation:** auto-detect `coverage.json` if fresh (within 1h of cucumber.ndjson mtime); inject coverage summary into the cached system prompt alongside `RUBRIC_TEXT`.
- **Audit reconciliation:** cross-check our enumeration against `coverage.py`'s authoritative per-file branch count. Any gap lands in `unattributed_branches` — surfaced, not silently dropped.

---

## 2. Architecture

```
backend/
├── pyproject.toml                          [M] add coverage>=7.13,<7.14 + pyan3>=2.5,<3 to dependency-groups.dev
└── tools/
    └── branch_coverage/                    [N]
        ├── __init__.py
        ├── __main__.py                     CLI (argparse; ~50 LOC)
        ├── analyzer.py                     Analyzer orchestrator
        ├── models.py                       @dataclass: Endpoint, ReachableBranch, FunctionCoverage,
                                                         CoveragePerEndpoint, AuditReport, CoverageReport
        ├── routes.py                       RouteEnumerator: reflective app.routes walker
        ├── callgraph.py                    CallGraphBuilder: pyan3 subprocess wrapper + graph parser
        ├── reachability.py                 Reachability: BFS from each handler through graph
        ├── coverage_data.py                CoverageDataLoader: coverage.py Python API reader
        ├── grader.py                       Grader: merge + pct + thresholds + audit reconciliation
        ├── json_emitter.py                 JsonEmitter: CoverageReport → coverage.json
        ├── renderer.py                     DashboardRenderer: Jinja2 → coverage.html
        └── templates/
            ├── base.html.j2                Shell + summary cards + per-endpoint grid + audit section
            ├── _endpoint_card.html.j2      Per-endpoint card (tone class: success/warning/error)
            └── _function_drilldown.html.j2 Function tree with uncovered-branch lists

backend/tests/
├── unit/tools/branch_coverage/             [N]
│   ├── __init__.py
│   ├── conftest.py                         Shared fixtures (minimal.coverage, pyan3_output, minimal_app)
│   ├── test_routes.py
│   ├── test_callgraph.py
│   ├── test_reachability.py
│   ├── test_coverage_data.py
│   ├── test_grader.py
│   ├── test_json_emitter.py                Golden-file against fixtures/golden_coverage.json
│   ├── test_renderer.py                    Golden-file against fixtures/golden_coverage.html
│   └── test_analyzer.py                    End-to-end with mocked CallGraphBuilder
└── fixtures/branch_coverage/               [N]
    ├── minimal.coverage                    Tiny binary .coverage file (generated once, committed)
    ├── fake_adjacency.py                   Hand-built CallGraph fixture (Python, not DOT)
    ├── golden_coverage.json
    ├── golden_coverage.html
    └── minimal_app/
        ├── __init__.py
        ├── main.py                         Tiny FastAPI app (1 router, 2 routes)
        └── game.py                         1 function with 3 branches

backend/tools/dashboard/                    [M] Feature 2 augmentation (5 files modified)
├── analyzer.py                             [M] check for coverage.json at run start
├── packager.py                             (unchanged — coverage goes into cached system, not packages)
├── llm/client.py                           [M] LlmEvaluator accepts coverage_summary param; _SYSTEM derived
├── llm/rubric.py                           [M] add criterion D7 — Missed coverage opportunity
├── renderer.py                             [M] new "Code coverage" summary card (or placeholder)
├── models.py                               [M] add CoverageContext dataclass

Root:
├── Makefile                                [M] + `backend-coverage` + `bdd-coverage` targets
├── scripts/backend-coverage.sh             [N] PID-tracking exec wrapper for coverage-under-uvicorn
├── frontend/package.json                   [M] + "bdd:coverage" script with distinct output path
└── .gitignore                              [M] + `.backend-coverage.pid`, `.coverage`, `.coverage.*`
```

### Dependency graph (module-level)

```
__main__ → Analyzer → {RouteEnumerator, CallGraphBuilder, Reachability,
                       CoverageDataLoader, Grader, JsonEmitter, DashboardRenderer}
                                ↓
                           models.py (leaf)

templates/ consumed by DashboardRenderer only
```

- `models.py` has zero imports from other tool modules — leaf-level.
- `analyzer.py` is the only orchestrator. Each other module has one responsibility.
- Feature 2's code imports nothing from Feature 3. Coupling is purely via the `coverage.json` file on disk.

---

## 3. Pipeline — data flow + audit reconciliation

### 3.1 Runtime orchestration (`make bdd-coverage` wall-clock)

```
Terminal 1 (foreground):
  make backend-coverage
  └→ scripts/backend-coverage.sh
       ├ writes $$ to .backend-coverage.pid
       └ exec uv run coverage run --branch --parallel-mode --source=src/hangman \
              -m uvicorn hangman.main:app --host 127.0.0.1 --port $PORT

Terminal 2 (foreground):
  make frontend                                       (unchanged from Feature 1)

Terminal 3 (one-shot):
  make bdd-coverage
  ├ 1. cd frontend && pnpm exec cucumber-js \
                       --format message:test-results/cucumber.coverage.ndjson
  ├ 2. PID=$(cat .backend-coverage.pid); kill -TERM "$PID" 2>/dev/null
  │      (coverage.py 7.13's sigterm=true handler flushes .coverage.* fragments)
  ├ 3. rm .backend-coverage.pid
  ├ 4. sleep 2   (grace period for fragment writes)
  ├ 5. cd backend && uv run coverage combine
  │      (merges .coverage.<host>.<pid>.* → single .coverage)
  └ 6. cd backend && uv run python -m tools.branch_coverage
         → writes coverage.json + coverage.html
```

After step 6 Terminal 1 has exited. Dev re-runs `make backend-coverage` for the next iteration. Opt-in nature + infrequent use makes this acceptable.

### 3.2 Analyzer pipeline (step 6)

```
                            ┌────────────────────────────┐
                            │ hangman.main.app (import)  │
                            └─────────────┬──────────────┘
                                          │
                            ┌─────────────▼──────────────┐
                            │ RouteEnumerator.enumerate()│
                            │ → list[Endpoint]           │
                            └─────────────┬──────────────┘
                                          │
      ┌───────────────────────────────────┼──────────────────────────────────┐
      │                                   │                                  │
  ┌───▼──────────────┐          ┌─────────▼────────┐                ┌────────▼───────────┐
  │ CallGraphBuilder │          │  Reachability    │                │ CoverageDataLoader │
  │ pyan3 subprocess │          │  BFS from each   │                │ load .coverage via │
  │ → CallGraph      │          │  handler         │                │ coverage.py API    │
  │                  │          │ → {endpoint:     │                │ → {branch_id: int} │
  │                  │          │   [ReachBranch]} │                │   (hit counts)     │
  └────────┬─────────┘          └─────────┬────────┘                └────────┬───────────┘
           │                              │                                  │
           └──────────────┬───────────────┘                                  │
                          │                                                  │
                    ┌─────▼──────┐                                           │
                    │ Grader     │ ◄─────────────────────────────────────────┘
                    │ merge +    │
                    │ pct +      │       Also: loader exposes
                    │ audit      │       coverage.py's authoritative
                    │            │       total_branches_per_file for
                    │            │       reconciliation
                    └─────┬──────┘
                          │
                          │ CoverageReport
                          │ (includes audit block)
                          │
            ┌─────────────┴──────────────┐
            │                            │
    ┌───────▼────────┐           ┌───────▼────────┐
    │ JsonEmitter    │           │ DashboardRender│
    │ coverage.json  │           │ coverage.html  │
    └────────────────┘           └────────────────┘
```

Both output files emit atomically. If Grader's reconciliation check fails (`reconciled: false`), analyzer logs a loud error to stderr but still emits both artifacts — dev sees the audit warning in the report rather than a blank failure.

### 3.3 Audit reconciliation (correctness invariant)

Failure mode: a branch that both pyan3 misses AND the BDD run doesn't exercise would be silently absent. Coverage.json would over-report.

Defense: `coverage.py` instruments at bytecode level and knows the total branch count per file authoritatively, independent of our static graph. The Grader cross-checks:

```
# Per file, coverage.py tells us:
total_branches_in_file(f)  →  authoritative count (a set of unique branch_id's)

# Our enumeration (DEDUPED — a branch reachable from N endpoints is
# counted once, not N times):
enumerated_in_file(f) = distinct(file, branch_id) tuples across:
    {branches linked to any endpoint in file f}
    ∪ {extra_coverage branches in file f}
    ∪ {unattributed branches in file f}

# Invariant:
assert total_branches_in_file(f) == |enumerated_in_file(f)|,
       for every file in backend/src/hangman/
```

**Dedup is essential.** A shared helper function reachable from two endpoints appears in both endpoints' `reachable_functions` lists. For _per-endpoint_ coverage percentage, that's correct — each endpoint legitimately reports "of what I reach, this much was exercised." For the _audit_ reconciliation, we must dedupe: count each `(file, branch_id)` tuple once.

The Grader maintains two views:

- Per-endpoint: branches stay duplicated across endpoints (legitimate shared coverage).
- Audit/totals: distinct set of `(file, branch_id)` tuples across the whole graph-walked enumeration.

Test coverage mandate (for the plan): `test_grader.py` MUST include a fixture where a shared helper is reached from two endpoints, asserting (a) both endpoints report the helper's branches in their percentages, and (b) the audit `enumerated_in_file` count matches coverage.py's authoritative total (no double-counting).

If the invariant holds, `CoverageReport.audit.reconciled = True`. If any file mismatches, the delta goes into `unattributed_branches` (the "third bucket" — neither linked to an endpoint nor hit by tests), and `reconciled = False` triggers a stderr warning plus a red audit banner on `coverage.html`.

`totals` calculation treats **unattributed branches as uncovered** (penalty for completeness). So the headline percentage never silently over-reports; unknown branches drag the number down until someone investigates them.

### 3.4 I/O boundaries

| Boundary                          | Module                                                                                                 | Side                                          |
| --------------------------------- | ------------------------------------------------------------------------------------------------------ | --------------------------------------------- |
| Reads `hangman.main`              | `routes.py`                                                                                            | Input (reflective import — see risk #2 below) |
| Reads `backend/src/hangman/**.py` | `callgraph.py` (via `pyan.analyzer.CallGraphVisitor` in-process) + `renderer.py` (for source snippets) | Input                                         |
| In-process pyan3 analysis         | `callgraph.py`                                                                                         | CPU (no subprocess; pyan3 Python API)         |
| Reads `.coverage` file            | `coverage_data.py`                                                                                     | Input                                         |
| Writes `coverage.json`            | `json_emitter.py`                                                                                      | Output                                        |
| Writes `coverage.html`            | `renderer.py`                                                                                          | Output                                        |
| SIGTERM backend process           | `Makefile` recipe                                                                                      | Side-effect (outside the Python package)      |

All analyzer internals are pure data transforms. Every external dependency is clearly at the edges.

---

## 4. Module specs

### 4.1 `models.py`

Frozen dataclasses. Leaf-level.

```python
from dataclasses import dataclass
from enum import Enum


class Tone(Enum):
    SUCCESS = "success"   # ≥ 80%
    WARNING = "warning"   # 50% to < 80%
    ERROR = "error"       # < 50%
    NA = "na"             # 0 branches (degenerate)


@dataclass(frozen=True)
class Endpoint:
    method: str                       # "GET" | "POST" | ...
    path: str                         # "/api/v1/games/{id}"
    handler_qualname: str             # "hangman.routes.create_game"


@dataclass(frozen=True)
class ReachableBranch:
    file: str                         # "backend/src/hangman/game.py"
    line: int
    branch_id: str                    # coverage.py's branch arc, e.g. "42->45"
    condition_text: str               # source snippet of the if/match condition
    not_taken_to_line: int            # the arc's destination line; negative = exit
    function_qualname: str            # "hangman.words.pick_random" (owner; used by uncovered_branches_flat)


@dataclass(frozen=True)
class FunctionCoverage:
    file: str
    qualname: str                     # "hangman.words.pick_random"
    total_branches: int
    covered_branches: int
    pct: float                        # [0.0, 100.0]; N/A rendered as 0.0 if total_branches == 0
    reached: bool                     # did coverage.py see any hit on this function
    uncovered_branches: tuple[ReachableBranch, ...]


@dataclass(frozen=True)
class CoveragePerEndpoint:
    endpoint: Endpoint
    reachable_functions: tuple[FunctionCoverage, ...]
    total_branches: int               # sum across reachable_functions
    covered_branches: int
    pct: float
    tone: Tone

    @property
    def uncovered_branches_flat(self) -> tuple[ReachableBranch, ...]:
        """Flattened view derived from reachable_functions. Used by
        JsonEmitter to produce the `uncovered_branches_flat` JSON field
        (which Feature 2's LLM packager consumes). Not stored — derived
        at emit time — to avoid redundant state in the dataclass."""
        return tuple(
            b
            for fc in self.reachable_functions
            for b in fc.uncovered_branches
        )


@dataclass(frozen=True)
class ExtraCoverage:
    """Functions hit by the BDD run that the static graph didn't link to any endpoint."""
    file: str
    qualname: str
    reason: str                       # e.g. "Called via FastAPI Depends() — pyan3 missed"


@dataclass(frozen=True)
class UnattributedBranch:
    """Branch in backend/src/hangman/ that neither static graph linked nor coverage.py hit."""
    file: str
    line: int
    branch_id: str
    reason: str                       # human-readable


@dataclass(frozen=True)
class AuditReport:
    total_branches_per_coverage_py: int
    total_branches_enumerated_via_reachability: int
    extra_coverage_branches: int
    unattributed_branches: tuple[UnattributedBranch, ...]
    reconciled: bool                  # True iff the invariant holds


@dataclass(frozen=True)
class Totals:
    total_branches: int               # coverage.py's authoritative count
    covered_branches: int
    pct: float
    tone: Tone


@dataclass(frozen=True)
class CoverageReport:
    version: int                      # schema version (1 for MVP)
    timestamp: str                    # ISO 8601; derived from cucumber.coverage.ndjson's meta.startedAt
    cucumber_ndjson: str              # relative path to the NDJSON this report was built against
    instrumented: bool                # always True for Feature 3 output
    thresholds: dict[str, float]      # {"red": 50.0, "yellow": 80.0}
    totals: Totals
    endpoints: tuple[CoveragePerEndpoint, ...]
    extra_coverage: tuple[ExtraCoverage, ...]
    audit: AuditReport
```

### 4.2 `routes.py` — `RouteEnumerator`

```python
class RouteEnumerator:
    def enumerate(self) -> tuple[Endpoint, ...]:
        """Import hangman.main and list FastAPI routes from app.routes.

        Reflective; no AST-parsing. `app.include_router(prefix=...)` and
        `add_api_route` are handled natively.

        Filters to routes with non-None `methods` (excludes WebSocket,
        HEAD-only, etc.); future: broaden if needed.
        """
```

- Returns `Endpoint` tuples sorted by `(path, method)` for deterministic output.
- Handler qualname extracted from `route.endpoint.__module__ + "." + route.endpoint.__qualname__`.
- If importing `hangman.main` raises (e.g., DB init failure), surface the exception — caller handles.

### 4.3 `callgraph.py` — `CallGraphBuilder`

```python
class CallGraphBuilder:
    def build(self, source_root: Path) -> CallGraph:
        """Uses pyan3's programmatic API (CallGraphVisitor) to analyze
        backend/src/hangman/**/*.py. Returns an adjacency map keyed by
        qualified name.
        """
```

**Implementation via pyan3's Python API** (per research brief — pyan3 2.5.0 exposes `pyan.analyzer.CallGraphVisitor(["pkg/mod.py", ...])` + `.get_node(qualname)` / callgraph node traversal). Subprocess + DOT-parsing rejected: hand-written DOT parsers are bug magnets, and we lose programmatic access to node metadata.

```python
from pyan.analyzer import CallGraphVisitor

def build(self, source_root: Path) -> CallGraph:
    files = list(source_root.rglob("*.py"))
    visitor = CallGraphVisitor([str(f) for f in files])
    # visitor.uses_graph: dict[Node, set[Node]] — "X uses Y" = X calls Y
    adjacency: dict[str, frozenset[str]] = {}
    for caller, callees in visitor.uses_graph.items():
        adjacency[caller.get_name()] = frozenset(c.get_name() for c in callees)
    return CallGraph(adjacency=adjacency)
```

- Runs in-process — no subprocess, no DOT parsing, no timeout handling needed.
- Returns an adjacency map: `dict[qualname, frozenset[qualname]]` — callee names reachable in one step.
- **Degraded path:** if `CallGraphVisitor` raises (pyan3 API drift, unparseable source, bug), catch broad `Exception`, log error with the file that tripped it, return an empty graph. Reachability then reports 0 reachable functions per endpoint; audit reconciliation surfaces everything as `unattributed`. Tool still emits a valid report; dev sees the degraded state and can investigate pyan3.
- **API drift risk:** pyan3 was just-revived (2026-02); its internal API may change. Plan-phase task: integration test smoke run pyan3 against the real Hangman codebase; pin `pyan3>=2.5,<3` (major-version bound). Plan's H-equivalent live run catches breakage.

### 4.4 `reachability.py` — `Reachability`

```python
class Reachability:
    def compute(
        self,
        endpoints: tuple[Endpoint, ...],
        graph: CallGraph,
        source_root: Path,
    ) -> dict[Endpoint, list[ReachableBranch]]:
        """BFS from each endpoint's handler through `graph`; for each
        reachable function, read its source file and enumerate branches
        (file:line pairs + condition text + arc targets).
        """
```

- Per endpoint: BFS on `graph`, collecting all reachable qualnames.
- Filter to qualnames whose source file lives under `source_root` (boundary from PRD: `backend/src/hangman/` only; stop at external imports).
- For each reachable function, use `ast.parse` on the function's source file + positional info to enumerate branches (if/elif/else, try/except, ternary, comprehension predicates).
- Each branch becomes a `ReachableBranch` with `file`, `line`, `branch_id` (`coverage.py`-compatible `"line->target"` arc), `condition_text` (source snippet).
- Cycles: BFS with visited set; cycles don't loop.
- Unreachable handlers (e.g. handler not in graph due to decorator weirdness): log warning, return empty branch list for that endpoint.

### 4.5 `coverage_data.py` — `CoverageDataLoader`

```python
class CoverageDataLoader:
    def load(self, coverage_file: Path) -> CoverageData:
        """Use coverage.py's Python API (coverage.Coverage + CoverageData)
        to read the .coverage file. Returns:
          - hit_branches: frozenset[tuple[file, branch_id]]  # what ran
          - total_branches_per_file: dict[file, int]         # authoritative
        """
```

- Uses `coverage.Coverage(data_file=coverage_file)` + `.load()` + `.get_data()` → `CoverageData`.
- `CoverageData.arcs(file)` returns the branch-arc tuples hit.
- Authoritative total per file: `CoverageData.measured_files()` + per-file arc set via `coverage.Analyzer`.
- Handles negative target lines (`[12, -12]` = function-exit arc) without crashing; these are filtered from the ReachableBranch enumeration (they aren't "branches" in the user-facing sense, they're exit arcs).
- If the `.coverage` file is missing/corrupt, raise `CoverageDataLoadError` with a specific hint ("Run `make bdd-coverage` first; is `.backend-coverage.pid` stale?"). Caller (analyzer) surfaces to stderr.

### 4.6 `grader.py` — `Grader`

```python
class Grader:
    def grade(
        self,
        reachability: dict[Endpoint, list[ReachableBranch]],
        hits: CoverageData,
    ) -> CoverageReport:
        """Merge reachability + hits. Compute per-endpoint pct + tone.
        Build the audit block by cross-checking enumerated vs
        coverage.py's authoritative per-file totals.
        """
```

Pipeline within Grader:

1. Flatten `reachability` values → master set of enumerated branches (`{(file, line, branch_id): endpoints[]}`)
2. Intersect with `hits.hit_branches` → covered branches per endpoint
3. Compute `CoveragePerEndpoint` per endpoint (branch-weighted pct, tone via thresholds)
4. Extract `ExtraCoverage`: files hit but no endpoint-reaching function contains that line
5. Audit reconciliation:
   - For each file in `backend/src/hangman/`:
     - `a = hits.total_branches_per_file[file]` (authoritative)
     - `b = count(enumerated branches in file)` (includes all endpoints + extra_coverage)
     - Delta `a - b` = unattributed count for that file
   - Enumerate the unattributed arcs from `hits` that aren't in our enumerated set
   - Set `audit.reconciled = all(deltas are accounted for)`
6. Compute `totals`: uses coverage.py's authoritative total (not our enumeration); covered = coverage.py's total hits in `backend/src/hangman/`

Thresholds hardcoded as `_RED_THRESHOLD = 50.0`, `_YELLOW_THRESHOLD = 80.0` module constants.

### 4.7 `json_emitter.py` — `JsonEmitter`

```python
class JsonEmitter:
    def emit(self, report: CoverageReport, output_path: Path) -> None:
        """Serialize CoverageReport → coverage.json (pretty-printed, stable
        field order). Deterministic output for golden-file tests.
        """
```

- Uses `dataclasses.asdict` + stable sort for list fields (already deterministic from upstream).
- Enum serialization: `Tone.SUCCESS` → `"success"`.
- Tuple → list (JSON has no tuple).
- `indent=2` for human-readable output + stable golden files.

### 4.8 `renderer.py` — `DashboardRenderer`

```python
class DashboardRenderer:
    def render(self, report: CoverageReport, output_path: Path) -> None:
        """Jinja2 (PackageLoader + select_autoescape(['html','j2'])) →
        coverage.html. Reads CoverageReport in memory, no JSON round-trip.
        """
```

Template structure (matches Feature 2's pattern):

- `base.html.j2` — shell with CSS (dark theme matching Feature 2), summary cards (total pct + totals), per-endpoint grid, extra_coverage section, audit section (banner if `reconciled == False`)
- `_endpoint_card.html.j2` — per-endpoint card with tone class, click-to-expand function tree
- `_function_drilldown.html.j2` — per-function breakdown with uncovered branch list (file:line + condition snippet)

Autoescape on (source code snippets in `condition_text` are HTML-escaped by default; prevents template injection from exotic Python source).

### 4.9 `analyzer.py` — `Analyzer`

```python
class Analyzer:
    def __init__(self, routes, callgraph, reachability, coverage_data,
                 grader, json_emitter, renderer):
        ...

    def run(self, coverage_file: Path, source_root: Path,
            json_output: Path, html_output: Path) -> None:
        endpoints = self.routes.enumerate()
        graph = self.callgraph.build(source_root)
        reach = self.reachability.compute(endpoints, graph, source_root)
        hits = self.coverage_data.load(coverage_file)
        report = self.grader.grade(reach, hits)
        self.json_emitter.emit(report, json_output)
        self.renderer.render(report, html_output)
        self._report_audit(report.audit)  # stderr summary
```

Dependency injection — lets `test_analyzer.py` swap components with test doubles.

### 4.10 `__main__.py` — CLI

Argparse CLI with defaults anchored off `Path(__file__).resolve().parents[3]` (repo root):

- `--coverage-file` default: `<repo>/backend/.coverage`
- `--source-root` default: `<repo>/backend/src/hangman`
- `--json-output` default: `<repo>/tests/bdd/reports/coverage.json`
- `--html-output` default: `<repo>/tests/bdd/reports/coverage.html`

No API key / env check (Feature 3 is local-only). Exit code 0 on success; 2 on CoverageDataLoadError; 3 on pyan3 build failure (still writes a degraded report first); 1 on unexpected errors.

---

## 5. `coverage.json` schema (exhaustive)

**Version 1 schema.** Canonical example in `docs/prds/bdd-branch-coverage.md` §6 Data Models + Section 2 of this doc. Full listing with every field documented:

```json
{
  "version": 1,
  "timestamp": "2026-04-24T20:00:00Z",
  "cucumber_ndjson": "frontend/test-results/cucumber.coverage.ndjson",
  "instrumented": true,
  "thresholds": { "red": 50.0, "yellow": 80.0 },
  "totals": {
    "total_branches": 142,
    "covered_branches": 98,
    "pct": 69.01,
    "tone": "warning"
  },
  "endpoints": [
    {
      "method": "POST",
      "path": "/api/v1/games",
      "handler_qualname": "hangman.routes.create_game",
      "total_branches": 12,
      "covered_branches": 10,
      "pct": 83.33,
      "tone": "success",
      "reachable_functions": [
        {
          "file": "backend/src/hangman/game.py",
          "qualname": "hangman.game.new_game",
          "total_branches": 4,
          "covered_branches": 4,
          "pct": 100.0,
          "reached": true,
          "uncovered_branches": []
        },
        {
          "file": "backend/src/hangman/words.py",
          "qualname": "hangman.words.pick_random",
          "total_branches": 3,
          "covered_branches": 2,
          "pct": 66.67,
          "reached": true,
          "uncovered_branches": [
            {
              "file": "backend/src/hangman/words.py",
              "line": 42,
              "branch_id": "42->45",
              "condition_text": "if category not in self._by_category:",
              "not_taken_to_line": 45
            }
          ]
        }
      ],
      "uncovered_branches_flat": [
        {
          "file": "backend/src/hangman/words.py",
          "line": 42,
          "branch_id": "42->45",
          "condition_text": "if category not in self._by_category:",
          "not_taken_to_line": 45,
          "function_qualname": "hangman.words.pick_random"
        }
      ]
    }
  ],
  "extra_coverage": [
    {
      "file": "backend/src/hangman/db.py",
      "qualname": "hangman.db.get_session",
      "reason": "Not linked to any endpoint by static call-graph (likely via FastAPI Depends)"
    }
  ],
  "audit": {
    "total_branches_per_coverage_py": 142,
    "total_branches_enumerated_via_reachability": 130,
    "extra_coverage_branches": 4,
    "unattributed_branches": [
      {
        "file": "backend/src/hangman/game.py",
        "line": 87,
        "branch_id": "87->90",
        "reason": "Not linked to any endpoint by static graph; not hit by BDD run"
      }
    ],
    "reconciled": true
  }
}
```

**Field contract — what Feature 2 reads:**

| Field                                          | Feature 2's use                                                                   |
| ---------------------------------------------- | --------------------------------------------------------------------------------- |
| `timestamp`                                    | Staleness check against `cucumber.ndjson.meta.startedAt`                          |
| `totals`                                       | Populates the new "Code coverage" summary card                                    |
| `endpoints[].method`, `.path`, `.pct`, `.tone` | Additional detail on the summary card, drill-down link text                       |
| `endpoints[].uncovered_branches_flat`          | Injected into the cached system prompt (LLM sees per-endpoint uncovered branches) |
| `audit.reconciled`                             | If `false`, render a warning banner next to the Code coverage card                |

All other fields are consumed only by `coverage.html` for drill-down rendering.

---

## 6. Feature 2 integration mechanics

5 files in `backend/tools/dashboard/` are modified. Existing 99 tests must continue passing; new tests are additive.

### 6.1 `analyzer.py`

At `run()` start:

```python
coverage_context = self._load_coverage_if_fresh(cucumber_ndjson_path)
# coverage_context is None OR a CoverageContext dataclass.
# Passed to LlmEvaluator and DashboardRenderer; both tolerate None.
```

`_load_coverage_if_fresh` checks:

- Does `tests/bdd/reports/coverage.json` exist?
- Is its `timestamp` within 1 hour of cucumber.ndjson's `meta.startedAt`?
- If yes to both: parse and return `CoverageContext`
- If no: log info-level, return None

### 6.2 `models.py`

New dataclass:

```python
@dataclass(frozen=True)
class CoverageContext:
    """Typed view over coverage.json's subset Feature 2 uses."""
    timestamp: str
    totals_pct: float
    totals_tone: str
    endpoints_summary: tuple[tuple[str, str, float, str], ...]  # (method, path, pct, tone)
    endpoints_uncovered_flat: dict[str, tuple[dict, ...]]       # key = f"{method} {path}"
    audit_reconciled: bool
    audit_unattributed_count: int
```

### 6.3 `llm/client.py` — LlmEvaluator

**Breaking change to Feature 2 internals** (no external API change): Feature 2 currently has module-level `_SYSTEM`, `_TOOLS`, `_TOOL_CHOICE` constants. With coverage injection, `_SYSTEM` must become an instance attribute because the text now depends on runtime-loaded coverage data.

- `_TOOLS` and `_TOOL_CHOICE` stay module-level (no runtime content dependency).
- `_SYSTEM` → `self._system`, built in `__init__`.

`__init__` gains optional `coverage_summary: str = ""`:

```python
def __init__(self, ..., coverage_summary: str = ""):
    system_text = RUBRIC_TEXT
    if coverage_summary:
        system_text += "\n\n---\n\n" + coverage_summary
    self._system = [{
        "type": "text",
        "text": system_text,
        "cache_control": {"type": "ephemeral"},
    }]
```

Within one `make bdd-dashboard` run, `system_text` is stable → prompt cache hits across all 44 calls (content-based caching; Anthropic hashes the text, not Python object identity). Between runs (when coverage.json changes), the prefix invalidates — that's the accepted cost of including coverage.

**Test updates required in Feature 2's `test_llm_client.py`:** tests that reference the module-level `_SYSTEM` (e.g. assertions like `client._SYSTEM is ...`) must switch to `client._system is ...` or inspect `call["system"]` from the MockAnthropicClient's recorded calls. Most existing tests already take the latter approach, so the cleanup is minimal.

Analyzer builds `coverage_summary` from `CoverageContext`:

```
## Coverage context for this run

The BDD suite (aggregate) achieved 69% branch coverage on
backend/src/hangman/ (98 of 142 branches).

Per-endpoint uncovered branches (use when emitting D7 findings):
- POST /api/v1/games (83% covered):
  - game.py:42 "if category not in self._by_category:" — not taken
  - words.py:17 "if self._rng is None:" — not taken
...
```

### 6.4 `llm/rubric.py` — new criterion D7

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
scenario could include a "create a game for a missing category" variant.)

**Passes:** the scenario covers the branch, OR the branch isn't
plausibly reachable from the scenario's user intent.

**Why it matters.** Coverage data surfaces specific gaps the rubric
(D1–D6) can't see — this criterion lets the LLM suggest targeted
additions with file:line evidence.
```

Adds ~500 tokens to RUBRIC_TEXT. Still well above the 4096-token cache floor.

### 6.5 `renderer.py` — new summary card

Adds one more entry to the `summary_cards` list in `_build_summary_cards`:

```python
if coverage_context is not None:
    cards.append(SummaryCard(
        title="Code coverage",
        value=f"{coverage_context.totals_pct:.0f}%",
        subtitle=f"{covered}/{total} branches · "
                 + ("⚠ audit failed" if not coverage_context.audit_reconciled else ""),
        tone=coverage_context.totals_tone,  # success/warning/error
        link="coverage.html",  # new field on SummaryCard
    ))
else:
    cards.append(SummaryCard(
        title="Code coverage",
        value="—",
        subtitle="Run `make bdd-coverage` to enable",
        tone="",
        link=None,
    ))
```

Minor template tweak: `_scenario_card.html.j2` stays unchanged; `base.html.j2` grows the card-link-rendering logic.

---

## 7. Make target orchestration

### 7.1 Makefile additions

```makefile
.PHONY: backend-coverage bdd-coverage
# (add to existing .PHONY list)

backend-coverage:  ## Start backend under coverage instrumentation (run in its own terminal)
	bash scripts/backend-coverage.sh

bdd-coverage:  ## Run BDD suite with coverage instrumentation + generate reports
	@if [ ! -f .backend-coverage.pid ]; then \
	  echo "ERROR: Backend not running under coverage. Start with: make backend-coverage"; \
	  exit 2; \
	fi
	cd frontend && HANGMAN_BACKEND_PORT=$(HANGMAN_BACKEND_PORT) \
	  pnpm exec cucumber-js \
	  --format "message:test-results/cucumber.coverage.ndjson" \
	  --format "progress-bar"
	@PID=$$(cat .backend-coverage.pid) && \
	  kill -0 $$PID 2>/dev/null && \
	  kill -TERM $$PID || \
	  echo "WARN: Backend PID $$PID not running; coverage data may be stale"
	@rm -f .backend-coverage.pid
	@sleep 2
	cd backend && uv run coverage combine
	cd backend && uv run python -m tools.branch_coverage
```

### 7.2 `scripts/backend-coverage.sh`

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/.."
echo "$$" > .backend-coverage.pid
trap 'rm -f .backend-coverage.pid' EXIT
cd backend
exec uv run coverage run --branch --parallel-mode --source=src/hangman \
  -m uvicorn hangman.main:app --host 127.0.0.1 --port "${HANGMAN_BACKEND_PORT:-8000}"
```

`exec` chain: bash → uv → coverage → uvicorn. All same PID. SIGTERM on that PID hits uvicorn; coverage.py 7.13's `sigterm=true` handler flushes the data.

### 7.3 `frontend/package.json`

No script needed — cucumber's `--format` flag in the Make recipe handles the distinct output path. (Plan-phase may add `"bdd:coverage": "cucumber-js --format message:test-results/cucumber.coverage.ndjson"` as a convenience.)

### 7.4 `backend/pyproject.toml`

Add to `[dependency-groups].dev`:

```toml
"coverage>=7.13,<7.14",
"pyan3>=2.5,<3",
```

Note: `coverage` may already be a transitive dep of `pytest-cov`; pinning directly prevents drift.

### 7.5 `.gitignore`

Add:

```
.backend-coverage.pid
.coverage
.coverage.*
```

(`.coverage` and `.coverage.*` are the data files coverage.py writes.)

---

## 8. Testing strategy

See PRD §5 + the discussion's Section 4. Summary:

### 8.1 Feature 3 unit tests (~60-80 tests across 8 test files)

| Test file               | Coverage                                                                                                                                                                           |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_routes.py`        | `RouteEnumerator.enumerate()` on fixture app; handles `prefix=`, `add_api_route`, missing methods                                                                                  |
| `test_callgraph.py`     | `CallGraphBuilder.build()` against `fixtures/branch_coverage/minimal_app/` (real pyan3 API run); separate test mocks `CallGraphVisitor` to simulate failure → empty graph fallback |
| `test_reachability.py`  | BFS correctness, cycle handling, handler-not-in-graph edge case, boundary enforcement                                                                                              |
| `test_coverage_data.py` | Reads committed `minimal.coverage` fixture; handles negative target-line arcs; missing-file error                                                                                  |
| `test_grader.py`        | Branch-weighted pct math; threshold tone resolution; **audit reconciliation invariant** (the correctness guarantor)                                                                |
| `test_json_emitter.py`  | Golden-file against `fixtures/golden_coverage.json`; enum + tuple serialization                                                                                                    |
| `test_renderer.py`      | Golden-file against `fixtures/golden_coverage.html`; autoescape of condition_text                                                                                                  |
| `test_analyzer.py`      | End-to-end with a fake `CallGraphBuilder` returning a hand-built adjacency map (no real pyan3 invocation at test time); happy path + degraded-pyan3 path (empty graph)             |

### 8.2 Feature 2 tests to update (~10 new/modified)

- `test_analyzer.py`: staleness check (coverage.json present-and-fresh / present-and-stale / absent)
- `test_llm_client.py`: `coverage_summary` injection into cached system prompt; cache-hit behavior preserved
- `test_rubric.py`: new criterion D7 present in RUBRIC_TEXT
- `test_renderer.py`: new "Code coverage" card (populated / placeholder)
- `test_models.py`: (new file? or add to existing) — `CoverageContext` parsing from coverage.json

### 8.3 Manual integration smoke (Phase 5.4 analog)

1. Implement Feature 3
2. Start `make backend-coverage` in Terminal 1
3. Start `make frontend` in Terminal 2
4. Run `make bdd-coverage` in Terminal 3
5. Verify artifacts emit: `tests/bdd/reports/coverage.json` + `tests/bdd/reports/coverage.html` + `frontend/test-results/cucumber.coverage.ndjson`
6. Open `coverage.html` — confirm: summary cards, per-endpoint grid with tones, click-to-expand function tree, uncovered-branch list with condition text, audit section with `reconciled: true` (hopefully!)
7. Run `make bdd-dashboard` — confirm: new "Code coverage" card appears on the Feature 2 dashboard; LLM's findings reference coverage data (or explain why they don't — this is the interesting qualitative check)
8. Reconciliation assertion: `audit.reconciled` should be `true` on the real hangman codebase (if `false`, we have a real bug to fix per NO BUGS LEFT BEHIND)

### 8.4 Phase 5.4 E2E

**N/A — developer tooling.** Same justification as Feature 2: no user-facing product surface. Manual smoke (§8.3) is the verification.

---

## 9. Determinism boundary

Every module in Feature 3 is deterministic. Same inputs → same outputs.

**Deterministic invariants:**

- `RouteEnumerator.enumerate()` — given the same FastAPI app, identical `Endpoint` tuples (sorted)
- `CallGraphBuilder.build()` — pyan3 itself is deterministic for a fixed codebase; subprocess stdout is bit-for-bit stable across invocations
- `Reachability.compute()` — BFS with stable visited-set iteration
- `CoverageDataLoader.load()` — reads a binary data file; deterministic
- `Grader.grade()` — pure function over dicts/sets with stable iteration order
- `JsonEmitter.emit()` — `json.dumps` with stable field order + `indent=2`
- `DashboardRenderer.render()` — Jinja2 with no dates/RNG in templates

The only time-varying input is `timestamp` (from `cucumber.coverage.ndjson.meta.startedAt`). Golden-file tests inject a fixed timestamp via the fixture.

No LLM in Feature 3. Feature 2's LLM is the non-deterministic surface (and its own golden files are scoped to deterministic modules).

---

## 10. Non-goals (reaffirmed from PRD v1.0)

- No frontend (TypeScript/Playwright) coverage.
- No per-scenario branch attribution — aggregate only.
- No 100% accurate static call-graph — best-effort, audit reconciliation is the safety net.
- No coverage of SQLAlchemy ORM / stdlib / FastAPI internals (boundary = `backend/src/hangman/` only).
- No replacing Feature 2's tag-based "Endpoint coverage" card — we add a new "Code coverage" card alongside.
- No always-on instrumentation in `make bdd`. Opt-in via `make bdd-coverage`.
- No CI/CD integration, scheduled reports, Slack/Teams push. Local only.
- No coverage trend tracking over time (may be a future feature).
- No test-suite recommendation engine. Feature 2's LLM surfaces gaps in plain language.
- No config file / CLI flag for thresholds. Hardcoded constants.
- No Anthropic API calls from Feature 3. No `ANTHROPIC_API_KEY` required for `make bdd-coverage`.

---

## 11. Open questions

All resolved. 7 PRD open questions resolved via research + brainstorming; 5 plan-phase details resolved in Section 13.

## 11.1 Plan-phase decisions (resolved at design close-out)

- **Cucumber `--format` location:** **Make recipe passes `--format` inline.** No new `bdd:coverage` script in `frontend/package.json`. One place to find the NDJSON filename (the Make recipe in `backend-coverage` / `bdd-coverage`).
- **`scripts/backend-coverage.sh` PID cleanup:** `trap 'rm -f .backend-coverage.pid' EXIT INT TERM` inside the script. `make bdd-coverage` does `kill -0 $PID` before `kill -TERM` (check-alive); warns (does not error) on stale PID; always `rm -f` the file after. README documents "if you `kill -9` the backend process, `rm .backend-coverage.pid` manually before next run."
- **Repo `LICENSE` file:** **Add MIT LICENSE** as part of Feature 3's implementation plan. Permissive; matches Python dev-tooling ecosystem; no obligation propagation from pyan3 (which stays in `[dependency-groups].dev` only, never runtime).
- **`condition_text` extraction edge cases:** Plan-phase unit tests in `test_reachability.py` cover: multi-line conditions, pattern-match guards, ternary expressions, `try/except` arcs (use exception type or `"(conditional arc)"` as fallback). Degraded extraction never raises — returns a placeholder string instead.
- **Feature 2 summary-card ordering:** new "Code coverage" card placed **immediately after the existing tag-based "Endpoint coverage" card**. Lets the viewer compare tag-based (what scenarios claim) vs code-path-based (what's actually tested) side-by-side.

---

## 12. Non-scope risks carried forward

5 risks documented in the brainstorming (Section 5). Re-stated here for the implementation plan to address:

1. **pyan3 misses `Depends()` / async / decorator-registered handlers.** Mitigation: audit reconciliation. Any gap lands in `unattributed_branches` and is visible to the dev. Escape hatch if pyan3 stalls upstream: vendor it into `backend/tools/branch_coverage/_pyan3/`.

2. **`hangman.main` import side effects.** Plan-phase task: audit `backend/src/hangman/*.py` for import-time work (especially `db.py`). If any module eagerly opens connections / runs migrations at import, use a test-mode env var to suppress for `RouteEnumerator`'s import.

3. **SIGTERM coordination edge cases.** `.backend-coverage.pid` file has stale-PID / race-condition modes. Makefile must: `kill -0` check alive before `kill -TERM`; `rm -f` (not `rm`) the pid file; log warning (not error) on stale.

4. **Audit reconciliation failure in practice.** If `reconciled: false` fires on the first live run, it's a real bug. `test_grader.py` must include an invariant test over fixture inputs. Manual smoke §8.3 verifies against the real Hangman codebase.

5. **pyan3 GPL v2+ licensing.** Add repo `LICENSE` file during implementation (permissive — MIT or Apache-2.0). pyan3 stays in `[dependency-groups].dev`, never runtime. Documented in this spec.

---

## 13. References

- **PRD:** `docs/prds/bdd-branch-coverage.md` v1.0
- **PRD discussion:** `docs/prds/bdd-branch-coverage-discussion.md`
- **Research brief:** `docs/research/2026-04-24-bdd-branch-coverage.md`
- **Feature 1 (merged):** `docs/plans/2026-04-23-bdd-suite-design.md`, `docs/plans/2026-04-23-bdd-suite-plan.md`
- **Feature 2 (merged):** `docs/prds/bdd-dashboard.md` v2.0, `docs/plans/2026-04-24-bdd-dashboard-design.md`, `docs/plans/2026-04-24-bdd-dashboard-plan.md`
- **coverage.py docs:** https://coverage.readthedocs.io/ — `--branch`, `--parallel-mode`, `sigterm=true`
- **pyan3 PyPI:** https://pypi.org/project/pyan3/
- **FastAPI route enumeration:** https://fastapi.tiangolo.com/reference/apirouter/
- **Project rules:** `.claude/rules/{principles,workflow,testing,python-style,security}.md`
