# Design: BDD Dashboard

**Date:** 2026-04-24
**Status:** Draft (awaiting KC review)
**PRD:** `docs/prds/bdd-dashboard.md` v1.1
**Research brief:** `docs/research/2026-04-23-bdd-dashboard.md`

This is the technical design for **Feature 2 of the three-feature BDD plan** — a Python analyzer + HTML dashboard generator that turns the Hangman BDD suite's output (11 `.feature` files + `cucumber.ndjson`) into a single self-contained, opinionated HTML report.

This feature is a **pure reporter**. No gates. No hooks. No CI/CD. No Teams push. See PRD §2 non-goals for the full exclusion list.

---

## Summary of load-bearing decisions

Locked by PRD v1.1 + research brief + brainstorm dialogue, restated here so the design reads cold:

- **Python 3.12** analyzer in `backend/tools/dashboard/`. Not part of the installable `hangman` package. Invoked from `backend/` via `uv run python -m tools.dashboard` (hooked up by the `make bdd-dashboard` target at repo root).
- **Jinja2 ~3.1.6** for templating — new dev-group dependency in `backend/pyproject.toml`. No new runtime deps on the `hangman` package.
- **Chart.js 4.5.1 via CDN** (exact pin, not `@4` / `@latest`) — for the byte-identical-output guarantee (PRD US-007).
- **NDJSON is the primary source of truth** (brainstorm Q4a). `gherkinDocument` envelopes in the NDJSON give us the Gherkin AST for free — zero-dep, no regex-fragility for core parsing. Filesystem glob is advisory only (warn on orphan `.feature` files). No `gherkin-official` dep.
- **Object-oriented module structure** (brainstorm Q1c). Each module is a class with a single responsibility. 13 rules are classes implementing a `Rule` Protocol.
- **Uniform rule interface** (brainstorm Q2b). Every rule receives an `AnalysisContext` (all features, all scenarios, endpoint index, UC index) and returns `list[Finding]`. Per-scenario rules just iterate `context.scenarios`.
- **Jinja base + partials** (brainstorm Q3b). One `base.html.j2` for the shell, plus `_scenario_card.html.j2` and `_modal.html.j2` partials.
- **13-rule starter opinion engine** pinned in PRD Appendix B (D1–D6 domain + H1–H7 hygiene). P0/P1/P2/P3 severities per `.claude/rules/workflow.md` rubric.
- **Informational output only** (PRD §2). `make bdd-dashboard` always exits 0 on successful HTML emission regardless of how many findings the opinion engine produces.
- **Single viable architecture** — the PRD left most strategic decisions pre-resolved. Contrarian gate (Phase 3.1c) will validate no alternative was missed; expected verdict: VALIDATE.

---

## 1. Architecture

