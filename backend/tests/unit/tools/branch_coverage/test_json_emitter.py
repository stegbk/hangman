"""Tests for JsonEmitter."""

from __future__ import annotations

import json
from pathlib import Path

from tools.branch_coverage.json_emitter import JsonEmitter
from tools.branch_coverage.models import (
    AuditReport,
    CoveragePerEndpoint,
    CoverageReport,
    Endpoint,
    FunctionCoverage,
    ReachableBranch,
    Tone,
    Totals,
)


def _fixture_report() -> CoverageReport:
    """Deterministic CoverageReport used for golden-file comparison.

    Per plan-review iter 5 P2 (Claude): file paths use the canonical
    runtime format `src/hangman/<module>.py` — matching what coverage.py
    with `relative_files = true` produces and what Reachability emits
    via `source_file.relative_to(source_root.parent.parent)`. The
    `backend/` prefix is NEVER part of the canonical format and is
    fail-fast rejected by H1 Step 7b. The golden_coverage.json baked
    from this fixture is the worked example future maintainers will
    copy when adding new endpoints — it must show the right shape.

    Per plan-review iter 11 P1 (Codex): all symbol names are grounded
    in real Hangman files:
    - `hangman.routes.start_game` is the real handler for `POST
      /api/v1/games` (`backend/src/hangman/routes.py:127`).
    - `hangman.words.WordPool.random_word` is reachable from
      start_game via the word-pick flow
      (`backend/src/hangman/words.py:22-25`); its `if category not in
      self.categories` raise-KeyError branch is the real uncovered
      example. NOT `hangman.game.new_game` (no such function) and
      NOT `self._by_category` (the real attribute is
      `self.categories`).
    """
    ep = Endpoint(method="POST", path="/api/v1/games", handler_qualname="hangman.routes.start_game")
    branch = ReachableBranch(
        file="src/hangman/words.py",
        line=23,
        branch_id="23->24",
        condition_text="if category not in self.categories:",
        not_taken_to_line=24,
        function_qualname="hangman.words.WordPool.random_word",
    )
    fc = FunctionCoverage(
        file="src/hangman/words.py",
        qualname="hangman.words.WordPool.random_word",
        total_branches=1,
        covered_branches=0,
        pct=0.0,
        reached=False,
        uncovered_branches=(branch,),
    )
    ep_cov = CoveragePerEndpoint(
        endpoint=ep,
        reachable_functions=(fc,),
        total_branches=1,
        covered_branches=0,
        pct=0.0,
        tone=Tone.ERROR,
    )
    audit = AuditReport(
        total_branches_per_coverage_py=1,
        total_branches_enumerated_via_reachability=1,
        extra_coverage_branches=0,
        unattributed_branches=(),
        reconciled=True,
    )
    return CoverageReport(
        version=1,
        timestamp="2026-04-24T20:00:00Z",
        cucumber_ndjson="frontend/test-results/cucumber.coverage.ndjson",
        instrumented=True,
        thresholds={"red": 50.0, "yellow": 80.0},
        totals=Totals(total_branches=1, covered_branches=0, pct=0.0, tone=Tone.ERROR),
        endpoints=(ep_cov,),
        extra_coverage=(),
        audit=audit,
    )


class TestEmit:
    def test_writes_json_file(self, tmp_path: Path) -> None:
        out = tmp_path / "coverage.json"
        JsonEmitter().emit(_fixture_report(), out)
        assert out.exists()
        parsed = json.loads(out.read_text())
        assert parsed["version"] == 1

    def test_tone_enum_serializes_as_string(self, tmp_path: Path) -> None:
        out = tmp_path / "coverage.json"
        JsonEmitter().emit(_fixture_report(), out)
        parsed = json.loads(out.read_text())
        assert parsed["totals"]["tone"] == "error"

    def test_uncovered_branches_flat_derives_from_functions(self, tmp_path: Path) -> None:
        out = tmp_path / "coverage.json"
        JsonEmitter().emit(_fixture_report(), out)
        parsed = json.loads(out.read_text())
        ep = parsed["endpoints"][0]
        assert "uncovered_branches_flat" in ep
        assert len(ep["uncovered_branches_flat"]) == 1
        assert (
            ep["uncovered_branches_flat"][0]["function_qualname"]
            == "hangman.words.WordPool.random_word"
        )


class TestGoldenFile:
    def test_matches_golden(self, tmp_path: Path, fixtures_dir: Path) -> None:
        """Deterministic inputs → byte-identical JSON.

        To regenerate: run this test, copy tmp file content to
        fixtures/branch_coverage/golden_coverage.json.
        """
        out = tmp_path / "coverage.json"
        JsonEmitter().emit(_fixture_report(), out)
        golden = (fixtures_dir / "golden_coverage.json").read_text()
        assert out.read_text() == golden
