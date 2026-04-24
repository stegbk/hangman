# Design: BDD Dashboard

**Date:** 2026-04-24
**Version:** 2.0
**Status:** Draft (awaiting KC review)
**PRD:** `docs/prds/bdd-dashboard.md` v2.0
**Research brief:** `docs/research/2026-04-23-bdd-dashboard.md` (incl. "Addendum — LLM evaluation path")

Technical design for **Feature 2 of the three-feature BDD plan** — a Python analyzer + HTML dashboard generator that:

1. Parses the 11 `.feature` files via `gherkinDocument` envelopes from `cucumber.ndjson`
2. Rolls up scenario pass/fail from `testStepFinished.testStepResult.status`
3. Grades coverage procedurally (tag-set intersection against scraped endpoint strings + UC-named Feature blocks)
4. **Packages each scenario + each feature into an LLM prompt, sends ~44 Anthropic Messages API calls with prompt caching and forced tool use, collects typed `Finding` JSON**
5. Renders a single self-contained `dashboard.html` via Jinja2

No gates. No hooks. No CI/CD. No Teams push. Developer-only tool.

**Revision history:**

| Version | Date       | Change                                                                                                                                                                                                            |
| ------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.0     | 2026-04-24 | Initial design (Python OO rule engine, 13 hardcoded Rule classes, byte-identical-output guarantee). Approved but superseded before writing-plans by PRD v2.0 pivot.                                               |
| 2.0     | 2026-04-24 | PRD v2.0 pivot — replace Rule Protocol with Packager + LlmEvaluator + Rubric. Drop byte-identical-output / golden-full-HTML test. Add anthropic SDK integration, prompt caching, forced tool use, cost reporting. |

---

## Summary of load-bearing decisions

Locked by PRD v2.0 + research addendum + brainstorm dialogue:

