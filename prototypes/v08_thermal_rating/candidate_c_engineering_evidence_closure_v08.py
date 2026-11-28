"""Design C freeze: engineering spec, review, and evidence validators."""

# ruff: noqa: E501

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    _side_inlet_density_kg_m3,
)
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
    geometry_identity_v2_hash,
    geometry_projection_hash_v1,
)
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    _fluid_density_kg_m3,
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import build_candidate_rating_bindings
from prototypes.v08_thermal_rating.candidate_c_identity_v08 import (
    CANDIDATE_C_SHELL_NOZZLE_ID_M,
    CANDIDATE_C_SHELL_NOZZLE_ID_MM,
    CANDIDATE_C_TUBE_NOZZLE_ID_M,
    CANDIDATE_C_TUBE_NOZZLE_ID_MM,
)
from prototypes.v08_thermal_rating.first_joint_candidate_freeze_v08 import (
    ENGINEERING_DESIGN_STATUS,
    _resolve_frozen_bundle,
    _thermal_ntu_bundle,
)
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_FIRST_JOINT_CANDIDATE_ID,
    FROZEN_FIRST_JOINT_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.four_port_nozzle_correction_and_validation_v08 import (
    _common_diameter_bounds,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import run_thermal_prescreen
from prototypes.v08_thermal_rating.v08_candidate_c_validators_v08 import (
    ValidatorStatus,
    evaluate_nozzle_only_high_k_feasibility,
    validate_fixed_nozzle_override_check,
    validate_outlet_property_consistency,
)
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import (
    build_engineering_case_v2_from_v08,
)
from prototypes.v08_thermal_rating.v08_task037_evaluate_binding_v08 import (
    evaluate_binding_task037,
)

JointPrescreen = Literal["PASS", "BLOCKED"]
HighKFeasibility = Literal[
    "INFEASIBLE_UNDER_ASSUMED_K",
    "FEASIBLE_UNDER_ASSUMED_K",
    "NOT_EVALUATED",
]


@dataclass(frozen=True)
class CandidateCEvidenceClosureReport:
    candidate_id: str
    geometry_v2: str
    structure_identity_replay: Literal["PASS", "BLOCKED"]
    nozzle_design_hash: str
    outlet_property_consistency: ValidatorStatus
    outlet_property_failures: tuple[str, ...]
    fixed_nozzle_override_check: ValidatorStatus
    fixed_override_failures: tuple[str, ...]
    four_port_strict_velocity_check: ValidatorStatus
    clean_q_w: str
    fouled_q_w: str
    clean_q_margin_w: str
    mid_tube_dp_pa: str | None
    mid_shell_dp_pa: str | None
    mid_tube_margin_pa: str | None
    mid_shell_margin_pa: str | None
    high_tube_dp_pa: str | None
    high_shell_dp_pa: str | None
    mid_joint_prescreen: JointPrescreen
    all_scenario_prescreen: JointPrescreen
    nozzle_only_high_k_feasibility: HighKFeasibility
    min_high_tube_dp_at_max_nozzle_pa: str | None
    design_spec: dict[str, Any]
    engineering_review_md: str


def _scenario_sections(hydraulic: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for row in hydraulic.scenarios:
        out[row.scenario_key] = {
            "hydraulic_check": row.hydraulic_check,
            "tube_full_path_dp_pa": row.tube_full_path_dp_pa,
            "shell_full_path_dp_pa": row.shell_full_path_dp_pa,
            "tube_margin_pa": row.tube_margin_pa,
            "shell_margin_pa": row.shell_margin_pa,
            "tube_breakdown": dict(row.tube_breakdown),
            "shell_breakdown": dict(row.shell_breakdown),
        }
    return out


def _build_design_spec(
    *,
    bundle: Any,
    bindings: Any,
    normalized: NormalizedUserDesignCase,
    clean: Any,
    foul: Any,
    hydraulic: Any,
    t037_c: Any,
    t037_f: Any,
    ntu: str | None,
    cr: str | None,
    eff: str | None,
    validators: dict[str, Any],
) -> dict[str, Any]:
    struct = bundle.structural_bundle
    cand = struct.candidate
    layout = struct.bundle.task021_layout
    target_q = str(normalized.target_duty_w)
    q_clean = Decimal(clean.epsilon_ntu_q_w or "0")
    q_margin = str((q_clean - Decimal(target_q)).quantize(Decimal("0.1")))
    ports = [
        {
            "port_id": p.port_id,
            "inside_diameter_m": str(p.inside_diameter_m),
            "inside_diameter_mm": str(
                (p.inside_diameter_m * Decimal("1000")).quantize(Decimal("0.01"))
            ),
            "effective_area_m2": str(p.effective_area_m2),
            "mass_flow_kg_s": str(p.mass_flow_kg_s),
            "density_kg_m3": str(p.density_kg_m3),
            "velocity_m_s": str(p.velocity_m_s),
            "velocity_basis": p.velocity_basis,
        }
        for p in hydraulic.ports
    ]
    t174 = bindings.rating_request.task174_result
    t166 = bindings.bundle.bundle.task166_result
    return {
        "schema": "hxforge.candidate-C-design-spec.v1",
        "task_id": "V08_03_CANDIDATE_C_ENGINEERING_EVIDENCE_CLOSURE",
        "engineering_design_status": ENGINEERING_DESIGN_STATUS,
        "scheme": "C",
        "candidate_id": FROZEN_FIRST_JOINT_CANDIDATE_ID,
        "geometry_identity_v2": FROZEN_FIRST_JOINT_GEOMETRY_V2,
        "tube_common_nozzle_id_mm": str(CANDIDATE_C_TUBE_NOZZLE_ID_MM),
        "shell_common_nozzle_id_mm": str(CANDIDATE_C_SHELL_NOZZLE_ID_MM),
        "nozzle_design_hash": hydraulic.nozzle_design_hash,
        "task168_request_hash_digest": struct.task168_request_hash_digest,
        "task166_applicability": getattr(t166, "applicability", None)
        and getattr(t166.applicability, "status", None)
        and str(t166.applicability.status),
        "task174_result_hash": getattr(t174, "result_hash", None),
        "task037_clean_result_hash": t037_c.result_hash,
        "task037_fouled_result_hash": t037_f.result_hash,
        "geometry_projection_hash": bindings.geometry_projection_hash,
        "geometry": {
            "shell_inside_diameter_m": str(cand.shell_inside_diameter_m),
            "tube_length_m": str(cand.tube_length_m),
            "physical_tube_count": int(layout.physical_tube_count),
            "baffle_count": cand.baffle_count,
            "baffle_cut_fraction": str(cand.baffle_cut_fraction),
            "baffle_spacing_m": str(cand.baffle_spacing_m),
            "placement_envelope_scale": bundle.envelope_scale,
        },
        "thermal_results": {
            "clean": {
                "q_w": clean.epsilon_ntu_q_w,
                "ua_w_per_k": clean.ua_w_per_k,
                "status": clean.status,
                "predicted_tube_outlet_k": clean.predicted_tube_outlet_k,
                "predicted_shell_outlet_k": clean.predicted_shell_outlet_k,
                "q_margin_w": q_margin,
            },
            "fouled_t039_demo": {
                "q_w": foul.epsilon_ntu_q_w,
                "status": foul.status,
            },
            "ntu_clean": ntu,
            "cr_clean": cr,
            "effectiveness_clean": eff,
        },
        "hydraulic_results": {
            "r27b_k_authority": {
                k: {
                    "scenario_id": v["scenario_id"],
                    "source_nature": v["source_nature"],
                    "disclosure": v["disclosure"],
                }
                for k, v in R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS.items()
            },
            "outlet_pressure_disclosure": (
                "Outlet nozzle COOLPROP_TP uses ε-NTU prescreen outlet T with case inlet P "
                "(experimental approximation; Task173 converged outlet pressure not available)."
            ),
            "nozzle_manufacturing_authority": "PROVISIONAL",
            "nozzle_standard_series": "UNRESOLVED",
            "nozzle_reinforcement": str(hydraulic.installation.nozzle_reinforcement),
            "scenarios": _scenario_sections(hydraulic),
            "ports": ports,
        },
        "validators": validators,
    }


def _engineering_review_md(
    spec: dict[str, Any],
    *,
    high_k_note: str | None,
    fouled_q: str,
) -> str:
    clean = spec["thermal_results"]["clean"]
    mid = spec["hydraulic_results"]["scenarios"].get("mid_band", {})
    high = spec["hydraulic_results"]["scenarios"].get("high_loss_sensitivity", {})
    lines = [
        "# Design C — Experimental Prescreen Evidence (not manufacturing acceptance)",
        "",
        f"**Scheme C nozzles:** tube {spec['tube_common_nozzle_id_mm']} mm, "
        f"shell {spec['shell_common_nozzle_id_mm']} mm (trial IDs, not standard series).",
        "",
        "## Thermal (indicative ε-NTU)",
        "",
        f"- CLEAN Q = {clean['q_w']} W; margin vs target = {clean['q_margin_w']} W "
        "(~0.29% computational slack only — **not** verified thermal design margin).",
        f"- T039_DEMO fouling Q = {fouled_q} W — **does not meet** 330 kW target.",
        "- Task037 material/fouling authorities remain **experimental**.",
        "- Task173 production thermal acceptance: **BLOCKED**.",
        "",
        "## Hydraulics (R27B assumption full path + outlet COOLPROP_TP)",
        "",
        f"- Mid tube/shell Δp: {mid.get('tube_full_path_dp_pa')} / {mid.get('shell_full_path_dp_pa')} Pa.",
        f"- High tube/shell Δp: {high.get('tube_full_path_dp_pa')} / {high.get('shell_full_path_dp_pa')} Pa.",
        "- Three K scenarios are **not** owner-verified; sensitivity only.",
        "",
        "## High-K tube bound",
        "",
        high_k_note or "High-K nozzle-only feasibility not evaluated.",
        "",
        "## Manufacturing gaps",
        "",
        "- Standard nozzle effective ID, strength, and reinforcement: **UNRESOLVED**.",
        "- Licensed plant fouling factors: **not approved**.",
        "",
        "## Validator summary",
        "",
        f"- OUTLET_PROPERTY_CONSISTENCY: {spec['validators']['outlet_property_consistency']}",
        f"- FIXED_NOZZLE_OVERRIDE_CHECK: {spec['validators']['fixed_nozzle_override_check']}",
        f"- FOUR_PORT_STRICT_VELOCITY: {spec['validators']['four_port_strict_velocity_check']}",
    ]
    return "\n".join(lines)


def run_candidate_c_engineering_evidence_closure(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
) -> CandidateCEvidenceClosureReport:
    active = provider or CoolPropProvider()
    bundle = _resolve_frozen_bundle(normalized, handoff)
    struct = bundle.structural_bundle
    v2 = geometry_identity_v2_hash(struct)
    replay: Literal["PASS", "BLOCKED"] = (
        "PASS"
        if struct.candidate.candidate_id == FROZEN_FIRST_JOINT_CANDIDATE_ID
        and v2 == FROZEN_FIRST_JOINT_GEOMETRY_V2
        else "BLOCKED"
    )
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
        raise RuntimeError("bindings blocked for design C")

    t037_c = evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
    t037_f = evaluate_binding_task037(bindings, fouling_scenario="T039_DEMO_FOULING")
    clean = run_thermal_prescreen(
        bindings, normalized, provider=active, task037_override=t037_c.raw
    )
    foul = run_thermal_prescreen(bindings, normalized, provider=active, task037_override=t037_f.raw)
    tube_out_k = Decimal(clean.predicted_tube_outlet_k) if clean.predicted_tube_outlet_k else None
    shell_out_k = (
        Decimal(clean.predicted_shell_outlet_k) if clean.predicted_shell_outlet_k else None
    )
    if tube_out_k is None or shell_out_k is None:
        raise RuntimeError("CLEAN prescreen missing outlet temperatures")

    hydraulic = run_autonomous_nozzle_full_path(
        bindings,
        fixed_tube_inside_diameter_m=CANDIDATE_C_TUBE_NOZZLE_ID_M,
        fixed_shell_inside_diameter_m=CANDIDATE_C_SHELL_NOZZLE_ID_M,
        tube_outlet_temperature_k=tube_out_k,
        shell_outlet_temperature_k=shell_out_k,
        provider=active,
    )

    outlet_status, outlet_fails = validate_outlet_property_consistency(
        bindings=bindings, clean=clean, hydraulic=hydraulic, provider=active
    )
    fixed_status, fixed_fails = validate_fixed_nozzle_override_check(
        bindings=bindings, hydraulic=hydraulic
    )
    strict: ValidatorStatus = (
        "PASS" if hydraulic.nozzle_velocity_check == "PASS" and not fixed_fails else "BLOCKED"
    )

    case = build_engineering_case_v2_from_v08(normalized)
    tube_rho_in = Decimal(str(_side_inlet_density_kg_m3(case, "tube_side")))
    tube_p = Decimal(str(case.tube_side.inlet_pressure_pa))
    tube_rho_out = _fluid_density_kg_m3(active, temperature_k=tube_out_k, pressure_pa=tube_p)
    tube_bounds = _common_diameter_bounds(
        mass_kg_s=Decimal(str(case.tube_side.mass_flow_kg_s)),
        rho_in=tube_rho_in,
        rho_out=tube_rho_out,
        side="tube",
    )
    high_k_status, min_high_dp, high_k_note = evaluate_nozzle_only_high_k_feasibility(
        bindings=bindings,
        tube_d_max_m=tube_bounds.common_feasible_upper_m,
        shell_d_m=CANDIDATE_C_SHELL_NOZZLE_ID_M,
        tube_out_k=tube_out_k,
        shell_out_k=shell_out_k,
    )

    ntu = cr = eff = None
    if clean.ua_w_per_k:
        ntu, cr, eff = _thermal_ntu_bundle(
            provider=active, normalized=normalized, ua_w_k=clean.ua_w_per_k
        )

    target_q = Decimal(str(normalized.target_duty_w))
    q_clean = Decimal(clean.epsilon_ntu_q_w or "0")
    q_margin = str((q_clean - target_q).quantize(Decimal("0.1")))

    mid = next(s for s in hydraulic.scenarios if s.scenario_key == "mid_band")
    high = next(s for s in hydraulic.scenarios if s.scenario_key == "high_loss_sensitivity")
    thermal_pass = clean.status == "INDICATIVE_PASS"
    mid_joint: JointPrescreen = "PASS"
    if (
        not thermal_pass
        or strict != "PASS"
        or mid.hydraulic_check != "PASS"
        or outlet_status != "PASS"
        or fixed_status != "PASS"
    ):
        mid_joint = "BLOCKED"
    all_pass: JointPrescreen = (
        "PASS"
        if all(s.hydraulic_check == "PASS" for s in hydraulic.scenarios)
        and strict == "PASS"
        and thermal_pass
        else "BLOCKED"
    )

    validators_payload = {
        "outlet_property_consistency": outlet_status,
        "outlet_property_failures": list(outlet_fails),
        "fixed_nozzle_override_check": fixed_status,
        "fixed_override_failures": list(fixed_fails),
        "four_port_strict_velocity_check": strict,
        "nozzle_only_high_k_feasibility": high_k_status,
        "min_high_tube_dp_at_max_nozzle_pa": min_high_dp,
    }
    spec = _build_design_spec(
        bundle=bundle,
        bindings=bindings,
        normalized=normalized,
        clean=clean,
        foul=foul,
        hydraulic=hydraulic,
        t037_c=t037_c,
        t037_f=t037_f,
        ntu=ntu,
        cr=cr,
        eff=eff,
        validators=validators_payload,
    )
    review = _engineering_review_md(
        spec, high_k_note=high_k_note, fouled_q=str(foul.epsilon_ntu_q_w or "UNAVAILABLE")
    )

    return CandidateCEvidenceClosureReport(
        candidate_id=FROZEN_FIRST_JOINT_CANDIDATE_ID,
        geometry_v2=FROZEN_FIRST_JOINT_GEOMETRY_V2,
        structure_identity_replay=replay,
        nozzle_design_hash=hydraulic.nozzle_design_hash,
        outlet_property_consistency=outlet_status,
        outlet_property_failures=outlet_fails,
        fixed_nozzle_override_check=fixed_status,
        fixed_override_failures=fixed_fails,
        four_port_strict_velocity_check=strict,
        clean_q_w=str(clean.epsilon_ntu_q_w or "UNAVAILABLE"),
        fouled_q_w=str(foul.epsilon_ntu_q_w or "UNAVAILABLE"),
        clean_q_margin_w=q_margin,
        mid_tube_dp_pa=mid.tube_full_path_dp_pa,
        mid_shell_dp_pa=mid.shell_full_path_dp_pa,
        mid_tube_margin_pa=mid.tube_margin_pa,
        mid_shell_margin_pa=mid.shell_margin_pa,
        high_tube_dp_pa=high.tube_full_path_dp_pa,
        high_shell_dp_pa=high.shell_full_path_dp_pa,
        mid_joint_prescreen=mid_joint,
        all_scenario_prescreen=all_pass,
        nozzle_only_high_k_feasibility=high_k_status,  # type: ignore[arg-type]
        min_high_tube_dp_at_max_nozzle_pa=min_high_dp,
        design_spec=spec,
        engineering_review_md=review,
    )


def write_candidate_c_artifacts(
    report: CandidateCEvidenceClosureReport,
    *,
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    jp = Path(json_path)
    mp = Path(md_path)
    jp.parent.mkdir(parents=True, exist_ok=True)
    mp.parent.mkdir(parents=True, exist_ok=True)
    jp.write_text(json.dumps(report.design_spec, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(report.engineering_review_md, encoding="utf-8")


__all__ = [
    "CandidateCEvidenceClosureReport",
    "run_candidate_c_engineering_evidence_closure",
    "write_candidate_c_artifacts",
]
