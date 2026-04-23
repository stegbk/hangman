# PRD: Hangman Scaffold

**Version:** 1.2
**Status:** Draft
**Author:** Claude + KC
**Created:** 2026-04-22
**Last Updated:** 2026-04-22

---

## 1. Overview

Scaffold a playable end-to-end local hangman game: FastAPI backend + React/Vite frontend + SQLite persistence. A single local user picks one of three categories (Animals / Food / Tech) and a difficulty (Easy = 8 lives / Medium = 6 / Hard = 4), guesses letters against a masked word, and accumulates score + consecutive-win streak + finished-game history across sessions via a 30-day session cookie. This PR establishes working primitives (game state machine, API contract, DB schema, component shape, Playwright harness) so follow-up features (visual polish, more categories, SVG animations) can land cleanly.

## 2. Goals & Success Metrics

### Goals

- **Primary:** Deliver a fully playable hangman skeleton — open the app, play a round, win or lose, see score/streak/history update and persist.
- **Secondary:** Commit the repo to a testing shape (verify-e2e markdown use cases + Playwright framework installed) so every future user-facing feature has a regression gate from day one.
- **Tertiary:** Establish code primitives — `game.py` state machine, CSV word parser, SQLAlchemy models, Pydantic schemas, API routes, typed React components — that follow-up features can extend without rework.

### Success Metrics

| Metric                    | Target                                                          | How Measured                                                                                          |
| ------------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| E2E happy path            | 1 Playwright spec + 1 markdown use case pass                    | `pnpm exec playwright test` green; verify-e2e agent report classifies PASS                            |
| Unit test coverage        | `game.py` logic: 100% branches exercised                        | `pytest --cov=hangman.game` ≥ 95%                                                                     |
| Integration test coverage | Every endpoint in §4 exercised by at least one integration test | `pytest backend/tests/integration` green                                                              |
| Typecheck                 | No errors                                                       | Backend: `mypy hangman/` clean; Frontend: `tsc --noEmit` clean                                        |
| Lint/format               | Clean                                                           | `ruff check . && ruff format --check .`; ESLint + Prettier clean                                      |
| Cold-start dev loop       | `make install && make backend` / `make frontend` both boot      | `curl http://localhost:8000/api/v1/categories` returns 200 + JSON; `http://localhost:3000` serves app |
| Session persistence       | Cookie survives reload + 30-day TTL set correctly               | Playwright reload test; `Set-Cookie` header inspection                                                |

### Non-Goals (Explicitly Out of Scope)

- ❌ Multi-user auth / accounts / login
- ❌ Leaderboards across devices or users
- ❌ Multiplayer / real-time play
- ❌ Hints, power-ups, time bonuses, or anything beyond the scoring formula in §4/US-002
- ❌ SVG/Canvas hangman art, animations, or "organic shapes" visual polish (deferred to future polish feature)
- ❌ Tailwind, Biome, styled-components, or any styling framework beyond plain CSS
- ❌ Pre-commit hooks
- ❌ CI/CD pipelines (the Playwright CI template ships unactivated per `rules/testing.md`)
- ❌ Internationalization (English only)
- ❌ Word lists beyond the ~45-word seed (15 × 3 categories); dictionary expansion is a future feature
- ❌ More than 3 categories in the scaffold seed
- ❌ Concurrency helpers (`honcho`, `concurrently`) — two-terminal dev flow documented instead

## 3. User Personas

### Local Player

- **Role:** Single-player playing hangman in a local browser.
- **Permissions:** Full access to all endpoints; no auth. Identified per browser via an opaque 30-day UUID session cookie.
- **Goals:** Pick a category, play a round, enjoy escalating score + streak, review past games.

### Developer (future sessions)

- **Role:** Claude or KC extending the scaffold with new features (polish, more categories, multiplayer, etc.).
- **Permissions:** Repo write access via normal `/new-feature` / `/fix-bug` workflow.
- **Goals:** Extend game state, schemas, routes, and components without refactoring the skeleton.

## 4. User Stories

### US-001: Pick and play a round

**As a** local player
**I want** to pick a category and difficulty and play a round of hangman
**So that** I can guess letters against a masked word until I win or lose

**Scenario:**

