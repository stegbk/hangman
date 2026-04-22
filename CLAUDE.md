@CONTINUITY.md

# CLAUDE.md - Hangman

## Project Overview

### What Is This?

Hangman is a local HTTP hangman game. Players pick a word category, guess letters against a hidden word, and track score/streaks across difficulty levels. Game history persists per browser via a session cookie.

### Tech Stack

- **Backend:** Python 3.12+, FastAPI, Pydantic, SQLAlchemy
- **Frontend:** React + TypeScript, Vite
- **Database:** SQLite (local file; stores game history keyed by session cookie)
- **Deploy:** Local only — `uvicorn` for the API, `vite` dev server for the UI

### File Structure

```
hangman/
├── backend/
│   ├── src/hangman/
│   │   ├── main.py            # FastAPI app + startup
│   │   ├── game.py            # Pure game logic (state machine, guess, scoring)
│   │   ├── routes.py          # /api/v1/... endpoints
│   │   ├── schemas.py         # Pydantic request/response models
│   │   ├── models.py          # SQLAlchemy ORM (Session, Game)
│   │   ├── db.py              # Engine + session factory
│   │   ├── sessions.py        # Cookie session handling
│   │   └── words.py           # words.txt loader + category picker
│   ├── tests/
│   │   ├── unit/              # Pure logic (game.py, scoring)
│   │   ├── integration/       # Real SQLite, real HTTP client
│   │   └── conftest.py
│   ├── words.txt              # Category word list (format TBD)
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/        # GameBoard, Keyboard, CategoryPicker, ScorePanel, HistoryList
│   │   ├── api/               # Fetch wrappers for the backend
│   │   └── types.ts
│   ├── tests/e2e/             # Playwright (if enabled)
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   ├── prds/         # Product requirements
│   ├── plans/        # Design documents
│   ├── solutions/    # Compounded learnings (searchable)
│   └── CHANGELOG.md  # Historical record
└── .claude/          # Claude Code configuration
    ├── commands/     # Workflow commands (ENFORCED)
    └── rules/        # Coding standards (auto-loaded)
```

### Design Direction (optional — delete if not needed)

<!-- Remove this comment block and fill in your project's aesthetic:
- Premium, dark-mode-first aesthetic (think Linear.app, Vercel.com)
- Font pairing: Instrument Serif for headlines, Geist for body
- Color palette: deep navy (#0A0E27), electric blue (#3B82F6), warm white (#F8FAFC)
- No generic "AI slop" — avoid Inter, purple gradients, evenly-spaced 3-card grids
-->

### Visual Design Preferences

- Never generate plain static rectangles for hero sections, landing pages, or key visual moments
- Always include at least one dynamic/animated element: SVG waves, Lottie, shader gradients, or canvas particles
- Prefer organic shapes (blobs, curves, clip-paths) over straight edges and 90-degree corners
- Animations must respect `prefers-reduced-motion` — provide static fallbacks

### Deployment (optional — delete if not needed)

<!-- Remove this comment block and fill in your deployment setup:
- Hosted on Vercel, auto-deploys from `main` branch
- Use `vercel --yes` for preview deployments
- Environment variables managed via Vercel dashboard
-->

### E2E Configuration

The `verify-e2e` agent adapts to this project's interfaces. Declare the interface type:

**interface_type:** fullstack

- `fullstack`: Both API and UI (UI tested via Playwright MCP)
- `api`: API only (HTTP interface, no UI)
- `cli`: Command-line only (stdin/stdout)
- `hybrid`: Use cases declare their own interface

**Server URLs** (for fullstack/api):

- API: `http://localhost:8000` (update as needed)
- UI: `http://localhost:3000` (update as needed)

See `.claude/rules/testing.md` for the full interface capability matrix.

### Playwright Framework (optional)

If you enabled Playwright via `setup.sh --with-playwright`, this project has:

- `playwright.config.ts` — at repo root for flat layouts, or inside a frontend subdirectory (`frontend/`, `apps/web/`, etc.) that was detected or passed via `--playwright-dir` at setup time
- `tests/e2e/specs/` — generated spec files (via Phase 6.2c), adjacent to `playwright.config.ts`
- `tests/e2e/fixtures/auth.ts` — auth bypass pattern, adjacent to `playwright.config.ts`
- `docs/ci-templates/e2e.yml` — CI workflow template (copy to `.github/workflows/` to activate); `working-directory` is already stamped to match where Playwright was scaffolded

Run specs locally from wherever `playwright.config.ts` lives:

```bash
pnpm exec playwright test             # flat layout
cd frontend && pnpm exec playwright test   # monorepo layout
```

### Research Enforcement

The `research-first` agent runs in Phase 2 of `/new-feature` (before design begins). It queries Context7, WebSearch, and WebFetch for every external library this feature touches and produces a brief at `docs/research/YYYY-MM-DD-<feature>.md`. The design phase reads this brief to avoid building on stale assumptions.

For bug fixes, targeted research runs after root-cause isolation (Phase 2.5 of `/fix-bug`).

### Key Commands

```bash
# Workflows (MANDATORY - hooks enforce these)
/new-feature <name>     # Full feature workflow
/fix-bug <name>         # Bug fix with systematic debugging
/quick-fix <name>       # Trivial changes only (< 3 files)
/council <question>     # Multi-perspective decision analysis (5 advisors + chairman)
/codex <instruction>    # Second opinion from OpenAI Codex CLI

# Backend (port 8000)
cd backend && uv run uvicorn hangman.main:app --reload    # Dev server
cd backend && uv run pytest                               # Tests
cd backend && uv run ruff check .                         # Lint

# Frontend (port 3000)
cd frontend && pnpm dev                                   # Dev server
cd frontend && pnpm test                                  # Vitest
cd frontend && pnpm exec playwright test                  # E2E (if enabled)

/finish-branch                                            # Merge PR + cleanup worktree
```

---

## No Bugs Left Behind Policy

**NEVER defer known issues "for later."** When a review, test, or tool flags an issue — fix it in the same branch before moving on. This applies to:

- Code bugs found during review
- Deployment/infrastructure issues found during testing
- Configuration mismatches across environments (Docker, K8s, Helm)
- Security findings from any reviewer (Claude, Codex, PR toolkit)
- Test coverage gaps for new code

No "follow-up PRs" for known problems. No "v2" for things that should work in v1. If it's found, it's fixed — or the branch isn't ready.

## Detailed Rules

All coding standards, workflow rules, and policies are in `.claude/rules/`.
These files are auto-loaded by Claude Code with the same priority as this file.

**What's in `.claude/rules/`:**

- `principles.md` — Top-level principles and design philosophy
- `workflow.md` — Decision matrix for choosing the right command
- `worktree-policy.md` — Git worktree isolation rules
- `critical-rules.md` — Non-negotiable rules (branch safety, TDD, etc.)
- `memory.md` — How to use persistent memory and save learnings
- `security.md`, `testing.md`, `api-design.md` — Coding standards
- Language-specific: `python-style.md`, `typescript-style.md`, `database.md`, `frontend-design.md`
