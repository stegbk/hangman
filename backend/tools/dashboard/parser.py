"""Parser: Cucumber Messages NDJSON → ParseResult.

Validates meta.protocolVersion major == 32 (schema we built against).
Reads gherkinDocument envelopes for AST (zero parse-the-raw-Gherkin cost).
Correlates pickle.id → scenario, testCaseStarted.testCaseId → testCase.pickleId
→ scenario, rolls up testStepFinished.testStepResult.status → Outcome.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.dashboard.models import (
    Feature,
    Outcome,
    ParseResult,
    Scenario,
    Step,
)

_STATUS_TO_OUTCOME: dict[str, Outcome] = {
    "PASSED": Outcome.PASSED,
    "FAILED": Outcome.FAILED,
    "SKIPPED": Outcome.SKIPPED,
    "PENDING": Outcome.FAILED,
    "AMBIGUOUS": Outcome.FAILED,
    "UNDEFINED": Outcome.FAILED,
    "UNKNOWN": Outcome.UNKNOWN,
}


def _rollup_outcome(step_statuses: list[str]) -> Outcome:
    if not step_statuses:
        return Outcome.NOT_RUN
    outcomes = [_STATUS_TO_OUTCOME.get(s, Outcome.UNKNOWN) for s in step_statuses]
    if Outcome.FAILED in outcomes:
        return Outcome.FAILED
    if Outcome.UNKNOWN in outcomes:
        return Outcome.UNKNOWN
    if Outcome.SKIPPED in outcomes:
        return Outcome.SKIPPED
    if all(o == Outcome.PASSED for o in outcomes):
        return Outcome.PASSED
    return Outcome.UNKNOWN


class NdjsonParser:
    def parse(self, ndjson_path: Path) -> ParseResult:
        envelopes = self._read_envelopes(ndjson_path)
        self._validate_protocol_version(envelopes)

        gherkin_docs: list[Any] = [
            e["gherkinDocument"] for e in envelopes if "gherkinDocument" in e
        ]
        pickles: dict[str, Any] = {
            e["pickle"]["id"]: e["pickle"] for e in envelopes if "pickle" in e
        }
        test_cases: dict[str, Any] = {
            e["testCase"]["id"]: e["testCase"] for e in envelopes if "testCase" in e
        }
        test_case_starteds: dict[str, Any] = {
            e["testCaseStarted"]["id"]: e["testCaseStarted"]
            for e in envelopes
            if "testCaseStarted" in e
        }

        # testCaseStartedId → list of (testStepId, status)
        step_results: dict[str, list[tuple[str, str]]] = {}
        for e in envelopes:
            if "testStepFinished" not in e:
                continue
            tsf: Any = e["testStepFinished"]
            step_results.setdefault(tsf["testCaseStartedId"], []).append(
                (tsf["testStepId"], tsf["testStepResult"]["status"])
            )

        # pickleId → ordered step statuses
        pickle_statuses: dict[str, list[str]] = {}
        for tcs_id, results in step_results.items():
            tcs: Any = test_case_starteds.get(tcs_id)
            if tcs is None:
                continue
            tc: Any = test_cases.get(tcs["testCaseId"])
            if tc is None:
                continue
            # order by testStep position in the testCase
            order: dict[str, int] = {ts["id"]: i for i, ts in enumerate(tc["testSteps"])}
            ordered = sorted(results, key=lambda r: order.get(r[0], 0))
            pickle_statuses[tc["pickleId"]] = [status for _, status in ordered]

        # scenario ast node id → pickle (many pickles possible for Scenario Outline; simple 1:1 here)
        pickle_by_scenario_ast: dict[str, Any] = {}
        for pk in pickles.values():
            for node_id in pk.get("astNodeIds", []):
                pickle_by_scenario_ast[str(node_id)] = pk

        features: list[Feature] = []
        scenarios: list[Scenario] = []
        uris: set[str] = set()

        for gd in gherkin_docs:
            uri: str = gd.get("uri", "")
            uris.add(uri)
            feature_block: Any = gd.get("feature") or {}
            feature_name: str = feature_block.get("name", "")
            feature_line: int = feature_block.get("location", {}).get("line", 0)

            feat_scenarios: list[Scenario] = []
            for child in feature_block.get("children", []):
                sc_ast: Any = child.get("scenario")
                if sc_ast is None:
                    continue
                sc_line: int = sc_ast.get("location", {}).get("line", 0)
                sc_name: str = sc_ast.get("name", "")
                tags = tuple(str(t["name"]) for t in sc_ast.get("tags", []))
                steps = tuple(
                    Step(
                        keyword=str(st["keyword"]),
                        text=str(st["text"]),
                        outcome=Outcome.NOT_RUN,
                    )
                    for st in sc_ast.get("steps", [])
                )
                pickle: Any = pickle_by_scenario_ast.get(str(sc_ast["id"]))
                step_statuses_list = pickle_statuses.get(str(pickle["id"]), []) if pickle else []
                outcome = _rollup_outcome(step_statuses_list)

                scenario = Scenario(
                    feature_file=uri,
                    feature_name=feature_name,
                    name=sc_name,
                    line=sc_line,
                    tags=tags,
                    steps=steps,
                    outcome=outcome,
                )
                feat_scenarios.append(scenario)
                scenarios.append(scenario)

            features.append(
                Feature(
                    file=uri,
                    name=feature_name,
                    scenarios=tuple(feat_scenarios),
                    line=feature_line,
                )
            )

        timestamp = self._extract_timestamp(envelopes)

        return ParseResult(
            features=tuple(features),
            scenarios=tuple(scenarios),
            timestamp=timestamp,
            gherkin_document_uris=frozenset(uris),
        )

    def _read_envelopes(self, path: Path) -> list[Any]:
        with path.open() as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def _validate_protocol_version(self, envelopes: list[Any]) -> None:
        meta_envelopes = [e for e in envelopes if "meta" in e]
        if not meta_envelopes:
            raise ValueError("NDJSON missing meta envelope")
        version: str = meta_envelopes[0]["meta"]["protocolVersion"]
        if not version.startswith("32."):
            raise ValueError(
                f"Unsupported Cucumber Messages protocolVersion {version} — expected 32.x"
            )

    def _extract_timestamp(self, envelopes: list[Any]) -> str:
        for e in envelopes:
            if "testRunStarted" in e:
                ts: Any = e["testRunStarted"]["timestamp"]
                seconds = int(ts["seconds"]) + int(ts.get("nanos", 0)) / 1e9
                dt = datetime.fromtimestamp(seconds, tz=UTC)
                return dt.isoformat().replace("+00:00", "Z")
        return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
