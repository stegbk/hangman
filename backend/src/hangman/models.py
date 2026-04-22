"""SQLAlchemy 2.0 ORM — Session + Game tables."""

from datetime import UTC, datetime
from typing import Final

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now_utc() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=_now_utc)
    updated_at: Mapped[datetime] = mapped_column(default=_now_utc, onupdate=_now_utc)
    current_streak: Mapped[int] = mapped_column(default=0)
    best_streak: Mapped[int] = mapped_column(default=0)
    total_score: Mapped[int] = mapped_column(default=0)


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    category: Mapped[str]
    difficulty: Mapped[str]  # 'easy' | 'medium' | 'hard' (enforced at API boundary)
    word: Mapped[str]
    wrong_guesses_allowed: Mapped[int]
    state: Mapped[str] = mapped_column(default="IN_PROGRESS", index=True)
    wrong_guesses: Mapped[int] = mapped_column(default=0)
    correct_reveals: Mapped[int] = mapped_column(default=0)
    guessed_letters: Mapped[str] = mapped_column(default="")
    score: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(default=_now_utc)
    finished_at: Mapped[datetime | None] = mapped_column(default=None, nullable=True)

    __table_args__ = (Index("ix_games_session_state", "session_id", "state"),)


STATE_IN_PROGRESS: Final = "IN_PROGRESS"
STATE_WON: Final = "WON"
STATE_LOST: Final = "LOST"
