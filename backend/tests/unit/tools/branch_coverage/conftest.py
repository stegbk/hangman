"""Shared fixtures for branch_coverage tests."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "branch_coverage"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def minimal_app_source_root(fixtures_dir: Path) -> Path:
    return fixtures_dir / "minimal_app"
