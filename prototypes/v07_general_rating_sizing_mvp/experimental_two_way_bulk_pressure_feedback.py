"""Experimental two-way bulk pressure feedback between live hydraulics and Task173 rating (R22)."""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    REVIEWED_MAX_PRESSURE_PA,
    REVIEWED_MIN_PRESSURE_PA,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import REFERENCE_PRESSURE_PA
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    bind_task172_pressure_observations,
    drain_task172_pressure_observations,
    reset_task172_pressure_observations,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.live_thermal_state_hydraulic_postpass import (
    postpass_from_mesh_row,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    NativeCellContext,
    run_mesh_numeric_with_profile,
)

COUPLING_SCOPE = "EXPERIMENTAL_TWO_WAY_BULK_PRESSURE_FEEDBACK"
THERMAL_PRESSURE_CONTEXT_STATUS_ACTIVE = "EXPERIMENTAL_BULK_PROPERTY_PRESSURE_BOUND"
MAX_COUPLED_ITERATIONS = 5
MAX_COUPLED_WALL_SECONDS = 900.0
DP_CONVERGENCE_PA = Decimal("0.05")
DUTY_CONVERGENCE_W = Decimal("0.05")
BULK_PRESSURE_CONVERGENCE_PA = Decimal("0.05")
ENERGY_BALANCE_TOLERANCE_W = Decimal("1e-3")


def experimental_two_way_bulk_pressure_feedback_enabled(case: EngineeringCase) -> bool:
    return bool(getattr(case, "experimental_two_way_bulk_pressure_feedback", False))


def validate_two_way_activation(case: EngineeringCase) -> None:
    if not experimental_two_way_bulk_pressure_feedback_enabled(case):
        return
    if not getattr(case, "experimental_live_thermal_hydraulic_postpass", False):
        raise ValueError(
            "experimental_two_way_bulk_pressure_feedback requires "
            "experimental_live_thermal_hydraulic_postpass=true"
        )


def _bulk_mean_pressure(inlet_pa: Decimal, outlet_pa: Decimal) -> Decimal:
    return (inlet_pa + outlet_pa) / Decimal(2)


def _mesh_row_from_run(
    mesh: dict[str, Any],
    profile: dict[str, Any],
    obs: Any,
) -> dict[str, Any]:
    row = {**mesh, "solver_performance_profile": profile}
    if obs is not None:
        row["tube_outlet_temperature_k"] = str(obs.tube_outlet_temperature_k)
        row["shell_outlet_temperature_k"] = str(obs.shell_outlet_temperature_k)
    return row


def _iteration_record(
    *,
    index: int,
    tube_bulk_pa: Decimal,
    shell_bulk_pa: Decimal,
    mesh: dict[str, Any],
    postpass: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "iteration_index": index,
        "tube_bulk_property_pressure_pa": str(tube_bulk_pa),
        "shell_bulk_property_pressure_pa": str(shell_bulk_pa),
        "total_duty_w": mesh.get("total_duty_w"),
        "tube_outlet_temperature_k": mesh.get("tube_outlet_temperature_k"),
        "shell_outlet_temperature_k": mesh.get("shell_outlet_temperature_k"),
        "energy_balance_residual_w": mesh.get("energy_balance_residual_w"),
        "task172_local_evaluation_count": mesh.get("task172_local_evaluation_count"),
        "wall_seconds": mesh.get("wall_seconds"),
        "recalculated_tube_dp_pa": (postpass or {}).get("recalculated_tube_dp_pa"),
        "recalculated_shell_dp_pa": (postpass or {}).get("recalculated_shell_dp_pa"),
        "tube_outlet_pressure_pa": (postpass or {}).get("tube_outlet_pressure_pa"),
        "shell_outlet_pressure_pa": (postpass or {}).get("shell_outlet_pressure_pa"),
    }


def _pressure_in_reviewed_domain(pressure_pa: Decimal) -> bool:
    return REVIEWED_MIN_PRESSURE_PA <= pressure_pa <= REVIEWED_MAX_PRESSURE_PA


def _energy_balance_status(mesh_row: dict[str, Any]) -> str:
    residual = abs(Decimal(str(mesh_row.get("energy_balance_residual_w", "0"))))
    if residual <= ENERGY_BALANCE_TOLERANCE_W:
        return "WITHIN_MESH_TOLERANCE"
    return "MESH_RESIDUAL_NONZERO"


