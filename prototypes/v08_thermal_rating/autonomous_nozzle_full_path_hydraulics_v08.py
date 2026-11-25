"""Autonomous four-port nozzle + fixed-design full-path hydraulics for V08."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from hexagent.canonical_json import canonical_sha256
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    NOZZLE_VELOCITY_DESIGN_RULE,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    nozzle_flow_area_m2,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    LossScenarioKey,
    _geometry_fit_risk,
    _side_inlet_density_kg_m3,
)
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CandidateRatingBindings,
    build_candidate_rating_bindings,
    enumerate_structural_bundles,
)
from prototypes.v08_thermal_rating.full_path_fixed_nozzle_evaluator_v08 import (
    CheckStatus,
    DpAuthority,
    classify_scenario_robustness,
    evaluate_fixed_nozzle_all_scenarios,
    select_fixed_nozzle_design,
)
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import (
    build_engineering_case_v2_from_v08,
    candidate_selection_record_from_bindings,
    task174_hydraulic_postpass_from_bindings,
)

LOSS_SCENARIOS: tuple[LossScenarioKey, ...] = (
    "mid_band",
    "low_loss_sensitivity",
    "high_loss_sensitivity",
)

NozzleSizeAuthority = Literal["PARAMETRIC_CALCULATED", "STANDARD_SERIES"]
VelocityBasis = Literal[
    "INLET_TP_PROPERTY",
    "INDICATIVE_THERMAL_PRESCREEN_OUTLET",
    "PROVISIONAL_SYMMETRIC_INLET",
]


@dataclass(frozen=True)
class NozzlePortDesign:
    port_id: Literal["TUBE_INLET", "TUBE_OUTLET", "SHELL_INLET", "SHELL_OUTLET"]
    inside_diameter_m: Decimal
    velocity_m_s: Decimal
    effective_area_m2: Decimal
    mass_flow_kg_s: Decimal
    density_kg_m3: Decimal
    size_authority: NozzleSizeAuthority
    velocity_basis: VelocityBasis
    multiplicity: int


@dataclass(frozen=True)
class MechanicalInstallationAuthority:
    preliminary_geometry_fit: Literal["PASS", "BLOCKED"]
    mechanical_clearance: Literal["PASS", "BLOCKED", "UNRESOLVED"]
    nozzle_reinforcement: Literal["PASS", "BLOCKED", "UNRESOLVED"]
    manufacturing_size_authority: Literal["VERIFIED", "PROVISIONAL"]


@dataclass(frozen=True)
class FullPathScenarioResult:
    scenario_key: LossScenarioKey
    tube_dp_authority: DpAuthority
    shell_dp_authority: DpAuthority
    tube_full_path_dp_pa: str | None
    shell_full_path_dp_pa: str | None
    tube_margin_pa: str | None
    shell_margin_pa: str | None
    tube_breakdown: dict[str, str]
    shell_breakdown: dict[str, str]
    hydraulic_check: CheckStatus
    full_path_feasible: bool
    overall_fp_status: str | None


@dataclass(frozen=True)
class Task174PartialHydraulics:
    tube_dp_pa: str
    shell_dp_pa: str
    tube_margin_pa: str
    shell_margin_pa: str
    authority: DpAuthority
    tube_friction_dp_pa: str | None
    tube_local_dp_pa: str | None
    shell_bell_total_dp_pa: str


@dataclass(frozen=True)
class NozzleBisectOutcome:
    tube_select_status: str
    shell_select_status: str
    tube_inside_diameter_m: str
    shell_inside_diameter_m: str
    search_infeasible_notes: tuple[str, ...]


@dataclass(frozen=True)
class AutonomousNozzleFullPathReport:
    case_id: str
    candidate_id: str
    structural_geometry_hash: str
    nozzle_design_hash: str
    nozzle_size_authority: NozzleSizeAuthority
    ports: tuple[NozzlePortDesign, ...]
    nozzle_velocity_check: CheckStatus
    nozzle_same_geometry_all_scenarios: bool
    installation: MechanicalInstallationAuthority
    full_path_dp_authority: Literal["ASSUMPTION_BASED"]
    scenario_robustness: CheckStatus
    scenarios: tuple[FullPathScenarioResult, ...]
    task174_partial: Task174PartialHydraulics
    nozzle_bisect: NozzleBisectOutcome
    remaining_blockers: tuple[str, ...]
    disclosure: tuple[str, ...]


def _velocity_in_band(v: Decimal) -> bool:
    return Decimal("1") <= v <= Decimal("3")


def _fluid_density_kg_m3(
    provider: CoolPropProvider, *, temperature_k: Decimal, pressure_pa: Decimal
) -> Decimal:
    from hexagent.properties.base import FluidIdentifier

    state = provider.state_tp(
        FluidIdentifier(name="Water"), float(temperature_k), float(pressure_pa)
    )
    return Decimal(str(state.density_kg_m3))


def _nozzle_design_hash(ports: tuple[NozzlePortDesign, ...]) -> str:
    payload = {
        "ports": [
            {
                "port_id": p.port_id,
                "inside_diameter_m": str(p.inside_diameter_m),
                "multiplicity": p.multiplicity,
            }
            for p in ports
        ],
        "velocity_rule": NOZZLE_VELOCITY_DESIGN_RULE["rule_id"],
    }
    return canonical_sha256(payload)


def _port_designs(
    *,
    case_engineering: Any,
    tube_d_m: Decimal,
    shell_d_m: Decimal,
    provider: CoolPropProvider | None = None,
    tube_outlet_temperature_k: Decimal | None = None,
    shell_outlet_temperature_k: Decimal | None = None,
) -> tuple[NozzlePortDesign, ...]:
    active = provider or CoolPropProvider()
    tube_p = Decimal(str(case_engineering.tube_side.inlet_pressure_pa))
    shell_p = Decimal(str(case_engineering.shell_side.inlet_pressure_pa))
    tube_rho_in = Decimal(str(_side_inlet_density_kg_m3(case_engineering, "tube_side")))
    shell_rho_in = Decimal(str(_side_inlet_density_kg_m3(case_engineering, "shell_side")))
    if tube_outlet_temperature_k is not None:
        tube_rho_out = _fluid_density_kg_m3(
            active, temperature_k=tube_outlet_temperature_k, pressure_pa=tube_p
        )
    else:
        tube_rho_out = tube_rho_in
    if shell_outlet_temperature_k is not None:
        shell_rho_out = _fluid_density_kg_m3(
            active, temperature_k=shell_outlet_temperature_k, pressure_pa=shell_p
        )
    else:
        shell_rho_out = shell_rho_in
    tube_m = Decimal(str(case_engineering.tube_side.mass_flow_kg_s))
    shell_m = Decimal(str(case_engineering.shell_side.mass_flow_kg_s))
    from prototypes.v08_thermal_rating.full_path_fixed_nozzle_evaluator_v08 import (
        _decimal_velocity_m_s,
    )

    tube_v_in = _decimal_velocity_m_s(mass_flow_kg_s=tube_m, rho=tube_rho_in, diameter_m=tube_d_m)
    tube_v_out = _decimal_velocity_m_s(mass_flow_kg_s=tube_m, rho=tube_rho_out, diameter_m=tube_d_m)
    shell_v_in = _decimal_velocity_m_s(
        mass_flow_kg_s=shell_m, rho=shell_rho_in, diameter_m=shell_d_m
    )
    shell_v_out = _decimal_velocity_m_s(
        mass_flow_kg_s=shell_m, rho=shell_rho_out, diameter_m=shell_d_m
    )
    tube_area = Decimal(str(nozzle_flow_area_m2(tube_d_m)))
    shell_area = Decimal(str(nozzle_flow_area_m2(shell_d_m)))
    authority: NozzleSizeAuthority = "PARAMETRIC_CALCULATED"

    def port(
        port_id: Literal["TUBE_INLET", "TUBE_OUTLET", "SHELL_INLET", "SHELL_OUTLET"],
        d: Decimal,
        v: Decimal,
        area: Decimal,
        m: Decimal,
        rho: Decimal,
        basis: VelocityBasis,
    ) -> NozzlePortDesign:
        return NozzlePortDesign(
            port_id=port_id,
            inside_diameter_m=d,
            velocity_m_s=v,
            effective_area_m2=area,
            mass_flow_kg_s=m,
            density_kg_m3=rho,
            size_authority=authority,
            velocity_basis=basis,
            multiplicity=1,
        )

    out_basis: VelocityBasis = (
        "INDICATIVE_THERMAL_PRESCREEN_OUTLET"
        if tube_outlet_temperature_k is not None
        else "PROVISIONAL_SYMMETRIC_INLET"
    )
    return (
        port(
            "TUBE_INLET", tube_d_m, tube_v_in, tube_area, tube_m, tube_rho_in, "INLET_TP_PROPERTY"
        ),
        port("TUBE_OUTLET", tube_d_m, tube_v_out, tube_area, tube_m, tube_rho_out, out_basis),
        port(
            "SHELL_INLET",
            shell_d_m,
            shell_v_in,
            shell_area,
            shell_m,
            shell_rho_in,
            "INLET_TP_PROPERTY",
        ),
        port("SHELL_OUTLET", shell_d_m, shell_v_out, shell_area, shell_m, shell_rho_out, out_basis),
    )


def _installation_authority(
    record: Any, tube_d: Decimal, shell_d: Decimal
) -> MechanicalInstallationAuthority:
    risk = _geometry_fit_risk(
        record=record,
        tube_nozzle_d_m=float(tube_d),
        shell_nozzle_d_m=float(shell_d),
    )
    flags = risk.get("geometry_adaptation_risk_flags") or []
    prelim: Literal["PASS", "BLOCKED"] = "BLOCKED" if flags else "PASS"
    return MechanicalInstallationAuthority(
        preliminary_geometry_fit=prelim,
        mechanical_clearance="UNRESOLVED",
        nozzle_reinforcement="UNRESOLVED",
        manufacturing_size_authority="PROVISIONAL",
    )


NozzleSelectionObjective = Literal["MINIMUM_DIAMETER", "MAX_MARGIN_WITHIN_VELOCITY_BAND"]


def run_autonomous_nozzle_full_path(
    bindings: CandidateRatingBindings,
    *,
    tube_nozzle_objective: NozzleSelectionObjective = "MINIMUM_DIAMETER",
    shell_nozzle_objective: NozzleSelectionObjective = "MINIMUM_DIAMETER",
    fixed_tube_inside_diameter_m: Decimal | None = None,
    fixed_shell_inside_diameter_m: Decimal | None = None,
    tube_outlet_temperature_k: Decimal | None = None,
    shell_outlet_temperature_k: Decimal | None = None,
    provider: CoolPropProvider | None = None,
    hydraulic_postpass_override: dict[str, Any] | None = None,
) -> AutonomousNozzleFullPathReport:
    case = build_engineering_case_v2_from_v08(bindings.normalized)
    record = candidate_selection_record_from_bindings(bindings)
    postpass = (
        hydraulic_postpass_override
        if hydraulic_postpass_override is not None
        else task174_hydraulic_postpass_from_bindings(bindings)
    )
    t174 = bindings.rating_request.task174_result
    blockers: list[str] = []
    disclosures_list = [
        "Single fixed nozzle pair sized once (mid_band bisect); three K scenarios reuse same IDs.",
        "Loss coefficients: R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS.",
        "PARAMETRIC_CALCULATED nozzle IDs — no verified standard series catalog.",
        "Outlet nozzle velocity PROVISIONAL (no production thermal outlet state bound).",
    ]
    if tube_nozzle_objective == "MAX_MARGIN_WITHIN_VELOCITY_BAND":
        disclosures_list.append(
            "Tube nozzle uses largest ID within 1–3 m/s band for mid-band pressure margin probe."
        )
    if shell_nozzle_objective == "MAX_MARGIN_WITHIN_VELOCITY_BAND":
        disclosures_list.append(
            "Shell nozzle uses largest ID within 1–3 m/s band for mid-band shell margin probe."
        )
    if tube_outlet_temperature_k is not None:
        disclosures_list.append(
            "Outlet port velocities use INDICATIVE_THERMAL_PRESCREEN_OUTLET density (ε-NTU), "
            "not Task173 converged state."
        )
        disclosures_list.append(
            "When outlet T is set, R27B outlet nozzles/transitions use COOLPROP_TP in full-path "
            "calculation (experimental prescreen path only)."
        )
    disclosures = tuple(disclosures_list)

    fixed = select_fixed_nozzle_design(
        case=case,
        record=record,
        postpass=postpass,
        tube_nozzle_objective=tube_nozzle_objective,
        shell_nozzle_objective=shell_nozzle_objective,
        fixed_tube_inside_diameter_m=fixed_tube_inside_diameter_m,
        fixed_shell_inside_diameter_m=fixed_shell_inside_diameter_m,
    )
    _computable_bisect = frozenset(
        {
            "FEASIBLE_WITHIN_DESIGN_BOUNDS",
            "FIXED_OVERRIDE",
            "NO_FEASIBLE_WITHIN_DESIGN_BOUNDS",
        }
    )
    search_notes: list[str] = []
    if fixed.shell_select_status == "NO_FEASIBLE_WITHIN_DESIGN_BOUNDS":
        search_notes.append("SHELL_NOZZLE_SEARCH_NO_FEASIBLE_POINT_IN_VELOCITY_BAND")
    elif fixed.shell_select_status not in _computable_bisect:
        blockers.append(f"SHELL_NOZZLE_BISECT:{fixed.shell_select_status}")
    if fixed.tube_select_status == "NO_FEASIBLE_WITHIN_DESIGN_BOUNDS":
        search_notes.append("TUBE_NOZZLE_SEARCH_NO_FEASIBLE_POINT_IN_VELOCITY_BAND")
    elif fixed.tube_select_status not in _computable_bisect:
        blockers.append(f"TUBE_NOZZLE_BISECT:{fixed.tube_select_status}")

    tube_out_state: tuple[Decimal, Decimal] | None = None
    shell_out_state: tuple[Decimal, Decimal] | None = None
    if tube_outlet_temperature_k is not None:
        tube_out_state = (
            tube_outlet_temperature_k,
            Decimal(str(case.tube_side.inlet_pressure_pa)),
        )
    if shell_outlet_temperature_k is not None:
        shell_out_state = (
            shell_outlet_temperature_k,
            Decimal(str(case.shell_side.inlet_pressure_pa)),
        )

    evals = evaluate_fixed_nozzle_all_scenarios(
        case=case,
        record=record,
        postpass=postpass,
        fixed=fixed,
        tube_outlet_state_k_pa=tube_out_state,
        shell_outlet_state_k_pa=shell_out_state,
    )
    scenario_rows: list[FullPathScenarioResult] = []
    for ev in evals:
        scenario_rows.append(
            FullPathScenarioResult(
                scenario_key=ev.scenario_key,
                tube_dp_authority=ev.tube.authority,
                shell_dp_authority=ev.shell.authority,
                tube_full_path_dp_pa=ev.tube.total_dp_pa,
                shell_full_path_dp_pa=ev.shell.total_dp_pa,
                tube_margin_pa=ev.tube.margin_pa,
                shell_margin_pa=ev.shell.margin_pa,
                tube_breakdown=dict(ev.tube.components),
                shell_breakdown=dict(ev.shell.components),
                hydraulic_check=ev.hydraulic_check,
                full_path_feasible=ev.full_path_feasible,
                overall_fp_status=ev.overall_fp_status,
            )
        )

    active = provider or CoolPropProvider()
    ports = _port_designs(
        case_engineering=case,
        tube_d_m=fixed.tube_inside_diameter_m,
        shell_d_m=fixed.shell_inside_diameter_m,
        provider=active,
        tube_outlet_temperature_k=tube_outlet_temperature_k,
        shell_outlet_temperature_k=shell_outlet_temperature_k,
    )
    all_vel_ok = all(_velocity_in_band(p.velocity_m_s) for p in ports)
    velocity_check: CheckStatus = "PASS" if all_vel_ok else "BLOCKED"
    if not all_vel_ok:
        blockers.append("NOZZLE_VELOCITY_OUTSIDE_1_3_M_S")

    scenario_robust = classify_scenario_robustness(evals)
    install = _installation_authority(
        record, fixed.tube_inside_diameter_m, fixed.shell_inside_diameter_m
    )

    tube_lim = bindings.normalized.max_tube_side_pressure_drop_pa
    shell_lim = bindings.normalized.max_shell_side_pressure_drop_pa
    tube_dp = t174.modeled_total_tube_side_pressure_drop_pa
    shell_dp = t174.bell_total_shell_pressure_drop_pa
    exp = postpass.get("experimental_transitional_tube_hydraulic") or {}

    task174_partial = Task174PartialHydraulics(
        tube_dp_pa=str(tube_dp),
        shell_dp_pa=str(shell_dp),
        tube_margin_pa=str(tube_lim - tube_dp),
        shell_margin_pa=str(shell_lim - shell_dp),
        authority="TASK174_PARTIAL_DP",
        tube_friction_dp_pa=str(exp.get("tube_friction_dp_pa"))
        if exp.get("tube_friction_dp_pa")
        else None,
        tube_local_dp_pa=str(exp.get("tube_local_loss_dp_pa"))
        if exp.get("tube_local_loss_dp_pa")
        else None,
        shell_bell_total_dp_pa=str(shell_dp),
    )

    bisect_outcome = NozzleBisectOutcome(
        tube_select_status=fixed.tube_select_status,
        shell_select_status=fixed.shell_select_status,
        tube_inside_diameter_m=str(fixed.tube_inside_diameter_m),
        shell_inside_diameter_m=str(fixed.shell_inside_diameter_m),
        search_infeasible_notes=tuple(search_notes),
    )
    return AutonomousNozzleFullPathReport(
        case_id=bindings.engineering_case_id,
        candidate_id=bindings.rating_request.candidate_id,
        structural_geometry_hash=bindings.geometry_projection_hash,
        nozzle_design_hash=_nozzle_design_hash(ports),
        nozzle_size_authority="PARAMETRIC_CALCULATED",
        ports=ports,
        nozzle_velocity_check=velocity_check,
        nozzle_same_geometry_all_scenarios=True,
        installation=install,
        full_path_dp_authority="ASSUMPTION_BASED",
        scenario_robustness=scenario_robust,
        scenarios=tuple(scenario_rows),
        task174_partial=task174_partial,
        nozzle_bisect=bisect_outcome,
        remaining_blockers=tuple(blockers),
        disclosure=disclosures,
    )


@dataclass(frozen=True)
class ManufacturableHydraulicInventory:
    manufacturable_valid_count: int
    task174_hydraulic_feasible_count: int
    full_path_mid_feasible_count: int
    full_path_all_scenario_feasible_count: int
    distinct_full_path_feasible_geometries: int
    per_candidate: tuple[dict[str, Any], ...]
    gap_notes: tuple[str, ...]


def scan_manufacturable_full_path_inventory(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
    max_candidates: int = 64,
    enumerate_fn: Any = None,
) -> ManufacturableHydraulicInventory:
    active = provider or CoolPropProvider()
    if enumerate_fn is None:
        _space_hash, t168_digest, bundles, geom = enumerate_structural_bundles(
            normalized, handoff, max_valid=max_candidates
        )
    else:
        _space_hash, t168_digest, bundles, geom = enumerate_fn(
            normalized, handoff, max_valid=max_candidates
        )
    per: list[dict[str, Any]] = []
    mfg = len(bundles)
    t174_ok = 0
    mid_ok = 0
    all_ok = 0
    feasible_geometries: set[str] = set()
    for bundle in bundles:
        bindings = build_candidate_rating_bindings(
            bundle,
            space_hash=_space_hash,
            t168_digest=t168_digest,
            normalized=normalized,
            handoff=handoff,
            provider=active,
            geometry_projection_hash=geom.get(bundle.candidate.candidate_id, ""),
        )
        if bindings is None:
            per.append({"candidate_id": bundle.candidate.candidate_id, "status": "TASK174_BLOCKED"})
            continue
        t174 = bindings.rating_request.task174_result
        tube_lim = bindings.normalized.max_tube_side_pressure_drop_pa
        shell_lim = bindings.normalized.max_shell_side_pressure_drop_pa
        partial_ok = (
            t174.modeled_total_tube_side_pressure_drop_pa <= tube_lim
            and t174.bell_total_shell_pressure_drop_pa <= shell_lim
        )
        if partial_ok:
            t174_ok += 1
        if not partial_ok:
            per.append(
                {
                    "candidate_id": bindings.rating_request.candidate_id,
                    "geometry_hash": bindings.geometry_projection_hash,
                    "first_blocker": "TASK174_PARTIAL_DP_EXCEEDS_LIMIT",
                }
            )
            continue
        try:
            report = run_autonomous_nozzle_full_path(bindings)
        except Exception as exc:  # noqa: BLE001
            per.append(
                {
                    "candidate_id": bindings.rating_request.candidate_id,
                    "autonomous_error": type(exc).__name__,
                }
            )
            continue
        mid = next(s for s in report.scenarios if s.scenario_key == "mid_band")
        if mid.hydraulic_check == "PASS":
            mid_ok += 1
            feasible_geometries.add(report.structural_geometry_hash)
        if report.scenario_robustness == "PASS":
            all_ok += 1
        per.append(
            {
                "candidate_id": report.candidate_id,
                "geometry_hash": report.structural_geometry_hash,
                "scenario_robustness": report.scenario_robustness,
                "mid_band_check": mid.hydraulic_check,
                "nozzle_design_hash": report.nozzle_design_hash,
            }
        )

    gaps: list[str] = []
    if len(feasible_geometries) < 2:
        gaps.append(f"DISTINCT_FULL_PATH_FEASIBLE_GEOMETRIES={len(feasible_geometries)}<2")
    return ManufacturableHydraulicInventory(
        manufacturable_valid_count=mfg,
        task174_hydraulic_feasible_count=t174_ok,
        full_path_mid_feasible_count=mid_ok,
        full_path_all_scenario_feasible_count=all_ok,
        distinct_full_path_feasible_geometries=len(feasible_geometries),
        per_candidate=tuple(per),
        gap_notes=tuple(gaps),
    )


__all__ = [
    "AutonomousNozzleFullPathReport",
    "FullPathScenarioResult",
    "ManufacturableHydraulicInventory",
    "MechanicalInstallationAuthority",
    "NozzleBisectOutcome",
    "NozzlePortDesign",
    "Task174PartialHydraulics",
    "run_autonomous_nozzle_full_path",
    "scan_manufacturable_full_path_inventory",
]
