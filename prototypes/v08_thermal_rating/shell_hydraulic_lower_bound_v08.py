"""Shell full-path Δp lower bounds and PROVEN infeasibility under R27B K scenarios."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    NOZZLE_VELOCITY_DESIGN_RULE,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS,
    build_r27b_assumption_based_hydraulic_path_input_v1,
    nozzle_flow_area_m2,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_physical_consistency import (
    validate_no_duplicate_local_loss_with_postpass,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    _component_dp_pa,
    _search_nozzle_d_in_velocity_band,
    _shell_external_dp_pa_for_nozzle_d,
    _side_inlet_density_kg_m3,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import CandidateRatingBindings
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import (
    build_engineering_case_v2_from_v08,
    candidate_selection_record_from_bindings,
    task174_hydraulic_postpass_from_bindings,
)

ScenarioKey = Literal["mid_band", "low_loss_sensitivity", "high_loss_sensitivity"]


@dataclass(frozen=True)
class ShellScenarioLowerBound:
    scenario_key: ScenarioKey
    shell_bell_internal_dp_pa: str
    shell_inlet_nozzle_dp_pa: str
    shell_outlet_nozzle_dp_pa: str
    shell_inlet_transition_dp_pa: str
    shell_outlet_transition_dp_pa: str
    shell_nozzle_pair_min_dp_pa: str
    shell_external_min_dp_pa: str
    remaining_internal_budget_pa: str
    shell_dp_limit_pa: str
    proven_hydraulic_infeasible_under_assumed_k: bool
    shell_full_path_dp_pa: str | None
    shell_dp_margin_pa: str | None
    shell_min_nozzle_diameter_m: str


@dataclass(frozen=True)
class ShellHydraulicLowerBoundReport:
    candidate_id: str
    geometry_projection_hash: str
    shell_dp_limit_pa: str
    scenarios: tuple[ShellScenarioLowerBound, ...]
    any_proven_infeasible: bool
    all_proven_infeasible: bool
    mid_remaining_internal_budget_pa: str
    high_remaining_internal_budget_pa: str
    bell_reduction_required_for_mid_feasibility_pa: str | None
    duplicate_dp_component_errors: tuple[str, ...]


def _single_nozzle_dp_pa(
    *,
    rho: Decimal,
    mass_kg_s: Decimal,
    nozzle_d_m: Decimal,
    loss_k: Decimal,
) -> Decimal:
    area = nozzle_flow_area_m2(nozzle_d_m)
    return _component_dp_pa(
        rho=rho,
        mass_kg_s=mass_kg_s,
        ref_area_m2=area,
        loss_k=loss_k,
        multiplicity=1,
    )


def _min_external_breakdown(
    *,
    case: Any,
    record: Any,
    scenario: dict[str, Any],
) -> dict[str, Decimal]:
    _d_min, d_max = _search_nozzle_d_in_velocity_band(
        case=case, side="shell_side", velocity_rule=NOZZLE_VELOCITY_DESIGN_RULE
    )
    shell_d = Decimal(str(d_max))
    ext, breakdown = _shell_external_dp_pa_for_nozzle_d(
        case=case,
        record=record,
        scenario=scenario,
        shell_nozzle_d_m=shell_d,
        include_nozzle_pair=True,
    )
    if ext is None or breakdown is None:
        raise RuntimeError("shell external min breakdown failed")
    rho = Decimal(str(_side_inlet_density_kg_m3(case, "shell_side")))
    m = Decimal(str(case.shell_side.mass_flow_kg_s))
    k = scenario["shell_nozzle_k"]
    inlet_noz = _single_nozzle_dp_pa(rho=rho, mass_kg_s=m, nozzle_d_m=shell_d, loss_k=k)
    outlet_noz = inlet_noz
    return {
        "shell_min_nozzle_diameter_m": shell_d,
        "shell_inlet_nozzle_dp_pa": inlet_noz,
        "shell_outlet_nozzle_dp_pa": outlet_noz,
        "shell_inlet_transition_dp_pa": breakdown["shell_inlet_transition_dp_pa"] or Decimal("0"),
        "shell_outlet_transition_dp_pa": breakdown["shell_outlet_transition_dp_pa"] or Decimal("0"),
        "shell_nozzle_pair_min_dp_pa": breakdown["shell_nozzle_pair_dp_pa"] or Decimal("0"),
        "shell_external_min_dp_pa": ext,
    }


def analyze_shell_hydraulic_lower_bound(
    bindings: CandidateRatingBindings,
    *,
    full_path_mid_shell_dp_pa: Decimal | None = None,
    full_path_mid_margin_pa: Decimal | None = None,
) -> ShellHydraulicLowerBoundReport:
    case = build_engineering_case_v2_from_v08(bindings.normalized)
    record = candidate_selection_record_from_bindings(bindings)
    postpass = task174_hydraulic_postpass_from_bindings(bindings)
    t174 = bindings.rating_request.task174_result
    bell = Decimal(str(t174.bell_total_shell_pressure_drop_pa))
    limit = bindings.normalized.max_shell_side_pressure_drop_pa

    duplicate_errors: tuple[str, ...] = ()
    try:
        path_input = build_r27b_assumption_based_hydraulic_path_input_v1(
            case=case,
            record=record,
            loss_scenario_key="mid_band",
            tube_nozzle_inside_diameter_m=Decimal("0.1"),
            shell_nozzle_inside_diameter_m=Decimal("0.1"),
        )
        duplicate_errors = tuple(
            validate_no_duplicate_local_loss_with_postpass(path_input, postpass)
        )
    except Exception:
        duplicate_errors = ("PATH_INPUT_BINDING_FAILED_FOR_DUPLICATE_AUDIT",)

    scenario_rows: list[ShellScenarioLowerBound] = []
    scenario_keys: tuple[ScenarioKey, ...] = (
        "mid_band",
        "low_loss_sensitivity",
        "high_loss_sensitivity",
    )
    for key in scenario_keys:
        scenario = R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS[key]
        parts = _min_external_breakdown(case=case, record=record, scenario=scenario)
        external_min = parts["shell_external_min_dp_pa"]
        remaining = limit - external_min
        proven = bell + external_min > limit
        fp_dp: str | None = None
        margin: str | None = None
        if key == "mid_band" and full_path_mid_shell_dp_pa is not None:
            fp_dp = str(full_path_mid_shell_dp_pa)
            margin = (
                str(full_path_mid_margin_pa)
                if full_path_mid_margin_pa is not None
                else str(limit - full_path_mid_shell_dp_pa)
            )
        scenario_rows.append(
            ShellScenarioLowerBound(
                scenario_key=key,
                shell_bell_internal_dp_pa=str(bell),
                shell_inlet_nozzle_dp_pa=str(parts["shell_inlet_nozzle_dp_pa"]),
                shell_outlet_nozzle_dp_pa=str(parts["shell_outlet_nozzle_dp_pa"]),
                shell_inlet_transition_dp_pa=str(parts["shell_inlet_transition_dp_pa"]),
                shell_outlet_transition_dp_pa=str(parts["shell_outlet_transition_dp_pa"]),
                shell_nozzle_pair_min_dp_pa=str(parts["shell_nozzle_pair_min_dp_pa"]),
                shell_external_min_dp_pa=str(external_min),
                remaining_internal_budget_pa=str(remaining),
                shell_dp_limit_pa=str(limit),
                proven_hydraulic_infeasible_under_assumed_k=proven,
                shell_full_path_dp_pa=fp_dp,
                shell_dp_margin_pa=margin,
                shell_min_nozzle_diameter_m=str(parts["shell_min_nozzle_diameter_m"]),
            )
        )

    mid_row = next(s for s in scenario_rows if s.scenario_key == "mid_band")
    high_row = next(s for s in scenario_rows if s.scenario_key == "high_loss_sensitivity")
    bell_reduction: str | None = None
    if mid_row.proven_hydraulic_infeasible_under_assumed_k:
        excess = bell - Decimal(mid_row.remaining_internal_budget_pa)
        if excess > 0:
            bell_reduction = str(excess)

    return ShellHydraulicLowerBoundReport(
        candidate_id=bindings.rating_request.candidate_id,
        geometry_projection_hash=bindings.geometry_projection_hash,
        shell_dp_limit_pa=str(limit),
        scenarios=tuple(scenario_rows),
        any_proven_infeasible=any(
            s.proven_hydraulic_infeasible_under_assumed_k for s in scenario_rows
        ),
        all_proven_infeasible=all(
            s.proven_hydraulic_infeasible_under_assumed_k for s in scenario_rows
        ),
        mid_remaining_internal_budget_pa=mid_row.remaining_internal_budget_pa,
        high_remaining_internal_budget_pa=high_row.remaining_internal_budget_pa,
        bell_reduction_required_for_mid_feasibility_pa=bell_reduction,
        duplicate_dp_component_errors=duplicate_errors,
    )


__all__ = [
    "ShellHydraulicLowerBoundReport",
    "ShellScenarioLowerBound",
    "analyze_shell_hydraulic_lower_bound",
]
