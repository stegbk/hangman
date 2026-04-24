"""Tests for CoverageGrader."""

from tools.dashboard.coverage import CoverageGrader
from tools.dashboard.models import CoverageState

from tests.fixtures.dashboard.coverage_fixtures import (
    full_coverage_feature,
    no_coverage_feature,
    partial_coverage_feature,
)


class TestEndpointScraping:
    def test_get_endpoint_extracted_from_step_text(self) -> None:
        grader = CoverageGrader()
        features = (partial_coverage_feature(),)
        endpoint_index, _, _ = grader.grade(features)
        assert "GET /games/{id}" in endpoint_index

    def test_post_endpoint_extracted(self) -> None:
        grader = CoverageGrader()
        features = (full_coverage_feature(),)
        endpoint_index, _, _ = grader.grade(features)
        assert "POST /guesses" in endpoint_index

    def test_numeric_id_normalized_to_placeholder(self) -> None:
        from tools.dashboard.models import Feature, Outcome, Scenario, Step

        sc = Scenario(
            feature_file="f.feature",
            feature_name="F",
            name="x",
            line=1,
            tags=("@happy",),
            steps=(Step(keyword="Given ", text="I GET /games/12345", outcome=Outcome.PASSED),),
            outcome=Outcome.PASSED,
        )
        feat = Feature(file="f.feature", name="F", scenarios=(sc,), line=1)
        endpoint_index, _, _ = CoverageGrader().grade((feat,))
        assert "GET /games/{id}" in endpoint_index


class TestUcScraping:
    def test_uc_number_extracted_from_feature_name(self) -> None:
        grader = CoverageGrader()
        features = (full_coverage_feature(),)
        _, uc_index, _ = grader.grade(features)
        assert "UC1" in uc_index

    def test_feature_without_uc_label_skipped(self) -> None:
        from tools.dashboard.models import Feature

        plain = Feature(file="x.feature", name="Smoke", scenarios=(), line=1)
        _, uc_index, _ = CoverageGrader().grade((plain,))
        assert uc_index == {}


class TestGrading:
    def test_happy_plus_failure_plus_edge_is_full(self) -> None:
        grades = CoverageGrader().grade((full_coverage_feature(),))[2]
        uc1 = next(g for g in grades if g.subject == "UC1" and g.kind == "uc")
        assert uc1.state == CoverageState.FULL
        assert uc1.missing_tags == ()

    def test_only_happy_is_partial(self) -> None:
        grades = CoverageGrader().grade((partial_coverage_feature(),))[2]
        uc2 = next(g for g in grades if g.subject == "UC2" and g.kind == "uc")
        assert uc2.state == CoverageState.PARTIAL
        assert set(uc2.missing_tags) == {"@failure", "@edge"}

    def test_no_primary_tag_is_none(self) -> None:
        grades = CoverageGrader().grade((no_coverage_feature(),))[2]
        uc3 = next((g for g in grades if g.subject == "UC3" and g.kind == "uc"), None)
        assert uc3 is not None
        assert uc3.state == CoverageState.NONE
