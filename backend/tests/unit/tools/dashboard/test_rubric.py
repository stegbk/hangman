"""Rubric length + structure gates."""

from tools.dashboard.llm.rubric import RUBRIC_TEXT, rubric_token_count


class TestRubricLength:
    def test_rubric_meets_cache_floor(self) -> None:
        # 4096 is our conservative floor. Anthropic's minimum cacheable
        # prompt is model-specific per their prompt-caching docs (often
        # lower than 4096 on smaller models). Keep this buffer to guarantee
        # caching across every model we expose via --model.
        assert rubric_token_count() >= 4096, (
            f"Rubric is {rubric_token_count()} tokens — below our "
            "4096-token cache floor. Expand the rubric before shipping."
        )

    def test_rubric_text_non_empty(self) -> None:
        assert len(RUBRIC_TEXT) > 0


class TestRubricStructure:
    def test_contains_all_13_criteria(self) -> None:
        required = [f"D{i}" for i in range(1, 7)] + [f"H{i}" for i in range(1, 8)]
        missing = [cid for cid in required if cid not in RUBRIC_TEXT]
        assert missing == [], f"Rubric missing criteria: {missing}"

    def test_mentions_report_findings_tool(self) -> None:
        assert "ReportFindings" in RUBRIC_TEXT

    def test_mentions_all_severity_levels(self) -> None:
        for level in ("P0", "P1", "P2", "P3"):
            assert level in RUBRIC_TEXT