```gherkin
Given I have opened the app and no game is in progress
When I pick category "Animals" and difficulty "Medium"
Then the server creates a game with 6 wrong-guesses allowed and a random lowercase word from the Animals pool
And the UI shows the masked word (one underscore per letter), an on-screen keyboard with letters a–z, the remaining-lives count, and the ASCII hangman figure in its initial state
When I guess a letter that appears in the word
Then every occurrence of that letter is revealed in the masked word
And remaining-lives is unchanged
And the letter is marked as guessed on the keyboard (disabled)
When I guess a letter that does NOT appear in the word
Then remaining-lives decrements by 1
And the ASCII hangman figure advances one stage
And the letter is marked as guessed (disabled)
When I reveal the last hidden letter
Then the game state becomes WON
And the full word is displayed
When remaining-lives reaches 0
Then the game state becomes LOST
And the full word is revealed
```

**Acceptance Criteria:**

- [ ] `POST /api/v1/games` with `{category: "Animals", difficulty: "medium"}` returns 201 with `Location` header and JSON body `{id, category, difficulty, masked_word, wrong_guesses_allowed: 6, wrong_guesses: 0, guessed_letters: [], state: "IN_PROGRESS", lives_remaining: 6, score: 0, started_at}`. The raw `word` field is NOT in the response until state is terminal.
- [ ] `POST /api/v1/games/{id}/guesses` with `{letter: "a"}` returns 200 with the updated game DTO. Invalid letter (non a–z, length ≠ 1, or already-guessed) returns 422 with the standard error envelope from `rules/api-design.md`.
- [ ] Guesses are case-insensitive (`"A"` and `"a"` are the same guess).
- [ ] When state becomes WON or LOST, the response includes the now-unmasked `word`.
- [ ] The UI renders a masked word (one underscore `_` per hidden letter, actual letter per revealed letter, spaces between) and disables on-screen keyboard letters that have been guessed.
- [ ] The ASCII hangman figure has **9 states**: stage 0 (empty gallows) + stages 1–8 (the 8 hanging parts). Easy (8 lives) uses stages 0–8; Medium (6 lives) uses stages 2–8 (starts further along); Hard (4 lives) uses stages 4–8. The backend computes `lives_remaining` and the frontend maps to stage = `wrong_guesses_allowed - lives_remaining + (8 - wrong_guesses_allowed)` so all three difficulties end at the same stage-8 "fully hanged" figure.
- [ ] Category "Animals" is valid; so are "Food" and "Tech". Any other category returns 422.
- [ ] Difficulty is one of `easy` (8 lives), `medium` (6 lives), `hard` (4 lives). Any other value returns 422.

**Edge Cases:**

| Condition                                            | Expected Behavior                                                                                               |
| ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Guess a letter already guessed                       | 422 `ALREADY_GUESSED` with message; game state unchanged; letter remains disabled in UI                         |
| Guess a non-letter (digit, symbol, multi-char)       | 422 `INVALID_LETTER`                                                                                            |
| Guess uppercase                                      | Normalized to lowercase; treated as the same guess as lowercase                                                 |
| `POST /games/{id}/guesses` on a terminal game        | 409 `GAME_ALREADY_FINISHED`                                                                                     |
| Game id does not exist or belongs to another session | 404 `GAME_NOT_FOUND` (do not leak existence across sessions)                                                    |
| Cookie missing on first request                      | Backend assigns new session cookie on response, creates session row, proceeds                                   |
| Word pool for chosen category is empty               | Startup fails loudly (words.py validates at load); will not happen in practice since seed has ≥ 15 per category |

**Priority:** Must Have

---

### US-002: See score and streak

**As a** local player
**I want** my wins to earn points and my consecutive wins to multiply the score
**So that** I have a reason to keep playing and improving

**Scenario:**

```gherkin
Given I have completed 1 previous game that I WON (streak = 1, total_score = X)
When I win my next round with 4 correct-letter reveals and 3 lives remaining
Then the round base_score is computed as (4 × 10) + (3 × 5) = 55
And because my resulting streak is 2, the round score is 55 × 2 = 110
And total_score becomes X + 110
And current_streak becomes 2
And best_streak is max(best_streak, 2)
When I lose my next round
Then the round score is 0
And current_streak resets to 0
And best_streak is unchanged
When I win my next round with streak reaching 3
Then the multiplier is 3× and persists for every subsequent consecutive win until a loss
```

**Acceptance Criteria:**

