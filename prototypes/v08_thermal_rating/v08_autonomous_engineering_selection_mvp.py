"""V08_AUTONOMOUS_ENGINEERING_SELECTION_MVP — prototype unified selection entry (experimental)."""

# ruff: noqa: E501

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.live_thermal_state_hydraulic_postpass import (
    Task168CandidateBundle,
    run_live_thermal_state_hydraulic_postpass_from_ctx,
)
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.physical_feasibility import THERMODYNAMIC_DUTY_TOLERANCE
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.geometry_identity_v2 import (
    geometry_identity_v2_hash,
    geometry_projection_hash_v1,
)
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    run_autonomous_nozzle_full_path,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CandidateRatingBindings,
    build_candidate_rating_bindings,
)
from prototypes.v08_thermal_rating.candidate_c_identity_v08 import (
    CANDIDATE_C_SHELL_NOZZLE_ID_M,
    CANDIDATE_C_TUBE_NOZZLE_ID_M,
)
from prototypes.v08_thermal_rating.engineering_shortlist_robustness_v08 import (
    _CANONICAL_SCALE,
    _SHORTLIST,
    _build_t168_with_envelope,
    _resolve_structural,
)
from prototypes.v08_thermal_rating.fixed_layout_variable_mdot_hydraulic_replay_v1 import (
    AUTHORITY_ID as REPLAY_AUTHORITY,
)
from prototypes.v08_thermal_rating.fixed_layout_variable_mdot_hydraulic_replay_v1 import (
    LossTierRow,
    MdotScenarioReplayRow,
    live_postpass_to_r27_bridge,
    run_replay_matrix_v1,
)
from prototypes.v08_thermal_rating.thermal_prescreen_v08 import run_thermal_prescreen
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import (
    build_engineering_case_v2_from_v08,
)
from prototypes.v08_thermal_rating.v08_task037_evaluate_binding_v08 import evaluate_binding_task037

TASK_ID = "V08_AUTONOMOUS_ENGINEERING_SELECTION_MVP"
ENGINEERING_DESIGN_STATUS = "EXPERIMENTAL_PRESCREEN_ONLY_NOT_PRODUCTION_THERMAL_ACCEPTANCE"
HYDRAULIC_VALIDATION_STATUS = (
    "EXPERIMENTAL_VARIABLE_MDOT_REPLAY_NOT_MANUFACTURING_DESIGN_APPROVAL"
)


@dataclass(frozen=True)
class ScenarioJointVerdict:
    shortlist_key: str
    scenario_key: str
    geometry_v2: str
    tube_layout_hash: str
    thermal_pass: bool
    thermal_q_w: str | None
    thermal_gap_w: str | None
    task027_pass: bool
    variable_mdot_binding_pass: bool
    hydraulic_tiers_computed: bool
    hydraulic_all_tiers_pass: bool
    nozzle_velocity_pass: bool
    identity_binding_pass: bool
    engineering_joint_pass: bool
    joint_block_reasons: tuple[str, ...]


@dataclass(frozen=True)
class CandidateRanking:
    nominal_best: str | None
    thermal_margin_best: str | None
    hydraulic_margin_best: str | None
    robust_exploration: str | None
    notes: tuple[str, ...]


@dataclass(frozen=True)
class AutonomousEngineeringSelectionReport:
    task_id: str
    engineering_design_status: str
    hydraulic_validation_status: str
    replay_authority_id: str
    engineering_case_id: str
    target_duty_w: str
    scenario_verdicts: tuple[ScenarioJointVerdict, ...]
    rankings: CandidateRanking
    selected_design_spec: dict[str, Any] | None
    t235_l5p5_thermal_audit: dict[str, Any]
    case_result_hash: str


def _thermal_meets_target(q_w: str | None, target: Decimal) -> tuple[bool, str | None]:
    if q_w is None:
        return False, None
    q = Decimal(q_w)
    gap = q - target
    ok = q * THERMODYNAMIC_DUTY_TOLERANCE >= target
    return ok, str(gap.quantize(Decimal("0.1")))


def _tier_pass(row: MdotScenarioReplayRow, tier: str) -> bool:
    for t in row.loss_tiers:
        if t.tier == tier:
            return t.hydraulic_check == "PASS" and t.full_path_feasible
    return False


def _all_hydraulic_tiers_pass(row: MdotScenarioReplayRow) -> bool:
    if len(row.loss_tiers) != 3:
        return False
    return all(t.hydraulic_check == "PASS" and t.full_path_feasible for t in row.loss_tiers)


