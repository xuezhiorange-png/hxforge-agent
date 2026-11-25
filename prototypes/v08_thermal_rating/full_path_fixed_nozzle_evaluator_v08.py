"""Fixed-nozzle full-path evaluation: one design, three K scenarios (no per-scenario resize)."""

# ruff: noqa: E501

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    NOZZLE_VELOCITY_DESIGN_RULE,
)
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import CandidateSelectionRecord
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    LossScenarioKey,
    _authorized_full_path_feasible,
    _bisect_feasible_nozzle_d,
    _side_inlet_density_kg_m3,
    _verify_full_path,
)

DpAuthority = Literal[
    "TASK174_PARTIAL_DP",
    "SIDE_MODEL_AT_VELOCITY_BOUND_DP",
    "VERIFIED_ASSUMPTION_FULL_PATH_DP",
    "FULL_PATH_NOT_COMPUTED",
]

CheckStatus = Literal["PASS", "OVER_DP", "BLOCKED", "UNRESOLVED", "SCENARIO_DEPENDENT"]

_PI = Decimal("3.1415926535897932384626433832795")


def _decimal_velocity_m_s(*, mass_flow_kg_s: Decimal, rho: Decimal, diameter_m: Decimal) -> Decimal:
    area = _PI * (diameter_m / Decimal("2")) ** 2
    return mass_flow_kg_s / (rho * area)


def _diameter_at_velocity_m(
    *, mass_flow_kg_s: Decimal, rho: Decimal, velocity_m_s: Decimal
) -> Decimal:
    area = mass_flow_kg_s / (rho * velocity_m_s)
    ratio = Decimal("4") * area / _PI
    return ratio.sqrt() if hasattr(ratio, "sqrt") else Decimal(str(math.sqrt(float(ratio))))


def _clamp_nozzle_d_to_velocity_band(
    *,
    case: EngineeringCase,
    side: Literal["tube_side", "shell_side"],
    diameter_m: Decimal,
    velocity_rule: dict[str, Any] | None = None,
) -> Decimal:
    rule = velocity_rule or NOZZLE_VELOCITY_DESIGN_RULE
    v_min = Decimal(str(rule["velocity_m_s_min"]))
    v_max = Decimal(str(rule["velocity_m_s_max"]))
    spec = case.tube_side if side == "tube_side" else case.shell_side
    m = Decimal(str(spec.mass_flow_kg_s))
    rho = Decimal(str(_side_inlet_density_kg_m3(case, side)))
    d = diameter_m
    v = _decimal_velocity_m_s(mass_flow_kg_s=m, rho=rho, diameter_m=d)
    if v < v_min:
        d = _diameter_at_velocity_m(mass_flow_kg_s=m, rho=rho, velocity_m_s=v_min)
        v = _decimal_velocity_m_s(mass_flow_kg_s=m, rho=rho, diameter_m=d)
        step = Decimal("1e-8")
        while v < v_min and d > step:
            d -= step
            v = _decimal_velocity_m_s(mass_flow_kg_s=m, rho=rho, diameter_m=d)
    elif v > v_max:
        d = _diameter_at_velocity_m(mass_flow_kg_s=m, rho=rho, velocity_m_s=v_max)
    return d


@dataclass(frozen=True)
class FixedNozzleDesign:
    tube_inside_diameter_m: Decimal
    shell_inside_diameter_m: Decimal
    tube_select_status: str
    shell_select_status: str
    selection_loss_scenario: LossScenarioKey


@dataclass(frozen=True)
class SideDpBreakdown:
    authority: DpAuthority
    total_dp_pa: str | None
    margin_pa: str | None
    components: dict[str, str]
    constraint_status: str | None


@dataclass(frozen=True)
class FixedNozzleScenarioEvaluation:
    scenario_key: LossScenarioKey
    tube: SideDpBreakdown
    shell: SideDpBreakdown
    hydraulic_check: CheckStatus
    full_path_feasible: bool
    overall_fp_status: str | None
    blockers: tuple[str, ...]


def _largest_feasible_nozzle_diameter(
    *,
    case: EngineeringCase,
    record: CandidateSelectionRecord,
    postpass: dict[str, Any],
    scenario: dict[str, Any],
    side: Literal["tube_side", "shell_side"],
    max_dp_pa: Decimal,
    velocity_rule: dict[str, Any] | None,
    tube_nozzle_d_m: Decimal | None,
    shell_nozzle_d_m: Decimal | None,
) -> Decimal | None:
    from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
        _search_nozzle_d_in_velocity_band,
        _shell_bd_internal_pa,
        _shell_external_dp_pa_for_nozzle_d,
        _tube_path_dp_pa_for_nozzle_d,
    )

    d_lo, d_hi = _search_nozzle_d_in_velocity_band(
        case=case, side=side, velocity_rule=velocity_rule
    )

    def side_total_dp(d_m: float) -> Decimal | None:
        d_dec = Decimal(str(d_m))
        if side == "tube_side":
            total, _ = _tube_path_dp_pa_for_nozzle_d(
                case=case,
                record=record,
                postpass=postpass,
                scenario=scenario,
                tube_nozzle_d_m=d_dec,
                include_nozzle_pair=True,
            )
            return total
        ext, _ = _shell_external_dp_pa_for_nozzle_d(
            case=case,
            record=record,
            scenario=scenario,
            shell_nozzle_d_m=d_dec,
            include_nozzle_pair=True,
        )
        bd = _shell_bd_internal_pa(postpass)
        if ext is None or bd is None:
            return None
        return bd + ext

    dp_hi = side_total_dp(d_hi)
    if dp_hi is not None and dp_hi <= max_dp_pa:
        return Decimal(str(d_hi))
    dp_lo = side_total_dp(d_lo)
    if dp_lo is None or dp_lo > max_dp_pa:
        return None
    lo, hi = float(d_lo), float(d_hi)
    best = lo
    for _ in range(48):
        mid = (lo + hi) / 2.0
        dp_mid = side_total_dp(mid)
        if dp_mid is None:
            return None
        if dp_mid <= max_dp_pa:
            best = mid
            lo = mid
        else:
            hi = mid
    return Decimal(str(best))


