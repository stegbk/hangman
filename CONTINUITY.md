# CONTINUITY

## Goal

A local HTTP hangman game with category picker, score/streak tracking, difficulty levels, and per-session game history.

## Key Decisions

| Decision          | Choice                              | Why                                                   |
| ----------------- | ----------------------------------- | ----------------------------------------------------- |
| Backend framework | Python 3.12 + FastAPI               | Matches project rules (uv / pytest / ruff / Pydantic) |
| Frontend          | React + TypeScript + Vite           | Rich interactive UI, standard tooling                 |
| Persistence       | SQLite + session cookie             | Per-browser history, zero-setup local storage         |
| Word source       | Bundled `words.txt` with categories | Offline, deterministic, no external API dependency    |
| Features          | Score + streaks + difficulty        | Replayability beyond one-and-done games               |

---

## State

### Done (recent 2-3 only)

- Backend complete — 108 tests passing (unit + integration); 6 endpoints under `/api/v1/` (2026-04-22)
- Frontend complete — 23 tests passing; 6 components + App.tsx + api client; `pnpm build` clean (2026-04-22)
- Playwright framework installed; chromium downloaded; config + auth fixture stub ready (2026-04-22)

### Now

Phase 4 nearly complete — Tasks 1–23 committed (backend + frontend + Playwright); Task 24 checkpoint smoke-verified via curl. Port 8000 has an SSH tunnel conflict blocking real E2E dispatch on canonical ports; awaiting user direction (kill tunnel / make ports configurable / skip E2E as N/A).

### Next

- Task 24a: verify-e2e agent dispatch + report persistence (blocked on port 8000)
- Task 24b: Playwright smoke spec (blocked on port 8000)
- Task 25: README with setup/run instructions
- Phase 5: code-review loop + simplify + verify + E2E

---

## Workflow

> Updated automatically by `/new-feature` and `/fix-bug` commands.
> The Stop hook reminds you of the current phase on every response.
> The PreToolUse hook blocks commit/push/PR if quality gates are incomplete.
> Delete this section when no workflow is active (or set Command to `none`).

| Field     | Value                                                                               |
| --------- | ----------------------------------------------------------------------------------- |
| Command   | /new-feature hangman-scaffold                                                       |
| Phase     | 4 — Execute                                                                         |
| Next step | Resolve port 8000 conflict → dispatch Task 24a verify-e2e → Tasks 24b, 25 → Phase 5 |

### Checklist

