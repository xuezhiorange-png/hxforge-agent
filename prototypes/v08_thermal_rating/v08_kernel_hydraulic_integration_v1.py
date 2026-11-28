"""V08 kernel thermal ↔ hydraulic joint path (kernel authority, not Task173)."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from hexagent.properties.base import FluidIdentifier
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    _side_inlet_density_kg_m3,
)
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    AutonomousNozzleFullPathReport,
    _fluid_density_kg_m3,
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import CandidateRatingBindings
from prototypes.v08_thermal_rating.four_port_nozzle_correction_and_validation_v08 import (
    PortVelocityRecord,
    TrialNozzleEvaluation,
    _common_diameter_bounds,
    _evaluate_trial,
    _strict_velocity_failures,
)
from prototypes.v08_thermal_rating.v08_independent_engineering_rating_kernel_v1 import (
    KERNEL_AUTHORITY_ID,
    KernelThermalRatingResult,
)
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import (
    build_engineering_case_v2_from_v08,
    task174_hydraulic_postpass_from_bindings,
)

HYDRAULIC_AUTHORITY_ID = "V08-KERNEL-JOINT-HYDRAULIC-INTEGRATION-V1"
_V08_MIN_OUTLET_PRESSURE_PA = Decimal("50000")
_V08_MAX_OUTLET_PRESSURE_PA = Decimal("10000000")
_V_LO = Decimal("1")
_V_HI = Decimal("3")

JointClass = Literal[
    "FULL_E2E_SUCCESS",
    "ROBUST_THREE_K_PASS",
    "CONDITIONAL_MID_K_ONLY",
    "THERMAL_ONLY",
    "HYDRAULIC_BLOCKED",
    "NOZZLE_INFEASIBLE",
    "THERMAL_BLOCKED",
]


@dataclass(frozen=True)
class KernelNozzleSelection:
    tube_inside_diameter_m: Decimal
    shell_inside_diameter_m: Decimal
    tube_bounds_feasible: bool
    shell_bounds_feasible: bool
    strict_velocity: Literal["PASS", "BLOCKED"]
    velocity_failures: tuple[str, ...]


@dataclass(frozen=True)
class KernelJointHydraulicRecord:
    authority_id: str
    thermal_authority_id: str
    nozzle: KernelNozzleSelection
    hydraulic_report: AutonomousNozzleFullPathReport
    trial_evaluation: TrialNozzleEvaluation | None
    v08_outlet_domain_reassessed: bool
    full_path_authoritative_mid: bool
    full_path_authoritative_all_k: bool
    joint_class: JointClass
    blockers: tuple[str, ...]


def build_kernel_hydraulic_postpass(
    bindings: CandidateRatingBindings,
    thermal: KernelThermalRatingResult,
) -> dict[str, Any]:
    """Merge kernel outlet state into Task174 postpass (does not claim Task173 rating)."""
    base = dict(task174_hydraulic_postpass_from_bindings(bindings))
    if thermal.tube_outlet_t_k is not None:
        base["tube_outlet_temperature_k"] = thermal.tube_outlet_t_k
    if thermal.shell_outlet_t_k is not None:
        base["shell_outlet_temperature_k"] = thermal.shell_outlet_t_k
    base["thermal_outlet_authority"] = thermal.authority_id
    base["not_task173_production_rating"] = True
    return base


def v08_kernel_outlet_domain_ok(
    provider: CoolPropProvider,
    *,
    temperature_k: Decimal,
    pressure_pa: Decimal,
) -> tuple[bool, str | None]:
    """Atmospheric V08 cases: allow outlet P below 100 kPa when still in liquid envelope."""
    if pressure_pa < _V08_MIN_OUTLET_PRESSURE_PA or pressure_pa > _V08_MAX_OUTLET_PRESSURE_PA:
        return False, "V08_OUTLET_PRESSURE_OUT_OF_ENVELOPE"
    try:
        state = provider.state_tp(
            FluidIdentifier("Water", "HEOS"),
            float(temperature_k),
            float(pressure_pa),
        )
    except Exception as exc:
        return False, f"COOLPROP_TP_ERROR:{type(exc).__name__}"
    phase_name = getattr(state.phase, "value", str(state.phase)).lower()
    if "liquid" not in phase_name:
        return False, f"COOLPROP_PHASE_{phase_name}"
    return True, None


def _reassess_full_path_outlet_domain(
    fp: dict[str, Any],
    *,
    case: EngineeringCase,
    postpass: dict[str, Any],
    provider: CoolPropProvider,
) -> dict[str, Any]:
    """Patch authorized full-path dict when legacy 100 kPa floor blocks atmospheric outlets."""
    if not fp or fp.get("status") != "COMPUTED":
        return fp
    out = dict(fp)
    tube_t = Decimal(
        str(postpass.get("tube_outlet_temperature_k", case.tube_side.inlet_temperature_k))
    )
    shell_t = Decimal(
        str(postpass.get("shell_outlet_temperature_k", case.shell_side.inlet_temperature_k))
    )
    tube_dp = Decimal(str(out["TUBE_FULL_PATH_TOTAL_DP_PA"]))
    shell_dp = Decimal(str(out["SHELL_FULL_PATH_TOTAL_DP_PA"]))
    tube_p_out = Decimal(str(case.tube_side.inlet_pressure_pa)) - tube_dp
    shell_p_out = Decimal(str(case.shell_side.inlet_pressure_pa)) - shell_dp
    tok, tdet = v08_kernel_outlet_domain_ok(provider, temperature_k=tube_t, pressure_pa=tube_p_out)
    sok, sdet = v08_kernel_outlet_domain_ok(
        provider, temperature_k=shell_t, pressure_pa=shell_p_out
    )
    out["FULL_PATH_TUBE_OUTLET_DOMAIN_STATUS"] = (
        "SATISFIED" if tok else "OUTLET_PRESSURE_OUT_OF_DOMAIN"
    )
    out["FULL_PATH_SHELL_OUTLET_DOMAIN_STATUS"] = (
        "SATISFIED" if sok else "OUTLET_PRESSURE_OUT_OF_DOMAIN"
    )
    out["FULL_PATH_TUBE_OUTLET_DOMAIN_DETAIL"] = tdet
    out["FULL_PATH_SHELL_OUTLET_DOMAIN_DETAIL"] = sdet
    tube_c = out.get("FULL_PATH_TUBE_CONSTRAINT_STATUS")
    shell_c = out.get("FULL_PATH_SHELL_CONSTRAINT_STATUS")
    if tube_c == "SATISFIED" and shell_c == "SATISFIED" and tok and sok:
        out["FULL_PATH_HYDRAULIC_STATUS"] = "SATISFIED"
    elif not tok or not sok:
        out["FULL_PATH_HYDRAULIC_STATUS"] = "OUTLET_PRESSURE_DOMAIN_BLOCKED"
    else:
        out["FULL_PATH_HYDRAULIC_STATUS"] = "NOT_SATISFIED"
    out["v08_kernel_outlet_domain_reassessed"] = True
    return out


def _ports_in_band_eps(port_v: Decimal) -> bool:
    eps = Decimal("0.002")
    return (_V_LO - eps) <= port_v <= (_V_HI + eps)


def _search_kernel_nozzle_pair(
    bindings: CandidateRatingBindings,
    thermal: KernelThermalRatingResult,
    *,
    provider: CoolPropProvider,
) -> KernelNozzleSelection | None:
    if thermal.tube_outlet_t_k is None or thermal.shell_outlet_t_k is None:
        return None
    case = build_engineering_case_v2_from_v08(bindings.normalized)
    tube_out = Decimal(thermal.tube_outlet_t_k)
    shell_out = Decimal(thermal.shell_outlet_t_k)
    tube_rho_in = Decimal(str(_side_inlet_density_kg_m3(case, "tube_side")))
    shell_rho_in = Decimal(str(_side_inlet_density_kg_m3(case, "shell_side")))
    tube_p = Decimal(str(case.tube_side.inlet_pressure_pa))
    shell_p = Decimal(str(case.shell_side.inlet_pressure_pa))
    tube_rho_out = _fluid_density_kg_m3(provider, temperature_k=tube_out, pressure_pa=tube_p)
    shell_rho_out = _fluid_density_kg_m3(provider, temperature_k=shell_out, pressure_pa=shell_p)
    tb = _common_diameter_bounds(
        mass_kg_s=Decimal(str(case.tube_side.mass_flow_kg_s)),
        rho_in=tube_rho_in,
        rho_out=tube_rho_out,
        side="tube",
    )
    sb = _common_diameter_bounds(
        mass_kg_s=Decimal(str(case.shell_side.mass_flow_kg_s)),
        rho_in=shell_rho_in,
        rho_out=shell_rho_out,
        side="shell",
    )
    if not tb.feasible_interval_nonempty or not sb.feasible_interval_nonempty:
        return None
    candidates: list[tuple[Decimal, Decimal, tuple[str, ...]]] = []
    for t_frac in (Decimal("0.35"), Decimal("0.55"), Decimal("0.75"), Decimal("1.0")):
        for s_frac in (Decimal("0.35"), Decimal("0.55"), Decimal("0.75"), Decimal("1.0")):
            t_d = tb.common_feasible_lower_m + t_frac * (
                tb.common_feasible_upper_m - tb.common_feasible_lower_m
            )
            s_d = sb.common_feasible_lower_m + s_frac * (
                sb.common_feasible_upper_m - sb.common_feasible_lower_m
            )
            hyd = run_autonomous_nozzle_full_path(
                bindings,
                fixed_tube_inside_diameter_m=t_d,
                fixed_shell_inside_diameter_m=s_d,
                tube_outlet_temperature_k=tube_out,
                shell_outlet_temperature_k=shell_out,
                provider=provider,
            )
            records = tuple(
                PortVelocityRecord(
                    port_id=p.port_id,
                    inside_diameter_m=p.inside_diameter_m,
                    density_kg_m3=p.density_kg_m3,
                    mass_flow_kg_s=p.mass_flow_kg_s,
                    velocity_m_s=p.velocity_m_s,
                    velocity_basis=p.velocity_basis,
                )
                for p in hyd.ports
            )
            failures = _strict_velocity_failures(records)
            eps_fail = tuple(
                f for f in failures if not all(_ports_in_band_eps(r.velocity_m_s) for r in records)
            )
            if not eps_fail and all(_ports_in_band_eps(r.velocity_m_s) for r in records):
                candidates.append((t_d, s_d, ()))
            elif not failures:
                candidates.append((t_d, s_d, failures))
    if not candidates:
        return KernelNozzleSelection(
            tube_inside_diameter_m=tb.common_feasible_upper_m,
            shell_inside_diameter_m=sb.common_feasible_upper_m,
            tube_bounds_feasible=tb.feasible_interval_nonempty,
            shell_bounds_feasible=sb.feasible_interval_nonempty,
            strict_velocity="BLOCKED",
            velocity_failures=("NO_STRICT_FOUR_PORT_GRID_POINT",),
        )
    best = max(candidates, key=lambda c: c[0] + c[1])
    return KernelNozzleSelection(
        tube_inside_diameter_m=best[0],
        shell_inside_diameter_m=best[1],
        tube_bounds_feasible=True,
        shell_bounds_feasible=True,
        strict_velocity="PASS",
        velocity_failures=best[2],
    )


def evaluate_kernel_joint_hydraulics(
    bindings: CandidateRatingBindings,
    thermal: KernelThermalRatingResult,
    *,
    provider: CoolPropProvider | None = None,
) -> KernelJointHydraulicRecord:
    active = provider or CoolPropProvider()
    if thermal.status != "RATING_SUCCESS":
        return KernelJointHydraulicRecord(
            authority_id=HYDRAULIC_AUTHORITY_ID,
            thermal_authority_id=thermal.authority_id,
            nozzle=KernelNozzleSelection(
                tube_inside_diameter_m=Decimal(0),
                shell_inside_diameter_m=Decimal(0),
                tube_bounds_feasible=False,
                shell_bounds_feasible=False,
                strict_velocity="BLOCKED",
                velocity_failures=(thermal.blocked_code or "THERMAL_BLOCKED",),
            ),
            hydraulic_report=_empty_hydraulic_blocked(bindings),
            trial_evaluation=None,
            v08_outlet_domain_reassessed=False,
            full_path_authoritative_mid=False,
            full_path_authoritative_all_k=False,
            joint_class="THERMAL_BLOCKED",
            blockers=(thermal.blocked_code or "THERMAL_BLOCKED",),
        )
    nozzle = _search_kernel_nozzle_pair(bindings, thermal, provider=active)
    if nozzle is None or nozzle.strict_velocity != "PASS":
        return KernelJointHydraulicRecord(
            authority_id=HYDRAULIC_AUTHORITY_ID,
            thermal_authority_id=thermal.authority_id,
            nozzle=nozzle
            or KernelNozzleSelection(
                Decimal(0),
                Decimal(0),
                False,
                False,
                "BLOCKED",
                ("NOZZLE_INTERVAL_EMPTY",),
            ),
            hydraulic_report=_empty_hydraulic_blocked(bindings),
            trial_evaluation=None,
            v08_outlet_domain_reassessed=False,
            full_path_authoritative_mid=False,
            full_path_authoritative_all_k=False,
            joint_class="NOZZLE_INFEASIBLE",
            blockers=nozzle.velocity_failures if nozzle else ("NOZZLE_INTERVAL_EMPTY",),
        )
    case = build_engineering_case_v2_from_v08(bindings.normalized)
    tube_out = Decimal(thermal.tube_outlet_t_k or "0")
    shell_out = Decimal(thermal.shell_outlet_t_k or "0")
    hyd = run_autonomous_nozzle_full_path(
        bindings,
        fixed_tube_inside_diameter_m=nozzle.tube_inside_diameter_m,
        fixed_shell_inside_diameter_m=nozzle.shell_inside_diameter_m,
        tube_outlet_temperature_k=tube_out,
        shell_outlet_temperature_k=shell_out,
        provider=active,
    )
    build_kernel_hydraulic_postpass(bindings, thermal)
    trial = _evaluate_trial(
        bindings=bindings,
        case=case,
        normalized=bindings.normalized,
        tube_mm=(nozzle.tube_inside_diameter_m * Decimal("1000")).quantize(Decimal("0.001")),
        shell_mm=(nozzle.shell_inside_diameter_m * Decimal("1000")).quantize(Decimal("0.001")),
        tube_out_k=tube_out,
        shell_out_k=shell_out,
        thermal_pass=True,
        provider=active,
        grid_trial=False,
    )

    def scenario_kernel_pass(sc: Any) -> bool:
        if sc.tube_margin_pa is None or sc.shell_margin_pa is None:
            return False
        if Decimal(sc.tube_margin_pa) < 0 or Decimal(sc.shell_margin_pa) < 0:
            return False
        if sc.tube_full_path_dp_pa is None or sc.shell_full_path_dp_pa is None:
            return False
        tube_p_out = Decimal(str(case.tube_side.inlet_pressure_pa)) - Decimal(
            sc.tube_full_path_dp_pa
        )
        shell_p_out = Decimal(str(case.shell_side.inlet_pressure_pa)) - Decimal(
            sc.shell_full_path_dp_pa
        )
        tok, _ = v08_kernel_outlet_domain_ok(active, temperature_k=tube_out, pressure_pa=tube_p_out)
        sok, _ = v08_kernel_outlet_domain_ok(
            active, temperature_k=shell_out, pressure_pa=shell_p_out
        )
        return tok and sok

    mid = next(s for s in hyd.scenarios if s.scenario_key == "mid_band")
    all_k = all(scenario_kernel_pass(sc) for sc in hyd.scenarios)
    mid_ok = scenario_kernel_pass(mid)
    nozzle_ok = all(_ports_in_band_eps(p.velocity_m_s) for p in hyd.ports)
    blockers: list[str] = list(hyd.remaining_blockers)
    if not nozzle_ok:
        blockers.append("KERNEL_FOUR_PORT_VELOCITY_EPS_FAIL")
    joint: JointClass = "HYDRAULIC_BLOCKED"
    if mid_ok and nozzle_ok and all_k:
        joint = "ROBUST_THREE_K_PASS"
    elif mid_ok and nozzle_ok:
        joint = "CONDITIONAL_MID_K_ONLY"
    elif thermal.status == "RATING_SUCCESS" and not mid_ok:
        joint = "THERMAL_ONLY"
    if mid_ok and nozzle_ok and all_k and thermal.duty_meets_target:
        joint = "FULL_E2E_SUCCESS"
    return KernelJointHydraulicRecord(
        authority_id=HYDRAULIC_AUTHORITY_ID,
        thermal_authority_id=thermal.authority_id,
        nozzle=nozzle,
        hydraulic_report=hyd,
        trial_evaluation=trial,
        v08_outlet_domain_reassessed=True,
        full_path_authoritative_mid=mid_ok,
        full_path_authoritative_all_k=all_k,
        joint_class=joint,
        blockers=tuple(dict.fromkeys(blockers)),
    )


def _empty_hydraulic_blocked(bindings: CandidateRatingBindings) -> AutonomousNozzleFullPathReport:
    from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
        MechanicalInstallationAuthority,
        NozzleBisectOutcome,
        Task174PartialHydraulics,
    )

    Decimal(0)
    return AutonomousNozzleFullPathReport(
        case_id=bindings.engineering_case_id,
        candidate_id=bindings.rating_request.candidate_id,
        structural_geometry_hash=bindings.geometry_projection_hash,
        nozzle_design_hash="blocked",
        nozzle_size_authority="PARAMETRIC_CALCULATED",
        ports=(),
        nozzle_velocity_check="BLOCKED",
        nozzle_same_geometry_all_scenarios=True,
        installation=MechanicalInstallationAuthority(
            preliminary_geometry_fit="BLOCKED",
            mechanical_clearance="UNRESOLVED",
            nozzle_reinforcement="UNRESOLVED",
            manufacturing_size_authority="PROVISIONAL",
        ),
        full_path_dp_authority="ASSUMPTION_BASED",
        scenario_robustness="BLOCKED",
        scenarios=(),
        task174_partial=Task174PartialHydraulics(
            tube_dp_pa="0",
            shell_dp_pa="0",
            tube_margin_pa="0",
            shell_margin_pa="0",
            authority="TASK174_PARTIAL_DP",
            tube_friction_dp_pa=None,
            tube_local_dp_pa=None,
            shell_bell_total_dp_pa="0",
        ),
        nozzle_bisect=NozzleBisectOutcome("BLOCKED", "BLOCKED", "0", "0", ()),
        remaining_blockers=("HYDRAULIC_NOT_RUN",),
        disclosure=(KERNEL_AUTHORITY_ID,),
    )


def candidate_geometry_snapshot(bindings: CandidateRatingBindings) -> dict[str, str]:
    c = bindings.bundle.candidate
    shell = bindings.bundle.shell_record
    layout = bindings.bundle.bundle.task021_layout
    t025 = bindings.bundle.bundle.task025_result
    return {
        "candidate_id": c.candidate_id,
        "geometry_projection_hash": bindings.geometry_projection_hash,
        "shell_inside_diameter_m": str(shell.shell_inside_diameter_m),
        "tube_outer_diameter_m": str(c.tube_outer_diameter_m),
        "tube_length_m": str(c.tube_length_m),
        "tube_pass_count": str(c.tube_pass_count),
        "physical_tube_count": str(layout.physical_tube_count),
        "heat_transfer_area_m2": str(getattr(t025, "internal_heat_transfer_surface_area_m2", "")),
    }


__all__ = [
    "HYDRAULIC_AUTHORITY_ID",
    "KernelJointHydraulicRecord",
    "build_kernel_hydraulic_postpass",
    "evaluate_kernel_joint_hydraulics",
    "candidate_geometry_snapshot",
    "v08_kernel_outlet_domain_ok",
]
