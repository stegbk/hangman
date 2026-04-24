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

---

## Addendum — LLM evaluation path (2026-04-24)

**Context:** Design pivoted from a static rule engine to an LLM-based evaluator using the Anthropic API. The 13-criterion rubric is still the scoring contract, but it is applied by a Claude model (not hand-rolled Python rules) and delivered via a forced `ReportFindings` tool call. This addendum researches every LLM-specific surface the new design touches. Pre-existing sections above remain valid; they cover the non-LLM stack (NDJSON, Jinja2, Chart.js, prior-art survey).

### Libraries Touched (delta)

| Library                            | Our Version  | Latest Stable                                                       | Breaking Changes Since Ours                   | Source                                                                                                         |
| ---------------------------------- | ------------ | ------------------------------------------------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **`anthropic` Python SDK**         | n/a (to add) | 0.97.0 (2026-04-23)                                                 | Adding fresh                                  | [PyPI anthropic](https://pypi.org/project/anthropic/) (accessed 2026-04-24)                                    |
| **Claude API `anthropic-version`** | n/a          | `2023-06-01` (stable header; SDK pins it by default)                | No; header is date-pinned and has not rotated | [SDK docs — Default headers](https://platform.claude.com/docs/en/api/sdks/python) (accessed 2026-04-24)        |
| **Claude models**                  | n/a          | `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001` | N/A (first adoption)                          | [Models overview](https://platform.claude.com/docs/en/docs/about-claude/models/overview) (accessed 2026-04-24) |

---

### 1. `anthropic` Python SDK

**Versions:** ours=none (adding fresh), latest=**0.97.0** (released 2026-04-23 on PyPI — same day as the initial brief).

**Minimum Python:** `>=3.9`. Our runtime is 3.12 → compatible; install from the default group in `backend/pyproject.toml` `[dependency-groups.dashboard]` alongside Jinja2. No stdlib compatibility shim needed.

**Breaking changes since ours:** N/A (net-new). SDK follows SemVer but documents that minor bumps may include type-only or internal-path changes — pin a conservative range `"anthropic>=0.97,<1.0"`.

**Recommended pattern (verified from official SDK docs):**

```python
import os
from anthropic import Anthropic

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[...],        # list[dict] with cache_control on rubric block
    tools=[REPORT_TOOL], # ReportFindings schema with cache_control
    tool_choice={"type": "tool", "name": "ReportFindings"},
    messages=[{"role": "user", "content": "<scenario json>"}],
)
# response.content -> list[ContentBlock]; look for block.type == "tool_use"
```

**Sync vs async:** Both provided. `Anthropic` (sync) and `AsyncAnthropic` (async). For our 44-call batch, **sync + bounded concurrency via `concurrent.futures.ThreadPoolExecutor`** is simpler than asyncio and matches stdlib parity; async adds an event loop the rest of the codebase doesn't have. Recommend sync + pool size 5–8 (well under Tier-2 Sonnet RPM of 1,000). No need for `aiohttp` extras.

**Retries:** SDK retries **2 times by default** with exponential backoff on: connection errors, 408, 409, 429, and ≥500. Configurable via `Anthropic(max_retries=N)` or per-call `client.with_options(max_retries=N).messages.create(...)`. `retry-after` header is honored on 429. Errors surface as typed exceptions: `anthropic.RateLimitError` (429), `anthropic.APIConnectionError`, `anthropic.APITimeoutError`, `anthropic.APIStatusError` (generic).

**Timeouts:** Default 10 minutes. Overridable with `Anthropic(timeout=20.0)` or `httpx.Timeout(60.0, read=5.0, write=10.0, connect=2.0)`. For our rubric calls (short output, tool-use JSON) a 60–120s per-call timeout is generous.

**Import path for Messages API + tool use:** Stable — `client.messages.create(...)` with top-level `tools=[...]`, `tool_choice={...}`, and `system=[...]`. The experimental `client.beta.messages.tool_runner(...)` + `@beta_tool` decorator exists, but it drives an agentic loop with auto tool-execution — **not what we want.** Our use is single-turn forced structured output (the LLM calls exactly one tool once and we collect its `input` dict). Use the plain `messages.create` path.

**Sources:**

1. [Anthropic Python SDK on PyPI — 0.97.0 release metadata](https://pypi.org/project/anthropic/) — accessed 2026-04-24
2. [Official SDK reference — sync/async, retries, timeouts](https://platform.claude.com/docs/en/api/sdks/python) — accessed 2026-04-24
3. [anthropic-sdk-python GitHub repo](https://github.com/anthropics/anthropic-sdk-python) — accessed 2026-04-24

**Design impact:**

- Add `"anthropic>=0.97,<1.0"` to `backend/pyproject.toml` — same dependency group as Jinja2 (dashboard-only, not a runtime dep of the FastAPI app).
- Use sync `Anthropic` client; wrap in a `ClaudeEvaluator` class with a single `evaluate(scenario_or_feature) -> list[Finding]` method for testability.
- Leave SDK's default `max_retries=2` in place; do NOT reduce it. Add one layer of our own around the evaluator that catches `anthropic.APIError` subclasses and degrades to "LLM unavailable — skipping opinion engine, emitting bare results section" (non-fatal, preserves the value of the deterministic dashboard half).
- Concurrency: use `concurrent.futures.ThreadPoolExecutor(max_workers=6)` to issue the 44 calls in parallel. A semaphore is unnecessary at this scale; the SDK's internal backoff handles transient 429s.
- Model ID: plumb `--model` CLI flag through to the evaluator; default to `"claude-sonnet-4-6"`. Accept alias form (no dated suffix) so KC can pass `--model haiku` or `--model opus` and we map to the full IDs.

**Test implication:**

- Unit tests mock `anthropic.Anthropic` (the SDK is a legitimate external API — per `testing.md` mocking rules, Anthropic is Stripe/OpenAI-adjacent, mock it).
- One integration test (opt-in via `ANTHROPIC_API_KEY` env; skipped in CI without the key) verifies a live round-trip with a tiny rubric over a canned scenario and asserts the returned Finding set parses cleanly.
- Add a unit test that exercises the "SDK raises `RateLimitError`" path to confirm we catch + degrade to no-opinion-engine mode rather than crashing the dashboard build.
- Add a unit test that exercises the "SDK raises `APIConnectionError`" path (offline mode) with the same degradation.

---

### 2. Prompt caching (`cache_control: {"type": "ephemeral"}`)

**Confirmed mechanics (from live docs):**

- **Attach points:** Tools array, System array, and individual Messages content blocks. Cache order is **Tools → System → Messages** — anything before your last `cache_control` breakpoint gets cached.
- **Breakpoints:** Up to **4 explicit `cache_control` markers per request.** Placement must follow cache order (a breakpoint on system implicitly caches the tools above it). There is also an "automatic" top-level `cache_control` field on the request that applies to the last cacheable block, but explicit placement is clearer and recommended for our case.
- **TTL:** Default **5 minutes** (`"ttl"` field absent or set to 5m). Optional **1 hour** via `{"type": "ephemeral", "ttl": "1h"}` at 2x base input token price per write (vs 1.25x for 5m). When mixing TTLs in one prompt, longer-TTL entries must appear first in the hierarchy.
- **Cache-read discount:** **0.1× base input token price (90% off).** Cache-write surcharge: 1.25× for 5m, 2.0× for 1h. Cache reads do NOT count against ITPM for 4.x models (older models marked † still count them).
- **Minimum cacheable length:** **4,096 input tokens** for Opus 4.7, Opus 4.6, Sonnet 4.6, Haiku 4.5 (all the models we'd use). Below this, `cache_control` silently no-ops (check `usage.cache_creation_input_tokens` + `usage.cache_read_input_tokens` to verify — both zero = fell short).
- **Lookback window:** 20 blocks per breakpoint.
- **Invalidation rules (critical for our design):**
  - Changing tool definitions invalidates tools + system + messages.
  - Changing `tool_choice` invalidates tools + system, but NOT messages.
  - Changing images or system content invalidates tools + system.
  - Changing the variable user message only invalidates that message's cache layer — upstream blocks stay hot.
- **Workspace isolation (2026-02-05 change):** Caches are isolated per workspace, not per organization. Not relevant for our single-user local dev tool; flagged for completeness.

**Cache hit verification:**

```python
print(response.usage.cache_read_input_tokens)    # >0 on a hit
print(response.usage.cache_creation_input_tokens) # >0 on the first call only
```

**Recommended pattern for our use (confirmed best practice):**

Put the 13-criterion rubric in the **system array** as one large text block with `cache_control: {"type": "ephemeral"}` at its end. Put the `ReportFindings` tool definition in **tools** with `cache_control` on it. The per-scenario variable payload (scenario name, steps, pass/fail, AST snippet) goes in the **user message without** `cache_control`. This yields a hot cache for the rubric + tool across all 44 calls in a single run (well within the 5-minute TTL for 44 parallel calls completing in < 60s). First call pays 1.25× write; remaining 43 calls pay 0.1× read.

**Sources:**

1. [Prompt caching — Claude API docs](https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching) — accessed 2026-04-24
2. [Hacker News — community verification of Anthropic cache breakpoints / 90% savings](https://news.ycombinator.com/item?id=47363074) — accessed 2026-04-24
3. [The IllusionCloud Blog — cache breakpoint depth patterns (2026-01)](https://blog.illusioncloud.biz/2026/01/13/prompt-caching-anthropic-cache-breakpoints/) — accessed 2026-04-24

**Design impact:**

- **Minimum rubric length matters:** The rubric MUST exceed **4,096 tokens** to be cacheable on Sonnet 4.6 / Haiku 4.5 / Opus 4.7. At ~300 words per criterion × 13 criteria ≈ 3,900 words ≈ 5,000 tokens — almost certainly fits naturally. If a future PR compacts the rubric to under 4,096 tokens, caching silently stops working and cost jumps 3–4× per run. **Add a length guard + emit a warning if `cache_creation_input_tokens == 0` on the first call.**
- **Two breakpoints:** one on the tool schema, one at the end of the system rubric block. Leaves 2 breakpoints free for future expansion.
- **5-minute TTL is sufficient** for a local run (all 44 calls finish inside 1 minute with parallelism). Do NOT pay the 2× surcharge for 1h TTL — YAGNI.
- **Rubric edit invalidates cache mid-run:** the rubric text is static across a single run, so this is only a risk if someone edits while the tool is executing. Not a real concern.
- **Tool_choice change = system cache invalidation:** Keep `tool_choice` fixed at `{"type": "tool", "name": "ReportFindings"}` across all 44 calls. Do not vary it per call — would trash the system+tools cache.

**Test implication:**

- Unit test: mock the SDK response's `usage` object and assert our evaluator reads `cache_read_input_tokens` and logs cache-hit-rate at the end of the run (observability).
- Unit test: the prompt-assembly function emits exactly 2 `cache_control` markers in the right places.
- Integration test (opt-in): run evaluator twice in sequence against the same rubric + tool; second run reports `cache_read_input_tokens > 0` (verifies real cache hit, not just that we asked for it).

---

### 3. Tool use / structured output (forced `ReportFindings` tool)

**Confirmed mechanics:**

- **Tool definition shape:**

  ```python
  REPORT_TOOL = {
      "name": "ReportFindings",
      "description": "Report BDD rubric findings for this scenario/feature. Use exactly once.",
      "input_schema": {
          "type": "object",
          "properties": {
              "findings": {
                  "type": "array",
                  "items": {
                      "type": "object",
                      "properties": {
                          "rule_id": {"type": "string", "enum": ["D1", "D2", ...]},
                          "severity": {"type": "string", "enum": ["pass", "warn", "fail"]},
                          "message": {"type": "string"},
                          "quote": {"type": "string"},
                      },
                      "required": ["rule_id", "severity", "message"],
                  }
              }
          },
          "required": ["findings"],
      },
      "cache_control": {"type": "ephemeral"},
  }
  ```

- **Forcing the tool:** `tool_choice={"type": "tool", "name": "ReportFindings"}` forces Claude to call this exact tool. Per docs: when `tool_choice` is `any` or `tool`, the API prefills the assistant message to force a tool call — **the model emits no natural-language preamble, only tool_use blocks.** This is exactly the shape we want.
- **Response shape:** `response.content` is `list[ContentBlock]`. With forced tool use, the only block we expect is `{"type": "tool_use", "id": "toolu_...", "name": "ReportFindings", "input": {"findings": [...]}}`. `response.stop_reason == "tool_use"`.
- **Strict tool use (`strict: true`):** Optional flag that guarantees tool inputs match the schema exactly. Trade-offs: no recursive schemas, must use `additionalProperties: false`, may hit "schema is too complex" errors if findings array grows too nested. For our flat-ish schema (array of 4-field objects), `strict: true` is a cheap correctness win — **enable it.**
- **Error modes (observed):**
  - If the model doesn't return tool_use (rare with forced tool_choice but possible on refusal / overlong scenario): `response.content[0].type == "text"`. **Handle this by treating it as "no findings" + logging the raw text for diagnostics.**
  - If schema validation fails (possible without `strict: true`): the `input` dict may be malformed. Pydantic-validate on our side anyway (defense in depth).
  - `stop_reason == "max_tokens"`: truncated mid-tool-call. Bump `max_tokens` (1024 → 4096 for long findings lists).
- **Extended thinking + forced tool use incompatibility:** `tool_choice: {"type": "tool", "name": "..."}` is **NOT supported** with extended thinking on Sonnet 4.6 / Haiku 4.5 (the Opus 4.7 model uses "adaptive thinking" which IS supported). Since we don't need extended thinking for this task (it's a structured classification, not multi-step reasoning), this is a non-issue — just do not enable `thinking` on the request.

**Pydantic-friendly pattern:**

```python
from pydantic import BaseModel

class Finding(BaseModel):
    rule_id: Literal["D1", "D2", "D3", "D4", "D5", "D6", "H1", "H2", "H3", "H4", "H5", "H6", "H7"]
    severity: Literal["pass", "warn", "fail"]
    message: str
    quote: str | None = None

class ReportFindingsInput(BaseModel):
    findings: list[Finding]

# After call:
tool_block = next(b for b in response.content if b.type == "tool_use")
findings = ReportFindingsInput.model_validate(tool_block.input).findings
```

Generate the JSON schema from the Pydantic model via `ReportFindingsInput.model_json_schema()` to keep one source of truth. This is the standard pattern per the community best-practices article.

**Sources:**

1. [Tool use overview — Claude API docs](https://platform.claude.com/docs/en/docs/build-with-claude/tool-use/overview) — accessed 2026-04-24
2. [Define tools — tool_choice semantics and forced tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools) — accessed 2026-04-24
3. [How tool use works — stop_reason and content block shapes](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works) — accessed 2026-04-24
4. [Agenta blog — structured outputs + function calling best practices (2026)](https://agenta.ai/blog/the-guide-to-structured-outputs-and-function-calling-with-llms) — accessed 2026-04-24

**Design impact:**

- Use `tool_choice={"type": "tool", "name": "ReportFindings"}` — not `"any"` — so there is exactly one tool in the toolset and the model is pinned to it.
- Set `"strict": true` on the tool definition. The 13-rule, 4-field-per-finding schema is well under complexity limits.
- Generate the `input_schema` from a Pydantic `ReportFindingsInput` model via `.model_json_schema()`; validate the response `input` dict through the same Pydantic model before converting to dataclasses. Two wins: (a) single source of truth, (b) defense-in-depth against schema drift.
- Handle the `text`-response escape hatch: if no `tool_use` block appears, log + emit an empty findings list for that scenario (do not crash the whole dashboard build).
- Do NOT enable extended thinking on any request — forced tool choice is incompatible on Sonnet/Haiku 4.x.

**Test implication:**

- Unit test: "tool_use block found → findings parsed cleanly" (golden happy-path).
- Unit test: "only text block → empty findings returned + warning logged" (degradation path).
- Unit test: "max_tokens truncation → raises diagnostic error with scenario ID" (we need to know which call was clipped).
- Unit test: "malformed `input` dict (bad rule_id enum) → Pydantic ValidationError surfaced with scenario context."
- The Pydantic model doubles as a testable contract for the schema itself.

---

### 4. Model selection (Opus 4.7 / Sonnet 4.6 / Haiku 4.5)

**Confirmed specs (from Models overview):**

| Model                 | API ID                      | Alias               | Context window | Max output | Input $/MTok | Output $/MTok |
| --------------------- | --------------------------- | ------------------- | -------------- | ---------- | -----------: | ------------: |
| **Claude Opus 4.7**   | `claude-opus-4-7`           | `claude-opus-4-7`   | 1M tokens      | 128K       |           $5 |           $25 |
| **Claude Sonnet 4.6** | `claude-sonnet-4-6`         | `claude-sonnet-4-6` | 1M tokens      | 64K        |           $3 |           $15 |
| **Claude Haiku 4.5**  | `claude-haiku-4-5-20251001` | `claude-haiku-4-5`  | 200K tokens    | 64K        |           $1 |            $5 |

Prompt caching:

- Cached **write** (5m TTL): 1.25× input price (e.g., Sonnet $3.75/MTok, Haiku $1.25/MTok, Opus $6.25/MTok).
- Cached **read**: 0.1× input price (Sonnet $0.30/MTok, Haiku $0.10/MTok, Opus $0.50/MTok).

**Recommended use-case fit (per Anthropic's own guidance + our task shape):**

| Use-case signal                                    | Best model                        | Why                                                                 |
| -------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------- |
| Cheap cycle during dev, quick feedback             | **Haiku 4.5** (`--model haiku`)   | Fastest; "near-frontier intelligence"; 10× cheaper output than Opus |
| Default for normal runs                            | **Sonnet 4.6** (`--model sonnet`) | Best speed/intelligence balance; 200K-token rubric fits easily      |
| Deep-dive run when findings look shallow/incorrect | **Opus 4.7** (`--model opus`)     | Most capable; highest fidelity; use when cost is justified          |

**Context-window fit:** Our prompts are small (rubric ~5K tokens + per-scenario payload ~2K tokens + tool definition ~1K). Even Haiku's 200K window is ~25× what we need. No model is excluded on size.

**Sources:**

1. [Claude Models overview (pricing, context, IDs)](https://platform.claude.com/docs/en/docs/about-claude/models/overview) — accessed 2026-04-24
2. [Prompt caching docs (cached read/write multipliers)](https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching) — accessed 2026-04-24

**Design impact:**

- Default `--model sonnet` (`claude-sonnet-4-6`). Aliases: `haiku` → `claude-haiku-4-5`, `opus` → `claude-opus-4-7`, plus pass-through for any literal `claude-*` ID.
- Validate unknown model names at CLI-parse time (not inside the SDK call) to fail fast with a helpful message.
- Note in design: Haiku is compatible with everything we need (forced tool use + prompt caching ≥ 4,096 tokens + 200K context). No capability-gating between the three models for our workload.

**Test implication:**

- Unit test: CLI flag `--model haiku` resolves to `claude-haiku-4-5`; `--model opus` → `claude-opus-4-7`; unknown alias → clear error.
- Parametrize the evaluator unit tests over all three model IDs (with mocked SDK) to confirm no model-specific branching slips in.

---

### 5. Rate limits + retries for a 44-call burst

**Confirmed limits (standard Tier; worst-case model for our burst):**

| Tier  | Model      | RPM   | ITPM    | OTPM   |
| ----- | ---------- | ----- | ------- | ------ |
| **1** | Sonnet 4.x | 50    | 30,000  | 8,000  |
| **1** | Haiku 4.5  | 50    | 50,000  | 10,000 |
| **1** | Opus 4.x   | 50    | 30,000  | 8,000  |
| **2** | Sonnet 4.x | 1,000 | 450,000 | 90,000 |
| **2** | Haiku 4.5  | 1,000 | 450,000 | 90,000 |
| **2** | Opus 4.x   | 1,000 | 450,000 | 90,000 |

**Cached input tokens do NOT count against ITPM for 4.x models** — a key multiplier. With our rubric cached, the effective ITPM budget goes ~5× further.

**Our 44-call burst profile:**

- 44 calls × ~2K uncached input + ~5K cached read input per call ≈ 88K uncached + 220K cached input tokens total per run. Only 88K + 88K (cache create amortized) counts against ITPM.
- 44 × ~1K output ≈ 44K output tokens per run.
- At Tier 1 Sonnet: 30K ITPM means the full run's 88K ITPM-counted input would take ~3 minutes if issued serially. At Tier 2, < 12s. **Tier 2 is the comfortable floor.**
- RPM: 44 requests in ~60s = 0.73 RPS ≈ 44 RPM. Fits Tier 1's 50 RPM with no headroom; Tier 2's 1,000 RPM is trivial.

**SDK behavior on 429:**

- Raises `anthropic.RateLimitError` after exhausting retries (default 2).
- `retry-after` header honored during retry backoff.
- Response headers `anthropic-ratelimit-{requests,input-tokens,output-tokens}-{limit,remaining,reset}` provide live budget (accessible via `client.messages.with_raw_response.create(...)` + `.headers.get(...)`).

**Concurrency recommendation:**

- **Sequential + SDK retries:** ~60s per run on Tier 2 Sonnet (serial latency dominated by Sonnet response time).
- **Bounded parallelism** (`ThreadPoolExecutor(max_workers=6)`): ~10s per run on Tier 2. Simpler than async; no event loop dependency; still headroom on RPM.
- **Avoid unbounded parallelism:** At Tier 1 (50 RPM), 44 concurrent calls fire past the per-second limit (which the docs call out is enforced as ~1 RPS for 60 RPM). Stick with pool size ≤ 8 to be safe across tiers.
- **No first-party `anthropic-client` concurrency helper** exists (beyond the `Message Batches API`, which is async, queued, and 24h-SLA — not appropriate for an interactive `make dashboard` run). Confirmed not applicable.

**Sources:**

1. [Rate limits — Claude API docs (tiers, RPM/ITPM/OTPM)](https://platform.claude.com/docs/en/api/rate-limits) — accessed 2026-04-24
2. [Python SDK docs — retries, timeouts, error types](https://platform.claude.com/docs/en/api/sdks/python) — accessed 2026-04-24

**Design impact:**

- Document **Tier 2 as the minimum supported tier** in the feature README + CLI error message (Tier 1 works, but ITPM serializes the burst into a multi-minute wait; poor UX).
- Concurrency: `ThreadPoolExecutor(max_workers=6)`. Rely on the SDK's `max_retries=2` default; do NOT reduce it and do NOT try to hand-roll backoff on top of it (common mistake — double-backoff thrashes).
- Rate-limit error handling: on `RateLimitError` after SDK retries exhaust, **log once, skip that scenario, continue the run**, and emit a warning banner in the dashboard "N scenarios skipped due to rate limiting — rerun `make dashboard`."
- Plumb `retry-after` / `anthropic-ratelimit-*` headers into the evaluator's diagnostic log (opt-in via `--verbose`) for users who hit tier limits and need to understand why.

**Test implication:**

- Unit test: `RateLimitError` raised by the SDK mock → evaluator marks that scenario as "rate-limited" in its report, does NOT crash the batch.
- Unit test: `ThreadPoolExecutor` shutdown on KeyboardInterrupt (Ctrl+C during run) cancels outstanding calls cleanly.
- Observability test: the evaluator logs the final run's `anthropic-ratelimit-input-tokens-remaining` so a developer can spot "I'm close to my tier limit" before it bites.

---

### 6. Streaming vs non-streaming

**Confirmed:** Streaming is fully supported via `client.messages.stream(...)` (helper) or `create(..., stream=True)` (iterator). It's designed for progressive text display.

**Our use case:** Each call is one short JSON tool-use output (≤ 1K tokens). We don't render the response to the user incrementally — we parse the final `tool_use` block and move on. Streaming offers no UX value here.

**Trade-offs of streaming for our task:**

- ✅ Slightly lower TTFT perceived latency (irrelevant for non-interactive `make` step).
- ✅ Avoids the SDK's 10-minute long-request `ValueError` (irrelevant — our calls are ≤ 30s even on Opus).
- ❌ Harder to consume `tool_use` content from the stream (requires accumulating fragments and parsing at `message_stop`).
- ❌ Interacts awkwardly with `ThreadPoolExecutor` (each thread owns an open SSE connection for the call's duration).

**Sources:**

1. [Python SDK docs — streaming section](https://platform.claude.com/docs/en/api/sdks/python) — accessed 2026-04-24

**Design impact:** Use **non-streaming** `messages.create(stream=False)` (the default). No design change needed — just document the choice in the evaluator module docstring so a future reader doesn't "optimize" it to streaming and regress maintainability.

**Test implication:** None beyond "we don't test streaming." Standard coverage sufficient.

---

### 7. Cost estimation per run

**Assumptions (from the caller):** ~150K total input tokens + ~50K total output tokens per full run (across all 44 calls).

**Assumptions (from us, confirmed against the rubric math):**

- Rubric ~5K tokens, cached. Sent on every call but only the first call pays the 1.25× cache-write surcharge; remaining 43 read at 0.1×.
- Tool schema ~1K tokens, cached with the rubric (same breakpoint group).
- Per-call variable payload ~2K tokens × 44 calls ≈ 88K uncached input.
- Cache write (one-shot): ~6K tokens. Cache read: ~6K × 43 = ~258K tokens.
- Grand totals: ~88K uncached input + ~6K cache-write + ~258K cache-read + ~50K output.

**Cost per full run:**

| Model          | Uncached input (88K × base) | Cache write (6K × 1.25×) | Cache read (258K × 0.1×) |  Output (50K × out$) | **Total/run** |
| -------------- | --------------------------: | -----------------------: | -----------------------: | -------------------: | ------------: |
| **Haiku 4.5**  |         88K × $1/M = $0.088 |    6K × $1.25/M = $0.008 |  258K × $0.10/M = $0.026 |  50K × $5/M = $0.250 |    **~$0.37** |
| **Sonnet 4.6** |         88K × $3/M = $0.264 |    6K × $3.75/M = $0.023 |  258K × $0.30/M = $0.077 | 50K × $15/M = $0.750 |    **~$1.11** |
| **Opus 4.7**   |         88K × $5/M = $0.440 |    6K × $6.25/M = $0.038 |  258K × $0.50/M = $0.129 | 50K × $25/M = $1.250 |    **~$1.86** |

**Sanity check against uncached baseline** (what it would cost without prompt caching — rubric & tool sent fully on every call, pushing input tokens to ~350K):

| Model      | Uncached total/run (no caching) | With caching (above) | Savings |
| ---------- | ------------------------------: | -------------------: | ------: |
| Haiku 4.5  |                          ~$0.60 |               ~$0.37 |    ~38% |
| Sonnet 4.6 |                          ~$1.80 |               ~$1.11 |    ~38% |
| Opus 4.7   |                          ~$3.00 |               ~$1.86 |    ~38% |

Savings are dominated by rubric re-transmission avoidance — the full 90% cache-read discount only applies to the cached portion, so the blended savings for this workload come in around 35–40%. Still, Sonnet at **~$1.11/run** and Haiku at **~$0.37/run** is well inside "iterate freely" territory for a dev tool. Opus at **~$1.86/run** is reasonable for deep-dive runs.

**Sources:**

1. [Claude Models overview — pricing per model](https://platform.claude.com/docs/en/docs/about-claude/models/overview) — accessed 2026-04-24
2. [Prompt caching — cache read/write multipliers](https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching) — accessed 2026-04-24

**Design impact:**

- Display an estimated cost + the observed `usage` totals at the end of each `make dashboard` run. Developers learn their own cost curve; avoids nasty surprises.
- CLI flag defaults make economic sense: `sonnet` is the right default for routine use; `--model haiku` for fast iteration; `--model opus` only when the rubric findings look unreliable and you want to burn 2× the budget to double-check.
- `--no-llm` flag: emit the dashboard with the deterministic half only (no opinion engine). Free. Useful for CI or when `ANTHROPIC_API_KEY` is absent.

**Test implication:**

- Unit test: the cost-display function reads the SDK's `usage` object (including `cache_creation_input_tokens` and `cache_read_input_tokens`) and produces a rounded dollar estimate using pinned per-model price constants. Guards against future maintainer forgetting to update prices when Anthropic changes them (we will catch drift; the printed number becomes visibly wrong).
- Keep model prices in a single `PRICING: dict[str, tuple[float, float]]` module constant so it's trivially updatable in one place.

---

### Addendum summary — load-bearing findings

Three additional findings that should drive PRD v2.0 corrections beyond what the caller already flagged (API key required, tool use for structured findings, prompt caching for cost control):

1. **Rubric length must exceed 4,096 tokens to be cacheable on 4.x models.** The 13-criterion rubric is naturally in this range (~5K tokens), but a future compaction PR could silently drop caching and triple the per-run cost. PRD v2.0 should specify a minimum rubric token budget + a runtime assertion (`raise if usage.cache_creation_input_tokens == 0 on the first call`).
2. **Forced tool use is incompatible with extended thinking on Sonnet 4.6 / Haiku 4.5.** We do not need extended thinking for this task, but PRD v2.0 should explicitly prohibit enabling `thinking` on requests — otherwise the model returns a 400 and the whole run fails. Quiet trap.
3. **Tool-choice changes invalidate the system cache.** Keep `tool_choice={"type": "tool", "name": "ReportFindings"}` fixed across every call in a run. PRD v2.0 should call this out as a non-negotiable constraint on any future refactor that "might want to sometimes let the model skip the tool."

Two secondary PRD-level facts worth capturing:

4. **Default to Sonnet 4.6, not Opus 4.7.** Caller wording ("Sonnet 4.6 default, Haiku 4.5 cheap, Opus 4.7 deep") matches the research-derived cost/value curve — confirm this in the PRD.
5. **Tier 2 is the minimum comfortable API tier.** Tier 1's 30K ITPM serializes the burst into a multi-minute wait. PRD v2.0 should note this as an operational requirement.

### New open risks (append to existing section, numbered 8+)

8. **Prompt-caching hit-rate collapses if the rubric or tool schema is edited during development.** Mid-session rubric tweaks invalidate the cache for 5 minutes, which is usually fine, but a bulk find-replace across the rubric during a `make dashboard` run will force every call to re-write. **Mitigation:** log cache hit-rate at end of run (`cache_read / (cache_read + cache_create + uncached)`); warn when < 80% on a run with > 10 calls. Also add a PRD note: "treat the rubric as a static artifact during a run; edit only between runs."
9. **Anthropic model deprecations can invalidate our defaults.** Sonnet 4 / Opus 4 (no suffix) are deprecated and retire 2026-06-15. We default to Sonnet 4.6 / Opus 4.7 which are current — but model deprecation is an ongoing concern. **Mitigation:** pin the exact model alias in a module constant; when a deprecation notice lands, update one line.
10. **`ANTHROPIC_API_KEY` missing in CI breaks dashboard generation.** Unless the `--no-llm` flag is wired and documented, users in environments without the key hit an `AuthenticationError` at first SDK call. **Mitigation:** fail fast at CLI start (check env var before any work) with a helpful message pointing to `--no-llm`.
11. **SDK `max_retries=2` may be silently insufficient on Tier 1.** If the user is on Tier 1 and their rubric + burst push them over ITPM, the SDK's 2 retries are not enough to ride out the 60-second rate-limit window. **Mitigation:** catch `RateLimitError`, log the failed scenarios, continue; emit a banner in the dashboard telling them to upgrade tier or rerun.
12. **No official Python binding of the Cucumber Messages schema still applies** — same as risk #7 in the original brief. Not LLM-specific but remains true after the LLM pivot.
13. **Workspace-level cache isolation (2026-02-05 change)** — caches are per-workspace now. Not relevant for local single-user use, but if the tool ever runs in a shared CI workspace with multiple feature branches generating dashboards, their caches are isolated. No action required today; flagged for future context.
