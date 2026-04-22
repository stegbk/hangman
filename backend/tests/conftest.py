"""Shared pytest fixtures for the backend test suite."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from hangman.models import Base


@pytest.fixture
def engine():
    """Fresh in-memory SQLite engine with StaticPool (shared across connections)."""
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
    """Test-scoped ORM session. Commits land in the in-memory DB per-test."""
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    db = testing_session()
    try:
        yield db
    finally:
        db.close()
