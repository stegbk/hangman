"""Minimal FastAPI app fixture — 2 routes, both calling validate_letter."""

from fastapi import APIRouter, FastAPI
from tests.fixtures.branch_coverage.minimal_app.game import validate_letter

router = APIRouter(prefix="/api/v1")


@router.post("/games")
def create_game() -> dict:
    return {"id": "fixture-1"}


@router.post("/games/{game_id}/guesses")
def make_guess(game_id: str, letter: str) -> dict:
    normalized = validate_letter(letter)
    return {"guess": normalized}


app = FastAPI()
app.include_router(router)
