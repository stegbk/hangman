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
        if rubric_token_count() < _RUBRIC_CACHE_MIN_TOKENS:
            raise RubricTooShortError(
                f"Rubric is {rubric_token_count()} tokens — below "
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

        # Loop serially through packages until one succeeds. This lets us
        # assert cache activation against a KNOWN-good call, not whichever
        # package happens to be first in the list.
        #
        # Invariant after this loop:
        #   sequential_results == [self._call(p) for p in packages[: last_sequential_idx + 1]]
        #   We break on the first success after asserting cache tokens > 0.
        #   If no package succeeds, last_sequential_idx == len(packages) - 1
        #   and remainder is empty — no CacheNotActiveError is raised because
        #   we have zero successful responses to witness caching against.
        sequential_results: list[LlmCallResult] = []
        last_sequential_idx = -1
        for idx, pkg in enumerate(packages):
            result = self._call(pkg)
            sequential_results.append(result)
            last_sequential_idx = idx
            if result.succeeded:
                if result.cache_creation_input_tokens == 0:
                    raise CacheNotActiveError(
                        f"First successful LLM call (package {pkg.id}) "
                        f"returned cache_creation_input_tokens == 0 — "
                        f"prompt caching is not active. Check rubric length "
                        f"and cache_control placement on system AND tools."
                    )
                break

        # If every package failed, remainder is empty and we skip the pool.
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
