"""Pricing table + CostReport rollup for LLM calls."""

from __future__ import annotations

from tools.dashboard.models import CostReport, LlmCallResult

PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
    "claude-haiku-4-5": {"input": 1.0 / 1_000_000, "output": 5.0 / 1_000_000},
    "claude-opus-4-7": {"input": 5.0 / 1_000_000, "output": 25.0 / 1_000_000},
}

CACHE_WRITE_MULT = 1.25
CACHE_READ_MULT = 0.1


def compute_cost(results: list[LlmCallResult]) -> CostReport:
    succeeded = [r for r in results if r.succeeded]
    if not succeeded:
        return CostReport(
            model=results[0].model if results else "",
            total_input_tokens=0,
            total_cache_read_tokens=0,
            total_cache_creation_tokens=0,
            total_output_tokens=0,
            total_usd=0.0,
            cache_hit_rate=0.0,
        )

    model = succeeded[0].model
    # Anthropic returns disambiguated model names in responses (e.g.
    # 'claude-sonnet-4-6-20250101'). Match via prefix; default to sonnet
    # rates if none match — keeps a live run from blowing up over a model
    # rename rather than a real pricing problem.
    rates = next(
        (r for prefix, r in PRICING.items() if model.startswith(prefix)),
        PRICING["claude-sonnet-4-6"],
    )

    total_input = sum(r.input_tokens for r in succeeded)
    total_read = sum(r.cache_read_input_tokens for r in succeeded)
    total_write = sum(r.cache_creation_input_tokens for r in succeeded)
    total_output = sum(r.output_tokens for r in succeeded)

    total_usd = 0.0
    for r in succeeded:
        # input_tokens from the Anthropic API is the number of *uncached* (regular)
        # input tokens processed.  cache_read and cache_creation are reported
        # separately and are NOT subtracted from input_tokens — they are additive.
        total_usd += r.input_tokens * rates["input"]
        total_usd += r.cache_creation_input_tokens * rates["input"] * CACHE_WRITE_MULT
        total_usd += r.cache_read_input_tokens * rates["input"] * CACHE_READ_MULT
        total_usd += r.output_tokens * rates["output"]

    # Denominator = all tokens sent to the model (regular + cached-read + cache-write).
    # input_tokens from the API counts only the non-cached (regular) portion.
    total_all_input = total_input + total_read + total_write
    cache_hit_rate = total_read / total_all_input if total_all_input else 0.0

    return CostReport(
        model=model,
        total_input_tokens=total_input,
        total_cache_read_tokens=total_read,
        total_cache_creation_tokens=total_write,
        total_output_tokens=total_output,
        total_usd=total_usd,
        cache_hit_rate=cache_hit_rate,
    )
