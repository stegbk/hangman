# E2E Use Cases — hangman-scaffold (graduated 2026-04-23 from docs/plans/2026-04-22-hangman-scaffold-plan.md)

## E2E Use Cases (Phase 3.2b)

These use cases belong in this plan file during execution. After Phase 5.4 passes, they graduate to `tests/e2e/use-cases/` (Phase 6.2b) and a `.spec.ts` (Phase 6.2c).

All use cases run against the Hangman fullstack app: API on :8000, UI on :3000 via Playwright MCP (for UI steps) + direct HTTP (for API steps).

### UC1 — Happy path: play a round end-to-end and persist (@smoke, covers US-001 + US-002 + US-004)

**Interface:** API + UI (API-first per `rules/testing.md`)

**Intent:** A fresh local player picks a category and difficulty, plays a round through to completion, and sees score + streak + history update. Reloading the page preserves state.

**Setup:** None (fresh session).

**Steps (API phase):**

1. `GET /api/v1/categories` — expect 200 + 3 categories (animals, food, tech) + 3 difficulties (easy/8, medium/6, hard/4). Capture `Set-Cookie` header; re-use cookie on all subsequent calls.
2. `GET /api/v1/session` — expect 200 + `{current_streak: 0, best_streak: 0, total_score: 0}`.
3. `GET /api/v1/games/current` — expect 404 `NO_ACTIVE_GAME`.
4. `POST /api/v1/games` with `{category: "animals", difficulty: "easy"}` — expect 201 + `Location: /api/v1/games/<id>` + game DTO with `masked_word` all underscores, `lives_remaining: 8`, `forfeited_game_id: null`, and **`word` key ABSENT** (PRD US-001 requires omission, not null).
5. Guess every letter a–z via `POST /api/v1/games/{id}/guesses` until state is WON or LOST. At each step assert 200 and state transitions match (IN_PROGRESS → WON or LOST on final guess).
6. `GET /api/v1/session` — if WON: `current_streak == 1`, `best_streak >= 1`, `total_score > 0`. If LOST: all zeros.
7. `GET /api/v1/history` — expect `items.length == 1`, item's `state` matches prior.

**Steps (UI phase):**

8. Navigate to `http://localhost:3000`.
9. Verify `ScorePanel` shows the same numbers as step 6.
10. Verify `HistoryList` shows the one played game with category, difficulty, word (revealed), and score.
11. Verify `GameBoard` shows the terminal banner (`data-testid="game-won"` with revealed word for a WON game, or `data-testid="game-lost"` for a LOST game). The terminal game remains in `currentGame` until the user starts a new one — the banner is the "what just happened" affordance, not an empty state. (`GameBoard` only shows "Pick a category to start." when there has never been a game this session.)
12. Reload the page (Ctrl+R). Verify the ScorePanel + HistoryList still show the same values (session cookie persisted).

**Verification (ARRANGE/VERIFY boundary):** API assertions via HTTP status + JSON body. UI assertions via `data-testid` selectors (`score-total`, `streak-current`, `streak-best`, `history-item-<id>`). No direct DB reads.

**Persistence:** Step 12 reload is the persistence check.

### UC2 — Loss resets streak to 0 (covers US-002 loss behavior)

**Interface:** API + UI

**Intent:** A player on a win streak loses a round; `current_streak` resets to 0, `best_streak` is unchanged, the game appears in history as LOST with score 0.

**Setup:**

1. Via `POST /api/v1/games` + sequential correct-letter guesses, achieve at least one WON game so `current_streak >= 1` and `best_streak >= 1`.

**Steps:**

2. `POST /api/v1/games` with a new category — should not forfeit because the prior is already WON.
3. Intentionally guess wrong letters (use letters not in common English: `q`, `x`, `z`, then continue with rarely-used letters) until `state == LOST`.
4. `GET /api/v1/session` — assert `current_streak == 0`, `best_streak` unchanged from pre-loss value.
5. `GET /api/v1/history` — assert the LOST game exists, `score == 0`.

