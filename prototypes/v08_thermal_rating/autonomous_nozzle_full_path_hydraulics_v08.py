"""Autonomous four-port nozzle sizing and R27C full-path hydraulic closure for V08."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from hexagent.canonical_json import canonical_sha256
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    NOZZLE_VELOCITY_DESIGN_RULE,
    estimate_preliminary_nozzle_diameters,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    nozzle_flow_area_m2,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    LossScenarioKey,
    _geometry_fit_risk,
    _side_inlet_density_kg_m3,
    _velocity_from_diameter_m,
    cooptimize_nozzles_for_candidate_scenario,
)
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CandidateRatingBindings,
    build_candidate_rating_bindings,
    enumerate_structural_bundles,
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
CheckStatus = Literal["PASS", "BLOCKED", "UNRESOLVED"]


@dataclass(frozen=True)
class NozzlePortDesign:
    port_id: Literal["TUBE_INLET", "TUBE_OUTLET", "SHELL_INLET", "SHELL_OUTLET"]
    inside_diameter_m: Decimal
    velocity_m_s: Decimal
    effective_area_m2: Decimal
    mass_flow_kg_s: Decimal
    density_kg_m3: Decimal
    size_authority: NozzleSizeAuthority
    multiplicity: int


@dataclass(frozen=True)
class FullPathScenarioResult:
    scenario_key: LossScenarioKey
    tube_full_path_dp_pa: str | None
    shell_full_path_dp_pa: str | None
    tube_margin_pa: str | None
    shell_margin_pa: str | None
    hydraulic_check: CheckStatus
    overall_status: str
    tube_nozzle_inside_diameter_m: str | None
    shell_nozzle_inside_diameter_m: str | None
    full_path_feasible: bool
    tube_modeled_side_dp_pa: str | None
    shell_modeled_side_dp_pa: str | None


@dataclass(frozen=True)
class AutonomousNozzleFullPathReport:
    case_id: str
    candidate_id: str
    structural_geometry_hash: str
    nozzle_design_hash: str
    nozzle_size_authority: NozzleSizeAuthority
    ports: tuple[NozzlePortDesign, ...]
    nozzle_velocity_check: CheckStatus
    nozzle_installation_check: CheckStatus
    full_path_dp_authority: Literal["ASSUMPTION_BASED"]
    scenarios: tuple[FullPathScenarioResult, ...]
    task174_baseline_tube_dp_pa: str
    task174_baseline_shell_dp_pa: str
    remaining_blockers: tuple[str, ...]
    disclosure: tuple[str, ...]


def _velocity_in_band(v: Decimal) -> bool:
    # Allow numeric noise at band edge (e.g. 1.0 m/s target from float diameter solve).
    return Decimal("0.999") <= v <= Decimal("3.001")


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
    tube_v = Decimal(
        str(
            _velocity_from_diameter_m(
                mass_flow_kg_s=float(tube_m),
                rho=float(tube_rho),
                diameter_m=float(tube_d_m),
            )
        )
    )
    shell_v = Decimal(
        str(
            _velocity_from_diameter_m(
                mass_flow_kg_s=float(shell_m),
                rho=float(shell_rho),
                diameter_m=float(shell_d_m),
            )
        )
    )
    tube_area = Decimal(str(nozzle_flow_area_m2(tube_d_m)))
    shell_area = Decimal(str(nozzle_flow_area_m2(shell_d_m)))
    authority: NozzleSizeAuthority = "PARAMETRIC_CALCULATED"
    ports = (
        NozzlePortDesign(
            port_id="TUBE_INLET",
            inside_diameter_m=tube_d_m,
            velocity_m_s=tube_v,
            effective_area_m2=tube_area,
            mass_flow_kg_s=tube_m,
            density_kg_m3=tube_rho,
            size_authority=authority,
            multiplicity=1,
        ),
        NozzlePortDesign(
            port_id="TUBE_OUTLET",
            inside_diameter_m=tube_d_m,
            velocity_m_s=tube_v,
            effective_area_m2=tube_area,
            mass_flow_kg_s=tube_m,
            density_kg_m3=tube_rho,
            size_authority=authority,
            multiplicity=1,
        ),
        NozzlePortDesign(
            port_id="SHELL_INLET",
            inside_diameter_m=shell_d_m,
            velocity_m_s=shell_v,
            effective_area_m2=shell_area,
            mass_flow_kg_s=shell_m,
            density_kg_m3=shell_rho,
            size_authority=authority,
            multiplicity=1,
        ),
        NozzlePortDesign(
            port_id="SHELL_OUTLET",
            inside_diameter_m=shell_d_m,
            velocity_m_s=shell_v,
            effective_area_m2=shell_area,
            mass_flow_kg_s=shell_m,
            density_kg_m3=shell_rho,
            size_authority=authority,
            multiplicity=1,
        ),
    )
    return ports


def _installation_check(record: Any, tube_d: Decimal, shell_d: Decimal) -> CheckStatus:
    risk = _geometry_fit_risk(
        record=record,
        tube_nozzle_d_m=float(tube_d),
        shell_nozzle_d_m=float(shell_d),
    )
    flags = risk.get("geometry_adaptation_risk_flags") or []
    if flags:
        return "BLOCKED"
    return "PASS"


def run_autonomous_nozzle_full_path(
    bindings: CandidateRatingBindings,
) -> AutonomousNozzleFullPathReport:
    """Size tube/shell nozzles via R27C co-optimization; report all loss scenarios."""
    case = build_engineering_case_v2_from_v08(bindings.normalized)
    record = candidate_selection_record_from_bindings(bindings)
    postpass = task174_hydraulic_postpass_from_bindings(bindings)
    t174 = bindings.rating_request.task174_result
    blockers: list[str] = []
    disclosures = (
        "Nozzle IDs from R27C nozzle_pressure_budget_solver co-optimization.",
        "Loss coefficients: R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS (not owner-verified K).",
        "No authorized standard nozzle diameter catalog in V08-02 space — PARAMETRIC_CALCULATED.",
        "Tube-side nozzle velocity uses connection area; not Task025 bundle bulk velocity.",
    )

    scenario_rows: list[FullPathScenarioResult] = []
    reference_tube_d: Decimal | None = None
    reference_shell_d: Decimal | None = None

    for key in LOSS_SCENARIOS:
        opt = cooptimize_nozzles_for_candidate_scenario(
            case=case,
            record=record,
            postpass=postpass,
            loss_scenario_key=key,
        )
        fp = opt.get("full_path_hydraulic_verification") or {}
        tube_dp = fp.get("TUBE_FULL_PATH_TOTAL_DP_PA")
        shell_dp = fp.get("SHELL_FULL_PATH_TOTAL_DP_PA")
        tube_ok = fp.get("FULL_PATH_TUBE_CONSTRAINT_STATUS") == "SATISFIED"
        shell_ok = fp.get("FULL_PATH_SHELL_CONSTRAINT_STATUS") == "SATISFIED"
        feasible = bool(opt.get("full_path_feasible"))
        if feasible and tube_ok and shell_ok:
            check: CheckStatus = "PASS"
        elif opt.get("status") == "BLOCKED_APPLICABILITY":
            check = "UNRESOLVED"
            blockers.append(f"SCENARIO_{key}:BLOCKED_APPLICABILITY")
        else:
            check = "BLOCKED"

        tube_solve = opt.get("tube_nozzle_solve") or {}
        shell_solve = opt.get("shell_nozzle_solve") or {}
        if key == "mid_band":
            if tube_solve.get("selected_inside_diameter_m") is not None:
                reference_tube_d = Decimal(str(tube_solve["selected_inside_diameter_m"]))
            shell_pick = shell_solve.get("selected_inside_diameter_m")
            if shell_pick is None:
                shell_pick = shell_solve.get("theoretical_at_band_max_diameter_m")
            if shell_pick is not None:
                reference_shell_d = Decimal(str(shell_pick))

        scenario_rows.append(
            FullPathScenarioResult(
                scenario_key=key,
                tube_full_path_dp_pa=str(tube_dp) if tube_dp is not None else None,
                shell_full_path_dp_pa=str(shell_dp) if shell_dp is not None else None,
                tube_margin_pa=str(fp.get("TUBE_FULL_PATH_DP_MARGIN_PA"))
                if fp.get("TUBE_FULL_PATH_DP_MARGIN_PA") is not None
                else None,
                shell_margin_pa=str(fp.get("SHELL_FULL_PATH_DP_MARGIN_PA"))
                if fp.get("SHELL_FULL_PATH_DP_MARGIN_PA") is not None
                else None,
                hydraulic_check=check,
                overall_status=str(opt.get("overall_scenario_status", "UNKNOWN")),
                tube_nozzle_inside_diameter_m=(
                    str(tube_solve.get("selected_inside_diameter_m"))
                    if tube_solve.get("selected_inside_diameter_m") is not None
                    else None
                ),
                shell_nozzle_inside_diameter_m=(
                    str(shell_solve.get("selected_inside_diameter_m"))
                    if shell_solve.get("selected_inside_diameter_m") is not None
                    else (
                        str(shell_solve.get("theoretical_at_band_max_diameter_m"))
                        if shell_solve.get("theoretical_at_band_max_diameter_m") is not None
                        else None
                    )
                ),
                full_path_feasible=feasible,
                tube_modeled_side_dp_pa=(
                    str(tube_solve.get("modeled_side_total_dp_pa"))
                    if tube_solve.get("modeled_side_total_dp_pa") is not None
                    else None
                ),
                shell_modeled_side_dp_pa=(
                    str(shell_solve.get("modeled_side_total_dp_pa"))
                    if shell_solve.get("modeled_side_total_dp_pa") is not None
                    else (
                        str(shell_solve.get("dp_at_max_diameter_min_velocity_pa"))
                        if shell_solve.get("dp_at_max_diameter_min_velocity_pa") is not None
                        else None
                    )
                ),
            )
        )

    if reference_tube_d is None or reference_shell_d is None:
        prelim = estimate_preliminary_nozzle_diameters(case)
        mid_tube = prelim["sides"]["tube_side"]["diameter_candidates_m"][2]["inside_diameter_m"]
        mid_shell = prelim["sides"]["shell_side"]["diameter_candidates_m"][2]["inside_diameter_m"]
        reference_tube_d = reference_tube_d or Decimal(str(mid_tube))
        reference_shell_d = reference_shell_d or Decimal(str(mid_shell))
        blockers.append("R27C_PARTIAL_BISECT_FALLBACK_TO_PRELIMINARY_MID_BAND")
    mid = next((s for s in scenario_rows if s.scenario_key == "mid_band"), None)
    shell_infeasible = (
        mid is not None
        and mid.shell_nozzle_inside_diameter_m is not None
        and not mid.full_path_feasible
    )
    if shell_infeasible:
        blockers.append("SHELL_FIXED_TRANSITIONS_AND_BUNDLE_DOMINATE_DP_BUDGET")

    ports = _port_designs(
        case_engineering=case, tube_d_m=reference_tube_d, shell_d_m=reference_shell_d
    )
    all_vel_ok = all(_velocity_in_band(p.velocity_m_s) for p in ports)
    velocity_check: CheckStatus = "PASS" if all_vel_ok else "BLOCKED"
    if not all_vel_ok:
        blockers.append("NOZZLE_VELOCITY_OUTSIDE_1_3_M_S")

    install_check = _installation_check(record, reference_tube_d, reference_shell_d)

    return AutonomousNozzleFullPathReport(
        case_id=bindings.engineering_case_id,
        candidate_id=bindings.rating_request.candidate_id,
        structural_geometry_hash=bindings.geometry_projection_hash,
        nozzle_design_hash=_nozzle_design_hash(ports),
        nozzle_size_authority="PARAMETRIC_CALCULATED",
        ports=ports,
        nozzle_velocity_check=velocity_check,
        nozzle_installation_check=install_check,
        full_path_dp_authority="ASSUMPTION_BASED",
        scenarios=tuple(scenario_rows),
        task174_baseline_tube_dp_pa=str(t174.modeled_total_tube_side_pressure_drop_pa),
        task174_baseline_shell_dp_pa=str(t174.bell_total_shell_pressure_drop_pa),
        remaining_blockers=tuple(blockers),
        disclosure=disclosures,
    )


@dataclass(frozen=True)
class ManufacturableHydraulicInventory:
    manufacturable_valid_count: int
    task174_hydraulic_feasible_count: int
    full_path_hydraulic_feasible_count: int
    scenario_feasible_mid_band: int
    per_candidate: tuple[dict[str, Any], ...]
    gap_notes: tuple[str, ...]


def scan_manufacturable_full_path_inventory(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
    max_candidates: int = 64,
) -> ManufacturableHydraulicInventory:
    """Enumerate V08 structural candidates; run autonomous nozzle + full-path per binding."""
    active = provider or CoolPropProvider()
    _space_hash, t168_digest, bundles, geom = enumerate_structural_bundles(
        normalized, handoff, max_valid=max_candidates
    )
    per: list[dict[str, Any]] = []
    mfg = len(bundles)
    t174_ok = 0
    full_ok = 0
    mid_ok = 0
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
            per.append(
                {
                    "candidate_id": bundle.candidate.candidate_id,
                    "status": "TASK174_BLOCKED",
                }
            )
            continue
        tube_lim = bindings.normalized.max_tube_side_pressure_drop_pa
        shell_lim = bindings.normalized.max_shell_side_pressure_drop_pa
        t174 = bindings.rating_request.task174_result
        partial_ok = (
            t174.modeled_total_tube_side_pressure_drop_pa <= tube_lim
            and t174.bell_total_shell_pressure_drop_pa <= shell_lim
        )
        if partial_ok:
            t174_ok += 1
        try:
            report = run_autonomous_nozzle_full_path(bindings)
        except Exception as exc:  # noqa: BLE001 — inventory must not abort
            per.append(
                {
                    "candidate_id": bindings.rating_request.candidate_id,
                    "geometry_hash": bindings.geometry_projection_hash,
                    "partial_hydraulic_pass": partial_ok,
                    "autonomous_error": type(exc).__name__,
                }
            )
            continue
        mid = next(s for s in report.scenarios if s.scenario_key == "mid_band")
        if mid.full_path_feasible:
            full_ok += 1
        if mid.hydraulic_check == "PASS":
            mid_ok += 1
        per.append(
            {
                "candidate_id": report.candidate_id,
                "geometry_hash": report.structural_geometry_hash,
                "partial_hydraulic_pass": partial_ok,
                "nozzle_velocity_check": report.nozzle_velocity_check,
                "mid_band_full_path": mid.hydraulic_check,
                "nozzle_design_hash": report.nozzle_design_hash,
            }
        )

    gaps: list[str] = []
    if full_ok < 2:
        gaps.append(
            f"FULL_PATH_HYDRAULIC_FEASIBLE_COUNT={full_ok}<2: "
            "discrete structural space insufficient for two independent qualified structures."
        )
    if t174_ok < mfg:
        gaps.append(
            f"Only {t174_ok}/{mfg} manufacturable structures pass Task174 partial Δp vs "
            f"{normalized.max_tube_side_pressure_drop_pa}/{normalized.max_shell_side_pressure_drop_pa} Pa limits."
        )

    return ManufacturableHydraulicInventory(
        manufacturable_valid_count=mfg,
        task174_hydraulic_feasible_count=t174_ok,
        full_path_hydraulic_feasible_count=full_ok,
        scenario_feasible_mid_band=mid_ok,
        per_candidate=tuple(per),
        gap_notes=tuple(gaps),
    )


__all__ = [
    "AutonomousNozzleFullPathReport",
    "ManufacturableHydraulicInventory",
    "NozzlePortDesign",
    "run_autonomous_nozzle_full_path",
    "scan_manufacturable_full_path_inventory",
]
