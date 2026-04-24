"""Tests for ReportFindings tool schema + Pydantic validators."""

import pytest
from tools.dashboard.llm.tool_schema import (
    REPORT_FINDINGS_TOOL,
    MalformedReportError,
    ReportFindingsPayload,
    parse_tool_input,
)


class TestToolSchemaShape:
    def test_tool_has_name(self) -> None:
        assert REPORT_FINDINGS_TOOL["name"] == "ReportFindings"

    def test_tool_has_input_schema(self) -> None:
        schema = REPORT_FINDINGS_TOOL["input_schema"]
        assert schema["type"] == "object"
        assert "findings" in schema["properties"]
        assert schema["required"] == ["findings"]

    def test_finding_item_has_required_fields(self) -> None:
        item = REPORT_FINDINGS_TOOL["input_schema"]["properties"]["findings"]["items"]
        required = set(item["required"])
        assert required == {
            "criterion_id",
            "severity",
            "problem",
            "evidence",
            "reason",
            "fix_example",
        }

    def test_severity_enum_constrained(self) -> None:
        item = REPORT_FINDINGS_TOOL["input_schema"]["properties"]["findings"]["items"]
        assert item["properties"]["severity"]["enum"] == ["P0", "P1", "P2", "P3"]


class TestValidation:
    def test_valid_payload_parses(self) -> None:
        data = {
            "findings": [
                {
                    "criterion_id": "D1",
                    "severity": "P2",
                    "problem": "Trivial pass",
                    "evidence": "Then the response status is 200",
                    "reason": "No body check",
                    "fix_example": "And the body has lives_remaining == 6",
                }
            ]
        }
        payload = parse_tool_input(data)
        assert isinstance(payload, ReportFindingsPayload)
        assert len(payload.findings) == 1
        assert payload.findings[0].criterion_id == "D1"

    def test_empty_findings_is_valid(self) -> None:
        payload = parse_tool_input({"findings": []})
        assert payload.findings == []

    def test_missing_required_field_raises(self) -> None:
        bad = {
            "findings": [
                {
                    "criterion_id": "D1",
                    "severity": "P2",
                    # missing problem, evidence, reason, fix_example
                }
            ]
        }
        with pytest.raises(MalformedReportError):
            parse_tool_input(bad)

    def test_invalid_severity_raises(self) -> None:
        bad = {
            "findings": [
                {
                    "criterion_id": "D1",
                    "severity": "P99",
                    "problem": "x",
                    "evidence": "x",
                    "reason": "x",
                    "fix_example": "x",
                }
            ]
        }
        with pytest.raises(MalformedReportError):
            parse_tool_input(bad)

    def test_non_dict_raises(self) -> None:
        with pytest.raises(MalformedReportError):
            parse_tool_input("not a dict")  # type: ignore[arg-type]

    def test_findings_not_a_list_raises(self) -> None:
        with pytest.raises(MalformedReportError):
            parse_tool_input({"findings": "not a list"})
