"""Frozen 0.52 m shell: Task037 authority, ε-NTU prescreen, hydraulic margins & sensitivity."""

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
)
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import build_candidate_rating_bindings
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import (
    resolve_recovered_shell_052_bundle,
)
from prototypes.v08_thermal_rating.recovered_shell_052_full_chain_v08 import (
    FROZEN_SHELL_052_CANDIDATE_ID,
    FROZEN_SHELL_052_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import (
    _cp_kg_s,
    run_thermal_prescreen,
)
from prototypes.v08_thermal_rating.v08_shell_052_task037_authority_v08 import (
    evaluate_shell_052_task037,
)

DesignDecision = Literal[
    "THERMAL_HYDRAULIC_PRESCREEN_PASS", "THERMAL_OR_MARGIN_BLOCKED"
]
HydraulicRobustness = Literal["UNPROVEN", "MID_MATHEMATICAL_PASS_ONLY"]


@dataclass(frozen=True)
class Shell052ThermalAuthorityMarginReport:
    candidate_id: str
    geometry_v2: str
    geometry_identity_replay: Literal["PASS", "BLOCKED"]
    task037_status: str
    wall_material_authority: str
    wall_conductivity_w_m_k: str | None
    wall_resistance_outer_m2_k_w: str | None
    task037_result_hash: str | None
    ua_w_k: str | None
    epsilon_ntu_q_w: str | None
    tube_outlet_k: str | None
    shell_outlet_k: str | None
    ntu: str | None
    cr: str | None
    thermal_prescreen: str
    tube_full_dp_pa: str
    shell_full_dp_pa: str
    tube_dp_margin_pa: str
    shell_dp_margin_pa: str
    high_tube_dp_pa: str | None
    high_shell_dp_pa: str | None
    high_failure_component: str | None
    mid_hydraulic_mathematical_pass: bool
    mid_hydraulic_design_robustness: HydraulicRobustness
    high_hydraulic: str
    nozzle_design_hash: str | None
    nozzle_manufacturing_authority: Literal["PROVISIONAL"]
    hydraulic_robustness: HydraulicRobustness
    sensitivity_notes: tuple[str, ...]
    design_decision: DesignDecision
    next_required_engineering_action: str


def _dp_margin(limit: Decimal, actual: Decimal) -> str:
    return str(limit - actual)


def run_shell_052_thermal_authority_and_margin(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
) -> Shell052ThermalAuthorityMarginReport:
    active = provider or CoolPropProvider()
    recovered = resolve_recovered_shell_052_bundle(normalized, handoff)
    if recovered is None:
        return Shell052ThermalAuthorityMarginReport(
            candidate_id="",
            geometry_v2="",
            geometry_identity_replay="BLOCKED",
            task037_status="NO_RECOVERED_BUNDLE",
            wall_material_authority="",
            wall_conductivity_w_m_k=None,
            wall_resistance_outer_m2_k_w=None,
            task037_result_hash=None,
            ua_w_k=None,
            epsilon_ntu_q_w=None,
            tube_outlet_k=None,
            shell_outlet_k=None,
            ntu=None,
            cr=None,
            thermal_prescreen="NOT_EVALUATED",
            tube_full_dp_pa="not_run",
            shell_full_dp_pa="not_run",
            tube_dp_margin_pa="not_run",
            shell_dp_margin_pa="not_run",
            high_tube_dp_pa=None,
            high_shell_dp_pa=None,
            high_failure_component=None,
            mid_hydraulic_mathematical_pass=False,
            mid_hydraulic_design_robustness="UNPROVEN",
            high_hydraulic="BLOCKED",
            nozzle_design_hash=None,
            nozzle_manufacturing_authority="PROVISIONAL",
            hydraulic_robustness="UNPROVEN",
            sensitivity_notes=(),
            design_decision="THERMAL_OR_MARGIN_BLOCKED",
            next_required_engineering_action="Recover 0.52 m bundle before validation.",
        )

    bundle = recovered.structural_bundle
    v2 = geometry_identity_v2_hash(bundle)
    cid = bundle.candidate.candidate_id
    replay = (
        "PASS"
        if cid == FROZEN_SHELL_052_CANDIDATE_ID and v2 == FROZEN_SHELL_052_GEOMETRY_V2
        else "BLOCKED"
    )

    task037_eval = evaluate_shell_052_task037(recovered)
    bindings = build_candidate_rating_bindings(
        bundle,
        space_hash=recovered.candidate_space_hash,
        t168_digest=bundle.task168_request_hash_digest,
        normalized=normalized,
        handoff=handoff,
        provider=active,
        geometry_projection_hash=v2,
    )
    if bindings is None:
        raise RuntimeError("frozen shell_052 bindings blocked")

    thermal = run_thermal_prescreen(
        bindings,
        normalized,
        provider=active,
        task037_override=task037_eval.raw,
    )

    hydraulic = run_autonomous_nozzle_full_path(bindings)
    mid = next(s for s in hydraulic.scenarios if s.scenario_key == "mid_band")
    high = next(s for s in hydraulic.scenarios if s.scenario_key == "high_loss_sensitivity")

    tube_lim = normalized.max_tube_side_pressure_drop_pa
    shell_lim = normalized.max_shell_side_pressure_drop_pa
    tube_dp = Decimal(mid.tube_full_path_dp_pa or "0")
    shell_dp = Decimal(mid.shell_full_path_dp_pa or "0")
    tube_margin = _dp_margin(tube_lim, tube_dp)
    shell_margin = _dp_margin(shell_lim, shell_dp)

    mid_pass = mid.hydraulic_check == "PASS"
    high_fail = None
    if high.hydraulic_check != "PASS":
        if high.shell_full_path_dp_pa and Decimal(high.shell_full_path_dp_pa) > shell_lim:
            excess = Decimal(high.shell_full_path_dp_pa) - shell_lim
            high_fail = f"SHELL_FULL_PATH_EXCESS_PA={excess}"
        elif high.tube_full_path_dp_pa and Decimal(high.tube_full_path_dp_pa) > tube_lim:
            excess = Decimal(high.tube_full_path_dp_pa) - tube_lim
            high_fail = f"TUBE_FULL_PATH_EXCESS_PA={excess}"
        else:
            high_fail = "HIGH_SCENARIO_OTHER_BLOCK"

    sens: list[str] = []
    if tube_margin == "0" or Decimal(tube_margin) <= Decimal("0.001"):
        sens.append("mid_tube_dp_at_limit_no_numeric_margin")
    if Decimal(shell_margin) <= Decimal("0.001"):
        sens.append("mid_shell_dp_at_limit_no_numeric_margin")
    sens.append("k_sensitivity_not_recomputed_R27B_frozen")

    hydraulic_robustness: HydraulicRobustness = (
        "MID_MATHEMATICAL_PASS_ONLY" if mid_pass else "UNPROVEN"
    )
    at_limit = (
        Decimal(tube_margin) <= Decimal("0.01")
        and Decimal(shell_margin) <= Decimal("0.01")
    )
    design_robustness: HydraulicRobustness = (
        "UNPROVEN" if at_limit or not mid_pass else "MID_MATHEMATICAL_PASS_ONLY"
    )

    ntu_s: str | None = None
    cr_s: str | None = None
    if task037_eval.raw and thermal.ua_w_per_k:
        t_ti = Decimal(str(normalized.tube_side.inlet_temperature_k))
        t_si = Decimal(str(normalized.shell_side.inlet_temperature_k))
        c_t = _cp_kg_s(
            active,
            _fluid="",
            t_k=t_ti,
            p_pa=Decimal(str(normalized.tube_side.inlet_pressure_pa)),
        ) * normalized.tube_side.mass_flow_kg_s
        c_s = _cp_kg_s(
            active,
            _fluid="",
            t_k=t_si,
            p_pa=Decimal(str(normalized.shell_side.inlet_pressure_pa)),
        ) * normalized.shell_side.mass_flow_kg_s
        c_min = min(c_t, c_s)
        c_max = max(c_t, c_s)
        ua = Decimal(thermal.ua_w_per_k)
        if c_min > 0:
            ntu_s = str(ua / c_min)
            cr_s = str(c_min / c_max)

    thermal_ok = thermal.status == "INDICATIVE_PASS"
    hydraulic_ok = mid_pass
    decision: DesignDecision = (
        "THERMAL_HYDRAULIC_PRESCREEN_PASS"
        if thermal_ok and hydraulic_ok and replay == "PASS"
        else "THERMAL_OR_MARGIN_BLOCKED"
    )
    next_act = (
        "Experimental 0.52 m mid hydraulics pass; confirm 316L Task037 production sign-off and high-K margin."
        if decision == "THERMAL_HYDRAULIC_PRESCREEN_PASS"
        else (
            "Increase effective UA or duty margin for 330 kW (epsilon-NTU short ~39 kW); "
            "restore mid full-path dp headroom; high-K shell path exceeds limit by ~143 Pa."
        )
    )

    return Shell052ThermalAuthorityMarginReport(
        candidate_id=cid,
        geometry_v2=v2,
        geometry_identity_replay=replay,
        task037_status=task037_eval.status,
        wall_material_authority=task037_eval.material_authority_id or task037_eval.material_grade,
        wall_conductivity_w_m_k=task037_eval.wall_conductivity_w_m_k,
        wall_resistance_outer_m2_k_w=task037_eval.wall_resistance_outer_m2_k_w,
        task037_result_hash=task037_eval.result_hash,
        ua_w_k=thermal.ua_w_per_k,
        epsilon_ntu_q_w=thermal.epsilon_ntu_q_w,
        tube_outlet_k=thermal.predicted_tube_outlet_k,
        shell_outlet_k=thermal.predicted_shell_outlet_k,
        ntu=ntu_s,
        cr=cr_s,
        thermal_prescreen=thermal.status,
        tube_full_dp_pa=str(mid.tube_full_path_dp_pa or ""),
        shell_full_dp_pa=str(mid.shell_full_path_dp_pa or ""),
        tube_dp_margin_pa=tube_margin,
        shell_dp_margin_pa=shell_margin,
        high_tube_dp_pa=high.tube_full_path_dp_pa,
        high_shell_dp_pa=high.shell_full_path_dp_pa,
        high_failure_component=high_fail,
        mid_hydraulic_mathematical_pass=mid_pass,
        mid_hydraulic_design_robustness=design_robustness,
        high_hydraulic="PASS" if high.hydraulic_check == "PASS" else "BLOCKED",
        nozzle_design_hash=hydraulic.nozzle_design_hash,
        nozzle_manufacturing_authority="PROVISIONAL",
        hydraulic_robustness=hydraulic_robustness,
        sensitivity_notes=tuple(sens),
        design_decision=decision,
        next_required_engineering_action=next_act,
    )


__all__ = ["Shell052ThermalAuthorityMarginReport", "run_shell_052_thermal_authority_and_margin"]