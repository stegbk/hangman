# PRD Discussion: bdd-dashboard

**Status:** In Progress
**Started:** 2026-04-23
**Participants:** KC, Claude

## Original user intent (from prior conversations)

- User built an example dashboard at `/Users/keithstegbauer/Downloads/bdd_dashboard_example.html` (1733 lines, Chart.js 4.4, dark-gradient theme, 7 summary cards, 2 charts, per-feature cards with issues/modal).
- Wants to "reproduce it" against this project's BDD suite.
- "Generate dashboard on every push / part of our PR creation ceremony."
- "Coverage on every endpoint and UC" — report whether every endpoint + use case is covered.
- "Artifact viewed locally or may be pushed to a teams channel later."
- Feature 3 (`bdd-branch-coverage`) covers call-graph + per-branch coverage + gap detection. So Feature 2 scope is the **dashboard** itself (visualizer + static analyzer inputs), not branch-level coverage.

## Prior-art analysis — the example dashboard structure

- **Header:** title, subtitle, timestamp.
- **7 summary cards** (info / success / success / warning / error / error / warning):
  - Total features + scenarios
  - % "thorough" (89/109)
  - % with failure paths (65/109)
  - % missing error paths (32/109)
  - Critical-issue feature count (17/109)
  - Scenarios requiring immediate attention (14)
  - Improvement opportunities (172)
- **Charts:** trend (24-day history, lines for critical/total/passing) + issues distribution (pie/donut).
- **Per-feature cards** with an `issues` array containing: `icon`, `severity`, `problem`, `description`, `reason`, `location`, `scenario`, `code_example`, `solution`, `fix_example`. Click opens detail modal.
- **Categories the example calls out as issues** — accepting 500-Internal-Server-Error, missing auth/authz tests, hardcoded credentials in scenarios, missing 401/403 tests, duplicate scenario names.

This is a **quality-analysis dashboard**, not just a pass/fail visualizer. It has OPINIONS about Gherkin text.

## Discussion Log

### Round 1 — scope / fidelity / data / workflow / stack (2026-04-23)

**Q1: opinion engine?** → **YES**. Dashboard includes a rule-based analyzer that grades each feature file for anti-patterns. It's not just pass/fail visualization.

**Q2: fidelity?** → **(b) structurally identical**. Same sections + charts + card layout + modal. Polish/colors can drift.

**Q3: coverage computation?** → **(a) scrape Gherkin text** for endpoint strings + UC names.

**Q4: input data source?** → **(c) parse `.feature` files directly for coverage + NDJSON for pass/fail**. (Two complementary sources — feature files for what SHOULD be covered, NDJSON for what was actually run green.)

**Q5: history storage?** → **(c) gitignored `.bdd-history/` locally**. Per-developer; no shared history.

**Q6: generation trigger?** → **(b) explicit `make bdd-dashboard`**. User invokes manually. Not auto-run by `make bdd`.

**Q7: output location?** → **(c) `tests/bdd/reports/dashboard.html`**, gitignored. Local artifact.

**Q8: Teams push?** → **DEFER**. Not in Feature 2 scope.