NozzleDiameterObjective = Literal["MINIMUM_DIAMETER", "MAX_MARGIN_WITHIN_VELOCITY_BAND"]


def select_fixed_nozzle_design(
    *,
    case: EngineeringCase,
    record: CandidateSelectionRecord,
    postpass: dict[str, Any],
    selection_scenario: LossScenarioKey = "mid_band",
    tube_nozzle_objective: NozzleDiameterObjective = "MINIMUM_DIAMETER",
    shell_nozzle_objective: NozzleDiameterObjective = "MINIMUM_DIAMETER",
    fixed_tube_inside_diameter_m: Decimal | None = None,
    fixed_shell_inside_diameter_m: Decimal | None = None,
) -> FixedNozzleDesign:
    """Pick one tube/shell nozzle ID (mid-band K) for all loss scenarios."""
    scenario = R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS[selection_scenario]
    tube_status = "FIXED_OVERRIDE"
    shell_status = "FIXED_OVERRIDE"
    if fixed_tube_inside_diameter_m is not None:
        tube_d = fixed_tube_inside_diameter_m
    else:
        tube_search = _bisect_feasible_nozzle_d(
            case=case,
            record=record,
            postpass=postpass,
            scenario=scenario,
            side="tube_side",
            max_dp_pa=Decimal(str(case.max_tube_side_pressure_drop_pa)),
            velocity_rule=None,
            tube_nozzle_d_m=None,
            shell_nozzle_d_m=None,
        )
        tube_status = str(tube_search.get("status", "UNKNOWN"))
        if tube_search.get("selected_inside_diameter_m") is not None:
            tube_d = Decimal(str(tube_search["selected_inside_diameter_m"]))
        else:
            tube_d = Decimal(str(tube_search["diameter_search_band_m"]["max"]))
        if tube_nozzle_objective == "MAX_MARGIN_WITHIN_VELOCITY_BAND":
            alt = _largest_feasible_nozzle_diameter(
                case=case,
                record=record,
                postpass=postpass,
                scenario=scenario,
                side="tube_side",
                max_dp_pa=Decimal(str(case.max_tube_side_pressure_drop_pa)),
                velocity_rule=None,
                tube_nozzle_d_m=None,
                shell_nozzle_d_m=None,
            )
            if alt is not None and alt > tube_d:
                tube_d = alt
        tube_d = _clamp_nozzle_d_to_velocity_band(case=case, side="tube_side", diameter_m=tube_d)
    if fixed_shell_inside_diameter_m is not None:
        shell_d = fixed_shell_inside_diameter_m
    else:
        shell_search = _bisect_feasible_nozzle_d(
            case=case,
            record=record,
            postpass=postpass,
            scenario=scenario,
            side="shell_side",
            max_dp_pa=Decimal(str(case.max_shell_side_pressure_drop_pa)),
            velocity_rule=None,
            tube_nozzle_d_m=tube_d,
            shell_nozzle_d_m=None,
        )
        shell_status = str(shell_search.get("status", "UNKNOWN"))
        if shell_search.get("selected_inside_diameter_m") is not None:
            shell_d = Decimal(str(shell_search["selected_inside_diameter_m"]))
        else:
            band = shell_search.get("diameter_search_band_m") or {}
            shell_d = Decimal(
                str(band.get("max", shell_search.get("theoretical_at_band_max_diameter_m")))
            )
        if shell_nozzle_objective == "MAX_MARGIN_WITHIN_VELOCITY_BAND":
            alt = _largest_feasible_nozzle_diameter(
                case=case,
                record=record,
                postpass=postpass,
                scenario=scenario,
                side="shell_side",
                max_dp_pa=Decimal(str(case.max_shell_side_pressure_drop_pa)),
                velocity_rule=None,
                tube_nozzle_d_m=tube_d,
                shell_nozzle_d_m=None,
            )
            if alt is not None and alt > shell_d:
                shell_d = alt
        shell_d = _clamp_nozzle_d_to_velocity_band(case=case, side="shell_side", diameter_m=shell_d)
    return FixedNozzleDesign(
        tube_inside_diameter_m=tube_d,
        shell_inside_diameter_m=shell_d,
        tube_select_status=tube_status,
        shell_select_status=shell_status,
        selection_loss_scenario=selection_scenario,
    )