**UI verification:**

6. Reload `http://localhost:3000`. `streak-current` shows 0, `streak-best` shows the pre-loss value, `history-item-<id>` shows the LOST game.

**Persistence:** UI reload in step 6.

### UC3 — Forfeit flow (covers US-005)

**Interface:** UI (primary — tests the `window.confirm` prompt) + API (for state inspection)

**Intent:** Starting a new game while one is in progress forfeits the active one.

**Setup:**

1. Start a game via UI: pick animals/easy, click Start. Guess 1 letter to confirm it's mid-play.

**Steps:**

2. In `CategoryPicker`, change category to "food" and difficulty to "medium". Click Start.
3. Browser shows `window.confirm` prompt: "You have an active game. Starting a new one will forfeit it. Continue?"
4. Accept the prompt.
5. Observe: a new game is in the `GameBoard` (masked word all underscores, 6 lives). `ScorePanel` shows `current_streak: 0` (reset from any prior streak).
6. `HistoryList` shows the forfeited game as LOST with score 0.

**API verification** (using same session cookie as browser):

7. `GET /api/v1/history` — assert the forfeited game is present with `state == LOST`, `score == 0`.

**Persistence:** 8. Reload the page. New game state is retained (`GET /games/current` returns the new game), history shows the forfeited one.

### UC3b — Terminal game → start new → NO forfeit confirm (covers US-005 inverse, added 2026-04-23 after user playtest)

**Interface:** UI

**Intent:** When the current game is terminal (WON or LOST), starting a new one must NOT show the forfeit confirmation — there's nothing to forfeit. PRD US-005 AC scopes the confirm to IN_PROGRESS games only. This UC exists because the original UC3 only covers the IN_PROGRESS path, so a regression in the frontend's "is this game forfeitable?" check would slip through.

**Setup:**

1. Start a game via UI (defaults OK: animals/easy).
2. Play through to a terminal state — either guess letters until you win, or guess 8 wrong letters to lose. (Losing is faster — click `q`, `x`, `z`, `j`, `v`, `w`, `k`, `y` on the keyboard.)
3. Verify the terminal banner appears: `data-testid="game-won"` or `data-testid="game-lost"`.

**Steps:**

4. With the terminal banner still visible on screen, click the `data-testid="start-game-btn"` button (with the same or different category/difficulty — doesn't matter).
5. **Hook `window.confirm`** before the click (Playwright: `page.on('dialog', ...)`) to detect whether a confirm dialog fires.

**Verification:**

6. No `window.confirm` dialog fires. The dialog handler count is zero.
7. A new game appears: `data-testid="game-board"` visible with a fresh masked word; terminal banner is gone.
8. `GET /api/v1/games/current` returns 200 with the new game (IN_PROGRESS).
9. `GET /api/v1/history` still contains the terminal game from step 2 (and nothing else new — there's no "forfeited" ghost game).

**Persistence:** Reload — new game state survives; history unchanged from step 9.

### UC4 — Mid-game reload persists IN_PROGRESS state (covers US-004)

**Interface:** UI

**Intent:** A reload mid-game brings back the exact game state: masked word, guessed letters, lives remaining.

**Setup:**

1. Start a game via UI: animals/easy.
2. Guess 3 letters (mix correct and wrong).
3. Capture the visible `masked_word`, `guessed_letters` keyboard disabled set, `lives-remaining`.

**Steps:**

4. Reload the page.
5. Verify:
   - `masked-word` shows the exact same revealed pattern.
   - In `Keyboard`, the same 3 letter buttons are disabled.
   - `lives-remaining` shows the exact same count.

**Persistence:** The reload itself is the persistence test.

### Regression on cookie edge cases (minor, part of UC1)

Not a separate UC. Covered inside UC1 step 1's cookie attribute assertions (HttpOnly + SameSite=Lax + Max-Age=2592000).