- [ ] Base score per won round = `correct_letter_reveals × 10 + lives_remaining × 5`. A correct-letter reveal counts once per letter guess, not once per revealed character (guessing `l` in "hello" is 1 reveal, not 2).
- [ ] Streak multiplier: `1×` if `streak_after_this_win < 2`, `2×` if `streak_after_this_win == 2`, `3×` if `streak_after_this_win >= 3`.
- [ ] Round score applied to `game.score` is the post-multiplier value. The game DTO exposes `score`; the session DTO exposes `current_streak`, `best_streak`, `total_score`.
- [ ] Loss: `game.score = 0`, `session.current_streak = 0`, `session.best_streak` unchanged.
- [ ] `Session.total_score` is the sum of all game scores for that session (monotonically non-decreasing).
- [ ] UI displays `current_streak`, `best_streak`, `total_score` in a `ScorePanel` component on the main game view.
- [ ] `GET /api/v1/session` returns 200 with `{current_streak, best_streak, total_score}` for the caller's session. New-session cookie is created on this call if no cookie is present (all three fields return 0 for a brand-new session). Frontend `ScorePanel` reads this endpoint on mount and after every game transition so it doesn't have to reconstruct session state from game DTOs.

**Edge Cases:**

| Condition                                                         | Expected Behavior                                              |
| ----------------------------------------------------------------- | -------------------------------------------------------------- |
| Win with 0 lives lost (perfect game)                              | Base = `reveals × 10 + wrong_guesses_allowed × 5` — max reward |
| Win a single-letter-reveal word (impossible with ≥ 4-letter seed) | Formula still applies; no special-casing                       |
| Streak increments beyond 3                                        | Multiplier stays 3× (no higher tier in v0)                     |
| Forfeit via starting a new game (US-005)                          | Treated as a loss for streak/score purposes                    |

**Priority:** Must Have

---

### US-003: Review finished-game history

**As a** local player
**I want** to see my past finished games for this browser session
**So that** I can track progress and revisit words I missed

**Scenario:**

```gherkin
Given I have finished 3 games across 2 categories and 2 difficulties in this session
When I open the app (or click "History")
Then I see a list of all 3 finished games, newest first
And each row shows: category, difficulty, word, state (WON/LOST), score, finished_at timestamp
And an IN_PROGRESS game is NOT in history
```

**Acceptance Criteria:**

- [ ] `GET /api/v1/history` returns `{items: [...], total, page, page_size}` per `rules/api-design.md`. Default page_size = 20, max 100.
- [ ] Items ordered by `finished_at DESC`.
- [ ] Only games with state in `{WON, LOST}` are returned — IN_PROGRESS is excluded.
- [ ] Returned fields per item: `id, category, difficulty, word, state, score, wrong_guesses, started_at, finished_at`.
- [ ] `HistoryList` React component renders the items in a scrollable list with `data-testid="history-item-{id}"` on each row.
- [ ] Empty history returns `{items: [], total: 0, ...}` with 200 OK; UI shows empty-state message.

**Edge Cases:**

| Condition                                | Expected Behavior                                                  |
| ---------------------------------------- | ------------------------------------------------------------------ |
| Cross-session request (different cookie) | Returns only the caller's session history (scoped by `session_id`) |
| `page` out of range                      | Returns empty `items` with correct `total`, 200 OK                 |

**Priority:** Must Have

---

### US-004: Session persists across reloads and visits

**As a** local player
**I want** my score, streak, and history to survive browser reloads and return visits within 30 days
**So that** my progress accumulates across sessions

**Scenario:**

```gherkin
Given I have played some games and accumulated score/streak/history
When I reload the page
Then the ScorePanel still shows my score, current_streak, best_streak
And the HistoryList still shows my past games
When I close the browser and return 7 days later
Then my session is restored via the cookie and state is intact
When I clear cookies
Then I'm treated as a new user (score = 0, no history)
```

**Acceptance Criteria:**

- [ ] On every request with no session cookie, the backend creates a new `Session` row, sets a `session_id` cookie (opaque UUID v4), `HttpOnly=true`, `SameSite=Lax`, `Secure=false` (local HTTP only), `Max-Age = 30 days`.
- [ ] On every request with a valid `session_id` cookie pointing to an existing `Session` row, the backend attaches that session to the request; `session.updated_at` is touched.
- [ ] On every request with a cookie whose UUID does NOT match any `Session` row, the backend issues a fresh cookie + session (stale cookie handled gracefully — no 401/500).
- [ ] Reload persists: the UI re-fetches `GET /api/v1/games/current` and `GET /api/v1/history` on mount and renders accordingly.
- [ ] Cookie UUIDs are generated via Python `uuid.uuid4()` (random, not sequential).

**Edge Cases:**

| Condition                  | Expected Behavior                                                                           |
| -------------------------- | ------------------------------------------------------------------------------------------- |
| Two tabs open concurrently | Both share the same session cookie; one active game rule (US-005) still applies across tabs |
| DB is empty (first launch) | New session created on first request; all endpoints behave as per empty-session defaults    |

**Priority:** Must Have

---

### US-005: One active game per session (forfeit-on-start)