```
backend/
├── pyproject.toml                       # + jinja2 in dependency-groups.dev
└── tools/                               # NEW — developer tooling, not part of hangman package
    ├── __init__.py
    └── dashboard/
        ├── __init__.py
        ├── __main__.py                  # CLI entrypoint (argparse; ~30 lines)
        ├── analyzer.py                  # Analyzer orchestrator class — wires the pipeline
        ├── models.py                    # @dataclass: Scenario, Feature, Finding, CoverageGrade, RunSummary, AnalysisContext
        ├── parser.py                    # NdjsonParser class — NDJSON → (Features, Scenarios, outcomes, timestamp)
        ├── rules/                       # Opinion engine
        │   ├── __init__.py              # exports ALL_RULES: list[Rule]
        │   ├── base.py                  # Rule Protocol + Severity enum
        │   ├── domain.py                # D1Rule..D6Rule (6 classes)
        │   └── hygiene.py               # H1Rule..H7Rule (7 classes)
        ├── coverage.py                  # CoverageGrader class — per-endpoint + per-UC grading
        ├── history.py                   # HistoryStore class — .bdd-history/ read/write
        ├── renderer.py                  # DashboardRenderer class — Jinja env + render
        └── templates/
            ├── base.html.j2             # Shell: header, CSS, charts, data blob, Chart.js CDN, scenario grid, modal root
            ├── _scenario_card.html.j2   # One rendered per Scenario (33×)
            └── _modal.html.j2           # Click-to-detail modal content template

backend/tests/unit/tools/dashboard/      # Pytest discovery via existing testpaths=["tests"]
├── __init__.py
├── conftest.py                          # shared NDJSON + gherkinDocument fixtures
├── test_parser.py                       # NDJSON parser + AST extraction
├── test_rules_domain.py                 # D1-D6 rule unit tests
├── test_rules_hygiene.py                # H1-H7 rule unit tests
├── test_coverage.py                     # per-endpoint + per-UC grading
├── test_history.py                      # append/read .bdd-history/, sparse-history placeholder
├── test_renderer.py                     # Jinja wiring + autoescape
├── test_analyzer.py                     # integration: pipeline end-to-end on a fixture NDJSON
└── test_dashboard_golden.py             # golden-file: run analyzer on current 11 features, diff HTML against snapshot

backend/tests/fixtures/dashboard/        # Test inputs
├── minimal.ndjson                       # 1 feature, 1 scenario — smallest valid input
├── zero_scenarios.feature               # for H6
├── dup_scenario_names.ndjson            # for H1
├── multi_primary_tag.ndjson             # for H3
├── all_same_tag.ndjson                  # for H7
├── trivial_pass.ndjson                  # for D1
├── failure_no_error_code.ndjson         # for D2
├── guesses_no_state_check.ndjson        # for D5
├── scenario_over_15_steps.ndjson        # for H4
├── outline_single_example.ndjson        # for H5
└── golden_dashboard.html                # snapshot for golden-file test (committed)

Root:
├── Makefile                             # + bdd-dashboard target
├── .gitignore                           # + .bdd-history/, + tests/bdd/reports/
└── tests/bdd/reports/                   # runtime output dir (gitignored, auto-created)
```

### Dependency graph (module-level)

```
__main__ → Analyzer → {NdjsonParser, CoverageGrader, ALL_RULES, HistoryStore, DashboardRenderer}
                ↓
              models.py (dataclasses; no logic)

Each rule class (D1..H7) → models.AnalysisContext (read-only)
```

- **`models.py`** has zero imports from other tool modules — it's leaf-level.
- **`rules/`** depends only on `models.py`. No parsing, no I/O.
- **`parser.py`, `coverage.py`, `history.py`, `renderer.py`** each depend on `models.py`; they do NOT depend on each other. The `Analyzer` class in `analyzer.py` is the only orchestrator.

---

## 2. Data flow

```
                    ┌─────────────────────────────────────┐
                    │   frontend/test-results/            │
                    │   cucumber.ndjson                   │
                    └────────────┬────────────────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │  NdjsonParser.parse()    │
                    │  - iter JSON lines       │
                    │  - collect envelopes:    │
                    │    * meta                │
                    │    * gherkinDocument     │
                    │    * pickle              │
                    │    * testCase*           │
                    │    * testStep*           │
                    │  - build Feature +       │
                    │    Scenario models       │
                    │  - status rollup per     │
                    │    scenario              │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │  CoverageGrader.grade()  │
                    │  - build endpoint_index  │
                    │    (regex-normalize      │
                    │    path params)          │
                    │  - build uc_index        │
                    │    (regex UC\d+[a-z]?    │
                    │    on Feature titles)    │
                    │  - grade each: Full /    │
                    │    Partial / None        │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │  AnalysisContext         │
                    │  (features, scenarios,   │
                    │   endpoint_index,        │
                    │   uc_index, timestamp)   │
                    └──┬─────────────┬─────────┘
                       │             │
         ┌─────────────▼──┐   ┌──────▼──────────┐
         │ ALL_RULES      │   │ HistoryStore    │
         │ (13 classes)   │   │ .append()       │
         │ → Findings     │   │ → .bdd-history/ │
         └───────┬────────┘   │ .read_all()     │
                 │            │ → [RunSummary]  │
                 │            └─────────┬───────┘
                 │                      │
                 └──────────┬───────────┘
                            │
                 ┌──────────▼──────────────┐
                 │ DashboardRenderer       │
                 │ .render(ctx, findings,  │
                 │   history)              │
                 │ - Jinja env with        │
                 │   autoescape            │
                 │ - render base template  │
                 │ - include partials per  │
                 │   scenario              │
                 └──────────┬──────────────┘
                            │
                 ┌──────────▼──────────────┐
                 │ tests/bdd/reports/      │
                 │ dashboard.html          │
                 └─────────────────────────┘
```

