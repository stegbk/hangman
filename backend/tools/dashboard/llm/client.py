"""LlmEvaluator: wraps anthropic SDK, evaluates Packages in parallel.

- System prompt carries the cached rubric (cache_control: ephemeral).
- Tool definition is ALSO cached (cache prefix: tools → system → messages).
- _TOOL_CHOICE is a module-level constant — same object, every call.
- 1 retry on MalformedReportError.
- On SDK exception: record failure, add to skipped.
- Cache-creation assertion runs on the first SUCCESSFUL call (not the
  first package). Failed first packages loop forward until one succeeds.
  If ALL packages fail before any success, return (results, skipped) — caching
  may be fine; we just have zero successful responses to witness it.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from tools.dashboard.llm.rubric import RUBRIC_TEXT, rubric_token_count
from tools.dashboard.llm.tool_schema import (
    REPORT_FINDINGS_TOOL,
    MalformedReportError,
    parse_tool_input,
)
from tools.dashboard.models import (
    Finding,
    LlmCallResult,
    Package,
    Severity,
)

_LOG = logging.getLogger(__name__)

# Conservative floor. Anthropic's minimum cacheable prompt varies by model
# per prompt-caching docs (often 1024 on newer models, but 4096 on
# older ones).  4096 gives margin.
# Re-exported so __main__.py can check it without duplicating the literal.
_RUBRIC_CACHE_MIN_TOKENS = 4096

_RECOGNIZED_CRITERIA: frozenset[str] = frozenset(
    [f"D{i}" for i in range(1, 7)] + [f"H{i}" for i in range(1, 8)]
)
_MAX_OUTPUT_TOKENS = 2048

# Cap the serial warm-up that validates cache activation. If two packages
# fail back-to-back, fall through to the parallel pool rather than
# serializing all N packages through retries — a broken API would otherwise
# block evaluate() for N × per-call timeout.
_MAX_WARMUP = 2

# Module-level constants for cache-prefix stability. MUST be the same
# object on every messages.create call — don't rebuild per-call.
_CACHED_TOOL: dict[str, Any] = {**REPORT_FINDINGS_TOOL, "cache_control": {"type": "ephemeral"}}
_TOOLS: list[dict[str, Any]] = [_CACHED_TOOL]
_TOOL_CHOICE: dict[str, Any] = {"type": "tool", "name": "ReportFindings"}
_SYSTEM: list[dict[str, Any]] = [
    {
        "type": "text",
        "text": RUBRIC_TEXT,
        "cache_control": {"type": "ephemeral"},
    }
]


class RubricTooShortError(RuntimeError):
    pass


class CacheNotActiveError(RuntimeError):
    """First SUCCESSFUL call didn't report cache_creation_input_tokens."""


