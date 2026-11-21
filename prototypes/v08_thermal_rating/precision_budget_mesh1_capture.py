"""V08-03: mesh-1 axial precision budget and outer terminal residual capture."""
# ruff: noqa: E402, E501, I001

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
import sys

sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import TERMINAL_TOLERANCE_K
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _CANDIDATE_RATING_CONTEXT,
    _candidate_context,
    _candidate_transient_outer_boundary,
    _cell_residual_acceptance_tolerance_w,
    _CellSearchStats,
    _eligible_trial,
    _Stage3Failure,
    _valid_trajectory,
    effective_shell_cold_inlet_enthalpy_j_kg,
    effective_shell_mass_flow_kg_s,
    effective_tube_mass_flow_kg_s,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import (
    _enumerate_for_fixture,
    _find_bundle,
)
from prototypes.v08_thermal_rating.mesh2_support2_direct_coupled_verify import (
    CANDIDATE_ID,
    _build_rating_request,
)

CANDIDATE_2 = "9277ebb8-5b05-5130-8b90-92ee4768606b"


def _capture_candidate(candidate_id: str, out_path: Path) -> dict[str, Any]:
    provider = CoolPropProvider()
    normalized, _, enum, _ = _enumerate_for_fixture()
    _find_bundle(enum, candidate_id)
    ctx_rating = _build_rating_request()
    if ctx_rating.candidate_id != candidate_id:
        ctx_rating = ctx_rating.model_copy(update={"candidate_id": candidate_id})
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
    ctx = _candidate_context(ctx_rating)
    ct = _CANDIDATE_RATING_CONTEXT.set(ctx)
    payload: dict[str, Any] = {
        "candidate_id": candidate_id,
        "inner_root_eligible_tolerance_rule": "max(1e-6, 2e-8*|q|)",
        "outer_terminal_tolerance_k": str(TERMINAL_TOLERANCE_K),
        "tube_mdot_kg_s": str(effective_tube_mass_flow_kg_s()),
        "shell_mdot_kg_s": str(effective_shell_mass_flow_kg_s()),
    }
    try:
        try:
            _candidate_transient_outer_boundary(
                1, provider, ctx.shell_authority, _CellSearchStats()
            )
            payload["outer_transient"] = "VALID"
        except _Stage3Failure as exc:
            payload["outer_transient"] = exc.code
            payload["outer_diagnostics"] = list(exc.diagnostics)[:32]
        cold_h = effective_shell_cold_inlet_enthalpy_j_kg()
        f_hi = float(cold_h + Decimal("5000"))
        try:
            run = _valid_trajectory(1, Decimal(str(f_hi)), provider, ctx.shell_authority, 0, None)
            cells: list[dict[str, Any]] = []
            for record in run.cells:
                sol = record.solution
                tol = _cell_residual_acceptance_tolerance_w(sol)
                f_residual = sol.q_w - sol.task172_result.signed_q_hot_to_cold_w
                trial = type("T", (), {})()
                trial.classification = "VALID_CELL_EVALUATION"
                trial.evaluation = sol
                trial.residual = f_residual
                trial.q_w = float(sol.q_w)
                cells.append(
                    {
                        "support_id": record.support.physical_segment_id,
                        "q_trial_would_be_eligible_at": str(tol),
                        "q_task172_w": str(sol.task172_result.signed_q_hot_to_cold_w),
                        "q_propagation_w": str(sol.q_w),
                        "f_q_w": str(f_residual),
                        "eligible_if_f_at_trial_q": _eligible_trial(trial),  # type: ignore[arg-type]
                        "propagation_matches_task172": abs(f_residual) == 0,
                    }
                )
            payload["mesh1_probe_enthalpy_j_kg"] = str(f_hi)
            payload["cells"] = cells
            payload["terminal_residual_k"] = str(run.observables.terminal_boundary_residual_k)
            payload["terminal_residual_j_kg"] = str(run.observables.terminal_boundary_residual_j_kg)
        except _Stage3Failure as exc:
            payload["mesh1_probe"] = exc.code
            payload["mesh1_probe_diagnostics"] = list(exc.diagnostics)[:16]
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    out_dir = Path("/opt/cursor/artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    _capture_candidate(CANDIDATE_ID, out_dir / f"precision_budget_{CANDIDATE_ID}.json")
    _capture_candidate(CANDIDATE_2, out_dir / f"precision_budget_{CANDIDATE_2}.json")
    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
