"""Shared fixtures for dashboard tests."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "dashboard"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def minimal_ndjson_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "minimal.ndjson"


@pytest.fixture
def multi_ndjson_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "multi_scenario.ndjson"
