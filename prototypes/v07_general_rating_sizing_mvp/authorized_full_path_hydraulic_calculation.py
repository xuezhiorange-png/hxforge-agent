"""Authorized full-path hydraulic pressure loss calculation (R26G)."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.tube_side_local_loss.computation import (
    compute_local_loss_component,
)
from hexagent.properties.base import FluidIdentifier
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import CandidateSelectionRecord
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_dp_breakdown import (
    build_hydraulic_dp_breakdown,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_completeness import (
    assess_hydraulic_path_completeness,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    EngineeringHydraulicPathInputV1,
    HydraulicPathComponentV1,
    resolved_reference_flow_area_m2,
    validate_path_input_binding,
)

_TASK_ID = "V07_R26G_AUTHORIZED_FULL_PATH_HYDRAULIC_CALCULATION"


def _dec(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _resolve_density_kg_m3(
    *,
    case: EngineeringCase,
    component: HydraulicPathComponentV1,
    provider: CoolPropProvider,
) -> tuple[Decimal | None, str | None]:
    source = component.fluid_density_source
    if source.kind == "CASE_SIDE_INLET":
        side = case.tube_side if source.fluid_role == "TUBE_SIDE" else case.shell_side
        temperature_k = Decimal(str(side.inlet_temperature_k))
        pressure_pa = Decimal(str(side.inlet_pressure_pa))
    else:
        if source.temperature_k is None or source.pressure_pa is None:
            return None, "COOLPROP_TP missing temperature_k or pressure_pa"
        temperature_k = source.temperature_k
        pressure_pa = source.pressure_pa
    try:
        state = provider.state_tp(
            FluidIdentifier("Water", "HEOS"),
            float(temperature_k),
            float(pressure_pa),
        )
    except Exception as exc:  # CoolProp domain errors are provider-specific
        return None, f"CoolProp density failed: {exc}"
    phase_name = getattr(state.phase, "value", str(state.phase)).lower()
    if "liquid" not in phase_name:
        return None, f"non-liquid phase at T={temperature_k} P={pressure_pa}"
    return Decimal(str(state.density_kg_m3)), None


def _compute_component_row(
    *,
    case: EngineeringCase,
    component: HydraulicPathComponentV1,
    provider: CoolPropProvider,
) -> dict[str, Any]:
    density, density_error = _resolve_density_kg_m3(case=case, component=component, provider=provider)
    if density is None:
        return {
            "component_id": component.component_id,
            "side": component.side,
            "component_type": component.component_type,
            "status": "BLOCKED",
            "blocker": density_error,
            "dp_pa": None,
        }
    ref_area = resolved_reference_flow_area_m2(component)
    try:
        _velocity, _single, component_pa = compute_local_loss_component(
            density_kg_m3=density,
            mass_flow_rate_kg_s=component.mass_flow_kg_s,
            reference_flow_area_m2=ref_area,
            loss_coefficient=component.loss_coefficient,
            multiplicity=component.multiplicity,
        )
    except Exception as exc:
        return {
            "component_id": component.component_id,
            "side": component.side,
            "component_type": component.component_type,
            "status": "BLOCKED",
            "blocker": str(exc),
            "dp_pa": None,
        }
    return {
        "component_id": component.component_id,
        "side": component.side,
        "component_type": component.component_type,
        "status": "COMPUTED",
        "reference_flow_area_m2": str(ref_area),
        "mass_flow_kg_s": str(component.mass_flow_kg_s),
        "fluid_density_kg_m3": str(density),
        "loss_coefficient": str(component.loss_coefficient),
        "loss_coefficient_convention": component.loss_coefficient_convention,
        "coefficient_source_id": component.coefficient_source_id,
        "engineering_input_status": component.engineering_input_status,
        "dp_pa": str(component_pa),
    }


def _sum_component_dp(rows: list[dict[str, Any]]) -> Decimal | None:
    total = Decimal("0")
    for row in rows:
        if row.get("status") != "COMPUTED" or row.get("dp_pa") is None:
            return None
        total += Decimal(str(row["dp_pa"]))
    return total


def run_authorized_full_path_hydraulic_calculation(
    *,
    case: EngineeringCase,
    path_input: EngineeringHydraulicPathInputV1,
    record: CandidateSelectionRecord,
    postpass: dict[str, Any] | None,
) -> dict[str, Any]:
    binding_errors = validate_path_input_binding(path_input, case=case, record=record)
    completeness = assess_hydraulic_path_completeness(path_input)
    provider = CoolPropProvider()

    tube_rows = [
        _compute_component_row(case=case, component=component, provider=provider)
        for component in path_input.tube_side_components
    ]
    shell_external_rows = [
        _compute_component_row(case=case, component=component, provider=provider)
        for component in path_input.shell_external_components
    ]

    exp = (postpass or {}).get("experimental_transitional_tube_hydraulic") or {}
    partial_breakdown = build_hydraulic_dp_breakdown(postpass, case=case) if postpass else {}
    tube_friction = _dec(exp.get("tube_friction_dp_pa"))
    if tube_friction is None:
        tube_friction = _dec(partial_breakdown.get("TUBE_FRICTION_DP_PA"))
    if tube_friction is None and postpass:
        tube_total_partial = _dec(postpass.get("recalculated_tube_dp_pa"))
        tube_local_partial = _dec(exp.get("tube_local_loss_dp_pa"))
        if tube_local_partial is None:
            tube_local_partial = _dec(partial_breakdown.get("TUBE_LOCAL_LOSS_DP_PA"))
        if tube_total_partial is not None and tube_local_partial is not None:
            tube_friction = tube_total_partial - tube_local_partial

    shell_parts = (postpass or {}).get("shell_dp_components_pa") or {}
    shell_bd_internal = _dec(shell_parts.get("total"))
    if shell_bd_internal is None:
        shell_bd_internal = _dec(partial_breakdown.get("SHELL_INTERNAL_DP_PA"))
    if shell_bd_internal is None and postpass:
        shell_bd_internal = _dec(postpass.get("recalculated_shell_dp_pa"))

    tube_local_full = _sum_component_dp(tube_rows)
    shell_external_local = _sum_component_dp(shell_external_rows)

    tube_full = None
    shell_full = None
    tube_full_status = "BLOCKED"
    shell_full_status = "BLOCKED"
    blockers: list[str] = list(binding_errors)

    if binding_errors:
        overall_status = "BLOCKED_BINDING"
    elif completeness["path_completeness_status"] in (
        "INCOMPLETE_COMPONENT_COVERAGE",
        "INCOMPLETE_SEQUENCE",
        "PARTIAL_DECLARED",
    ):
        overall_status = "BLOCKED_INCOMPLETE_INPUT"
        blockers.append(completeness["path_completeness_status"])
    else:
        overall_status = "COMPUTED"
        if tube_friction is not None and tube_local_full is not None:
            tube_full = tube_friction + tube_local_full
            tube_full_status = "COMPUTED"
        else:
            tube_full_status = "ENGINEERING_GEOMETRY_INPUT_REQUIRED"
            blockers.append("tube friction or local path incomplete")
        if shell_bd_internal is not None and shell_external_local is not None:
            shell_full = shell_bd_internal + shell_external_local
            shell_full_status = "COMPUTED"
        else:
            shell_full_status = "ENGINEERING_GEOMETRY_INPUT_REQUIRED"
            blockers.append("shell Bell–Delaware or external path incomplete")
        if tube_full_status != "COMPUTED" or shell_full_status != "COMPUTED":
            overall_status = "BLOCKED_INCOMPLETE_INPUT"

    demo_only = completeness.get("demonstration_input_present")
    production = completeness.get("authorized_input_present") and not demo_only

    return {
        "TASK_ID": _TASK_ID,
        "status": overall_status,
        "blockers": blockers,
        "binding_validation_errors": binding_errors,
        "path_completeness": completeness,
        "TUBE_INTERNAL_FRICTION_DP_PA": str(tube_friction) if tube_friction is not None else None,
        "TUBE_LOCAL_DP_PA": str(tube_local_full) if tube_local_full is not None else None,
        "TUBE_FULL_PATH_TOTAL_DP_PA": str(tube_full) if tube_full is not None else None,
        "TUBE_FULL_PATH_STATUS": tube_full_status,
        "SHELL_BELL_DELAWARE_INTERNAL_DP_PA": (
            str(shell_bd_internal) if shell_bd_internal is not None else None
        ),
        "SHELL_EXTERNAL_LOCAL_DP_PA": (
            str(shell_external_local) if shell_external_local is not None else None
        ),
        "SHELL_FULL_PATH_TOTAL_DP_PA": str(shell_full) if shell_full is not None else None,
        "SHELL_FULL_PATH_STATUS": shell_full_status,
        "TUBE_DP_COMPONENTS": tube_rows,
        "SHELL_DP_COMPONENTS": shell_external_rows,
        "PRODUCTION_DESIGN_APPROVED": False,
        "ENGINEERING_SIZING_ELIGIBILITY": (
            "DEMONSTRATION_ONLY_NOT_ENGINEERING_SIZING_ELIGIBLE"
            if not production
            else "AUTHORIZED_INPUT_NOT_SIZING_APPROVED"
        ),
        "reconciliation": {
            "tube_full_equals_friction_plus_local": (
                tube_full is not None
                and tube_friction is not None
                and tube_local_full is not None
                and abs(tube_full - (tube_friction + tube_local_full)) <= Decimal("0.01")
            ),
            "shell_full_equals_bd_plus_external": (
                shell_full is not None
                and shell_bd_internal is not None
                and shell_external_local is not None
                and abs(shell_full - (shell_bd_internal + shell_external_local)) <= Decimal("0.01")
            ),
        },
    }
