"""Exact Mesh-1 outer-44 support-3 replay for V08-03 candidate e1baa795."""
# ruff: noqa: E402

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from hexagent.exchangers.shell_tube.task172_local_runtime.service import (
    audit_task172_solver_chain,
    recompute_task172_request_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _CANDIDATE_RATING_CONTEXT,
    _candidate_context,
    _candidate_transient_outer_boundary,
    _CellSearchStats,
    _enthalpy_cell_mean_states_for_q,
    _Stage3Failure,
    _task172_request,
    _Task172NumericalHole,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_thermal_rating.direct_coupled_cell_solver import physical_q_upper_w
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import (
    DEFAULT_FIXTURE,
    _enumerate_for_fixture,
)
from prototypes.v08_thermal_rating.mesh2_support2_direct_coupled_verify import (
    CANDIDATE_ID,
    _build_rating_request,
)

TARGET_MESH = 1
TARGET_OUTER = 44
TARGET_SUPPORT_SUFFIX = "support:3"
OUT = Path(f"/opt/cursor/artifacts/v08_03_support3_outer44_replay_{CANDIDATE_ID}.json")


class Support3ReplayError(RuntimeError):
    pass


def _task172_request_at_q(
    q_w: float,
    *,
    support: Any,
    tube_upstream: Any,
    shell_physical_left: Any,
    provider: Any,
    shell_authority: Any,
) -> Any:
    tube_local, shell_local = _enthalpy_cell_mean_states_for_q(
        q_w,
        tube_upstream=tube_upstream,
        shell_physical_left=shell_physical_left,
        provider=provider,
    )
    return _task172_request(support, tube_local, shell_local, shell_authority)


def main() -> int:
    os.environ.setdefault("HXFORGE_TASK173_CAPTURE_CELL_ROOT_DIAGNOSTICS", "1")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    hit: dict[str, Any] = {}
    capture: dict[str, Any] = {
        "task_id": "V08_03_SUPPORT3_EXACT_REPLAY",
        "candidate_id": CANDIDATE_ID,
        "target_mesh_subdivisions": TARGET_MESH,
        "target_outer_iteration": TARGET_OUTER,
        "target_support_suffix": TARGET_SUPPORT_SUFFIX,
        "status": "BLOCKED",
    }
    provider = CoolPropProvider()
    _enumerate_for_fixture()
    ctx_rating = _build_rating_request()
    if ctx_rating.candidate_id != CANDIDATE_ID:
        raise Support3ReplayError(f"candidate mismatch {ctx_rating.candidate_id}")
    capture["geometry_projection_hash"] = ctx_rating.geometry_projection_hash
    capture["candidate_hash"] = ctx_rating.candidate_hash
    normalized = validate_and_build_solver_handoff(
        load_general_user_design_case_json(DEFAULT_FIXTURE.read_text(encoding="utf-8")),
        provider=provider,
    ).normalized
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
    tok = bind_experimental_thermal_boundary_v1(exp)
    native_solve = t173._solve_cell
    ctx = _candidate_context(ctx_rating)
    ct = _CANDIDATE_RATING_CONTEXT.set(ctx)

    def intercept(**kwargs: Any) -> Any:
        subdiv = kwargs.get("mesh_subdivisions")
        outer = kwargs.get("outer_iteration")
        support = kwargs["support"]
        if (
            subdiv == TARGET_MESH
            and outer == TARGET_OUTER
            and TARGET_SUPPORT_SUFFIX in support.physical_segment_id
        ):
            hit.clear()
            hit.update(kwargs)
        return native_solve(**kwargs)

    t173._solve_cell = intercept  # type: ignore[method-assign]
    mesh_error: _Stage3Failure | None = None
    try:
        try:
            _candidate_transient_outer_boundary(
                TARGET_MESH, provider, ctx.shell_authority, _CellSearchStats()
            )
        except _Stage3Failure as exc:
            mesh_error = exc
    finally:
        t173._solve_cell = native_solve  # type: ignore[method-assign]
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)

    if mesh_error is not None:
        capture["mesh_outer_outcome"] = mesh_error.code
        capture["mesh_outer_diagnostics"] = list(mesh_error.diagnostics)

    if not hit:
        capture["failure_reason"] = (
            f"no capture at mesh={TARGET_MESH} outer={TARGET_OUTER} support suffix"
        )
        OUT.write_text(json.dumps(capture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(OUT)
        return 2

    support = hit["support"]
    capture.update(
        {
            "status": "CAPTURED",
            "physical_support_id": support.physical_segment_id,
            "captured_outer_iteration": hit.get("outer_iteration"),
            "captured_mesh_subdivisions": hit.get("mesh_subdivisions"),
            "shooting_enthalpy_j_kg": str(hit.get("shooting_enthalpy")),
        }
    )
    upper = physical_q_upper_w(
        tube_upstream=hit["tube_upstream"],
        shell_physical_left=hit["shell_physical_left"],
    )
    capture["physical_q_upper_w"] = upper
    endpoints: dict[str, Any] = {}
    for label, q in [("lower", 0.0), ("upper", upper)]:
        req = _task172_request_at_q(
            q,
            support=support,
            tube_upstream=hit["tube_upstream"],
            shell_physical_left=hit["shell_physical_left"],
            provider=provider,
            shell_authority=hit["shell_authority"],
        )
        endpoints[label] = {
            "q_w": q,
            "task172_request_hash": recompute_task172_request_hash(req),
            "solver_audit": audit_task172_solver_chain(req, provider),
        }
        try:
            t173._cell_evaluation(
                q,
                support=support,
                tube_upstream=hit["tube_upstream"],
                shell_physical_left=hit["shell_physical_left"],
                provider=provider,
                shell_authority=hit["shell_authority"],
            )
            endpoints[label]["cell_evaluation"] = "VALID"
        except _Task172NumericalHole:
            endpoints[label]["cell_evaluation"] = "TASK172_NUMERICAL_HOLE"
        except _Stage3Failure as exc:
            endpoints[label]["cell_evaluation"] = exc.code
    capture["endpoint_solver_audits"] = endpoints
    OUT.write_text(json.dumps(capture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