All pipeline stages are pure functions of their inputs (no global state, no hidden I/O) except:

- `NdjsonParser.parse()` reads the NDJSON file (one bounded I/O at start)
- `HistoryStore.append()` writes one JSON file + `HistoryStore.read_all()` reads the directory (bounded I/O)
- `DashboardRenderer.write()` writes `dashboard.html` (bounded I/O at end)

No other module touches the filesystem.

---

## 3. Module specs

### 3.1 `models.py`

Pure dataclasses (`@dataclass(frozen=True)` where practical). No logic. No imports from other tool modules.

```python
from dataclasses import dataclass, field
from enum import Enum

class Severity(Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

class Outcome(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_RUN = "not_run"         # scenario exists in gherkinDocument but no testCase* envelopes
    UNKNOWN = "unknown"         # fallback for unexpected status enum values

class CoverageState(Enum):
    FULL = "full"               # ≥1 @happy + ≥1 @failure + ≥1 @edge
    PARTIAL = "partial"         # ≥1 scenario but missing a primary tag class
    NONE = "none"               # zero scenarios reference it

@dataclass(frozen=True)
class Step:
    keyword: str                # "Given" | "When" | "Then" | "And" | "But"
    text: str                   # e.g., "I request "/api/v1/categories""
    outcome: Outcome

@dataclass(frozen=True)
class Scenario:
    feature_file: str           # e.g., "categories.feature"
    feature_name: str           # from Feature: block header text
    name: str                   # Scenario: title
    line: int                   # source line in the .feature file
    tags: tuple[str, ...]       # e.g., ("@happy", "@smoke") — lexically sorted
    steps: tuple[Step, ...]
    outcome: Outcome            # rollup over step outcomes

    @property
    def primary_tag(self) -> str | None: ...
    @property
    def is_smoke(self) -> bool: ...

@dataclass(frozen=True)
class Feature:
    file: str                   # e.g., "categories.feature"
    name: str                   # Feature: block text after the colon
    scenarios: tuple[Scenario, ...]
    line: int                   # Feature block line

@dataclass(frozen=True)
class Finding:
    rule_id: str                # e.g., "D2", "H7"
    severity: Severity
    scenario: Scenario | None   # None for feature-level findings like H6
    feature: Feature | None     # None for scenario-level findings (but present if scenario is present via scenario.feature_*)
    problem: str                # short statement
    reason: str                 # why it matters
    fix_example: str            # suggested Gherkin rewrite or change

@dataclass(frozen=True)
class CoverageGrade:
    subject: str                # "/api/v1/categories" or "UC1"
    kind: str                   # "endpoint" | "uc"
    state: CoverageState
    contributing_scenarios: tuple[Scenario, ...]
    missing_tags: tuple[str, ...]  # subset of {"@happy", "@failure", "@edge"}

@dataclass(frozen=True)
class RunSummary:
    """One row in .bdd-history/<timestamp>.json."""
    timestamp: str              # ISO 8601 from NDJSON meta.startedAt (UTC)
    total_scenarios: int
    passed: int
    failed: int
    skipped: int
    finding_counts: dict[Severity, int]  # {Severity.P0: 0, Severity.P1: 2, ...}

@dataclass(frozen=True)
class AnalysisContext:
    """Passed to every Rule.apply(). Immutable snapshot of the current run."""
    features: tuple[Feature, ...]
    scenarios: tuple[Scenario, ...]                    # flat; same objects reachable via features[].scenarios
    endpoint_index: dict[str, tuple[Scenario, ...]]    # normalized endpoint template → scenarios referencing it
    uc_index: dict[str, tuple[Scenario, ...]]          # UC name → scenarios in that UC
    timestamp: str                                     # from NDJSON meta.startedAt
```

**Invariant:** Everything in `AnalysisContext` is deterministic — tuples in stable order (scenarios by `(feature_file, line)`; dict keys sorted alphabetically; tags sorted lexically). This is the foundation for US-007's byte-identical-output guarantee.