def _nozzle_pass(row: MdotScenarioReplayRow) -> bool:
    if not row.port_velocities:
        return False
    for vel in row.port_velocities.values():
        v = Decimal(vel)
        if v < Decimal("1") or v > Decimal("3"):
            return False
    return True


def verdict_from_row(
    row: MdotScenarioReplayRow,
    *,
    target_q: Decimal,
    layout_geometry_v2: str,
    layout_hash: str,
) -> ScenarioJointVerdict:
    thermal_pass, gap = _thermal_meets_target(row.clean_q_w, target_q)
    task027_pass = row.task027_status == "PASS"
    hydraulic_computed = len(row.loss_tiers) == 3
    hydraulic_all = _all_hydraulic_tiers_pass(row)
    nozzle_ok = _nozzle_pass(row)
    identity_ok = row.geometry_v2 == layout_geometry_v2 and row.tube_layout_hash == layout_hash
    reasons: list[str] = []
    if not thermal_pass:
        reasons.append("THERMAL_Q_BELOW_TARGET")
    if not task027_pass:
        reasons.append(row.task027_blocker or "TASK027_BLOCKED")
    if not row.variable_mdot_binding_pass:
        reasons.append("VARIABLE_MDOT_BINDING_FAIL")
    if not hydraulic_computed:
        reasons.append("HYDRAULIC_TIERS_NOT_COMPUTED")
    if hydraulic_computed and not hydraulic_all:
        reasons.append("HYDRAULIC_TIER_MARGIN_FAIL")
    if not nozzle_ok:
        reasons.append("NOZZLE_VELOCITY_OUT_OF_1_3_M_S")
    if not identity_ok:
        reasons.append("GEOMETRY_IDENTITY_DRIFT")
    joint = (
        thermal_pass
        and task027_pass
        and row.variable_mdot_binding_pass
        and hydraulic_all
        and nozzle_ok
        and identity_ok
    )
    return ScenarioJointVerdict(
        shortlist_key=row.shortlist_key,
        scenario_key=row.scenario_key,
        geometry_v2=row.geometry_v2,
        tube_layout_hash=row.tube_layout_hash,
        thermal_pass=thermal_pass,
        thermal_q_w=row.clean_q_w,
        thermal_gap_w=gap,
        task027_pass=task027_pass,
        variable_mdot_binding_pass=row.variable_mdot_binding_pass,
        hydraulic_tiers_computed=hydraulic_computed,
        hydraulic_all_tiers_pass=hydraulic_all,
        nozzle_velocity_pass=nozzle_ok,
        identity_binding_pass=identity_ok,
        engineering_joint_pass=joint,
        joint_block_reasons=tuple(reasons),
    )


def _high_margins(row: dict[str, Any]) -> tuple[Decimal, Decimal]:
    hi = next(t for t in row["loss_tiers"] if t["tier"] == "high_loss_sensitivity")
    tm = Decimal(hi["tube_margin_pa"]) if hi.get("tube_margin_pa") else Decimal("-999999")
    sm = Decimal(hi["shell_margin_pa"]) if hi.get("shell_margin_pa") else Decimal("-999999")
    return tm, sm


