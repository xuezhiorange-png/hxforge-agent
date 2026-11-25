"""V08_AUTONOMOUS_DESIGN_USER_INPUT_DELIVERY — user-in → dynamic geometry → design out (experimental)."""

# ruff: noqa: E501

from __future__ import annotations

import json
import textwrap
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Literal

from pydantic import ValidationError

from hexagent.canonical_json import canonical_sha256
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.live_thermal_state_hydraulic_postpass import (
    Task168CandidateBundle,
    run_live_thermal_state_hydraulic_postpass_from_ctx,
)
from prototypes.v08_general_user_case.errors import V08UserCaseValidationError
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.discrete_space import (
    DEFAULT_V08_DISCRETE_SPACE_PATH,
    load_v08_discrete_space,
)
from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
    geometry_identity_v2_hash,
    geometry_projection_hash_v1,
)
from prototypes.v08_geometry_candidate_generation.structural_bundles import (
    V08StructuralGeometryBundle,
)
from prototypes.v08_geometry_candidate_generation.task168_builder import (
    build_v08_task168_request,
    filter_discrete_space_by_envelope,
)
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    LOSS_SCENARIOS,
    AutonomousNozzleFullPathReport,
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    enumerate_structural_bundles,
    build_candidate_rating_bindings,
)
from prototypes.v08_thermal_rating.candidate_c_identity_v08 import (
    CANDIDATE_C_SHELL_NOZZLE_ID_M,
    CANDIDATE_C_TUBE_NOZZLE_ID_M,
)
from prototypes.v08_thermal_rating.engineering_shortlist_robustness_v08 import (
    _CANONICAL_SCALE,
    _SHORTLIST,
    _handoff_for_case,
    _perturb_case,
    _resolve_structural,
)
from prototypes.v08_thermal_rating.fixed_layout_variable_mdot_hydraulic_replay_v1 import (
    LossTierRow,
    MdotScenarioReplayRow,
    live_postpass_to_r27_bridge,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import run_thermal_prescreen
from prototypes.v08_thermal_rating.v08_autonomous_engineering_selection_mvp import (
    ENGINEERING_DESIGN_STATUS,
    ScenarioJointVerdict,
    verdict_from_row,
)
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import build_engineering_case_v2_from_v08
from prototypes.v08_thermal_rating.v08_task037_evaluate_binding_v08 import evaluate_binding_task037

TASK_ID = "V08_AUTONOMOUS_DESIGN_USER_INPUT_DELIVERY"
NOZZLE_VELOCITY_MIN_M_S = Decimal("1")
NOZZLE_VELOCITY_MAX_M_S = Decimal("3")
_MDOT_KEYS: tuple[str, ...] = (
    "baseline",
    "tube_mdot_minus_1pct",
    "tube_mdot_minus_3pct",
    "tube_mdot_plus_3pct",
    "shell_mdot_minus_3pct",
    "shell_mdot_plus_3pct",
)


@dataclass(frozen=True)
class UserInputIngestionResult:
    ok: bool
    engineering_case_id: str | None
    blockers: tuple[dict[str, str], ...]
    normalized: NormalizedUserDesignCase | None
    handoff: V08SolverHandoffV1 | None


@dataclass(frozen=True)
class StructuralEntry:
    bundle: V08StructuralGeometryBundle
    space_hash: str
    t168_digest: str
    geom_hash: str


@dataclass(frozen=True)
class CandidateBaselineRecord:
    candidate_id: str
    layout_key: str
    geometry_identity_v2: str
    tube_layout_hash: str
    thermal_q_w: str | None
    thermal_pass: bool
    task027_pass: bool
    hydraulic_all_tiers_pass: bool
    nozzle_velocity_pass: bool
    engineering_joint_pass: bool
    block_reasons: tuple[str, ...]


@dataclass(frozen=True)
class AutonomousDesignToolReport:
    task_id: str
    engineering_design_status: str
    production_rating_validated: bool
    ingestion: UserInputIngestionResult
    structural_candidates_generated: int
    structural_candidates_evaluated: int
    candidate_records: tuple[CandidateBaselineRecord, ...]
    rankings: dict[str, str | None]
    recommended_candidate_id: str | None
    recommended_layout_key: str | None
    no_feasible_candidate: bool
    design_specification: dict[str, Any] | None
    mdot_verdicts: tuple[ScenarioJointVerdict, ...]
    applicability_notes: tuple[str, ...]
    result_hash: str


def ingest_user_design_input(
    case_json_text: str,
    *,
    provider: CoolPropProvider | None = None,
) -> UserInputIngestionResult:
    """Validate user JSON through V08 case model, unit resolution, and physical feasibility."""
    provider = provider or CoolPropProvider()
    try:
        case = load_general_user_design_case_json(case_json_text)
    except (ValidationError, ValueError) as exc:
        return UserInputIngestionResult(
            ok=False,
            engineering_case_id=None,
            blockers=(_blocker("INPUT_SCHEMA_OR_UNIT", str(exc)),),
            normalized=None,
            handoff=None,
        )
    try:
        pipeline = validate_and_build_solver_handoff(case, provider=provider)
    except V08UserCaseValidationError as exc:
        blockers = tuple(
            _blocker(issue.code.value, f"{issue.field}: {issue.message}") for issue in exc.issues
        )
        return UserInputIngestionResult(
            ok=False,
            engineering_case_id=case.engineering_case_id,
            blockers=blockers,
            normalized=None,
            handoff=None,
        )
    notes = (
        "Single-phase PURE_ORDINARY_WATER only; two-phase and exotic fluids return INPUT blockers.",
        "Nozzle velocity band 1–3 m/s (R27 autonomous nozzle rule); not user-overridable in this prototype.",
        "Thermal results are ε-NTU experimental prescreen — not production Task173 rating.",
    )
    _ = notes
    return UserInputIngestionResult(
        ok=True,
        engineering_case_id=pipeline.normalized.engineering_case_id,
        blockers=(),
        normalized=pipeline.normalized,
        handoff=pipeline.handoff,
    )


def _blocker(code: str, detail: str) -> dict[str, str]:
    return {"code": code, "detail": detail}


def _collect_structural_entries(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    max_candidates: int,
) -> list[StructuralEntry]:
    """Standard discrete-space enumeration plus frozen approved shortlist layouts (no new search)."""
    try:
        space_hash, t168_digest, bundles, geom = enumerate_structural_bundles(
            normalized, handoff, max_valid=max_candidates
        )
    except ValueError as exc:
        if "empty after envelope filtering" in str(exc):
            bundles = ()
            space_hash, t168_digest, geom = "", "", {}
        else:
            raise
    seen: set[str] = set()
    entries: list[StructuralEntry] = []
    for structural in bundles:
        g2 = geometry_identity_v2_hash(structural)
        if g2 in seen:
            continue
        seen.add(g2)
        entries.append(
            StructuralEntry(
                bundle=structural,
                space_hash=space_hash,
                t168_digest=t168_digest,
                geom_hash=geom.get(structural.candidate.candidate_id, "")
                or geometry_projection_hash_v1(structural),
            )
        )
    for tube_count, tube_length_m in _SHORTLIST:
        scale = _CANONICAL_SCALE[tube_count]
        try:
            structural, outcome = _resolve_structural(
                normalized,
                handoff,
                tube_count=tube_count,
                tube_length_m=tube_length_m,
                envelope_scale=scale,
            )
        except (ValueError, RuntimeError):
            continue
        g2 = geometry_identity_v2_hash(structural)
        if g2 in seen:
            continue
        seen.add(g2)
        entries.append(
            StructuralEntry(
                bundle=structural,
                space_hash=outcome.space_hash,
                t168_digest=structural.task168_request_hash_digest,
                geom_hash=geometry_projection_hash_v1(structural),
            )
        )
    return entries


def _layout_key(structural: V08StructuralGeometryBundle) -> str:
    layout = structural.bundle.task021_layout
    return f"T{int(layout.physical_tube_count)}_L{structural.candidate.tube_length_m}"


def _t168_handoff(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
):
    space = load_v08_discrete_space(DEFAULT_V08_DISCRETE_SPACE_PATH)
    filtered, _ = filter_discrete_space_by_envelope(space, normalized.design_envelope)
    return build_v08_task168_request(normalized, handoff, filtered)


def _evaluate_baseline_candidate(
    structural: V08StructuralGeometryBundle,
    *,
    space_hash: str,
    t168_digest: str,
    geom_hash: str,
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    provider: CoolPropProvider,
) -> tuple[CandidateBaselineRecord, dict[str, Any] | None, AutonomousNozzleFullPathReport | None]:
    layout = structural.bundle.task021_layout
    g2 = geometry_identity_v2_hash(structural)
    layout_hash = str(layout.layout_hash)
    bindings = build_candidate_rating_bindings(
        structural,
        space_hash=space_hash,
        t168_digest=t168_digest,
        normalized=normalized,
        handoff=handoff,
        provider=provider,
        geometry_projection_hash=geom_hash or geometry_projection_hash_v1(structural),
    )
    if bindings is None:
        rec = CandidateBaselineRecord(
            candidate_id=structural.candidate.candidate_id,
            layout_key=_layout_key(structural),
            geometry_identity_v2=g2,
            tube_layout_hash=layout_hash,
            thermal_q_w=None,
            thermal_pass=False,
            task027_pass=False,
            hydraulic_all_tiers_pass=False,
            nozzle_velocity_pass=False,
            engineering_joint_pass=False,
            block_reasons=("TASK174_BINDINGS_BLOCKED",),
        )
        return rec, None, None
    t037 = evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
    prescreen = run_thermal_prescreen(bindings, normalized, provider=provider, task037_override=t037.raw)
    t168 = _t168_handoff(normalized, handoff)
    eng_case = build_engineering_case_v2_from_v08(normalized)
    ctx = Task168CandidateBundle(
        candidate_id=bindings.rating_request.candidate_id,
        candidate_hash=bindings.geometry_projection_hash,
        t168_request=t168,
        bundle=structural.bundle,
        authority=t168.evaluation_input_authority,
        configuration=structural.bundle.task020_configuration,
        layout=layout,
    )
    live = run_live_thermal_state_hydraulic_postpass_from_ctx(
        eng_case,
        ctx,
        tube_inlet_temperature_k=normalized.tube_side.inlet_temperature_k,
        tube_outlet_temperature_k=Decimal(
            str(prescreen.predicted_tube_outlet_k or normalized.tube_side.inlet_temperature_k)
        ),
        shell_inlet_temperature_k=normalized.shell_side.inlet_temperature_k,
        shell_outlet_temperature_k=Decimal(
            str(prescreen.predicted_shell_outlet_k or normalized.shell_side.inlet_temperature_k)
        ),
        tube_inlet_pressure_pa=normalized.tube_side.inlet_pressure_pa,
        shell_inlet_pressure_pa=normalized.shell_side.inlet_pressure_pa,
        provider=provider,
    )
    task027_pass = live.get("tube_hydraulic_recompute_status") in {
        "SUCCESS",
        "EXPERIMENTAL_TRANSITIONAL_SUCCESS",
    } and not any(
        "BL_T027" in str(b.get("code", "")) for b in live.get("blockers") or []
    )
    bridge = live_postpass_to_r27_bridge(live, normalized=normalized)
    loss_tiers: list[LossTierRow] = []
    port_vel: dict[str, str] = {}
    hydraulic: AutonomousNozzleFullPathReport | None = None
    if task027_pass and not live.get("blockers"):
        try:
            hydraulic = run_autonomous_nozzle_full_path(
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
                sc = next(s for s in hydraulic.scenarios if s.scenario_key == tier)
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
            for p in hydraulic.ports:
                port_vel[p.port_id] = str(p.velocity_m_s)
        except (ValueError, ValidationError):
            pass
    mdot_row = MdotScenarioReplayRow(
        shortlist_key=_layout_key(structural),
        scenario_key="baseline",
        scenario_label="nominal equipment mass",
        geometry_v2=g2,
        tube_layout_hash=layout_hash,
        candidate_spec_id=structural.candidate.candidate_id,
        rating_candidate_id=bindings.rating_request.candidate_id,
        tube_mass_flow_kg_s=str(normalized.tube_side.mass_flow_kg_s),
        shell_mass_flow_kg_s=str(normalized.shell_side.mass_flow_kg_s),
        reynolds_number=live.get("tube_reynolds_number"),
        task027_status="PASS" if task027_pass else "BLOCKED",
        task027_blocker=None if task027_pass else "TASK027_OR_POSTPASS_BLOCKED",
        clean_q_w=prescreen.epsilon_ntu_q_w,
        variable_mdot_binding_pass=True,
        postpass_authority=live.get("authority_id"),
        tube_task029_dp_pa=live.get("recalculated_tube_dp_pa"),
        shell_bell_dp_pa=live.get("recalculated_shell_dp_pa"),
        loss_tiers=tuple(loss_tiers),
        port_velocities=port_vel,
        joint_prescreen_pass=False,
        outcome="COMPUTED",
        block_reason=None,
    )
    verdict = verdict_from_row(
        mdot_row,
        target_q=normalized.target_duty_w,
        layout_geometry_v2=g2,
        layout_hash=layout_hash,
    )
    spec = _design_spec_from_parts(
        structural, bindings, prescreen, live, hydraulic, verdict, normalized
    )
    rec = CandidateBaselineRecord(
        candidate_id=bindings.rating_request.candidate_id,
        layout_key=_layout_key(structural),
        geometry_identity_v2=g2,
        tube_layout_hash=layout_hash,
        thermal_q_w=prescreen.epsilon_ntu_q_w,
        thermal_pass=verdict.thermal_pass,
        task027_pass=verdict.task027_pass,
        hydraulic_all_tiers_pass=verdict.hydraulic_all_tiers_pass,
        nozzle_velocity_pass=verdict.nozzle_velocity_pass,
        engineering_joint_pass=verdict.engineering_joint_pass,
        block_reasons=verdict.joint_block_reasons,
    )
    return rec, spec, hydraulic


def _design_spec_from_parts(
    structural: V08StructuralGeometryBundle,
    bindings: Any,
    prescreen: Any,
    live: dict[str, Any],
    hydraulic: AutonomousNozzleFullPathReport | None,
    verdict: ScenarioJointVerdict,
    normalized: NormalizedUserDesignCase,
) -> dict[str, Any]:
    cand = structural.candidate
    shell = structural.shell_record
    layout = structural.bundle.task021_layout
    tube_id = cand.tube_outer_diameter_m - Decimal("2") * cand.tube_wall_thickness_m
    mid = high = None
    ports: list[dict[str, str]] = []
    if hydraulic is not None:
        mid = next(s for s in hydraulic.scenarios if s.scenario_key == "mid_band")
        high = next(s for s in hydraulic.scenarios if s.scenario_key == "high_loss_sensitivity")
        ports = [
            {"port_id": p.port_id, "inside_diameter_m": str(p.inside_diameter_m), "velocity_m_s": str(p.velocity_m_s)}
            for p in hydraulic.ports
        ]
    return {
        "schema": "hxforge.autonomous-design-specification.v1",
        "engineering_design_status": ENGINEERING_DESIGN_STATUS,
        "engineering_joint_pass_baseline": verdict.engineering_joint_pass,
        "block_reasons": list(verdict.joint_block_reasons),
        "geometry": {
            "shell_inside_diameter_m": str(shell.shell_inside_diameter_m),
            "tube_outer_diameter_m": str(cand.tube_outer_diameter_m),
            "tube_inner_diameter_m": str(tube_id),
            "tube_wall_thickness_m": str(cand.tube_wall_thickness_m),
            "tube_pitch_m": str(cand.tube_pitch_m),
            "tube_layout_pattern": cand.tube_layout,
            "physical_tube_count": int(layout.physical_tube_count),
            "tube_length_m": str(cand.tube_length_m),
            "tube_pass_count": cand.tube_pass_count,
            "baffle_type": cand.baffle_type,
            "baffle_cut_fraction": str(cand.baffle_cut_fraction),
            "baffle_count": cand.baffle_count,
            "baffle_spacing_m": str(cand.baffle_spacing_m),
        },
        "nozzles_four_port": ports,
        "thermal_experimental_prescreen": {
            "clean_q_w": prescreen.epsilon_ntu_q_w,
            "target_duty_w": str(normalized.target_duty_w),
            "tube_htc_w_m2_k": prescreen.tube_htc_w_m2_k,
            "shell_htc_w_m2_k": prescreen.shell_htc_w_m2_k,
            "overall_ua_w_per_k": prescreen.ua_w_per_k,
            "heat_transfer_area_basis_m2": prescreen.area_basis_m2,
            "tube_inlet_k": str(normalized.tube_side.inlet_temperature_k),
            "tube_outlet_k": prescreen.predicted_tube_outlet_k,
            "shell_inlet_k": str(normalized.shell_side.inlet_temperature_k),
            "shell_outlet_k": prescreen.predicted_shell_outlet_k,
        },
        "hydraulic_baseline": {
            "tube_task029_dp_pa": live.get("recalculated_tube_dp_pa"),
            "shell_bell_dp_pa": live.get("recalculated_shell_dp_pa"),
            "mid_full_path_tube_dp_pa": mid.tube_full_path_dp_pa if mid else None,
            "mid_full_path_shell_dp_pa": mid.shell_full_path_dp_pa if mid else None,
            "high_full_path_tube_dp_pa": high.tube_full_path_dp_pa if high else None,
            "high_full_path_shell_dp_pa": high.shell_full_path_dp_pa if high else None,
            "tube_margin_high_pa": high.tube_margin_pa if high else None,
            "shell_margin_high_pa": high.shell_margin_pa if high else None,
            "limits_pa": {
                "tube": str(normalized.max_tube_side_pressure_drop_pa),
                "shell": str(normalized.max_shell_side_pressure_drop_pa),
            },
        },
        "candidate_ids": {
            "catalog_candidate_id": cand.candidate_id,
            "rating_candidate_id": bindings.rating_request.candidate_id,
            "geometry_identity_v2": geometry_identity_v2_hash(structural),
        },
    }


def evaluate_mdot_for_structural(
    structural: V08StructuralGeometryBundle,
    *,
    space_hash: str,
    t168_digest: str,
    geom_hash: str,
    normalized_baseline: NormalizedUserDesignCase,
    handoff_baseline: V08SolverHandoffV1,
    scenario_key: str,
    provider: CoolPropProvider,
) -> MdotScenarioReplayRow:
    layout = structural.bundle.task021_layout
    g2 = geometry_identity_v2_hash(structural)
    case_norm, label = _perturb_case(normalized_baseline, scenario_key=scenario_key)
    handoff = handoff_baseline if scenario_key == "baseline" else _handoff_for_case(case_norm, provider)
    bindings = build_candidate_rating_bindings(
        structural,
        space_hash=space_hash,
        t168_digest=t168_digest,
        normalized=case_norm,
        handoff=handoff,
        provider=provider,
        geometry_projection_hash=geom_hash or geometry_projection_hash_v1(structural),
    )
    shortlist_key = _layout_key(structural)
    if bindings is None:
        return MdotScenarioReplayRow(
            shortlist_key=shortlist_key,
            scenario_key=scenario_key,
            scenario_label=label,
            geometry_v2=g2,
            tube_layout_hash=str(layout.layout_hash),
            candidate_spec_id=structural.candidate.candidate_id,
            rating_candidate_id=None,
            tube_mass_flow_kg_s=str(case_norm.tube_side.mass_flow_kg_s),
            shell_mass_flow_kg_s=str(case_norm.shell_side.mass_flow_kg_s),
            reynolds_number=None,
            task027_status="BLOCKED",
            task027_blocker="BINDINGS_BLOCKED",
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
    t037 = evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
    prescreen = run_thermal_prescreen(bindings, case_norm, provider=provider, task037_override=t037.raw)
    t168 = _t168_handoff(case_norm, handoff)
    eng_case = build_engineering_case_v2_from_v08(case_norm)
    ctx = Task168CandidateBundle(
        candidate_id=bindings.rating_request.candidate_id,
        candidate_hash=bindings.geometry_projection_hash,
        t168_request=t168,
        bundle=structural.bundle,
        authority=t168.evaluation_input_authority,
        configuration=structural.bundle.task020_configuration,
        layout=layout,
    )
    live = run_live_thermal_state_hydraulic_postpass_from_ctx(
        eng_case,
        ctx,
        tube_inlet_temperature_k=case_norm.tube_side.inlet_temperature_k,
        tube_outlet_temperature_k=Decimal(str(prescreen.predicted_tube_outlet_k or case_norm.tube_side.inlet_temperature_k)),
        shell_inlet_temperature_k=case_norm.shell_side.inlet_temperature_k,
        shell_outlet_temperature_k=Decimal(str(prescreen.predicted_shell_outlet_k or case_norm.shell_side.inlet_temperature_k)),
        tube_inlet_pressure_pa=case_norm.tube_side.inlet_pressure_pa,
        shell_inlet_pressure_pa=case_norm.shell_side.inlet_pressure_pa,
        provider=provider,
    )
    from prototypes.v08_thermal_rating.fixed_layout_variable_mdot_hydraulic_replay_v1 import (
        _mass_binding_pass,
    )

    mdot_pass = _mass_binding_pass(live, case_norm)
    task027_pass = live.get("tube_hydraulic_recompute_status") in {
        "SUCCESS",
        "EXPERIMENTAL_TRANSITIONAL_SUCCESS",
    } and not any("BL_T027" in str(b.get("code", "")) for b in live.get("blockers") or [])
    bridge = live_postpass_to_r27_bridge(live, normalized=case_norm)
    loss_tiers: list[LossTierRow] = []
    port_vel: dict[str, str] = {}
    outcome = "BLOCKED"
    block_reason: str | None = None
    if not task027_pass:
        outcome = "PHYSICAL_MODEL_BLOCKED"
        block_reason = "TASK027_OR_POSTPASS_BLOCKED"
    elif live.get("blockers"):
        outcome = "POSTPASS_BLOCKED"
        block_reason = str(live.get("blockers"))
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
            outcome = "COMPUTED"
        except (ValueError, ValidationError) as exc:
            outcome = "FULL_PATH_BLOCKED"
            block_reason = type(exc).__name__
    return MdotScenarioReplayRow(
        shortlist_key=shortlist_key,
        scenario_key=scenario_key,
        scenario_label=label,
        geometry_v2=g2,
        tube_layout_hash=str(layout.layout_hash),
        candidate_spec_id=structural.candidate.candidate_id,
        rating_candidate_id=bindings.rating_request.candidate_id,
        tube_mass_flow_kg_s=str(case_norm.tube_side.mass_flow_kg_s),
        shell_mass_flow_kg_s=str(case_norm.shell_side.mass_flow_kg_s),
        reynolds_number=live.get("tube_reynolds_number"),
        task027_status="PASS" if task027_pass else "BLOCKED",
        task027_blocker=None if task027_pass else block_reason,
        clean_q_w=prescreen.epsilon_ntu_q_w,
        variable_mdot_binding_pass=mdot_pass,
        postpass_authority=live.get("authority_id"),
        tube_task029_dp_pa=live.get("recalculated_tube_dp_pa"),
        shell_bell_dp_pa=live.get("recalculated_shell_dp_pa"),
        loss_tiers=tuple(loss_tiers),
        port_velocities=port_vel,
        joint_prescreen_pass=False,
        outcome=outcome,
        block_reason=block_reason,
    )


def _rank_dynamic_candidates(
    records: tuple[CandidateBaselineRecord, ...],
) -> dict[str, str | None]:
    joint = [r for r in records if r.engineering_joint_pass]
    thermal = [r for r in records if r.thermal_pass]
    hyd = [r for r in records if r.hydraulic_all_tiers_pass and r.task027_pass]
    nominal = max(joint, key=lambda r: Decimal(r.thermal_q_w or "0")).layout_key if joint else None
    thermal_best = (
        max(thermal, key=lambda r: Decimal(r.thermal_q_w or "-999")).layout_key if thermal else None
    )
    hyd_best = hyd[0].layout_key if len(hyd) == 1 else (hyd[0].layout_key if hyd else None)
    if len(hyd) > 1:
        # pick max min-margin using baseline record only — approximate by thermal Q proxy when hyd pass tie
        hyd_best = max(hyd, key=lambda r: Decimal(r.thermal_q_w or "0")).layout_key
    return {
        "nominal_joint_best_layout": nominal,
        "thermal_margin_best_layout": thermal_best,
        "hydraulic_margin_best_layout": hyd_best,
        "robust_exploration_layout": None,
    }


def run_autonomous_design_tool(
    case_json_text: str,
    *,
    provider: CoolPropProvider | None = None,
    max_candidates: int = 48,
    run_mdot_on_recommendation: bool = True,
) -> AutonomousDesignToolReport:
    """Full prototype: validated user input → enumerate → prescreen/hydraulic → rank → design JSON."""
    provider = provider or CoolPropProvider()
    ingestion = ingest_user_design_input(case_json_text, provider=provider)
    applicability = (
        "Approved V08 discrete geometry/material space only; search clipped by user design_envelope.",
        "Does not expand frozen 330 kW placement-envelope recovery ladders.",
        ENGINEERING_DESIGN_STATUS,
    )
    if not ingestion.ok or ingestion.normalized is None or ingestion.handoff is None:
        return AutonomousDesignToolReport(
            task_id=TASK_ID,
            engineering_design_status=ENGINEERING_DESIGN_STATUS,
            production_rating_validated=False,
            ingestion=ingestion,
            structural_candidates_generated=0,
            structural_candidates_evaluated=0,
            candidate_records=(),
            rankings={},
            recommended_candidate_id=None,
            recommended_layout_key=None,
            no_feasible_candidate=True,
            design_specification=None,
            mdot_verdicts=(),
            applicability_notes=applicability,
            result_hash=canonical_sha256({"blocked": [ingestion.blockers]}),
        )
    normalized = ingestion.normalized
    handoff = ingestion.handoff
    entries = _collect_structural_entries(normalized, handoff, max_candidates=max_candidates)
    records: list[CandidateBaselineRecord] = []
    specs: dict[str, dict[str, Any]] = {}
    entry_by_layout: dict[str, StructuralEntry] = {}
    for entry in entries:
        structural = entry.bundle
        rec, spec, _ = _evaluate_baseline_candidate(
            structural,
            space_hash=entry.space_hash,
            t168_digest=entry.t168_digest,
            geom_hash=entry.geom_hash,
            normalized=normalized,
            handoff=handoff,
            provider=provider,
        )
        entry_by_layout[rec.layout_key] = entry
        records.append(rec)
        if spec is not None:
            specs[rec.candidate_id] = spec
    rankings = _rank_dynamic_candidates(tuple(records))
    joint_ok = [r for r in records if r.engineering_joint_pass]
    recommended: CandidateBaselineRecord | None = None
    if joint_ok:
        recommended = max(joint_ok, key=lambda r: Decimal(r.thermal_q_w or "0"))
    no_feasible = recommended is None
    design_spec = specs.get(recommended.candidate_id) if recommended else None
    mdot_verdicts: list[ScenarioJointVerdict] = []
    if recommended and run_mdot_on_recommendation:
        entry = entry_by_layout[recommended.layout_key]
        structural = entry.bundle
        g2 = recommended.geometry_identity_v2
        lh = recommended.tube_layout_hash
        for sk in _MDOT_KEYS:
            row = evaluate_mdot_for_structural(
                structural,
                space_hash=entry.space_hash,
                t168_digest=entry.t168_digest,
                geom_hash=entry.geom_hash,
                normalized_baseline=normalized,
                handoff_baseline=handoff,
                scenario_key=sk,
                provider=provider,
            )
            mdot_verdicts.append(
                verdict_from_row(row, target_q=normalized.target_duty_w, layout_geometry_v2=g2, layout_hash=lh)
            )
        if all(v.engineering_joint_pass for v in mdot_verdicts):
            rankings["robust_exploration_layout"] = recommended.layout_key
    return AutonomousDesignToolReport(
        task_id=TASK_ID,
        engineering_design_status=ENGINEERING_DESIGN_STATUS,
        production_rating_validated=False,
        ingestion=ingestion,
        structural_candidates_generated=len(entries),
        structural_candidates_evaluated=len(records),
        candidate_records=tuple(records),
        rankings=rankings,
        recommended_candidate_id=recommended.candidate_id if recommended else None,
        recommended_layout_key=recommended.layout_key if recommended else None,
        no_feasible_candidate=no_feasible,
        design_specification=design_spec,
        mdot_verdicts=tuple(mdot_verdicts),
        applicability_notes=applicability,
        result_hash=canonical_sha256(
            {
                "case": normalized.engineering_case_id,
                "records": [asdict(r) for r in records],
                "rankings": rankings,
                "recommended": recommended.candidate_id if recommended else None,
            }
        ),
    )


def render_design_report_markdown(report: AutonomousDesignToolReport) -> str:
    if not report.ingestion.ok:
        lines = [
            f"# {TASK_ID}",
            "",
            "## Input blocked",
            "",
            *[f"- `{b['code']}`: {b['detail']}" for b in report.ingestion.blockers],
        ]
        return "\n".join(lines)
    lines = [
        f"# {TASK_ID}",
        "",
        f"**Case:** `{report.ingestion.engineering_case_id}`",
        f"**Status:** {report.engineering_design_status}",
        f"**Structural candidates generated:** {report.structural_candidates_generated}",
        f"**Evaluated:** {report.structural_candidates_evaluated}",
        "",
        "## Rankings",
        "",
    ]
    for k, v in report.rankings.items():
        lines.append(f"- **{k}:** {v or 'null'}")
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            f"- **No feasible candidate (full joint):** {report.no_feasible_candidate}",
            f"- **Recommended layout:** {report.recommended_layout_key or 'null'}",
            "",
        ]
    )
    if report.design_specification:
        g = report.design_specification["geometry"]
        th = report.design_specification["thermal_experimental_prescreen"]
        hy = report.design_specification["hydraulic_baseline"]
        lines.extend(
            [
                "## Design specification (experimental)",
                "",
                f"- Shell ID: {g['shell_inside_diameter_m']} m",
                f"- Tubes: {g['physical_tube_count']} × OD {g['tube_outer_diameter_m']} m, "
                f"length {g['tube_length_m']} m, pitch {g['tube_pitch_m']} m, passes {g['tube_pass_count']}",
                f"- Baffles: {g['baffle_count']} @ {g['baffle_spacing_m']} m, cut {g['baffle_cut_fraction']}",
                f"- Area basis: {th['heat_transfer_area_basis_m2']} m²",
                f"- Q (prescreen): {th['clean_q_w']} W (target {th['target_duty_w']} W)",
                f"- U·A: {th['overall_ua_w_per_k']} W/K",
                f"- Temperatures K: tube {th['tube_inlet_k']}→{th['tube_outlet_k']}, "
                f"shell {th['shell_inlet_k']}→{th['shell_outlet_k']}",
                f"- Δp high-loss full path Pa: tube {hy['high_full_path_tube_dp_pa']}, shell {hy['high_full_path_shell_dp_pa']}",
                "",
            ]
        )
    if report.mdot_verdicts:
        lines.append("## Mdot verification (recommended layout)")
        lines.append("")
        for v in report.mdot_verdicts:
            lines.append(
                f"- `{v.scenario_key}`: joint_pass={v.engineering_joint_pass} "
                f"Q={v.thermal_q_w} reasons={','.join(v.joint_block_reasons) or 'none'}"
            )
    lines.extend(["", "## Applicability", ""])
    lines.extend(f"- {n}" for n in report.applicability_notes)
    return "\n".join(lines)


def report_to_json_dict(report: AutonomousDesignToolReport) -> dict[str, Any]:
    return {
        "schema": "hxforge.autonomous-design-tool-report.v1",
        "task_id": report.task_id,
        "engineering_design_status": report.engineering_design_status,
        "production_rating_validated": report.production_rating_validated,
        "ingestion": {
            "ok": report.ingestion.ok,
            "engineering_case_id": report.ingestion.engineering_case_id,
            "blockers": [dict(b) for b in report.ingestion.blockers],
        },
        "structural_candidates_generated": report.structural_candidates_generated,
        "structural_candidates_evaluated": report.structural_candidates_evaluated,
        "candidate_records": [asdict(r) for r in report.candidate_records],
        "rankings": report.rankings,
        "recommended_candidate_id": report.recommended_candidate_id,
        "recommended_layout_key": report.recommended_layout_key,
        "no_feasible_candidate": report.no_feasible_candidate,
        "design_specification": report.design_specification,
        "mdot_verdicts": [asdict(v) for v in report.mdot_verdicts],
        "applicability_notes": list(report.applicability_notes),
        "result_hash": report.result_hash,
    }