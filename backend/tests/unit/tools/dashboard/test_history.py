"""Tests for HistoryStore."""

import json
from pathlib import Path

from tools.dashboard.history import HistoryStore
from tools.dashboard.models import CostReport, RunSummary, Severity


def _summary(timestamp: str = "2026-04-24T12:00:00Z") -> RunSummary:
    return RunSummary(
        timestamp=timestamp,
        total_scenarios=33,
        passed=30,
        failed=3,
        skipped=0,
        finding_counts={
            Severity.P0: 0,
            Severity.P1: 1,
            Severity.P2: 2,
            Severity.P3: 5,
        },
        model="claude-sonnet-4-6",
        cost=CostReport(
            model="claude-sonnet-4-6",
            total_input_tokens=160000,
            total_cache_read_tokens=140000,
            total_cache_creation_tokens=5000,
            total_output_tokens=48000,
            total_usd=1.07,
            cache_hit_rate=0.875,
        ),
        skipped_packages=(),
    )


class TestAppendAndRead:
    def test_append_creates_dir(self, tmp_path: Path) -> None:
        store = HistoryStore()
        hist_dir = tmp_path / "bdd-history"
        store.append(_summary(), hist_dir)
        assert hist_dir.is_dir()

    def test_append_writes_json_file(self, tmp_path: Path) -> None:
        store = HistoryStore()
        store.append(_summary(), tmp_path)
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1

    def test_roundtrip_preserves_fields(self, tmp_path: Path) -> None:
        store = HistoryStore()
        s1 = _summary("2026-04-24T12:00:00Z")
        store.append(s1, tmp_path)
        entries = store.read_all(tmp_path)
        assert len(entries) == 1
        got = entries[0]
        assert got.timestamp == s1.timestamp
        assert got.total_scenarios == s1.total_scenarios
        assert got.finding_counts[Severity.P2] == 2
        assert got.cost.total_usd == 1.07
        assert got.model == "claude-sonnet-4-6"

    def test_read_all_sorts_by_timestamp(self, tmp_path: Path) -> None:
        store = HistoryStore()
        store.append(_summary("2026-04-24T14:00:00Z"), tmp_path)
        store.append(_summary("2026-04-24T12:00:00Z"), tmp_path)
        store.append(_summary("2026-04-24T13:00:00Z"), tmp_path)
        entries = store.read_all(tmp_path)
        assert [e.timestamp for e in entries] == [
            "2026-04-24T12:00:00Z",
            "2026-04-24T13:00:00Z",
            "2026-04-24T14:00:00Z",
        ]


class TestCorruptionTolerance:
    def test_missing_dir_returns_empty(self, tmp_path: Path) -> None:
        entries = HistoryStore().read_all(tmp_path / "nope")
        assert entries == []

    def test_corrupt_json_skipped_not_raised(self, tmp_path: Path) -> None:
        tmp_path.mkdir(exist_ok=True)
        (tmp_path / "bad.json").write_text("{not json")
        (tmp_path / "good.json").write_text(
            json.dumps(
                {
                    "timestamp": "2026-04-24T12:00:00Z",
                    "total_scenarios": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                    "finding_counts": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
                    "model": "claude-sonnet-4-6",
                    "cost": {
                        "model": "claude-sonnet-4-6",
                        "total_input_tokens": 0,
                        "total_cache_read_tokens": 0,
                        "total_cache_creation_tokens": 0,
                        "total_output_tokens": 0,
                        "total_usd": 0.0,
                        "cache_hit_rate": 0.0,
                    },
                    "skipped_packages": [],
                }
            )
        )
        entries = HistoryStore().read_all(tmp_path)
        assert len(entries) == 1

    def test_timestamp_collision_appends_suffix(self, tmp_path: Path) -> None:
        store = HistoryStore()
        store.append(_summary("2026-04-24T12:00:00Z"), tmp_path)
        store.append(_summary("2026-04-24T12:00:00Z"), tmp_path)
        files = sorted(tmp_path.glob("*.json"))
        assert len(files) == 2