def rank_candidates(
    verdicts: tuple[ScenarioJointVerdict, ...],
    rows: list[dict[str, Any]],
    *,
    target_q: Decimal,
) -> CandidateRanking:
    by_layout: dict[str, list[ScenarioJointVerdict]] = {}
    for v in verdicts:
        by_layout.setdefault(v.shortlist_key, []).append(v)
    baselines = {k: next(x for x in vs if x.scenario_key == "baseline") for k, vs in by_layout.items()}
    row_by_key = {(r["shortlist_key"], r["scenario_key"]): r for r in rows}

    joint_baselines = [b for b in baselines.values() if b.engineering_joint_pass]
    nominal_best: str | None = None
    if joint_baselines:
        nominal_best = max(
            joint_baselines,
            key=lambda b: (
                Decimal(b.thermal_gap_w or "-999"),
                *_high_margins(row_by_key[(b.shortlist_key, "baseline")]),
            ),
        ).shortlist_key

    thermal_margin_best: str | None = None
    thermal_candidates = [b for b in baselines.values() if b.task027_pass and b.thermal_q_w]
    if thermal_candidates:
        thermal_margin_best = max(
            thermal_candidates,
            key=lambda b: Decimal(b.thermal_gap_w or "-999999"),
        ).shortlist_key

    hydraulic_margin_best: str | None = None
    hyd_candidates = [
        b
        for b in baselines.values()
        if b.task027_pass and b.hydraulic_all_tiers_pass and (b.shortlist_key, "baseline") in row_by_key
    ]
    if hyd_candidates:
        hydraulic_margin_best = max(
            hyd_candidates,
            key=lambda b: min(_high_margins(row_by_key[(b.shortlist_key, "baseline")])),
        ).shortlist_key

    robust: str | None = None
    for key, vs in by_layout.items():
        if all(v.engineering_joint_pass for v in vs):
            robust = key
            break

    notes: list[str] = []
    if robust is None:
        notes.append(
            "ROBUST_EXPLORATION_NONE: no layout passes engineering_joint_pass on all six mdot scenarios."
        )
    if nominal_best is None:
        notes.append("NOMINAL_BEST_NONE: no baseline satisfies full thermal-hydraulic joint criteria.")
    notes.append(
        "Hydraulic tier computation alone does not imply engineering_joint_pass "
        "(thermal Q, Task027, nozzles, and identity are evaluated separately)."
    )
    return CandidateRanking(
        nominal_best=nominal_best,
        thermal_margin_best=thermal_margin_best,
        hydraulic_margin_best=hydraulic_margin_best,
        robust_exploration=robust,
        notes=tuple(notes),
    )


def _audit_t235_thermal(verdicts: tuple[ScenarioJointVerdict, ...]) -> dict[str, Any]:
    rows = [v for v in verdicts if v.shortlist_key == "T235_L5.5"]
    below = [
        {
            "scenario_key": v.scenario_key,
            "clean_q_w": v.thermal_q_w,
            "thermal_pass": v.thermal_pass,
            "thermal_gap_w": v.thermal_gap_w,
            "engineering_joint_pass": v.engineering_joint_pass,
        }
        for v in rows
        if v.thermal_q_w is not None and not v.thermal_pass
    ]
    return {
        "layout": "T235_L5.5",
        "scenarios_below_target_count": len(below),
        "below_target_rows": below,
        "cause_note": (
            "ε-NTU experimental prescreen Q tracks perturbed tube/shell mass flows (C·ΔT path). "
            "Reduced mdot lowers capacitance and/or LMTD — not an artifact of nominal hydraulic postpass. "
            "R19A variable-mdot replay rebinding confirms separate tube Δp at scenario flow."
        ),
    }


def _build_bindings_baseline(
    normalized: NormalizedUserDesignCase,
    handoff: Any,
    *,
    tube_count: int,
    tube_length_m: Decimal,
    provider: CoolPropProvider,
) -> tuple[CandidateRatingBindings | None, Any]:
    scale = _CANONICAL_SCALE[tube_count]
    structural, outcome = _resolve_structural(
        normalized,
        handoff,
        tube_count=tube_count,
        tube_length_m=tube_length_m,
        envelope_scale=scale,
    )
    bindings = build_candidate_rating_bindings(
        structural,
        space_hash=outcome.space_hash,
        t168_digest=structural.task168_request_hash_digest,
        normalized=normalized,
        handoff=handoff,
        provider=provider,
        geometry_projection_hash=geometry_projection_hash_v1(structural),
    )
    return bindings, structural