def _postpass_hydraulic_ok(postpass: dict[str, Any]) -> tuple[bool, str]:
    if postpass.get("hydraulic_constraint_status") == "BLOCKED":
        return False, "HYDRAULIC_CONSTRAINT_BLOCKED"
    tube_status = postpass.get("tube_hydraulic_recompute_status")
    if tube_status not in {"SUCCESS", "EXPERIMENTAL_TRANSITIONAL_SUCCESS"}:
        return False, f"TUBE_HYDRAULIC_{tube_status}"
    if postpass.get("shell_hydraulic_recompute_status") != "SUCCESS":
        return False, f"SHELL_HYDRAULIC_{postpass.get('shell_hydraulic_recompute_status')}"
    if postpass.get("task174_style_outlet_pressure_window_pass") is False:
        return False, "OUTLET_PRESSURE_WINDOW_FAILED"
    if postpass.get("recalculated_tube_dp_pa") is None:
        return False, "MISSING_TUBE_DP"
    if postpass.get("recalculated_shell_dp_pa") is None:
        return False, "MISSING_SHELL_DP"
    return True, "OK"


def _canonical_pressure_decimal(value: str) -> Decimal:
    """Align with Task173 CoolProp float round-trip for binding checks."""
    return Decimal(str(float(Decimal(str(value)))))


def _decimal_equal(left: str | None, right: str | None) -> bool:
    if left is None or right is None:
        return False
    return _canonical_pressure_decimal(left) == _canonical_pressure_decimal(right)


def _task172_pressure_binding_ok(observations: list[dict[str, str]]) -> tuple[bool, str]:
    if not observations:
        return False, "NO_TASK172_OBSERVATIONS"
    sample = observations[-1]
    for side in ("tube", "shell"):
        thermo_key = f"task173_{side}_thermo_pressure_pa"
        request_key = f"task172_{side}_local_pressure_pa"
        eval_key = f"task173_{side}_property_evaluation_pressure_pa"
        if not _decimal_equal(sample.get(thermo_key), sample.get(request_key)):
            return False, f"{side.upper()}_THERMO_REQUEST_MISMATCH"
        if not _decimal_equal(sample.get(thermo_key), sample.get(eval_key)):
            return False, f"{side.upper()}_THERMO_EVAL_MISMATCH"
    return True, "TASK172_PROPERTY_PRESSURE_CONSISTENT"


def evaluate_coupled_fixed_point_residual(
    *,
    tube_bulk_pa: Decimal,
    shell_bulk_pa: Decimal,
    tube_outlet_pa: Decimal,
    shell_outlet_pa: Decimal,
    inlet_pa: Decimal,
) -> tuple[Decimal, Decimal]:
    target_tube = _bulk_mean_pressure(inlet_pa, tube_outlet_pa)
    target_shell = _bulk_mean_pressure(inlet_pa, shell_outlet_pa)
    return abs(target_tube - tube_bulk_pa), abs(target_shell - shell_bulk_pa)


def iteration_satisfies_convergence_gates(
    *,
    mesh_row: dict[str, Any],
    postpass: dict[str, Any],
    tube_bulk_pa: Decimal,
    shell_bulk_pa: Decimal,
    inlet_pa: Decimal,
    prev_duty: Decimal | None,
    prev_tube_dp: Decimal | None,
    prev_shell_dp: Decimal | None,
    task172_observations: list[dict[str, str]],
) -> tuple[bool, str, str]:
    """Return (converged, coupled_residual_status, detail)."""
    if mesh_row.get("status") != "NUMERIC_VALID":
        return False, "RATING_NOT_NUMERIC_VALID", "mesh_status"
    if _energy_balance_status(mesh_row) != "WITHIN_MESH_TOLERANCE":
        return False, "ENERGY_BALANCE_NOT_SATISFIED", "energy_balance"
    hydraulic_ok, hydraulic_reason = _postpass_hydraulic_ok(postpass)
    if not hydraulic_ok:
        return False, "HYDRAULIC_POSTPASS_NOT_VALID", hydraulic_reason
    binding_ok, binding_reason = _task172_pressure_binding_ok(task172_observations)
    if not binding_ok:
        return False, "TASK172_PRESSURE_BINDING_FAILED", binding_reason

    duty = Decimal(str(mesh_row["total_duty_w"]))
    tube_dp = Decimal(str(postpass["recalculated_tube_dp_pa"]))
    shell_dp = Decimal(str(postpass["recalculated_shell_dp_pa"]))
    tube_out_p = Decimal(str(postpass["tube_outlet_pressure_pa"]))
    shell_out_p = Decimal(str(postpass["shell_outlet_pressure_pa"]))
    if not _pressure_in_reviewed_domain(tube_out_p):
        return False, "OUTLET_PRESSURE_OUT_OF_DOMAIN", "outlet_pressure"
    if not _pressure_in_reviewed_domain(shell_out_p):
        return False, "OUTLET_PRESSURE_OUT_OF_DOMAIN", "outlet_pressure"

    tube_residual, shell_residual = evaluate_coupled_fixed_point_residual(
        tube_bulk_pa=tube_bulk_pa,
        shell_bulk_pa=shell_bulk_pa,
        tube_outlet_pa=tube_out_p,
        shell_outlet_pa=shell_out_p,
        inlet_pa=inlet_pa,
    )
    if tube_residual > BULK_PRESSURE_CONVERGENCE_PA:
        return (
            False,
            "BULK_PRESSURE_FIXED_POINT_NOT_SATISFIED",
            f"tube_residual={tube_residual},shell_residual={shell_residual}",
        )
    if shell_residual > BULK_PRESSURE_CONVERGENCE_PA:
        return (
            False,
            "BULK_PRESSURE_FIXED_POINT_NOT_SATISFIED",
            f"tube_residual={tube_residual},shell_residual={shell_residual}",
        )

    if prev_duty is None or prev_tube_dp is None or prev_shell_dp is None:
        return False, "FIRST_ITERATION_NOT_CONVERGED", "need_prior_iteration"

    if (
        abs(duty - prev_duty) > DUTY_CONVERGENCE_W
        or abs(tube_dp - prev_tube_dp) > DP_CONVERGENCE_PA
        or abs(shell_dp - prev_shell_dp) > DP_CONVERGENCE_PA
    ):
        return False, "DUTY_OR_DP_NOT_STATIONARY", "duty_or_dp"

    return True, "COUPLED_FIXED_POINT_SATISFIED", "all_gates_passed"


