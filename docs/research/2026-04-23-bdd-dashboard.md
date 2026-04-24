# Research: bdd-dashboard

**Date:** 2026-04-23
**Feature:** Python analyzer + single-file HTML generator that reports on the 33-scenario Hangman BDD suite (pure reporter, non-gating).
**Researcher:** research-first agent

---

## Libraries Touched

| Library                         | Our Version                                         | Latest Stable       | Breaking Changes Since Ours                                                              | Source                                                                                                   |
| ------------------------------- | --------------------------------------------------- | ------------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **Jinja2**                      | n/a (to add)                                        | 3.1.6 (2025-03-05)  | Adding fresh — no migration baseline                                                     | [PyPI Jinja2](https://pypi.org/project/Jinja2/) (accessed 2026-04-23)                                    |
| **Chart.js (CDN)**              | PRD pin 4.4.0                                       | 4.5.1 (2025-10-13)  | None between 4.4.x and 4.5.1 (patch/minor bugfixes only)                                 | [Chart.js v4.5.1 release](https://github.com/chartjs/Chart.js/releases/tag/v4.5.1) (accessed 2026-04-23) |
| **Cucumber Messages schema**    | 32.2.0 (emitted by cucumber-js 12.8.1 in Feature 1) | 32.3.1 (2026-04-13) | None relevant — all 32.x is schema-stable (`protocolVersion` is SEMVER, same major line) | [cucumber/messages repo](https://github.com/cucumber/messages) (accessed 2026-04-23)                     |
| **gherkin-official** (optional) | n/a (not installed)                                 | 39.0.0 (2026-03-01) | n/a                                                                                      | [PyPI gherkin-official](https://pypi.org/project/gherkin-official/) (accessed 2026-04-23)                |

No other external libraries are net-new. stdlib-only for NDJSON parsing (`json.loads` over `str.splitlines()`), dataclasses, and CLI (`argparse`). pytest is already in `backend/pyproject.toml` dev group.

---

## Per-Library Analysis

### Jinja2

**Versions:** ours=none (to add), latest=3.1.6 (released 2025-03-05)

**Breaking changes since ours:** N/A (adding fresh). Relevant context on the 3.1 line: 3.1.5 was a security fix for a potential sandbox escape on untrusted templates; 3.1.6 is a further maintenance release. Neither affects our use because we ship only in-repo trusted templates.

**Deprecations:** None relevant. Python support is `>=3.7` which aligns with our `>=3.12` runtime.

**Recommended pattern:**

1. **Loader:** `PackageLoader("tools.dashboard", "templates")` is the idiomatic choice for package-bundled templates. It resolves the package root automatically, survives installation layouts, and avoids hard-coded filesystem paths. `FileSystemLoader` is only preferred when templates live outside the Python package (not our case). Multiple sources concur on this recommendation.
2. **Autoescape:** Always pass `autoescape=select_autoescape(["html", "htm", "xml"])`. Jinja2 defaults `autoescape=False` — leaving it unset is the classic XSS footgun (Ruff `S701`, Bandit `B701`, CodeQL `py/jinja2-autoescape-false` all flag it).
3. **Environment config:** One `Environment` instance at module scope. Enable `trim_blocks=True` and `lstrip_blocks=True` for readable HTML output. No `cache_size` tuning needed at our scale (single render per run).

**Sources:**

1. [Jinja2 on PyPI](https://pypi.org/project/Jinja2/) — accessed 2026-04-23
2. [Jinja3.1.x API docs — loaders and autoescape](https://jinja.palletsprojects.com/en/stable/api/) — accessed 2026-04-23
3. [Ruff S701 — jinja2-autoescape-false](https://docs.astral.sh/ruff/rules/jinja2-autoescape-false/) — accessed 2026-04-23

**Design impact:** Add `"jinja2>=3.1.6,<4"` to `backend/pyproject.toml` `[project.dependencies]` (or to a new `[dependency-groups.dashboard]` if we want to keep the runtime `hangman` package lean — recommended, since the dashboard tool is not part of the FastAPI app). Choose `PackageLoader("tools.dashboard", "templates")` + `select_autoescape(["html"])`. Template directory: `backend/tools/dashboard/templates/`.

**Test implication:** Add a unit test asserting `Environment.autoescape` is truthy for `.html` templates (regression against accidentally dropping `select_autoescape`). A golden-file test (already called out in US-007) implicitly protects the template logic.

---

### Chart.js 4.x via CDN

**Versions:** PRD currently pins 4.4.0; latest stable is 4.5.1 (released 2025-10-13). 4.5.0 shipped 2025-09 with stacked-bars-with-multiple-x-axes fix and line-chart filler-pivot color support. 4.5.1 is a pure patch (plugin lifecycle, Doughnut legend sync, Chrome zoom rendering fix, type improvements).

**Breaking changes since ours:** **None.** 4.5.x is backwards-compatible with 4.4.x APIs. The Chart.js v4 migration guide (documenting the v3 → v4 break) is unchanged since 4.0 shipped; no v4-internal breakage. Both of the charts the dashboard needs — a line chart for the trend chart (US-005) and a doughnut/pie for finding-severity distribution — use stable APIs across all 4.x.

**Deprecations:** None relevant to line/doughnut charts.

**Recommended pattern:**

- **CDN URL:** `https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js` (UMD build, min suffix). This is the jsdelivr canonical pattern (`/npm/<pkg>@<semver>/<path>`). **Pin the exact patch version** — never `@4` or `@latest`, because the dashboard HTML is persistent and we want byte-identical output across runs on unchanged input.
- **Integrity hint (optional, P3):** jsdelivr supports Subresource Integrity. Not required for a local dev tool, but if we want to harden against CDN compromise later, we can add `integrity="sha384-..."` and `crossorigin="anonymous"` to the `<script>` tag.

**Sources:**

1. [Chart.js v4.5.1 release notes](https://github.com/chartjs/Chart.js/releases/tag/v4.5.1) — accessed 2026-04-23
2. [Chart.js 4.x migration guide (no v4.4 → v4.5 break)](https://www.chartjs.org/docs/latest/migration/v4-migration.html) — accessed 2026-04-23
3. [jsdelivr chart.js package page](https://www.jsdelivr.com/package/npm/chart.js) — accessed 2026-04-23

**Design impact:** **Bump the Chart.js pin from 4.4.0 → 4.5.1** in the PRD + generated HTML. Free upgrade (pure bugfixes), no code shape changes. If KC prefers to keep parity with the reference dashboard (`/Users/keithstegbauer/Downloads/bdd_dashboard_example.html`, which uses 4.4.0), 4.4.0 is also acceptable — they are API-identical for our two chart types.

**Test implication:** Add an HTML-emission unit test asserting the generated `<script>` tag carries an exact-version pin (regex `chart\.js@\d+\.\d+\.\d+/dist/chart\.umd\.min\.js`) — guards against a future maintainer switching to `@latest` and breaking byte-deterministic output.

---

### Cucumber Messages NDJSON schema

**Versions:** Feature 1 produces messages under `protocolVersion: "32.2.0"` (cucumber-js 12.8.1). The schema repo is at 32.3.1 (2026-04-13). The entire 32.x line is additive-only — no breaking changes within the major. `protocolVersion` is declared SEMVER, so the PRD's "same major family = compatible" stance is correct.

**Envelope message types we care about** (confirmed from `jsonschema/messages.md`):

| Type               | Why we need it                                                                                                                                                               |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `meta`             | `protocolVersion` check (hard-error on major mismatch per PRD §6).                                                                                                           |
| `source`           | Raw `.feature` text (alternative to filesystem scrape; redundant for us).                                                                                                    |
| `gherkinDocument`  | AST (feature + scenarios + steps) — **pre-parsed by cucumber-js for free**.                                                                                                  |
| `pickle`           | Scenario after Examples expansion; has `astNodeIds` linking back to doc.                                                                                                     |
| `testCase`         | Pickle + test steps (execution plan).                                                                                                                                        |
| `testCaseStarted`  | Execution run ID + timestamp.                                                                                                                                                |
| `testStepStarted`  | Per-step timestamp.                                                                                                                                                          |
| `testStepFinished` | `{ testCaseStartedId, testStepId, testStepResult, timestamp }`. `testStepResult.status` ∈ { `UNKNOWN`, `PASSED`, `SKIPPED`, `PENDING`, `UNDEFINED`, `AMBIGUOUS`, `FAILED` }. |
| `testCaseFinished` | `{ testCaseStartedId, timestamp, willBeRetried }`. Does NOT carry a status — compute from the worst child `testStepFinished`.                                                |
| `testRunFinished`  | Suite-level end marker.                                                                                                                                                      |

**Breaking changes since ours:** None. 32.3.0/32.3.1 are additive/bugfix within 32.x.

**Deprecations:** None relevant to us.

**Recommended pattern:**

- **Parse loop:** read NDJSON line-by-line (`for line in path.read_text().splitlines(): msg = json.loads(line)`). Each JSON object is exactly one `Envelope` with one populated key. No new dep needed.
- **Joining pass/fail to scenario:** (a) index `pickle` objects by `id` and by `astNodeIds`; (b) index `testCase` by `pickleId` and `id`; (c) aggregate `testStepFinished.testStepResult.status` per `testCaseStartedId` (fail if any step failed, skipped if all skipped, else passed). This is the textbook Cucumber Messages consumer pattern.
- **`protocolVersion` check:** `meta.protocolVersion.split(".")[0]` must equal `"32"` — hard-fail with a pointer to cucumber-js upgrade docs if not.
- **`willBeRetried` handling:** for Feature 1 we have no retries configured, so `willBeRetried=true` never appears. Still, treat any `testCaseFinished` with `willBeRetried=true` as "not the final result" (skip and wait for the retry).

**Sources:**

1. [cucumber/messages repo + jsonschema/messages.md](https://github.com/cucumber/messages) — accessed 2026-04-23
2. [Cucumber::Messages 32.2.0 per-type reference (mirror of JSON schema)](https://metacpan.org/release/CUKEBOT/Cucumber-Messages-32.2.0) — accessed 2026-04-23
3. [Cucumber Messages 32.3.1 current release](https://metacpan.org/release/CUKEBOT/Cucumber-Messages-32.3.1) — accessed 2026-04-23

**Design impact:** Confirms the PRD's version-pinning stance. Adds one **concrete fact the PRD does not currently capture**: `testCaseFinished` does not carry `status` — status must be derived from the worst child `testStepFinished.testStepResult.status`. This belongs in the design's NDJSON-parser section (Phase 3). Also confirms that the `gherkinDocument` envelopes present in the NDJSON give us a **free AST** for every `.feature` file cucumber-js touched — which invalidates part of the "regex scrape vs gherkin-official" trade-off (see next section).

**Test implication:** Fixture NDJSON files should cover: (a) all-pass suite, (b) mixed pass/fail/skipped, (c) scenario with undefined/pending steps, (d) `protocolVersion` mismatch (major-bump), (e) `willBeRetried=true` edge case, (f) truncated NDJSON (last line unterminated → clear parse error with line number per US-001).

---

### gherkin-official (Python)

**Versions:** ours=not installed, latest=39.0.0 (released 2026-03-01). Maintained by the Cucumber org (authors aslakhellesoy, cukebot). Semantic versioning across 39 major releases; healthy release cadence; MIT license; supports Python 3.9–3.13 — aligns with our 3.12.

**Breaking changes since ours:** N/A.

**Deprecations:** None relevant.

**Recommended pattern:**

```python
from gherkin.parser import Parser
from gherkin.pickles.compiler import Compiler

doc = Parser().parse(Path("foo.feature").read_text())
doc["uri"] = "foo.feature"
pickles = Compiler().compile(doc)
```

Returns a dict-shaped AST (same schema as `gherkinDocument` in the NDJSON envelope). Exact schema parity with Cucumber Messages — so our downstream code can consume either source.

**Sources:**

1. [gherkin-official on PyPI](https://pypi.org/project/gherkin-official/) — accessed 2026-04-23
2. [cucumber/gherkin repo README (Python usage)](https://github.com/cucumber/gherkin) — accessed 2026-04-23
3. [gherkin-official Snyk health report](https://snyk.io/advisor/python/gherkin-official) — accessed 2026-04-23

**Design impact (load-bearing — PRD v1.1 candidate):** The PRD currently says "MVP scrapes via regex (no AST). Full AST parsing is a follow-up iteration." The research finds a **cheaper third path**: **cucumber-js already emits `gherkinDocument` envelopes in the NDJSON we're consuming.** We can read the AST for free from the same file we're already parsing for pass/fail — no new dep, no regex fragility, no Gherkin re-parse. `gherkin-official` would only be needed if we want to parse `.feature` files that cucumber-js didn't execute (e.g., a scenario filtered out by `--tags`); even then, gherkin-official is cheap (pure Python, MIT, 9.5KB install) and trivial to swap in later. Recommendation: **drop the filesystem regex scrape plan; consume `gherkinDocument` envelopes from NDJSON.** Keep `.feature` file globbing only as a discovery mechanism (to detect files that produced zero envelopes — file-level `H6` rule). This is a simpler and more robust MVP than the PRD's current plan.

**Test implication:** Tests become cleaner — assertions on a typed AST dict rather than regex over raw text. Add one fixture with a file present-on-disk-but-not-in-NDJSON (filtered out) to confirm the "no gherkinDocument → file exists" detection works for H6.

---

### Python HTML emission library comparison (breadth check)

| Library                   | Verdict for our use | Notes                                                                                                                                                                                                        |
| ------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Jinja2 (chosen)**       | **Best fit**        | Template inheritance (useful for per-card sub-templates), autoescape, macros, and the de-facto Python default. No compelling reason to deviate.                                                              |
| **chevron** (mustache)    | Not recommended     | Logic-less mustache implementation. Simpler but has no inheritance or macros. **Not actively maintained** per recent search results. Would force logic into Python that Jinja2 handles cleanly in templates. |
| **Hand-rolled f-strings** | Not recommended     | Tempting for ~1500 lines of HTML, but XSS escape is manual and the `<script>` data blob carrying scenario JSON is exactly where hand-escaping goes wrong (`</script>` break-out).                            |
| **htpy / dominate**       | Not recommended     | "HTML from dataclasses" libraries. Fine for small widgets, but scenario cards + modals are template-shaped content, not programmatic DOM construction.                                                       |

**Design impact:** **Stick with Jinja2 as the PRD already implies.** No change.

**Test implication:** None beyond the Jinja2 section above.

**Sources:**

1. [Evaluation and comparison of Python templating libraries (twolfson gist)](https://gist.github.com/twolfson/b861c182107cefcef086266c3b4b83a6) — accessed 2026-04-23
2. [Opensource.com — 3 Python template libraries compared](https://opensource.com/resources/python/template-libraries) — accessed 2026-04-23
3. [Superset PR #11617 — chevron vs jinja discussion](https://github.com/apache/superset/pull/11617) — accessed 2026-04-23

---

### Prior-art BDD dashboard tools (survey, not adoption)

**Scope:** Quick survey to confirm we are not reinventing a wheel. TL;DR — the opinion engine is the differentiator. No prior-art tool does the D1–D6/H1–H7 rule-based grading we need.

| Tool                                | What it does                                                                                                                                | What we can learn                                                                                                                      | Do we adopt it?                                                                                                            |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **cucumber-html-reporter** (Node)   | Converts Cucumber JSON (legacy, not NDJSON) to per-scenario HTML. 3 themes (Bootstrap, Foundation, Simple). Runs in a Node `afterAll` hook. | Per-scenario-card UI pattern. Consolidates multiple JSON inputs (we only have one). Shows feature-level + scenario-level aggregates.   | No — consumes legacy JSON, not the NDJSON Feature 1 emits, and has no opinion engine.                                      |
| **multiple-cucumber-html-reporter** | Richer Node reporter — searchable/filterable, per-browser/device metadata, mini-dashboards per feature.                                     | Searchable scenario table, metadata panel, feature grouping (matches our layout intent).                                               | No — same reason. Plus Node-side.                                                                                          |
| **Allure (allure-behave)**          | Framework-agnostic HTML report with flakiness tracking, per-step timing, environment metadata, trends over runs, history tab.               | **Trend chart** — Allure stores last N runs and draws pass/fail trends, exactly our US-005 target. **Severity buckets** on failures.   | No — server-side Java tool, too heavy for a local dev tool. But lift the trend-chart UX (sparkline/line over last-N runs). |
| **Pickles / picklesdoc**            | .NET living-docs generator: Gherkin → static HTML docs (no execution data). Outputs MD/Word/Excel too.                                      | Shows a "feature directory" tree + scenario cards as documentation.                                                                    | No — pure documentation, no pass/fail, no opinion engine. Different use case.                                              |
| **BehaveX** (Python)                | Behave + pytest test runner with HTML reports, execution metrics (automation rate, pass rate, step timings).                                | Per-scenario timing, which we could add as a cheap bonus (NDJSON gives us `testStepStarted.timestamp` + `testStepFinished.timestamp`). | No — framework-coupled to Behave; we use cucumber-js.                                                                      |

**Conclusion — is this a reinvention?** **No.** Our feature combines three axes that no single tool offers together:

1. Cucumber Messages NDJSON 32.x as input (most reporters consume the legacy JSON).
2. A 13-rule **opinion engine** grading scenario quality beyond pass/fail (unique — Allure has "flakiness," but not domain-specific lint rules).
3. Per-endpoint and per-UC coverage grading with Full/Partial/None rubric (unique).

The **lesson to steal**: Allure's trend-history UX is already in our US-005. Multiple-cucumber-html-reporter's per-feature metadata panel is a reasonable layout reference. Neither invalidates our plan.

**Sources:**

1. [cucumber-html-reporter npm](https://www.npmjs.com/package/cucumber-html-reporter) — accessed 2026-04-23
2. [multiple-cucumber-html-reporter npm](https://www.npmjs.com/package/multiple-cucumber-html-reporter) — accessed 2026-04-23
3. [Allure Report docs](https://docs.qameta.io/allure/) — accessed 2026-04-23
4. [picklesdoc.com](https://www.picklesdoc.com/) — accessed 2026-04-23
5. [BehaveX on PyPI](https://pypi.org/project/behavex/) — accessed 2026-04-23

**Design impact:** No change to scope. Confirms the build-vs-adopt decision is "build" — but we should explicitly mention in the design that the trend-chart UX is inspired by Allure, to save future reviewers a "why didn't we use Allure?" round.

**Test implication:** None — survey only.

---

### Python-side non-dep choices (stdlib)

| Concern         | Choice                                  | Rationale                                                                                                                                                   |
| --------------- | --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| NDJSON parsing  | stdlib `json.loads` over `splitlines()` | No dep. Streaming via `for line in f:` is equally valid if files grow large; 33-scenario suite files are < 1MB — read-all-then-parse is simpler and faster. |
| In-memory types | stdlib `dataclasses`                    | Matches PRD §6 model names verbatim (`Scenario`, `Feature`, `Finding`, `CoverageGrade`, `RunSummary`). Frozen + slots for immutability.                     |
| CLI             | stdlib `argparse`                       | Zero deps; the tool has only a handful of flags (`--since`, `--output`, `--ndjson`). `click` is not worth the dep here.                                     |
| Testing         | `pytest` (already present)              | Dev group in `backend/pyproject.toml`. Golden-file test via `syrupy` is optional; a plain text-diff against a checked-in golden is enough.                  |

**Design impact:** Confirms "no new runtime deps except Jinja2." No change.

**Test implication:** Golden-file test strategy is already in US-007 — no change.

---

## Not Researched (with justification)

- **cucumber-js, @playwright/test, tsx, React, Vite, TypeScript** — shipped in Feature 1 (`docs/research/2026-04-23-bdd-suite.md` covers them). This feature consumes their NDJSON output; it does not extend them.
- **FastAPI, Pydantic, SQLAlchemy, uvicorn** — not touched by this feature. The dashboard analyzer is outside the `hangman` app package.
- **pytest, ruff, mypy** — already standard tooling. No version bump required.
- **uv** — workflow tool; no changes to its usage.

---

## Open Risks

1. **Chart.js version pin drift (P3).** The PRD currently pins 4.4.0 in the CDN URL. Recommend bumping to 4.5.1 for free bug fixes (no breaking changes). Either is fine; keep the pin **exact** (not `@4` / `@latest`) so the generated HTML is byte-deterministic across runs on unchanged input (required for US-007 "running twice produces byte-identical output").

2. **Load-bearing finding — `gherkinDocument` is free in the NDJSON.** The PRD §5 "Gherkin scraping, not AST" framing is stale. cucumber-js already emits `gherkinDocument` envelopes in `cucumber.ndjson`, giving us a ready-to-consume AST without adding `gherkin-official`. This simplifies the design and removes the "regex is fragile" known-limitation from §5. **Recommend patching PRD to v1.1** before Phase 3 begins — change the framing from "MVP scrapes via regex" to "MVP consumes `gherkinDocument` envelopes from the NDJSON; regex is used only for endpoint-template normalization (`/games/1/guesses` → `/games/{id}/guesses`) within step text."

3. **`testCaseFinished` has no `status` field.** The PRD §6 data model implies per-scenario pass/fail comes straight from NDJSON. It doesn't — scenario outcome is computed from the worst `testStepFinished.testStepResult.status` across that scenario's steps. Small but concrete: the design should name this rollup function and unit-test it against all 7 status-enum values (`UNKNOWN`, `PASSED`, `SKIPPED`, `PENDING`, `UNDEFINED`, `AMBIGUOUS`, `FAILED`).

4. **`willBeRetried=true` edge case.** Not currently an issue (no retries configured in Feature 1), but the design should have a stance: treat `testCaseFinished.willBeRetried=true` as "ignore, wait for retry." A unit test with a fixture NDJSON containing a retry will future-proof this.

5. **Jinja2 autoescape drift.** `select_autoescape(["html"])` must be set at `Environment` creation. A later refactor dropping it re-introduces XSS risk via scenario text / findings text that could contain user-controlled HTML from `.feature` files. **Add one unit test** asserting `env.autoescape` is truthy for `.html` templates — this is the cheapest regression guard.

6. **CDN availability in offline mode.** Accepted trade-off per PRD §5 (local dev tool). If offline use ever becomes a real need, swap the CDN `<script>` for an inlined `chart.umd.min.js` (adds ~200KB to the HTML). Not a Phase 3 concern.

7. **No Cucumber Messages Python library adopted.** We're hand-parsing `dict` envelopes rather than using a typed Python binding. There is no first-party Python binding of Cucumber Messages (only the gherkin-official parser, which only does the parse side — not the full schema). Our dataclass shims are the cheapest path. If the 32.x schema ever bumps major (33.x), our `protocolVersion` guard will fail loud with a clear message — this is the designed failure mode.

---

## Summary for caller

Research complete.
Brief: `docs/research/2026-04-23-bdd-dashboard.md`
Libraries researched: 5 in depth (Jinja2, Chart.js CDN, Cucumber Messages schema, gherkin-official, prior-art tool survey) + 1 breadth (HTML-emission comparison).
Design-changing findings: 3 (Chart.js 4.4.0 → 4.5.1 bump, gherkinDocument free-in-NDJSON, testCaseFinished status rollup).
Open risks: 7.

**Key finding:** cucumber-js already emits `gherkinDocument` envelopes in the NDJSON — we get the full AST for free and can drop the PRD's "regex scrape" MVP plan in favour of typed AST consumption. This is cleaner, more robust, and adds zero new dependencies. Recommend bumping the PRD to v1.1 to reflect this before Phase 3 design starts.
