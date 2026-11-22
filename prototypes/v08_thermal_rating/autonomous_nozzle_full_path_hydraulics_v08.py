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
VelocityBasis = Literal["INLET_TP_PROPERTY", "PROVISIONAL_SYMMETRIC_INLET"]


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
    remaining_blockers: tuple[str, ...]
    disclosure: tuple[str, ...]


def _velocity_in_band(v: Decimal) -> bool:
    return Decimal("1") <= v <= Decimal("3")


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
) -> tuple[NozzlePortDesign, ...]:
    tube_rho = Decimal(str(_side_inlet_density_kg_m3(case_engineering, "tube_side")))
    shell_rho = Decimal(str(_side_inlet_density_kg_m3(case_engineering, "shell_side")))
    tube_m = Decimal(str(case_engineering.tube_side.mass_flow_kg_s))
    shell_m = Decimal(str(case_engineering.shell_side.mass_flow_kg_s))
    from prototypes.v08_thermal_rating.full_path_fixed_nozzle_evaluator_v08 import (
        _decimal_velocity_m_s,
    )

    tube_v = _decimal_velocity_m_s(mass_flow_kg_s=tube_m, rho=tube_rho, diameter_m=tube_d_m)
    shell_v = _decimal_velocity_m_s(mass_flow_kg_s=shell_m, rho=shell_rho, diameter_m=shell_d_m)
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

    return (
        port("TUBE_INLET", tube_d_m, tube_v, tube_area, tube_m, tube_rho, "INLET_TP_PROPERTY"),
        port(
            "TUBE_OUTLET",
            tube_d_m,
            tube_v,
            tube_area,
            tube_m,
            tube_rho,
            "PROVISIONAL_SYMMETRIC_INLET",
        ),
        port(
            "SHELL_INLET", shell_d_m, shell_v, shell_area, shell_m, shell_rho, "INLET_TP_PROPERTY"
        ),
        port(
            "SHELL_OUTLET",
            shell_d_m,
            shell_v,
            shell_area,
            shell_m,
            shell_rho,
            "PROVISIONAL_SYMMETRIC_INLET",
        ),
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
) -> AutonomousNozzleFullPathReport:
    case = build_engineering_case_v2_from_v08(bindings.normalized)
    record = candidate_selection_record_from_bindings(bindings)
    postpass = task174_hydraulic_postpass_from_bindings(bindings)
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
    disclosures = tuple(disclosures_list)

    fixed = select_fixed_nozzle_design(
        case=case,
        record=record,
        postpass=postpass,
        tube_nozzle_objective=tube_nozzle_objective,
    )
    if fixed.shell_select_status != "FEASIBLE_WITHIN_DESIGN_BOUNDS":
        blockers.append(f"SHELL_NOZZLE_BISECT:{fixed.shell_select_status}")
    if fixed.tube_select_status != "FEASIBLE_WITHIN_DESIGN_BOUNDS":
        blockers.append(f"TUBE_NOZZLE_BISECT:{fixed.tube_select_status}")

    evals = evaluate_fixed_nozzle_all_scenarios(
        case=case, record=record, postpass=postpass, fixed=fixed
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

    ports = _port_designs(
        case_engineering=case,
        tube_d_m=fixed.tube_inside_diameter_m,
        shell_d_m=fixed.shell_inside_diameter_m,
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
    "NozzlePortDesign",
    "Task174PartialHydraulics",
    "run_autonomous_nozzle_full_path",
    "scan_manufacturable_full_path_inventory",
]
