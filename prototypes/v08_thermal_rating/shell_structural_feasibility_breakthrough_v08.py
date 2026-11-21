"""Limited structural feasibility search: Task168 → hydraulics with proven-infeasible skip."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
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
)
from prototypes.v08_thermal_rating.shell_hydraulic_lower_bound_v08 import (
    analyze_shell_hydraulic_lower_bound,
)
from prototypes.v08_thermal_rating.task168_rejection_diagnostics_v08 import (
    BREAKTHROUGH_DISCRETE_SPACE_PATH,
    Task168RejectionRow,
    _enumerate_with_payload,
    collect_larger_shell_task168_rejections,
)
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import (
    task174_hydraulic_postpass_from_bindings,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
BREAKTHROUGH_SEARCH_SPACES: tuple[tuple[Path, Decimal, str], ...] = (
    (BREAKTHROUGH_DISCRETE_SPACE_PATH, Decimal("0.35"), "BREAKTHROUGH_CUT_035"),
    (
        _REPO_ROOT / "docs/tasks/evidence/V08-03-breakthrough-discrete-space-cut049-r1.json",
        Decimal("0.49"),
        "BREAKTHROUGH_CUT_049",
    ),
)


@dataclass(frozen=True)
class BreakthroughCandidateRow:
    candidate_id: str
    geometry_projection_hash: str
    baffle_cut_fraction: str
    shell_inside_diameter_m: str
    tube_length_m: str
    baffle_spacing_m: str
    baffle_count: int
    physical_tube_count: int | None
    manufacturing_geometry_authority: str
    upstream_hydraulic_authority_valid: bool
    bell_dp_pa: str | None
    shell_minimum_full_path_dp_pa: str | None
    mid_tube_full_path_dp_pa: str | None
    mid_shell_full_path_dp_pa: str | None
    high_shell_full_path_dp_pa: str | None
    mid_shell_margin_pa: str | None
    high_shell_margin_pa: str | None
    nozzle_velocity_check: str | None
    full_path_status: Literal[
        "MID_PASS",
        "NOT_RUN_PROVEN_INFEASIBLE_UNDER_ASSUMED_K",
        "COMPUTED_BLOCKED",
        "TASK168_BLOCKED",
    ]
    first_blocker: str | None
    hydraulic_report: AutonomousNozzleFullPathReport | None


@dataclass(frozen=True)
class ShellStructuralFeasibilityBreakthroughReport:
    larger_shell_failures_verified: bool
    task168_binding_defect: bool
    task168_geometry_defect: bool
    larger_shell_rejection_sample: tuple[Task168RejectionRow, ...]
    distinct_candidates_evaluated: int
    structurally_valid_count: int
    mid_full_path_feasible_count: int
    high_full_path_feasible_count: int
    best: BreakthroughCandidateRow | None
    rows: tuple[BreakthroughCandidateRow, ...]
    design_decision: Literal["MID_FEASIBLE_FOUND", "EXISTING_MODEL_SPACE_EXHAUSTED"]
    next_required_structural_change: str
    minimum_shell_full_path_dp_pa: str | None


def _row_from_bindings(
    bindings: Any,
    *,
    baffle_cut: Decimal,
    geometry_space: str,
) -> BreakthroughCandidateRow:
    cand = bindings.bundle.candidate
    shell = bindings.bundle.shell_record.shell_inside_diameter_m
    layout = bindings.bundle.bundle.task021_layout
    t174 = bindings.rating_request.task174_result
    postpass = task174_hydraulic_postpass_from_bindings(bindings)
    upstream = assess_upstream_hydraulic_postpass_for_full_path(postpass)
    upstream_ok = bool(
        upstream.get("tube_side_numeric_usable") and upstream.get("shell_side_numeric_usable")
    )
    lb = analyze_shell_hydraulic_lower_bound(bindings)
    mid_sc = next(s for s in lb.scenarios if s.scenario_key == "mid_band")
    shell_min = str(
        Decimal(mid_sc.shell_bell_internal_dp_pa) + Decimal(mid_sc.shell_external_min_dp_pa)
    )

    if lb.all_proven_infeasible:
        return BreakthroughCandidateRow(
            candidate_id=bindings.rating_request.candidate_id,
            geometry_projection_hash=bindings.geometry_projection_hash,
            baffle_cut_fraction=str(baffle_cut),
            shell_inside_diameter_m=str(shell),
            tube_length_m=str(cand.tube_length_m),
            baffle_spacing_m=str(cand.baffle_spacing_m),
            baffle_count=int(bindings.bundle.bundle.task024_geometry.position_count),
            physical_tube_count=int(layout.physical_tube_count),
            manufacturing_geometry_authority=geometry_space,
            upstream_hydraulic_authority_valid=upstream_ok,
            bell_dp_pa=str(t174.bell_total_shell_pressure_drop_pa),
            shell_minimum_full_path_dp_pa=shell_min,
            mid_tube_full_path_dp_pa=None,
            mid_shell_full_path_dp_pa=None,
            high_shell_full_path_dp_pa=None,
            mid_shell_margin_pa=None,
            high_shell_margin_pa=None,
            nozzle_velocity_check=None,
            full_path_status="NOT_RUN_PROVEN_INFEASIBLE_UNDER_ASSUMED_K",
            first_blocker="PROVEN_HYDRAULIC_INFEASIBLE_UNDER_ASSUMED_K",
            hydraulic_report=None,
        )

    report = run_autonomous_nozzle_full_path(bindings)
    mid = next(s for s in report.scenarios if s.scenario_key == "mid_band")
    high = next(s for s in report.scenarios if s.scenario_key == "high_loss_sensitivity")
    status: Literal["MID_PASS", "COMPUTED_BLOCKED"] = (
        "MID_PASS" if mid.hydraulic_check == "PASS" else "COMPUTED_BLOCKED"
    )
    blocker = None
    if mid.hydraulic_check != "PASS":
        if mid.shell_full_path_dp_pa:
            excess = (
                Decimal(mid.shell_full_path_dp_pa)
                - bindings.normalized.max_shell_side_pressure_drop_pa
            )
            blocker = f"SHELL_FULL_PATH_EXCESS_PA={excess}"
        else:
            blocker = "FULL_PATH_NOT_COMPUTED"

    return BreakthroughCandidateRow(
        candidate_id=bindings.rating_request.candidate_id,
        geometry_projection_hash=bindings.geometry_projection_hash,
        baffle_cut_fraction=str(baffle_cut),
        shell_inside_diameter_m=str(shell),
        tube_length_m=str(cand.tube_length_m),
        baffle_spacing_m=str(cand.baffle_spacing_m),
        baffle_count=int(bindings.bundle.bundle.task024_geometry.position_count),
        physical_tube_count=int(layout.physical_tube_count),
        manufacturing_geometry_authority=geometry_space,
        upstream_hydraulic_authority_valid=upstream_ok,
        bell_dp_pa=str(t174.bell_total_shell_pressure_drop_pa),
        shell_minimum_full_path_dp_pa=shell_min,
        mid_tube_full_path_dp_pa=mid.tube_full_path_dp_pa,
        mid_shell_full_path_dp_pa=mid.shell_full_path_dp_pa,
        high_shell_full_path_dp_pa=high.shell_full_path_dp_pa,
        mid_shell_margin_pa=mid.shell_margin_pa,
        high_shell_margin_pa=high.shell_margin_pa,
        nozzle_velocity_check=str(report.nozzle_velocity_check),
        full_path_status=status,
        first_blocker=blocker,
        hydraulic_report=report,
    )


def _scan_cut(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    provider: CoolPropProvider,
    *,
    discrete_path: Path,
    baffle_cut: Decimal,
    geometry_space: str,
) -> list[BreakthroughCandidateRow]:
    space_hash, t168_digest, valid, _rej = _enumerate_with_payload(
        normalized, handoff, discrete_path=discrete_path, baffle_cut_override=baffle_cut
    )
    if not valid:
        return []
    from prototypes.v08_geometry_candidate_generation.discrete_space import (
        format_engineering_decimal,
    )
    from prototypes.v08_geometry_candidate_generation.generator import _geometry_projection_hash

    rows: list[BreakthroughCandidateRow] = []
    for bundle in valid:
        cand = bundle.candidate
        layout = bundle.bundle.task021_layout
        geom_hash = _geometry_projection_hash(
            shell_inside_diameter_m=str(bundle.shell_record.shell_inside_diameter_m),
            tube_length_m=format_engineering_decimal(cand.tube_length_m),
            baffle_spacing_m=format_engineering_decimal(cand.baffle_spacing_m),
            tube_pass_count=int(cand.tube_pass_count),
            physical_tube_count=int(layout.physical_tube_count),
        )
        bindings = build_candidate_rating_bindings(
            bundle,
            space_hash=space_hash,
            t168_digest=t168_digest or bundle.task168_request_hash_digest,
            normalized=normalized,
            handoff=handoff,
            provider=provider,
            geometry_projection_hash=geom_hash,
        )
        if bindings is None:
            continue
        rows.append(
            _row_from_bindings(bindings, baffle_cut=baffle_cut, geometry_space=geometry_space)
        )
    return rows


def run_shell_structural_feasibility_breakthrough(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
) -> ShellStructuralFeasibilityBreakthroughReport:
    active = provider or CoolPropProvider()
    rej_sample = collect_larger_shell_task168_rejections(normalized, handoff)
    binding_defect = any(
        "TASK021" in (r.field_path or "") and "envelope" in (r.message or "").lower()
        for r in rej_sample
    )
    geometry_defect = any(
        r.failure_stage in ("BAFFLE_GEOMETRY", "TUBE_SIDE", "TUBE_DP") for r in rej_sample
    )
    larger_verified = len(rej_sample) > 0 and all(r.blocker_code for r in rej_sample[:6])

    rows: list[BreakthroughCandidateRow] = []
    for discrete_path, cut, label in BREAKTHROUGH_SEARCH_SPACES:
        rows.extend(
            _scan_cut(
                normalized,
                handoff,
                active,
                discrete_path=discrete_path,
                baffle_cut=cut,
                geometry_space=f"{EXPERIMENTAL_GEOMETRY_LABEL}/{label}",
            )
        )

    sh, dg, r1_bundles, geom = enumerate_structural_bundles(normalized, handoff, max_valid=8)
    for bundle in r1_bundles:
        bindings = build_candidate_rating_bindings(
            bundle,
            space_hash=sh,
            t168_digest=dg,
            normalized=normalized,
            handoff=handoff,
            provider=active,
            geometry_projection_hash=geom.get(bundle.candidate.candidate_id, ""),
        )
        if bindings is None:
            continue
        rows.append(
            _row_from_bindings(
                bindings,
                baffle_cut=Decimal("0.25"),
                geometry_space="APPROVED_R1_SEARCH_ONLY",
            )
        )

    distinct = {r.geometry_projection_hash for r in rows}
    mid_ok = sum(1 for r in rows if r.full_path_status == "MID_PASS")
    high_ok = sum(
        1 for r in rows if r.hydraulic_report and r.hydraulic_report.scenario_robustness == "PASS"
    )
    computed = [r for r in rows if r.mid_shell_full_path_dp_pa is not None]
    min_shell = None
    if computed:
        min_shell = min(computed, key=lambda r: Decimal(r.mid_shell_full_path_dp_pa or "1e12"))

    def rank(r: BreakthroughCandidateRow) -> tuple[int, Decimal]:
        if r.full_path_status == "MID_PASS":
            return (0, Decimal("0"))
        if r.mid_shell_full_path_dp_pa:
            return (1, Decimal(r.mid_shell_full_path_dp_pa))
        if r.shell_minimum_full_path_dp_pa:
            return (2, Decimal(r.shell_minimum_full_path_dp_pa))
        return (3, Decimal("1e12"))

    best = min(rows, key=rank) if rows else None
    decision: Literal["MID_FEASIBLE_FOUND", "EXISTING_MODEL_SPACE_EXHAUSTED"] = (
        "MID_FEASIBLE_FOUND" if mid_ok > 0 else "EXISTING_MODEL_SPACE_EXHAUSTED"
    )
    next_change = (
        "Extend supported shell-side flow geometry (e.g. shell-dependent baffle cut + larger "
        "shell with resolved tube-side Re/HTC bands) or re-prove R27B transition K — "
        f"best computed mid shell full-path ≈ {min_shell.mid_shell_full_path_dp_pa if min_shell else 'unknown'} Pa "
        f"vs 1180 Pa limit under frozen K."
    )

    return ShellStructuralFeasibilityBreakthroughReport(
        larger_shell_failures_verified=larger_verified,
        task168_binding_defect=binding_defect,
        task168_geometry_defect=geometry_defect,
        larger_shell_rejection_sample=rej_sample[:24],
        distinct_candidates_evaluated=len(distinct),
        structurally_valid_count=len(rows),
        mid_full_path_feasible_count=mid_ok,
        high_full_path_feasible_count=high_ok,
        best=best,
        rows=tuple(rows),
        design_decision=decision,
        next_required_structural_change=next_change,
        minimum_shell_full_path_dp_pa=(min_shell.mid_shell_full_path_dp_pa if min_shell else None),
    )


__all__ = [
    "ShellStructuralFeasibilityBreakthroughReport",
    "run_shell_structural_feasibility_breakthrough",
]
