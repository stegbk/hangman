"""Synthetic Feature objects for coverage grading tests."""

from tools.dashboard.models import Feature, Outcome, Scenario, Step


def _step(text: str, keyword: str = "Given ") -> Step:
    return Step(keyword=keyword, text=text, outcome=Outcome.PASSED)


def _sc(
    feature_file: str,
    feature_name: str,
    name: str,
    line: int,
    tags: tuple[str, ...],
    step_texts: tuple[str, ...],
) -> Scenario:
    return Scenario(
        feature_file=feature_file,
        feature_name=feature_name,
        name=name,
        line=line,
        tags=tags,
        steps=tuple(_step(t) for t in step_texts),
        outcome=Outcome.PASSED,
    )


def full_coverage_feature() -> Feature:
    """UC1 with POST /guesses endpoint, @happy + @failure + @edge scenarios."""
    name = "UC1 — Play a round"
    file = "features/uc1_play.feature"
    scenarios = (
        _sc(file, name, "valid guess", 10, ("@happy",), ("I POST /guesses with 'a'",)),
        _sc(file, name, "empty letter", 20, ("@failure",), ("I POST /guesses with ''",)),
        _sc(file, name, "unicode letter", 30, ("@edge",), ("I POST /guesses with 'ü'",)),
    )
    return Feature(file=file, name=name, scenarios=scenarios, line=1)


def partial_coverage_feature() -> Feature:
    name = "UC2 — View game"
    file = "features/uc2_view.feature"
    scenarios = (_sc(file, name, "view active", 10, ("@happy",), ("I GET /games/{id}",)),)
    return Feature(file=file, name=name, scenarios=scenarios, line=1)


def no_coverage_feature() -> Feature:
    name = "UC3 — Untagged"
    file = "features/uc3_untagged.feature"
    scenarios = (_sc(file, name, "no primary tag", 10, ("@smoke",), ("I GET /status",)),)
    return Feature(file=file, name=name, scenarios=scenarios, line=1)
