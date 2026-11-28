"""Joint thermal (ε-NTU) + full-path hydraulic screening in V08-03 experimental space."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
    geometry_identity_v2_hash,
    geometry_projection_hash_v1,
)
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    AutonomousNozzleFullPathReport,
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    build_candidate_rating_bindings,
)
from prototypes.v08_thermal_rating.experimental_geometry_discrete_space_v08 import (
    EXPERIMENTAL_GEOMETRY_LABEL,
    EXPERIMENTAL_V08_DISCRETE_SPACE_PATH,
)
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import (
    resolve_recovered_shell_052_bundle,
)
from prototypes.v08_thermal_rating.recovered_shell_052_full_chain_v08 import (
    FROZEN_SHELL_052_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import (
    ThermalPrescreenResult,
    run_thermal_prescreen,
)
from prototypes.v08_thermal_rating.v08_geometry_enumeration_bridge import (
    enumerate_structural_bundles_for_space,
)
from prototypes.v08_thermal_rating.v08_task037_evaluate_binding_v08 import (
    evaluate_binding_task037,
)

JointClassification = Literal[
    "THERMAL_PASS_HYDRAULIC_FAIL",
    "HYDRAULIC_PASS_THERMAL_FAIL",
    "MID_JOINT_PRESCREEN_PASS",
    "ALL_SCENARIO_JOINT_PRESCREEN_PASS",
    "AUTHORITY_OR_UPSTREAM_BLOCKED",
    "THERMAL_AND_HYDRAULIC_FAIL",
]


@dataclass(frozen=True)
class JointCooptimizationRow:
    candidate_id: str
    geometry_v2: str
    geometry_projection_hash: str
    shell_inside_diameter_m: str
    tube_length_m: str
    baffle_spacing_m: str
    baffle_cut_fraction: str
    physical_tube_count: int | None
    experimental_source: str
    task037_status: str
    clean_thermal: ThermalPrescreenResult
    fouled_thermal: ThermalPrescreenResult
    joint_thermal_basis: Literal["CLEAN_TASK172_STAGE2_EXPERIMENTAL"]
    hydraulic: AutonomousNozzleFullPathReport | None
    classification: JointClassification
    mid_tube_dp_pa: str | None
    mid_shell_dp_pa: str | None
    mid_tube_margin_pa: str | None
    mid_shell_margin_pa: str | None
    high_tube_dp_pa: str | None
    high_shell_dp_pa: str | None
    nozzle_design_hash: str | None


@dataclass(frozen=True)
class ThermalHydraulicJointCooptimizationReport:
    task168_valid_count: int
    distinct_v2_geometries: int
    mid_thermal_hydraulic_prescreen_pass_count: int
    all_scenario_prescreen_pass_count: int
    thermal_pass_hydraulic_fail_count: int
    hydraulic_pass_thermal_fail_count: int
    best: JointCooptimizationRow | None
    rows: tuple[JointCooptimizationRow, ...]
    notes: tuple[str, ...]


def _margins(
    normalized: NormalizedUserDesignCase, hydraulic: AutonomousNozzleFullPathReport
) -> tuple[str | None, str | None, str | None, str | None]:
    mid = next(s for s in hydraulic.scenarios if s.scenario_key == "mid_band")
    tube_lim = normalized.max_tube_side_pressure_drop_pa
    shell_lim = normalized.max_shell_side_pressure_drop_pa
    if mid.tube_full_path_dp_pa is None or mid.shell_full_path_dp_pa is None:
        return mid.tube_full_path_dp_pa, mid.shell_full_path_dp_pa, None, None
    t_dp = Decimal(mid.tube_full_path_dp_pa)
    s_dp = Decimal(mid.shell_full_path_dp_pa)
    return (
        mid.tube_full_path_dp_pa,
        mid.shell_full_path_dp_pa,
        str(tube_lim - t_dp),
        str(shell_lim - s_dp),
    )


def _classify_row(
    *,
    task037_ok: bool,
    clean: ThermalPrescreenResult,
    hydraulic: AutonomousNozzleFullPathReport | None,
    normalized: NormalizedUserDesignCase,
) -> JointClassification:
    if not task037_ok:
        return "AUTHORITY_OR_UPSTREAM_BLOCKED"
    if hydraulic is None:
        return "THERMAL_AND_HYDRAULIC_FAIL"
    mid = next(s for s in hydraulic.scenarios if s.scenario_key == "mid_band")
    thermal_ok = clean.status == "INDICATIVE_PASS"
    mid_hyd = mid.hydraulic_check == "PASS"
    all_hyd = hydraulic.scenario_robustness == "PASS"
    if thermal_ok and all_hyd:
        return "ALL_SCENARIO_JOINT_PRESCREEN_PASS"
    if thermal_ok and mid_hyd:
        return "MID_JOINT_PRESCREEN_PASS"
    if thermal_ok and not mid_hyd:
        return "THERMAL_PASS_HYDRAULIC_FAIL"
    if mid_hyd and not thermal_ok:
        return "HYDRAULIC_PASS_THERMAL_FAIL"
    _ = normalized
    return "THERMAL_AND_HYDRAULIC_FAIL"


def _rank_key(row: JointCooptimizationRow) -> tuple[int, Decimal, Decimal, Decimal]:
    mid_margin = Decimal(row.mid_shell_margin_pa or "-1e9")
    tube_margin = Decimal(row.mid_tube_margin_pa or "-1e9")
    min_margin = min(mid_margin, tube_margin)
    q = Decimal(row.clean_thermal.epsilon_ntu_q_w or "0")
    class_rank = {
        "ALL_SCENARIO_JOINT_PRESCREEN_PASS": 0,
        "MID_JOINT_PRESCREEN_PASS": 1,
        "THERMAL_PASS_HYDRAULIC_FAIL": 2,
        "HYDRAULIC_PASS_THERMAL_FAIL": 3,
        "THERMAL_AND_HYDRAULIC_FAIL": 4,
        "AUTHORITY_OR_UPSTREAM_BLOCKED": 5,
    }[row.classification]
    return (class_rank, -min_margin, -q, Decimal(row.mid_shell_dp_pa or "1e9"))


def run_thermal_hydraulic_joint_cooptimization(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
    max_valid: int = 40,
) -> ThermalHydraulicJointCooptimizationReport:
    active = provider or CoolPropProvider()
    _space_hash, _t168_digest, bundles, geom = enumerate_structural_bundles_for_space(
        normalized,
        handoff,
        discrete_space_path=EXPERIMENTAL_V08_DISCRETE_SPACE_PATH,
        max_valid=max_valid,
    )
    bundle_list = list(bundles)
    recovered = resolve_recovered_shell_052_bundle(normalized, handoff)
    recovered_included = False
    if recovered is not None:
        rb = recovered.structural_bundle
        v2_rec = geometry_identity_v2_hash(rb)
        if v2_rec == FROZEN_SHELL_052_GEOMETRY_V2:
            bundle_list.append(rb)
            geom[rb.candidate.candidate_id] = geometry_projection_hash_v1(rb)
            recovered_included = True
    rows: list[JointCooptimizationRow] = []
    v2_set: set[str] = set()
    for bundle in bundle_list:
        bindings = build_candidate_rating_bindings(
            bundle,
            space_hash=_space_hash,
            t168_digest=_t168_digest,
            normalized=normalized,
            handoff=handoff,
            provider=active,
            geometry_projection_hash=geom.get(bundle.candidate.candidate_id, ""),
        )
        if bindings is None:
            continue
        v2 = geometry_identity_v2_hash(bindings.bundle)
        v2_set.add(v2)
        t037_clean = evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
        t037_foul = evaluate_binding_task037(bindings, fouling_scenario="T039_DEMO_FOULING")
        task037_ok = t037_clean.status == "SUCCESS" and t037_foul.status == "SUCCESS"
        clean_prescreen = run_thermal_prescreen(
            bindings,
            normalized,
            provider=active,
            task037_override=t037_clean.raw if t037_clean.raw else None,
        )
        foul_prescreen = run_thermal_prescreen(
            bindings,
            normalized,
            provider=active,
            task037_override=t037_foul.raw if t037_foul.raw else None,
        )
        hydraulic: AutonomousNozzleFullPathReport | None = None
        try:
            hydraulic = run_autonomous_nozzle_full_path(bindings)
        except Exception:
            hydraulic = None
        classification = _classify_row(
            task037_ok=task037_ok,
            clean=clean_prescreen,
            hydraulic=hydraulic,
            normalized=normalized,
        )
        t_dp, s_dp, t_m, s_m = (
            (None, None, None, None) if hydraulic is None else _margins(normalized, hydraulic)
        )
        high = None
        if hydraulic is not None:
            high = next(s for s in hydraulic.scenarios if s.scenario_key == "high_loss_sensitivity")
        cand = bindings.bundle.candidate
        shell = bindings.bundle.shell_record.shell_inside_diameter_m
        rows.append(
            JointCooptimizationRow(
                candidate_id=bindings.rating_request.candidate_id,
                geometry_v2=v2,
                geometry_projection_hash=bindings.geometry_projection_hash,
                shell_inside_diameter_m=str(shell),
                tube_length_m=str(cand.tube_length_m),
                baffle_spacing_m=str(cand.baffle_spacing_m),
                baffle_cut_fraction=str(cand.baffle_cut_fraction),
                physical_tube_count=int(bindings.bundle.bundle.task021_layout.physical_tube_count),
                experimental_source=(
                    "RECOVERED_SHELL_052"
                    if geometry_identity_v2_hash(bindings.bundle) == FROZEN_SHELL_052_GEOMETRY_V2
                    else EXPERIMENTAL_GEOMETRY_LABEL
                ),
                task037_status=t037_clean.status if task037_ok else "BLOCKED",
                clean_thermal=clean_prescreen,
                fouled_thermal=foul_prescreen,
                joint_thermal_basis="CLEAN_TASK172_STAGE2_EXPERIMENTAL",
                hydraulic=hydraulic,
                classification=classification,
                mid_tube_dp_pa=t_dp,
                mid_shell_dp_pa=s_dp,
                mid_tube_margin_pa=t_m,
                mid_shell_margin_pa=s_m,
                high_tube_dp_pa=high.tube_full_path_dp_pa if high else None,
                high_shell_dp_pa=high.shell_full_path_dp_pa if high else None,
                nozzle_design_hash=hydraulic.nozzle_design_hash if hydraulic else None,
            )
        )

    mid_joint = sum(1 for r in rows if r.classification == "MID_JOINT_PRESCREEN_PASS")
    all_joint = sum(1 for r in rows if r.classification == "ALL_SCENARIO_JOINT_PRESCREEN_PASS")
    t_ph = sum(1 for r in rows if r.classification == "THERMAL_PASS_HYDRAULIC_FAIL")
    h_pt = sum(1 for r in rows if r.classification == "HYDRAULIC_PASS_THERMAL_FAIL")
    ranked = sorted(rows, key=_rank_key)
    best = ranked[0] if ranked else None
    notes = (
        "joint_thermal_uses_clean_task172_stage2_experimental_basis",
        "fouled_scenario_t039_demo_sensitivity_only",
        f"recovered_shell_052_included={recovered_included}",
        "see_recovered_shell_052_pareto_joint_v08_for_bounded_local_search",
    )
    return ThermalHydraulicJointCooptimizationReport(
        task168_valid_count=len(rows),
        distinct_v2_geometries=len(v2_set),
        mid_thermal_hydraulic_prescreen_pass_count=mid_joint + all_joint,
        all_scenario_prescreen_pass_count=all_joint,
        thermal_pass_hydraulic_fail_count=t_ph,
        hydraulic_pass_thermal_fail_count=h_pt,
        best=best,
        rows=tuple(rows),
        notes=notes,
    )


__all__ = [
    "JointCooptimizationRow",
    "ThermalHydraulicJointCooptimizationReport",
    "run_thermal_hydraulic_joint_cooptimization",
]
