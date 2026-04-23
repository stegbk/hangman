# Design: Hangman Scaffold

**Date:** 2026-04-22
**Status:** Approved (sections 1–5)
**PRD:** `docs/prds/hangman-scaffold.md` (v1.2)
**Research brief:** `docs/research/2026-04-22-hangman-scaffold.md`

This document is the technical design for the hangman-scaffold feature. It turns the PRD's user-story requirements into a module-by-module architecture with clear seams, concrete responsibilities, and a test strategy. It is the input to the implementation plan (Phase 3.2, `/superpowers:writing-plans`).

---

## Summary of load-bearing decisions

Locked by PRD v1.2 and the research brief, restated here so the design reads cold:

- **Sync Python stack.** All FastAPI route handlers `def` (not `async def`), SQLAlchemy 2.0 sync `Session`, sync `TestClient` for tests. No `pytest-asyncio`, no `aiosqlite`. Rationale: single-user local SQLite has zero concurrency; async + sync-DB is a perf trap; async + async adds dependency complexity for no benefit.
- **Hand-rolled cookie dependency.** A FastAPI `Depends()` reads `request.cookies["session_id"]`, looks up / creates the `Session` row, and calls `response.set_cookie(httponly=True, samesite="lax", secure=False, max_age=2592000)`. No Starlette `SessionMiddleware` (that's for signed key/value stores and requires `itsdangerous` + a secret).
- **Node 22+, pnpm 10+.** Updated from "Node 20+, pnpm 9+" because pnpm 10 dropped Node 20 and pnpm 9 EOLs 2026-04-30.
- **Frontend state = prop-drilling from `App.tsx`.** Depth is 1, five components, `App` owns all state. No Context, no Zustand, no `useReducer`. YAGNI-trivial refactor if the tree deepens.
- **Plain CSS, ASCII hangman figure, `<div role="alert">` errors.** Visual polish is a future feature; this scaffold deliberately ships minimal UI.
- **Playwright framework installed in this PR.** `playwright.config.ts` inside `frontend/` per the monorepo pattern in `rules/testing.md`.

---

## 1. Architecture

Monorepo with `backend/` (FastAPI + SQLite, uv-managed) and `frontend/` (React 19 + Vite 8 + TypeScript, pnpm-managed). Root `Makefile` for common commands. Dev flow = two terminals: `make backend` → uvicorn `:8000`, `make frontend` → vite `:3000` proxying `/api/*` to the backend.

```
hangman/
├── backend/
│   ├── src/hangman/          # PEP 621 src-layout
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI() + lifespan(create_all, load_words) + include_router + middleware + exception handlers
│   │   ├── game.py           # PURE state machine + scoring (no FastAPI, no SQLAlchemy imports)
│   │   ├── routes.py         # APIRouter under /api/v1, all 6 endpoints
│   │   ├── schemas.py        # Pydantic v2 request/response models
│   │   ├── models.py         # SQLAlchemy 2.0 DeclarativeBase + Mapped[...] + mapped_column
│   │   ├── db.py             # engine + SessionLocal + get_session() dep
│   │   ├── sessions.py       # get_or_create_session() Depends() (cookie ↔ Session row)
│   │   ├── words.py          # WordPool + load_words() CSV parser
│   │   └── errors.py         # HangmanError, error-envelope handlers, RequestIdMiddleware
│   ├── tests/
│   │   ├── conftest.py       # engine, client fixtures (in-memory SQLite + StaticPool, test-scoped WORD_POOL)
│   │   ├── unit/
│   │   │   ├── test_game.py
│   │   │   └── test_words.py
│   │   └── integration/
│   │       ├── test_categories.py
│   │       ├── test_games.py
│   │       ├── test_guesses.py
│   │       ├── test_history.py
│   │       └── test_session.py
│   ├── words.txt             # CSV seed (category,word), 45 entries across 3 categories
│   └── pyproject.toml        # uv project, deps + dev-deps via [dependency-groups]
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Owns all state; composes the 5 components + error banner
│   │   ├── main.tsx          # createRoot + <StrictMode>
│   │   ├── components/
│   │   │   ├── GameBoard.tsx
│   │   │   ├── Keyboard.tsx
│   │   │   ├── CategoryPicker.tsx
│   │   │   ├── ScorePanel.tsx
│   │   │   ├── HistoryList.tsx
│   │   │   └── HangmanFigure.tsx
│   │   ├── api/
│   │   │   └── client.ts     # Typed fetch wrappers + ApiError
│   │   ├── types.ts          # DTOs mirroring backend schemas
│   │   ├── styles.css        # Plain CSS, flex column
│   │   └── test/setup.ts     # @testing-library/jest-dom/vitest
│   ├── tests/e2e/
│   │   ├── specs/            # populated by Phase 6.2c (play-round.spec.ts)
│   │   ├── fixtures/auth.ts  # no-op stub (scaffold has no auth; file required by rules/testing.md)
│   │   └── use-cases/        # populated by Phase 6.2b
│   ├── vite.config.ts        # server.port=3000, proxy /api → :8000, changeOrigin
│   ├── vitest.config.ts      # environment: 'jsdom', setupFiles
│   ├── playwright.config.ts  # webServer: [backend, frontend], chromium only
│   ├── eslint.config.js      # ESLint 9 flat config + typescript-eslint + react-hooks + react-refresh + prettier/flat
│   ├── .prettierrc.json
│   ├── tsconfig.json, tsconfig.app.json, tsconfig.node.json
│   └── package.json          # "packageManager": "pnpm@10.x"
├── Makefile                  # install / backend / frontend / test / lint / typecheck / verify
├── .gitignore                # add backend/hangman.db, .venv, node_modules, dist, .env*, playwright-report/
└── docs/                     # prds, plans, research, solutions (existing)
```

Backend route organization is a single `APIRouter` in `routes.py` with resource-grouped helper functions. Per-resource routers would be idiomatic at ~10+ endpoints; we have 6.

---

## 2. Backend modules

Each module has one responsibility. The seams:

- `game.py` imports nothing from FastAPI or SQLAlchemy → 100% unit-testable without mocks.
- `routes.py` is the only module with HTTP decorators → everything else is importable from tests.
- `sessions.py` is a `Depends()` consumed by routes; it depends on `db.py` but not on routes.
- `words.py` loads once at startup; routes read from `app.state.word_pool`.

### `game.py` — pure state machine + scoring

```python
from dataclasses import dataclass
from typing import Literal

Difficulty = Literal["easy", "medium", "hard"]
GameState = Literal["IN_PROGRESS", "WON", "LOST"]

DIFFICULTY_LIVES: dict[Difficulty, int] = {"easy": 8, "medium": 6, "hard": 4}
MAX_FIGURE_STAGE = 8

@dataclass(frozen=True)
class GuessResult:
    new_guessed: str              # sorted lowercase letters, e.g. "aelt"
    new_wrong_guesses: int
    correct_reveal: bool          # True if the letter appeared in the word
    new_state: GameState

class AlreadyGuessed(ValueError): pass
class InvalidLetter(ValueError): pass

def mask_word(word: str, guessed: str) -> str: ...
def apply_guess(word: str, guessed: str, wrong: int, allowed: int, letter: str) -> GuessResult: ...
def figure_stage(wrong_guesses: int, wrong_guesses_allowed: int) -> int: ...
def compute_round_score(correct_reveals: int, lives_remaining: int, streak_after_win: int) -> int: ...
def streak_multiplier(streak: int) -> int:  # 1 / 2 / 3
    ...
```

`apply_guess` is the canonical state transition. It does not mutate anything — it returns a new `GuessResult`, and `routes.py` writes the fields back to the ORM Game row. `routes.py` separately counts correct-letter reveals across the game lifecycle (a tally maintained on the Game row) to feed `compute_round_score` at the WON transition.

**Note on reveal-counting:** The PRD defines a "reveal" as a guess that newly exposes ≥ 1 letter in the masked word. We track this as `correct_reveal: bool` in `GuessResult` and accumulate a counter on the `Game` row (new field, see §3). This keeps `game.py` stateless.

### `words.py` — CSV loader

```python
from dataclasses import dataclass
from pathlib import Path
import random

@dataclass(frozen=True)
class WordPool:
    categories: dict[str, tuple[str, ...]]

    def category_names(self) -> list[str]: ...
    def random_word(self, category: str) -> str: ...

def load_words(path: Path, rng: random.Random | None = None) -> WordPool:
    """
    Parse words.txt. Rules:
      - Lines starting with '#' are comments.
      - Blank lines are ignored.
      - Data lines: 'category,word' (comma split, strip whitespace).
      - Validates: word is non-empty, lowercase a-z only, length >= 3.
      - Categories with zero valid words → ValueError at load time.
      - Raises ValueError on bad line with the line number.
    """
```

`rng` parameter is injection-friendly for deterministic tests; production code passes the module default.

### `models.py` — SQLAlchemy 2.0

```python
class Base(DeclarativeBase): pass

class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(primary_key=True)            # UUID v4 string
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    current_streak: Mapped[int] = mapped_column(default=0)
    best_streak: Mapped[int] = mapped_column(default=0)
    total_score: Mapped[int] = mapped_column(default=0)

class Game(Base):
    __tablename__ = "games"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    category: Mapped[str]
    difficulty: Mapped[str]                                      # 'easy'|'medium'|'hard' (enforced at API)
    word: Mapped[str]                                            # lowercase a-z
    wrong_guesses_allowed: Mapped[int]
    state: Mapped[str] = mapped_column(default="IN_PROGRESS", index=True)
    wrong_guesses: Mapped[int] = mapped_column(default=0)
    correct_reveals: Mapped[int] = mapped_column(default=0)       # NEW — needed for scoring
    guessed_letters: Mapped[str] = mapped_column(default="")
    score: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime]
    finished_at: Mapped[datetime | None] = mapped_column(default=None, nullable=True)

    __table_args__ = (Index("ix_games_session_state", "session_id", "state"),)
```

`correct_reveals` is the one addition vs the PRD data model — required to compute score at the WON transition without replaying guess history.

### `db.py` — engine + session factory

```python
DATABASE_URL = os.environ.get("HANGMAN_DB_URL", "sqlite:///./backend/hangman.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_session() -> Iterator[OrmSession]:
    """FastAPI dep — yields session, rolls back on exception, commits + closes on success."""
```

### `sessions.py` — cookie dependency

```python
COOKIE_NAME = "session_id"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days

def get_or_create_session(request: Request, response: Response, db: OrmSession = Depends(get_session)) -> Session:
    cookie = request.cookies.get(COOKIE_NAME)
    session = db.get(Session, cookie) if cookie else None
    if session is None:
        session = Session(id=str(uuid4()), created_at=now_utc(), updated_at=now_utc())
        db.add(session)
        db.flush()
    response.set_cookie(
        key=COOKIE_NAME, value=session.id, max_age=COOKIE_MAX_AGE,
        httponly=True, samesite="lax", secure=False,
    )
    session.updated_at = now_utc()
    return session
```

### `schemas.py` — Pydantic v2 DTOs

All request / response models separated per `rules/api-design.md`:

- `DifficultyOption` = `{id: Literal[...], label: str, wrong_guesses_allowed: int}`
- `CategoriesResponse` = `{categories: list[str], difficulties: list[DifficultyOption]}`
- `GameCreate` = `{category: str, difficulty: Literal["easy", "medium", "hard"]}` — category is validated against loaded pool in the route (not at schema level; the pool isn't known to Pydantic)
- `GuessRequest` = `{letter: Annotated[str, Field(min_length=1, max_length=1, pattern=r"^[A-Za-z]$")]}` + `field_validator("letter", mode="before")` that lowercases
- `GameResponse` = all `Game` row fields except `word`; with a `model_validator(mode="after")` that adds `word` only if `state != "IN_PROGRESS"`, and computes derived `masked_word` and `lives_remaining`
- `CreateGameResponse` = `GameResponse` + `forfeited_game_id: int | None` (only the `POST /games` route returns this shape; GET routes return `GameResponse`). Per PRD US-005.
- `SessionResponse` = `{current_streak, best_streak, total_score}`
- `HistoryResponse` = paginated `{items: list[GameResponse], total, page, page_size}`
- `ErrorResponse` = the envelope: `{error: {code, message, details, request_id}}`

### `errors.py` — exception handlers + RequestIdMiddleware

```python
class HangmanError(Exception):
    def __init__(self, code: str, http_status: int, message: str, details: list | None = None): ...

# Middleware generates X-Request-ID per request, stores on request.state.request_id,
# returns header on response.

# Exception handlers (installed in main.py):
#   HangmanError        → 4xx with {error: {code, message, details, request_id}}
#   RequestValidationError → 422 with code="VALIDATION_ERROR"
#   Exception (fallback) → 500 with code="INTERNAL_ERROR", message sanitized
```

### `routes.py` — single APIRouter

```python
router = APIRouter(prefix="/api/v1")

@router.get("/categories", response_model=CategoriesResponse)
def list_categories(request: Request): ...

@router.get("/session", response_model=SessionResponse)
def get_session_state(session: SessionModel = Depends(get_or_create_session)): ...

@router.post("/games", response_model=GameResponse, status_code=201)
def start_game(payload: GameCreate, response: Response,
               session: SessionModel = Depends(get_or_create_session),
               db: OrmSession = Depends(get_session),
               request: Request): ...

@router.get("/games/current", response_model=GameResponse)
def get_current_game(session: SessionModel = Depends(get_or_create_session),
                     db: OrmSession = Depends(get_session)): ...

@router.post("/games/{game_id}/guesses", response_model=GameResponse)
def submit_guess(game_id: int, payload: GuessRequest,
                 session: SessionModel = Depends(get_or_create_session),
                 db: OrmSession = Depends(get_session)): ...

@router.get("/history", response_model=HistoryResponse)
def list_history(page: int = 1, page_size: int = 20,
                 session: SessionModel = Depends(get_or_create_session),
                 db: OrmSession = Depends(get_session)): ...
```

`start_game` handles the forfeit transaction (§4 data flow).

### `main.py` — assembly

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    app.state.word_pool = load_words(Path(__file__).parent.parent.parent / "words.txt")
    yield

app = FastAPI(lifespan=lifespan, title="Hangman API", version="0.1.0")
app.add_middleware(RequestIdMiddleware)
app.add_exception_handler(HangmanError, handle_hangman_error)
app.add_exception_handler(RequestValidationError, handle_validation_error)
app.add_exception_handler(Exception, handle_uncaught)
app.include_router(routes.router)
```

---

## 3. Frontend components

All prop-drilled from `App.tsx`. Components are presentational — they receive data + callback props and render. No network calls in components.

### `App.tsx` — state owner

```ts
type AppState = {
  categories: string[];
  difficulties: DifficultyOption[];
  session: SessionDTO | null; // {current_streak, best_streak, total_score}
  currentGame: GameDTO | null; // IN_PROGRESS game
  history: GameDTO[];
  loading: boolean;
  error: string | null;
};
```

**Mount effect** (once, no deps):

```ts
Promise.all([api.getCategories(), api.getSession(), api.getCurrentGame(), api.getHistory()])
  .then(([cats, sess, cur, hist]) => setState({ ... }))
  .catch((e) => setState(s => ({ ...s, error: humanMessage(e), loading: false })));
```

`api.getCurrentGame` converts 404 → `null`.

**Handlers passed down:**

- `onStartGame(category, difficulty)` — if `currentGame != null`, show `window.confirm`; on yes, `api.startGame({category, difficulty})`, replace `currentGame`, refresh `session` + `history`.
- `onGuess(letter)` — `api.guess(currentGame.id, letter)`, replace `currentGame`; on WON/LOST transition, refresh `session` + `history`.

**Error banner:** `<div role="alert" data-testid="error-banner">` rendered at top of App when `error != null`, with a close button that sets `error = null`.

### `api/client.ts`

```ts
const BASE = "/api/v1";

class ApiError extends Error {
  constructor(
    public status: number,
    public body: { error?: { code?: string; message?: string } },
  ) {
    super(body?.error?.message ?? `HTTP ${status}`);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok)
    throw new ApiError(res.status, await res.json().catch(() => ({})));
  return res.status === 204 ? (undefined as T) : await res.json();
}

export const api = {
  getCategories: () => request<CategoriesDTO>("/categories"),
  getSession: () => request<SessionDTO>("/session"),
  getCurrentGame: () =>
    request<GameDTO | null>("/games/current").catch((e) =>
      e instanceof ApiError && e.status === 404 ? null : Promise.reject(e),
    ),
  startGame: (body: GameCreate) =>
    request<GameDTO>("/games", { method: "POST", body: JSON.stringify(body) }),
  guess: (id: number, letter: string) =>
    request<GameDTO>(`/games/${id}/guesses`, {
      method: "POST",
      body: JSON.stringify({ letter }),
    }),
  getHistory: (page = 1) => request<HistoryDTO>(`/history?page=${page}`),
};
```

### `types.ts`

Hand-rolled DTOs mirroring `schemas.py`. Name-matched so any future OpenAPI generator slots in cleanly.

### Components

- **`CategoryPicker`** — `<select data-testid="category-select">` (3 options) + difficulty radios `data-testid="difficulty-easy|medium|hard"` + `<button data-testid="start-game-btn">Start New Game</button>`. Disabled while `loading`. Calls `onStartGame`.
- **`HangmanFigure`** — pure function of `{stage: 0..8}`. 9 ASCII strings in a hard-coded array, rendered in a `<pre data-testid="hangman-figure">`.
- **`GameBoard`** — empty-state when `currentGame === null` (`"Pick a category to start."`). Otherwise renders `HangmanFigure`, `<span data-testid="masked-word">`, `<span data-testid="lives-remaining">`, and a terminal message when `state !== 'IN_PROGRESS'`.
- **`Keyboard`** — grid of 26 `<button data-testid="keyboard-letter-{a..z}">`. Disabled if letter in `guessed_letters` or game terminal. Calls `onGuess(letter)`.
- **`ScorePanel`** — three stats tiles: `data-testid="score-total"`, `data-testid="streak-current"`, `data-testid="streak-best"`. Renders zeros on null session.
- **`HistoryList`** — `<ol>` with `<li data-testid="history-item-{id}">` each showing category/difficulty/word/state/score. Empty state: `"No games played yet."`.

Layout (top-to-bottom flex in `App`):

```
[ScorePanel] [CategoryPicker] [GameBoard (+HangmanFigure)] [Keyboard] [HistoryList]
```

---

## 4. Data flow

### Happy path

```
Mount:
  Promise.all([ getCategories, getSession, getCurrentGame, getHistory ])
  → browser sends cookie (or gets one back)
  → first call creates Session row if missing, sets Set-Cookie header

Start game (no existing IN_PROGRESS):
  POST /games {category, difficulty}
  → get_or_create_session (touches updated_at)
  → SELECT IN_PROGRESS game for session → None
  → WORD_POOL.random_word(category)
  → INSERT games (state=IN_PROGRESS, wrong_guesses_allowed, word, started_at)
  → commit
  → 201 GameResponse (masked_word, lives_remaining computed; word field omitted)

Guess letter (non-terminal):
  POST /games/{id}/guesses {letter}
  → get_or_create_session
  → SELECT game WHERE id AND session_id → else 404 GAME_NOT_FOUND
  → if state != IN_PROGRESS → 409 GAME_ALREADY_FINISHED
  → apply_guess(...) pure
  → if letter in guessed_letters → raises AlreadyGuessed → 422 ALREADY_GUESSED
  → UPDATE games (wrong_guesses, guessed_letters, correct_reveals++ if reveal, state)
  → if state WON: session.current_streak++, session.best_streak=max(...), session.total_score += score;
    game.score = compute_round_score(correct_reveals, lives_remaining, new_streak)
  → if state LOST: session.current_streak=0, game.score=0
  → commit (single transaction)
  → 200 GameResponse (word field included iff terminal)
```

### Forfeit path (US-005)

```
App.tsx: if (currentGame) confirm(...); else proceed
  → POST /games {category, difficulty}
  → BEGIN TRANSACTION
  → SELECT IN_PROGRESS game for session → prior_game
  → if prior_game: UPDATE games SET state='LOST', score=0, finished_at=now WHERE id=prior_game.id
                   UPDATE sessions SET current_streak=0 WHERE id=session.id
  → INSERT new games row
  → COMMIT
  → 201 GameResponse (new game) with {..., forfeited_game_id: prior_game.id or null}
  → frontend re-fetches /session and /history
```

### Error paths

| Scenario                          | Envelope `code`                   | HTTP |
| --------------------------------- | --------------------------------- | ---- |
| Bad category / difficulty         | `VALIDATION_ERROR` (Pydantic)     | 422  |
| Bad letter (non a-z, length != 1) | `VALIDATION_ERROR`                | 422  |
| Category not in loaded pool       | `UNKNOWN_CATEGORY` (HangmanError) | 422  |
| Letter already guessed            | `ALREADY_GUESSED`                 | 422  |
| Guess on terminal game            | `GAME_ALREADY_FINISHED`           | 409  |
| Game id missing or cross-session  | `GAME_NOT_FOUND`                  | 404  |
| Uncaught exception                | `INTERNAL_ERROR`                  | 500  |

`GET /games/current` with no IN_PROGRESS game returns 404 with `code="NO_ACTIVE_GAME"` — this is the one "404 is not an error" response the frontend handles specially (treats as `null`, not error banner).

### Cookie lifecycle

- **First ever request:** no cookie → `get_or_create_session` INSERTs a Session row, sets `Set-Cookie: session_id=<uuid>; HttpOnly; SameSite=Lax; Max-Age=2592000`.
- **Subsequent requests within 30 days:** cookie present → session loaded, `updated_at` touched, cookie re-sent (sliding window).
- **Stale cookie** (Session row deleted, e.g. DB wiped): `db.get()` returns None → treat as new user, INSERT new Session, new cookie. No 401.
- **Browser cookies cleared:** treated as new user.

No cleanup job in scaffold. Sessions live forever in the DB unless manually deleted. A future feature can add a sweeper.

---

## 5. Testing strategy

Four layers, fastest to broadest.

### Layer 1 — Backend unit (`backend/tests/unit/`)

Pure logic only. No FastAPI, no DB.

- **`test_game.py`** — `pytest.mark.parametrize` tables over:
  - `mask_word` — all-revealed, all-hidden, repeated letters
  - `apply_guess` — correct / wrong / already-guessed (raises) / invalid (raises) / WON transition / LOST transition
  - `figure_stage` — all 3 difficulties × wrong 0..max → expected stages 0..8, all end at 8
  - `compute_round_score` — covers 1x / 2x / 3x multiplier boundaries and zero-on-loss
  - `streak_multiplier` — explicit table over streak values 0..5
- **`test_words.py`** — `load_words` against tmpdir CSVs: happy, bad line (non-lowercase), blank/comment handling, short word rejected, empty category rejected, `random_word(unknown_cat)` raises

**Target:** 100% branch coverage on `game.py`, ≥ 95% on `words.py`.

### Layer 2 — Backend integration (`backend/tests/integration/`)

`TestClient(app)` + in-memory SQLite with `StaticPool`. Test-scoped `WORD_POOL` override via `app.state.word_pool` in a fixture.

**`conftest.py`:**

```python
@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    test_db = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{test_db}", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    def _override_get_session():
        db = TestingSessionLocal()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_session] = _override_get_session
    with TestClient(app) as c:
        c.app.state.word_pool = WordPool(categories={"test": ("cat", "dog", "bird", "fish")})
        yield c
    app.dependency_overrides.clear()
```

**Test files** (one per resource area):

- `test_categories.py` — `GET /categories` returns loaded pool + 3 difficulties with correct `wrong_guesses_allowed`
- `test_session.py` — `GET /session` on fresh cookie returns zeros + sets cookie; subsequent calls return same session; cookie header asserts `HttpOnly`, `SameSite=Lax`, `Max-Age=2592000`
- `test_games.py` — start happy (201 + Location), start forfeits prior IN_PROGRESS (prior.state=LOST, score=0, finished_at set, session.current_streak=0, response.forfeited_game_id set), 422 on bad category/difficulty, `GET /games/current` 200 vs 404 (NO_ACTIVE_GAME), cross-session 404 GAME_NOT_FOUND
- `test_guesses.py` — correct reveals decrement none of lives, wrong decrements lives + advances figure stage implicitly (stage computed frontend-side so assertion is on DTO fields), uppercase normalized, ALREADY_GUESSED 422, INVALID_LETTER 422, GAME_ALREADY_FINISHED 409, winning updates session + game.score per formula, losing zeroes streak + game.score
- `test_history.py` — empty returns `{items:[], total:0}`, finished games DESC order, IN_PROGRESS excluded, pagination works

### Layer 3 — Frontend unit (`frontend/src/**/*.test.tsx`)

Vitest + jsdom + `@testing-library/react`. One test file per component (excluding `App.tsx`):

- `HangmanFigure.test.tsx` — 9 stages render expected text
- `Keyboard.test.tsx` — guessed letters disabled; clicking a letter calls `onGuess`; all 26 letters rendered
- `ScorePanel.test.tsx` — renders three tiles with correct testids; handles null session (zeros); handles populated session
- `HistoryList.test.tsx` — empty state; rendered rows with testids; newest first
- `CategoryPicker.test.tsx` — start button disabled while loading; clicking calls `onStartGame(selectedCategory, selectedDifficulty)`; default selections
- `GameBoard.test.tsx` — empty state when `currentGame === null`; IN_PROGRESS renders masked word + lives; WON renders win message + revealed word; LOST renders lose message + revealed word

`App.tsx` is validated end-to-end.

### Layer 4 — E2E

**Markdown use cases** (designed now, executed in Phase 5.4, graduated in Phase 6.2b):

- **UC1** (@smoke, US-001 + US-002 + US-004): Happy path — start Animals/Easy → guess letters to win → score/streak visible → reload → state persists
- **UC2** (US-002 loss behavior): Lose intentionally → round score 0, streak resets, game appears in history as LOST
- **UC3** (US-005 forfeit): Start game → pick new category → confirm → prior game LOST in history, new game IN_PROGRESS
- **UC4** (US-004 mid-game persistence): Play partway → reload → masked word + guessed letters + lives remaining all restored

Full use-case specs with Intent / Setup / Steps / Verification / Persistence go into §6 of the plan file in Phase 3.2b.

**Playwright spec** graduates in Phase 6.2c as `play-round.spec.ts @smoke`.

**`playwright.config.ts`:**

```ts
export default defineConfig({
  testDir: "./tests/e2e/specs",
  use: { baseURL: "http://localhost:3000" },
  webServer: [
    {
      command: "cd ../backend && uv run uvicorn hangman.main:app --port 8000",
      url: "http://localhost:8000/api/v1/categories",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "pnpm dev",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
```

### Quality gates

| Gate                       | Command                                                  | When                                  |
| -------------------------- | -------------------------------------------------------- | ------------------------------------- |
| Backend unit + integration | `uv run pytest` (in `backend/`)                          | Phase 5.3 verify-app                  |
| Backend lint + format      | `uv run ruff check . && uv run ruff format --check .`    | Phase 5.3                             |
| Backend types              | `uv run mypy src/hangman`                                | Phase 5.3                             |
| Frontend unit              | `pnpm test` (vitest run)                                 | Phase 5.3                             |
| Frontend lint + format     | `pnpm lint && pnpm format:check`                         | Phase 5.3                             |
| Frontend types             | `pnpm tsc --noEmit -p tsconfig.app.json`                 | Phase 5.3                             |
| E2E (markdown UCs)         | verify-e2e subagent                                      | Phase 5.4                             |
| E2E (Playwright smoke)     | `cd frontend && pnpm exec playwright test --grep @smoke` | Phase 5.4b / CI-ready (template only) |

All gates must be green before PR. PRD §2 success metrics.

---

## 6. Non-goals / deferred work

Reaffirming the PRD non-goals plus design-specific deferrals:

- No Alembic — `Base.metadata.create_all()` at startup. Schema-change feature will add Alembic later.
- No auth, no leaderboards, no multiplayer.
- No toast library — `<div role="alert">` in App.
- No visual polish, animations, SVG figure — ASCII only.
- No concurrency helper (`concurrently`, `honcho`) — two-terminal dev flow documented.
- No pre-commit hooks — deferred.
- No session sweeper — sessions live forever in DB.
- No OpenAPI client generator — `types.ts` is hand-rolled.

---

## 7. Open questions

- Exact ASCII art for the 9 figure stages — proposed in the plan file, easy to iterate on PR.
- Exact 45 seed words (15 × 3 categories) — proposed in the plan file, easy to iterate on PR.

Both are trivial to revise at implementation time; neither affects the design.

---

## 8. References

- PRD: `docs/prds/hangman-scaffold.md` (v1.2)
- Research brief: `docs/research/2026-04-22-hangman-scaffold.md`
- PRD discussion: `docs/prds/hangman-scaffold-discussion.md`
- Project rules: `.claude/rules/{api-design,testing,security,principles}.md`
- Project context: `CLAUDE.md`, `CONTINUITY.md`
