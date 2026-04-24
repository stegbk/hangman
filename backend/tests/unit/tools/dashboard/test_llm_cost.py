"""Tests for llm/cost.py."""

import pytest
from tools.dashboard.llm.cost import (
    CACHE_READ_MULT,
    CACHE_WRITE_MULT,
    PRICING,
    compute_cost,
)
from tools.dashboard.models import CostReport, LlmCallResult


def _result(
    *,
    input_tokens: int = 0,
    cache_read: int = 0,
    cache_write: int = 0,
    output: int = 0,
    model: str = "claude-sonnet-4-6",
    succeeded: bool = True,
) -> LlmCallResult:
    return LlmCallResult(
        package_id="pkg:test",
        model=model,
        input_tokens=input_tokens,
        cache_read_input_tokens=cache_read,
        cache_creation_input_tokens=cache_write,
        output_tokens=output,
        wall_clock_ms=100,
        succeeded=succeeded,
        error_message=None,
        findings=(),
    )


class TestPricingTable:
    def test_all_supported_models_priced(self) -> None:
        for model in ("claude-sonnet-4-6", "claude-haiku-4-5", "claude-opus-4-7"):
            assert model in PRICING
            assert "input" in PRICING[model]
            assert "output" in PRICING[model]


class TestComputeCost:
    def test_single_call_no_cache(self) -> None:
        result = _result(input_tokens=1000, output=500)
        report = compute_cost([result])
        input_rate = PRICING["claude-sonnet-4-6"]["input"]
        output_rate = PRICING["claude-sonnet-4-6"]["output"]
        expected = 1000 * input_rate + 500 * output_rate
        assert report.total_usd == pytest.approx(expected, rel=1e-6)

    def test_cache_write_charged_at_125x(self) -> None:
        # Anthropic API: input_tokens = uncached regular tokens.
        # When the entire prompt is newly cached, input_tokens=0 and
        # cache_creation_input_tokens=1000.
        result = _result(input_tokens=0, cache_write=1000, output=0)
        report = compute_cost([result])
        input_rate = PRICING["claude-sonnet-4-6"]["input"]
        expected = 1000 * input_rate * CACHE_WRITE_MULT
        assert report.total_usd == pytest.approx(expected, rel=1e-6)

    def test_cache_read_charged_at_0_1x(self) -> None:
        # Anthropic API: input_tokens = uncached regular tokens.
        # When the entire prompt is served from cache, input_tokens=0 and
        # cache_read_input_tokens=1000.
        result = _result(input_tokens=0, cache_read=1000, output=0)
        report = compute_cost([result])
        input_rate = PRICING["claude-sonnet-4-6"]["input"]
        expected = 1000 * input_rate * CACHE_READ_MULT
        assert report.total_usd == pytest.approx(expected, rel=1e-6)

    def test_cache_hit_rate_computed(self) -> None:
        # cache_hit_rate = total_read / (regular + read + write)
        # a: input=100 (uncached regular), cache_read=900, cache_write=100
        # b: input=200, cache_read=800, cache_write=200
        # total_read = 1700, total_all = (100+200) + (900+800) + (100+200) = 2300
        a = _result(input_tokens=100, cache_read=900, cache_write=100)
        b = _result(input_tokens=200, cache_read=800, cache_write=200)
        report = compute_cost([a, b])
        total_read = 900 + 800
        total_all = (100 + 200) + (900 + 800) + (100 + 200)
        assert report.cache_hit_rate == pytest.approx(total_read / total_all)

    def test_aggregates_tokens_across_calls(self) -> None:
        calls = [_result(input_tokens=1000, output=500) for _ in range(10)]
        report = compute_cost(calls)
        assert report.total_input_tokens == 10000
        assert report.total_output_tokens == 5000

    def test_failed_calls_excluded(self) -> None:
        good = _result(input_tokens=1000, output=500, succeeded=True)
        bad = _result(input_tokens=5000, output=2000, succeeded=False)
        report = compute_cost([good, bad])
        assert report.total_input_tokens == 1000

    def test_empty_list_zero_cost(self) -> None:
        report = compute_cost([])
        assert isinstance(report, CostReport)
        assert report.total_usd == 0.0
        assert report.cache_hit_rate == 0.0

    def test_mixed_models_uses_first_model_name(self) -> None:
        # In practice LlmEvaluator uses one model per run; if mixed, we
        # record the first model seen (documented behaviour).
        calls = [
            _result(input_tokens=100, output=50, model="claude-sonnet-4-6"),
            _result(input_tokens=100, output=50, model="claude-haiku-4-5"),
        ]
        report = compute_cost(calls)
        assert report.model == "claude-sonnet-4-6"