def build_experimental_design_specification(
    *,
    layout_key: str,
    normalized: NormalizedUserDesignCase,
    handoff: Any,
    provider: CoolPropProvider,
) -> dict[str, Any] | None:
    tube_count = int(layout_key.split("_")[0][1:])
    tube_length_m = Decimal(layout_key.split("_L")[1])
    bindings, structural = _build_bindings_baseline(
        normalized, handoff, tube_count=tube_count, tube_length_m=tube_length_m, provider=provider
    )
    if bindings is None:
        return None
    t037 = evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
    prescreen = run_thermal_prescreen(bindings, normalized, provider=provider, task037_override=t037.raw)
    scale = _CANONICAL_SCALE[tube_count]
    t168 = _build_t168_with_envelope(normalized, handoff, scale)
    eng_case = build_engineering_case_v2_from_v08(normalized)
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
        tube_inlet_temperature_k=normalized.tube_side.inlet_temperature_k,
        tube_outlet_temperature_k=Decimal(str(prescreen.predicted_tube_outlet_k or normalized.tube_side.inlet_temperature_k)),
        shell_inlet_temperature_k=normalized.shell_side.inlet_temperature_k,
        shell_outlet_temperature_k=Decimal(str(prescreen.predicted_shell_outlet_k or normalized.shell_side.inlet_temperature_k)),
        tube_inlet_pressure_pa=normalized.tube_side.inlet_pressure_pa,
        shell_inlet_pressure_pa=normalized.shell_side.inlet_pressure_pa,
        provider=provider,
    )
    bridge = live_postpass_to_r27_bridge(live, normalized=normalized)
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
    cand = structural.candidate
    shell = structural.shell_record
    layout = structural.bundle.task021_layout
    tube_id = cand.tube_outer_diameter_m - Decimal("2") * cand.tube_wall_thickness_m
    mid = next(s for s in hydraulic.scenarios if s.scenario_key == "mid_band")
    high = next(s for s in hydraulic.scenarios if s.scenario_key == "high_loss_sensitivity")
    ports = [
        {
            "port_id": p.port_id,
            "inside_diameter_m": str(p.inside_diameter_m),
            "velocity_m_s": str(p.velocity_m_s),
        }
        for p in hydraulic.ports
    ]
    return {
        "schema": "hxforge.autonomous-engineering-design-spec.v1",
        "engineering_design_status": ENGINEERING_DESIGN_STATUS,
        "layout_key": layout_key,
        "geometry_identity_v2": geometry_identity_v2_hash(structural),
        "geometry": {
            "shell_inside_diameter_m": str(shell.shell_inside_diameter_m),
            "tube_outer_diameter_m": str(cand.tube_outer_diameter_m),
            "tube_inner_diameter_m": str(tube_id),
            "tube_wall_thickness_m": str(cand.tube_wall_thickness_m),
            "tube_pitch_m": str(cand.tube_pitch_m),
            "tube_length_m": str(cand.tube_length_m),
            "physical_tube_count": int(layout.physical_tube_count),
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
            "target_gap_w": prescreen.target_duty_gap_w,
            "tube_inlet_k": str(normalized.tube_side.inlet_temperature_k),
            "tube_outlet_k": prescreen.predicted_tube_outlet_k,
            "shell_inlet_k": str(normalized.shell_side.inlet_temperature_k),
            "shell_outlet_k": prescreen.predicted_shell_outlet_k,
            "heat_transfer_area_basis_m2": prescreen.area_basis_m2,
        },
        "hydraulic_variable_mdot_baseline": {
            "tube_equipment_dp_pa": live.get("recalculated_tube_dp_pa"),
            "shell_bell_dp_pa": live.get("recalculated_shell_dp_pa"),
            "mid_full_path_tube_dp_pa": mid.tube_full_path_dp_pa,
            "mid_full_path_shell_dp_pa": mid.shell_full_path_dp_pa,
            "high_full_path_tube_dp_pa": high.tube_full_path_dp_pa,
            "high_full_path_shell_dp_pa": high.shell_full_path_dp_pa,
            "tube_margin_high_pa": high.tube_margin_pa,
            "shell_margin_high_pa": high.shell_margin_pa,
            "limits_pa": {
                "tube": str(normalized.max_tube_side_pressure_drop_pa),
                "shell": str(normalized.max_shell_side_pressure_drop_pa),
            },
        },
    }


