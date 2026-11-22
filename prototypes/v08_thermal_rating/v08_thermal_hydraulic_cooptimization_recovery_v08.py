"""Orchestrate authority audit, dual fouling baseline, required UA, joint search."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from hexagent.properties.base import PropertyProvider
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
    geometry_identity_v2_hash,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    build_candidate_rating_bindings,
)
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import (
    resolve_recovered_shell_052_bundle,
)
from prototypes.v08_thermal_rating.shell_052_thermal_authority_and_margin_v08 import (
    run_shell_052_thermal_authority_and_margin,
)
from prototypes.v08_thermal_rating.thermal_hydraulic_joint_cooptimization_v08 import (
    ThermalHydraulicJointCooptimizationReport,
    run_thermal_hydraulic_joint_cooptimization,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import (
    ThermalPrescreenResult,
    _cp_kg_s,
    run_thermal_prescreen,
)
from prototypes.v08_thermal_rating.v08_epsilon_ntu_required_ua_v08 import required_ua_w_k_for_duty
from prototypes.v08_thermal_rating.v08_shell_052_task037_authority_v08 import (
    evaluate_shell_052_task037,
)
from prototypes.v08_thermal_rating.v08_task037_experimental_authority_v08 import (
    Task037AuthorityProvenanceAudit,
    audit_task037_authority_provenance,
)


@dataclass(frozen=True)
class FoulingScenarioSnapshot:
    fouling_scenario: str
    ua_w_k: str | None
    epsilon_ntu_q_w: str | None
    duty_gap_w: str | None
    tube_outlet_k: str | None
    shell_outlet_k: str | None
    wall_conductivity_w_m_k: str | None
    wall_resistance_outer_m2_k_w: str | None
    task037_result_hash: str | None


@dataclass(frozen=True)
class ThermalHydraulicCooptimizationRecoveryReport:
    provenance: Task037AuthorityProvenanceAudit
    clean: FoulingScenarioSnapshot
    fouled: FoulingScenarioSnapshot
    required_ua_w_k: str | None
    baseline_ua_gap_w_k: str | None
    ua_required_increase_fraction: str | None
    high_tube_excess_pa: str | None
    high_shell_excess_pa: str | None
    joint: ThermalHydraulicJointCooptimizationReport


def _snapshot(
    *,
    label: str,
    prescreen: ThermalPrescreenResult,
    conductivity: str | None,
    wall_r: str | None,
    result_hash: str | None,
) -> FoulingScenarioSnapshot:
    return FoulingScenarioSnapshot(
        fouling_scenario=label,
        ua_w_k=prescreen.ua_w_per_k,
        epsilon_ntu_q_w=prescreen.epsilon_ntu_q_w,
        duty_gap_w=prescreen.target_duty_gap_w,
        tube_outlet_k=prescreen.predicted_tube_outlet_k,
        shell_outlet_k=prescreen.predicted_shell_outlet_k,
        wall_conductivity_w_m_k=conductivity,
        wall_resistance_outer_m2_k_w=wall_r,
        task037_result_hash=result_hash,
    )


def run_thermal_hydraulic_cooptimization_recovery(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: PropertyProvider,
    max_valid: int = 36,
) -> ThermalHydraulicCooptimizationRecoveryReport:
    provenance = audit_task037_authority_provenance()
    recovered = resolve_recovered_shell_052_bundle(normalized, handoff)
    clean_ev = fouled_ev = None
    clean_ps = fouled_ps = ThermalPrescreenResult(
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
    )
    if recovered is not None:
        bundle = recovered.structural_bundle
        v2 = geometry_identity_v2_hash(bundle)
        bindings = build_candidate_rating_bindings(
            bundle,
            space_hash=recovered.candidate_space_hash,
            t168_digest=bundle.task168_request_hash_digest,
            normalized=normalized,
            handoff=handoff,
            provider=provider,
            geometry_projection_hash=v2,
        )
        clean_ev = evaluate_shell_052_task037(recovered, fouling_scenario="CLEAN")
        fouled_ev = evaluate_shell_052_task037(recovered, fouling_scenario="T039_DEMO_FOULING")
        if bindings is not None and clean_ev.raw is not None and fouled_ev.raw is not None:
            clean_ps = run_thermal_prescreen(
                bindings, normalized, provider=provider, task037_override=clean_ev.raw
            )
            fouled_ps = run_thermal_prescreen(
                bindings, normalized, provider=provider, task037_override=fouled_ev.raw
            )

    t_ti = Decimal(str(normalized.tube_side.inlet_temperature_k))
    t_si = Decimal(str(normalized.shell_side.inlet_temperature_k))
    p_t = Decimal(str(normalized.tube_side.inlet_pressure_pa))
    p_s = Decimal(str(normalized.shell_side.inlet_pressure_pa))
    c_t = _cp_kg_s(provider, _fluid="", t_k=t_ti, p_pa=p_t) * normalized.tube_side.mass_flow_kg_s
    c_s = _cp_kg_s(provider, _fluid="", t_k=t_si, p_pa=p_s) * normalized.shell_side.mass_flow_kg_s
    req_ua = required_ua_w_k_for_duty(
        target_q_w=normalized.target_duty_w,
        c_hot=c_t,
        c_cold=c_s,
        t_hot_in=t_ti,
        t_cold_in=t_si,
    )
    baseline_ua = Decimal(fouled_ps.ua_w_per_k or "0") if fouled_ps.ua_w_per_k else None
    gap: str | None = None
    inc: str | None = None
    if req_ua is not None and baseline_ua and baseline_ua > 0:
        gap = str((req_ua - baseline_ua).quantize(Decimal("0.01")))
        inc = str(((req_ua / baseline_ua) - Decimal("1")).quantize(Decimal("0.0001")))

    tube_lim = normalized.max_tube_side_pressure_drop_pa
    shell_lim = normalized.max_shell_side_pressure_drop_pa
    margin = run_shell_052_thermal_authority_and_margin(normalized, handoff, provider=provider)
    high_tube_excess = None
    high_shell_excess = None
    if margin.high_tube_dp_pa:
        high_tube_excess = str(Decimal(margin.high_tube_dp_pa) - tube_lim)
    if margin.high_shell_dp_pa:
        high_shell_excess = str(Decimal(margin.high_shell_dp_pa) - shell_lim)

    joint = run_thermal_hydraulic_joint_cooptimization(
        normalized, handoff, provider=provider, max_valid=max_valid
    )
    return ThermalHydraulicCooptimizationRecoveryReport(
        provenance=provenance,
        clean=_snapshot(
            label="CLEAN",
            prescreen=clean_ps,
            conductivity=clean_ev.wall_conductivity_w_m_k if clean_ev else None,
            wall_r=clean_ev.wall_resistance_outer_m2_k_w if clean_ev else None,
            result_hash=clean_ev.result_hash if clean_ev else None,
        ),
        fouled=_snapshot(
            label="T039_DEMO_FOULING",
            prescreen=fouled_ps,
            conductivity=fouled_ev.wall_conductivity_w_m_k if fouled_ev else None,
            wall_r=fouled_ev.wall_resistance_outer_m2_k_w if fouled_ev else None,
            result_hash=fouled_ev.result_hash if fouled_ev else None,
        ),
        required_ua_w_k=str(req_ua.quantize(Decimal("0.01"))) if req_ua else None,
        baseline_ua_gap_w_k=gap,
        ua_required_increase_fraction=inc,
        high_tube_excess_pa=high_tube_excess,
        high_shell_excess_pa=high_shell_excess,
        joint=joint,
    )


__all__ = [
    "FoulingScenarioSnapshot",
    "ThermalHydraulicCooptimizationRecoveryReport",
    "run_thermal_hydraulic_cooptimization_recovery",
]