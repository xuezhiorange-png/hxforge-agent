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
    polish_eval_trial_residual_gate_at_nextafter,
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
    effective_shell_mass_flow_kg_s,
    effective_tube_mass_flow_kg_s,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.direct_coupled_cell_solver import physical_q_upper_w
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import (
    _enumerate_for_fixture,
    _find_bundle,
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


def _endpoint_audits(hit: dict[str, Any], provider: CoolPropProvider) -> dict[str, Any]:
    support = hit["support"]
    upper = physical_q_upper_w(
        tube_upstream=hit["tube_upstream"],
        shell_physical_left=hit["shell_physical_left"],
    )
    endpoints: dict[str, Any] = {}
    hashes: dict[str, str] = {}
    for label, q in [("lower", 0.0), ("upper", upper)]:
        tube_local, shell_local = _enthalpy_cell_mean_states_for_q(
            q,
            tube_upstream=hit["tube_upstream"],
            shell_physical_left=hit["shell_physical_left"],
            provider=provider,
        )
        req = _task172_request(support, tube_local, shell_local, hit["shell_authority"])
        req_hash = recompute_task172_request_hash(req)
        hashes[label] = req_hash
        seed_twi = float(tube_local.native.temperature_k)
        seed_two = float(shell_local.native.temperature_k)
        audit = audit_task172_solver_chain(req, provider, trial_q_w=float(q))
        polish_q = float(audit.get("solver_iterate_q_w", q))
        polish_twi = float(audit.get("twi_k", seed_twi))
        polish_two = float(audit.get("two_k", seed_two))
        if audit.get("frozen_trf_direct_q_w") is not None:
            polish_q = float(audit["frozen_trf_direct_q_w"])
            polish_twi = float(audit.get("twi_k", polish_twi))
            polish_two = float(audit.get("two_k", polish_two))
        polish = polish_eval_trial_residual_gate_at_nextafter(
            req, provider, polish_q, polish_twi, polish_two
        )
        endpoints[label] = {
            "q_w": q,
            "task172_request_hash": req_hash,
            "solver_audit": audit,
            "nextafter_polish": polish,
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
    return {
        "physical_q_upper_w": upper,
        "endpoint_solver_audits": endpoints,
        "endpoint_request_hash_replay": {
            label: recompute_task172_request_hash(
                _task172_request_at_q(
                    0.0 if label == "lower" else upper,
                    support=support,
                    tube_upstream=hit["tube_upstream"],
                    shell_physical_left=hit["shell_physical_left"],
                    provider=provider,
                    shell_authority=hit["shell_authority"],
                )
            )
            == hashes[label]
            for label in ("lower", "upper")
        },
        "tube_mass_flow_kg_s": str(effective_tube_mass_flow_kg_s()),
        "shell_mass_flow_kg_s": str(effective_shell_mass_flow_kg_s()),
    }


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
        "replay_context_identity": "BLOCKED",
    }
    provider = CoolPropProvider()
    normalized, _handoff, enum, _digest = _enumerate_for_fixture()
    _find_bundle(enum, CANDIDATE_ID)
    geom_by_id = {r.candidate_id: r.geometry_projection_hash for r in enum.candidate_records}
    geometry_projection_hash = geom_by_id[CANDIDATE_ID]
    ctx_rating = _build_rating_request()
    if ctx_rating.candidate_id != CANDIDATE_ID:
        raise Support3ReplayError(f"candidate mismatch {ctx_rating.candidate_id}")
    capture["candidate_hash"] = ctx_rating.candidate_hash
    capture["geometry_projection_hash"] = geometry_projection_hash
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
    mesh_error: _Stage3Failure | None = None

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
    try:
        try:
            _candidate_transient_outer_boundary(
                TARGET_MESH, provider, ctx.shell_authority, _CellSearchStats()
            )
        except _Stage3Failure as exc:
            mesh_error = exc
        if mesh_error is not None:
            capture["mesh_outer_outcome"] = mesh_error.code
            capture["mesh_outer_diagnostics"] = list(mesh_error.diagnostics)[:16]
        if hit:
            capture.update(
                {
                    "status": "CAPTURED",
                    "replay_context_identity": "PASS",
                    "physical_support_id": hit["support"].physical_segment_id,
                    "captured_outer_iteration": hit.get("outer_iteration"),
                    "captured_mesh_subdivisions": hit.get("mesh_subdivisions"),
                    "shooting_enthalpy_j_kg": str(hit.get("shooting_enthalpy")),
                }
            )
            capture.update(_endpoint_audits(hit, provider))
        else:
            capture["failure_reason"] = (
                f"no capture at mesh={TARGET_MESH} outer={TARGET_OUTER} support suffix"
            )
    finally:
        t173._solve_cell = native_solve  # type: ignore[method-assign]
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)

    if capture.get("replay_context_identity") == "PASS":
        capture["support3_exact_replay"] = (
            "PASS" if capture.get("status") == "CAPTURED" else "BLOCKED"
        )
    OUT.write_text(json.dumps(capture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT)
    return 0 if capture.get("status") == "CAPTURED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