class LlmEvaluator:
    def __init__(
        self,
        client: Any | None = None,
        model: str = "claude-sonnet-4-6",
        max_workers: int = 6,
        max_retries_per_call: int = 1,
    ) -> None:
        token_count = rubric_token_count()
        if token_count < _RUBRIC_CACHE_MIN_TOKENS:
            raise RubricTooShortError(
                f"Rubric is {token_count} tokens — below "
                f"{_RUBRIC_CACHE_MIN_TOKENS}-token cache floor."
            )
        if client is None:
            from anthropic import Anthropic

            self._client: Any = Anthropic()
        else:
            self._client = client
        self._model = model
        self._max_workers = max_workers
        self._max_retries = max_retries_per_call

    def evaluate(
        self, packages: tuple[Package, ...]
    ) -> tuple[tuple[LlmCallResult, ...], tuple[str, ...]]:
        if not packages:
            return (), ()

        # Warm-up: try up to _MAX_WARMUP packages serially. As soon as one
        # succeeds, validate cache activation against it and fall through to
        # the parallel pool for the remainder. If the warm-up exhausts
        # without a success, fall through anyway — the remainder runs in
        # parallel and we accept that we have no opportunity to catch a
        # broken cache before fanout. This caps the worst case at
        # _MAX_WARMUP × per-call timeout instead of N × per-call timeout
        # when every package fails.
        sequential_results: list[LlmCallResult] = []
        last_sequential_idx = -1
        warmup_limit = min(_MAX_WARMUP, len(packages))
        for idx in range(warmup_limit):
            result = self._call(packages[idx])
            sequential_results.append(result)
            last_sequential_idx = idx
            if result.succeeded:
                # Caching is active if the call either WROTE the cache
                # (cache_creation_input_tokens > 0) or READ from it
                # (cache_read_input_tokens > 0).  A warm cache hits the read
                # branch; a cold cache hits the write branch.
                cache_active = (
                    result.cache_creation_input_tokens > 0 or result.cache_read_input_tokens > 0
                )
                if not cache_active:
                    raise CacheNotActiveError(
                        f"First successful LLM call (package {packages[idx].id}) "
                        f"returned both cache_creation_input_tokens == 0 and "
                        f"cache_read_input_tokens == 0 — prompt caching is "
                        f"not active. Check rubric length and cache_control "
                        f"placement on system AND tools."
                    )
                break

        remainder = packages[last_sequential_idx + 1 :]

        if remainder:
            with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
                results_rest = list(pool.map(self._call, remainder))
        else:
            results_rest = []

        all_results = tuple(sequential_results + results_rest)
        skipped = tuple(r.package_id for r in all_results if not r.succeeded)
        return all_results, skipped

    def _call(self, pkg: Package) -> LlmCallResult:
        t0 = time.monotonic()
        attempts = self._max_retries + 1
        last_error: str | None = None
        for attempt in range(attempts):
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=_MAX_OUTPUT_TOKENS,
                    system=_SYSTEM,
                    tools=_TOOLS,
                    tool_choice=_TOOL_CHOICE,
                    messages=[
                        {"role": "user", "content": pkg.prompt_content},
                    ],
                )
            except Exception as exc:  # noqa: BLE001 — SDK exception taxonomy is broad
                last_error = f"{type(exc).__name__}: {exc}"
                _LOG.warning("LLM call failed for %s: %s", pkg.id, last_error)
                break

            tool_input = self._extract_tool_input(response)
            try:
                payload = parse_tool_input(tool_input)
            except MalformedReportError as exc:
                last_error = f"MalformedReportError: {exc}"
                _LOG.warning(
                    "Malformed tool payload on attempt %d for %s: %s",
                    attempt + 1,
                    pkg.id,
                    last_error,
                )
                if attempt < attempts - 1:
                    continue
                break

            findings = tuple(self._to_finding(item, pkg) for item in payload.findings)
            elapsed = int((time.monotonic() - t0) * 1000)
            usage = response.usage
            return LlmCallResult(
                package_id=pkg.id,
                model=response.model,
                input_tokens=usage.input_tokens,
                cache_read_input_tokens=usage.cache_read_input_tokens or 0,
                cache_creation_input_tokens=usage.cache_creation_input_tokens or 0,
                output_tokens=usage.output_tokens,
                wall_clock_ms=elapsed,
                succeeded=True,
                error_message=None,
                findings=findings,
            )

        elapsed = int((time.monotonic() - t0) * 1000)
        return LlmCallResult(
            package_id=pkg.id,
            model=self._model,
            input_tokens=0,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
            output_tokens=0,
            wall_clock_ms=elapsed,
            succeeded=False,
            error_message=last_error,
            findings=(),
        )

    def _extract_tool_input(self, response: Any) -> Any:
        for block in response.content:
            if (
                getattr(block, "type", None) == "tool_use"
                and getattr(block, "name", None) == "ReportFindings"
            ):
                return block.input
        raise MalformedReportError("Response contained no ReportFindings tool_use block")

    def _to_finding(self, item: Any, pkg: Package) -> Finding:
        return Finding(
            criterion_id=item.criterion_id,
            severity=Severity(item.severity),
            scenario=pkg.scenario,
            feature=pkg.feature,
            problem=item.problem,
            evidence=item.evidence,
            reason=item.reason,
            fix_example=item.fix_example,
            is_recognized_criterion=item.criterion_id in _RECOGNIZED_CRITERIA,
        )
