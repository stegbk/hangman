"""Shared pytest fixtures for the backend test suite."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from hangman.db import get_session
from hangman.models import Base
from hangman.words import WordPool


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine) -> Iterator[OrmSession]:
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    db = testing_session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_word_pool() -> WordPool:
    # 'test' is a deterministic 1-word category used by scoring/win tests that
    # need a hermetic path: POST /games {category: "test"} → always pick "cat" →
    # guess c, a, t → win. Avoids nondeterministic "guess a-z exhaustively" flakes.
    return WordPool(
        categories={
            "animals": ("cat", "dog", "bird", "fish"),
            "food": ("pizza", "taco", "pasta"),
            "test": ("cat",),
        }
    )


@pytest.fixture
def client(engine, test_word_pool) -> Iterator[TestClient]:
    """TestClient with an in-memory DB + test word pool injected via dependency overrides + app.state."""
    # Import lazily so tasks before `main.py` exists can still run.
    from hangman.main import app

    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def _override_get_session() -> Iterator[OrmSession]:
        db = testing_session()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_session] = _override_get_session
    with TestClient(app) as c:
        c.app.state.word_pool = test_word_pool  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()
