"""ReportFindings tool JSON schema + Pydantic validators.

The LLM is forced to call this tool (tool_choice={"type": "tool",
"name": "ReportFindings"}). Valid tool_use content blocks parse via
parse_tool_input; malformed blocks raise MalformedReportError, which
LlmEvaluator catches to trigger one retry.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ValidationError

REPORT_FINDINGS_TOOL: dict[str, Any] = {
    "name": "ReportFindings",
    "description": (
        "Report quality findings for the BDD scenario or feature. "
        "Emit one entry per issue; emit an empty list if the input "
        "is clean."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "criterion_id": {
                            "type": "string",
                            "description": (
                                "D1-D6 / H1-H7 from the rubric, or a NEW "
                                "ID if you observe an issue not in the "
                                "rubric."
                            ),
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["P0", "P1", "P2", "P3"],
                        },
                        "problem": {"type": "string"},
                        "evidence": {"type": "string"},
                        "reason": {"type": "string"},
                        "fix_example": {"type": "string"},
                    },
                    "required": [
                        "criterion_id",
                        "severity",
                        "problem",
                        "evidence",
                        "reason",
                        "fix_example",
                    ],
                },
            }
        },
        "required": ["findings"],
    },
}


class FindingPayload(BaseModel):
    criterion_id: str
    severity: Literal["P0", "P1", "P2", "P3"]
    problem: str
    evidence: str
    reason: str
    fix_example: str


class ReportFindingsPayload(BaseModel):
    findings: list[FindingPayload]


class MalformedReportError(ValueError):
    """Raised when the LLM's tool_use payload fails Pydantic validation."""


def parse_tool_input(data: Any) -> ReportFindingsPayload:
    if not isinstance(data, dict):
        raise MalformedReportError(
            f"Expected dict for ReportFindings input, got {type(data).__name__}"
        )
    try:
        return ReportFindingsPayload.model_validate(data)
    except ValidationError as exc:
        raise MalformedReportError(str(exc)) from exc
