"""Freeze first joint-pass candidate: design spec, thermal/hydraulic replay, engineering review."""

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
    geometry_identity_v2_hash,
    geometry_projection_hash_v1,
)
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    AutonomousNozzleFullPathReport,
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CandidateRatingBindings,
    build_candidate_rating_bindings,
)
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_FIRST_JOINT_CANDIDATE_ID,
    FROZEN_FIRST_JOINT_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import (
    RecoveredShell052Bundle,
    enumerate_shell_052_bounded_local_combos,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import (
    ThermalPrescreenResult,
    _cp_kg_s,
    _epsilon_ntu_counterflow,
    run_thermal_prescreen,
)
from prototypes.v08_thermal_rating.v08_epsilon_ntu_required_ua_v08 import required_ua_w_k_for_duty
from prototypes.v08_thermal_rating.v08_prescreen_validators_v08 import (
    ValidatorStatus,
    validate_frozen_structure_spec,
    validate_generic_user_constraints,
    validate_pareto_missing_result_handling,
)
from prototypes.v08_thermal_rating.v08_task037_evaluate_binding_v08 import (
    evaluate_binding_task037,
)

ENGINEERING_DESIGN_STATUS = "EXPERIMENTAL_PRESCREEN_ONLY"
HYDRAULIC_ENGINEERING_VALIDATION = "UNRESOLVED"
EffectivenessAuthority = Literal["INDICATIVE_EPSILON_NTU_COUNTERFLOW", "BLOCKED"]


@dataclass(frozen=True)
class FirstJointCandidateFreezeReport:
    candidate_id: str
    geometry_v2: str
    geometry_identity_replay: Literal["PASS", "BLOCKED"]
    structure_spec_complete: bool
    design_spec: dict[str, Any]
    engineering_review_md: str
    clean_thermal: ThermalPrescreenResult
    fouled_thermal: ThermalPrescreenResult
    hydraulic: AutonomousNozzleFullPathReport
    ntu_clean: str | None
    cr_clean: str | None
    effectiveness_clean: str | None
    sensitivity_notes: tuple[str, ...]
    generic_user_constraints: ValidatorStatus
    pareto_missing_result_handling: ValidatorStatus
    structure_spec_validation: ValidatorStatus


def _resolve_frozen_bundle(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
) -> RecoveredShell052Bundle:
    bundles, _ = enumerate_shell_052_bounded_local_combos(normalized, handoff)
    for item in bundles:
        v2 = geometry_identity_v2_hash(item.structural_bundle)
        if v2 == FROZEN_FIRST_JOINT_GEOMETRY_V2:
            return item
    raise RuntimeError(
        f"frozen first joint geometry_v2 {FROZEN_FIRST_JOINT_GEOMETRY_V2} not in bounded local combos"
    )


def _thermal_ntu_bundle(
    *,
    provider: CoolPropProvider,
    normalized: NormalizedUserDesignCase,
    ua_w_k: str,
) -> tuple[str, str, str]:
    t_ti = Decimal(str(normalized.tube_side.inlet_temperature_k))
    t_si = Decimal(str(normalized.shell_side.inlet_temperature_k))
    c_t = (
        _cp_kg_s(
            provider,
            _fluid="",
            t_k=t_ti,
            p_pa=Decimal(str(normalized.tube_side.inlet_pressure_pa)),
        )
        * normalized.tube_side.mass_flow_kg_s
    )
    c_s = (
        _cp_kg_s(
            provider,
            _fluid="",
            t_k=t_si,
            p_pa=Decimal(str(normalized.shell_side.inlet_pressure_pa)),
        )
        * normalized.shell_side.mass_flow_kg_s
    )
    _, _, _, eff = _epsilon_ntu_counterflow(
        ua=Decimal(ua_w_k),
        c_hot=c_t,
        c_cold=c_s,
        t_hot_in=t_ti,
        t_cold_in=t_si,
    )
    c_min = min(c_t, c_s)
    c_max = max(c_t, c_s)
    cr = c_min / c_max if c_max > 0 else Decimal("0")
    ntu = Decimal(ua_w_k) / c_min if c_min > 0 else Decimal("0")
    return str(ntu.quantize(Decimal("0.001"))), str(cr.quantize(Decimal("0.0001"))), str(
        eff.quantize(Decimal("0.0001"))
    )


def _scenario_block(scenario_key: str, hydraulic: AutonomousNozzleFullPathReport) -> dict[str, Any]:
    scenario = next(s for s in hydraulic.scenarios if s.scenario_key == scenario_key)
    return {
        "scenario_key": scenario_key,
        "hydraulic_check": scenario.hydraulic_check,
        "tube_full_path_dp_pa": scenario.tube_full_path_dp_pa or "UNAVAILABLE",
        "shell_full_path_dp_pa": scenario.shell_full_path_dp_pa or "UNAVAILABLE",
        "tube_margin_pa": scenario.tube_margin_pa or "UNAVAILABLE",
        "shell_margin_pa": scenario.shell_margin_pa or "UNAVAILABLE",
        "tube_breakdown": dict(scenario.tube_breakdown),
        "shell_breakdown": dict(scenario.shell_breakdown),
    }


def _sensitivity_notes(
    *,
    hydraulic: AutonomousNozzleFullPathReport,
    normalized: NormalizedUserDesignCase,
) -> tuple[str, ...]:
    notes: list[str] = []
    mid = next(s for s in hydraulic.scenarios if s.scenario_key == "mid_band")
    high = next(s for s in hydraulic.scenarios if s.scenario_key == "high_loss_sensitivity")
    shell_lim = normalized.max_shell_side_pressure_drop_pa
    if mid.shell_margin_pa and Decimal(mid.shell_margin_pa) <= Decimal("0.01"):
        notes.append(
            "mid_band shell full-path Δp within 0.01 Pa of user limit; "
            "numerical prescreen pass is not manufacturing margin."
        )
    if high.shell_full_path_dp_pa and shell_lim is not None:
        excess = Decimal(high.shell_full_path_dp_pa) - shell_lim
        if excess > 0:
            dominant = max(
                ((k, Decimal(v)) for k, v in high.shell_breakdown.items()),
                key=lambda kv: kv[1],
                default=("unknown", Decimal("0")),
            )
            notes.append(
                f"high_loss_sensitivity shell excess {excess.quantize(Decimal('0.01'))} Pa; "
                f"largest listed component={dominant[0]} ({dominant[1]} Pa)."
            )
    notes.append(
        "Nozzle bore perturbation sensitivity is computed in the nozzle margin comparison "
        "artifact (±5% ID reruns on mid_band full path), not analytic estimates."
    )
    notes.append(
        "Placement envelope scale 0.80 is Task021 tube-center envelope fraction of shell ID, "
        "not baffle spacing."
    )
    notes.append(f"HYDRAULIC_ENGINEERING_VALIDATION={HYDRAULIC_ENGINEERING_VALIDATION}")
    return tuple(notes)


def _thermal_block(label: str, thermal: ThermalPrescreenResult) -> dict[str, Any]:
    return {
        "label": label,
        "status": thermal.status,
        "ua_w_per_k": thermal.ua_w_per_k or "UNAVAILABLE",
        "epsilon_ntu_q_w": thermal.epsilon_ntu_q_w or "UNAVAILABLE",
        "target_duty_gap_w": thermal.target_duty_gap_w or "UNAVAILABLE",
        "predicted_tube_outlet_k": thermal.predicted_tube_outlet_k or "UNAVAILABLE",
        "predicted_shell_outlet_k": thermal.predicted_shell_outlet_k or "UNAVAILABLE",
        "shell_htc_w_m2_k": thermal.shell_htc_w_m2_k or "UNAVAILABLE",
        "tube_htc_w_m2_k": thermal.tube_htc_w_m2_k or "UNAVAILABLE",
        "area_basis_m2": thermal.area_basis_m2 or "UNAVAILABLE",
        "wall_resistance_source": thermal.wall_resistance_source or "UNAVAILABLE",
        "property_basis": thermal.property_basis or "UNAVAILABLE",
        "task166_applicability": thermal.task166_applicability,
        "notes": list(thermal.notes),
    }


def _build_design_spec(
    *,
    bundle: RecoveredShell052Bundle,
    bindings: CandidateRatingBindings,
    normalized: NormalizedUserDesignCase,
    clean: ThermalPrescreenResult,
    foul: ThermalPrescreenResult,
    hydraulic: AutonomousNozzleFullPathReport,
    ntu: str | None,
    cr: str | None,
    effectiveness: str | None,
    task037_clean_authority: str,
    task037_foul_authority: str,
) -> dict[str, Any]:
    struct = bundle.structural_bundle
    cand = struct.candidate
    shell = struct.shell_record
    layout = struct.bundle.task021_layout
    tube_id = cand.tube_outer_diameter_m - Decimal("2") * cand.tube_wall_thickness_m
    target_q = str(normalized.target_duty_w)
    q_clean = Decimal(clean.epsilon_ntu_q_w or "0")
    q_margin = (
        str((q_clean - Decimal(target_q)).quantize(Decimal("0.1")))
        if clean.epsilon_ntu_q_w
        else "UNAVAILABLE"
    )
    ports = [
        {
            "port_id": p.port_id,
            "inside_diameter_mm": str((p.inside_diameter_m * Decimal("1000")).quantize(Decimal("0.01"))),
            "velocity_m_s": str(p.velocity_m_s.quantize(Decimal("0.001"))),
            "effective_area_m2": str(p.effective_area_m2),
            "size_authority": p.size_authority,
        }
        for p in hydraulic.ports
    ]
    return {
        "schema": "hxforge.first-joint-candidate-design-spec.v1",
        "task_id": "V08_03_FIRST_JOINT_CANDIDATE_FREEZE_AND_RISK_VALIDATION",
        "engineering_design_status": ENGINEERING_DESIGN_STATUS,
        "hydraulic_engineering_validation": HYDRAULIC_ENGINEERING_VALIDATION,
        "candidate_id": cand.candidate_id,
        "geometry_identity_v2": FROZEN_FIRST_JOINT_GEOMETRY_V2,
        "task168_request_hash_digest": struct.task168_request_hash_digest,
        "structural_source": {
            "origin": "SHELL_052_LOCAL_COMBO",
            "recovery_authority_label": bundle.experimental_authority_label,
            "discrete_space_authority_id": bundle.discrete_space_authority_id,
            "discrete_space_content_hash": bundle.discrete_space_content_hash,
            "candidate_space_hash": bundle.candidate_space_hash,
        },
        "geometry": {
            "shell_inside_diameter_m": str(shell.shell_inside_diameter_m),
            "tube_outer_diameter_m": str(cand.tube_outer_diameter_m),
            "tube_inner_diameter_m": str(tube_id),
            "tube_wall_thickness_m": str(cand.tube_wall_thickness_m),
            "tube_pitch_m": str(cand.tube_pitch_m),
            "tube_length_m": str(cand.tube_length_m),
            "tube_pass_count": cand.tube_pass_count,
            "tube_layout_pattern": cand.tube_layout,
            "physical_tube_count": int(layout.physical_tube_count),
            "baffle_type": cand.baffle_type,
            "baffle_cut_fraction": str(cand.baffle_cut_fraction),
            "baffle_spacing_m": str(cand.baffle_spacing_m),
            "baffle_count": cand.baffle_count,
            "placement_envelope_diameter_m": bundle.placement_envelope_diameter_m,
            "placement_envelope_scale": str(bundle.envelope_scale),
            "placement_envelope_note": (
                "envelope_scale is Task021 tube-center envelope / shell ID, not baffle pitch"
            ),
            "layout_identity": getattr(layout, "layout_id", "UNAVAILABLE"),
        },
        "user_case_limits": {
            "target_duty_w": target_q,
            "max_tube_side_pressure_drop_pa": str(normalized.max_tube_side_pressure_drop_pa),
            "max_shell_side_pressure_drop_pa": str(normalized.max_shell_side_pressure_drop_pa),
        },
        "thermal_authorities": {
            "clean_task037_content_hash": task037_clean_authority,
            "fouled_task037_content_hash": task037_foul_authority,
            "fouling_scenario_labels": ("CLEAN", "T039_DEMO_FOULING"),
            "model_scope": (
                "Indicative counterflow ε-NTU prescreen using Task166/026/037 + CoolProp; "
                "not production Task173/BVP acceptance."
            ),
        },
        "thermal_results": {
            "clean": _thermal_block("CLEAN", clean),
            "fouled_t039_demo": _thermal_block("T039_DEMO_FOULING", foul),
            "required_ua_w_per_k": _required_ua(normalized),
            "ntu_clean": ntu or "UNAVAILABLE",
            "cr_clean": cr or "UNAVAILABLE",
            "effectiveness_clean": effectiveness or "UNAVAILABLE",
            "effectiveness_authority": "INDICATIVE_EPSILON_NTU_COUNTERFLOW",
            "q_margin_note": (
                f"Q_clean - target = {q_margin} W is computational prescreen slack only, "
                "not a verified thermal design margin."
            ),
        },
        "hydraulic_results": {
            "nozzle_design_hash": hydraulic.nozzle_design_hash,
            "nozzle_velocity_check": hydraulic.nozzle_velocity_check,
            "nozzle_manufacturing_authority": "PROVISIONAL",
            "scenario_robustness": hydraulic.scenario_robustness,
            "low_loss": _scenario_block("low_loss_sensitivity", hydraulic),
            "mid_band": _scenario_block("mid_band", hydraulic),
            "high_loss": _scenario_block("high_loss_sensitivity", hydraulic),
            "ports": ports,
        },
        "geometry_projection_hash": bindings.geometry_projection_hash,
    }


def _required_ua(normalized: NormalizedUserDesignCase) -> str:
    t_ti = Decimal(str(normalized.tube_side.inlet_temperature_k))
    t_si = Decimal(str(normalized.shell_side.inlet_temperature_k))
    provider = CoolPropProvider()
    c_t = (
        _cp_kg_s(
            provider,
            _fluid="",
            t_k=t_ti,
            p_pa=Decimal(str(normalized.tube_side.inlet_pressure_pa)),
        )
        * normalized.tube_side.mass_flow_kg_s
    )
    c_s = (
        _cp_kg_s(
            provider,
            _fluid="",
            t_k=t_si,
            p_pa=Decimal(str(normalized.shell_side.inlet_pressure_pa)),
        )
        * normalized.shell_side.mass_flow_kg_s
    )
    req = required_ua_w_k_for_duty(
        target_q_w=normalized.target_duty_w,
        c_hot=c_t,
        c_cold=c_s,
        t_hot_in=t_ti,
        t_cold_in=t_si,
    )
    return str(req.quantize(Decimal("0.01"))) if req else "UNAVAILABLE"


def _engineering_review_md(
    *,
    design_spec: dict[str, Any],
    sensitivity: tuple[str, ...],
    hydraulic: AutonomousNozzleFullPathReport,
) -> str:
    g = design_spec["geometry"]
    clean = design_spec["thermal_results"]["clean"]
    foul = design_spec["thermal_results"]["fouled_t039_demo"]
    mid = design_spec["hydraulic_results"]["mid_band"]
    high = design_spec["hydraulic_results"]["high_loss"]
    lines = [
        "# First Joint Candidate — Engineering Review (Experimental Prescreen Only)",
        "",
        f"**Status:** `{ENGINEERING_DESIGN_STATUS}` — not manufacturing acceptance.",
        "",
        "## Structure",
        "",
        (
            f"- Shell ID **{g['shell_inside_diameter_m']} m**, tube length **{g['tube_length_m']} m**, "
            f"**{g['physical_tube_count']}** tubes, **{g['tube_pass_count']}** passes, layout `{g['tube_layout_pattern']}`."
        ),
        (
            f"- Tube **OD {g['tube_outer_diameter_m']} m** / **ID {g['tube_inner_diameter_m']} m**, "
            f"pitch **{g['tube_pitch_m']} m**, segmental baffles cut **{g['baffle_cut_fraction']}**, "
            f"count **{g['baffle_count']}**, spacing **{g['baffle_spacing_m']} m**."
        ),
        (
            f"- Task021 placement envelope diameter **{g['placement_envelope_diameter_m']} m** "
            f"(scale **{g['placement_envelope_scale']}** of shell ID — not baffle spacing)."
        ),
        "",
        "## How this geometry was produced",
        "",
        "- Bounded recovery on frozen 0.52 m shell catalog with constrained Task021 envelope overrides.",
        "- Six local combinations (5.5/6.0 m × 0.80/0.85/0.90) only; search frozen after first mid joint pass.",
        f"- Candidate `{design_spec['candidate_id']}` / geometry_v2 `{design_spec['geometry_identity_v2'][:16]}…`.",
        "",
        "## Thermal (indicative ε-NTU)",
        "",
        f"- **CLEAN:** Q={clean['epsilon_ntu_q_w']} W, UA={clean['ua_w_per_k']} W/K, status={clean['status']}.",
        f"- **T039_DEMO fouling:** Q={foul['epsilon_ntu_q_w']} W, status={foul['status']}.",
        (
            f"- NTU={design_spec['thermal_results']['ntu_clean']}, "
            f"Cr={design_spec['thermal_results']['cr_clean']}, "
            f"ε={design_spec['thermal_results']['effectiveness_clean']} (counterflow idealization)."
        ),
        "- CoolProp water properties at stated inlets; Task037 wall/fouling authorities are experimental V08-03 packs.",
        f"- {design_spec['thermal_results']['q_margin_note']}",
        "",
        "## Hydraulics (assumption-based full path)",
        "",
        f"- Mid band: tube Δp={mid['tube_full_path_dp_pa']} Pa (margin {mid['tube_margin_pa']} Pa), "
        f"shell Δp={mid['shell_full_path_dp_pa']} Pa (margin {mid['shell_margin_pa']} Pa).",
        f"- High loss shell Δp={high['shell_full_path_dp_pa']} Pa — **BLOCKED** vs user limit.",
        "- Only **mid_band** achieves mathematical PASS; high shell loss fails primarily on shell-side budget.",
        f"- Nozzle authority: **PROVISIONAL**; `{HYDRAULIC_ENGINEERING_VALIDATION}`.",
        "",
        "## Why only mid K passes",
        "",
        "- Mid loss vector sits at tube/shell limits simultaneously; shell margin is numerically ~0 Pa.",
        "- High loss adds ~150 Pa shell excess (see high_loss shell breakdown in JSON spec).",
        "",
        "## Experimental inputs still unresolved",
        "",
        "- Standard-series nozzle bore and reinforcement not verified.",
        "- Local K vectors and Bell-Delaware calibration are prototype bridges, not licensed rule-pack output.",
        "- Fouling T039_DEMO is sensitivity-only, not plant fouling guarantee.",
        "",
        "## Gap to manufacturing release",
        "",
        "- Production Task172/173 rating, licensed compliance pack, and verified nozzle/manufacturing authority.",
        "- Independent fouling/cleaning margin and field velocity limits.",
        "- BVP production route remains **STOP** for this prototype.",
        "",
        "## Sensitivity (analysis-only)",
        "",
    ]
    lines.extend(f"- {note}" for note in sensitivity)
    lines.append("")
    lines.append(
        f"Robustness: `{hydraulic.scenario_robustness}`; "
        "scenario_robustness not met because high K fails."
    )
    return "\n".join(lines)


def run_first_joint_candidate_freeze(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
) -> FirstJointCandidateFreezeReport:
    active = provider or CoolPropProvider()
    bundle = _resolve_frozen_bundle(normalized, handoff)
    struct = bundle.structural_bundle
    v2 = geometry_identity_v2_hash(struct)
    cid = struct.candidate.candidate_id
    replay: Literal["PASS", "BLOCKED"] = (
        "PASS"
        if cid == FROZEN_FIRST_JOINT_CANDIDATE_ID and v2 == FROZEN_FIRST_JOINT_GEOMETRY_V2
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
        raise RuntimeError("first joint candidate bindings blocked")

    t037_c = evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
    t037_f = evaluate_binding_task037(bindings, fouling_scenario="T039_DEMO_FOULING")
    clean = run_thermal_prescreen(
        bindings, normalized, provider=active, task037_override=t037_c.raw
    )
    foul = run_thermal_prescreen(
        bindings, normalized, provider=active, task037_override=t037_f.raw
    )
    tube_out = (
        Decimal(clean.predicted_tube_outlet_k) if clean.predicted_tube_outlet_k else None
    )
    shell_out = (
        Decimal(clean.predicted_shell_outlet_k) if clean.predicted_shell_outlet_k else None
    )
    hydraulic = run_autonomous_nozzle_full_path(
        bindings,
        tube_nozzle_objective="MAX_MARGIN_WITHIN_VELOCITY_BAND",
        tube_outlet_temperature_k=tube_out,
        shell_outlet_temperature_k=shell_out,
        provider=active,
    )

    ntu = cr = eff = None
    if clean.ua_w_per_k:
        ntu, cr, eff = _thermal_ntu_bundle(
            provider=active, normalized=normalized, ua_w_k=clean.ua_w_per_k
        )

    spec = _build_design_spec(
        bundle=bundle,
        bindings=bindings,
        normalized=normalized,
        clean=clean,
        foul=foul,
        hydraulic=hydraulic,
        ntu=ntu,
        cr=cr,
        effectiveness=eff,
        task037_clean_authority=t037_c.result_hash or "UNAVAILABLE",
        task037_foul_authority=t037_f.result_hash or "UNAVAILABLE",
    )
    sens = _sensitivity_notes(hydraulic=hydraulic, normalized=normalized)
    review = _engineering_review_md(design_spec=spec, sensitivity=sens, hydraulic=hydraulic)

    structure_validation = validate_frozen_structure_spec(spec)
    structure_complete = structure_validation == "PASS" and replay == "PASS"

    generic_status = validate_generic_user_constraints(provider=active)
    pareto_status = validate_pareto_missing_result_handling(provider=active)
    spec["quality_gates"] = {
        "structure_spec_validation": structure_validation,
        "generic_user_constraints": generic_status,
        "pareto_missing_result_handling": pareto_status,
    }

    return FirstJointCandidateFreezeReport(
        candidate_id=cid,
        geometry_v2=v2,
        geometry_identity_replay=replay,
        structure_spec_complete=structure_complete,
        design_spec=spec,
        engineering_review_md=review,
        clean_thermal=clean,
        fouled_thermal=foul,
        hydraulic=hydraulic,
        ntu_clean=ntu,
        cr_clean=cr,
        effectiveness_clean=eff,
        sensitivity_notes=sens,
        generic_user_constraints=generic_status,
        pareto_missing_result_handling=pareto_status,
        structure_spec_validation=structure_validation,
    )


def write_freeze_artifacts(
    report: FirstJointCandidateFreezeReport,
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
    "ENGINEERING_DESIGN_STATUS",
    "FirstJointCandidateFreezeReport",
    "HYDRAULIC_ENGINEERING_VALIDATION",
    "run_first_joint_candidate_freeze",
    "write_freeze_artifacts",
]