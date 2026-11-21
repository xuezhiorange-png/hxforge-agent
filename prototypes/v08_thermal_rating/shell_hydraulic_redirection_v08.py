"""Shell hydraulic redirection: lower bounds, proven infeasibility, targeted geometry scan."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_physical_consistency import (
    assess_upstream_hydraulic_postpass_for_full_path,
)
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
)
from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
    resolve_baffle_authority,
)
from prototypes.v08_thermal_rating.shell_hydraulic_lower_bound_v08 import (
    ShellHydraulicLowerBoundReport,
    analyze_shell_hydraulic_lower_bound,
)
from prototypes.v08_thermal_rating.v08_geometry_enumeration_bridge import (
    enumerate_structural_bundles_for_space,
)
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import (
    task174_hydraulic_postpass_from_bindings,
)

ThermalDutyStatus = Literal["THERMAL_DUTY=NOT_EVALUATED"]


@dataclass(frozen=True)
class ShellRedirectionCandidateRow:
    candidate_id: str
    geometry_projection_hash: str
    geometry_space: Literal["R1_APPROVED", "EXPERIMENTAL_COOPT"]
    shell_inside_diameter_m: str
    tube_length_m: str
    baffle_spacing_m: str
    baffle_count: int
    manufacturing_geometry_authority: str
    task174_partial_pass: bool
    thermal_duty_status: ThermalDutyStatus
    lower_bound: ShellHydraulicLowerBoundReport
    first_hydraulic_blocker: str | None
    hydraulic_report: AutonomousNozzleFullPathReport | None
    mid_shell_full_path_dp_pa: str | None
    mid_tube_full_path_dp_pa: str | None
    mid_shell_excess_pa: str | None


@dataclass(frozen=True)
class ShellHydraulicRedirectionReport:
    baseline_candidate_id: str
    baseline_geometry_hash: str
    baseline_lower_bound: ShellHydraulicLowerBoundReport
    upstream_hydraulic_authority_valid: bool
    duplicate_dp_components: int
    total_search_records: int
    distinct_structural_geometries: int
    new_experimental_distinct_geometries: int
    structural_valid_count: int
    task174_partial_feasible_count: int
    full_path_mid_feasible_count: int
    full_path_all_scenario_feasible_count: int
    best_new: ShellRedirectionCandidateRow | None
    rows: tuple[ShellRedirectionCandidateRow, ...]
    design_gap_notes: tuple[str, ...]


def _upstream_authority_ok(bindings: Any) -> tuple[bool, int]:
    postpass = task174_hydraulic_postpass_from_bindings(bindings)
    upstream = assess_upstream_hydraulic_postpass_for_full_path(postpass)
    dup = len(analyze_shell_hydraulic_lower_bound(bindings).duplicate_dp_component_errors)
    usable = bool(
        upstream.get("tube_side_numeric_usable") and upstream.get("shell_side_numeric_usable")
    )
    return usable, dup


def _row_from_binding(
    bindings: Any,
    *,
    geometry_space: Literal["R1_APPROVED", "EXPERIMENTAL_COOPT"],
) -> ShellRedirectionCandidateRow:
    cand = bindings.bundle.candidate
    shell = bindings.bundle.shell_record.shell_inside_diameter_m
    t174 = bindings.rating_request.task174_result
    tube_lim = bindings.normalized.max_tube_side_pressure_drop_pa
    shell_lim = bindings.normalized.max_shell_side_pressure_drop_pa
    t174_ok = (
        t174.modeled_total_tube_side_pressure_drop_pa <= tube_lim
        and t174.bell_total_shell_pressure_drop_pa <= shell_lim
    )
    mfg = (
        "APPROVED_R1_SEARCH_ONLY"
        if geometry_space == "R1_APPROVED"
        else EXPERIMENTAL_GEOMETRY_LABEL
    )
    blocker: str | None = None
    report: AutonomousNozzleFullPathReport | None = None
    mid_shell_fp: str | None = None
    mid_tube_fp: str | None = None
    mid_excess: str | None = None

    lb = analyze_shell_hydraulic_lower_bound(bindings)

    if lb.all_proven_infeasible:
        blocker = "PROVEN_HYDRAULIC_INFEASIBLE_UNDER_ASSUMED_K"
        mid_mid = next(s for s in lb.scenarios if s.scenario_key == "mid_band")
        excess = Decimal(mid_mid.shell_bell_internal_dp_pa) + Decimal(
            mid_mid.shell_external_min_dp_pa
        ) - shell_lim
        mid_excess = str(excess)
    elif not t174_ok:
        blocker = (
            "TASK174_PARTIAL_TUBE_DP_EXCEEDED"
            if t174.modeled_total_tube_side_pressure_drop_pa > tube_lim
            else "TASK174_PARTIAL_SHELL_DP_EXCEEDED"
        )
    else:
        report = run_autonomous_nozzle_full_path(bindings)
        mid = next(s for s in report.scenarios if s.scenario_key == "mid_band")
        mid_shell_fp = mid.shell_full_path_dp_pa
        mid_tube_fp = mid.tube_full_path_dp_pa
        lb = analyze_shell_hydraulic_lower_bound(
            bindings,
            full_path_mid_shell_dp_pa=(
                Decimal(mid.shell_full_path_dp_pa) if mid.shell_full_path_dp_pa else None
            ),
            full_path_mid_margin_pa=(
                Decimal(mid.shell_margin_pa) if mid.shell_margin_pa else None
            ),
        )
        if report.scenario_robustness == "PASS":
            blocker = None
        elif mid.shell_full_path_dp_pa:
            excess = Decimal(mid.shell_full_path_dp_pa) - shell_lim
            mid_excess = str(excess)
            blocker = f"SHELL_FULL_PATH_EXCESS_PA={excess}"
        else:
            blocker = "FULL_PATH_NOT_COMPUTED_OR_SHELL_BLOCKED"

    return ShellRedirectionCandidateRow(
        candidate_id=bindings.rating_request.candidate_id,
        geometry_projection_hash=bindings.geometry_projection_hash,
        geometry_space=geometry_space,
        shell_inside_diameter_m=str(shell),
        tube_length_m=str(cand.tube_length_m),
        baffle_spacing_m=str(cand.baffle_spacing_m),
        baffle_count=resolve_baffle_authority(
            candidate=bindings.bundle.candidate,
            bundle=bindings.bundle.bundle,
        ).baffle_count_authoritative,
        manufacturing_geometry_authority=mfg,
        task174_partial_pass=t174_ok,
        thermal_duty_status="THERMAL_DUTY=NOT_EVALUATED",
        lower_bound=lb,
        first_hydraulic_blocker=blocker,
        hydraulic_report=report,
        mid_shell_full_path_dp_pa=mid_shell_fp,
        mid_tube_full_path_dp_pa=mid_tube_fp,
        mid_shell_excess_pa=mid_excess,
    )


def _scan_bindings(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    provider: CoolPropProvider,
    *,
    discrete_space_path: Any,
    geometry_space: Literal["R1_APPROVED", "EXPERIMENTAL_COOPT"],
    max_valid: int,
) -> list[Any]:
    if discrete_space_path is None:
        sh, dg, bundles, geom = enumerate_structural_bundles(
            normalized, handoff, max_valid=max_valid
        )
    else:
        sh, dg, bundles, geom = enumerate_structural_bundles_for_space(
            normalized,
            handoff,
            discrete_space_path=discrete_space_path,
            max_valid=max_valid,
        )
    out: list[Any] = []
    for bundle in bundles:
        bindings = build_candidate_rating_bindings(
            bundle,
            space_hash=sh,
            t168_digest=dg,
            normalized=normalized,
            handoff=handoff,
            provider=provider,
            geometry_projection_hash=geom.get(bundle.candidate.candidate_id, ""),
        )
        if bindings is not None:
            out.append(bindings)
    return out


def _pick_best(rows: tuple[ShellRedirectionCandidateRow, ...]) -> ShellRedirectionCandidateRow | None:
    feasible = [r for r in rows if r.first_hydraulic_blocker is None and r.hydraulic_report]
    if feasible:
        return feasible[0]

    def bell_pa(r: ShellRedirectionCandidateRow) -> Decimal:
        mid = next(s for s in r.lower_bound.scenarios if s.scenario_key == "mid_band")
        return Decimal(mid.shell_bell_internal_dp_pa)

    ranked = [
        r
        for r in rows
        if r.mid_shell_excess_pa is not None and r.hydraulic_report is not None
    ]
    if ranked:
        return min(ranked, key=lambda r: Decimal(r.mid_shell_excess_pa or "1e12"))
    return min(rows, key=bell_pa) if rows else None


def run_shell_hydraulic_redirection(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
    baseline_candidate_id: str = "9277ebb8-5b05-5130-8b90-92ee4768606b",
    max_valid: int = 64,
) -> ShellHydraulicRedirectionReport:
    active = provider or CoolPropProvider()
    r1_bindings = _scan_bindings(
        normalized,
        handoff,
        active,
        discrete_space_path=None,
        geometry_space="R1_APPROVED",
        max_valid=max_valid,
    )
    exp_bindings = _scan_bindings(
        normalized,
        handoff,
        active,
        discrete_space_path=EXPERIMENTAL_V08_DISCRETE_SPACE_PATH,
        geometry_space="EXPERIMENTAL_COOPT",
        max_valid=max_valid,
    )

    def _rows_from(bindings_list: list[Any], space: Literal["R1_APPROVED", "EXPERIMENTAL_COOPT"]):
        return [_row_from_binding(b, geometry_space=space) for b in bindings_list]

    rows = tuple(_rows_from(r1_bindings, "R1_APPROVED") + _rows_from(exp_bindings, "EXPERIMENTAL_COOPT"))
    geom_hashes = {r.geometry_projection_hash for r in rows}
    r1_hashes = {r.geometry_projection_hash for r in rows if r.geometry_space == "R1_APPROVED"}
    exp_hashes = {r.geometry_projection_hash for r in rows if r.geometry_space == "EXPERIMENTAL_COOPT"}
    new_exp = exp_hashes - r1_hashes

    baseline_row = next((r for r in rows if r.candidate_id == baseline_candidate_id), rows[0] if rows else None)
    assert baseline_row is not None

    ref_binding = next(
        (b for b in r1_bindings + exp_bindings if b.rating_request.candidate_id == baseline_candidate_id),
        r1_bindings[0] if r1_bindings else exp_bindings[0],
    )
    upstream_ok, dup_count = _upstream_authority_ok(ref_binding)

    t174_ok = sum(1 for r in rows if r.task174_partial_pass)
    mid_ok = sum(
        1
        for r in rows
        if r.hydraulic_report
        and next(
            s for s in r.hydraulic_report.scenarios if s.scenario_key == "mid_band"
        ).hydraulic_check
        == "PASS"
    )
    all_ok = sum(
        1
        for r in rows
        if r.hydraulic_report and r.hydraulic_report.scenario_robustness == "PASS"
    )

    gaps: list[str] = []
    gaps.append(
        f"Mid K lower bound: Bell must drop by "
        f"{baseline_row.lower_bound.bell_reduction_required_for_mid_feasibility_pa} Pa "
        f"for feasibility at min 1 m/s nozzles + R27B transitions."
    )
    gaps.append(
        "See V08_03_SHELL_STRUCTURAL_FEASIBILITY_BREAKTHROUGH: per-shell Task168 rejection rows "
        "(BFG hole/cut at 0.52 m, tube-side Re transition at 0.62 m, etc.), not template envelope."
    )
    if mid_ok == 0:
        gaps.append("No mid_band full-path feasible geometry in R1+verified experimental enumeration.")

    return ShellHydraulicRedirectionReport(
        baseline_candidate_id=baseline_row.candidate_id,
        baseline_geometry_hash=baseline_row.geometry_projection_hash,
        baseline_lower_bound=baseline_row.lower_bound,
        upstream_hydraulic_authority_valid=upstream_ok,
        duplicate_dp_components=dup_count,
        total_search_records=len(rows),
        distinct_structural_geometries=len(geom_hashes),
        new_experimental_distinct_geometries=len(new_exp),
        structural_valid_count=len(rows),
        task174_partial_feasible_count=t174_ok,
        full_path_mid_feasible_count=mid_ok,
        full_path_all_scenario_feasible_count=all_ok,
        best_new=_pick_best(rows),
        rows=rows,
        design_gap_notes=tuple(gaps),
    )


__all__ = ["ShellHydraulicRedirectionReport", "run_shell_hydraulic_redirection"]