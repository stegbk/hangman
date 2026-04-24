"""Packager: per-scenario + per-feature LLM prompt packages."""

from __future__ import annotations

from collections import Counter

from tools.dashboard.models import (
    Feature,
    Package,
    PackageKind,
    Scenario,
)


class Packager:
    def make_packages(self, features: tuple[Feature, ...]) -> tuple[Package, ...]:
        scenario_packages = tuple(
            self._make_scenario_package(sc) for feat in features for sc in feat.scenarios
        )
        feature_packages = tuple(self._make_feature_package(feat) for feat in features)
        return scenario_packages + feature_packages

    def _make_scenario_package(self, sc: Scenario) -> Package:
        tags = " ".join(sc.tags) if sc.tags else "(none)"
        steps = "\n".join(f"  {st.keyword.strip()} {st.text}" for st in sc.steps)
        prompt = (
            f"SCENARIO: {sc.name}\n"
            f"File: {sc.feature_file}:{sc.line}\n"
            f"Feature: {sc.feature_name}\n"
            f"Tags: {tags}\n"
            f"Outcome: {sc.outcome.value}\n"
            f"\n"
            f"STEPS:\n"
            f"{steps}\n"
        )
        return Package(
            id=f"scenario:{sc.feature_file}:{sc.line}",
            kind=PackageKind.SCENARIO,
            scenario=sc,
            feature=None,
            prompt_content=prompt,
        )

    def _make_feature_package(self, feat: Feature) -> Package:
        primary_counts = Counter(sc.primary_tag for sc in feat.scenarios if sc.primary_tag)
        primary_line = (
            " · ".join(f"{n} {tag}" for tag, n in sorted(primary_counts.items()))
            or "(no primary tags)"
        )

        scenario_lines = "\n".join(
            f"  - {sc.name} ({' '.join(sc.tags) if sc.tags else '(no tags)'}, {sc.outcome.value})"
            for sc in feat.scenarios
        )

        prompt = (
            f"FEATURE: {feat.name}\n"
            f"File: {feat.file}\n"
            f"Scenarios: {len(feat.scenarios)}\n"
            f"Primary tag mix: {primary_line}\n"
            f"\n"
            f"{scenario_lines}\n"
        )
        return Package(
            id=f"feature:{feat.file}",
            kind=PackageKind.FEATURE,
            scenario=None,
            feature=feat,
            prompt_content=prompt,
        )
