"""Tests for NdjsonParser."""

import json
from pathlib import Path

import pytest
from tools.dashboard.models import Outcome, ParseResult
from tools.dashboard.parser import NdjsonParser


class TestParseMinimal:
    def test_returns_parse_result(self, minimal_ndjson_path: Path) -> None:
        parser = NdjsonParser()
        result = parser.parse(minimal_ndjson_path)
        assert isinstance(result, ParseResult)

    def test_extracts_one_feature(self, minimal_ndjson_path: Path) -> None:
        parser = NdjsonParser()
        result = parser.parse(minimal_ndjson_path)
        assert len(result.features) == 1
        assert result.features[0].name == "Minimal"
        assert result.features[0].file == "features/minimal.feature"

    def test_extracts_one_scenario(self, minimal_ndjson_path: Path) -> None:
        parser = NdjsonParser()
        result = parser.parse(minimal_ndjson_path)
        assert len(result.scenarios) == 1
        sc = result.scenarios[0]
        assert sc.name == "trivial pass"
        assert sc.feature_file == "features/minimal.feature"
        assert sc.feature_name == "Minimal"

    def test_scenario_tags_populated(self, minimal_ndjson_path: Path) -> None:
        parser = NdjsonParser()
        result = parser.parse(minimal_ndjson_path)
        assert result.scenarios[0].tags == ("@happy", "@smoke")

    def test_scenario_primary_tag(self, minimal_ndjson_path: Path) -> None:
        parser = NdjsonParser()
        sc = parser.parse(minimal_ndjson_path).scenarios[0]
        assert sc.primary_tag == "@happy"
        assert sc.is_smoke is True

    def test_scenario_outcome_passed(self, minimal_ndjson_path: Path) -> None:
        parser = NdjsonParser()
        sc = parser.parse(minimal_ndjson_path).scenarios[0]
        assert sc.outcome == Outcome.PASSED

    def test_steps_preserved_in_order(self, minimal_ndjson_path: Path) -> None:
        parser = NdjsonParser()
        sc = parser.parse(minimal_ndjson_path).scenarios[0]
        assert [s.text for s in sc.steps] == ["a setup", "an action", "a result"]
        assert [s.keyword.strip() for s in sc.steps] == ["Given", "When", "Then"]

    def test_timestamp_iso_format(self, minimal_ndjson_path: Path) -> None:
        parser = NdjsonParser()
        result = parser.parse(minimal_ndjson_path)
        # derived from testRunStarted.timestamp.seconds = 1714000000
        assert result.timestamp.startswith("2024-04-24T")
        assert result.timestamp.endswith("Z")

    def test_uris_populated(self, minimal_ndjson_path: Path) -> None:
        parser = NdjsonParser()
        result = parser.parse(minimal_ndjson_path)
        assert "features/minimal.feature" in result.gherkin_document_uris


class TestParseMultiScenario:
    def test_extracts_two_features(self, multi_ndjson_path: Path) -> None:
        result = NdjsonParser().parse(multi_ndjson_path)
        assert len(result.features) == 2

    def test_extracts_four_scenarios(self, multi_ndjson_path: Path) -> None:
        result = NdjsonParser().parse(multi_ndjson_path)
        assert len(result.scenarios) == 4

    def test_failed_step_rolls_up_to_failed_scenario(self, multi_ndjson_path: Path) -> None:
        result = NdjsonParser().parse(multi_ndjson_path)
        failed = [s for s in result.scenarios if s.outcome == Outcome.FAILED]
        assert len(failed) >= 1

    def test_scenario_without_primary_tag_returns_none(self, multi_ndjson_path: Path) -> None:
        result = NdjsonParser().parse(multi_ndjson_path)
        no_primary = [s for s in result.scenarios if s.primary_tag is None]
        assert len(no_primary) >= 1


class TestOutcomeRollup:
    @pytest.mark.parametrize(
        "step_statuses,expected",
        [
            (["PASSED", "PASSED", "PASSED"], Outcome.PASSED),
            (["PASSED", "FAILED", "PASSED"], Outcome.FAILED),
            (["PASSED", "SKIPPED", "PASSED"], Outcome.SKIPPED),
            (["PASSED", "PENDING"], Outcome.FAILED),
            (["PASSED", "AMBIGUOUS"], Outcome.FAILED),
            (["PASSED", "UNDEFINED"], Outcome.FAILED),
            (["UNKNOWN"], Outcome.UNKNOWN),
            ([], Outcome.NOT_RUN),
        ],
    )
    def test_rollup_matrix(self, step_statuses: list[str], expected: Outcome) -> None:
        from tools.dashboard.parser import _rollup_outcome

        assert _rollup_outcome(step_statuses) == expected


class TestProtocolVersionGuard:
    def test_wrong_major_version_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.ndjson"
        bad.write_text(
            json.dumps(
                {
                    "meta": {
                        "protocolVersion": "99.0.0",
                        "implementation": {"name": "x", "version": "1"},
                    }
                }
            )
            + "\n"
        )
        with pytest.raises(ValueError, match="protocolVersion"):
            NdjsonParser().parse(bad)
