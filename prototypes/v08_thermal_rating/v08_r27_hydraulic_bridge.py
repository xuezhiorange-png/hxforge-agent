"""Bridge V08 candidate bindings to V07 R27C nozzle / full-path hydraulic inputs."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.bell_delaware.models import (
    ApplicabilityStatus,
    Task166BlockedResult,
    Task166Result,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    candidate_rating_request_hash,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import Task174SuccessResult
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import CandidateSelectionRecord
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_physical_consistency import (
    _outlet_domain_ok,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_input import (
    CandidateGenerationConstraints,
    FluidSideSpec,
    GeneralEngineeringCaseV2,
    SolverBudgetSpec,
)
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.discrete_space import (
    DEFAULT_V08_DISCRETE_SPACE_PATH,
    load_v08_discrete_space,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import CandidateRatingBindings


def _mass_flow_str(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.000001"))
    text = format(quantized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return f"{text}.000000" if "." not in text else text


def build_engineering_case_v2_from_v08(
    normalized: NormalizedUserDesignCase,
) -> GeneralEngineeringCaseV2:
    space = load_v08_discrete_space(DEFAULT_V08_DISCRETE_SPACE_PATH)
    shells = space.shell_inside_diameters_m
    return GeneralEngineeringCaseV2(
        engineering_case_id=normalized.engineering_case_id,
        exchanger_type="SHELL_AND_TUBE_FIXED_TUBESHEET_SINGLE_PHASE",
        tube_side=FluidSideSpec(
            fluid="PURE_ORDINARY_WATER",
            inlet_temperature_k=normalized.tube_side.inlet_temperature_k,
            inlet_pressure_pa=normalized.tube_side.inlet_pressure_pa,
            mass_flow_kg_s=_mass_flow_str(normalized.tube_side.mass_flow_kg_s),
        ),
        shell_side=FluidSideSpec(
            fluid="PURE_ORDINARY_WATER",
            inlet_temperature_k=normalized.shell_side.inlet_temperature_k,
            inlet_pressure_pa=normalized.shell_side.inlet_pressure_pa,
            mass_flow_kg_s=_mass_flow_str(normalized.shell_side.mass_flow_kg_s),
        ),
        target_duty_w=normalized.target_duty_w,
        max_tube_side_pressure_drop_pa=normalized.max_tube_side_pressure_drop_pa,
        max_shell_side_pressure_drop_pa=normalized.max_shell_side_pressure_drop_pa,
        candidate_constraints=CandidateGenerationConstraints(
            shell_inside_diameter_m=shells[0],
            shell_inside_diameters_m=shells,
            tube_outer_diameter_m=space.tube_outer_diameter_m,
            tube_wall_thickness_m=space.tube_wall_thickness_m,
            tube_pitch_m=space.tube_pitch_m,
            tube_lengths_m=space.tube_lengths_m,
            baffle_spacings_m=space.baffle_spacings_m,
            baffle_count=space.tube_baffle_ladder[0].baffle_count,
            tube_pass_count=space.tube_pass_counts[0],
        ),
        solver_budget=SolverBudgetSpec(),
        experimental_transitional_tube_hydraulic=True,
        experimental_live_thermal_hydraulic_postpass=True,
        experimental_variable_water_temperature=True,
        experimental_engineering_tube_local_loss=False,
        notes="V08-03 bridge for autonomous nozzle / full-path hydraulics (R27C reuse).",
    )


def candidate_selection_record_from_bindings(
    bindings: CandidateRatingBindings,
) -> CandidateSelectionRecord:
    raw = bindings.bundle.bundle
    t174 = bindings.rating_request.task174_result
    if not isinstance(t174, Task174SuccessResult):
        raise TypeError("Task174 VALIDATED result required for hydraulic bridge")
    candidate = bindings.bundle.candidate
    shell_d = bindings.bundle.shell_record.shell_inside_diameter_m
    return CandidateSelectionRecord(
        candidate_id=bindings.rating_request.candidate_id,
        candidate_hash=canonical_sha256(
            {
                "candidate_id": bindings.rating_request.candidate_id,
                "geometry_hash": bindings.geometry_projection_hash,
            }
        ),
        tube_length_m=str(candidate.tube_length_m),
        baffle_spacing_m=str(candidate.baffle_spacing_m),
        geometry_projection_hash=bindings.geometry_projection_hash,
        structural_admitted=True,
        task168_chain_status="VALID",
        task168_blocked_stage=None,
        task168_blocked_codes=(),
        task174_status="VALIDATED",
        rating_request_ready=True,
        rating_request_hash=candidate_rating_request_hash(bindings.rating_request),
        task171_result_hash=None,
        task174_result_hash=t174.result_hash,
        selected_for_rating=True,
        task173_rating_status="NOT_RUN",
        physical_tube_count=None,
        shell_inside_diameter_m=str(shell_d),
        task025_total_parallel_flow_area_m2=str(raw.task025_result.total_parallel_flow_area_m2),
    )


def task174_hydraulic_postpass_from_bindings(
    bindings: CandidateRatingBindings,
) -> dict[str, Any]:
    """Live Task174 decomposition for R27C friction separation (no Task029 total as friction)."""
    raw = bindings.bundle.bundle
    t174 = bindings.rating_request.task174_result
    if not isinstance(t174, Task174SuccessResult):
        raise TypeError("Task174 VALIDATED result required")
    t027 = raw.task027_result
    t029 = raw.task029_result
    friction = t027.straight_tube_friction_pressure_drop_pa
    tube_total = t029.modeled_total_tube_side_pressure_drop_pa
    local = tube_total - friction
    shell_total = t174.bell_total_shell_pressure_drop_pa
    tube_margin = bindings.normalized.max_tube_side_pressure_drop_pa - tube_total
    shell_margin = bindings.normalized.max_shell_side_pressure_drop_pa - shell_total
    norm = bindings.normalized
    tube_p_in = str(norm.tube_side.inlet_pressure_pa)
    shell_p_in = str(norm.shell_side.inlet_pressure_pa)
    tube_t = str(norm.tube_side.inlet_temperature_k)
    shell_t = str(norm.shell_side.inlet_temperature_k)

    t166 = raw.task166_result
    correlation_applicability = "NOT_EVALUATED"
    correlation_detail: list[str] = []
    if isinstance(t166, Task166Result) and t166.applicability is not None:
        if t166.applicability.status == ApplicabilityStatus.APPLICABLE:
            correlation_applicability = "APPLICABLE"
        else:
            correlation_applicability = f"NOT_{t166.applicability.status.value}"
            correlation_detail.append(str(t166.applicability.status.value))
    elif isinstance(t166, Task166BlockedResult):
        correlation_applicability = "NOT_EVALUATED"
        correlation_detail.append("TASK166_BLOCKED")
    else:
        correlation_detail.append("TASK166_MISSING")

    partial_satisfied = (
        tube_total <= bindings.normalized.max_tube_side_pressure_drop_pa
        and shell_total <= bindings.normalized.max_shell_side_pressure_drop_pa
    )
    hydraulic_constraint_status = "SATISFIED" if partial_satisfied else "NOT_SATISFIED"

    provider = CoolPropProvider()
    tube_out_ok, tube_out_reason = _outlet_domain_ok(
        provider,
        temperature_k=Decimal(tube_t),
        pressure_pa=t174.tube_outlet_pressure_pa,
    )
    shell_out_ok, shell_out_reason = _outlet_domain_ok(
        provider,
        temperature_k=Decimal(shell_t),
        pressure_pa=t174.shell_outlet_pressure_pa,
    )

    return {
        "correlation_applicability_status": correlation_applicability,
        "correlation_applicability_detail": tuple(correlation_detail),
        "tube_hydraulic_recompute_status": "EXPERIMENTAL_TRANSITIONAL_SUCCESS",
        "shell_hydraulic_recompute_status": "SUCCESS",
        "tube_inlet_pressure_pa": tube_p_in,
        "shell_inlet_pressure_pa": shell_p_in,
        "tube_outlet_pressure_pa": str(t174.tube_outlet_pressure_pa),
        "shell_outlet_pressure_pa": str(t174.shell_outlet_pressure_pa),
        "property_inputs": {
            "tube": {"bulk_pressure_pa": tube_p_in, "bulk_temperature_k": tube_t},
            "shell": {"bulk_pressure_pa": shell_p_in, "bulk_temperature_k": shell_t},
        },
        "coolprop_outlet_domain_checks": {
            "tube": {"ok": tube_out_ok, "detail": tube_out_reason},
            "shell": {"ok": shell_out_ok, "detail": shell_out_reason},
        },
        "experimental_transitional_tube_hydraulic": {
            "tube_friction_dp_pa": str(friction),
            "tube_local_loss_dp_pa": str(local),
            "total_tube_dp_pa": str(tube_total),
            "authority": "TASK027_STRAIGHT_TUBE_FRICTION_PLUS_TASK029_DECOMPOSITION",
        },
        "task027_straight_tube_friction_pressure_drop_pa": str(friction),
        "recalculated_tube_dp_pa": str(tube_total),
        "recalculated_shell_dp_pa": str(shell_total),
        "shell_dp_components_pa": {
            "total": str(shell_total),
            "central_crossflow": str(t174.bell_central_crossflow_contribution_pa),
            "window": str(t174.bell_window_contribution_pa),
            "inlet_end_zone": str(t174.bell_inlet_end_zone_contribution_pa),
            "outlet_end_zone": str(t174.bell_outlet_end_zone_contribution_pa),
        },
        "hydraulic_constraint_status": hydraulic_constraint_status,
        "tube_dp_margin_pa": str(tube_margin),
        "shell_dp_margin_pa": str(shell_margin),
        "upstream_hydraulic_authority_disclosure": (
            "V08 bridge binds live Task027/029/174 numeric outputs. "
            "R27B K coefficients remain ASSUMPTION_BASED until owner-verified engineering input."
        ),
        "task174_partial_model_disclosure": (
            "Tube total from Task029; shell Bell-Delaware from Task174. "
            "Full-path adds channel/transition/nozzle K scenarios (R27B)."
        ),
    }


__all__ = [
    "build_engineering_case_v2_from_v08",
    "candidate_selection_record_from_bindings",
    "task174_hydraulic_postpass_from_bindings",
]
