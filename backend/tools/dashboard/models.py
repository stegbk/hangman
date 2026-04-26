"""Dataclass models for the BDD dashboard pipeline.

Leaf-level module: imports nothing from other tools.dashboard modules.
Every dataclass is frozen — the pipeline is a pure data transformation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Severity(Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class Outcome(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_RUN = "not_run"
    UNKNOWN = "unknown"


class CoverageState(Enum):
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class PackageKind(Enum):
    SCENARIO = "scenario"
    FEATURE = "feature"


PRIMARY_TAGS: frozenset[str] = frozenset({"@happy", "@failure", "@edge"})


@dataclass(frozen=True)
class Step:
    keyword: str
    text: str
    outcome: Outcome


@dataclass(frozen=True)
class Scenario:
    feature_file: str
    feature_name: str
    name: str
    line: int
    tags: tuple[str, ...]
    steps: tuple[Step, ...]
    outcome: Outcome

    @property
    def primary_tag(self) -> str | None:
        primaries = [t for t in self.tags if t in PRIMARY_TAGS]
        if len(primaries) == 1:
            return primaries[0]
        return None

    @property
    def is_smoke(self) -> bool:
        return "@smoke" in self.tags


@dataclass(frozen=True)
class Feature:
    file: str
    name: str
    scenarios: tuple[Scenario, ...]
    line: int


@dataclass(frozen=True)
class Finding:
    criterion_id: str
    severity: Severity
    scenario: Scenario | None
    feature: Feature | None
    problem: str
    evidence: str
    reason: str
    fix_example: str
    is_recognized_criterion: bool


@dataclass(frozen=True)
class CoverageGrade:
    subject: str
    kind: str
    state: CoverageState
    contributing_scenarios: tuple[Scenario, ...]
    missing_tags: tuple[str, ...]


@dataclass(frozen=True)
class Package:
    id: str
    kind: PackageKind
    scenario: Scenario | None
    feature: Feature | None
    prompt_content: str


@dataclass(frozen=True)
class LlmCallResult:
    package_id: str
    model: str
    input_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int
    output_tokens: int
    wall_clock_ms: int
    succeeded: bool
    error_message: str | None
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class CostReport:
    model: str
    total_input_tokens: int
    total_cache_read_tokens: int
    total_cache_creation_tokens: int
    total_output_tokens: int
    total_usd: float
    cache_hit_rate: float


@dataclass(frozen=True)
class RunSummary:
    timestamp: str
    total_scenarios: int
    passed: int
    failed: int
    skipped: int
    finding_counts: dict[Severity, int]
    model: str
    cost: CostReport
    skipped_packages: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisContext:
    features: tuple[Feature, ...]
    scenarios: tuple[Scenario, ...]
    endpoint_index: dict[str, tuple[Scenario, ...]]
    uc_index: dict[str, tuple[Scenario, ...]]
    timestamp: str


@dataclass(frozen=True)
class ParseResult:
    features: tuple[Feature, ...]
    scenarios: tuple[Scenario, ...]
    timestamp: str
    gherkin_document_uris: frozenset[str]


@dataclass(frozen=True)
class CoverageContext:
    """Typed view over coverage.json (Feature 3's output) consumed by Feature 2.

    When present, drives: (a) the augment "Code coverage" summary card,
    and (b) a coverage summary injected into the LLM's cached system
    prompt. See design spec §6.2.
    """

    timestamp: str
    totals_pct: float
    totals_tone: str  # "success" | "warning" | "error"
    totals_covered_branches: int
    totals_total_branches: int
    endpoints_summary: tuple[tuple[str, str, float, str], ...]  # (method, path, pct, tone)
    endpoints_uncovered_flat: dict[str, tuple[dict[str, Any], ...]]  # key = f"{method} {path}"
    audit_reconciled: bool
    audit_unattributed_count: int