### 3.2 `parser.py` — `NdjsonParser`

Single class. One public method: `parse(ndjson_path: Path) -> ParseResult`, where `ParseResult` is a small typed tuple the parser can produce without knowing about coverage grading:

```python
@dataclass(frozen=True)
class ParseResult:
    features: tuple[Feature, ...]
    scenarios: tuple[Scenario, ...]
    timestamp: str
    gherkin_document_uris: frozenset[str]   # source .feature URIs present in NDJSON; used by Analyzer's orphan check
```

The final `AnalysisContext` is constructed by the `Analyzer` in §3.8 from the `ParseResult` plus the outputs of `CoverageGrader.grade()`. Keeping `AnalysisContext` as the sole "fully-populated, read-only view" preserves the invariant in §3.1 — callers can rely on a non-empty `endpoint_index` and `uc_index`.

Responsibilities of `NdjsonParser.parse()`:

- Iterate NDJSON lines (stdlib `json.loads` per line).
- Accumulate envelopes by type. We only care about: `meta`, `gherkinDocument`, `pickle`, `testCase`, `testCaseStarted`, `testCaseFinished`, `testStep`, `testStepFinished`.
- Validate `meta.protocolVersion` major = 32. Raise with a clear message on mismatch.
- Build `Feature` + `Scenario` models from `gherkinDocument` envelopes (each has `feature.children[*]` for scenarios or backgrounds; background steps are prepended to each scenario's step list).
- Map `pickle` IDs → scenario models (pickles are Cucumber's "runnable" form of a scenario after tag filtering and outline expansion).
- Map `testCaseStarted.testCaseId` → pickle; correlate `testStepFinished.testStepId` to step + result.
- Compute scenario `outcome` via `_rollup_outcome(step_statuses)` (see §4).

Orphan-file detection is **not** the parser's responsibility — the `Analyzer` handles it in §3.8 using `ParseResult.gherkin_document_uris` + the `features_glob` path. Parser stays pure: input file in, typed result out.

### 3.3 `coverage.py` — `CoverageGrader`

Single class. One public method: `grade(features: tuple[Feature, ...]) -> tuple[dict[str, tuple[Scenario, ...]], dict[str, tuple[Scenario, ...]], list[CoverageGrade]]`. Returns `(endpoint_index, uc_index, grades)`.

Responsibilities:

- **Endpoint extraction:** scan every step text for `"/api/v1/..."` strings via regex `r'"(/api/v1/[^"]*)"'`. Normalize path params: `/games/123/guesses` → `/games/{id}/guesses` via `re.sub(r'/\d+', '/{id}', ...)`.
- **UC extraction:** regex `r'\bUC\d+[a-z]?\b'` against each Feature's `name` field. `UC3` and `UC3b` are distinct (word-boundary anchor).
- **Grading:** for each entry in the endpoint index (or UC index), compute the set of primary tags present across its contributing scenarios. `CoverageState.FULL` iff `{"@happy", "@failure", "@edge"} ⊆ tag_set`; `PARTIAL` iff non-empty subset; `NONE` iff no scenarios (only happens when the caller explicitly asks to grade a known-empty key, which we don't — so in practice `NONE` is unreachable from this method).

### 3.4 `rules/base.py` — `Rule` Protocol

```python
from typing import Protocol

class Rule(Protocol):
    rule_id: str               # class-level attribute, e.g., "D2"
    severity: Severity         # class-level attribute
    description: str           # class-level — used by the HTML to describe the rule
    reason: str                # class-level — why it matters

    def apply(self, context: AnalysisContext) -> list[Finding]:
        ...
```

Each rule is a concrete class:

```python
class D2Rule:
    rule_id = "D2"
    severity = Severity.P2
    description = "@failure scenario does not assert error.code"
    reason = "Our error envelope IS the contract. 'Failed somehow' ≠ 'failed the right way'."

    def apply(self, context: AnalysisContext) -> list[Finding]:
        findings = []
        for scenario in context.scenarios:
            if scenario.primary_tag != "@failure":
                continue
            if any('"error.code"' in step.text for step in scenario.steps):
                continue
            findings.append(
                Finding(
                    rule_id=self.rule_id, severity=self.severity,
                    scenario=scenario, feature=None,
                    problem="@failure scenario without error.code assertion",
                    reason=self.reason,
                    fix_example='Add: And the response error code is "UNKNOWN_CATEGORY"',
                )
            )
        return findings
```

**13 rules, one class each.** All classes are pure — no I/O, no mutation. Stateless (instance state only, no globals). Deterministic (iteration order follows `AnalysisContext.scenarios`).

### 3.5 `rules/__init__.py` — `ALL_RULES`

Module-level constant:

```python
from tools.dashboard.rules.domain import D1Rule, D2Rule, D3Rule, D4Rule, D5Rule, D6Rule
from tools.dashboard.rules.hygiene import H1Rule, H2Rule, H3Rule, H4Rule, H5Rule, H6Rule, H7Rule

ALL_RULES: tuple[Rule, ...] = (
    D1Rule(), D2Rule(), D3Rule(), D4Rule(), D5Rule(), D6Rule(),
    H1Rule(), H2Rule(), H3Rule(), H4Rule(), H5Rule(), H6Rule(), H7Rule(),
)
```

Order is stable (declaration order). Severity-sort happens in the renderer, not here.

### 3.6 `history.py` — `HistoryStore`

Single class, two public methods:

- `append(summary: RunSummary, history_dir: Path) -> Path` — writes one JSON file named `<ISO-timestamp>.json` (e.g., `2026-04-24T15-30-00Z.json`). Returns the written path.
- `read_all(history_dir: Path) -> tuple[RunSummary, ...]` — reads every `*.json` file, sorts by filename (filename IS the timestamp, lexical sort = chronological), returns parsed summaries. Skips unparseable files with a stderr warning (per PRD US-005 edge case).

No retention cap (PRD: keep forever). Trend chart in the renderer trims to last 90 for display.

### 3.7 `renderer.py` — `DashboardRenderer`

Single class. One public method: `render(context: AnalysisContext, findings: list[Finding], grades: list[CoverageGrade], history: tuple[RunSummary, ...], output_path: Path) -> None`.

Construction sets up:

```python
from jinja2 import Environment, PackageLoader, select_autoescape

self.env = Environment(
    loader=PackageLoader("tools.dashboard", "templates"),
    autoescape=select_autoescape(["html", "j2"]),
    keep_trailing_newline=False,
)
```

`render()` builds a **render context dict** from the inputs — a plain Python dict structure that mirrors what the Jinja templates iterate over. Keys:

```python
{
    "title": "Hangman BDD Dashboard",
    "timestamp": context.timestamp,               # ISO from NDJSON meta.startedAt
    "chartjs_cdn": "https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js",
    "summary_cards": [...],                       # 7 cards, see §5
    "endpoint_coverage": [...],                   # list of CoverageGrade-as-dict
    "uc_coverage": [...],                         # list of CoverageGrade-as-dict
    "scenarios": [...],                           # 33× scenario dicts, severity-sorted findings inline
    "trend_data": {...} | None,                   # None when < 5 history entries → placeholder
    "issues_data": {...},                         # severity distribution for donut chart
}
```

The render context is JSON-serializable — the template inlines it into a `<script id="dashboard-data">` tag for the client-side JavaScript to read for click-to-modal lookups.

### 3.8 `analyzer.py` — `Analyzer`

The orchestrator. One class, one public method: `run(ndjson_path: Path, output_path: Path, history_dir: Path, features_glob: Path) -> None`.

```python
class Analyzer:
    def __init__(
        self,
        parser: NdjsonParser,
        grader: CoverageGrader,
        rules: tuple[Rule, ...],
        history: HistoryStore,
        renderer: DashboardRenderer,
    ) -> None:
        ...

    def run(self, ...) -> None:
        parse_result = self.parser.parse(ndjson_path)
        # orphan-file check (warns on stderr; does not raise)
        self._warn_on_orphan_features(features_glob, parse_result.gherkin_document_uris)
        # grade coverage
        endpoint_index, uc_index, grades = self.grader.grade(parse_result.features)
        # construct the final fully-populated context
        context = AnalysisContext(
            features=parse_result.features,
            scenarios=parse_result.scenarios,
            endpoint_index=endpoint_index,
            uc_index=uc_index,
            timestamp=parse_result.timestamp,
        )
        # apply all rules
        findings: list[Finding] = []
        for rule in self.rules:
            findings.extend(rule.apply(context))
        findings = self._sort_findings(findings)
        # persist history
        summary = self._summarize(context, findings)
        self.history.append(summary, history_dir)
        # render
        recent_history = self.history.read_all(history_dir)
        self.renderer.render(context, findings, grades, recent_history, output_path)
```

Constructor injection for all collaborators — enables unit tests to pass in fakes. `__main__.py` wires real collaborators with default paths.

### 3.9 `__main__.py` — CLI

Minimal. `argparse` (stdlib, no `click` dep).

```python
def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.dashboard")
    parser.add_argument("--ndjson", default="../frontend/test-results/cucumber.ndjson", type=Path)
    parser.add_argument("--output", default="../tests/bdd/reports/dashboard.html", type=Path)
    parser.add_argument("--history-dir", default="../.bdd-history", type=Path)
    parser.add_argument("--features-dir", default="../frontend/tests/bdd/features", type=Path)
    args = parser.parse_args()

    analyzer = Analyzer(
        parser=NdjsonParser(),
        grader=CoverageGrader(),
        rules=ALL_RULES,
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

if __name__ == "__main__":
    sys.exit(main())
```

Defaults assume CWD is `backend/` (the Makefile target cd's there).

---

## 4. Scenario outcome rollup

Per research brief finding #3, `testCaseFinished` carries no status; we roll up `testStepFinished.testStepResult.status` across all steps.

```python
def _rollup_outcome(step_statuses: list[str]) -> Outcome:
    """Cucumber Messages v32.x status enum rollup.

    Per Cucumber's runtime semantics: the worst-wins. A single FAILED step
    fails the scenario; SKIPPED anywhere when everything else passed = skipped;
    any unexpected value → UNKNOWN (loud, not silent).
    """
    if not step_statuses:
        return Outcome.NOT_RUN
    if "FAILED" in step_statuses:
        return Outcome.FAILED
    if any(s in ("AMBIGUOUS", "UNDEFINED", "PENDING") for s in step_statuses):
        return Outcome.FAILED  # cucumber treats these as failures
    if all(s == "PASSED" for s in step_statuses):
        return Outcome.PASSED
    if all(s in ("PASSED", "SKIPPED") for s in step_statuses):
        return Outcome.SKIPPED
    return Outcome.UNKNOWN
```

Unit-tested against all 7 enum values per research brief risk #3.

**willBeRetried handling:** if `testCaseFinished.willBeRetried = true`, the scenario's `testCaseFinished` event is followed by a fresh `testCaseStarted` for the retry. Parser discards the initial `testCaseFinished` and keeps the final one. Unit-tested with a synthetic retry NDJSON fixture.

---

## 5. Summary cards (7) — pinned contents

Matches the example dashboard's structure (PRD §4 US-001 & §2 goals). Each card renders from the render context:

| #   | Title             | Value                       | Subtitle                                 | Tone                                            |
| --- | ----------------- | --------------------------- | ---------------------------------------- | ----------------------------------------------- |
| 1   | Total scenarios   | `{total_scenarios}`         | `{feature_count} features`               | info                                            |
| 2   | Passing           | `{passed}/{total}` ({pct}%) | `@smoke: {smoke_passed}/{smoke_total}`   | success                                         |
| 3   | Endpoint coverage | `{full}/{total}` Full       | `{partial} Partial · {none_listed} None` | varies: success if `full == total` else warning |
| 4   | UC coverage       | `{full}/{total}` Full       | `{partial} Partial · {none_listed} None` | varies (same as endpoint)                       |
| 5   | P0 findings       | `{p0_count}`                | "Broken — must fix"                      | error if > 0 else success                       |
| 6   | P1 findings       | `{p1_count}`                | "Wrong — must fix"                       | error if > 0 else success                       |
| 7   | P2 findings       | `{p2_count}`                | "Poor — should fix"                      | warning if > 0 else success                     |

P3 findings are not a card — they appear inline on scenario cards only. Keeps the top strip focused on signal.

---

## 6. Jinja template layout

### 6.1 `templates/base.html.j2`

Sections in order:

1. `<head>` — title, `<meta>`, inline `<style>` (dark-theme palette from the example), Chart.js CDN script.
2. Header — title + `timestamp` from render context.
3. Summary card grid — 7 cards from §5 above, iterated.
4. Charts section — two `<canvas>` elements for trend + issues. Trend chart is wrapped in a conditional:

   ```jinja
   {% if trend_data %}
     <canvas id="trendChart"></canvas>
   {% else %}
     <p class="trend-placeholder">Run <code>make bdd-dashboard</code> at least 5 times to see trends.</p>
   {% endif %}
   ```

5. Endpoint coverage section — list of grades with colored badges.
6. UC coverage section — same structure.
7. Scenario grid — `{% for scenario in scenarios %}{% include '_scenario_card.html.j2' %}{% endfor %}`. 33 cards.
8. Modal root — empty `<div id="modal" hidden>` populated by client-side JS on click. Uses `{% include '_modal.html.j2' %}` to pre-render the modal shell; JS populates `scenario_id`-specific content from the `<script id="dashboard-data">` JSON blob.
9. Inline `<script>` — minimal vanilla JS for card-click → modal open, Esc/outside-click → close, and Chart.js setup. ~60 lines. No build step.

### 6.2 `templates/_scenario_card.html.j2`

Per-scenario card: name + primary-tag badge + `@smoke` if present + pass/fail indicator + findings count by severity + first 2 finding titles (overflow truncated with "+N more..."). Clickable region links to modal-open JS.

### 6.3 `templates/_modal.html.j2`

Full modal content: Feature name, Scenario title, tag list, full Gherkin steps with per-step pass/fail, complete findings list with `rule_id`, `severity`, `description`, `reason`, `fix_example`.

**Autoescape:** `select_autoescape(["html", "j2"])` — all scenario text, step text, and finding strings are escaped. Scenario text could contain user-controlled HTML from `.feature` files (e.g., `<script>` in a Gherkin step string). Unit-tested per research brief risk #5.

---

## 7. Determinism for byte-identical output (PRD US-007)

Two sources of non-determinism we actively prevent:

1. **Iteration order of dicts/sets.** Mitigation: everywhere a dict or set crosses an abstraction boundary, it's either a tuple with stable sort order or a dict with explicitly sorted keys. Python 3.12 preserves insertion order; we ensure insertion is always sorted.
2. **Jinja2 whitespace control and trailing newlines.** Mitigation: `keep_trailing_newline=False`; `trim_blocks=True`; templates explicitly use `{%- ... -%}` where relevant.

**Stable sort keys used throughout:**

- Features: `(feature.file, feature.line)`
- Scenarios: `(scenario.feature_file, scenario.line, scenario.name)`
- Tags within scenario: lexical sort
- Findings: `(severity_order[finding.severity], finding.rule_id, scenario.feature_file, scenario.line)` where `severity_order = {P0: 0, P1: 1, P2: 2, P3: 3}`
- Endpoint index keys: lexical sort
- UC index keys: lexical sort (UC1, UC10, UC2 — we accept lexical for simplicity since the suite has < 10 UCs for the foreseeable future)

The only source of non-determinism LEFT is the header timestamp — by design (every run reflects the actual run time). For the golden-file test we strip the timestamp line before diffing.

---

## 8. History format + trend chart

### 8.1 Per-run file

`.bdd-history/<timestamp>.json` where `<timestamp>` is the NDJSON's `meta.startedAt`, normalized to `YYYY-MM-DDTHH-MM-SSZ` (colons replaced with dashes for filesystem safety on Windows):

```json
{
  "timestamp": "2026-04-24T15:30:00Z",
  "total_scenarios": 33,
  "passed": 33,
  "failed": 0,
  "skipped": 0,
  "finding_counts": { "P0": 0, "P1": 0, "P2": 2, "P3": 5 }
}
```

Compact (< 1 KB per run). Keep forever (PRD Q22a). Never deleted by the tool.

### 8.2 Trend chart

- Reads all `.bdd-history/*.json` files.
- Sorts by filename (lexical = chronological).
- When count < 5: renders the "run more" placeholder (PRD Q21).
- When count ≥ 5: displays the last 90 entries on a Chart.js line chart with 4 series: total / passing / failing / (P0 + P1) findings.
- Older entries remain on disk but are not shown on the chart.

---

## 9. Testing strategy

### 9.1 Layer 1 — Unit tests (pytest)

One test file per module. All tests use synthetic fixtures under `backend/tests/fixtures/dashboard/`.

- `test_parser.py` — NDJSON parsing; `_rollup_outcome()` against all 7 status enums; retry handling; protocol version mismatch; empty NDJSON.
- `test_rules_domain.py` — D1–D6, one test class per rule with positive + negative cases.
- `test_rules_hygiene.py` — H1–H7, same pattern.
- `test_coverage.py` — endpoint-template normalization (`/games/1/guesses` → `/games/{id}/guesses`); UC regex; all three grade states.
- `test_history.py` — append + read roundtrip; sparse history placeholder; corrupt entry skip.
- `test_renderer.py` — Jinja env autoescape verification (tests `env.autoescape` is truthy per research brief risk #5); rendering with empty findings list.
- `test_analyzer.py` — constructor injection works; end-to-end pipeline on a fixture NDJSON produces non-empty HTML at a temp path.

### 9.2 Layer 2 — Golden-file test

`test_dashboard_golden.py`:

1. Runs the real analyzer against the actual 11 `.feature` files + a checked-in fixture NDJSON (representing the current state of the BDD suite).
2. Renders HTML.
3. Strips the timestamp header line.
4. Diffs against `backend/tests/fixtures/dashboard/golden_dashboard.html`.

**Golden update protocol:** on intentional changes to the ruleset / template / coverage logic, regenerate the golden:

```bash
cd backend && uv run python -m tools.dashboard --output tests/fixtures/dashboard/golden_dashboard.html
# then sed out the timestamp line
```

The golden file is committed; changes are reviewed in PR.

### 9.3 Layer 3 — Integration test (manual)

Phase 5 checklist asks for `make bdd-dashboard` to run against the live suite once. Verify by opening the HTML in a browser.

Phase 5.4 E2E: **N/A** — this feature is developer tooling, not user-facing. The Phase 5 checklist entry will read: `- [x] E2E verified — N/A: developer tooling, no user-facing surface. Dashboard render verified manually in Chrome/Firefox/Safari.`

---

## 10. Makefile + gitignore

### `Makefile` addition

```makefile
bdd-dashboard:
	cd backend && uv run python -m tools.dashboard
```

Added to `.PHONY`. No env-var overrides needed at MVP (defaults in `__main__.py` point at the canonical paths).

### `.gitignore` additions

```
.bdd-history/
tests/bdd/reports/
```

---

## 11. Non-goals (reaffirmed from PRD)

Not shipping in this feature:

- Gating on findings (explicit per PRD §2 non-goals).
- `routes.py` introspection for endpoint enumeration (Feature 3).
- Call-graph / branch-coverage (Feature 3).
- Teams / Slack / webhook push.
- CI/CD integration.
- Auto-invoke on `make bdd`.
- Offline-mode CDN replacement.
- SPA / React dashboard.
- Shared history storage.
- Cucumber Messages Python binding dep.
- `gherkin-official` as a fallback parser.
- Rule hot-reload or config file — rules are code.

---

## 12. Open questions

None. All decisions resolved in PRD v1.1 + research brief + Q1–Q4 brainstorm answers.

---

## 13. References

- **PRD:** `docs/prds/bdd-dashboard.md` v1.1
- **PRD discussion:** `docs/prds/bdd-dashboard-discussion.md` (4 rounds, 30+ questions resolved)
- **Research brief:** `docs/research/2026-04-23-bdd-dashboard.md` (5 libs in depth, 7 open risks)
- **Reference dashboard (visual target):** `/Users/keithstegbauer/Downloads/bdd_dashboard_example.html`
- **Feature 1 (merged):** `docs/plans/2026-04-23-bdd-suite-design.md`, `docs/plans/2026-04-23-bdd-suite-plan.md`
- **Project rules:** `.claude/rules/{principles,workflow,testing,python-style}.md`