- [x] Worktree created
- [x] Project state read
- [x] Plugins verified
- [x] PRD created
- [x] Research artifact produced (`docs/research/2026-04-22-hangman-scaffold.md` — 20 libs, gate passed; PRD v1.1 patched with sync-stack + Node 22/pnpm 10 + hand-rolled cookie decisions)
- [x] Design guidance loaded (if UI) — N/A: scaffold UI is intentionally minimal (ASCII figure, plain CSS, one page) per PRD non-goals. Visual polish deferred to a follow-up feature at which point `frontend-design:frontend-design` will be loaded.
- [x] Brainstorming complete (`docs/plans/2026-04-22-hangman-scaffold-design.md` v1, approved by KC 2026-04-22)
- [x] Approach comparison filled (see `## Approach Comparison` below)
- [x] Contrarian gate passed — VALIDATE (Codex, gpt-5.4, 2026-04-22: "The PRD and explicit Q1/Q2/Q17 directives require a playable end-to-end scaffold… The thin-skeleton alternative is cheaper only by failing the requested scope, so it is not a credible competing approach.")
- [x] Council verdict (if triggered) — N/A: VALIDATE skipped the council per protocol
- [x] Plan written (`docs/plans/2026-04-22-hangman-scaffold-plan.md` — 27 tasks incl. Tasks 24a + 24b, ~4850 lines, Dispatch Plan + E2E Use Cases included)
- [x] Plan review loop (3 iterations) — PASS. Iter 1 found 6 P1 + 4 P2 (CHANGES_REQUIRED, all fixed). Iter 2 found 1 residual P1 (Playwright spec `test` category fragile, fixed to wiring-only smoke). Iter 3: Codex verdict CLEAN ("All 11 named fixes landed: Task 10 is coherently reference-only before tests/RED/implementation, and Task 24b is self-sufficient against the real backend path without `test` category or score assumptions"). Two P3 nits (15-letter sequence doesn't cover `algorithm`/`encryption` — acceptable because default category is `animals`; tightened Task 10 Step 5 assertion from `"word" not in body or body["word"] is None` to strict `"word" not in body`).
- [ ] TDD execution complete
- [ ] Code review loop (0 iterations) — iterate until no P0/P1/P2
- [ ] Simplified
- [ ] Verified (tests/lint/types)
- [ ] E2E use cases designed (Phase 3.2b)
- [ ] E2E verified via verify-e2e agent (Phase 5.4)
- [ ] E2E regression passed (Phase 5.4b)
- [ ] E2E use cases graduated to tests/e2e/use-cases/ (Phase 6.2b)
- [ ] E2E specs graduated to tests/e2e/specs/ (Phase 6.2c — if Playwright framework installed)
- [ ] Learnings documented (if any)
- [ ] State files updated
- [ ] Committed and pushed
- [ ] PR created
- [ ] PR reviews addressed
- [ ] Branch finished

---

## Approach Comparison

### Chosen Default

**Full end-to-end playable scaffold in one PR.** FastAPI + React/Vite monorepo with sync Python stack, hand-rolled session cookie, prop-drilling frontend, Playwright framework installed, full quality-gate coverage (unit + integration + E2E + lint + types + format). Matches PRD v1.2 §2 goals and the user's explicit Q1 answer ("playable end-to-end") and Q17 ("install Playwright now").

### Best Credible Alternative

**Thin-skeleton scaffold: file stubs only, gameplay and tests deferred.** Lay out the directories and module files with empty / raise-`NotImplementedError` stubs, merge, then iterate in follow-up PRs. The user's Q1 answer rejected this, but it IS a credible alternative worth pressure-testing because it's the pattern some teams use to lower per-PR risk.

### Scoring

| Axis                    | Default (full playable)                              | Alternative (thin stubs)                                                                                                                         |
| ----------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Complexity              | M — ~30 files touched, full stack wired              | L — ~15 files, stubs only                                                                                                                        |
| Blast Radius            | M — every scaffold module present                    | L — only file structure                                                                                                                          |
| Reversibility           | M — schema migration + route shape settled           | L — can rewrite stubs freely, no committed behavior                                                                                              |
| Time to Validate        | M — E2E + unit + integration must pass               | L — "does it import?" is the bar                                                                                                                 |
| User / Correctness Risk | L — end-to-end validated, can't ship silently broken | M — primitives are untested, later features build on unverified assumptions; defers known work into "follow-up PR" (NO BUGS LEFT BEHIND tension) |

Sub-question already resolved by research (documented for completeness, not re-scored): **sync Python stack vs async Python stack** — research brief (`docs/research/2026-04-22-hangman-scaffold.md` §Cross-cutting findings → SQLite thread safety) identified async + sync-DB as a documented perf trap and async + async as zero-benefit dep bloat at 1 user. Sync wins unambiguously.

### Cheapest Falsifying Test

**N/A — comparison is about scope / ceremony level, not correctness.** The thin-skeleton alternative would "fail" only in the sense that follow-up PRs would be required. No runtime experiment disambiguates this; it's a judgment call already made by the user in PRD discussion Q1 ("playable end-to-end, 3 categories") and reinforced by the NO BUGS LEFT BEHIND rule (don't ship broken, defer-able work).

Estimate: > 30 min to prototype both; value: zero (user's directive is already clear). **Skip spike; proceed to contrarian gate.**

### Contrarian Gate Expectation

Default should VALIDATE. The user has already given explicit direction (Q1), research has already made the sync-vs-async call, and the default aligns with both. Gate is a formality — but still run it (Codex confirms no overlooked alternative).

---

## Open Questions

- [Question needing resolution]

## Blockers

- [None currently]

---

## Update Rules

> **IMPORTANT:** You (Claude) are responsible for updating this file. The Stop hook will remind you, but YOU must make the edits.

**On task completion:**

1. Add to Done (keep only 2-3 recent items)
2. Move top of Next → Now
3. Add to CHANGELOG.md if significant

**On new feature:**
Clear Done section, start fresh

**Where detailed progress lives:**

- Feature subtasks → `docs/plans/[feature].md`
- Historical record → `docs/CHANGELOG.md`
- Learnings → `docs/solutions/`

---

## Session Start

Claude should say:

> "Loaded project state. Current focus: [Now]. Ready to continue or start something new?"