**Q9: implementation stack?** → **(a) Python in backend/**. Leverage existing Python tool ecosystem; invoke via `uv run python -m ...`.

**Q10: charting library?** → **Claude's call** — recommending `Chart.js` via CDN to match the example structurally and keep the Python side scope-limited to data + HTML emission.

### Round 2 — opinion engine + coverage + arch (2026-04-23)

**Q11: ruleset scope?** → **(c) Both** — domain-specific Hangman rules AND universal Gherkin hygiene.

**Q12: severity scheme?** → **Map to P0/P1/P2/P3** from `.claude/rules/workflow.md` (instead of the example's Critical/Warning/Info trio).

**Q13: trivial-pass detection?** → **YES in scope**.

**Q14: endpoint inventory?** → **(c) scrape Gherkin only**. Authoritative endpoint list from `routes.py` is Feature 3's scope.

**Q15: UC inventory?** → **(b) scrape Feature-block titles** for UC pattern (e.g., `Feature: UC1 — Play a round ...`).

**Q16: coverage definition?** → **1 happy + 1 failure + 1 edge = full**. Fuller grading lives in Feature 3.

**Q17: Python location?** → **(b) `backend/tools/dashboard/`** — developer-only, not part of the installable `hangman` package.

**Q18: HTML template approach?** → **Claude's call** — recommending **Jinja2** (readable + data-as-dict).

**Q19: tests?** → **(c) Both unit + golden-file**.

### Round 3 — operational specifics (2026-04-23)

**Q20: feature card granularity?** → **Per BDD scenario**, not per `.feature` file. User clarified that "multiple BDD tests can live in a file" — interpreting that as one card per Scenario = 33 cards. (See Q20-FOLLOWUP below for confirmation.)

**Q21: sparse-history chart?** → **"Run more to see trends" placeholder** when < 5 runs.

**Q22: history retention?** → **(a) keep forever** — each run is a timestamped NDJSON file under `.bdd-history/`.

**Q23: trivial-pass heuristic?** → **(a) status-only** — scenario whose only assertions are `Then the response status is {int}` (no body path, no UI state, no persistence check).

**Q24: dashboard timestamp?** → **(a) from NDJSON `meta.startedAt`**.

**Q25: modal interactivity?** → **KEEP** click-to-detail modal per example.

**Q20-FOLLOWUP: card granularity?** → **(i) Per Scenario = 33 cards**. Each card: scenario name + primary tag + @smoke (if present) + pass/fail outcome + inline issues list from the opinion engine. Click-to-modal for full detail (steps, NDJSON trace, suggested fixes).

**Q23 (no explicit answer → default):** Trivial-pass heuristic = **(a) status-only**. Flagged when scenario's only `Then` is `the response status is {int}`.

---

## Refined Understanding

### Personas

- **Developer** (primary) — runs `make bdd-dashboard` after `make bdd`, opens `tests/bdd/reports/dashboard.html` locally to triage scenario quality + coverage gaps.

### Overview

A developer-only tooling deliverable: a Python analyzer + HTML report generator that produces a single self-contained `dashboard.html` from the Hangman BDD suite's output. Structurally modeled on the user's example dashboard (`/Users/keithstegbauer/Downloads/bdd_dashboard_example.html`) — dark theme, summary cards, Chart.js trend + issues charts, per-scenario cards with click-to-modal details. Applies both domain-specific and universal Gherkin hygiene rules at P0/P1/P2/P3 severities.

### In scope (MVP)

1. **Static analyzer** (Python): parses 11 `.feature` files + `cucumber.ndjson` from last run.
2. **Opinion engine** with 6 domain-specific + 7 hygiene rules (13 total), emitting P0/P1/P2/P3 findings per scenario.
3. **Coverage grading** — per endpoint (scraped from Gherkin) + per UC (scraped from Feature titles): full / partial / none, based on @happy + @failure + @edge tag mix.
4. **Trivial-pass detection** — scenarios asserting only `response status is {int}`.
5. **HTML generator** (Jinja2) emitting single-file `tests/bdd/reports/dashboard.html` with:
   - Header (title + NDJSON `meta.startedAt` timestamp).
   - 7 summary cards (totals, pass %, coverage %, P0/P1/P2 counts, etc. — final card contents pinned in PRD).
   - 2 Chart.js charts: trend (last N runs) + issues breakdown (pie by severity).
   - 33 per-scenario cards (one per Scenario) with pass/fail + inline issue summary.
   - Click-to-modal for full scenario detail (steps, NDJSON outcome, opinion findings, suggested fixes).
6. **History** — append each run's NDJSON (timestamped filename) to gitignored `.bdd-history/`, keep forever, read last N for the trend chart. Show "run more to see trends" placeholder when < 5 runs.
7. **Makefile target** `make bdd-dashboard` — runs the analyzer + emits the HTML.
8. **Tests** — unit tests on the rule engine (synthetic .feature inputs) + golden-file test against the real 11 feature files.

### Non-goals (deferred)

- Call-graph / branch-coverage / per-code-path gap detection → Feature 3 (`bdd-branch-coverage`).
- Endpoint enumeration from `routes.py` → Feature 3.
- Teams-channel push integration → later.
- CI/CD publishing → local-only for now.
- Auto-run on `make bdd` → explicit invocation only.
- Git-tracked HTML artifact → dashboard is a gitignored local build.
- Dashboard-as-SPA / React component → single static HTML + inlined data blob.
- Real-time / live-updating dashboard → static snapshot only.

### Key decisions (locked)

- Implementation: Python in `backend/tools/dashboard/` (separate from `hangman` package).
- Template: Jinja2.
- Chart: Chart.js via CDN (matches example).
- Data: `.feature` files (for coverage + rule input) + `cucumber.ndjson` (for pass/fail + timestamp).
- Output: single file `tests/bdd/reports/dashboard.html`, gitignored.
- History: `.bdd-history/<timestamp>.ndjson` append, gitignored, keep forever.
- Severities: P0/P1/P2/P3 (matches `workflow.md` rubric).
- Coverage grading: full = 1 @happy + 1 @failure + 1 @edge per endpoint/UC.

### Ruleset (13 rules for opinion engine)

**Domain-specific (D1–D6):**

- D1 (P2): Scenario asserts status but no body path.
- D2 (P2): `@failure` scenario doesn't assert `error.code`.
- D3 (P2): `@failure` scenario doesn't assert specific non-200 status.
- D4 (P3): UI scenario doesn't verify persisted side-effect.
- D5 (P2): `/guesses`-hitting scenario doesn't verify `guessed_letters`/`masked_word`/`lives_remaining`.
- D6 (P3): Endpoint referenced but no `@smoke` scenario for it.

**Hygiene (H1–H7):**

- H1 (P1): Duplicate Scenario title in Feature.
- H2 (P1): Zero primary tag.
- H3 (P1): Multiple primary tags.
- H4 (P3): Scenario > 15 steps.
- H5 (P3): `Scenario Outline` with 1 `Examples` row.
- H6 (P0): Feature file with zero scenarios.
- H7 (P2): File where all scenarios share one primary tag.

### Open Questions (none remaining)

---

### Round 4 — dynamic vs gating (2026-04-23)

**Clarification from user:** "We don't want it to gate anything, we want the HTML report to be generated dynamically based on the content of the features."

**Resolution:** The dashboard is a **pure reporter**, NOT a pre-commit/pre-push/PR gate. Explicitly out-of-scope:

- Blocking `git commit`, `git push`, or `gh pr create` on any rule finding.
- Wiring the analyzer into `make bdd` or `make verify` so their exit codes depend on rule findings.
- New hook gates (no change to `.claude/hooks/check-workflow-gates.sh`).
- Auto-invoking the analyzer on file-save or editor hooks.

**"Dynamic" interpretation (confirmed):** the report is a pure function of `.feature` files + `cucumber.ndjson`. Adding/removing/editing scenarios or features changes the next run's output automatically — there's no hardcoded scenario count, endpoint list, UC manifest, or feature manifest anywhere in the analyzer. Every run scrapes + evaluates fresh.

**Implication for MVP scope (reinforced):**

- `make bdd-dashboard` exit code is always 0 on successful HTML emission — regardless of how many P0/P1/P2/P3 findings the opinion engine produced.
- Findings are INFORMATIONAL ONLY. They appear in the HTML so the developer can review them; no automation consumes them.
- A developer who wants to enforce rules can grep the generated HTML / run a custom check, but the tool ships no such check.