def _side_from_full_path(
    fp: dict[str, Any] | None,
    *,
    side: Literal["tube", "shell"],
) -> SideDpBreakdown:
    if not fp or fp.get("status") != "COMPUTED":
        return SideDpBreakdown(
            authority="FULL_PATH_NOT_COMPUTED",
            total_dp_pa=None,
            margin_pa=None,
            components={},
            constraint_status=None,
        )
    if side == "tube":
        total = fp.get("TUBE_FULL_PATH_TOTAL_DP_PA")
        margin = fp.get("TUBE_FULL_PATH_DP_MARGIN_PA")
        status = fp.get("FULL_PATH_TUBE_CONSTRAINT_STATUS")
        rows = fp.get("TUBE_DP_COMPONENTS") or []
    else:
        total = fp.get("SHELL_FULL_PATH_TOTAL_DP_PA")
        margin = fp.get("SHELL_FULL_PATH_DP_MARGIN_PA")
        status = fp.get("FULL_PATH_SHELL_CONSTRAINT_STATUS")
        rows = fp.get("SHELL_DP_COMPONENTS") or []
    components = {
        str(row.get("component_id", row.get("label", f"item_{i}"))): str(
            row.get("pressure_drop_pa", row.get("dp_pa", ""))
        )
        for i, row in enumerate(rows)
        if isinstance(row, dict)
    }
    if total is None:
        return SideDpBreakdown(
            authority="FULL_PATH_NOT_COMPUTED",
            total_dp_pa=None,
            margin_pa=str(margin) if margin is not None else None,
            components=components,
            constraint_status=str(status) if status else None,
        )
    return SideDpBreakdown(
        authority="VERIFIED_ASSUMPTION_FULL_PATH_DP",
        total_dp_pa=str(total),
        margin_pa=str(margin) if margin is not None else None,
        components=components,
        constraint_status=str(status) if status else None,
    )


def evaluate_fixed_nozzle_all_scenarios(
    *,
    case: EngineeringCase,
    record: CandidateSelectionRecord,
    postpass: dict[str, Any],
    fixed: FixedNozzleDesign,
    scenarios: tuple[LossScenarioKey, ...] = (
        "mid_band",
        "low_loss_sensitivity",
        "high_loss_sensitivity",
    ),
    tube_outlet_state_k_pa: tuple[Decimal, Decimal] | None = None,
    shell_outlet_state_k_pa: tuple[Decimal, Decimal] | None = None,
) -> tuple[FixedNozzleScenarioEvaluation, ...]:
    out: list[FixedNozzleScenarioEvaluation] = []
    for key in scenarios:
        fp = _verify_full_path(
            case=case,
            record=record,
            postpass=postpass,
            loss_scenario_key=key,
            tube_nozzle_d_m=fixed.tube_inside_diameter_m,
            shell_nozzle_d_m=fixed.shell_inside_diameter_m,
            tube_outlet_state_k_pa=tube_outlet_state_k_pa,
            shell_outlet_state_k_pa=shell_outlet_state_k_pa,
        )
        tube = _side_from_full_path(fp, side="tube")
        shell = _side_from_full_path(fp, side="shell")
        feasible = _authorized_full_path_feasible(fp)
        if feasible:
            check: CheckStatus = "PASS"
        elif fp and fp.get("status") == "COMPUTED":
            tube_st = fp.get("FULL_PATH_TUBE_CONSTRAINT_STATUS")
            shell_st = fp.get("FULL_PATH_SHELL_CONSTRAINT_STATUS")
            if tube_st == "SATISFIED" and shell_st == "SATISFIED":
                check = "BLOCKED"
            else:
                check = "OVER_DP"
        else:
            check = "UNRESOLVED"
        blockers = tuple(str(b) for b in (fp or {}).get("blockers") or ())
        out.append(
            FixedNozzleScenarioEvaluation(
                scenario_key=key,
                tube=tube,
                shell=shell,
                hydraulic_check=check,
                full_path_feasible=feasible,
                overall_fp_status=str(fp.get("status")) if fp else None,
                blockers=blockers,
            )
        )
    return tuple(out)


def classify_scenario_robustness(
    evaluations: tuple[FixedNozzleScenarioEvaluation, ...],
) -> CheckStatus:
    passes = [e for e in evaluations if e.hydraulic_check == "PASS"]
    if len(passes) == len(evaluations) and evaluations:
        return "PASS"
    if passes and len(passes) < len(evaluations):
        return "SCENARIO_DEPENDENT"
    if any(e.hydraulic_check == "UNRESOLVED" for e in evaluations):
        return "UNRESOLVED"
    return "BLOCKED"


__all__ = [
    "DpAuthority",
    "FixedNozzleDesign",
    "FixedNozzleScenarioEvaluation",
    "NozzleDiameterObjective",
    "SideDpBreakdown",
    "classify_scenario_robustness",
    "evaluate_fixed_nozzle_all_scenarios",
    "select_fixed_nozzle_design",
]