**As a** local player
**I want** the system to prevent me from having two IN_PROGRESS games at once
**So that** my streak and score stay unambiguous

**Scenario:**

```gherkin
Given I have an IN_PROGRESS game in category "Animals"
When I pick category "Tech" and click "Start New Game" without finishing the current one
Then the UI prompts "You have an active game. Starting a new one will forfeit it. Continue?"
When I confirm
Then the previous game state becomes LOST
And my current_streak resets to 0
And a new IN_PROGRESS game is created
When I cancel the prompt
Then nothing changes — my IN_PROGRESS Animals game remains active
```

**Acceptance Criteria:**

- [ ] `POST /api/v1/games` accepts the new-game request, finds any existing IN_PROGRESS game for the session, atomically transitions it to LOST (score=0, finished_at=now) + resets `session.current_streak=0`, then creates the new game. All in one transaction.
- [ ] The response for a new game includes a `forfeited_game_id` field (nullable int) indicating which game was forfeited, if any.
- [ ] The UI shows a native `window.confirm` (simple for scaffold — can upgrade to a custom modal later) when starting a new game while `GET /games/current` returns a non-404 IN_PROGRESS game.
- [ ] `GET /api/v1/games/current` returns 200 with the DTO if an IN_PROGRESS game exists, else 404.

**Edge Cases:**

| Condition                                                  | Expected Behavior                                                                              |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| User force-calls `POST /games` via curl without confirming | Backend still forfeits the prior game. The confirm is a UX affordance, not a security boundary |
| Prior game is already terminal (WON/LOST)                  | `forfeited_game_id` is null; no forfeit transition happens                                     |

**Priority:** Must Have

---

## 5. Technical Constraints

### Known Limitations

- **Local-only, single-user.** No auth, no HTTPS enforcement, `Secure=false` cookies.
- **SQLite file-based DB.** File location: `backend/hangman.db` (gitignored). Schema managed via SQLAlchemy `Base.metadata.create_all(engine)` at startup — no Alembic in the scaffold (Alembic can be added in a future feature if schema evolution becomes painful).
- **Vite dev server on port 3000** proxies `/api/*` to `http://localhost:8000` (FastAPI). This avoids CORS in dev.
- **No concurrency orchestrator.** Backend on terminal A (`make backend`), frontend on terminal B (`make frontend`). Documented in README.
- **No word-pool filtering by difficulty.** Difficulty controls only wrong-guesses-allowed. All words in a chosen category are eligible at any difficulty.
- **Sync Python stack** (decided 2026-04-22 after research — see `docs/research/2026-04-22-hangman-scaffold.md`). All FastAPI route handlers are `def` (not `async def`), SQLAlchemy uses the sync `Session` API, tests use sync `TestClient`. No `pytest-asyncio`, no `aiosqlite`. Rationale: single-user local SQLite has no concurrency; async + sync-DB is a documented performance trap; async + async doubles dependency complexity (`aiosqlite`, lifespan gymnastics in tests) for zero benefit at this scale.
- **Hand-rolled session cookie dependency** (not Starlette `SessionMiddleware`). A FastAPI `Depends()` reads `request.cookies["session_id"]`, looks up / creates the `Session` row, and calls `response.set_cookie(httponly=True, samesite="lax", secure=False, max_age=2592000)` on first response. Starlette's `SessionMiddleware` is designed for signed key/value session stores (requires `itsdangerous` + a secret) and adds surface for no benefit — our cookie is an opaque UUID with no embedded payload.

### Dependencies

- **Requires:** Python 3.12+, **Node 22+**, **pnpm 10+**, uv (Python package manager). (Node 20 + pnpm 9 were the original defaults; updated 2026-04-22 because `pnpm` 10 dropped Node 20 and `pnpm` 9 EOL is 2026-04-30. See `docs/research/2026-04-22-hangman-scaffold.md` §Open Risks.)
- **Blocked by:** None.

### Integration Points

- None — fully offline, no external API calls.

## 6. Data Requirements

### New Data Models

**`Session` (table `sessions`):**

- `id: UUID (PK, cookie value, stored as string)`
- `created_at: datetime (UTC)`
- `updated_at: datetime (UTC)`
- `current_streak: int (default 0)`
- `best_streak: int (default 0)`
- `total_score: int (default 0)`

**`Game` (table `games`):**

