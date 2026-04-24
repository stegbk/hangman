"""Shared fixtures for dashboard tests."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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


@dataclass
class FakeToolUseBlock:
    name: str
    input: dict  # type: ignore[type-arg]
    type: str = "tool_use"


@dataclass
class FakeUsage:
    input_tokens: int = 1000
    output_tokens: int = 200
    cache_creation_input_tokens: int = 800
    cache_read_input_tokens: int = 0


@dataclass
class FakeMessage:
    content: list  # type: ignore[type-arg]
    usage: FakeUsage = field(default_factory=FakeUsage)
    model: str = "claude-sonnet-4-6"


class MockAnthropicClient:
    """Deterministic stand-in for anthropic.Anthropic.

    Configure behavior by appending to .scripted_responses.  Each call
    to messages.create pops the next response (or errors if exhausted). Each
    response can be:
      - a FakeMessage (returned as-is)
      - an Exception instance (raised)
      - a dict payload (wrapped in FakeMessage with a tool_use block)
    """

    def __init__(self) -> None:
        self.scripted_responses: list[Any] = []
        self.calls: list[dict[str, Any]] = []
        self.messages = self

    def create(self, **kwargs: Any) -> FakeMessage:
        self.calls.append(kwargs)
        if not self.scripted_responses:
            raise AssertionError("MockAnthropicClient called but no scripted response queued")
        response = self.scripted_responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        if isinstance(response, FakeMessage):
            if len(self.calls) > 1:
                # Simulate cache HIT on call 2+ by moving creation→read.
                response.usage = FakeUsage(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    cache_creation_input_tokens=0,
                    cache_read_input_tokens=response.usage.cache_creation_input_tokens or 800,
                )
            return response
        if isinstance(response, dict):
            block = FakeToolUseBlock(name="ReportFindings", input=response)
            return FakeMessage(content=[block])
        raise AssertionError(f"Unsupported scripted response: {type(response).__name__}")


@pytest.fixture
def mock_anthropic_client() -> MockAnthropicClient:
    return MockAnthropicClient()


@pytest.fixture
def good_tool_input(fixtures_dir: Path) -> dict:  # type: ignore[type-arg]
    return json.loads((fixtures_dir / "llm_response_good.json").read_text())


@pytest.fixture
def malformed_tool_input(fixtures_dir: Path) -> dict:  # type: ignore[type-arg]
    return json.loads((fixtures_dir / "llm_response_malformed.json").read_text())
