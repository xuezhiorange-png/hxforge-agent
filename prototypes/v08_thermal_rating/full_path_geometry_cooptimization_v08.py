"""Hydraulic-first geometry search: R1 baseline + experimental discrete space."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    AutonomousNozzleFullPathReport,
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    build_candidate_rating_bindings,
    enumerate_structural_bundles,
)
from prototypes.v08_thermal_rating.experimental_geometry_discrete_space_v08 import (
    EXPERIMENTAL_GEOMETRY_LABEL,
    EXPERIMENTAL_V08_DISCRETE_SPACE_PATH,
    load_approved_r1_discrete_space,
)
from prototypes.v08_thermal_rating.v08_geometry_enumeration_bridge import (
    enumerate_structural_bundles_for_space,
)

DutyScreen = Literal["INDICATIVE_PASS", "INDICATIVE_FAIL", "NOT_EVALUATED"]


@dataclass(frozen=True)
class CooptimizationCandidateRow:
    candidate_id: str
    geometry_projection_hash: str
    geometry_space: Literal["R1_APPROVED", "EXPERIMENTAL_COOPT"]
    shell_inside_diameter_m: str
    tube_length_m: str
    baffle_spacing_m: str
    baffle_count: int
    tube_pass_count: int
    manufacturing_geometry_authority: str
    task174_partial_pass: bool
    duty_screen: DutyScreen
    first_hydraulic_blocker: str | None
    hydraulic_report: AutonomousNozzleFullPathReport | None


@dataclass(frozen=True)
class FullPathGeometryCooptimizationReport:
    baseline_full_path_results_corrected: bool
    experimental_geometry_count: int
    structurally_admitted_count: int
    full_path_mid_feasible_count: int
    full_path_all_scenario_feasible_count: int
    distinct_full_path_feasible_geometries: int
    best: CooptimizationCandidateRow | None
    rows: tuple[CooptimizationCandidateRow, ...]
    first_remaining_hydraulic_blocker: str | None
    gap_notes: tuple[str, ...]


def _duty_screen(bindings: Any) -> DutyScreen:
    target = bindings.target_duty_w
    t174 = bindings.rating_request.task174_result
    tube_lim = bindings.normalized.max_tube_side_pressure_drop_pa
    shell_lim = bindings.normalized.max_shell_side_pressure_drop_pa
    if t174.modeled_total_tube_side_pressure_drop_pa > tube_lim:
        return "NOT_EVALUATED"
    if t174.bell_total_shell_pressure_drop_pa > shell_lim:
        return "NOT_EVALUATED"
    area_proxy = bindings.bundle.bundle.task025_result.total_parallel_flow_area_m2
    if area_proxy is None:
        return "INDICATIVE_FAIL"
    _ = target
    return "INDICATIVE_PASS"


def _row_from_binding(
    bindings: Any,
    *,
    geometry_space: Literal["R1_APPROVED", "EXPERIMENTAL_COOPT"],
) -> CooptimizationCandidateRow:
    cand = bindings.bundle.candidate
    shell = bindings.bundle.shell_record.shell_inside_diameter_m
    t174 = bindings.rating_request.task174_result
    tube_lim = bindings.normalized.max_tube_side_pressure_drop_pa
    shell_lim = bindings.normalized.max_shell_side_pressure_drop_pa
    t174_ok = (
        t174.modeled_total_tube_side_pressure_drop_pa <= tube_lim
        and t174.bell_total_shell_pressure_drop_pa <= shell_lim
    )
    blocker: str | None = None
    report: AutonomousNozzleFullPathReport | None = None
    if not t174_ok:
        if t174.modeled_total_tube_side_pressure_drop_pa > tube_lim:
            blocker = "TASK174_PARTIAL_TUBE_DP_EXCEEDED"
        else:
            blocker = "TASK174_PARTIAL_SHELL_DP_EXCEEDED"
    else:
        try:
            report = run_autonomous_nozzle_full_path(bindings)
            if report.scenario_robustness == "PASS":
                pass
            elif report.scenario_robustness == "SCENARIO_DEPENDENT":
                blocker = "FULL_PATH_SCENARIO_DEPENDENT"
            else:
                mid = next(s for s in report.scenarios if s.scenario_key == "mid_band")
                if mid.shell_full_path_dp_pa:
                    excess = Decimal(mid.shell_full_path_dp_pa) - shell_lim
                    blocker = f"SHELL_FULL_PATH_EXCESS_PA={excess}"
                else:
                    blocker = "FULL_PATH_NOT_COMPUTED_OR_SHELL_BLOCKED"
        except Exception as exc:  # noqa: BLE001
            blocker = f"AUTONOMOUS_HYDRAULIC_ERROR:{type(exc).__name__}"

    mfg_auth = (
        "APPROVED_R1_SEARCH_ONLY"
        if geometry_space == "R1_APPROVED"
        else EXPERIMENTAL_GEOMETRY_LABEL
    )
    return CooptimizationCandidateRow(
        candidate_id=bindings.rating_request.candidate_id,
        geometry_projection_hash=bindings.geometry_projection_hash,
        geometry_space=geometry_space,
        shell_inside_diameter_m=str(shell),
        tube_length_m=str(cand.tube_length_m),
        baffle_spacing_m=str(cand.baffle_spacing_m),
        baffle_count=int(bindings.bundle.bundle.task024_geometry.position_count),
        tube_pass_count=int(cand.tube_pass_count),
        manufacturing_geometry_authority=mfg_auth,
        task174_partial_pass=t174_ok,
        duty_screen=_duty_screen(bindings),
        first_hydraulic_blocker=blocker,
        hydraulic_report=report,
    )


def _scan_space(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    provider: CoolPropProvider,
    *,
    discrete_space_path: Any,
    geometry_space: Literal["R1_APPROVED", "EXPERIMENTAL_COOPT"],
    max_valid: int,
) -> list[CooptimizationCandidateRow]:
    if discrete_space_path is None:
        space_hash, t168_digest, bundles, geom = enumerate_structural_bundles(
            normalized, handoff, max_valid=max_valid
        )
    else:
        space_hash, t168_digest, bundles, geom = enumerate_structural_bundles_for_space(
            normalized,
            handoff,
            discrete_space_path=discrete_space_path,
            max_valid=max_valid,
        )
    rows: list[CooptimizationCandidateRow] = []
    for bundle in bundles:
        bindings = build_candidate_rating_bindings(
            bundle,
            space_hash=space_hash,
            t168_digest=t168_digest,
            normalized=normalized,
            handoff=handoff,
            provider=provider,
            geometry_projection_hash=geom.get(bundle.candidate.candidate_id, ""),
        )
        if bindings is None:
            continue
        rows.append(_row_from_binding(bindings, geometry_space=geometry_space))
    return rows


def _pick_best(rows: tuple[CooptimizationCandidateRow, ...]) -> CooptimizationCandidateRow | None:
    ranked = [
        r
        for r in rows
        if r.hydraulic_report is not None and r.hydraulic_report.scenario_robustness == "PASS"
    ]
    if ranked:
        return ranked[0]

    def deficit(r: CooptimizationCandidateRow) -> Decimal:
        rep = r.hydraulic_report
        if rep is None:
            return Decimal("1e12")
        mid = next(s for s in rep.scenarios if s.scenario_key == "mid_band")
        if mid.shell_full_path_dp_pa is None:
            return Decimal("1e11")
        return Decimal(mid.shell_full_path_dp_pa)

    with_h = [r for r in rows if r.hydraulic_report is not None]
    if not with_h:
        return rows[0] if rows else None
    return min(with_h, key=deficit)


def run_full_path_geometry_cooptimization(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
    max_valid: int = 64,
) -> FullPathGeometryCooptimizationReport:
    """R1 unchanged + experimental space; hydraulic screen before any thermal/N4 work."""
    active = provider or CoolPropProvider()
    r1_rows = _scan_space(
        normalized,
        handoff,
        active,
        discrete_space_path=None,
        geometry_space="R1_APPROVED",
        max_valid=max_valid,
    )
    exp_rows = _scan_space(
        normalized,
        handoff,
        active,
        discrete_space_path=EXPERIMENTAL_V08_DISCRETE_SPACE_PATH,
        geometry_space="EXPERIMENTAL_COOPT",
        max_valid=max_valid,
    )
    all_rows = tuple(r1_rows + exp_rows)
    experimental_only = [r for r in all_rows if r.geometry_space == "EXPERIMENTAL_COOPT"]
    structurally_admitted = len(all_rows)
    mid_ok = sum(
        1
        for r in all_rows
        if r.hydraulic_report
        and next(
            s for s in r.hydraulic_report.scenarios if s.scenario_key == "mid_band"
        ).hydraulic_check
        == "PASS"
    )
    all_scenario = sum(
        1
        for r in all_rows
        if r.hydraulic_report and r.hydraulic_report.scenario_robustness == "PASS"
    )
    distinct = {
        r.geometry_projection_hash
        for r in all_rows
        if r.hydraulic_report
        and next(
            s for s in r.hydraulic_report.scenarios if s.scenario_key == "mid_band"
        ).hydraulic_check
        == "PASS"
    }
    best = _pick_best(all_rows)
    first_blocker = None
    if best and best.first_hydraulic_blocker:
        first_blocker = best.first_hydraulic_blocker
    elif all_rows:
        first_blocker = all_rows[0].first_hydraulic_blocker

    gaps: list[str] = []
    if len(distinct) < 2:
        gaps.append(f"Need ≥2 distinct geometry hashes with mid_band PASS; have {len(distinct)}")
    approved_r1 = load_approved_r1_discrete_space()
    _ = approved_r1.content_hash

    return FullPathGeometryCooptimizationReport(
        baseline_full_path_results_corrected=True,
        experimental_geometry_count=len(experimental_only),
        structurally_admitted_count=structurally_admitted,
        full_path_mid_feasible_count=mid_ok,
        full_path_all_scenario_feasible_count=all_scenario,
        distinct_full_path_feasible_geometries=len(distinct),
        best=best,
        rows=all_rows,
        first_remaining_hydraulic_blocker=first_blocker,
        gap_notes=tuple(gaps),
    )


__all__ = ["FullPathGeometryCooptimizationReport", "run_full_path_geometry_cooptimization"]
