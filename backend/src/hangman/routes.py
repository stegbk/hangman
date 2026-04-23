"""HTTP routes. One APIRouter at /api/v1."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from hangman.db import get_session
from hangman.errors import HangmanError
from hangman.game import (
    DIFFICULTY_LIVES,
    AlreadyGuessed,
    InvalidLetter,
    apply_guess,
    compute_round_score,
)
from hangman.models import STATE_IN_PROGRESS, STATE_LOST, STATE_WON, Game, Session
from hangman.schemas import (
    CategoriesResponse,
    CreateGameResponse,
    GameCreate,
    GameResponse,
    GuessRequest,
    HistoryResponse,
    SessionResponse,
    difficulty_options,
)
from hangman.sessions import get_or_create_session
from hangman.words import WordPool

logger = logging.getLogger("hangman.routes")

router = APIRouter(prefix="/api/v1")


def _word_pool(request: Request) -> WordPool:
    return cast(WordPool, request.app.state.word_pool)  # populated in main.lifespan


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _game_to_response(g: Game) -> GameResponse:
    return GameResponse.from_game_row(
        _word=g.word,
        id=g.id,
        category=g.category,
        difficulty=g.difficulty,
        wrong_guesses_allowed=g.wrong_guesses_allowed,
        wrong_guesses=g.wrong_guesses,
        guessed_letters=g.guessed_letters,
        state=g.state,
        score=g.score,
        started_at=g.started_at,
        finished_at=g.finished_at,
    )


def _game_to_create_response(g: Game, forfeited_game_id: int | None) -> CreateGameResponse:
    return CreateGameResponse.from_game_row(
        _word=g.word,
        forfeited_game_id=forfeited_game_id,
        id=g.id,
        category=g.category,
        difficulty=g.difficulty,
        wrong_guesses_allowed=g.wrong_guesses_allowed,
        wrong_guesses=g.wrong_guesses,
        guessed_letters=g.guessed_letters,
        state=g.state,
        score=g.score,
        started_at=g.started_at,
        finished_at=g.finished_at,
    )


def _assert_category_known(pool: WordPool, category: str) -> None:
    if category not in pool.categories:
        raise HangmanError(
            code="UNKNOWN_CATEGORY",
            http_status=422,
            message=f"Unknown category: {category!r}",
            details=[{"field": "category", "known": pool.category_names()}],
        )


# ---- GET /categories ----


@router.get("/categories", response_model=CategoriesResponse)
def list_categories(
    request: Request,
    # Cookie is created/refreshed on this route too — PRD US-004 requires a
    # session cookie on ANY first request. Callers typically hit /categories first.
    _session: Session = Depends(get_or_create_session),  # noqa: B008
) -> CategoriesResponse:
    pool = _word_pool(request)
    return CategoriesResponse(
        categories=pool.category_names(),
        difficulties=difficulty_options(),
    )


# ---- GET /session ----


@router.get("/session", response_model=SessionResponse)
def get_session_state(
    session: Session = Depends(get_or_create_session),  # noqa: B008
) -> SessionResponse:
    return SessionResponse(
        current_streak=session.current_streak,
        best_streak=session.best_streak,
        total_score=session.total_score,
    )


# ---- POST /games ----


@router.post(
    "/games",
    response_model=CreateGameResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_game(
    payload: GameCreate,
    request: Request,
    response: Response,
    session: Session = Depends(get_or_create_session),  # noqa: B008
    db: OrmSession = Depends(get_session),  # noqa: B008
) -> CreateGameResponse:
    pool = _word_pool(request)
    _assert_category_known(pool, payload.category)

    # Forfeit any existing IN_PROGRESS game in the same transaction.
    stmt = select(Game).where(Game.session_id == session.id, Game.state == STATE_IN_PROGRESS)
    prior = db.execute(stmt).scalar_one_or_none()
    forfeited_id: int | None = None
    if prior is not None:
        old_streak = session.current_streak
        prior.state = STATE_LOST
        prior.score = 0
        prior.finished_at = _now_utc()
        session.current_streak = 0
        forfeited_id = prior.id
        logger.info(
            "forfeit game=%d session=%s streak=%d->0",
            prior.id,
            session.id[:8],
            old_streak,
        )

    word = pool.random_word(payload.category)
    allowed = DIFFICULTY_LIVES[payload.difficulty]
    new_game = Game(
        session_id=session.id,
        category=payload.category,
        difficulty=payload.difficulty,
        word=word,
        wrong_guesses_allowed=allowed,
        state=STATE_IN_PROGRESS,
    )
    db.add(new_game)
    try:
        db.flush()  # assign id; may raise IntegrityError if concurrent POST races us
    except IntegrityError:
        db.rollback()
        # Another concurrent request already created an IN_PROGRESS game; re-select it
        # and attempt forfeit once more.
        prior2 = db.execute(stmt).scalar_one_or_none()
        if prior2 is not None:
            old_streak2 = session.current_streak
            prior2.state = STATE_LOST
            prior2.score = 0
            prior2.finished_at = _now_utc()
            session.current_streak = 0
            forfeited_id = prior2.id
            logger.info(
                "forfeit game=%d session=%s streak=%d->0 (retry after IntegrityError)",
                prior2.id,
                session.id[:8],
                old_streak2,
            )
            db.add(new_game)
            try:
                db.flush()
            except IntegrityError as exc2:
                raise HangmanError(
                    code="CONCURRENT_START",
                    http_status=409,
                    message="Concurrent game creation detected, retry.",
                ) from exc2
        else:
            raise HangmanError(
                code="CONCURRENT_START",
                http_status=409,
                message="Concurrent game creation detected, retry.",
            ) from None

    response.headers["Location"] = f"/api/v1/games/{new_game.id}"
    return _game_to_create_response(new_game, forfeited_id)


# ---- GET /games/current ----


@router.get("/games/current", response_model=GameResponse)
def get_current_game(
    session: Session = Depends(get_or_create_session),  # noqa: B008
    db: OrmSession = Depends(get_session),  # noqa: B008
) -> GameResponse:
    stmt = select(Game).where(Game.session_id == session.id, Game.state == STATE_IN_PROGRESS)
    game = db.execute(stmt).scalar_one_or_none()
    if game is None:
        raise HangmanError(
            code="NO_ACTIVE_GAME",
            http_status=404,
            message="No active game.",
        )
    return _game_to_response(game)


# ---- POST /games/{game_id}/guesses ----


@router.post("/games/{game_id}/guesses", response_model=GameResponse)
def submit_guess(
    game_id: int,
    payload: GuessRequest,
    session: Session = Depends(get_or_create_session),  # noqa: B008
    db: OrmSession = Depends(get_session),  # noqa: B008
) -> GameResponse:
    game = db.get(Game, game_id)
    if game is None or game.session_id != session.id:
        raise HangmanError(code="GAME_NOT_FOUND", http_status=404, message="Game not found.")
    if game.state != STATE_IN_PROGRESS:
        raise HangmanError(
            code="GAME_ALREADY_FINISHED",
            http_status=409,
            message=f"Game is {game.state}.",
        )

    try:
        result = apply_guess(
            word=game.word,
            guessed=game.guessed_letters,
            wrong=game.wrong_guesses,
            allowed=game.wrong_guesses_allowed,
            letter=payload.letter,
        )
    except AlreadyGuessed as e:
        raise HangmanError(code="ALREADY_GUESSED", http_status=422, message=str(e)) from e
    except InvalidLetter as e:
        raise HangmanError(code="INVALID_LETTER", http_status=422, message=str(e)) from e

    game.guessed_letters = result.new_guessed
    game.wrong_guesses = result.new_wrong_guesses
    game.state = result.new_state
    if result.correct_reveal:
        game.correct_reveals += 1

    if result.new_state == STATE_WON:
        lives_remaining = game.wrong_guesses_allowed - game.wrong_guesses
        new_streak = session.current_streak + 1
        game.score = compute_round_score(
            correct_reveals=game.correct_reveals,
            lives_remaining=lives_remaining,
            streak_after_win=new_streak,
        )
        session.current_streak = new_streak
        session.best_streak = max(session.best_streak, new_streak)
        session.total_score = session.total_score + game.score
        game.finished_at = _now_utc()
    elif result.new_state == STATE_LOST:
        game.score = 0
        session.current_streak = 0
        game.finished_at = _now_utc()

    return _game_to_response(game)


# ---- GET /history ----


@router.get("/history", response_model=HistoryResponse)
def list_history(
    page: int = 1,
    page_size: int = 20,
    session: Session = Depends(get_or_create_session),  # noqa: B008
    db: OrmSession = Depends(get_session),  # noqa: B008
) -> HistoryResponse:
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100

    base_stmt = (
        select(Game)
        .where(Game.session_id == session.id, Game.state.in_([STATE_WON, STATE_LOST]))
        .order_by(Game.finished_at.desc())
    )

    total = db.execute(
        select(func.count(Game.id)).where(
            Game.session_id == session.id, Game.state.in_([STATE_WON, STATE_LOST])
        )
    ).scalar_one()

    offset = (page - 1) * page_size
    games = db.execute(base_stmt.limit(page_size).offset(offset)).scalars().all()

    return HistoryResponse(
        items=[_game_to_response(g) for g in games],
        total=int(total),
        page=page,
        page_size=page_size,
    )
