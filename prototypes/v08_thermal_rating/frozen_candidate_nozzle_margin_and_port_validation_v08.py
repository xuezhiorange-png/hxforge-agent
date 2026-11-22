"""Frozen candidate: baseline vs shell max-margin nozzle designs + four-port state."""

# ruff: noqa: E501

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
    geometry_projection_hash_v1,
)
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    AutonomousNozzleFullPathReport,
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import build_candidate_rating_bindings
from prototypes.v08_thermal_rating.first_joint_candidate_freeze_v08 import _resolve_frozen_bundle
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_BASELINE_SHELL_NOZZLE_ID_M,
    FROZEN_BASELINE_TUBE_NOZZLE_ID_M,
    FROZEN_FIRST_JOINT_CANDIDATE_ID,
    FROZEN_FIRST_JOINT_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.full_path_fixed_nozzle_evaluator_v08 import (
    select_fixed_nozzle_design,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import run_thermal_prescreen
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import (
    build_engineering_case_v2_from_v08,
    candidate_selection_record_from_bindings,
    task174_hydraulic_postpass_from_bindings,
)
from prototypes.v08_thermal_rating.v08_task037_evaluate_binding_v08 import (
    evaluate_binding_task037,
)

CheckLabel = Literal["PASS", "BLOCKED", "NOT_EVALUATED"]
JointPrescreen = Literal["PASS", "BLOCKED"]


@dataclass(frozen=True)
class NozzleDesignComparison:
    design_label: Literal["A_BASELINE_FROZEN", "B_SHELL_MAX_MARGIN"]
    hydraulic: AutonomousNozzleFullPathReport
    mid_joint_prescreen: JointPrescreen
    high_joint_prescreen: JointPrescreen


@dataclass(frozen=True)
class FrozenNozzleMarginPortValidationReport:
    candidate_id: str
    geometry_v2: str
    baseline_nozzle_design_hash: str
    optimized_nozzle_design_hash: str
    four_port_density_and_velocity_check: CheckLabel
    design_a: NozzleDesignComparison
    design_b: NozzleDesignComparison
    clean_q_w: str
    clean_q_margin_w: str
    fouled_q_w: str
    real_perturbation_sensitivity: CheckLabel
    high_tube_infeasible_under_frozen_geometry: bool
    high_tube_infeasible_note: str | None
    perturbation_details: tuple[dict[str, str], ...]
    comparison_spec: dict[str, Any]
    next_required_engineering_change: str


def _joint_prescreen(
    report: AutonomousNozzleFullPathReport, *, thermal_pass: bool
) -> JointPrescreen:
    if not thermal_pass:
        return "BLOCKED"
    mid = next(s for s in report.scenarios if s.scenario_key == "mid_band")
    if mid.hydraulic_check != "PASS" or report.nozzle_velocity_check != "PASS":
        return "BLOCKED"
    return "PASS"


def _high_prescreen(
    report: AutonomousNozzleFullPathReport, *, thermal_pass: bool
) -> JointPrescreen:
    if not thermal_pass:
        return "BLOCKED"
    high = next(s for s in report.scenarios if s.scenario_key == "high_loss_sensitivity")
    if high.hydraulic_check == "PASS" and report.nozzle_velocity_check == "PASS":
        return "PASS"
    return "BLOCKED"


def _four_port_check(report: AutonomousNozzleFullPathReport) -> CheckLabel:
    if report.nozzle_velocity_check != "PASS":
        return "BLOCKED"
    for port in report.ports:
        v = port.velocity_m_s
        if v < Decimal("1") or v > Decimal("3"):
            return "BLOCKED"
    return "PASS"


def _scenario_payload(report: AutonomousNozzleFullPathReport) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for row in report.scenarios:
        out[row.scenario_key] = {
            "tube_full_path_dp_pa": row.tube_full_path_dp_pa,
            "shell_full_path_dp_pa": row.shell_full_path_dp_pa,
            "tube_margin_pa": row.tube_margin_pa,
            "shell_margin_pa": row.shell_margin_pa,
            "hydraulic_check": row.hydraulic_check,
            "tube_breakdown": dict(row.tube_breakdown),
            "shell_breakdown": dict(row.shell_breakdown),
        }
    return out


def _ports_payload(report: AutonomousNozzleFullPathReport) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for p in report.ports:
        rows.append(
            {
                "port_id": p.port_id,
                "inside_diameter_m": str(p.inside_diameter_m),
                "inside_diameter_mm": str(
                    (p.inside_diameter_m * Decimal("1000")).quantize(Decimal("0.01"))
                ),
                "velocity_m_s": str(p.velocity_m_s.quantize(Decimal("0.0001"))),
                "density_kg_m3": str(p.density_kg_m3.quantize(Decimal("0.01"))),
                "mass_flow_kg_s": str(p.mass_flow_kg_s),
                "effective_area_m2": str(p.effective_area_m2),
                "velocity_basis": p.velocity_basis,
            }
        )
    return rows


def _verify_high_tube_at_min_feasible(
    bindings: Any,
    *,
    tube_d: Decimal,
    shell_d: Decimal,
    provider: CoolPropProvider,
) -> tuple[bool, str | None]:
    case = build_engineering_case_v2_from_v08(bindings.normalized)
    record = candidate_selection_record_from_bindings(bindings)
    postpass = task174_hydraulic_postpass_from_bindings(bindings)
    max_margin = select_fixed_nozzle_design(
        case=case,
        record=record,
        postpass=postpass,
        tube_nozzle_objective="MAX_MARGIN_WITHIN_VELOCITY_BAND",
        shell_nozzle_objective="MINIMUM_DIAMETER",
        fixed_shell_inside_diameter_m=shell_d,
    )
    frozen_h = run_autonomous_nozzle_full_path(
        bindings,
        fixed_tube_inside_diameter_m=tube_d,
        fixed_shell_inside_diameter_m=shell_d,
        provider=provider,
    )
    band_h = run_autonomous_nozzle_full_path(
        bindings,
        fixed_tube_inside_diameter_m=max_margin.tube_inside_diameter_m,
        fixed_shell_inside_diameter_m=shell_d,
        provider=provider,
    )
    high_frozen = next(s for s in frozen_h.scenarios if s.scenario_key == "high_loss_sensitivity")
    high_band = next(s for s in band_h.scenarios if s.scenario_key == "high_loss_sensitivity")
    if high_frozen.tube_full_path_dp_pa is None or high_band.tube_full_path_dp_pa is None:
        return False, None
    dp_frozen = Decimal(high_frozen.tube_full_path_dp_pa)
    dp_band_min = Decimal(high_band.tube_full_path_dp_pa)
    if abs(tube_d - max_margin.tube_inside_diameter_m) > Decimal("0.0001"):
        return False, None
    if abs(dp_frozen - dp_band_min) <= Decimal("0.5"):
        lim = bindings.normalized.max_tube_side_pressure_drop_pa
        if lim is not None and dp_frozen > lim:
            return True, "HIGH_TUBE_INFEASIBLE_FOR_FROZEN_INTERNAL_GEOMETRY_UNDER_ASSUMED_K"
    return False, None


def _perturbation_sensitivity(
    bindings: Any,
    *,
    tube_d: Decimal,
    shell_d: Decimal,
    tube_out_k: Decimal | None,
    shell_out_k: Decimal | None,
    provider: CoolPropProvider,
) -> tuple[CheckLabel, tuple[dict[str, str], ...]]:
    details: list[dict[str, str]] = []
    factors = (
        ("tube_id_plus_5pct", Decimal("1.05"), Decimal("1")),
        ("shell_id_plus_5pct", Decimal("1"), Decimal("1.05")),
    )
    base = run_autonomous_nozzle_full_path(
        bindings,
        fixed_tube_inside_diameter_m=tube_d,
        fixed_shell_inside_diameter_m=shell_d,
        tube_outlet_temperature_k=tube_out_k,
        shell_outlet_temperature_k=shell_out_k,
        provider=provider,
    )
    mid_base = next(s for s in base.scenarios if s.scenario_key == "mid_band")
    for label, t_scale, s_scale in factors:
        t_d = (tube_d * t_scale).quantize(Decimal("0.00001"))
        s_d = (shell_d * s_scale).quantize(Decimal("0.00001"))
        trial = run_autonomous_nozzle_full_path(
            bindings,
            fixed_tube_inside_diameter_m=t_d,
            fixed_shell_inside_diameter_m=s_d,
            tube_outlet_temperature_k=tube_out_k,
            shell_outlet_temperature_k=shell_out_k,
            provider=provider,
        )
        if trial.nozzle_velocity_check != "PASS":
            details.append({label: "BLOCKED_VELOCITY_BAND"})
            continue
        mid = next(s for s in trial.scenarios if s.scenario_key == "mid_band")
        if mid.shell_full_path_dp_pa is None or mid_base.shell_full_path_dp_pa is None:
            details.append({label: "UNAVAILABLE"})
            continue
        delta = Decimal(mid.shell_full_path_dp_pa) - Decimal(mid_base.shell_full_path_dp_pa)
        details.append(
            {
                label: (
                    f"mid_shell_dp_pa={mid.shell_full_path_dp_pa};"
                    f"delta_vs_baseline_pa={delta.quantize(Decimal('0.01'))}"
                )
            }
        )
    if not details:
        return "NOT_EVALUATED", tuple(details)
    blocked = any("BLOCKED" in next(iter(d.values())) for d in details)
    return ("BLOCKED" if blocked else "PASS"), tuple(details)


def run_frozen_nozzle_margin_and_port_validation(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
) -> FrozenNozzleMarginPortValidationReport:
    active = provider or CoolPropProvider()
    bundle = _resolve_frozen_bundle(normalized, handoff)
    struct = bundle.structural_bundle
    bindings = build_candidate_rating_bindings(
        struct,
        space_hash=bundle.candidate_space_hash,
        t168_digest=struct.task168_request_hash_digest,
        normalized=normalized,
        handoff=handoff,
        provider=active,
        geometry_projection_hash=geometry_projection_hash_v1(struct),
    )
    if bindings is None:
        raise RuntimeError("bindings blocked for frozen nozzle validation")

    t037_c = evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
    clean = run_thermal_prescreen(
        bindings, normalized, provider=active, task037_override=t037_c.raw
    )
    foul_eval = evaluate_binding_task037(bindings, fouling_scenario="T039_DEMO_FOULING")
    foul = run_thermal_prescreen(
        bindings, normalized, provider=active, task037_override=foul_eval.raw
    )
    thermal_pass = clean.status == "INDICATIVE_PASS"
    tube_out = Decimal(clean.predicted_tube_outlet_k) if clean.predicted_tube_outlet_k else None
    shell_out = Decimal(clean.predicted_shell_outlet_k) if clean.predicted_shell_outlet_k else None

    design_a_h = run_autonomous_nozzle_full_path(
        bindings,
        fixed_tube_inside_diameter_m=FROZEN_BASELINE_TUBE_NOZZLE_ID_M,
        fixed_shell_inside_diameter_m=FROZEN_BASELINE_SHELL_NOZZLE_ID_M,
        tube_nozzle_objective="MINIMUM_DIAMETER",
        shell_nozzle_objective="MINIMUM_DIAMETER",
        tube_outlet_temperature_k=tube_out,
        shell_outlet_temperature_k=shell_out,
        provider=active,
    )
    design_b_h = run_autonomous_nozzle_full_path(
        bindings,
        fixed_tube_inside_diameter_m=FROZEN_BASELINE_TUBE_NOZZLE_ID_M,
        tube_nozzle_objective="MINIMUM_DIAMETER",
        shell_nozzle_objective="MAX_MARGIN_WITHIN_VELOCITY_BAND",
        tube_outlet_temperature_k=tube_out,
        shell_outlet_temperature_k=shell_out,
        provider=active,
    )

    design_a = NozzleDesignComparison(
        design_label="A_BASELINE_FROZEN",
        hydraulic=design_a_h,
        mid_joint_prescreen=_joint_prescreen(design_a_h, thermal_pass=thermal_pass),
        high_joint_prescreen=_high_prescreen(design_a_h, thermal_pass=thermal_pass),
    )
    design_b = NozzleDesignComparison(
        design_label="B_SHELL_MAX_MARGIN",
        hydraulic=design_b_h,
        mid_joint_prescreen=_joint_prescreen(design_b_h, thermal_pass=thermal_pass),
        high_joint_prescreen=_high_prescreen(design_b_h, thermal_pass=thermal_pass),
    )

    port_a = _four_port_check(design_a_h)
    port_b = _four_port_check(design_b_h)
    port_check: CheckLabel = "PASS" if port_a == "PASS" and port_b == "PASS" else "BLOCKED"
    high_inf, high_note = _verify_high_tube_at_min_feasible(
        bindings,
        tube_d=FROZEN_BASELINE_TUBE_NOZZLE_ID_M,
        shell_d=FROZEN_BASELINE_SHELL_NOZZLE_ID_M,
        provider=active,
    )
    sens_status, sens_details = _perturbation_sensitivity(
        bindings,
        tube_d=design_b_h.ports[0].inside_diameter_m,
        shell_d=design_b_h.ports[2].inside_diameter_m,
        tube_out_k=tube_out,
        shell_out_k=shell_out,
        provider=active,
    )

    target_q = Decimal(str(normalized.target_duty_w))
    q_clean = Decimal(clean.epsilon_ntu_q_w or "0")
    q_margin = (q_clean - target_q).quantize(Decimal("0.1"))

    comparison: dict[str, Any] = {
        "schema": "hxforge.frozen-nozzle-design-comparison.v1",
        "task_id": "V08_03_FROZEN_CANDIDATE_NOZZLE_MARGIN_AND_PORT_STATE_VALIDATION",
        "candidate_id": FROZEN_FIRST_JOINT_CANDIDATE_ID,
        "geometry_v2": FROZEN_FIRST_JOINT_GEOMETRY_V2,
        "design_a_baseline_frozen": {
            "tube_nozzle_id_mm": str(
                (FROZEN_BASELINE_TUBE_NOZZLE_ID_M * Decimal("1000")).quantize(Decimal("0.01"))
            ),
            "shell_nozzle_id_mm": str(
                (FROZEN_BASELINE_SHELL_NOZZLE_ID_M * Decimal("1000")).quantize(Decimal("0.01"))
            ),
            "nozzle_design_hash": design_a_h.nozzle_design_hash,
            "ports": _ports_payload(design_a_h),
            "scenarios": _scenario_payload(design_a_h),
        },
        "design_b_shell_max_margin": {
            "tube_nozzle_id_mm": str(
                (design_b_h.ports[0].inside_diameter_m * Decimal("1000")).quantize(Decimal("0.01"))
            ),
            "shell_nozzle_id_mm": str(
                (design_b_h.ports[2].inside_diameter_m * Decimal("1000")).quantize(Decimal("0.01"))
            ),
            "nozzle_design_hash": design_b_h.nozzle_design_hash,
            "ports": _ports_payload(design_b_h),
            "scenarios": _scenario_payload(design_b_h),
        },
        "outlet_state_authority": "INDICATIVE_THERMAL_PRESCREEN_OUTLET",
        "perturbation_sensitivity": [dict(d) for d in sens_details],
    }

    mid_a = next(s for s in design_a_h.scenarios if s.scenario_key == "mid_band")
    mid_b = next(s for s in design_b_h.scenarios if s.scenario_key == "mid_band")
    shell_improved = (
        mid_b.shell_full_path_dp_pa is not None
        and mid_a.shell_full_path_dp_pa is not None
        and Decimal(mid_b.shell_full_path_dp_pa) < Decimal(mid_a.shell_full_path_dp_pa)
    )
    if port_check == "BLOCKED" and shell_improved:
        next_change = (
            "Design B shell max-margin ID (~160 mm computed) cuts mid shell Δp to ~963 Pa vs ~1180 Pa, "
            "but strict 1–3 m/s four-port check fails under ε-NTU outlet densities on frozen 124.02 mm "
            "tube nozzles; licensed nozzle resize or Task173 outlet state required before adoption."
        )
    elif design_b.mid_joint_prescreen == "PASS" and design_b.high_joint_prescreen == "BLOCKED":
        next_change = (
            "Adopt design B shell max-margin for mid shell margin only; high_K path still blocked."
        )
    elif design_b.mid_joint_prescreen == "PASS":
        next_change = "Validate design B nozzle IDs against manufacturing standard catalog."
    else:
        next_change = (
            "Nozzle-only optimization cannot clear joint prescreen with current frozen geometry."
        )

    return FrozenNozzleMarginPortValidationReport(
        candidate_id=FROZEN_FIRST_JOINT_CANDIDATE_ID,
        geometry_v2=FROZEN_FIRST_JOINT_GEOMETRY_V2,
        baseline_nozzle_design_hash=design_a_h.nozzle_design_hash,
        optimized_nozzle_design_hash=design_b_h.nozzle_design_hash,
        four_port_density_and_velocity_check=port_check,
        design_a=design_a,
        design_b=design_b,
        clean_q_w=str(clean.epsilon_ntu_q_w or "UNAVAILABLE"),
        clean_q_margin_w=str(q_margin),
        fouled_q_w=str(foul.epsilon_ntu_q_w or "UNAVAILABLE"),
        real_perturbation_sensitivity=sens_status,
        high_tube_infeasible_under_frozen_geometry=high_inf,
        high_tube_infeasible_note=high_note,
        perturbation_details=sens_details,
        comparison_spec=comparison,
        next_required_engineering_change=next_change,
    )


def write_nozzle_comparison_artifact(
    report: FrozenNozzleMarginPortValidationReport,
    path: str | Path,
) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report.comparison_spec, indent=2, sort_keys=True), encoding="utf-8")


__all__ = [
    "FrozenNozzleMarginPortValidationReport",
    "run_frozen_nozzle_margin_and_port_validation",
    "write_nozzle_comparison_artifact",
]
