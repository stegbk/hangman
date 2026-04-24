"""Coverage grader: per-endpoint + per-UC grading via scenario tag intersection."""

from __future__ import annotations

import re

from tools.dashboard.models import (
    CoverageGrade,
    CoverageState,
    Feature,
    Scenario,
)

_ENDPOINT_RE = re.compile(r"\b(GET|POST|PATCH|PUT|DELETE)\s+(/[\w/{}\-]*)")
_UC_RE = re.compile(r"\bUC(\d+)\b")
_NUMERIC_SEG_RE = re.compile(r"/\d+")
_UUID_SEG_RE = re.compile(
    r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

_REQUIRED_PRIMARIES: tuple[str, ...] = ("@happy", "@failure", "@edge")


class CoverageGrader:
    def grade(
        self,
        features: tuple[Feature, ...],
    ) -> tuple[
        dict[str, tuple[Scenario, ...]],
        dict[str, tuple[Scenario, ...]],
        tuple[CoverageGrade, ...],
    ]:
        endpoint_index = self._build_endpoint_index(features)
        uc_index = self._build_uc_index(features)

        grades: list[CoverageGrade] = []
        for endpoint, scs in sorted(endpoint_index.items()):
            grades.append(self._grade(endpoint, "endpoint", scs))
        for uc, scs in sorted(uc_index.items()):
            grades.append(self._grade(uc, "uc", scs))

        return endpoint_index, uc_index, tuple(grades)

    def _build_endpoint_index(
        self,
        features: tuple[Feature, ...],
    ) -> dict[str, tuple[Scenario, ...]]:
        idx: dict[str, list[Scenario]] = {}
        for feat in features:
            for sc in feat.scenarios:
                for step in sc.steps:
                    for match in _ENDPOINT_RE.finditer(step.text):
                        method, path = match.group(1), match.group(2)
                        normalized = self._normalize_path(path)
                        key = f"{method} {normalized}"
                        idx.setdefault(key, []).append(sc)
        return {k: tuple(dict.fromkeys(v)) for k, v in idx.items()}

    def _build_uc_index(
        self,
        features: tuple[Feature, ...],
    ) -> dict[str, tuple[Scenario, ...]]:
        idx: dict[str, list[Scenario]] = {}
        for feat in features:
            m = _UC_RE.search(feat.name)
            if not m:
                continue
            uc_key = f"UC{m.group(1)}"
            idx.setdefault(uc_key, []).extend(feat.scenarios)
        return {k: tuple(dict.fromkeys(v)) for k, v in idx.items()}

    def _normalize_path(self, path: str) -> str:
        path = _UUID_SEG_RE.sub("/{id}", path)
        path = _NUMERIC_SEG_RE.sub("/{id}", path)
        return path

    def _grade(
        self,
        subject: str,
        kind: str,
        scenarios: tuple[Scenario, ...],
    ) -> CoverageGrade:
        tag_set: set[str] = set()
        for sc in scenarios:
            if sc.primary_tag:
                tag_set.add(sc.primary_tag)
        missing = tuple(sorted(t for t in _REQUIRED_PRIMARIES if t not in tag_set))

        if not tag_set:
            state = CoverageState.NONE
        elif len(tag_set & set(_REQUIRED_PRIMARIES)) == len(_REQUIRED_PRIMARIES):
            state = CoverageState.FULL
        else:
            state = CoverageState.PARTIAL

        return CoverageGrade(
            subject=subject,
            kind=kind,
            state=state,
            contributing_scenarios=scenarios,
            missing_tags=missing,
        )
