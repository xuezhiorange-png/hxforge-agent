"""Run true (q,Twi,Two) three-equation coupling at latest fatal support-thermo replay state."""

# Standalone verifier must prepend repository paths before project imports.
# ruff: noqa: E402

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173_service
from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _candidate_context,
    _CANDIDATE_RATING_CONTEXT,
    _candidate_transient_outer_boundary,
    _CellSearchStats,
    _Stage3Failure,
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
from prototypes.v08_thermal_rating.true_three_equation_cell_coupling import (
    solve_true_three_equation_coupling,
)

FIXTURE = _REPO_ROOT / "tests/fixtures/v08_03/e1baa795_fatal_cell_identity_minimal.json"
OUT_PATH = Path(f"/opt/cursor/artifacts/v08_03_true_coupled_verify_{CANDIDATE_ID}.json")


def main() -> int:
    os.environ.setdefault("HXFORGE_TASK173_CAPTURE_CELL_ROOT_DIAGNOSTICS", "1")
    Path("/opt/cursor/artifacts").mkdir(parents=True, exist_ok=True)
    fatal_wrapper = json.loads(FIXTURE.read_text(encoding="utf-8"))
    fatal = fatal_wrapper["fatal_cell"]
    target_mesh = int(fatal["mesh_subdivisions"])

    capture: dict[str, Any] = {
        "fixture_path": str(FIXTURE.relative_to(_REPO_ROOT)),
        "fatal_cell_from_fixture": fatal,
        "verify_ran": False,
    }
    replay_state: dict[str, Any] = {"outer_iteration": -1, "physical_support_id": None}

    rating_req = _build_rating_request()
    provider = CoolPropProvider()
    normalized, _, _enum, _ = _enumerate_for_fixture()
    case = load_general_user_design_case_json(DEFAULT_FIXTURE.read_text(encoding="utf-8"))
    pipeline = validate_and_build_solver_handoff(case, provider=provider)
    assert pipeline.handoff.thermal_binding is not None
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
    native_solve = t173_service._solve_cell

    def intercept(**kwargs: Any) -> Any:
        support = kwargs["support"]
        mesh = kwargs.get("mesh_subdivisions")
        outer = kwargs.get("outer_iteration")
        sid = support.physical_segment_id
        if (
            mesh == target_mesh
            and sid == fatal["physical_support_id"]
            and outer is not None
            and int(outer) >= int(replay_state["outer_iteration"])
        ):
            replay_state.update(kwargs)
            replay_state["outer_iteration"] = int(outer)
        return native_solve(**kwargs)

    t173_service._solve_cell = intercept  # type: ignore[method-assign]
    context = _candidate_context(rating_req)
    ctx_token = _CANDIDATE_RATING_CONTEXT.set(context)
    try:
        try:
            _candidate_transient_outer_boundary(
                target_mesh, provider, context.shell_authority, _CellSearchStats()
            )
        except _Stage3Failure as exc:
            capture["mesh_outer_outcome"] = exc.code
    finally:
        if replay_state.get("support") is not None:
            upper = physical_q_upper_w(
                tube_upstream=replay_state["tube_upstream"],
                shell_physical_left=replay_state["shell_physical_left"],
            )
            capture["physical_q_upper_w"] = upper
            capture["replayed_outer_iteration"] = replay_state["outer_iteration"]
            capture["three_equation"] = solve_true_three_equation_coupling(
                support=replay_state["support"],
                tube_upstream=replay_state["tube_upstream"],
                shell_physical_left=replay_state["shell_physical_left"],
                provider=replay_state["provider"],
                shell_authority=replay_state["shell_authority"],
                q_upper=upper,
            )
            capture["verify_ran"] = True
        _CANDIDATE_RATING_CONTEXT.reset(ctx_token)
        t173_service._solve_cell = native_solve  # type: ignore[method-assign]
        reset_experimental_thermal_boundary(token)

    capture["task_id"] = "V08_03_TRUE_COUPLED_CELL_VALIDATION"
    capture["direct_coupled_method_validated"] = bool(
        capture.get("three_equation", {}).get("original_residual_gate_pass")
    )
    OUT_PATH.write_text(json.dumps(capture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