def run_autonomous_engineering_selection(
    case_json_text: str,
    *,
    provider: CoolPropProvider | None = None,
) -> AutonomousEngineeringSelectionReport:
    """Unified prototype pipeline: case → structure shortlist → thermal/hydraulic/md-verify → rank."""
    provider = provider or CoolPropProvider()
    pipeline = validate_and_build_solver_handoff(
        load_general_user_design_case_json(case_json_text),
        provider=provider,
    )
    normalized = pipeline.normalized
    target_q = normalized.target_duty_w

    matrix = run_replay_matrix_v1(provider=provider, case_json_text=case_json_text)
    raw_rows = matrix["rows"]

    layout_meta: dict[str, tuple[str, str]] = {}
    for tube_count, tube_length_m in _SHORTLIST:
        key = f"T{tube_count}_L{tube_length_m}"
        sample = next(r for r in raw_rows if r["shortlist_key"] == key and r["scenario_key"] == "baseline")
        layout_meta[key] = (sample["geometry_v2"], sample["tube_layout_hash"])

    replay_rows: list[MdotScenarioReplayRow] = []
    for r in raw_rows:
        replay_rows.append(
            MdotScenarioReplayRow(
                shortlist_key=r["shortlist_key"],
                scenario_key=r["scenario_key"],
                scenario_label=r["scenario_label"],
                geometry_v2=r["geometry_v2"],
                tube_layout_hash=r["tube_layout_hash"],
                candidate_spec_id=r["candidate_spec_id"],
                rating_candidate_id=r.get("rating_candidate_id"),
                tube_mass_flow_kg_s=r["tube_mass_flow_kg_s"],
                shell_mass_flow_kg_s=r["shell_mass_flow_kg_s"],
                reynolds_number=r.get("reynolds_number"),
                task027_status=r["task027_status"],
                task027_blocker=r.get("task027_blocker"),
                clean_q_w=r.get("clean_q_w"),
                variable_mdot_binding_pass=r["variable_mdot_binding_pass"],
                postpass_authority=r.get("postpass_authority"),
                tube_task029_dp_pa=r.get("tube_task029_dp_pa"),
                shell_bell_dp_pa=r.get("shell_bell_dp_pa"),
                loss_tiers=tuple(LossTierRow(**t) for t in r["loss_tiers"]),
                port_velocities=dict(r.get("port_velocities") or {}),
                joint_prescreen_pass=r["joint_prescreen_pass"],
                outcome=r["outcome"],
                block_reason=r.get("block_reason"),
            )
        )

    verdicts_list: list[ScenarioJointVerdict] = []
    for row in replay_rows:
        g2, lh = layout_meta[row.shortlist_key]
        verdicts_list.append(verdict_from_row(row, target_q=target_q, layout_geometry_v2=g2, layout_hash=lh))
    verdicts = tuple(verdicts_list)
    rankings = rank_candidates(verdicts, raw_rows, target_q=target_q)

    pick = rankings.nominal_best or rankings.thermal_margin_best or rankings.hydraulic_margin_best
    design_spec = (
        build_experimental_design_specification(
            layout_key=pick,
            normalized=normalized,
            handoff=pipeline.handoff,
            provider=provider,
        )
        if pick
        else None
    )

    return AutonomousEngineeringSelectionReport(
        task_id=TASK_ID,
        engineering_design_status=ENGINEERING_DESIGN_STATUS,
        hydraulic_validation_status=HYDRAULIC_VALIDATION_STATUS,
        replay_authority_id=REPLAY_AUTHORITY,
        engineering_case_id=normalized.engineering_case_id,
        target_duty_w=str(target_q),
        scenario_verdicts=verdicts,
        rankings=rankings,
        selected_design_spec=design_spec,
        t235_l5p5_thermal_audit=_audit_t235_thermal(verdicts),
        case_result_hash=canonical_sha256(
            {
                "case": normalized.engineering_case_id,
                "verdicts": [asdict(v) for v in verdicts],
                "rankings": asdict(rankings),
            }
        ),
    )


def report_to_artifact_dict(report: AutonomousEngineeringSelectionReport) -> dict[str, Any]:
    return {
        "schema": "hxforge.autonomous-engineering-selection.v1",
        "task_id": report.task_id,
        "engineering_design_status": report.engineering_design_status,
        "hydraulic_validation_status": report.hydraulic_validation_status,
        "replay_authority_id": report.replay_authority_id,
        "engineering_case_id": report.engineering_case_id,
        "target_duty_w": report.target_duty_w,
        "rankings": asdict(report.rankings),
        "scenario_verdicts": [asdict(v) for v in report.scenario_verdicts],
        "selected_design_spec": report.selected_design_spec,
        "t235_l5p5_thermal_audit": report.t235_l5p5_thermal_audit,
        "case_result_hash": report.case_result_hash,
    }


def write_selection_artifact(path: Path, report: AutonomousEngineeringSelectionReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report_to_artifact_dict(report), indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_250, FIXTURE_330

    provider = CoolPropProvider()
    for label, fixture in (("330kW", FIXTURE_330), ("250kW_independent", FIXTURE_250)):
        report = run_autonomous_engineering_selection(fixture.read_text(encoding="utf-8"), provider=provider)
        out = Path(f"/opt/cursor/artifacts/v08_autonomous_engineering_selection_{label}.json")
        write_selection_artifact(out, report)
        summary = {
            "case": report.engineering_case_id,
            "rankings": asdict(report.rankings),
            "joint_pass_count": sum(1 for v in report.scenario_verdicts if v.engineering_joint_pass),
            "selected_layout": (report.selected_design_spec or {}).get("layout_key"),
        }
        print(label, json.dumps(summary, indent=2))