- **Python 3.12** analyzer in `backend/tools/dashboard/`. Not part of the installable `hangman` package.
- **Jinja2 ~3.1.6** + **anthropic >=0.97,<1** as new dev-group deps in `backend/pyproject.toml`.
- **Chart.js 4.5.1 via CDN** (exact pin).
- **NDJSON is the primary source of truth.** `gherkinDocument` envelopes give us the Gherkin AST for free. Orphan-file detection via filesystem glob is advisory only.
- **LLM evaluation via Anthropic SDK, forced tool use, prompt caching.** Default `claude-sonnet-4-6`; `--model` flag accepts `claude-haiku-4-5` / `claude-opus-4-7`. Rubric ≥ 4096 tokens as a **conservative cache floor** we set ourselves (Anthropic's per-model cacheable-prompt minimum is often lower per their caching docs — 4096 guarantees caching on every model we expose). Asserted at runtime via `rubric_token_count()`. Fixed `tool_choice={"type": "tool", "name": "ReportFindings"}` across all calls. No `thinking` parameter.
- **Two packaging levels** (brainstorm Q2 a+b): per-scenario (33 calls) + per-feature (11 calls) = 44 calls per run.
- **Rubric + free-form** (brainstorm Q3c): the rubric lists 13 criteria; the LLM also emits "what else do you see?" findings with an LLM-chosen criterion ID.
- **Object-oriented module structure** (brainstorm Q1c). Single-responsibility modules with typed dataclasses.
- **Coverage grading stays procedural** (brainstorm Q4 hybrid). Feature 3 will add call-graph coverage.
- **Deterministic render of non-deterministic findings.** The Renderer and CoverageGrader are unit-/golden-testable; the full dashboard HTML is NOT snapshot-tested (LLM findings vary across runs).

---

## 1. Architecture

```
backend/
├── pyproject.toml                       # + jinja2, + anthropic in dependency-groups.dev
└── tools/                               # NEW — developer tooling, not part of hangman package
    ├── __init__.py
    └── dashboard/
        ├── __init__.py
        ├── __main__.py                  # CLI entrypoint (argparse; ~60 lines)
        ├── analyzer.py                  # Analyzer orchestrator — wires the pipeline
        ├── models.py                    # @dataclass: Scenario, Feature, Finding, CoverageGrade,
                                         #             RunSummary, AnalysisContext, Package, LlmCallResult
        ├── parser.py                    # NdjsonParser — NDJSON → ParseResult
        ├── coverage.py                  # CoverageGrader — per-endpoint + per-UC grading
        ├── packager.py                  # Packager — produces ScenarioPackage + FeaturePackage
        ├── llm/
        │   ├── __init__.py
        │   ├── client.py                # LlmEvaluator — wraps anthropic SDK; batches 44 calls
        │   ├── rubric.py                # Rubric text (≥4096 tokens); embedded in system prompt
        │   ├── tool_schema.py           # ReportFindings tool JSON schema + Pydantic validator
        │   └── cost.py                  # Pricing table + token-to-USD helpers
        ├── history.py                   # HistoryStore — .bdd-history/ read/write
        ├── renderer.py                  # DashboardRenderer — Jinja env + render
        └── templates/
            ├── base.html.j2             # Shell: header, CSS, charts, data blob, Chart.js CDN,
                                         #        scenario grid, modal root, warning banner
            ├── _scenario_card.html.j2   # Per-scenario card (rendered 33×)
            └── _modal.html.j2           # Click-to-detail modal content

backend/tests/unit/tools/dashboard/      # Pytest discovery via existing testpaths=["tests"]
├── __init__.py
├── conftest.py                          # NDJSON + gherkinDocument fixtures; MockAnthropicClient
├── test_parser.py                       # NDJSON parser + AST extraction + status rollup
├── test_coverage.py                     # endpoint-template normalization + UC regex + grading
├── test_packager.py                     # scenario/feature package shape; deterministic package ID
├── test_llm_tool_schema.py              # ReportFindings Pydantic validation (good + malformed payloads)
├── test_llm_client.py                   # LlmEvaluator w/ mocked SDK; retry/cache-hit/error paths
├── test_llm_cost.py                     # token→USD rollup per model
├── test_history.py                      # append/read; sparse-history placeholder; corrupt-entry skip
├── test_renderer.py                     # Jinja env autoescape + golden-file test on deterministic render
├── test_rubric.py                       # rubric length ≥ 4096 tokens (caching prerequisite)
└── test_analyzer.py                     # end-to-end pipeline with mocked LLM client

backend/tests/fixtures/dashboard/        # Test inputs
├── minimal.ndjson                       # 1 feature, 1 scenario
├── golden_render.html                   # Renderer snapshot (deterministic inputs → HTML)
├── llm_response_good.json               # Canned valid ReportFindings payload
├── llm_response_malformed.json          # Canned invalid payload (for retry test)
└── coverage_fixtures/                   # Feature objects for grading unit tests

Root:
├── Makefile                             # + bdd-dashboard target (passes MODEL + ANTHROPIC_API_KEY)
├── .gitignore                           # + .bdd-history/, + tests/bdd/reports/
└── tests/bdd/reports/                   # runtime output dir (gitignored, auto-created)
```

### Dependency graph (module-level)

```
__main__ → Analyzer → {NdjsonParser, CoverageGrader, Packager, LlmEvaluator, HistoryStore, DashboardRenderer}
                ↓
              models.py (dataclasses; no logic)

llm/ subpackage: client → {rubric, tool_schema, cost}
                          (all leaf; depend only on models.py + stdlib + anthropic SDK)
```

- **`models.py`** has zero imports from other tool modules — leaf-level.
- **`llm/`** depends on `models.py` + `anthropic` SDK; no filesystem I/O other than reading the `ANTHROPIC_API_KEY` env var at startup.
- **`parser.py`, `coverage.py`, `packager.py`, `history.py`, `renderer.py`** each depend on `models.py`; they don't depend on each other.
- **`analyzer.py`** is the only orchestrator.

---

## 2. Data flow

```
                   ┌────────────────────────────────────────┐
                   │  frontend/test-results/                │
                   │  cucumber.ndjson                       │
                   └────────────┬───────────────────────────┘
                                │
                   ┌────────────▼────────────┐
                   │ NdjsonParser.parse()    │
                   │ - iter JSON lines       │
                   │ - collect envelopes     │
                   │ - build Feature +       │
                   │   Scenario models       │
                   │ - step-status rollup    │
                   │   per scenario          │
                   └────────────┬────────────┘
                                │
                                │ ParseResult (features, scenarios, timestamp, uris)
                                │
                   ┌────────────▼────────────┐
                   │ Analyzer:               │
                   │ - orphan-file check     │
                   │   (filesystem glob)     │
                   └────────────┬────────────┘
                                │
           ┌────────────────────┼────────────────────┐
           │                    │                    │
  ┌────────▼──────┐   ┌─────────▼────────┐   ┌──────▼─────────┐
  │ CoverageGrader│   │   Packager       │   │ HistoryStore   │
  │ (procedural)  │   │   .make_packages │   │ (later, at end)│
  │ - endpoint idx│   │   - 33 scenario  │   └────────────────┘
  │ - UC idx      │   │   - 11 feature   │
  │ - grades      │   │   = 44 packages  │
  └──────┬────────┘   └─────────┬────────┘
         │                      │
         │            ┌─────────▼────────────────┐
         │            │  LlmEvaluator.evaluate() │
         │            │  - ThreadPoolExecutor(6) │
         │            │  - per package: call     │
         │            │    Anthropic Messages    │
         │            │    with prompt cache +   │
         │            │    forced tool_choice    │
         │            │  - validate ReportFindings│
         │            │    via Pydantic          │
         │            │  - retry once on malformed│
         │            │  - collect LlmCallResult │
         │            └─────────┬────────────────┘
         │                      │
         └──────────┬───────────┘
                    │  (context, findings, grades, skipped_packages)
                    │
          ┌─────────▼───────────────┐
          │ AnalysisContext         │
          │ (features, scenarios,   │
          │  endpoint_index,        │
          │  uc_index, timestamp,   │
          │  cost_report)           │
          └─────────┬───────────────┘
                    │
          ┌─────────▼───────────────┐
          │ HistoryStore.append()   │
          │ RunSummary w/           │
          │ cost + model +          │
          │ cache hit rate          │
          └─────────┬───────────────┘
                    │
          ┌─────────▼───────────────┐
          │ DashboardRenderer       │
          │ .render(ctx, findings,  │
          │   grades, history,      │
          │   skipped_packages)     │
          │ - Jinja env +           │
          │   select_autoescape     │
          └─────────┬───────────────┘
                    │
          ┌─────────▼───────────────┐
          │ tests/bdd/reports/      │
          │ dashboard.html          │
          └─────────────────────────┘
```

**Pure-function boundaries** (no hidden I/O inside these):

- `CoverageGrader.grade()` — deterministic for fixed input
- `Packager.make_packages()` — deterministic for fixed input (package IDs are stable)
- `LlmEvaluator.evaluate()` — **NON-deterministic** (samples from Anthropic); only I/O: the API calls themselves
- `DashboardRenderer.render()` — deterministic for fixed input

**I/O boundaries** (clearly identified, mockable):

- `NdjsonParser.parse()` — reads NDJSON file
- `LlmEvaluator.evaluate()` — HTTP calls to `api.anthropic.com`
- `HistoryStore.append/read_all` — filesystem under `.bdd-history/`
- `DashboardRenderer.render()` — builds HTML and writes to `output_path` in one call (v2 merges render/write; test reads `output_path` back). Jinja rendering is deterministic; the filesystem write is the I/O side-effect.

---

## 3. Module specs

### 3.1 `models.py`

Dataclasses. Leaf-level. No tool-module imports.

```python
from dataclasses import dataclass
from enum import Enum

class Severity(Enum):
    P0 = "P0"; P1 = "P1"; P2 = "P2"; P3 = "P3"

class Outcome(Enum):
    PASSED = "passed"; FAILED = "failed"; SKIPPED = "skipped"
    NOT_RUN = "not_run"; UNKNOWN = "unknown"

class CoverageState(Enum):
    FULL = "full"; PARTIAL = "partial"; NONE = "none"

class PackageKind(Enum):
    SCENARIO = "scenario"   # one per Scenario; 33 of them
    FEATURE = "feature"     # one per Feature file; 11 of them

@dataclass(frozen=True)
class Step:
    keyword: str
    text: str
    outcome: Outcome

@dataclass(frozen=True)
class Scenario:
    feature_file: str
    feature_name: str
    name: str
    line: int
    tags: tuple[str, ...]
    steps: tuple[Step, ...]
    outcome: Outcome

    @property
    def primary_tag(self) -> str | None: ...
    @property
    def is_smoke(self) -> bool: ...

@dataclass(frozen=True)
class Feature:
    file: str
    name: str
    scenarios: tuple[Scenario, ...]
    line: int

@dataclass(frozen=True)
class Finding:
    criterion_id: str           # e.g., "D2" (from rubric) or LLM-invented (rendered w/ warning badge)
    severity: Severity
    scenario: Scenario | None   # None for feature-level findings
    feature: Feature | None
    problem: str                # one-line statement
    evidence: str               # LLM-extracted quote (short, from step text or Feature title)
    reason: str
    fix_example: str
    is_recognized_criterion: bool  # True if criterion_id is in the rubric's list

@dataclass(frozen=True)
class CoverageGrade:
    subject: str
    kind: str                   # "endpoint" | "uc"
    state: CoverageState
    contributing_scenarios: tuple[Scenario, ...]
    missing_tags: tuple[str, ...]

@dataclass(frozen=True)
class Package:
    """LLM-ready prompt input. Built by Packager.make_packages()."""
    id: str                     # deterministic, e.g., "scenario:guesses.feature:14" or "feature:games.feature"
    kind: PackageKind
    scenario: Scenario | None   # present for SCENARIO
    feature: Feature | None     # present for FEATURE (and carries scenarios via feature.scenarios)
    prompt_content: str         # the rendered prompt body; built from the AST, NOT from raw file text

@dataclass(frozen=True)
class LlmCallResult:
    package_id: str
    model: str
    input_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int
    output_tokens: int
    wall_clock_ms: int
    succeeded: bool
    error_message: str | None   # populated if succeeded=False
    findings: tuple[Finding, ...]

@dataclass(frozen=True)
class CostReport:
    model: str
    total_input_tokens: int
    total_cache_read_tokens: int
    total_cache_creation_tokens: int
    total_output_tokens: int
    total_usd: float
    cache_hit_rate: float       # cache_read / total_input

@dataclass(frozen=True)
class RunSummary:
    timestamp: str              # ISO from NDJSON meta.startedAt
    total_scenarios: int
    passed: int
    failed: int
    skipped: int
    finding_counts: dict[Severity, int]
    model: str
    cost: CostReport
    skipped_packages: tuple[str, ...]   # package IDs that failed LLM eval

@dataclass(frozen=True)
class AnalysisContext:
    features: tuple[Feature, ...]
    scenarios: tuple[Scenario, ...]
    endpoint_index: dict[str, tuple[Scenario, ...]]
    uc_index: dict[str, tuple[Scenario, ...]]
    timestamp: str
```

**Invariant (coverage + renderer side):** everything in `AnalysisContext` + `CoverageGrade` is deterministically ordered. LLM findings do NOT participate in determinism guarantees.

### 3.2 `parser.py` — `NdjsonParser`

Unchanged from v1. Public method:

```python
@dataclass(frozen=True)
class ParseResult:
    features: tuple[Feature, ...]
    scenarios: tuple[Scenario, ...]
    timestamp: str
    gherkin_document_uris: frozenset[str]
```

- Validates `meta.protocolVersion` major = 32.
- Builds Feature + Scenario models from `gherkinDocument` envelopes (Background steps prepended).
- Maps `pickle.id` → scenario; correlates `testCaseStarted.testCaseId` + `testStepFinished.testStepResult.status`.
- Rolls up scenario outcome via `_rollup_outcome()` — see §4.

### 3.3 `coverage.py` — `CoverageGrader`

Unchanged from v1. Deterministic. Returns `(endpoint_index, uc_index, grades)`.

### 3.4 `packager.py` — `Packager`

**NEW in v2.** Class with one public method:

```python
def make_packages(self, features: tuple[Feature, ...]) -> tuple[Package, ...]:
    scenario_packages = [self._make_scenario_package(s) for f in features for s in f.scenarios]
    feature_packages = [self._make_feature_package(f) for f in features]
    return tuple(scenario_packages + feature_packages)
```

Each package carries a deterministic `id` + a pre-rendered `prompt_content` string. The prompt content is built from the structured models — NOT concatenated raw text — so we have full control over what the LLM sees (no passthrough of arbitrary file bytes).

**ScenarioPackage prompt shape** (~500 tokens):

```
SCENARIO: <name>
File: <feature_file>:<line>
Feature: <feature_name>
Tags: <@happy, @smoke, ...>
Outcome: passed | failed | skipped | not_run

STEPS:
  Given <text>
  When  <text>
  Then  <text>
  ...
```

**FeaturePackage prompt shape** (~1.5-3KB):

```
FEATURE: <name>
File: <file>
Scenarios: <count>
  - <scenario 1 name> (tags, outcome)
  - <scenario 2 name> (tags, outcome)
  ...

[Optional: scenario-count per primary tag: 2 @happy / 1 @failure / 1 @edge]
```

Package IDs are stable across runs for identical inputs (used for cache keys / error messages / skipped-package bookkeeping). Format: `scenario:{file}:{line}` or `feature:{file}`.

### 3.5 `llm/rubric.py` — `Rubric`

**NEW in v2.** Module-level constant string containing the full rubric text. Embedded in every LLM call's system prompt with `cache_control: {"type": "ephemeral"}`.

Structure:

```
# BDD Quality Rubric — Hangman BDD Suite

You are evaluating BDD scenarios and features for the Hangman project.
Return findings via the ReportFindings tool.

## Severity mapping
P0 = broken (would crash); P1 = wrong (incorrect behavior); P2 = poor
(code smell); P3 = nit (style).

## Criteria (graded on every scenario/feature)

### D1 (P2): Trivial-pass scenario
  ...

### D2 (P2): @failure scenario missing error.code assertion
  ...

[13 criteria total: D1-D6 domain + H1-H7 hygiene, each with
 description + positive/negative examples]

## Output format (MUST use ReportFindings tool)

For each finding:
- criterion_id: one of D1..D6, H1..H7, OR a new ID you invent if you
  see an issue not in the rubric (will be rendered with a warning badge).
- severity: P0, P1, P2, or P3.
- problem: one-line statement of the issue.
- evidence: short quote from the scenario/feature text showing the issue.
- reason: why it matters.
- fix_example: concrete Gherkin rewrite or action.
```

**Length constraint:** the module has a `RUBRIC_TEXT: str` constant + a `rubric_token_count()` helper. At startup the Analyzer asserts `rubric_token_count() >= 4096`. This is our conservative floor — Anthropic's actual minimum cacheable-prompt size is model-specific per the caching docs (often lower than 4096 on smaller models); the floor guarantees caching on every model we expose via `--model`. Test `test_rubric.py` enforces this.

### 3.6 `llm/tool_schema.py` — `ReportFindings` tool definition + Pydantic validator

**NEW in v2.**

```python
REPORT_FINDINGS_TOOL: dict = {
    "name": "ReportFindings",
    "description": "Report quality findings for the BDD scenario or feature.",
    "input_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "criterion_id": {"type": "string", "description": "D1..D6, H1..H7, or an invented ID"},
                        "severity": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
                        "problem": {"type": "string"},
                        "evidence": {"type": "string"},
                        "reason": {"type": "string"},
                        "fix_example": {"type": "string"},
                    },
                    "required": ["criterion_id", "severity", "problem", "evidence", "reason", "fix_example"],
                },
            },
        },
        "required": ["findings"],
    },
}

class ReportFindingsPayload(BaseModel):
    findings: list[FindingPayload]

class FindingPayload(BaseModel):
    criterion_id: str
    severity: Literal["P0", "P1", "P2", "P3"]
    problem: str
    evidence: str
    reason: str
    fix_example: str
```

Malformed tool payloads (e.g., model returns text instead of tool_use) raise a typed error; `LlmEvaluator` handles retry.

### 3.7 `llm/cost.py` — pricing + USD rollup

**NEW in v2.** Pricing table hardcoded from Anthropic's published rates (research addendum):

```python
PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
    "claude-haiku-4-5":  {"input": 1.0 / 1_000_000, "output":  5.0 / 1_000_000},
    "claude-opus-4-7":   {"input": 5.0 / 1_000_000, "output": 25.0 / 1_000_000},
}
# Anthropic: cache writes = 1.25× input; cache reads = 0.1× input.
CACHE_WRITE_MULT = 1.25
CACHE_READ_MULT = 0.1

def compute_cost(results: list[LlmCallResult]) -> CostReport: ...
```

Unit-tested against sample token counts → expected USD.

### 3.8 `llm/client.py` — `LlmEvaluator`

**NEW in v2.** Wraps the `anthropic` SDK.

```python
class LlmEvaluator:
    def __init__(self, client: Anthropic | None = None, model: str = "claude-sonnet-4-6",
                 max_workers: int = 6, max_retries_per_call: int = 1):
        self._client = client or Anthropic()  # reads ANTHROPIC_API_KEY from env
        self._model = model
        self._max_workers = max_workers
        self._max_retries = max_retries_per_call

    def evaluate(self, packages: tuple[Package, ...]) -> tuple[tuple[LlmCallResult, ...], tuple[str, ...]]:
        """Returns (results, skipped_package_ids)."""
        ...
```

**Internals:**

- Pre-flight: assert `rubric_token_count() >= 4096`.
- `ThreadPoolExecutor(max_workers=self._max_workers)` — sync Anthropic client across threads.
- Per-package: build `messages` with system prompt containing cached rubric + cached tool definition + the package's prompt content. Force `tool_choice={"type": "tool", "name": "ReportFindings"}`.
- Parse tool-use content block → validate via `ReportFindingsPayload` → convert to `Finding` list.
- On malformed payload: retry once; on second failure, log + add to skipped list.
- On SDK exceptions (`RateLimitError`, `APIConnectionError`, etc. — per research addendum): SDK handles default retries (`max_retries=2`); surface final error as skipped package.
- Assert on first call: `cache_creation_input_tokens > 0`. Hard-fail startup if the rubric isn't actually being cached — this is the cost guardrail from research addendum risk #2.

**Mocking:** for unit tests, inject a `MockAnthropicClient` via the `client` parameter. Fixtures return canned `Message` objects with `tool_use` content blocks.

### 3.9 `history.py` — `HistoryStore`

Similar to v1; the `RunSummary` dataclass grows `model`, `cost: CostReport`, `skipped_packages`. The trend chart now has enough signal to show cost-per-run over time (future enhancement; for v2 the trend chart only plots total/passed/failed/P0+P1 counts as in v1).

### 3.10 `renderer.py` — `DashboardRenderer`

Similar to v1. Added responsibilities:

- Render warning banner if `skipped_packages` is non-empty ("N packages failed LLM evaluation and were skipped — see stderr for details").
- Render cost report card (or footer note) showing model + per-run USD.
- For `Finding.is_recognized_criterion == False`, render with a warning badge (e.g., yellow "⚠ LLM-invented" pill) so the user can spot LLM hallucinations.
- Jinja `select_autoescape(["html", "j2"])` still applies — this is the prompt-injection defense layer per PRD §7.

### 3.11 `analyzer.py` — `Analyzer`

Public method:

```python
class Analyzer:
    def __init__(self, parser, grader, packager, llm, history, renderer): ...

    def run(self, ndjson_path, output_path, history_dir, features_glob) -> None:
        parse_result = self.parser.parse(ndjson_path)
        self._warn_on_orphan_features(features_glob, parse_result.gherkin_document_uris)
        endpoint_index, uc_index, grades = self.grader.grade(parse_result.features)
        context = AnalysisContext(
            features=parse_result.features,
            scenarios=parse_result.scenarios,
            endpoint_index=endpoint_index,
            uc_index=uc_index,
            timestamp=parse_result.timestamp,
        )
        packages = self.packager.make_packages(parse_result.features)
        results, skipped = self.llm.evaluate(packages)
        findings = [f for r in results if r.succeeded for f in r.findings]
        findings = self._sort_findings(findings)
        cost = compute_cost(results)
        summary = self._summarize(context, findings, cost, skipped)
        self.history.append(summary, history_dir)
        recent_history = self.history.read_all(history_dir)
        self.renderer.render(context, findings, grades, recent_history, skipped, cost, output_path)
        self._print_cost_report(cost, skipped)  # to stderr
```

### 3.12 `__main__.py` — CLI

```python
def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.dashboard")
    parser.add_argument("--ndjson", default="../frontend/test-results/cucumber.ndjson", type=Path)
    parser.add_argument("--output", default="../tests/bdd/reports/dashboard.html", type=Path)
    parser.add_argument("--history-dir", default="../.bdd-history", type=Path)
    parser.add_argument("--features-dir", default="../frontend/tests/bdd/features", type=Path)
    parser.add_argument("--model", default="claude-sonnet-4-6",
                        choices=["claude-sonnet-4-6", "claude-haiku-4-5", "claude-opus-4-7"])
    parser.add_argument("--max-workers", default=6, type=int)
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not api_key.startswith("sk-ant-"):
        print("ERROR: ANTHROPIC_API_KEY env var missing or malformed.", file=sys.stderr)
        return 2

    # rubric length pre-flight
    assert rubric_token_count() >= 4096, "Rubric shorter than cache minimum"

    analyzer = Analyzer(
        parser=NdjsonParser(),
        grader=CoverageGrader(),
        packager=Packager(),
        llm=LlmEvaluator(model=args.model, max_workers=args.max_workers),
        history=HistoryStore(),
        renderer=DashboardRenderer(),
    )
    analyzer.run(
        ndjson_path=args.ndjson,
        output_path=args.output,
        history_dir=args.history_dir,
        features_glob=args.features_dir,
    )
    return 0
```

---

## 4. Scenario outcome rollup

Unchanged from v1 — see §4 of v1 for the full table. `willBeRetried` handling unchanged.

---

## 5. Summary cards (updated for v2)

7 cards:

| #   | Title             | Value                       | Subtitle                                 | Tone           |
| --- | ----------------- | --------------------------- | ---------------------------------------- | -------------- |
| 1   | Total scenarios   | `{total}`                   | `{feature_count} features`               | info           |
| 2   | Passing           | `{passed}/{total}` ({pct}%) | `@smoke: {smoke_passed}/{smoke_total}`   | success        |
| 3   | Endpoint coverage | `{full}/{total}` Full       | `{partial} Partial · {none_listed} None` | varies         |
| 4   | UC coverage       | `{full}/{total}` Full       | `{partial} Partial · {none_listed} None` | varies         |
| 5   | P0 findings       | `{p0_count}`                | "Broken"                                 | error if > 0   |
| 6   | P1 findings       | `{p1_count}`                | "Wrong"                                  | error if > 0   |
| 7   | P2 findings       | `{p2_count}`                | "Poor"                                   | warning if > 0 |

**Below the strip:** a compact **cost footer**: `Model: claude-sonnet-4-6 · 44 calls · $1.07 · 94% cache hit rate · 18s`. Pulled from `RunSummary.cost`.

**Warning banner** (conditionally above the strip): if `skipped_packages` is non-empty, `"⚠ N packages were skipped due to LLM errors: <ids>. See stderr."`

---

## 6. Jinja template layout

Base template adds:

- `{% if skipped_packages %}<div class="warning-banner">...</div>{% endif %}`
- Cost footer at the bottom of the header.
- Per-scenario card shows an "⚠ LLM-invented" pill if any finding has `is_recognized_criterion == False`.

Otherwise unchanged from v1. Autoescape stays on (defense against prompt-injected HTML in LLM findings).

---

## 7. Determinism vs. LLM-sampling boundary

v1 promised byte-identical output. v2 does NOT — the LLM is non-deterministic.

**What IS deterministic in v2** (testable via snapshots):

- `NdjsonParser.parse()` — given the same NDJSON, same models out.
- `CoverageGrader.grade()` — given the same features, same grades.
- `Packager.make_packages()` — given the same features, same packages with same IDs and same prompt content.
- `DashboardRenderer.render()` — given fixed findings + grades + history, same HTML.

**What is NOT deterministic:**

- `LlmEvaluator.evaluate()` — samples from Anthropic; identical packages on consecutive runs may yield slightly different findings (severity flip, finding-text wording).

**Design consequence:** we test the deterministic modules with golden files (see §9) and the non-deterministic module with mocks (fixed responses from a `MockAnthropicClient`). We do NOT snapshot the full `dashboard.html`.

**Stable sort keys** (still enforced for the deterministic parts):

- Features: `(file, line)`
- Scenarios: `(feature_file, line, name)`
- Tags: lexical
- Findings: `(severity_order, criterion_id, feature_file, line)` — after LLM returns them
- Endpoint/UC index keys: lexical
- Package IDs: derived from `(kind, file, line)`; stable

---

## 8. History + trend chart

`.bdd-history/<timestamp>.json` schema (v2 additions marked):

```json
{
  "timestamp": "2026-04-24T15:30:00Z",
  "total_scenarios": 33,
  "passed": 33,
  "failed": 0,
  "skipped": 0,
  "finding_counts": { "P0": 0, "P1": 0, "P2": 2, "P3": 5 },
  "model": "claude-sonnet-4-6", // NEW
  "cost": {
    // NEW
    "total_input_tokens": 160000,
    "total_cache_read_tokens": 145000,
    "total_cache_creation_tokens": 4200,
    "total_output_tokens": 48000,
    "total_usd": 1.07,
    "cache_hit_rate": 0.906
  },
  "skipped_packages": [] // NEW
}
```

Trend chart unchanged at v2: 4 series (total / passed / failed / P0+P1 count). Cost and cache-hit-rate are stored per entry but not yet plotted — a v3 enhancement.

---

## 9. Testing strategy

### 9.1 Deterministic modules (unit + golden-file)

| Test file                 | Coverage                                                                                                                               |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `test_parser.py`          | NDJSON iteration, envelope correlation, outcome rollup (all 7 status enums), retry handling                                            |
| `test_coverage.py`        | Endpoint-template normalization, UC regex, Full/Partial/None grading                                                                   |
| `test_packager.py`        | Scenario + feature package content; deterministic IDs; prompt token count within budget                                                |
| `test_rubric.py`          | **`rubric_token_count() >= 4096`** (hard gate per research addendum)                                                                   |
| `test_llm_tool_schema.py` | Pydantic validation of good payloads; malformed payloads raise cleanly                                                                 |
| `test_llm_cost.py`        | Pricing table correctness; USD rollup across 44 calls                                                                                  |
| `test_history.py`         | Append + read roundtrip; corrupt-entry skip; sparse-history placeholder                                                                |
| `test_renderer.py`        | Jinja autoescape verification; **golden-file test** on renderer with fixed findings + grades + history → `fixtures/golden_render.html` |

### 9.2 LLM-adjacent modules (mocked)

| Test file            | Coverage                                                                                                                                                                                                                                                                                                                                                                                                         |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_llm_client.py` | LlmEvaluator with `MockAnthropicClient`:<br>• happy path: valid tool-use response → findings<br>• malformed response → retry once → success<br>• malformed twice → skipped_packages populated<br>• SDK raises `APIConnectionError` → skipped<br>• cache assertion: `cache_creation_input_tokens > 0` on first call (hard-fail if not)<br>• parallel execution (6 workers) doesn't corrupt LlmCallResult ordering |
| `test_analyzer.py`   | End-to-end with `MockAnthropicClient`: fixture NDJSON + fixture LLM responses → expected HTML structure + expected `.bdd-history/` entry                                                                                                                                                                                                                                                                         |

### 9.3 Manual integration

Phase 5 checklist: run `make bdd-dashboard` once against the real suite with a valid `ANTHROPIC_API_KEY`. Verify:

1. 44 calls made (stderr log).
2. Cache hit rate > 90% from call #2 onward.
3. Cost report matches expected range (~$1.11 at Sonnet defaults).
4. Dashboard renders in Chrome/Firefox/Safari.
5. Click-to-modal works on 3 random scenarios.

### 9.4 Phase 5.4 E2E

**N/A** — developer tooling. Phase 5 checklist entry: `- [x] E2E verified — N/A: developer tooling, no user-facing surface. Manual browser smoke + 44-call integration run is the verification.`

---

## 10. Makefile + gitignore

### Makefile

```makefile
bdd-dashboard:
	cd backend && uv run python -m tools.dashboard \
	  --model $(or $(MODEL),claude-sonnet-4-6) \
	  --max-workers $(or $(MAX_WORKERS),6)
```

Usage:

```bash
make bdd-dashboard                                # Sonnet, 6 workers
make bdd-dashboard MODEL=claude-haiku-4-5         # Haiku for cheap iteration
make bdd-dashboard MODEL=claude-opus-4-7          # Opus for deep review
```

`ANTHROPIC_API_KEY` is read from the shell env, not passed via Make — keeps it out of process-listing surface.

### `.gitignore`

```
.bdd-history/
tests/bdd/reports/
```

(unchanged from v1)

---

## 11. Non-goals (reaffirmed from PRD v2.0)

- No gating. No hook enforcement. Exit code always 0 on successful HTML emission.
- No call-graph / per-branch coverage / `routes.py` enumeration — Feature 3.
- No offline mode / local LLM / Ollama.
- No multi-provider LLM support (Anthropic only in v2).
- No `thinking` parameter.
- No variable `tool_choice` across calls.
- No byte-identical output guarantee (dropped from v1).
- No golden-file test on the full dashboard HTML.
- No SPA / React dashboard.
- No Teams / Slack / webhook push.
- No CI/CD integration.
- No shared history storage.

---

## 12. Open questions

None blocking. All decisions resolved in PRD v2.0 + research brief + addendum + brainstorm Q1-Q8.

---

## 13. References

- **PRD:** `docs/prds/bdd-dashboard.md` v2.0
- **PRD discussion:** `docs/prds/bdd-dashboard-discussion.md`
- **Research brief:** `docs/research/2026-04-23-bdd-dashboard.md` (incl. Addendum 2026-04-24 — LLM evaluation path)
- **Reference dashboard:** `/Users/keithstegbauer/Downloads/bdd_dashboard_example.html`
- **Feature 1 (merged):** `docs/plans/2026-04-23-bdd-suite-design.md`, `docs/plans/2026-04-23-bdd-suite-plan.md`
- **Anthropic SDK:** https://pypi.org/project/anthropic/
- **Anthropic prompt caching:** https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching
- **Anthropic tool use:** https://platform.claude.com/docs/en/docs/build-with-claude/tool-use/overview
- **Project rules:** `.claude/rules/{principles,workflow,testing,python-style,security}.md`
