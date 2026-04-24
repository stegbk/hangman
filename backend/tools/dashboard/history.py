"""HistoryStore: append + read_all RunSummary entries under .bdd-history/."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from tools.dashboard.models import CostReport, RunSummary, Severity

_LOG = logging.getLogger(__name__)


class HistoryStore:
    def append(self, summary: RunSummary, history_dir: Path) -> None:
        history_dir.mkdir(parents=True, exist_ok=True)
        slug = summary.timestamp.replace(":", "-")
        path = history_dir / f"{slug}.json"
        if path.exists():
            path = history_dir / f"{slug}-{uuid.uuid4().hex[:8]}.json"
        path.write_text(json.dumps(self._to_dict(summary), indent=2))

    def read_all(self, history_dir: Path) -> list[RunSummary]:
        if not history_dir.is_dir():
            return []
        entries: list[RunSummary] = []
        for path in history_dir.glob("*.json"):
            try:
                entries.append(self._from_dict(json.loads(path.read_text())))
            except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
                _LOG.warning("Skipping corrupt history entry %s: %s", path, exc)
        entries.sort(key=lambda s: s.timestamp)
        return entries

    def _to_dict(self, s: RunSummary) -> dict[str, object]:
        return {
            "timestamp": s.timestamp,
            "total_scenarios": s.total_scenarios,
            "passed": s.passed,
            "failed": s.failed,
            "skipped": s.skipped,
            "finding_counts": {sev.value: n for sev, n in s.finding_counts.items()},
            "model": s.model,
            "cost": {
                "model": s.cost.model,
                "total_input_tokens": s.cost.total_input_tokens,
                "total_cache_read_tokens": s.cost.total_cache_read_tokens,
                "total_cache_creation_tokens": s.cost.total_cache_creation_tokens,
                "total_output_tokens": s.cost.total_output_tokens,
                "total_usd": s.cost.total_usd,
                "cache_hit_rate": s.cost.cache_hit_rate,
            },
            "skipped_packages": list(s.skipped_packages),
        }

    def _from_dict(self, d: dict[str, Any]) -> RunSummary:
        return RunSummary(
            timestamp=d["timestamp"],
            total_scenarios=int(d["total_scenarios"]),
            passed=int(d["passed"]),
            failed=int(d["failed"]),
            skipped=int(d["skipped"]),
            finding_counts={Severity(k): int(v) for k, v in d["finding_counts"].items()},
            model=d["model"],
            cost=CostReport(
                model=d["cost"]["model"],
                total_input_tokens=int(d["cost"]["total_input_tokens"]),
                total_cache_read_tokens=int(d["cost"]["total_cache_read_tokens"]),
                total_cache_creation_tokens=int(d["cost"]["total_cache_creation_tokens"]),
                total_output_tokens=int(d["cost"]["total_output_tokens"]),
                total_usd=float(d["cost"]["total_usd"]),
                cache_hit_rate=float(d["cost"]["cache_hit_rate"]),
            ),
            skipped_packages=tuple(d.get("skipped_packages", [])),
        )
