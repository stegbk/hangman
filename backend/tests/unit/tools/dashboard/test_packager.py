"""Tests for Packager."""

from tools.dashboard.models import PackageKind
from tools.dashboard.packager import Packager

from tests.fixtures.dashboard.coverage_fixtures import (
    full_coverage_feature,
    partial_coverage_feature,
)


class TestScenarioPackage:
    def test_one_package_per_scenario(self) -> None:
        features = (full_coverage_feature(), partial_coverage_feature())
        packages = Packager().make_packages(features)
        scenario_pkgs = [p for p in packages if p.kind == PackageKind.SCENARIO]
        assert len(scenario_pkgs) == 4  # 3 + 1

    def test_scenario_package_id_format(self) -> None:
        features = (full_coverage_feature(),)
        packages = Packager().make_packages(features)
        sc_pkg = next(p for p in packages if p.kind == PackageKind.SCENARIO)
        assert sc_pkg.id.startswith("scenario:features/uc1_play.feature:")

    def test_scenario_package_id_is_deterministic(self) -> None:
        features = (full_coverage_feature(),)
        a = Packager().make_packages(features)
        b = Packager().make_packages(features)
        assert [p.id for p in a] == [p.id for p in b]

    def test_prompt_contains_scenario_name(self) -> None:
        features = (full_coverage_feature(),)
        packages = Packager().make_packages(features)
        pkg = next(p for p in packages if p.scenario and p.scenario.name == "valid guess")
        assert "valid guess" in pkg.prompt_content

    def test_prompt_contains_tags_and_outcome(self) -> None:
        features = (full_coverage_feature(),)
        pkg = next(
            p
            for p in Packager().make_packages(features)
            if p.scenario and p.scenario.name == "valid guess"
        )
        assert "@happy" in pkg.prompt_content
        assert "passed" in pkg.prompt_content

    def test_prompt_contains_steps_with_keywords(self) -> None:
        features = (full_coverage_feature(),)
        pkg = next(
            p
            for p in Packager().make_packages(features)
            if p.scenario and p.scenario.name == "valid guess"
        )
        assert "Given" in pkg.prompt_content
        assert "I POST /guesses with 'a'" in pkg.prompt_content


class TestFeaturePackage:
    def test_one_package_per_feature(self) -> None:
        features = (full_coverage_feature(), partial_coverage_feature())
        packages = Packager().make_packages(features)
        feature_pkgs = [p for p in packages if p.kind == PackageKind.FEATURE]
        assert len(feature_pkgs) == 2

    def test_feature_package_id_format(self) -> None:
        features = (full_coverage_feature(),)
        packages = Packager().make_packages(features)
        feat_pkg = next(p for p in packages if p.kind == PackageKind.FEATURE)
        assert feat_pkg.id == "feature:features/uc1_play.feature"

    def test_feature_prompt_lists_scenario_names(self) -> None:
        features = (full_coverage_feature(),)
        feat_pkg = next(
            p for p in Packager().make_packages(features) if p.kind == PackageKind.FEATURE
        )
        assert "valid guess" in feat_pkg.prompt_content
        assert "empty letter" in feat_pkg.prompt_content
        assert "unicode letter" in feat_pkg.prompt_content

    def test_feature_prompt_includes_primary_tag_counts(self) -> None:
        features = (full_coverage_feature(),)
        feat_pkg = next(
            p for p in Packager().make_packages(features) if p.kind == PackageKind.FEATURE
        )
        # one @happy, one @failure, one @edge
        assert "@happy" in feat_pkg.prompt_content
        assert "@failure" in feat_pkg.prompt_content
        assert "@edge" in feat_pkg.prompt_content


class TestOrdering:
    def test_scenarios_before_features(self) -> None:
        features = (full_coverage_feature(),)
        packages = Packager().make_packages(features)
        kinds = [p.kind for p in packages]
        last_scenario_idx = max(i for i, k in enumerate(kinds) if k == PackageKind.SCENARIO)
        first_feature_idx = min(i for i, k in enumerate(kinds) if k == PackageKind.FEATURE)
        assert last_scenario_idx < first_feature_idx
