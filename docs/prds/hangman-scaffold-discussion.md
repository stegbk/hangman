# PRD Discussion: Hangman Scaffold

**Status:** Complete
**Started:** 2026-04-22
**Completed:** 2026-04-22
**Participants:** User (KC), Claude

## Original User Stories

From `CONTINUITY.md`:

> A local HTTP hangman game with category picker, score/streak tracking, difficulty levels, and per-session game history.

And the `Next` list:

- Scaffold FastAPI backend (`pyproject`, `main.py`, `game.py` stubs)
- Scaffold React + Vite frontend
- Define `words.txt` format + seed content

Implied by `CLAUDE.md` File Structure section:

- Backend modules: `main.py`, `game.py`, `routes.py`, `schemas.py`, `models.py`, `db.py`, `sessions.py`, `words.py`
- Frontend components: `GameBoard`, `Keyboard`, `CategoryPicker`, `ScorePanel`, `HistoryList`
- Persistence: SQLite + session cookie (history keyed by session cookie)
- Features: score + streaks + difficulty

## Phase 0 — Discovery Research (summary)

Sources consulted:

- [Hangmanwords.com — best hangman words](https://www.hangmanwords.com/words)
- [Coolmath Games Hangman](https://www.coolmathgames.com/0-hangman)
- [Thiagi — Hangman Step by Step](https://thiagi.net/archive/www/wgs-hangmanStepByStep.html)
- [Wordnik Hangman List](https://www.wordnik.com/lists/food--21)
- [Duke CompSci 101 Hangman Categories](https://courses.cs.duke.edu/fall14/compsci101/assign/assign7/categories.html)

Findings (relevant to scaffold decisions):

- **Difficulty tiers are standard** (easy / medium / hard). Common parameterization: word length, letter frequency (common vs. rare letters), max wrong guesses.
- **Scoring patterns:** points per correct letter, bonus for speed and lives remaining, streak multipliers (2× / 3× for consecutive wins).
- **Streak definition:** "consecutive words won without failing." Reset on a loss.
- **Word-list formats in the wild:** one file per category (`animals.txt`, `food.txt`) vs. one combined file with category delimiters. Thematic categories (Animals, Food, Cities, Tech, Movies, Sports, Space, etc.).
- **Game state:** classic is `IN_PROGRESS / WON / LOST` with 6 wrong-guesses to lose (hanged figure limbs = head, torso, 2 arms, 2 legs). Some modern variants use 7 (add face) or configurable.

## Discussion Log

### Round 1 — Targeted Questions (2026-04-22)

This scaffold is the skeleton the actual gameplay features will build on. The decisions below don't all have to be _final_, but the scaffold needs to commit to primitives concrete enough that `game.py`, `words.py`, `models.py`, and the API contract can be stubbed without re-doing work later.

**Scope / MVP cut**

1. **Does the scaffold ship a playable skeleton** (you can open the page, pick a category, guess letters, and win/lose a round) — or just empty stubs that compile, with gameplay deferred to follow-up features? My recommendation: playable-end-to-end skeleton with one category, easy difficulty, basic scoring. It validates the full stack and gives us something to run E2E against. Agree, or do you want stubs-only?
2. **Which of the four feature axes are live in the scaffold vs deferred?**
   - category picker
   - score (points for a round)
   - streak (consecutive wins)
   - difficulty levels (easy / medium / hard)
     Live in scaffold means the field/endpoint/type exists and is wired. Deferred means stubbed or omitted for now.

**Game rules**

3. **How many wrong guesses before you lose?** Classic is 6 (head/torso/2 arms/2 legs). Modern web variants often use 6 or 7. Fixed, or does it vary by difficulty (e.g., easy=8, medium=6, hard=4)?
4. **Scoring formula for v0** — I'll propose: `+10 per correct letter` + `remaining_lives × 5` on win, `0` on loss. Streak multiplier kicks in at 2 consecutive wins (2×) and 3+ (3×). Good default, or do you want something simpler (e.g., "1 point per win, streak = consecutive wins") or more elaborate (time bonus, hint penalty)?
5. **Difficulty semantics** — what changes across levels? My proposal:
   - **Easy:** 4–6 letter words, 8 wrong guesses allowed
   - **Medium:** 7–9 letter words, 6 wrong guesses
   - **Hard:** 10+ letter words or words with rare letters (j, q, x, z), 4 wrong guesses
     Agree, or different thresholds?

**Words & categories**

6. **`words.txt` format — one file with categories, or one file per category?** Two reasonable options:
   - **A (single file, sectioned):** lines like `# animals` headers and word-per-line below. Easy for humans to edit by hand.
   - **B (single file, CSV):** `category,word` per line. Trivial parsing, grep-able.
   - **C (per-category file):** `words/animals.txt`, `words/food.txt`, etc. Scales well, more files.
     My lean: **B (CSV)** for simplicity + grep-ability, unless you want per-category files.
7. **Seed categories for MVP?** Suggest 5: Animals, Food, Cities, Tech, Movies — ~15 words per category to start.
8. **Uppercase or lowercase storage?** Store canonical in the file (say lowercase), compare case-insensitively at guess time.

**Persistence & session**

9. **Session cookie lifetime?** Options: browser-session (cleared when window closes) vs persistent (30 days). Persistent is more fun ("come back tomorrow, streak intact"). Also — signed cookie (itsdangerous) vs opaque UUID?
10. **What does the `Game` table store?** Proposal: `id, session_id, category, difficulty, word (hidden until reveal), state (IN_PROGRESS/WON/LOST), wrong_guesses, guessed_letters (JSON/CSV), score, started_at, finished_at`. Session table: `id (cookie value), created_at, current_streak, best_streak, total_score`. Correct, or something different?
11. **Can a user have multiple games in flight, or exactly one active game per session?** One-at-a-time is simpler and matches classic hangman UX. Multi-tab concurrent play needs locking — I'd defer that. Agree?

**API shape**

12. **For the scaffold, which endpoints do we stub?** Proposal (all under `/api/v1/`):
    - `GET /categories` — list available categories (+ difficulty options)
    - `POST /games` — start a new game (`{category, difficulty}` → creates game, returns masked word + game id + lives)
    - `GET /games/current` — fetch current in-flight game
    - `POST /games/{id}/guesses` — submit a letter (`{letter}` → updated game state)
    - `GET /history` — list past games for this session
      Over-scoped, under-scoped, or just right?

**Frontend**

13. **Styling approach for the scaffold?** Options: plain CSS, CSS modules, Tailwind, or something else. The `CLAUDE.md` Visual Design Preferences section mentions "dynamic/animated elements… organic shapes" — I read that as a note for the later visual polish, not the scaffold skeleton. Confirm?
14. **Hangman figure rendering** — SVG (recommended, scales + animatable), Canvas, or ASCII? SVG fits the "organic shapes / animated" preference.

**Tooling**

15. **Linting / formatting** — `ruff` (already implied by rules) + `black`? Or `ruff` only (it formats now)? Frontend: ESLint + Prettier, or Biome? I'd pick **ruff** (lint+format) and **Biome** for speed, unless you prefer Prettier.
16. **Pre-commit hooks** — install now or defer? If now, which checks (ruff, pytest -x, type-check)?
17. **Playwright framework install now, or only markdown use cases + verify-e2e agent for now?** Given this is a local-only game (per `CLAUDE.md`), and `interface_type: fullstack`, I'd install Playwright now so the scaffold commits to the full testing shape. Agree?

**Deployment / infra**

18. **One command to run everything?** A `Makefile` or `justfile` with `make dev` that starts both uvicorn + vite concurrently (e.g., via `honcho` / `foreman` / `concurrently`), or document the two-terminal approach?

### Round 1 — Answers (2026-04-22)

| Q   | Decision                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Source                                                              |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| 1   | **Playable end-to-end skeleton.** Full flow: pick category + difficulty → play a round → score/streak updates → history recorded.                                                                                                                                                                                                                                                                                                                                                                                       | User explicit                                                       |
| 2   | **All four axes live** in the scaffold: category picker, score, streak, difficulty.                                                                                                                                                                                                                                                                                                                                                                                                                                     | User explicit                                                       |
| 3   | **Wrong-guesses per difficulty: Easy = 8, Medium = 6, Hard = 4.**                                                                                                                                                                                                                                                                                                                                                                                                                                                       | User explicit                                                       |
| 4   | Scoring: `+10 per correct letter reveal` + `remaining_lives × 5` on win. Streak multiplier applied to round score: 1× if streak < 2, 2× if streak ∈ {2}, 3× if streak ≥ 3. Loss → round score 0 and streak resets to 0.                                                                                                                                                                                                                                                                                                 | Claude default                                                      |
| 5   | **Difficulty = wrong-guesses only.** Words are NOT filtered by length per difficulty — any word from the chosen category can appear at any difficulty. (Simpler than the original tiered-length proposal; matches user Q3 answer.)                                                                                                                                                                                                                                                                                      | Claude default (narrowed per user answer)                           |
| 6   | `words.txt` format = **CSV**, columns: `category,word`. One word per line. Case-insensitive compare; stored lowercase. Blank lines + lines starting with `#` are comments.                                                                                                                                                                                                                                                                                                                                              | Claude default                                                      |
| 7   | **3 seed categories:** Animals, Food, Tech. Target ~15 words per category.                                                                                                                                                                                                                                                                                                                                                                                                                                              | User explicit (3 categories); Claude default (which 3)              |
| 8   | Lowercase storage, case-insensitive compare.                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | Claude default                                                      |
| 9   | **Cookie:** 30-day persistent, opaque UUID (no signing — local-only single-user app; opaque UUID is unguessable enough for per-browser identification). `HttpOnly` + `SameSite=Lax`. `Secure=False` since local-only HTTP.                                                                                                                                                                                                                                                                                              | Claude default                                                      |
| 10  | `Session` table: `id (UUID cookie value, PK), created_at, updated_at, current_streak, best_streak, total_score`. `Game` table: `id (int PK), session_id (FK), category, difficulty (enum: easy/medium/hard), word (text, lowercase), state (enum: IN_PROGRESS/WON/LOST), wrong_guesses (int), guessed_letters (text, sorted chars), score (int), started_at, finished_at (nullable)`.                                                                                                                                   | Claude default                                                      |
| 11  | **One active game per session.** Starting a new game while one is `IN_PROGRESS` forfeits the active one (state → LOST, streak resets). UI confirms before forfeiting.                                                                                                                                                                                                                                                                                                                                                   | User explicit (one-per-session); Claude default (forfeit semantics) |
| 12  | Endpoints under `/api/v1/`:<br>• `GET  /categories` — returns `{categories: [name…], difficulties: [{id, label, wrong_guesses_allowed}…]}`<br>• `POST /games` body `{category, difficulty}` — creates game (forfeits prior IN_PROGRESS if any), returns game DTO<br>• `GET  /games/current` — returns current IN_PROGRESS game, or 404 if none<br>• `POST /games/{id}/guesses` body `{letter}` — 200 with updated game DTO<br>• `GET  /history` — returns past finished games for this session, newest first, paginated | Claude default                                                      |
| 13  | **Plain CSS, simple scaffolding.** Vite default linting (ESLint). Defer Biome / Tailwind / elaborate animation work to a future "visual polish" feature.                                                                                                                                                                                                                                                                                                                                                                | User explicit                                                       |
| 14  | **ASCII hangman figure** for v0. (SVG upgrade in a future polish feature.)                                                                                                                                                                                                                                                                                                                                                                                                                                              | User explicit                                                       |
| 15  | Backend: **ruff** for lint + format (no black, no separate formatter). Frontend: **ESLint + Prettier** per Vite React-TS template default.                                                                                                                                                                                                                                                                                                                                                                              | Claude default                                                      |
| 16  | **Defer pre-commit hooks** to a future task.                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | User explicit                                                       |
| 17  | **Install Playwright framework now.** `interface_type: fullstack` per `CLAUDE.md`, and this commits the scaffold to the full testing shape.                                                                                                                                                                                                                                                                                                                                                                             | User explicit                                                       |
| 18  | **Makefile with separate targets:** `make backend`, `make frontend`, `make install`, `make test`. Document "run backend and frontend in two terminals" in the README — no concurrency helper (keeps deps minimal).                                                                                                                                                                                                                                                                                                      | Claude default                                                      |

## Refined Understanding

### Personas

- **Single-player local user** — opens `http://localhost:3000` in a browser, plays hangman rounds, sees score/streak/history accumulate across sessions via a 30-day cookie. No accounts, no auth. Local-only.
- **Developer (future Claude sessions / KC)** — extends the scaffold with new features (visual polish, more categories, multiplayer, etc.). The scaffold's job is to establish clear primitives (game state machine, API contract, DB schema, component shape) that future features can build on without rework.

### User Stories (Refined)

- **US-001 — Pick and play a round.** As a local user, I can open the app, pick one of 3 categories (Animals / Food / Tech) and a difficulty (Easy=8 lives / Medium=6 / Hard=4), then guess letters against a masked word until I win or lose.
- **US-002 — See score and streak.** When I win a round, my score increases (per formula in Q4) and my consecutive-win streak advances. When I lose, the round awards 0 and my streak resets.
- **US-003 — Review history.** I can see past finished games (category, difficulty, word, state, score, timestamp) for my browser session, newest first.
- **US-004 — Session persists.** My score, streak, and history survive a browser reload and up to 30 days of absence, via a session cookie. Clearing cookies = fresh start.
- **US-005 — One game at a time.** I cannot have two IN_PROGRESS games. Starting a new game while one is active prompts a confirm; confirming forfeits the active game (counts as loss, resets streak).

### Non-Goals (scaffold scope)

- Multi-user auth / accounts
- Leaderboards across devices
- Multiplayer / real-time
- Hint system, power-ups, time bonuses
- Elaborate animations, SVG hangman, organic/dynamic visual design (deferred to polish feature)
- Pre-commit hooks
- Biome / Tailwind
- CI/CD pipelines
- Word lists > ~50 total seed words (future feature can expand)
- Internationalization (English only for v0)

### Key Decisions

1. **Full playable skeleton**, not empty stubs. Validates full stack and gives E2E something to exercise.
2. **Difficulty affects wrong-guesses-allowed only** (8/6/4). Word pool is category-only, not difficulty-filtered. Simpler data model.
3. **One-file CSV word store** (`category,word`). Parser in `words.py` is ~10 lines.
4. **One active game per session.** Starting a new one forfeits the active one with a UI confirm.
5. **Opaque UUID session cookie**, 30-day persistent, `HttpOnly` + `SameSite=Lax`. Not signed — local-only app.
6. **ASCII hangman figure**, plain CSS, ESLint-only frontend. Visual polish is a follow-up feature, not this one.
7. **Playwright framework installed in scaffold** so first E2E use case can ship with this PR.
8. **Ruff (lint+format) for backend, ESLint+Prettier for frontend**, Makefile for common commands, two-terminal dev flow.

### Open Questions (Remaining)

- [ ] None blocking. The scoring formula (Q4), exact word lists (Q7), and Makefile targets (Q18) are defaults I'll implement; flag any of them during the plan-review loop to change before code is written.

---

Ready for `/prd:create hangman-scaffold`.
