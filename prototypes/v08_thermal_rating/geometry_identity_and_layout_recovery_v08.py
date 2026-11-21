"""V08-03 geometry identity V2, layout recovery, thermal prescreen, limited hydraulic joint validation."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Literal

from hexagent.exchangers.shell_tube.bell_delaware.models import ApplicabilityStatus
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
    geometry_identity_v2_hash,
    geometry_projection_hash_v1,
    legacy_geometry_projection_aliases,
    resolve_baffle_authority,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    build_candidate_rating_bindings,
    enumerate_structural_bundles,
)
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import (
    run_larger_shell_layout_recovery,
)
from prototypes.v08_thermal_rating.shell_structural_feasibility_breakthrough_v08 import (
    BREAKTHROUGH_SEARCH_SPACES,
    BreakthroughCandidateRow,
    _row_from_bindings,
)
from prototypes.v08_thermal_rating.task168_rejection_diagnostics_v08 import (
    _enumerate_with_payload,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import (
    ThermalPrescreenResult,
    run_thermal_prescreen,
)

DesignDecision = Literal[
    "MID_FEASIBLE_FOUND", "SINGLE_SEGMENTAL_MODEL_SPACE_EXHAUSTED"
]


@dataclass(frozen=True)
class GeometryRecoveryCandidateRow:
    breakthrough: BreakthroughCandidateRow
    geometry_identity_v2: str
    geometry_projection_hash_v1: str
    baffle_hole_position_count: int
    baffle_count_consistent: bool
    thermal: ThermalPrescreenResult


@dataclass(frozen=True)
class GeometryIdentityLayoutRecoveryReport:
    baffle_count_corrected: bool
    actual_baffle_count: int | None
    baffle_hole_position_count: int | None
    geometry_identity_v2_sample: str | None
    old_and_new_cut_hash_distinct: bool
    legacy_hash_collision_resolved: bool
    new_structurally_valid_count: int
    distinct_v2_geometry_count: int
    larger_shell_layout_recovered: bool
    task168_result: str
    task166_applicability: str
    mid_full_path_feasible_count: int
    high_full_path_feasible_count: int
    best_new: GeometryRecoveryCandidateRow | None
    rows: tuple[GeometryRecoveryCandidateRow, ...]
    design_decision: DesignDecision
    next_required_engineering_change: str


def _collect_rows(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    provider: CoolPropProvider,
) -> tuple[list[GeometryRecoveryCandidateRow], tuple[str, str]]:
    enriched: list[GeometryRecoveryCandidateRow] = []
    cut_pair_sample: tuple[str, str] | None = None

    for discrete_path, cut, label in BREAKTHROUGH_SEARCH_SPACES:
        space_hash, digest, valid, _rej = _enumerate_with_payload(
            normalized, handoff, discrete_path=discrete_path, baffle_cut_override=cut
        )
        for bundle in valid:
            v1 = geometry_projection_hash_v1(bundle)
            v2 = geometry_identity_v2_hash(bundle, baffle_cut_fraction=str(cut))
            if cut_pair_sample is None:
                cut_pair_sample = (
                    geometry_identity_v2_hash(bundle, baffle_cut_fraction="0.25"),
                    geometry_identity_v2_hash(bundle, baffle_cut_fraction="0.49"),
                )
            bindings = build_candidate_rating_bindings(
                bundle,
                space_hash=space_hash,
                t168_digest=digest or bundle.task168_request_hash_digest,
                normalized=normalized,
                handoff=handoff,
                provider=provider,
                geometry_projection_hash=v1,
            )
            if bindings is None:
                continue
            baffle = resolve_baffle_authority(candidate=bundle.candidate, bundle=bundle.bundle)
            br = _row_from_bindings(bindings, baffle_cut=cut, geometry_space=label)
            br = replace(br, geometry_projection_hash=v2, baffle_count=baffle.baffle_count_authoritative)
            thermal = run_thermal_prescreen(bindings, normalized)
            enriched.append(
                GeometryRecoveryCandidateRow(
                    breakthrough=br,
                    geometry_identity_v2=v2,
                    geometry_projection_hash_v1=v1,
                    baffle_hole_position_count=baffle.baffle_hole_position_count,
                    baffle_count_consistent=baffle.cross_check_ok,
                    thermal=thermal,
                )
            )

    sh, dg, r1_bundles, _geom = enumerate_structural_bundles(normalized, handoff, max_valid=8)
    for bundle in r1_bundles:
        v1 = geometry_projection_hash_v1(bundle)
        v2 = geometry_identity_v2_hash(bundle, baffle_cut_fraction="0.25")
        if cut_pair_sample is None:
            cut_pair_sample = (
                geometry_identity_v2_hash(bundle, baffle_cut_fraction="0.25"),
                geometry_identity_v2_hash(bundle, baffle_cut_fraction="0.49"),
            )
        bindings = build_candidate_rating_bindings(
            bundle,
            space_hash=sh,
            t168_digest=dg,
            normalized=normalized,
            handoff=handoff,
            provider=provider,
            geometry_projection_hash=v1,
        )
        if bindings is None:
            continue
        baffle = resolve_baffle_authority(candidate=bundle.candidate, bundle=bundle.bundle)
        br = _row_from_bindings(
            bindings,
            baffle_cut=Decimal("0.25"),
            geometry_space="APPROVED_R1_SEARCH_ONLY",
        )
        br = replace(br, geometry_projection_hash=v2, baffle_count=baffle.baffle_count_authoritative)
        thermal = run_thermal_prescreen(bindings, normalized)
        enriched.append(
            GeometryRecoveryCandidateRow(
                breakthrough=br,
                geometry_identity_v2=v2,
                geometry_projection_hash_v1=v1,
                baffle_hole_position_count=baffle.baffle_hole_position_count,
                baffle_count_consistent=baffle.cross_check_ok,
                thermal=thermal,
            )
        )

    sample = cut_pair_sample or ("", "")
    return enriched, sample


def run_geometry_identity_and_layout_recovery(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
) -> GeometryIdentityLayoutRecoveryReport:
    active = provider or CoolPropProvider()
    layout = run_larger_shell_layout_recovery(normalized, handoff)
    rows, cut_sample = _collect_rows(normalized, handoff, active)

    distinct_v2 = {r.geometry_identity_v2 for r in rows}
    mid_ok = sum(1 for r in rows if r.breakthrough.full_path_status == "MID_PASS")
    high_ok = sum(
        1
        for r in rows
        if r.breakthrough.hydraulic_report
        and r.breakthrough.hydraulic_report.scenario_robustness == "PASS"
    )

    v1_v2 = [(r.geometry_projection_hash_v1, r.geometry_identity_v2) for r in rows]
    legacy_aliases = legacy_geometry_projection_aliases(tuple(v1_v2))
    cut_distinct = (
        cut_sample[0] != cut_sample[1] and cut_sample[0] != "" and cut_sample[1] != ""
    )
    legacy_resolved = bool(legacy_aliases) and cut_distinct

    best_row: GeometryRecoveryCandidateRow | None = None

    def rank(r: GeometryRecoveryCandidateRow) -> tuple[int, Decimal]:
        br = r.breakthrough
        if br.full_path_status == "MID_PASS":
            return (0, Decimal("0"))
        if br.mid_shell_full_path_dp_pa:
            return (1, Decimal(br.mid_shell_full_path_dp_pa))
        if br.shell_minimum_full_path_dp_pa:
            return (2, Decimal(br.shell_minimum_full_path_dp_pa))
        return (3, Decimal("1e12"))

    if rows:
        best_row = min(rows, key=rank)

    decision: DesignDecision = (
        "MID_FEASIBLE_FOUND" if mid_ok > 0 else "SINGLE_SEGMENTAL_MODEL_SPACE_EXHAUSTED"
    )
    if decision == "SINGLE_SEGMENTAL_MODEL_SPACE_EXHAUSTED":
        next_change = (
            "Adopt a shell-side flow organization with validated Bell-Delaware geometry beyond "
            "single-segmental baffle cut/placement (e.g. double-segmental or rod-baffle) with "
            "Task166 correlation scope extension — not further cut-only tuning near 0.50."
        )
    else:
        next_change = "Continue isolated rating evidence; manufacturing approval still blocked."

    task166_app = "NOT_EVALUATED"
    if best_row and best_row.thermal.task166_applicability != "NOT_EVALUATED":
        task166_app = best_row.thermal.task166_applicability
    elif rows:
        for r in rows:
            if r.thermal.task166_applicability == ApplicabilityStatus.APPLICABLE.value:
                task166_app = ApplicabilityStatus.APPLICABLE.value
                break

    baffle_ok = bool(rows) and all(
        r.baffle_count_consistent and r.breakthrough.baffle_count == 4 for r in rows
    )
    hole_pos = best_row.baffle_hole_position_count if best_row else None
    actual_bc = best_row.breakthrough.baffle_count if best_row else None

    return GeometryIdentityLayoutRecoveryReport(
        baffle_count_corrected=baffle_ok,
        actual_baffle_count=actual_bc,
        baffle_hole_position_count=hole_pos,
        geometry_identity_v2_sample=best_row.geometry_identity_v2 if best_row else None,
        old_and_new_cut_hash_distinct=cut_distinct,
        legacy_hash_collision_resolved=legacy_resolved,
        new_structurally_valid_count=len(rows),
        distinct_v2_geometry_count=len(distinct_v2),
        larger_shell_layout_recovered=layout.larger_shell_layout_recovered,
        task168_result=layout.task168_result,
        task166_applicability=task166_app,
        mid_full_path_feasible_count=mid_ok,
        high_full_path_feasible_count=high_ok,
        best_new=best_row,
        rows=tuple(rows),
        design_decision=decision,
        next_required_engineering_change=next_change,
    )


__all__ = [
    "GeometryIdentityLayoutRecoveryReport",
    "GeometryRecoveryCandidateRow",
    "run_geometry_identity_and_layout_recovery",
]