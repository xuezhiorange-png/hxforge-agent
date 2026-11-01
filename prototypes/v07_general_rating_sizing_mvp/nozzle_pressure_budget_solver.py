"""R27C: nozzle pressure-budget co-optimization with full-path verification."""

# ruff: noqa: E501

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any, Literal

from hexagent.exchangers.shell_tube.tube_side_local_loss.computation import (
    compute_local_loss_component,
)
from hexagent.properties.base import FluidIdentifier
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.authorized_full_path_hydraulic_calculation import (
    run_authorized_full_path_hydraulic_calculation,
)
from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    NOZZLE_VELOCITY_DESIGN_RULE,
)
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import CandidateSelectionRecord
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS,
    _assumption_channel_head_area_m2,
    _assumption_shell_transition_area_m2,
    build_r27b_assumption_based_hydraulic_path_input_v1,
    nozzle_flow_area_m2,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_physical_consistency import (
    assess_tube_internal_friction_separation,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_transitional_tube_hydraulic import (
    APPLICABILITY_STATUS as R20_TRANSITIONAL_APPLICABILITY,
)

SideKey = Literal["tube_side", "shell_side"]
LossScenarioKey = Literal["mid_band", "low_loss_sensitivity", "high_loss_sensitivity"]

_ALLOWED_APPLICABILITY = frozenset({"APPLICABLE", R20_TRANSITIONAL_APPLICABILITY})


def _velocity_bounds_m_s(
    velocity_rule: dict[str, Any] | None = None,
) -> tuple[float, float]:
    rule = velocity_rule or NOZZLE_VELOCITY_DESIGN_RULE
    return float(rule["velocity_m_s_min"]), float(rule["velocity_m_s_max"])


def _diameter_from_velocity_m(*, mass_flow_kg_s: float, rho: float, velocity_m_s: float) -> float:
    area = mass_flow_kg_s / (rho * velocity_m_s)
    return math.sqrt(4.0 * area / math.pi)


def _velocity_from_diameter_m(*, mass_flow_kg_s: float, rho: float, diameter_m: float) -> float:
    area = math.pi * (diameter_m / 2.0) ** 2
    return mass_flow_kg_s / (rho * area)


def _side_inlet_density_kg_m3(case: EngineeringCase, side: SideKey) -> float:
    spec = case.tube_side if side == "tube_side" else case.shell_side
    provider = CoolPropProvider()
    state = provider.state_tp(
        FluidIdentifier("Water", "HEOS"),
        float(spec.inlet_temperature_k),
        float(spec.inlet_pressure_pa),
    )
    return float(state.density_kg_m3)


def _tube_friction_pa(postpass: dict[str, Any]) -> Decimal | None:
    friction, _authority, blockers = assess_tube_internal_friction_separation(postpass, partial_breakdown={})
    if blockers or friction is None:
        return None
    return friction


def _shell_bd_internal_pa(postpass: dict[str, Any]) -> Decimal | None:
    parts = postpass.get("shell_dp_components_pa") or {}
    raw = parts.get("total") or postpass.get("recalculated_shell_dp_pa")
    if raw is None:
        return None
    return Decimal(str(raw))


def _component_dp_pa(
    *,
    rho: Decimal,
    mass_kg_s: Decimal,
    ref_area_m2: Decimal,
    loss_k: Decimal,
    multiplicity: int = 1,
) -> Decimal:
    _v, _single, total = compute_local_loss_component(
        density_kg_m3=rho,
        mass_flow_rate_kg_s=mass_kg_s,
        reference_flow_area_m2=ref_area_m2,
        loss_coefficient=loss_k,
        multiplicity=multiplicity,
    )
    return total


def _tube_path_dp_pa_for_nozzle_d(
    *,
    case: EngineeringCase,
    record: CandidateSelectionRecord,
    postpass: dict[str, Any],
    scenario: dict[str, Any],
    tube_nozzle_d_m: Decimal,
) -> tuple[Decimal | None, dict[str, Decimal | None]]:
    friction = _tube_friction_pa(postpass)
    if friction is None or record.task025_total_parallel_flow_area_m2 is None:
        return None, {}
    rho = Decimal(str(_side_inlet_density_kg_m3(case, "tube_side")))
    m = Decimal(str(case.tube_side.mass_flow_kg_s))
    bundle = Decimal(str(record.task025_total_parallel_flow_area_m2))
    channel = _assumption_channel_head_area_m2(
        bundle_parallel_flow_area_m2=bundle,
        nozzle_inside_diameter_m=tube_nozzle_d_m,
    )
    nozzle_area = nozzle_flow_area_m2(tube_nozzle_d_m)
    breakdown: dict[str, Decimal | None] = {
        "tube_internal_friction_dp_pa": friction,
        "tube_channel_head_dp_pa": _component_dp_pa(
            rho=rho,
            mass_kg_s=m,
            ref_area_m2=channel,
            loss_k=scenario["tube_channel_head_k"],
        ),
        "tube_bundle_entrance_dp_pa": _component_dp_pa(
            rho=rho,
            mass_kg_s=m,
            ref_area_m2=bundle,
            loss_k=scenario["tube_bundle_entrance_k"],
        ),
        "tube_bundle_exit_dp_pa": _component_dp_pa(
            rho=rho,
            mass_kg_s=m,
            ref_area_m2=bundle,
            loss_k=scenario["tube_bundle_exit_k"],
        ),
        "tube_nozzle_pair_dp_pa": _component_dp_pa(
            rho=rho,
            mass_kg_s=m,
            ref_area_m2=nozzle_area,
            loss_k=scenario["tube_nozzle_k"],
            multiplicity=2,
        ),
    }
    if any(v is None for v in breakdown.values()):
        return None, breakdown
    total = friction
    for key in (
        "tube_channel_head_dp_pa",
        "tube_bundle_entrance_dp_pa",
        "tube_bundle_exit_dp_pa",
        "tube_nozzle_pair_dp_pa",
    ):
        total += breakdown[key]  # type: ignore[operator]
    breakdown["tube_modeled_full_path_dp_pa"] = total
    return total, breakdown


def _shell_external_dp_pa_for_nozzle_d(
    *,
    case: EngineeringCase,
    record: CandidateSelectionRecord,
    scenario: dict[str, Any],
    shell_nozzle_d_m: Decimal,
) -> tuple[Decimal | None, dict[str, Decimal | None]]:
    rho = Decimal(str(_side_inlet_density_kg_m3(case, "shell_side")))
    m = Decimal(str(case.shell_side.mass_flow_kg_s))
    shell_id = Decimal(str(record.shell_inside_diameter_m or "0.56"))
    transition = _assumption_shell_transition_area_m2(shell_inside_diameter_m=shell_id)
    nozzle_area = nozzle_flow_area_m2(shell_nozzle_d_m)
    breakdown: dict[str, Decimal | None] = {
        "shell_inlet_transition_dp_pa": _component_dp_pa(
            rho=rho,
            mass_kg_s=m,
            ref_area_m2=transition,
            loss_k=scenario["shell_transition_k"],
        ),
        "shell_outlet_transition_dp_pa": _component_dp_pa(
            rho=rho,
            mass_kg_s=m,
            ref_area_m2=transition,
            loss_k=scenario["shell_transition_k"],
        ),
        "shell_nozzle_pair_dp_pa": _component_dp_pa(
            rho=rho,
            mass_kg_s=m,
            ref_area_m2=nozzle_area,
            loss_k=scenario["shell_nozzle_k"],
            multiplicity=2,
        ),
    }
    total = Decimal("0")
    for val in breakdown.values():
        if val is None:
            return None, breakdown
        total += val
    breakdown["shell_external_local_dp_pa"] = total
    return total, breakdown


def _geometry_fit_risk(
    *,
    record: CandidateSelectionRecord,
    tube_nozzle_d_m: float,
    shell_nozzle_d_m: float,
) -> dict[str, Any]:
    shell_id = float(record.shell_inside_diameter_m or "0.56")
    risks: list[str] = []
    if shell_nozzle_d_m > 0.85 * shell_id:
        risks.append("SHELL_NOZZLE_ID_APPROACHES_SHELL_INSIDE_DIAMETER")
    if tube_nozzle_d_m > 0.5:
        risks.append("TUBE_NOZZLE_ID_LARGE_RELATIVE_TO_TYPICAL_TUBESHEET_LAYOUT")
    return {
        "PRELIMINARY_GEOMETRY_NOT_MECHANICALLY_VERIFIED": True,
        "geometry_adaptation_risk_flags": risks,
        "disclosure": (
            "Nozzles sized hydraulically only; mechanical clearance, reinforcement, and "
            "tubesheet layout are not verified."
        ),
    }


def _verify_full_path(
    *,
    case: EngineeringCase,
    record: CandidateSelectionRecord,
    postpass: dict[str, Any],
    loss_scenario_key: LossScenarioKey,
    tube_nozzle_d_m: Decimal,
    shell_nozzle_d_m: Decimal,
) -> dict[str, Any]:
    path_input = build_r27b_assumption_based_hydraulic_path_input_v1(
        case=case,
        record=record,
        loss_scenario_key=loss_scenario_key,
        tube_nozzle_inside_diameter_m=tube_nozzle_d_m,
        shell_nozzle_inside_diameter_m=shell_nozzle_d_m,
    )
    return run_authorized_full_path_hydraulic_calculation(
        case=case,
        path_input=path_input,
        record=record,
        postpass=postpass,
    )


def _search_nozzle_d_in_velocity_band(
    *,
    case: EngineeringCase,
    side: SideKey,
    velocity_rule: dict[str, Any] | None,
) -> tuple[float, float]:
    v_min, v_max = _velocity_bounds_m_s(velocity_rule)
    rho = _side_inlet_density_kg_m3(case, side)
    m = float(case.tube_side.mass_flow_kg_s if side == "tube_side" else case.shell_side.mass_flow_kg_s)
    d_at_v_max = _diameter_from_velocity_m(mass_flow_kg_s=m, rho=rho, velocity_m_s=v_max)
    d_at_v_min = _diameter_from_velocity_m(mass_flow_kg_s=m, rho=rho, velocity_m_s=v_min)
    return min(d_at_v_max, d_at_v_min), max(d_at_v_max, d_at_v_min)


def _bisect_feasible_nozzle_d(
    *,
    case: EngineeringCase,
    record: CandidateSelectionRecord,
    postpass: dict[str, Any],
    scenario: dict[str, Any],
    side: SideKey,
    max_dp_pa: Decimal,
    fixed_other_side_dp: Decimal,
    other_side: SideKey,
    velocity_rule: dict[str, Any] | None,
    tube_nozzle_d_m: Decimal | None,
    shell_nozzle_d_m: Decimal | None,
) -> dict[str, Any]:
    """Find largest nozzle diameter (lowest velocity) within band satisfying side budget."""
    d_lo, d_hi = _search_nozzle_d_in_velocity_band(case=case, side=side, velocity_rule=velocity_rule)
    rho = _side_inlet_density_kg_m3(case, side)
    m = float(case.tube_side.mass_flow_kg_s if side == "tube_side" else case.shell_side.mass_flow_kg_s)
    v_min, v_max = _velocity_bounds_m_s(velocity_rule)

    def side_external_dp(d_m: float) -> Decimal | None:
        d_dec = Decimal(str(d_m))
        if side == "tube_side":
            tube_d = d_dec
            shell_d = shell_nozzle_d_m or Decimal(str(d_lo))
            total, _ = _tube_path_dp_pa_for_nozzle_d(
                case=case,
                record=record,
                postpass=postpass,
                scenario=scenario,
                tube_nozzle_d_m=tube_d,
            )
            return total
        shell_d = d_dec
        tube_d = tube_nozzle_d_m or Decimal(str(d_lo))
        ext, _ = _shell_external_dp_pa_for_nozzle_d(
            case=case,
            record=record,
            scenario=scenario,
            shell_nozzle_d_m=shell_d,
        )
        bd = _shell_bd_internal_pa(postpass)
        if ext is None or bd is None:
            return None
        return bd + ext

    dp_at_largest = side_external_dp(d_hi)
    dp_at_smallest = side_external_dp(d_lo)

    result: dict[str, Any] = {
        "side": side,
        "velocity_band_m_s": {"min": v_min, "max": v_max},
        "diameter_search_band_m": {"min": d_lo, "max": d_hi},
        "dp_at_max_diameter_pa": str(dp_at_largest) if dp_at_largest is not None else None,
        "dp_at_min_diameter_pa": str(dp_at_smallest) if dp_at_smallest is not None else None,
        "allowed_total_dp_pa": str(max_dp_pa),
    }

    if dp_at_largest is None:
        result["status"] = "BLOCKED_UPSTREAM"
        return result

    if dp_at_largest > max_dp_pa:
        # Even slowest allowed nozzle (largest D) exceeds budget
        result["status"] = "NO_FEASIBLE_WITHIN_DESIGN_BOUNDS"
        min_possible = dp_at_largest
        if side == "shell_side":
            result["failure_dominant_mechanism"] = (
                "SHELL_BUNDLE_INTERNAL_PLUS_FIXED_TRANSITIONS_DOMINATE"
                if min_possible > max_dp_pa
                else "SHELL_NOZZLE_BUDGET_EXHAUSTED"
            )
        else:
            result["failure_dominant_mechanism"] = "TUBE_BUNDLE_AND_FIXED_LOCALS_DOMINATE"
        # theoretical diameter for zero nozzle loss not implemented separately — report velocity at d_hi
        result["theoretical_at_band_max_diameter_m"] = d_hi
        result["velocity_at_band_max_diameter_m_s"] = _velocity_from_diameter_m(
            mass_flow_kg_s=m, rho=rho, diameter_m=d_hi
        )
        if dp_at_smallest > max_dp_pa:
            result["OUTSIDE_DESIGN_VELOCITY_RANGE"] = (
                "Would require velocity above band maximum to reduce losses further"
            )
        return result

    # Binary search smallest d (highest v) that still satisfies — prefer max margin => use largest feasible d
    lo, hi = d_lo, d_hi
    for _ in range(48):
        mid = (lo + hi) / 2.0
        dp_mid = side_external_dp(mid)
        if dp_mid is None:
            result["status"] = "BLOCKED_UPSTREAM"
            return result
        if dp_mid <= max_dp_pa:
            lo = mid
        else:
            hi = mid
    chosen_d = lo
    chosen_v = _velocity_from_diameter_m(mass_flow_kg_s=m, rho=rho, diameter_m=chosen_d)
    result["status"] = "FEASIBLE_WITHIN_DESIGN_BOUNDS"
    result["selected_inside_diameter_m"] = chosen_d
    result["selected_velocity_m_s"] = chosen_v
    result["modeled_side_total_dp_pa"] = str(side_external_dp(chosen_d))
    result["remaining_dp_margin_pa"] = str(max_dp_pa - side_external_dp(chosen_d))  # type: ignore[operator]
    return result


def cooptimize_nozzles_for_candidate_scenario(
    *,
    case: EngineeringCase,
    record: CandidateSelectionRecord,
    postpass: dict[str, Any],
    loss_scenario_key: LossScenarioKey,
    velocity_rule: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Solve tube/shell nozzle diameters in velocity band; verify with authorized full-path calc."""
    scenario = R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS[loss_scenario_key]
    max_tube = case.max_tube_side_pressure_drop_pa
    max_shell = case.max_shell_side_pressure_drop_pa

    applic = postpass.get("correlation_applicability_status")
    if applic not in _ALLOWED_APPLICABILITY:
        return {
            "loss_scenario_key": loss_scenario_key,
            "scenario_id": scenario["scenario_id"],
            "status": "BLOCKED_APPLICABILITY",
            "blocker": applic,
        }

    tube_search = _bisect_feasible_nozzle_d(
        case=case,
        record=record,
        postpass=postpass,
        scenario=scenario,
        side="tube_side",
        max_dp_pa=max_tube,
        fixed_other_side_dp=Decimal("0"),
        other_side="shell_side",
        velocity_rule=velocity_rule,
        tube_nozzle_d_m=None,
        shell_nozzle_d_m=None,
    )
    shell_search = _bisect_feasible_nozzle_d(
        case=case,
        record=record,
        postpass=postpass,
        scenario=scenario,
        side="shell_side",
        max_dp_pa=max_shell,
        fixed_other_side_dp=Decimal("0"),
        other_side="tube_side",
        velocity_rule=velocity_rule,
        tube_nozzle_d_m=(
            Decimal(str(tube_search["selected_inside_diameter_m"]))
            if tube_search.get("selected_inside_diameter_m") is not None
            else None
        ),
        shell_nozzle_d_m=None,
    )

    tube_d: Decimal | None = None
    shell_d: Decimal | None = None
    if tube_search.get("status") == "FEASIBLE_WITHIN_DESIGN_BOUNDS":
        tube_d = Decimal(str(tube_search["selected_inside_diameter_m"]))
    if shell_search.get("status") == "FEASIBLE_WITHIN_DESIGN_BOUNDS":
        shell_d = Decimal(str(shell_search["selected_inside_diameter_m"]))

    full_path: dict[str, Any] | None = None
    full_path_feasible = False
    if tube_d is not None and shell_d is not None:
        full_path = _verify_full_path(
            case=case,
            record=record,
            postpass=postpass,
            loss_scenario_key=loss_scenario_key,
            tube_nozzle_d_m=tube_d,
            shell_nozzle_d_m=shell_d,
        )
        full_path_feasible = (
            full_path.get("FULL_PATH_HYDRAULIC_STATUS") == "SATISFIED"
            and full_path.get("status") == "COMPUTED"
        )

    tube_breakdown: dict[str, Any] = {}
    shell_breakdown: dict[str, Any] = {}
    if tube_d is not None:
        _t, tube_breakdown = _tube_path_dp_pa_for_nozzle_d(
            case=case,
            record=record,
            postpass=postpass,
            scenario=scenario,
            tube_nozzle_d_m=tube_d,
        )
    if shell_d is not None:
        _s, shell_breakdown = _shell_external_dp_pa_for_nozzle_d(
            case=case,
            record=record,
            scenario=scenario,
            shell_nozzle_d_m=shell_d,
        )
        bd = _shell_bd_internal_pa(postpass)
        if bd is not None:
            shell_breakdown["shell_bell_delaware_internal_dp_pa"] = bd

    geo_risk: dict[str, Any] = {}
    if tube_d is not None and shell_d is not None:
        geo_risk = _geometry_fit_risk(
            record=record,
            tube_nozzle_d_m=float(tube_d),
            shell_nozzle_d_m=float(shell_d),
        )

    overall = "NO_FEASIBLE_WITHIN_DESIGN_BOUNDS"
    if tube_search.get("status") != "FEASIBLE_WITHIN_DESIGN_BOUNDS":
        overall = tube_search.get("status", overall)
    elif shell_search.get("status") != "FEASIBLE_WITHIN_DESIGN_BOUNDS":
        overall = shell_search.get("status", overall)
    elif full_path_feasible:
        overall = "FEASIBLE_FULL_PATH_VERIFIED"
    elif full_path is not None:
        overall = "NOZZLE_BAND_FEASIBLE_BUT_FULL_PATH_NOT_SATISFIED"

    return {
        "loss_scenario_key": loss_scenario_key,
        "scenario_id": scenario["scenario_id"],
        "ASSUMPTION_BASED": True,
        "input_authority": "ASSUMPTION_BASED",
        "disclosure": scenario["disclosure"],
        "tube_nozzle_solve": tube_search,
        "shell_nozzle_solve": shell_search,
        "selected_nozzles": {
            "tube_side_inside_diameter_m": float(tube_d) if tube_d else None,
            "shell_side_inside_diameter_m": float(shell_d) if shell_d else None,
            "tube_side_velocity_m_s": tube_search.get("selected_velocity_m_s"),
            "shell_side_velocity_m_s": shell_search.get("selected_velocity_m_s"),
        },
        "local_loss_breakdown_pa": {
            "tube_side": {k: str(v) for k, v in tube_breakdown.items()},
            "shell_side": {k: str(v) for k, v in shell_breakdown.items()},
        },
        "remaining_nozzle_budget_before_solve": {
            "tube_side_partial_margin_pa": postpass.get("tube_dp_margin_pa"),
            "shell_side_partial_margin_pa": postpass.get("shell_dp_margin_pa"),
            "disclosure": (
                "Partial-model margins are bundle-only; full-path nozzle budget is separate."
            ),
        },
        "full_path_hydraulic_verification": full_path,
        "full_path_feasible": full_path_feasible,
        "overall_scenario_status": overall,
        "geometry_adaptation": geo_risk,
    }
