"""Tests for LlmEvaluator — mocked Anthropic client, no network."""

import pytest
from tools.dashboard.llm.client import CacheNotActiveError, LlmEvaluator, RubricTooShortError
from tools.dashboard.models import Package, PackageKind


def _pkg(pkg_id: str = "scenario:x.feature:1") -> Package:
    return Package(
        id=pkg_id,
        kind=PackageKind.SCENARIO,
        scenario=None,
        feature=None,
        prompt_content="prompt body",
    )


class TestSystemPromptAndCaching:
    def test_first_call_sends_cache_control_on_rubric(self, mock_anthropic_client, good_tool_input):
        mock_anthropic_client.scripted_responses.append(good_tool_input)
        evaluator = LlmEvaluator(client=mock_anthropic_client, max_workers=1)
        evaluator.evaluate((_pkg(),))
        call = mock_anthropic_client.calls[0]
        system = call["system"]
        assert isinstance(system, list)
        rubric_block = next(b for b in system if b.get("type") == "text")
        assert rubric_block["cache_control"] == {"type": "ephemeral"}

    def test_tool_definition_cached(self, mock_anthropic_client, good_tool_input):
        mock_anthropic_client.scripted_responses.append(good_tool_input)
        evaluator = LlmEvaluator(client=mock_anthropic_client, max_workers=1)
        evaluator.evaluate((_pkg(),))
        call = mock_anthropic_client.calls[0]
        assert isinstance(call["tools"], list)
        assert call["tools"][-1].get("cache_control") == {"type": "ephemeral"}

    def test_tool_choice_forced(self, mock_anthropic_client, good_tool_input):
        mock_anthropic_client.scripted_responses.append(good_tool_input)
        evaluator = LlmEvaluator(client=mock_anthropic_client, max_workers=1)
        evaluator.evaluate((_pkg(),))
        assert mock_anthropic_client.calls[0]["tool_choice"] == {
            "type": "tool",
            "name": "ReportFindings",
        }

    def test_tool_choice_is_same_object_across_calls(self, mock_anthropic_client, good_tool_input):
        mock_anthropic_client.scripted_responses.append(good_tool_input)
        mock_anthropic_client.scripted_responses.append(good_tool_input)
        evaluator = LlmEvaluator(client=mock_anthropic_client, max_workers=1)
        evaluator.evaluate((_pkg("p:1"), _pkg("p:2")))
        assert (
            mock_anthropic_client.calls[0]["tool_choice"]
            is (mock_anthropic_client.calls[1]["tool_choice"])
        )

    def test_first_successful_call_cache_creation_tokens_asserted_nonzero(
        self, mock_anthropic_client, good_tool_input
    ):
        mock_anthropic_client.scripted_responses.append(good_tool_input)
        evaluator = LlmEvaluator(client=mock_anthropic_client, max_workers=1)
        results, skipped = evaluator.evaluate((_pkg(),))
        assert len(results) == 1
        assert results[0].cache_creation_input_tokens > 0

    def test_warm_cache_read_only_does_not_raise(self, mock_anthropic_client):
        # Second+ run: cache_creation==0 but cache_read>0 — caching IS active.
        from tests.unit.tools.dashboard.conftest import FakeMessage, FakeUsage

        warm_response = FakeMessage(
            content=[],
            usage=FakeUsage(
                input_tokens=100,
                output_tokens=200,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=800,
            ),
        )
        # Patch content to return a valid tool_use block so parse succeeds.
        from tests.unit.tools.dashboard.conftest import FakeToolUseBlock

        warm_response.content = [FakeToolUseBlock(name="ReportFindings", input={"findings": []})]
        mock_anthropic_client.scripted_responses.append(warm_response)
        evaluator = LlmEvaluator(client=mock_anthropic_client, max_workers=1)
        # Must NOT raise CacheNotActiveError when cache_read>0 and cache_creation==0.
        results, skipped = evaluator.evaluate((_pkg(),))
        assert skipped == ()
        assert results[0].succeeded is True

    def test_no_cache_tokens_at_all_raises(self, mock_anthropic_client):
        # Neither cache_creation nor cache_read → caching is broken.
        from tests.unit.tools.dashboard.conftest import FakeMessage, FakeToolUseBlock, FakeUsage

        no_cache_response = FakeMessage(
            content=[FakeToolUseBlock(name="ReportFindings", input={"findings": []})],
            usage=FakeUsage(
                input_tokens=1000,
                output_tokens=200,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
            ),
        )
        mock_anthropic_client.scripted_responses.append(no_cache_response)
        evaluator = LlmEvaluator(client=mock_anthropic_client, max_workers=1)
        with pytest.raises(CacheNotActiveError):
            evaluator.evaluate((_pkg(),))

    def test_cache_assertion_skips_failed_first_package(
        self, mock_anthropic_client, malformed_tool_input, good_tool_input
    ):
        # Package 0 fails twice (retry exhausted) → package 1 is the first
        # success → cache assertion evaluates against package 1, not 0.
        mock_anthropic_client.scripted_responses.extend(
            [malformed_tool_input, malformed_tool_input, good_tool_input]
        )
        evaluator = LlmEvaluator(client=mock_anthropic_client, max_workers=1)
        results, skipped = evaluator.evaluate((_pkg("p:0"), _pkg("p:1")))
        assert "p:0" in skipped
        # Must not raise CacheNotActiveError just because p:0 failed.
        assert any(r.succeeded for r in results)


