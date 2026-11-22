"""0.52 m recovered structure + six combo local search + Pareto joint prescreen."""

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
from prototypes.v08_geometry_candidate_generation.structural_bundles import (
    V08StructuralGeometryBundle,
)
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    AutonomousNozzleFullPathReport,
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import build_candidate_rating_bindings
from prototypes.v08_thermal_rating.experimental_geometry_discrete_space_v08 import (
    EXPERIMENTAL_V08_DISCRETE_SPACE_PATH,
)
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import (
    RecoveredShell052Bundle,
    enumerate_shell_052_bounded_local_combos,
    resolve_recovered_shell_052_bundle,
)
from prototypes.v08_thermal_rating.recovered_shell_052_full_chain_v08 import (
    FROZEN_SHELL_052_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import (
    ThermalPrescreenResult,
    _cp_kg_s,
    run_thermal_prescreen,
)
from prototypes.v08_thermal_rating.v08_epsilon_ntu_required_ua_v08 import required_ua_w_k_for_duty
from prototypes.v08_thermal_rating.v08_geometry_enumeration_bridge import (
    enumerate_structural_bundles_for_space,
)
from prototypes.v08_thermal_rating.v08_task037_evaluate_binding_v08 import (
    evaluate_binding_task037,
)
from prototypes.v08_thermal_rating.v08_thermal_hydraulic_cooptimization_recovery_v08 import (
    REGRESSION_CLEAN_Q_W,
    REGRESSION_CLEAN_UA_GAP_W_K,
    REGRESSION_CLEAN_UA_W_K,
    REGRESSION_REQUIRED_UA_W_K,
)

TARGET_Q_W = Decimal("330000")
TUBE_DP_LIMIT_PA = Decimal("1150")
SHELL_DP_LIMIT_PA = Decimal("1180")

ParetoTier = Literal[
    "MID_JOINT_PRESCREEN_PASS",
    "ALL_SCENARIO_JOINT_PRESCREEN_PASS",
    "MID_HYDRAULIC_PASS_CLEAN_THERMAL_FAIL",
    "CLEAN_THERMAL_PASS_MID_HYDRAULIC_FAIL",
    "MID_PASS_HIGH_K_FAIL",
    "BLOCKED",
]

DesignDecision = Literal["JOINT_PRESCREEN_PASS", "BOUNDED_SEARCH_NOT_FEASIBLE"]

CandidateOrigin = Literal[
    "EXPERIMENTAL_DISCRETE",
    "RECOVERED_SHELL_052",
    "SHELL_052_LOCAL_COMBO",
]


@dataclass(frozen=True)
class ParetoJointRow:
    candidate_id: str
    geometry_v2: str
    origin: CandidateOrigin
    tube_length_m: str
    shell_diameter_m: str
    envelope_scale: str | None
    physical_tube_count: int
    clean_thermal: ThermalPrescreenResult
    fouled_thermal: ThermalPrescreenResult
    hydraulic: AutonomousNozzleFullPathReport | None
    q_deficit_w: str
    tube_dp_excess_pa: str
    shell_dp_excess_pa: str
    pareto_tier: ParetoTier
    mid_joint_pass: bool
    all_scenario_pass: bool
    mid_tube_dp_pa: str | None
    mid_shell_dp_pa: str | None
    tube_margin_pa: str | None
    shell_margin_pa: str | None
    high_tube_dp_pa: str | None
    high_shell_dp_pa: str | None
    task168_blocker: str | None
    clean_fouling_dependent: bool


@dataclass(frozen=True)
class Shell052ParetoJointReport:
    previous_experimental_count: int
    recovered_shell_052_included: bool
    newly_generated_count: int
    distinct_v2_geometries: int
    task168_valid_count: int
    mid_joint_prescreen_pass_count: int
    all_scenario_prescreen_pass_count: int
    clean_baseline_q_w: str
    clean_baseline_ua_w_k: str
    required_ua_w_k: str
    clean_ua_deficit_w_k: str
    recovered_clean_ua_gap_w_k: str
    rows: tuple[ParetoJointRow, ...]
    pareto_front: tuple[ParetoJointRow, ...]
    best: ParetoJointRow | None
    local_combo_blockers: tuple[str, ...]
    design_decision: DesignDecision
    next_required_engineering_change: str


def _excess_metrics(
    clean: ThermalPrescreenResult,
    hydraulic: AutonomousNozzleFullPathReport | None,
) -> tuple[str, str, str]:
    q = Decimal(clean.epsilon_ntu_q_w or "0")
    q_def = max(Decimal("0"), TARGET_Q_W - q)
    tube_ex = shell_ex = Decimal("0")
    if hydraulic is not None:
        mid = next(s for s in hydraulic.scenarios if s.scenario_key == "mid_band")
        if mid.tube_full_path_dp_pa:
            tube_ex = max(Decimal("0"), Decimal(mid.tube_full_path_dp_pa) - TUBE_DP_LIMIT_PA)
        if mid.shell_full_path_dp_pa:
            shell_ex = max(Decimal("0"), Decimal(mid.shell_full_path_dp_pa) - SHELL_DP_LIMIT_PA)
    return str(q_def.quantize(Decimal("0.1"))), str(tube_ex), str(shell_ex)


def _tier(
    *,
    clean: ThermalPrescreenResult,
    hydraulic: AutonomousNozzleFullPathReport | None,
    mid_joint: bool,
    all_pass: bool,
) -> ParetoTier:
    if not hydraulic:
        return "BLOCKED"
    if all_pass and clean.status == "INDICATIVE_PASS":
        return "ALL_SCENARIO_JOINT_PRESCREEN_PASS"
    if mid_joint:
        return "MID_JOINT_PRESCREEN_PASS"
    mid = next(s for s in hydraulic.scenarios if s.scenario_key == "mid_band")
    mid_hyd = mid.hydraulic_check == "PASS"
    thermal_ok = clean.status == "INDICATIVE_PASS"
    high = next(s for s in hydraulic.scenarios if s.scenario_key == "high_loss_sensitivity")
    if mid_hyd and thermal_ok and high.hydraulic_check != "PASS":
        return "MID_PASS_HIGH_K_FAIL"
    if thermal_ok and not mid_hyd:
        return "CLEAN_THERMAL_PASS_MID_HYDRAULIC_FAIL"
    if mid_hyd and not thermal_ok:
        return "MID_HYDRAULIC_PASS_CLEAN_THERMAL_FAIL"
    return "BLOCKED"


def _evaluate_bundle(
    bundle: V08StructuralGeometryBundle | RecoveredShell052Bundle,
    *,
    origin: CandidateOrigin,
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    provider: CoolPropProvider,
    space_hash: str,
    t168_digest: str,
    geometry_projection_hash: str,
    envelope_scale: str | None,
) -> ParetoJointRow | None:
    struct = bundle if isinstance(bundle, V08StructuralGeometryBundle) else bundle.structural_bundle
    space_h = (
        space_hash
        if isinstance(bundle, V08StructuralGeometryBundle)
        else bundle.candidate_space_hash
    )
    bindings = build_candidate_rating_bindings(
        struct,
        space_hash=space_h,
        t168_digest=struct.task168_request_hash_digest if t168_digest == "" else t168_digest,
        normalized=normalized,
        handoff=handoff,
        provider=provider,
        geometry_projection_hash=geometry_projection_hash or geometry_projection_hash_v1(struct),
    )
    if bindings is None:
        return None
    v2 = geometry_identity_v2_hash(struct)
    t037_c = evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
    t037_f = evaluate_binding_task037(bindings, fouling_scenario="T039_DEMO_FOULING")
    if t037_c.status != "SUCCESS" or t037_f.status != "SUCCESS":
        return ParetoJointRow(
            candidate_id=bindings.rating_request.candidate_id,
            geometry_v2=v2,
            origin=origin,
            tube_length_m=str(struct.candidate.tube_length_m),
            shell_diameter_m=str(struct.shell_record.shell_inside_diameter_m),
            envelope_scale=envelope_scale,
            physical_tube_count=int(struct.bundle.task021_layout.physical_tube_count),
            clean_thermal=ThermalPrescreenResult(
                status="NOT_EVALUATED",
                ua_w_per_k=None,
                epsilon_ntu_q_w=None,
                target_duty_gap_w=None,
                predicted_tube_outlet_k=None,
                predicted_shell_outlet_k=None,
                task166_applicability="NOT_EVALUATED",
                shell_htc_w_m2_k=None,
                tube_htc_w_m2_k=None,
                property_basis="",
                wall_resistance_source=None,
                area_basis_m2=None,
                notes=(),
            ),
            fouled_thermal=ThermalPrescreenResult(
                status="NOT_EVALUATED",
                ua_w_per_k=None,
                epsilon_ntu_q_w=None,
                target_duty_gap_w=None,
                predicted_tube_outlet_k=None,
                predicted_shell_outlet_k=None,
                task166_applicability="NOT_EVALUATED",
                shell_htc_w_m2_k=None,
                tube_htc_w_m2_k=None,
                property_basis="",
                wall_resistance_source=None,
                area_basis_m2=None,
                notes=(),
            ),
            hydraulic=None,
            q_deficit_w=str(TARGET_Q_W),
            tube_dp_excess_pa="0",
            shell_dp_excess_pa="0",
            pareto_tier="BLOCKED",
            mid_joint_pass=False,
            all_scenario_pass=False,
            mid_tube_dp_pa=None,
            mid_shell_dp_pa=None,
            tube_margin_pa=None,
            shell_margin_pa=None,
            high_tube_dp_pa=None,
            high_shell_dp_pa=None,
            task168_blocker="task037_blocked",
            clean_fouling_dependent=False,
        )
    clean = run_thermal_prescreen(
        bindings, normalized, provider=provider, task037_override=t037_c.raw
    )
    foul = run_thermal_prescreen(
        bindings, normalized, provider=provider, task037_override=t037_f.raw
    )
    try:
        hydraulic = run_autonomous_nozzle_full_path(
            bindings, tube_nozzle_objective="MAX_MARGIN_WITHIN_VELOCITY_BAND"
        )
    except Exception:
        hydraulic = None
    q_def, t_ex, s_ex = _excess_metrics(clean, hydraulic)
    mid_joint = (
        clean.status == "INDICATIVE_PASS"
        and hydraulic is not None
        and next(s for s in hydraulic.scenarios if s.scenario_key == "mid_band").hydraulic_check
        == "PASS"
    )
    all_pass = bool(mid_joint and hydraulic is not None and hydraulic.scenario_robustness == "PASS")
    tier = _tier(clean=clean, hydraulic=hydraulic, mid_joint=mid_joint, all_pass=all_pass)
    dep = clean.status == "INDICATIVE_PASS" and foul.status != "INDICATIVE_PASS"
    mid = (
        next(s for s in hydraulic.scenarios if s.scenario_key == "mid_band") if hydraulic else None
    )
    high = (
        next(s for s in hydraulic.scenarios if s.scenario_key == "high_loss_sensitivity")
        if hydraulic
        else None
    )
    return ParetoJointRow(
        candidate_id=bindings.rating_request.candidate_id,
        geometry_v2=v2,
        origin=origin,
        tube_length_m=str(struct.candidate.tube_length_m),
        shell_diameter_m=str(struct.shell_record.shell_inside_diameter_m),
        envelope_scale=envelope_scale,
        physical_tube_count=int(struct.bundle.task021_layout.physical_tube_count),
        clean_thermal=clean,
        fouled_thermal=foul,
        hydraulic=hydraulic,
        q_deficit_w=q_def,
        tube_dp_excess_pa=t_ex,
        shell_dp_excess_pa=s_ex,
        pareto_tier=tier,
        mid_joint_pass=mid_joint,
        all_scenario_pass=all_pass,
        mid_tube_dp_pa=mid.tube_full_path_dp_pa if mid else None,
        mid_shell_dp_pa=mid.shell_full_path_dp_pa if mid else None,
        tube_margin_pa=mid.tube_margin_pa if mid else None,
        shell_margin_pa=mid.shell_margin_pa if mid else None,
        high_tube_dp_pa=high.tube_full_path_dp_pa if high else None,
        high_shell_dp_pa=high.shell_full_path_dp_pa if high else None,
        task168_blocker=None,
        clean_fouling_dependent=dep,
    )


def _pareto_nondominated(rows: list[ParetoJointRow]) -> list[ParetoJointRow]:
    front: list[ParetoJointRow] = []
    for a in rows:
        dominated = False
        va = (Decimal(a.q_deficit_w), Decimal(a.tube_dp_excess_pa), Decimal(a.shell_dp_excess_pa))
        for b in rows:
            if a.candidate_id == b.candidate_id:
                continue
            vb = (
                Decimal(b.q_deficit_w),
                Decimal(b.tube_dp_excess_pa),
                Decimal(b.shell_dp_excess_pa),
            )
            if all(x <= y for x, y in zip(vb, va, strict=True)) and any(
                x < y for x, y in zip(vb, va, strict=True)
            ):
                dominated = True
                break
        if not dominated:
            front.append(a)
    return front


def run_recovered_shell_052_pareto_joint_optimization(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
) -> Shell052ParetoJointReport:
    active = provider or CoolPropProvider()
    exp_hash, exp_t168, exp_bundles, exp_geom = enumerate_structural_bundles_for_space(
        normalized,
        handoff,
        discrete_space_path=EXPERIMENTAL_V08_DISCRETE_SPACE_PATH,
        max_valid=64,
    )
    previous_experimental = len(exp_bundles)
    recovered = resolve_recovered_shell_052_bundle(normalized, handoff)
    local_bundles, local_blockers = enumerate_shell_052_bounded_local_combos(normalized, handoff)

    pool: list[
        tuple[
            V08StructuralGeometryBundle | RecoveredShell052Bundle,
            CandidateOrigin,
            str | None,
            str,
            str,
        ]
    ] = []
    for b in exp_bundles:
        pool.append(
            (b, "EXPERIMENTAL_DISCRETE", None, exp_hash, exp_geom.get(b.candidate.candidate_id, ""))
        )
    if recovered is not None:
        pool.append(
            (
                recovered,
                "RECOVERED_SHELL_052",
                recovered.envelope_scale,
                recovered.candidate_space_hash,
                geometry_projection_hash_v1(recovered.structural_bundle),
            )
        )
    for lb in local_bundles:
        pool.append(
            (
                lb,
                "SHELL_052_LOCAL_COMBO",
                lb.envelope_scale,
                lb.candidate_space_hash,
                geometry_projection_hash_v1(lb.structural_bundle),
            )
        )

    by_v2: dict[str, ParetoJointRow] = {}
    newly_generated = 0
    for item, origin, scale, space_h, proj in pool:
        row = _evaluate_bundle(
            item,
            origin=origin,
            normalized=normalized,
            handoff=handoff,
            provider=active,
            space_hash=space_h,
            t168_digest="",
            geometry_projection_hash=proj,
            envelope_scale=scale,
        )
        if row is None:
            continue
        if row.origin == "SHELL_052_LOCAL_COMBO":
            newly_generated += 1
        existing = by_v2.get(row.geometry_v2)
        if (
            existing is None
            or (row.mid_joint_pass and existing and not existing.mid_joint_pass)
            or row.origin == "RECOVERED_SHELL_052"
        ):
            by_v2[row.geometry_v2] = row

    rows = list(by_v2.values())
    front = _pareto_nondominated(rows)
    mid_count = sum(1 for r in rows if r.mid_joint_pass)
    all_count = sum(1 for r in rows if r.all_scenario_pass)

    def rank_key(r: ParetoJointRow) -> tuple:
        return (
            0 if r.mid_joint_pass else 1,
            Decimal(r.q_deficit_w),
            Decimal(r.tube_dp_excess_pa) + Decimal(r.shell_dp_excess_pa),
        )

    ranked = sorted(rows, key=rank_key)
    best = ranked[0] if ranked else None

    t_ti = Decimal(str(normalized.tube_side.inlet_temperature_k))
    t_si = Decimal(str(normalized.shell_side.inlet_temperature_k))
    c_t = (
        _cp_kg_s(
            active, _fluid="", t_k=t_ti, p_pa=Decimal(str(normalized.tube_side.inlet_pressure_pa))
        )
        * normalized.tube_side.mass_flow_kg_s
    )
    c_s = (
        _cp_kg_s(
            active, _fluid="", t_k=t_si, p_pa=Decimal(str(normalized.shell_side.inlet_pressure_pa))
        )
        * normalized.shell_side.mass_flow_kg_s
    )
    req_ua = required_ua_w_k_for_duty(
        target_q_w=normalized.target_duty_w,
        c_hot=c_t,
        c_cold=c_s,
        t_hot_in=t_ti,
        t_cold_in=t_si,
    )
    ua_def = None
    if req_ua and recovered:
        rec_row = by_v2.get(FROZEN_SHELL_052_GEOMETRY_V2)
        if rec_row and rec_row.clean_thermal.ua_w_per_k:
            ua_def = str(
                (req_ua - Decimal(rec_row.clean_thermal.ua_w_per_k)).quantize(Decimal("0.01"))
            )

    decision: DesignDecision = (
        "JOINT_PRESCREEN_PASS" if mid_count > 0 else "BOUNDED_SEARCH_NOT_FEASIBLE"
    )
    next_act = (
        "At least one mid joint prescreen candidate found in bounded search."
        if decision == "JOINT_PRESCREEN_PASS"
        else (
            "Six 0.52 m local combos + recovered baseline: no mid thermal-hydraulic joint pass. "
            "Pareto front shows Q vs Δp tradeoff; stop bounded search per V08-03 scope."
        )
    )

    return Shell052ParetoJointReport(
        previous_experimental_count=previous_experimental,
        recovered_shell_052_included=recovered is not None,
        newly_generated_count=newly_generated,
        distinct_v2_geometries=len(by_v2),
        task168_valid_count=len(rows),
        mid_joint_prescreen_pass_count=mid_count,
        all_scenario_prescreen_pass_count=all_count,
        clean_baseline_q_w=str(REGRESSION_CLEAN_Q_W),
        clean_baseline_ua_w_k=str(REGRESSION_CLEAN_UA_W_K),
        required_ua_w_k=str(req_ua.quantize(Decimal("0.01")))
        if req_ua
        else str(REGRESSION_REQUIRED_UA_W_K),
        clean_ua_deficit_w_k=ua_def or str(REGRESSION_CLEAN_UA_GAP_W_K),
        recovered_clean_ua_gap_w_k=str(REGRESSION_CLEAN_UA_GAP_W_K),
        rows=tuple(rows),
        pareto_front=tuple(front),
        best=best,
        local_combo_blockers=tuple(local_blockers),
        design_decision=decision,
        next_required_engineering_change=next_act,
    )


__all__ = [
    "ParetoJointRow",
    "Shell052ParetoJointReport",
    "run_recovered_shell_052_pareto_joint_optimization",
]
