"""SQLite engine + session factory + FastAPI dependency."""

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker

from hangman.paths import BACKEND_ROOT

_DEFAULT_DB = BACKEND_ROOT / "hangman.db"
DATABASE_URL = os.environ.get("HANGMAN_DB_URL", f"sqlite:///{_DEFAULT_DB}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_session() -> Iterator[OrmSession]:
    """FastAPI dependency: yield an ORM session, rollback on exception, commit + close otherwise."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