class TestValidResponseParsing:
    def test_happy_path_yields_findings(self, mock_anthropic_client, good_tool_input):
        mock_anthropic_client.scripted_responses.append(good_tool_input)
        evaluator = LlmEvaluator(client=mock_anthropic_client, max_workers=1)
        results, skipped = evaluator.evaluate((_pkg(),))
        assert skipped == ()
        assert len(results) == 1
        assert results[0].succeeded is True
        assert len(results[0].findings) == 1
        assert results[0].findings[0].criterion_id == "D1"


class TestMalformedRetry:
    def test_malformed_triggers_retry_then_succeeds(
        self, mock_anthropic_client, good_tool_input, malformed_tool_input
    ):
        mock_anthropic_client.scripted_responses.append(malformed_tool_input)
        mock_anthropic_client.scripted_responses.append(good_tool_input)
        evaluator = LlmEvaluator(client=mock_anthropic_client, max_workers=1)
        results, skipped = evaluator.evaluate((_pkg(),))
        assert skipped == ()
        assert len(results) == 1
        assert results[0].succeeded is True
        assert len(mock_anthropic_client.calls) == 2

    def test_malformed_twice_ends_in_skipped(self, mock_anthropic_client, malformed_tool_input):
        mock_anthropic_client.scripted_responses.extend(
            [malformed_tool_input, malformed_tool_input]
        )
        evaluator = LlmEvaluator(client=mock_anthropic_client, max_workers=1)
        results, skipped = evaluator.evaluate((_pkg("p:1"),))
        assert "p:1" in skipped


class TestSdkErrorsAreSkipped:
    def test_api_exception_surfaces_as_skipped(self, mock_anthropic_client):
        mock_anthropic_client.scripted_responses.append(RuntimeError("connection reset"))
        evaluator = LlmEvaluator(client=mock_anthropic_client, max_workers=1)
        results, skipped = evaluator.evaluate((_pkg("p:err"),))
        assert "p:err" in skipped
        assert results[0].succeeded is False

    def test_all_packages_fail_returns_results_not_raises(
        self, mock_anthropic_client, malformed_tool_input
    ):
        # Every package malformed twice → every package skipped. Must NOT
        # raise CacheNotActiveError.
        for _ in range(6):  # 3 packages × (1 try + 1 retry) = 6 responses
            mock_anthropic_client.scripted_responses.append(malformed_tool_input)
        evaluator = LlmEvaluator(client=mock_anthropic_client, max_workers=1)
        packages = tuple(_pkg(f"p:{i}") for i in range(3))
        results, skipped = evaluator.evaluate(packages)
        assert set(skipped) == {"p:0", "p:1", "p:2"}
        assert all(r.succeeded is False for r in results)
        assert len(results) == 3


class TestRubricLengthGuard:
    def test_startup_fails_if_rubric_below_minimum(self, monkeypatch, mock_anthropic_client):
        monkeypatch.setattr("tools.dashboard.llm.client.rubric_token_count", lambda: 100)
        with pytest.raises(RubricTooShortError):
            LlmEvaluator(client=mock_anthropic_client)


class TestParallelOrdering:
    def test_results_preserve_input_order(self, mock_anthropic_client, good_tool_input):
        for _ in range(5):
            mock_anthropic_client.scripted_responses.append(good_tool_input)
        evaluator = LlmEvaluator(client=mock_anthropic_client, max_workers=3)
        packages = tuple(_pkg(f"p:{i}") for i in range(5))
        results, _ = evaluator.evaluate(packages)
        assert tuple(r.package_id for r in results) == tuple(p.id for p in packages)