- `id: int (PK, autoinc)`
- `session_id: UUID (FK → sessions.id, indexed)`
- `category: str (non-null, enum of seed categories)`
- `difficulty: str (enum: 'easy' | 'medium' | 'hard')`
- `word: str (non-null, lowercase)`
- `wrong_guesses_allowed: int (non-null, derived from difficulty)`
- `state: str (enum: 'IN_PROGRESS' | 'WON' | 'LOST', indexed)`
- `wrong_guesses: int (default 0)`
- `guessed_letters: str (default '', sorted lowercase letters joined, e.g. 'aelt')`
- `score: int (default 0)`
- `started_at: datetime (UTC, non-null)`
- `finished_at: datetime (UTC, nullable)`

**Indexes:** `(session_id, state)` composite index to speed up `GET /games/current` and `GET /history`.

**`words.txt` (file):**

- Location: `backend/words.txt`
- Format: CSV, `category,word` per line. No header row. Lines starting with `#` are comments. Blank lines ignored. Words are lowercase a–z only (validated at load).
- Seed: 15 × 3 = 45 entries (Animals, Food, Tech). Word length 4–12.

### Data Validation Rules

- `category`: must be in the set of categories defined at startup by `words.py` from `words.txt`. Unknown category → 422.
- `difficulty`: must be in `{easy, medium, hard}`. Unknown → 422.
- `letter` (guess payload): exactly 1 character, `a–z` after lowercasing. Else → 422.
- `word` (in DB): validated at load time — all lowercase, `a–z` only, length ≥ 3.

### Data Migration

- None. Greenfield schema, `create_all` at startup.

## 7. Security Considerations

- **Authentication:** None. Local-only single-user. Session cookie identifies browser, not a user identity.
- **Authorization:** Session scoping — every game/history query is filtered by the caller's `session_id`. Cross-session access returns 404, not 403, so existence isn't leaked.
- **Data Protection:** No sensitive data collected. No PII. The cookie is an opaque UUID with no embedded identity.
- **Cookies:** `HttpOnly=true` (blocks JS access — unnecessary since no JS threat model applies, but good hygiene), `SameSite=Lax` (CSRF mitigation), `Secure=false` (local HTTP). 30-day `Max-Age`.
- **Input validation:** All request bodies validated by Pydantic per `rules/api-design.md` and `rules/security.md`. No string-concat SQL — all queries via SQLAlchemy ORM.
- **Audit:** None needed for v0. Backend logs at INFO level include `session_id` (abbreviated to first 8 chars) and game id, but never the `word` field until the game is terminal.
- **Error envelope:** All errors follow the `rules/api-design.md` envelope with `code`, `message`, `details`, `request_id` (generated per request via FastAPI middleware).

## 8. Open Questions

- [ ] Confirm seed word lists for Animals / Food / Tech — I'll propose ~15 each in the plan, flag during plan review if KC wants different words.
- [ ] Confirm the ASCII hangman stages (exact art for stages 0–8) — I'll propose them in the plan; easy to iterate.

## 9. References

- **Discussion Log:** `docs/prds/hangman-scaffold-discussion.md`
- **Project decisions:** `CONTINUITY.md` (tech stack, file structure), `CLAUDE.md` (overview, E2E config, design preferences)
- **Rules:** `.claude/rules/api-design.md`, `.claude/rules/testing.md`, `.claude/rules/security.md`, `.claude/rules/principles.md`
- **Competitor reference:**
  - [Hangmanwords.com — best hangman words](https://www.hangmanwords.com/words) (word-selection guidance)
  - [Coolmath Games Hangman](https://www.coolmathgames.com/0-hangman) (scoring + difficulty patterns)
  - [Thiagi — Hangman Step by Step](https://thiagi.net/archive/www/wgs-hangmanStepByStep.html) (game flow reference)
  - [Duke CompSci 101 Hangman Categories](https://courses.cs.duke.edu/fall14/compsci101/assign/assign7/categories.html) (category organization)

---

## Appendix A: Revision History

| Version | Date       | Author      | Changes                                                                                                                                                                                                                                      |
| ------- | ---------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.0     | 2026-04-22 | Claude + KC | Initial PRD                                                                                                                                                                                                                                  |
| 1.1     | 2026-04-22 | Claude + KC | Post-research patches: sync Python stack (no `async def`, no `pytest-asyncio`), hand-rolled cookie dependency (no Starlette `SessionMiddleware`), bump prereqs Node 22+/pnpm 10+. Sources in `docs/research/2026-04-22-hangman-scaffold.md`. |
| 1.2     | 2026-04-22 | Claude + KC | Add `GET /api/v1/session` endpoint (surfaced during Section 3 of brainstorming — `ScorePanel` needs session state independently of game DTOs). `<div role="alert">` chosen over toast library. Error-banner UX confirmed.                    |

## Appendix B: Approval

- [ ] Product Owner approval
- [ ] Technical Lead approval
- [ ] Ready for technical design
