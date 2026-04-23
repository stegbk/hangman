"""FastAPI app assembly + lifespan."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from hangman.db import engine
from hangman.errors import RequestIdMiddleware, install_error_handlers
from hangman.models import Base
from hangman.paths import BACKEND_ROOT
from hangman.routes import router
from hangman.words import load_words


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(engine)
    override = os.environ.get("HANGMAN_WORDS_FILE")
    words_path = Path(override) if override else BACKEND_ROOT / "words.txt"
    if not words_path.is_absolute():
        words_path = (BACKEND_ROOT / words_path).resolve()
    app.state.word_pool = load_words(words_path)
    yield


app = FastAPI(lifespan=lifespan, title="Hangman API", version="0.1.0")
app.add_middleware(RequestIdMiddleware)
install_error_handlers(app)
app.include_router(router)