def run_two_way_bulk_pressure_coupled_rating(
    case: EngineeringCase,
    native: NativeCellContext,
    *,
    mesh_level: int,
    enable_ephemeral_tp_cache: bool = False,
) -> dict[str, Any]:
    """Run coupled thermal–hydraulic iterations with side-specific bulk property pressures."""
    validate_two_way_activation(case)
    t0 = time.perf_counter()
    inlet_pa = REFERENCE_PRESSURE_PA
    tube_bulk = inlet_pa
    shell_bulk = inlet_pa
    history: list[dict[str, Any]] = []
    one_way_baseline: dict[str, Any] | None = None
    last_mesh: dict[str, Any] | None = None
    last_postpass: dict[str, Any] | None = None
    prev_duty: Decimal | None = None
    prev_tube_dp: Decimal | None = None
    prev_shell_dp: Decimal | None = None
    coupled_status = "NOT_STARTED"
    pressure_residual_status = "NOT_EVALUATED"
    coupled_residual_status = "NOT_EVALUATED"
    energy_balance_status = "NOT_EVALUATED"
    task172_pressure_consistency = "NOT_EVALUATED"
    obs_token = bind_task172_pressure_observations()
    try:
        for index in range(MAX_COUPLED_ITERATIONS):
            if time.perf_counter() - t0 > MAX_COUPLED_WALL_SECONDS:
                coupled_status = "BLOCKED_COUPLED_TIME_BUDGET"
                break
            if not _pressure_in_reviewed_domain(tube_bulk) or not _pressure_in_reviewed_domain(
                shell_bulk
            ):
                coupled_status = "BLOCKED_PRESSURE_APPLICABILITY_DOMAIN"
                pressure_residual_status = "OUT_OF_REVIEWED_DOMAIN"
                break

            mesh, profile, obs = run_mesh_numeric_with_profile(
                native,
                subdivisions=mesh_level,
                case=case,
                enable_live_thermal_boundary=True,
                enable_ephemeral_tp_cache=enable_ephemeral_tp_cache,
                tube_property_evaluation_pressure_pa=tube_bulk,
                shell_property_evaluation_pressure_pa=shell_bulk,
            )
            mesh_row = _mesh_row_from_run(mesh, profile, obs)
            if mesh_row.get("status") != "NUMERIC_VALID":
                coupled_status = "BLOCKED_THERMAL_RATING"
                break

            postpass = postpass_from_mesh_row(
                case,
                candidate_id=native.candidate_id,
                mesh=mesh_row,
                native_reference_tube_dp=native.modeled_tube_side_pressure_drop_pa,
                native_reference_shell_dp=native.modeled_shell_side_pressure_drop_pa,
                tube_property_evaluation_pressure_pa=tube_bulk,
                shell_property_evaluation_pressure_pa=shell_bulk,
            )
            if postpass is None:
                coupled_status = "BLOCKED_HYDRAULIC_POSTPASS"
                break

            task172_observations = drain_task172_pressure_observations()
            binding_ok, binding_label = _task172_pressure_binding_ok(task172_observations)
            if binding_ok:
                task172_pressure_consistency = binding_label
            else:
                task172_pressure_consistency = binding_label
                coupled_status = "BLOCKED_TASK172_PRESSURE_BINDING"
                coupled_residual_status = binding_label
                break

            record = _iteration_record(
                index=index,
                tube_bulk_pa=tube_bulk,
                shell_bulk_pa=shell_bulk,
                mesh=mesh_row,
                postpass=postpass,
            )
            record["task172_pressure_observations"] = task172_observations
            history.append(record)
            if index == 0:
                one_way_baseline = {
                    "comparison_label": "ONE_WAY_POSTPASS_AT_REFERENCE_BULK_PRESSURE",
                    **record,
                }

            duty = Decimal(str(mesh_row["total_duty_w"]))
            tube_dp = Decimal(str(postpass["recalculated_tube_dp_pa"]))
            shell_dp = Decimal(str(postpass["recalculated_shell_dp_pa"]))
            tube_out_p = Decimal(str(postpass["tube_outlet_pressure_pa"]))
            shell_out_p = Decimal(str(postpass["shell_outlet_pressure_pa"]))
            energy_balance_status = _energy_balance_status(mesh_row)

            converged, coupled_residual_status, _detail = iteration_satisfies_convergence_gates(
                mesh_row=mesh_row,
                postpass=postpass,
                tube_bulk_pa=tube_bulk,
                shell_bulk_pa=shell_bulk,
                inlet_pa=inlet_pa,
                prev_duty=prev_duty,
                prev_tube_dp=prev_tube_dp,
                prev_shell_dp=prev_shell_dp,
                task172_observations=task172_observations,
            )
            if converged:
                coupled_status = "COUPLED_CONVERGED"
                pressure_residual_status = "BULK_PRESSURE_FIXED_POINT_SATISFIED"
                last_mesh, last_postpass = mesh_row, postpass
                break

            if not _pressure_in_reviewed_domain(tube_out_p) or not _pressure_in_reviewed_domain(
                shell_out_p
            ):
                coupled_status = "BLOCKED_OUTLET_PRESSURE_DOMAIN"
                pressure_residual_status = "OUTLET_OUT_OF_REVIEWED_DOMAIN"
                coupled_residual_status = "OUTLET_OUT_OF_REVIEWED_DOMAIN"
                break

            prev_duty, prev_tube_dp, prev_shell_dp = duty, tube_dp, shell_dp
            last_mesh, last_postpass = mesh_row, postpass

            tube_bulk = _bulk_mean_pressure(inlet_pa, tube_out_p)
            shell_bulk = _bulk_mean_pressure(inlet_pa, shell_out_p)

            if index == MAX_COUPLED_ITERATIONS - 1:
                coupled_status = "COUPLED_NOT_CONVERGED_WITHIN_ITERATION_BUDGET"
                pressure_residual_status = "MAX_ITERATIONS_REACHED"
                if coupled_residual_status == "NOT_EVALUATED":
                    coupled_residual_status = "MAX_ITERATIONS_REACHED"
    finally:
        reset_task172_pressure_observations(obs_token)

    total_wall = round(time.perf_counter() - t0, 3)
    if coupled_status == "NOT_STARTED":
        coupled_status = "BLOCKED_NO_ITERATION"

    return {
        "schema_version": "hxforge.experimental-two-way-bulk-pressure-feedback.v1",
        "coupling_scope": COUPLING_SCOPE,
        "THERMAL_PRESSURE_CONTEXT_STATUS": THERMAL_PRESSURE_CONTEXT_STATUS_ACTIVE,
        "TASK172_PRESSURE_BINDING_STATUS": (
            "SIDE_BULK_PRESSURE_MATCHES_TASK173_PROPERTY_EVALUATION"
        ),
        "TASK173_PRESSURE_REEVALUATION_STATUS": (
            "RE_RATED_EACH_ITERATION_WITH_UPDATED_BULK_PRESSURE"
        ),
        "REAL_THERMAL_ITERATION_COUNT": len(history),
        "iteration_history": history,
        "one_way_baseline": one_way_baseline,
        "COUPLED_ITERATION_STATUS": coupled_status,
        "ENERGY_BALANCE_STATUS": energy_balance_status,
        "PRESSURE_RESIDUAL_STATUS": pressure_residual_status,
        "COUPLED_RESIDUAL_STATUS": coupled_residual_status,
        "TASK172_PROPERTY_PRESSURE_CONSISTENCY": task172_pressure_consistency,
        "convergence_criteria": {
            "max_iterations": MAX_COUPLED_ITERATIONS,
            "max_wall_seconds": MAX_COUPLED_WALL_SECONDS,
            "duty_tolerance_w": str(DUTY_CONVERGENCE_W),
            "dp_tolerance_pa": str(DP_CONVERGENCE_PA),
            "bulk_pressure_tolerance_pa": str(BULK_PRESSURE_CONVERGENCE_PA),
            "bulk_pressure_definition": "P_bulk=(P_inlet+P_outlet)/2 per side",
        },
        "final_mesh": last_mesh,
        "final_live_thermal_state_hydraulic_postpass": last_postpass,
        "total_wall_seconds": total_wall,
    }
