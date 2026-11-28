"""FIXED_LAYOUT_VARIABLE_MDOT_HYDRAULIC_REPLAY_V1 — R19A postpass at scenario mass (prototype)."""

# ruff: noqa: E501

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from hexagent.canonical_json import canonical_sha256
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.live_thermal_state_hydraulic_postpass import (
    Task168CandidateBundle,
    run_live_thermal_state_hydraulic_postpass_from_ctx,
)
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    LOSS_SCENARIOS,
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import build_candidate_rating_bindings
from prototypes.v08_thermal_rating.candidate_c_identity_v08 import (
    CANDIDATE_C_SHELL_NOZZLE_ID_M,
    CANDIDATE_C_TUBE_NOZZLE_ID_M,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.engineering_shortlist_robustness_v08 import (
    _CANONICAL_SCALE,
    _SHORTLIST,
    _build_t168_with_envelope,
    _fixed_layout_tube_side_replay,
    _handoff_for_case,
    _perturb_case,
    _resolve_structural,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import run_thermal_prescreen
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import (
    build_engineering_case_v2_from_v08,
)
from prototypes.v08_thermal_rating.v08_task037_evaluate_binding_v08 import evaluate_binding_task037

AUTHORITY_ID = "FIXED_LAYOUT_VARIABLE_MDOT_HYDRAULIC_REPLAY_V1"

_MDOT_SCENARIO_KEYS: tuple[str, ...] = (
    "baseline",
    "tube_mdot_minus_1pct",
    "tube_mdot_minus_3pct",
    "tube_mdot_plus_3pct",
    "shell_mdot_minus_3pct",
    "shell_mdot_plus_3pct",
)

_TUBE_DP_LIM = Decimal("1150")
_SHELL_DP_LIM = Decimal("1180")
_TARGET_Q_W = Decimal("330000")


@dataclass(frozen=True)
class LossTierRow:
    tier: Literal["low_loss_sensitivity", "mid_band", "high_loss_sensitivity"]
    tube_full_path_dp_pa: str | None
    shell_full_path_dp_pa: str | None
    tube_margin_pa: str | None
    shell_margin_pa: str | None
    hydraulic_check: str
    full_path_feasible: bool


@dataclass(frozen=True)
class MdotScenarioReplayRow:
    shortlist_key: str
    scenario_key: str
    scenario_label: str
    geometry_v2: str
    tube_layout_hash: str
    candidate_spec_id: str
    rating_candidate_id: str | None
    tube_mass_flow_kg_s: str
    shell_mass_flow_kg_s: str
    reynolds_number: str | None
    task027_status: str
    task027_blocker: str | None
    clean_q_w: str | None
    variable_mdot_binding_pass: bool
    postpass_authority: str | None
    tube_task029_dp_pa: str | None
    shell_bell_dp_pa: str | None
    loss_tiers: tuple[LossTierRow, ...]
    port_velocities: dict[str, str]
    joint_prescreen_pass: bool
    outcome: str
    block_reason: str | None


def live_postpass_to_r27_bridge(
    live: dict[str, Any],
    *,
    normalized: NormalizedUserDesignCase,
) -> dict[str, Any]:
    """Map R19A live postpass document to Task174-hydraulic-postpass shape for R27 full-path."""
    tube_total = live.get("recalculated_tube_dp_pa")
    shell_total = live.get("recalculated_shell_dp_pa")
    friction = live.get("task027_straight_tube_friction_pressure_drop_pa")
    exp = live.get("experimental_transitional_tube_hydraulic") or {}
    if friction is None and exp.get("tube_friction_dp_pa"):
        friction = exp["tube_friction_dp_pa"]
    if tube_total is not None and friction is not None:
        str(Decimal(str(tube_total)) - Decimal(str(friction)))
    elif exp.get("tube_local_loss_dp_pa"):
        str(exp["tube_local_loss_dp_pa"])
    shell_parts = live.get("shell_dp_components_pa") or {}
    tube_lim = normalized.max_tube_side_pressure_drop_pa
    shell_lim = normalized.max_shell_side_pressure_drop_pa
    tube_margin = str(tube_lim - Decimal(str(tube_total))) if tube_total is not None else None
    shell_margin = str(shell_lim - Decimal(str(shell_total))) if shell_total is not None else None
    constraint = live.get("hydraulic_constraint_status", "BLOCKED")
    return {
        "authority_id": AUTHORITY_ID,
        "correlation_applicability_status": live.get(
            "correlation_applicability_status", "NOT_EVALUATED"
        ),
        "correlation_applicability_detail": (),
        "tube_hydraulic_recompute_status": live.get("tube_hydraulic_recompute_status", "BLOCKED"),
        "shell_hydraulic_recompute_status": live.get("shell_hydraulic_recompute_status", "NOT_RUN"),
        "tube_inlet_pressure_pa": str(normalized.tube_side.inlet_pressure_pa),
        "shell_inlet_pressure_pa": str(normalized.shell_side.inlet_pressure_pa),
        "tube_outlet_pressure_pa": live.get("tube_outlet_pressure_pa"),
        "shell_outlet_pressure_pa": live.get("shell_outlet_pressure_pa"),
        "property_inputs": live.get("property_inputs", {}),
        "coolprop_outlet_domain_checks": live.get("coolprop_outlet_domain_checks", {}),
        "experimental_transitional_tube_hydraulic": exp if exp else None,
        "task027_straight_tube_friction_pressure_drop_pa": friction,
        "recalculated_tube_dp_pa": tube_total,
        "recalculated_shell_dp_pa": shell_total,
        "shell_dp_components_pa": {
            "total": str(shell_total) if shell_total is not None else None,
            "central_crossflow": shell_parts.get("central_crossflow"),
            "window": shell_parts.get("window"),
            "inlet_end_zone": shell_parts.get("end_zone"),
            "outlet_end_zone": shell_parts.get("end_zone"),
        },
        "hydraulic_constraint_status": constraint,
        "tube_dp_margin_pa": tube_margin,
        "shell_dp_margin_pa": shell_margin,
        "upstream_hydraulic_authority_disclosure": (
            "FIXED_LAYOUT_VARIABLE_MDOT_HYDRAULIC_REPLAY_V1: Task029/166 recomputed at scenario equipment mdot."
        ),
        "task174_partial_model_disclosure": live.get("mass_flow_binding"),
    }


def _mass_binding_pass(live: dict[str, Any], normalized: NormalizedUserDesignCase) -> bool:
    binding = live.get("mass_flow_binding") or {}
    if binding.get("tube_binding_status") != "MATCHED_EQUIPMENT_TOTAL":
        return False
    if binding.get("shell_binding_status") != "MATCHED_EQUIPMENT_TOTAL":
        return False
    return (
        Decimal(binding.get("task026_input_mass_flow_kg_s", "0"))
        == normalized.tube_side.mass_flow_kg_s
        and Decimal(binding.get("task032_input_mass_flow_kg_s", "0"))
        == normalized.shell_side.mass_flow_kg_s
    )


def evaluate_mdot_scenario_v1(
    *,
    tube_count: int,
    tube_length_m: Decimal,
    scenario_key: str,
    normalized_baseline: NormalizedUserDesignCase,
    handoff_baseline: V08SolverHandoffV1,
    provider: CoolPropProvider,
) -> MdotScenarioReplayRow:
    scale = _CANONICAL_SCALE[tube_count]
    structural, outcome = _resolve_structural(
        normalized_baseline,
        handoff_baseline,
        tube_count=tube_count,
        tube_length_m=tube_length_m,
        envelope_scale=scale,
    )
    shortlist_key = f"T{tube_count}_L{tube_length_m}"
    layout = structural.bundle.task021_layout
    from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
        geometry_identity_v2_hash,
        geometry_projection_hash_v1,
    )

    g2 = geometry_identity_v2_hash(structural)
    case_norm, label = _perturb_case(normalized_baseline, scenario_key=scenario_key)
    handoff = (
        handoff_baseline if scenario_key == "baseline" else _handoff_for_case(case_norm, provider)
    )
    baseline_re = (
        str(structural.bundle.task026_result.reynolds_number)
        if structural.bundle.task026_result is not None
        else None
    )
    t168 = _build_t168_with_envelope(case_norm, handoff, scale)
    _, _, re, t027_status, t027_raw = _fixed_layout_tube_side_replay(
        structural,
        t168=t168,
        scenario_key=scenario_key,
        baseline_re=baseline_re,
    )
    bindings = build_candidate_rating_bindings(
        structural,
        space_hash=outcome.space_hash,
        t168_digest=structural.task168_request_hash_digest,
        normalized=case_norm,
        handoff=handoff,
        provider=provider,
        geometry_projection_hash=geometry_projection_hash_v1(structural),
    )
    if bindings is None:
        return MdotScenarioReplayRow(
            shortlist_key=shortlist_key,
            scenario_key=scenario_key,
            scenario_label=label,
            geometry_v2=g2,
            tube_layout_hash=layout.layout_hash,
            candidate_spec_id=structural.candidate.candidate_id,
            rating_candidate_id=None,
            tube_mass_flow_kg_s=str(case_norm.tube_side.mass_flow_kg_s),
            shell_mass_flow_kg_s=str(case_norm.shell_side.mass_flow_kg_s),
            reynolds_number=re,
            task027_status=t027_status,
            task027_blocker=t027_raw,
            clean_q_w=None,
            variable_mdot_binding_pass=False,
            postpass_authority=None,
            tube_task029_dp_pa=None,
            shell_bell_dp_pa=None,
            loss_tiers=(),
            port_velocities={},
            joint_prescreen_pass=False,
            outcome="BLOCKED",
            block_reason="BINDINGS_BLOCKED",
        )
    if t027_status != "PASS":
        return MdotScenarioReplayRow(
            shortlist_key=shortlist_key,
            scenario_key=scenario_key,
            scenario_label=label,
            geometry_v2=g2,
            tube_layout_hash=layout.layout_hash,
            candidate_spec_id=structural.candidate.candidate_id,
            rating_candidate_id=bindings.rating_request.candidate_id,
            tube_mass_flow_kg_s=str(case_norm.tube_side.mass_flow_kg_s),
            shell_mass_flow_kg_s=str(case_norm.shell_side.mass_flow_kg_s),
            reynolds_number=re,
            task027_status=t027_status,
            task027_blocker=t027_raw,
            clean_q_w=None,
            variable_mdot_binding_pass=False,
            postpass_authority=None,
            tube_task029_dp_pa=None,
            shell_bell_dp_pa=None,
            loss_tiers=(),
            port_velocities={},
            joint_prescreen_pass=False,
            outcome="PHYSICAL_MODEL_BLOCKED",
            block_reason=t027_raw,
        )
    t037 = evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
    prescreen = run_thermal_prescreen(
        bindings, case_norm, provider=provider, task037_override=t037.raw
    )
    q = prescreen.epsilon_ntu_q_w
    eng_case = build_engineering_case_v2_from_v08(case_norm)
    postpass_ctx = Task168CandidateBundle(
        candidate_id=bindings.rating_request.candidate_id,
        candidate_hash=bindings.geometry_projection_hash,
        t168_request=t168,
        bundle=structural.bundle,
        authority=t168.evaluation_input_authority,
        configuration=structural.bundle.task020_configuration,
        layout=structural.bundle.task021_layout,
    )
    live = run_live_thermal_state_hydraulic_postpass_from_ctx(
        eng_case,
        postpass_ctx,
        tube_inlet_temperature_k=case_norm.tube_side.inlet_temperature_k,
        tube_outlet_temperature_k=Decimal(
            str(prescreen.predicted_tube_outlet_k or case_norm.tube_side.inlet_temperature_k)
        ),
        shell_inlet_temperature_k=case_norm.shell_side.inlet_temperature_k,
        shell_outlet_temperature_k=Decimal(
            str(prescreen.predicted_shell_outlet_k or case_norm.shell_side.inlet_temperature_k)
        ),
        tube_inlet_pressure_pa=case_norm.tube_side.inlet_pressure_pa,
        shell_inlet_pressure_pa=case_norm.shell_side.inlet_pressure_pa,
        provider=provider,
    )
    mdot_pass = _mass_binding_pass(live, case_norm)
    bridge = live_postpass_to_r27_bridge(live, normalized=case_norm)
    loss_tiers: list[LossTierRow] = []
    port_vel: dict[str, str] = {}
    joint_pass = False
    outcome = "BLOCKED"
    block_reason: str | None = None
    if live.get("tube_hydraulic_recompute_status") == "BLOCKED" or live.get("blockers"):
        block_reason = str(live.get("blockers") or live.get("tube_hydraulic_recompute_status"))
        outcome = "POSTPASS_BLOCKED"
    else:
        try:
            fp = run_autonomous_nozzle_full_path(
                bindings,
                fixed_tube_inside_diameter_m=CANDIDATE_C_TUBE_NOZZLE_ID_M,
                fixed_shell_inside_diameter_m=CANDIDATE_C_SHELL_NOZZLE_ID_M,
                tube_outlet_temperature_k=Decimal(str(prescreen.predicted_tube_outlet_k))
                if prescreen.predicted_tube_outlet_k
                else None,
                shell_outlet_temperature_k=Decimal(str(prescreen.predicted_shell_outlet_k))
                if prescreen.predicted_shell_outlet_k
                else None,
                provider=provider,
                hydraulic_postpass_override=bridge,
            )
            for tier in LOSS_SCENARIOS:
                sc = next(s for s in fp.scenarios if s.scenario_key == tier)
                loss_tiers.append(
                    LossTierRow(
                        tier=tier,
                        tube_full_path_dp_pa=sc.tube_full_path_dp_pa,
                        shell_full_path_dp_pa=sc.shell_full_path_dp_pa,
                        tube_margin_pa=sc.tube_margin_pa,
                        shell_margin_pa=sc.shell_margin_pa,
                        hydraulic_check=sc.hydraulic_check,
                        full_path_feasible=sc.full_path_feasible,
                    )
                )
            for p in fp.ports:
                port_vel[p.port_id] = str(p.velocity_m_s)
            high = next(s for s in fp.scenarios if s.scenario_key == "high_loss_sensitivity")
            joint_pass = (
                high.tube_full_path_dp_pa is not None
                and high.shell_full_path_dp_pa is not None
                and fp.nozzle_velocity_check == "PASS"
            )
            outcome = "COMPUTED" if joint_pass else "MARGIN_FAIL"
            if not joint_pass:
                block_reason = f"nozzle_check={fp.nozzle_velocity_check}"
        except (ValueError, ValidationError) as exc:
            block_reason = type(exc).__name__
            outcome = "FULL_PATH_BLOCKED"
    return MdotScenarioReplayRow(
        shortlist_key=shortlist_key,
        scenario_key=scenario_key,
        scenario_label=label,
        geometry_v2=g2,
        tube_layout_hash=layout.layout_hash,
        candidate_spec_id=structural.candidate.candidate_id,
        rating_candidate_id=bindings.rating_request.candidate_id,
        tube_mass_flow_kg_s=str(case_norm.tube_side.mass_flow_kg_s),
        shell_mass_flow_kg_s=str(case_norm.shell_side.mass_flow_kg_s),
        reynolds_number=re or live.get("tube_reynolds_number"),
        task027_status=t027_status,
        task027_blocker=t027_raw,
        clean_q_w=q,
        variable_mdot_binding_pass=mdot_pass,
        postpass_authority=live.get("authority_id"),
        tube_task029_dp_pa=live.get("recalculated_tube_dp_pa"),
        shell_bell_dp_pa=live.get("recalculated_shell_dp_pa"),
        loss_tiers=tuple(loss_tiers),
        port_velocities=port_vel,
        joint_prescreen_pass=joint_pass,
        outcome=outcome,
        block_reason=block_reason,
    )


def run_replay_matrix_v1(
    provider: CoolPropProvider | None = None,
    *,
    case_json_text: str | None = None,
    fixture_path: Path | None = None,
) -> dict[str, Any]:
    provider = provider or CoolPropProvider()
    if case_json_text is None:
        path = fixture_path or FIXTURE_330
        case_json_text = path.read_text(encoding="utf-8")
    case = load_general_user_design_case_json(case_json_text)
    pipeline = validate_and_build_solver_handoff(case, provider=provider)
    normalized = pipeline.normalized
    handoff = pipeline.handoff
    rows: list[MdotScenarioReplayRow] = []
    for tube_count, tube_length_m in _SHORTLIST:
        for scenario_key in _MDOT_SCENARIO_KEYS:
            rows.append(
                evaluate_mdot_scenario_v1(
                    tube_count=tube_count,
                    tube_length_m=tube_length_m,
                    scenario_key=scenario_key,
                    normalized_baseline=normalized,
                    handoff_baseline=handoff,
                    provider=provider,
                )
            )
    computed = [r for r in rows if r.outcome == "COMPUTED"]
    blocked = [r for r in rows if r.outcome != "COMPUTED"]
    nonbaseline = [r for r in rows if r.scenario_key != "baseline"]
    nb_computed = [r for r in nonbaseline if r.outcome == "COMPUTED"]
    layout_hashes = {r.shortlist_key: r.tube_layout_hash for r in rows}
    binding_pass = all(r.variable_mdot_binding_pass for r in rows if r.task027_status == "PASS")
    identity_ok = len(set(layout_hashes[k] for k in layout_hashes)) == 4
    return {
        "schema": "hxforge.fixed-layout-variable-mdot-hydraulic-replay.v1",
        "authority_id": AUTHORITY_ID,
        "fixture": str(fixture_path or FIXTURE_330),
        "target_duty_w": str(normalized.target_duty_w),
        "max_tube_side_pressure_drop_pa": str(normalized.max_tube_side_pressure_drop_pa),
        "max_shell_side_pressure_drop_pa": str(normalized.max_shell_side_pressure_drop_pa),
        "engineering_case_id": normalized.engineering_case_id,
        "scenario_count": len(rows),
        "nonbaseline_count": len(nonbaseline),
        "full_path_computed_count": len(computed),
        "nonbaseline_computed_count": len(nb_computed),
        "physical_model_blocked_count": len(
            [r for r in rows if r.outcome == "PHYSICAL_MODEL_BLOCKED"]
        ),
        "variable_mdot_binding_all_pass": binding_pass,
        "fixed_geometry_identity_pass": identity_ok,
        "joint_prescreen_pass_count": len([r for r in rows if r.joint_prescreen_pass]),
        "rows": [asdict(r) for r in rows],
        "blocked_summary": [
            {"layout": r.shortlist_key, "scenario": r.scenario_key, "reason": r.block_reason}
            for r in blocked
        ],
        "result_hash": canonical_sha256({"rows": [asdict(r) for r in rows]}),
    }


def write_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    out = Path("/opt/cursor/artifacts/fixed_layout_variable_mdot_hydraulic_replay_v1.json")
    payload = run_replay_matrix_v1()
    write_artifact(out, payload)
    print(json.dumps({k: payload[k] for k in payload if k != "rows"}, indent=2))
