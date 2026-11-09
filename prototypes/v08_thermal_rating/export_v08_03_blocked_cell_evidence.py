"""Export machine-readable Task173 cell-root + Task172 evidence for one V08 candidate (diagnostics).

Requires env:
  HXFORGE_TASK173_CAPTURE_CELL_ROOT_DIAGNOSTICS=1
  HXFORGE_TASK172_SOLVER_TRACE=1   (optional; records TRF/dogbox/R23-wide path)

Usage (from repo root)::

    HXFORGE_TASK173_CAPTURE_CELL_ROOT_DIAGNOSTICS=1 \\
    HXFORGE_TASK172_SOLVER_TRACE=1 \\
    python3 prototypes/v08_thermal_rating/export_v08_03_blocked_cell_evidence.py \\
      e1baa795-9cf5-5718-8fa8-0688d2102c5c

Writes ``v08_03_blocked_cell_evidence_<candidate_id>.json`` under ``/opt/cursor/artifacts/``.
"""

# Standalone entry point must prepend the repository path before project imports.
# ruff: noqa: E402

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, cast

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    request_hash as task168_request_hash_digest,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    candidate_rating_request_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import Task173BlockedResult
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    validate_candidate_rating,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.candidate_materialization import (
    materialize_candidate_task171,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.service import (
    _candidate_request_for_task174,
    v08_thermal_rating_request,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    Task174NativeOutputs,
    Task174SuccessResult,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    validate_candidate_request as validate_task174_candidate,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_geometry_candidate_generation.discrete_space import (
    DEFAULT_V08_DISCRETE_SPACE_PATH,
    load_v08_discrete_space,
)
from prototypes.v08_geometry_candidate_generation.generator import enumerate_structural_geometry
from prototypes.v08_geometry_candidate_generation.task168_builder import (
    build_v08_task168_request,
    filter_discrete_space_by_envelope,
)

REPO = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = REPO / "tests/fixtures/v08_user_case_no_geometry_task174_admissible.json"
DISCRETE_SPACE = DEFAULT_V08_DISCRETE_SPACE_PATH


def _enumerate_for_fixture() -> tuple[Any, Any, Any, str]:
    case_text = DEFAULT_FIXTURE.read_text(encoding="utf-8")
    case = load_general_user_design_case_json(case_text)
    pipeline = validate_and_build_solver_handoff(case, provider=CoolPropProvider())
    normalized = pipeline.normalized
    handoff = pipeline.handoff
    if (
        handoff.downstream_readiness != "THERMAL_HYDRAULIC_PARAMETERS_READY"
        or handoff.thermal_binding is None
    ):
        raise RuntimeError("fixture handoff not ready for thermal rating")

    space = load_v08_discrete_space(DISCRETE_SPACE)
    filtered, _ = filter_discrete_space_by_envelope(space, normalized.design_envelope)
    t168 = build_v08_task168_request(normalized, handoff, filtered)
    digest = task168_request_hash_digest(t168)
    enum = enumerate_structural_geometry(
        t168,
        filtered,
        (),
        max_valid_candidates=256,
    )
    return normalized, handoff, enum, digest


def _find_bundle(enum: Any, candidate_id: str):
    for row in enum.valid_structural:
        if row.candidate.candidate_id == candidate_id:
            return row
    raise LookupError(f"candidate_id not found in enumerated structural geometry: {candidate_id}")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: export_v08_03_blocked_cell_evidence.py <candidate_id>", file=sys.stderr)
        return 2
    candidate_id = sys.argv[1]

    os.environ.setdefault("HXFORGE_TASK173_CAPTURE_CELL_ROOT_DIAGNOSTICS", "1")
    os.environ.setdefault("HXFORGE_TASK172_SOLVER_TRACE", "1")

    normalized, handoff, enum, task168_digest = _enumerate_for_fixture()
    space_hash = enum.space_hash
    bundle_row = _find_bundle(enum, candidate_id)
    candidate = bundle_row.candidate
    b = bundle_row.bundle

    topology = materialize_candidate_task171(
        candidate=candidate,
        configuration=b.task020_configuration,
        layout=b.task021_layout,
        bundle_geometry=b.task022_geometry,
        baffle_geometry=b.task024_geometry,
        task025_result=b.task025_result,
        task024_request=b.task024_request,
        task025_request=b.task025_request,
    )
    t174_req = _candidate_request_for_task174(candidate, b, topology)
    t174 = validate_task174_candidate(
        t174_req,
        Task174NativeOutputs(
            task029=b.task029_result,
            task034=None,
            task166=b.task166_result,
        ),
    )
    if type(t174) is not Task174SuccessResult:
        print(f"TASK174 not validated: {type(t174).__name__}", file=sys.stderr)
        return 1

    rating_req = v08_thermal_rating_request(
        candidate,
        space_hash,
        b,
        topology,
        t174,
        task168_digest,
    )
    rhash = candidate_rating_request_hash(rating_req)

    assert handoff.thermal_binding is not None
    provider = CoolPropProvider()
    exp = build_experimental_thermal_boundary_v1(
        provider=provider,
        tube_inlet_temperature_k=normalized.tube_side.inlet_temperature_k,
        shell_inlet_temperature_k=normalized.shell_side.inlet_temperature_k,
        tube_mass_flow_kg_s=normalized.tube_side.mass_flow_kg_s,
        shell_mass_flow_kg_s=normalized.shell_side.mass_flow_kg_s,
        tube_property_evaluation_pressure_pa=normalized.tube_side.inlet_pressure_pa,
        shell_property_evaluation_pressure_pa=normalized.shell_side.inlet_pressure_pa,
        allow_live_variable_tube_mass_flow=True,
        allow_live_variable_shell_mass_flow=True,
        allow_variable_water_temperature=True,
    )
    token = bind_experimental_thermal_boundary_v1(exp)
    try:
        outcome = validate_candidate_rating(rating_req, provider)
    finally:
        reset_experimental_thermal_boundary(token)

    out_dir = Path("/opt/cursor/artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"v08_03_blocked_cell_evidence_{candidate_id}.json"

    geom_by_id = {r.candidate_id: r.geometry_projection_hash for r in enum.candidate_records}
    geometry_projection_hash = geom_by_id.get(candidate_id, "")

    payload: dict[str, Any] = {
        "task_id": "V08_03_NUMERICAL_SOLVER_PROOF_AND_CLOSEOUT",
        "candidate_id": candidate_id,
        "candidate_hash": candidate.candidate_hash,
        "geometry_projection_hash": geometry_projection_hash,
        "candidate_rating_request_hash": rhash,
        "task173_status": outcome.status if hasattr(outcome, "status") else type(outcome).__name__,
    }

    if type(outcome) is Task173BlockedResult:
        blocked = cast(Task173BlockedResult, outcome)
        payload["task173_failure_code"] = blocked.failure_code
        payload["task173_failed_mesh_subdivisions"] = blocked.failed_mesh_subdivisions
        payload["task173_result_hash"] = blocked.result_hash
        diag = list(blocked.diagnostics)
        payload["task173_diagnostics"] = diag
        stats_json = None
        for item in diag:
            if item.startswith("task173_cell_search_stats_json="):
                stats_json = json.loads(item.split("=", 1)[1])
                break
        payload["task173_cell_search_stats"] = stats_json
    else:
        payload["note"] = "Task173 did not return BLOCKED; success or unexpected type"

    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
