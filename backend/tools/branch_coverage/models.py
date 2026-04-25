"""Dataclass models for the branch coverage pipeline.

Leaf-level module: imports nothing from other tools.branch_coverage modules.
Every dataclass is frozen — the pipeline is a pure data transformation.
"""

from dataclasses import dataclass
from enum import Enum


class Tone(Enum):
    SUCCESS = "success"  # pct >= 80
    WARNING = "warning"  # 50 <= pct < 80
    ERROR = "error"  # pct < 50
    NA = "na"  # total_branches == 0


@dataclass(frozen=True)
class Endpoint:
    method: str
    path: str
    handler_qualname: str


@dataclass(frozen=True)
class ReachableBranch:
    file: str
    line: int
    branch_id: str
    condition_text: str
    not_taken_to_line: int
    function_qualname: str


@dataclass(frozen=True)
class FunctionCoverage:
    file: str
    qualname: str
    total_branches: int
    covered_branches: int
    pct: float
    reached: bool
    uncovered_branches: tuple[ReachableBranch, ...]


@dataclass(frozen=True)
class CoveragePerEndpoint:
    endpoint: Endpoint
    reachable_functions: tuple[FunctionCoverage, ...]
    total_branches: int
    covered_branches: int
    pct: float
    tone: Tone

    @property
    def uncovered_branches_flat(self) -> tuple[ReachableBranch, ...]:
        return tuple(b for fc in self.reachable_functions for b in fc.uncovered_branches)


@dataclass(frozen=True)
class ExtraCoverage:
    file: str
    qualname: str
    reason: str


@dataclass(frozen=True)
class UnattributedBranch:
    file: str
    line: int
    branch_id: str
    reason: str


@dataclass(frozen=True)
class AuditReport:
    total_branches_per_coverage_py: int
    total_branches_enumerated_via_reachability: int
    extra_coverage_branches: int
    unattributed_branches: tuple[UnattributedBranch, ...]
    reconciled: bool


@dataclass(frozen=True)
class Totals:
    total_branches: int
    covered_branches: int
    pct: float
    tone: Tone


@dataclass(frozen=True)
class LoadedCoverage:
    """Output of CoverageDataLoader. Per-context hit sets + authoritative totals."""

    hits_by_context: dict[str, frozenset[tuple[str, str]]]
    total_branches_per_file: dict[str, int]
    all_hits: frozenset[tuple[str, str]]


@dataclass(frozen=True)
class CoverageReport:
    version: int
    timestamp: str
    cucumber_ndjson: str
    instrumented: bool
    thresholds: dict[str, float]
    totals: Totals
    endpoints: tuple[CoveragePerEndpoint, ...]
    extra_coverage: tuple[ExtraCoverage, ...]
    audit: AuditReport
