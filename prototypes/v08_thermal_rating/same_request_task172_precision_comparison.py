"""Emit machine-readable same-request Task172 precision comparison at fatal cell."""

# ruff: noqa: E402

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173_service
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
    _Stage3Failure,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import (
    DEFAULT_FIXTURE,
    _enumerate_for_fixture,
)
from prototypes.v08_thermal_rating.mesh2_support2_direct_coupled_verify import (
    CANDIDATE_ID,
    _build_rating_request,
)
from prototypes.v08_thermal_rating.true_three_equation_cell_coupling import (
    build_task172_request_for_q,
    compare_same_request_production_vs_frozen_trf,
)

FIXTURE = _REPO / "tests/fixtures/v08_03/e1baa795_fatal_cell_identity_minimal.json"
OUT = Path(f"/opt/cursor/artifacts/v08_03_same_request_comparison_{CANDIDATE_ID}.json")


def main() -> int:
    os.environ.setdefault("HXFORGE_TASK173_CAPTURE_CELL_ROOT_DIAGNOSTICS", "1")
    Path("/opt/cursor/artifacts").mkdir(parents=True, exist_ok=True)
    fatal = json.loads(FIXTURE.read_text(encoding="utf-8"))["fatal_cell"]
    target_mesh = int(fatal["mesh_subdivisions"])
    capture: dict[str, Any] = {}
    replay: dict[str, Any] = {"outer_iteration": -1}

    provider = CoolPropProvider()
    normalized, _handoff, _enum, _digest = _enumerate_for_fixture()
    validate_and_build_solver_handoff(
        load_general_user_design_case_json(DEFAULT_FIXTURE.read_text(encoding="utf-8")),
        provider=provider,
    )
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
    native = t173_service._solve_cell
    rating_req = _build_rating_request()
    ctx = _candidate_context(rating_req)
    ct = _CANDIDATE_RATING_CONTEXT.set(ctx)

    def intercept(**kwargs: Any) -> Any:
        s = kwargs["support"]
        if (
            kwargs.get("mesh_subdivisions") == target_mesh
            and s.physical_segment_id == fatal["physical_support_id"]
            and int(kwargs.get("outer_iteration") or -1) >= int(replay["outer_iteration"])
        ):
            replay.update(kwargs)
            replay["outer_iteration"] = int(kwargs["outer_iteration"])
        return native(**kwargs)

    t173_service._solve_cell = intercept  # type: ignore[method-assign]
    try:
        try:
            _candidate_transient_outer_boundary(
                target_mesh, provider, ctx.shell_authority, _CellSearchStats()
            )
        except _Stage3Failure as exc:
            capture["mesh_outer_outcome"] = exc.code
        if replay.get("support"):
            q_probe = float(fatal.get("initial_valid_anchor_q_w") or 0) * 0.5
            if q_probe <= 0:
                q_probe = float(fatal.get("physical_upper_q_w") or 1) * 0.5
            request, _, _ = build_task172_request_for_q(
                q_probe,
                support=replay["support"],
                tube_upstream=replay["tube_upstream"],
                shell_physical_left=replay["shell_physical_left"],
                provider=replay["provider"],
                shell_authority=replay["shell_authority"],
            )
            capture["q_probe_w"] = q_probe
            capture["comparison"] = compare_same_request_production_vs_frozen_trf(request, provider)
            capture["replayed_outer_iteration"] = replay["outer_iteration"]
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        t173_service._solve_cell = native
        reset_experimental_thermal_boundary(tok)

    payload = {
        "TASK_ID": "V08_03_NUMERICAL_CLOSURE_AND_RATING_ACCEPTANCE",
        "candidate_id": CANDIDATE_ID,
        "fatal_cell_fixture": str(FIXTURE.relative_to(_REPO)),
        **capture,
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
