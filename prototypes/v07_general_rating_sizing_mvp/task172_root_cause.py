"""Reproduce Task172 failure diagnostics for MVP candidates (read-only)."""

from __future__ import annotations

import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from hexagent.exchangers.shell_tube.bell_delaware.models import Task166BlockedResult, Task166Result
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import candidate_space_hash
from hexagent.exchangers.shell_tube.task173_integrated_rating import validate_candidate_rating
from hexagent.exchangers.shell_tube.task173_integrated_sizing.candidate_materialization import (
    materialize_candidate_task171,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.service import (
    DIMENSION_ORDER,
    _candidate_rating_request,
    _candidate_request_for_task174,
    validate_task174_candidate,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    Task174NativeOutputs,
    Task174SuccessResult,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV1
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task173_sizing_request,
)


@dataclass(frozen=True)
class Task172RootCauseRecord:
    candidate_id: str
    candidate_hash: str
    rating_request_hash: str | None
    rating_result_hash: str | None
    task173_failure_code: str
    task172_original_failure_code: str | None
    task172_failure_field_path: str | None
    diagnostics: tuple[str, ...]
    failed_mesh_subdivisions: int | None
    native_identities: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "hxforge.task172-failure-root-cause.v1",
            "candidate_id": self.candidate_id,
            "candidate_hash": self.candidate_hash,
            "rating_request_hash": self.rating_request_hash,
            "rating_result_hash": self.rating_result_hash,
            "task173_failure_code": self.task173_failure_code,
            "task172_original_failure_code": self.task172_original_failure_code,
            "task172_failure_field_path": self.task172_failure_field_path,
            "diagnostics": list(self.diagnostics),
            "failed_mesh_subdivisions": self.failed_mesh_subdivisions,
            "native_identities": list(self.native_identities),
        }


def diagnose_first_blocked_candidate(case: GeneralEngineeringCaseV1) -> Task172RootCauseRecord:
    sizing_req = build_task173_sizing_request(case)
    t168 = sizing_req.task168_candidate_request
    authorities = task168._authority_map(t168)
    dimensions = tuple(
        task168._sort_values(authorities[role].values)
        for role in DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    )
    space_hash = candidate_space_hash(t168, t168.discrete_candidate_set_authorities)
    digest = sizing_req.requirement_authority.canonical_hash
    for combination in itertools.product(t168.shell_geometry_catalog.records, *dimensions):
        candidate = task168._candidate(t168, authorities, combination[0], tuple(combination[1:]))
        if task168._structural_blockers(candidate):
            continue
        bundle, stage_failure, _ = task168._execute_candidate_chain(
            t168,
            candidate,
            combination[0],
            include_legacy_task162=False,
            include_legacy_task168_rating_dependencies=False,
            preserve_baffle_orientation_sequence=False,
        )
        if stage_failure is not None:
            continue
        topology = materialize_candidate_task171(
            candidate=candidate,
            configuration=bundle.task020_configuration,
            layout=bundle.task021_layout,
            bundle_geometry=bundle.task022_geometry,
            baffle_geometry=bundle.task024_geometry,
            task025_result=bundle.task025_result,
            task024_request=bundle.task024_request,
            task025_request=bundle.task025_request,
        )
        t174_req = _candidate_request_for_task174(candidate, bundle, topology)
        t174 = validate_task174_candidate(
            t174_req,
            Task174NativeOutputs(
                task029=bundle.task029_result,
                task034=None,
                task166=cast(Task166Result | Task166BlockedResult | None, bundle.task166_result),
            ),
        )
        if type(t174) is not Task174SuccessResult:
            continue
        rating_request = _candidate_rating_request(
            candidate, space_hash, bundle, topology, t174, digest
        )
        from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
            candidate_rating_request_hash,
        )

        rating_request_hash = candidate_rating_request_hash(rating_request)
        outcome = validate_candidate_rating(rating_request)
        if getattr(outcome, "status", None) == "VALIDATED":
            raise RuntimeError("expected blocked rating for root-cause capture")
        task172_code = None
        if outcome.diagnostics:
            first = outcome.diagnostics[0]
            if first.startswith("BLOCKED_"):
                task172_code = first
        identities: tuple[tuple[str, str], ...] = (
            ("TASK171", topology.result_hash or ""),
            ("TASK174", t174.result_hash),
            ("TASK025", bundle.task025_result.result_hash),
        )
        return Task172RootCauseRecord(
            candidate_id=candidate.candidate_id,
            candidate_hash=candidate.candidate_hash,
            rating_request_hash=rating_request_hash,
            rating_result_hash=outcome.result_hash,
            task173_failure_code=outcome.failure_code,
            task172_original_failure_code=task172_code,
            task172_failure_field_path=None,
            diagnostics=outcome.diagnostics,
            failed_mesh_subdivisions=outcome.failed_mesh_subdivisions,
            native_identities=identities,
        )
    raise RuntimeError("no rateable candidate found for root-cause capture")


def write_task172_root_cause(case: GeneralEngineeringCaseV1, path: Path) -> Task172RootCauseRecord:
    record = diagnose_first_blocked_candidate(case)
    path.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record
