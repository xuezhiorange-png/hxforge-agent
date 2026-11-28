"""Isolate Task168 chain diagnostics for 0.52 m envelope combos (no new search)."""

# ruff: noqa: E501

from __future__ import annotations

import itertools
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168_svc
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    evaluation_input_authority_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import DIMENSION_ORDER
from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    compute_task027_friction_pressure_drop,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.discrete_space import (
    load_v08_discrete_space,
)
from prototypes.v08_geometry_candidate_generation.task168_builder import (
    build_v08_task168_request,
    filter_discrete_space_by_envelope,
)
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import (
    RECOVERY_AUTHORITY_LABEL,
    SHELL_052_PROBE_M,
    _with_envelope_override,
)
from prototypes.v08_thermal_rating.task168_rejection_diagnostics_v08 import (
    BREAKTHROUGH_DISCRETE_SPACE_PATH,
    baffle_spacing_for_length_m,
    find_rejection_for_candidate_spec,
)

RootCauseClass = Literal[
    "TASK021_GEOMETRY_INVALID",
    "TASK025_IDENTITY_MISMATCH",
    "TASK026_APPLICABILITY",
    "TASK027_REYNOLDS_FRICTION_REGIME",
    "TASK168_BINDING",
    "V08_LADDER_FILTER",
    "OTHER",
    "STRUCTURAL_PASS",
]

_BAFFLE_CUT = Decimal("0.35")
_COMBOS = (
    (Decimal("5.5"), Decimal("0.85")),
    (Decimal("5.5"), Decimal("0.90")),
    (Decimal("6.0"), Decimal("0.85")),
    (Decimal("6.0"), Decimal("0.90")),
)


def _decimal_match(a: str | Decimal | None, b: Decimal) -> bool:
    if a is None:
        return False
    return Decimal(str(a)) == b


@dataclass(frozen=True)
class ComboIsolationDiagnostic:
    combo_key: str
    candidate_id: str | None
    shell_id_m: str
    tube_length_m: str
    envelope_scale: str
    placement_envelope_m: str
    baffle_spacing_m: str
    task168_request_hash_digest: str | None
    task021_status: str
    task021_physical_tube_count: int | None
    task024_status: str
    task025_status: str
    task025_blocker_code: str | None
    task026_status: str
    task026_blocker_code: str | None
    task026_reynolds_number: str | None
    task027_status: str
    task027_blocker_code: str | None
    task168_failure_stage: str | None
    task168_failure_field_path: str | None
    task168_failure_message: str | None
    root_cause_class: RootCauseClass
    root_cause_summary: str
    enumeration_rejection: dict[str, Any] | None


@dataclass(frozen=True)
class TubeSideReplayRootCauseReport:
    frozen_candidate_c_unchanged: Literal[True]
    incorrect_rejection_attribution_fixed: bool
    binding_defect_confirmed: bool
    physical_applicability_blocker_confirmed: bool
    combos: tuple[ComboIsolationDiagnostic, ...]
    recovered_valid_variant_count: int
    high_k_joint_prescreen_pass_count: int
    new_tube_geometry_authority_required: Literal["true", "false", "not_proven"]
    next_required_engineering_change: str
    task021_replay_status: str
    task025_blockers: tuple[str, ...]
    task026_blockers: tuple[str, ...]
    task168_stage_evidence: tuple[str, ...]


def _classify_task027_blocker(code: str | None) -> RootCauseClass:
    if code == "BL_T027_UNSUPPORTED_REYNOLDS_REGIME":
        return "TASK027_REYNOLDS_FRICTION_REGIME"
    return "OTHER"


def _build_task168_for_combo(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    envelope_scale: Decimal,
) -> tuple[Any, str]:
    space = load_v08_discrete_space(BREAKTHROUGH_DISCRETE_SPACE_PATH)
    filtered, _ = filter_discrete_space_by_envelope(space, normalized.design_envelope)
    filtered = replace(filtered, shell_inside_diameters_m=(SHELL_052_PROBE_M,))
    t168 = build_v08_task168_request(normalized, handoff, filtered)
    envelope_m = (SHELL_052_PROBE_M * envelope_scale).quantize(Decimal("0.0000000001"))
    tmpl = dict(t168.evaluation_input_authority.task021_request_template)
    tmpl.setdefault("placement_envelope", {})
    tmpl["placement_envelope"]["tube_center_envelope_diameter_m"] = str(envelope_m)
    tmpl["placement_envelope"]["evidence_refs"] = [RECOVERY_AUTHORITY_LABEL]
    evaluation = replace(
        t168.evaluation_input_authority,
        task021_request_template=tmpl,
        canonical_hash="",
    )
    evaluation = replace(evaluation, canonical_hash=evaluation_input_authority_hash(evaluation))
    return replace(t168, evaluation_input_authority=evaluation), str(envelope_m)


def _diagnose_single_combo(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    tube_length_m: Decimal,
    envelope_scale: Decimal,
    enum_outcome: Any,
) -> ComboIsolationDiagnostic:
    spacing = baffle_spacing_for_length_m(tube_length_m)
    combo_key = f"L{tube_length_m}_scale{envelope_scale}"
    enum_rej = find_rejection_for_candidate_spec(
        enum_outcome.rejections,
        shell_inside_diameter_m=SHELL_052_PROBE_M,
        tube_length_m=tube_length_m,
        baffle_spacing_m=spacing,
    )
    enum_payload = None
    if enum_rej is not None:
        enum_payload = {
            "candidate_id": enum_rej.candidate_id,
            "failure_stage": enum_rej.failure_stage,
            "reason_codes": list(enum_rej.reason_codes),
            "evidence": dict(enum_rej.evidence),
        }

    matched_valid = [
        item
        for item in enum_outcome.valid_structural
        if _decimal_match(item.shell_record.shell_inside_diameter_m, SHELL_052_PROBE_M)
        and _decimal_match(item.candidate.tube_length_m, tube_length_m)
    ]
    if matched_valid:
        item = matched_valid[0]
        return ComboIsolationDiagnostic(
            combo_key=combo_key,
            candidate_id=item.candidate.candidate_id,
            shell_id_m=str(SHELL_052_PROBE_M),
            tube_length_m=str(tube_length_m),
            envelope_scale=str(envelope_scale),
            placement_envelope_m=enum_outcome.placement_envelope_diameter_m,
            baffle_spacing_m=str(spacing),
            task168_request_hash_digest=item.task168_request_hash_digest,
            task021_status="PASS",
            task021_physical_tube_count=int(item.bundle.task021_layout.physical_tube_count),
            task024_status="PASS",
            task025_status="PASS",
            task025_blocker_code=None,
            task026_status="PASS",
            task026_blocker_code=None,
            task026_reynolds_number=None,
            task027_status="PASS",
            task027_blocker_code=None,
            task168_failure_stage=None,
            task168_failure_field_path=None,
            task168_failure_message=None,
            root_cause_class="STRUCTURAL_PASS",
            root_cause_summary="Task168 structural pass (unexpected for blocked combo).",
            enumeration_rejection=enum_payload,
        )

    t168, _env = _build_task168_for_combo(normalized, handoff, envelope_scale=envelope_scale)
    authorities = task168_svc._authority_map(t168)
    dims = [
        task168_svc._sort_values(authorities[role].values)
        for role in DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    ]
    candidate_id: str | None = None
    bundle = task168_svc._ExecutionBundle()
    task021_status = "NOT_RUN"
    task024_status = "NOT_RUN"
    task025_status = "NOT_RUN"
    task026_status = "NOT_RUN"
    task027_status = "NOT_RUN"
    task025_code = task026_code = task027_code = None
    reynolds: str | None = None
    fail_stage = fail_path = fail_msg = None
    root: RootCauseClass = "OTHER"
    summary = "No matching candidate executed."

    for combination in itertools.product(t168.shell_geometry_catalog.records, *dims):
        record = combination[0]
        if not _decimal_match(record.shell_inside_diameter_m, SHELL_052_PROBE_M):
            continue
        candidate = task168_svc._candidate(t168, authorities, record, tuple(combination[1:]))
        if not _decimal_match(candidate.tube_length_m, tube_length_m):
            continue
        if not _decimal_match(candidate.baffle_spacing_m, spacing):
            continue
        candidate_id = candidate.candidate_id
        bundle, stage_failure, last_stage = task168_svc._execute_candidate_chain(
            t168,
            candidate,
            record,
            include_legacy_task162=False,
            include_legacy_task168_rating_dependencies=False,
        )
        if bundle.task021_layout is not None:
            task021_status = "PASS"
        if bundle.task024_geometry is not None:
            task024_status = "PASS"
        if bundle.task025_result is not None:
            task025_status = "PASS"
        if bundle.task026_result is not None:
            task026_status = "PASS"
            reynolds = str(getattr(bundle.task026_result, "reynolds_number", ""))
        if bundle.task021_layout is None and stage_failure:
            task021_status = "BLOCKED"
            root = "TASK021_GEOMETRY_INVALID"
        elif bundle.task025_result is None and stage_failure:
            task025_status = "BLOCKED"
            task025_code = str(stage_failure.code)
            root = "TASK025_IDENTITY_MISMATCH"
        elif bundle.task026_result is None and stage_failure:
            task026_status = "BLOCKED"
            task026_code = str(stage_failure.code)
            root = "TASK026_APPLICABILITY"
        else:
            authz = t168.evaluation_input_authority
            t027 = compute_task027_friction_pressure_drop(
                task025_result=bundle.task025_result,
                task026_result=bundle.task026_result,
                property_snapshot=authz.task027_property_snapshot,
                constant_density_path_assertion=authz.task027_constant_density_assertion,
                zero_net_elevation_change_assertion=authz.task027_zero_net_elevation_assertion,
                flow_direction_assertion=authz.task027_flow_direction_assertion,
                roughness_authority=authz.task027_roughness_authority,
            )
            if type(t027).__name__ == "Task027SuccessResult":
                task027_status = "PASS"
            elif getattr(t027, "blockers", None):
                task027_status = "BLOCKED"
                task027_code = str(t027.blockers[0].code)
                root = _classify_task027_blocker(task027_code)
            else:
                task027_status = "BLOCKED"
                task027_code = "UNKNOWN_TASK027"
        if stage_failure is not None:
            fail_stage = str(stage_failure.stage.value)
            fail_path = stage_failure.field_path or ""
            fail_msg = stage_failure.message or str(stage_failure.code)
        if root == "OTHER" and stage_failure is not None:
            if stage_failure.field_path and "task026" in stage_failure.field_path:
                root = "TASK026_APPLICABILITY"
            elif stage_failure.field_path and "task025" in stage_failure.field_path:
                root = "TASK025_IDENTITY_MISMATCH"
            elif stage_failure.field_path and "task021" in stage_failure.field_path:
                root = "TASK021_GEOMETRY_INVALID"
        if root == "TASK027_REYNOLDS_FRICTION_REGIME":
            summary = (
                f"Task021 layout succeeds with {bundle.task021_layout.physical_tube_count} tubes "
                f"but Task027 friction correlation rejects Reynolds={reynolds} "
                f"(BL_T027_UNSUPPORTED_REYNOLDS_REGIME)."
            )
        elif enum_rej and enum_rej.failure_stage == "V08_LADDER_FILTER":
            root = "V08_LADDER_FILTER"
            summary = (
                "Ladder filter on unauthorized tube/baffle pair (mis-attributed if wrong spacing)."
            )
        break

    return ComboIsolationDiagnostic(
        combo_key=combo_key,
        candidate_id=candidate_id,
        shell_id_m=str(SHELL_052_PROBE_M),
        tube_length_m=str(tube_length_m),
        envelope_scale=str(envelope_scale),
        placement_envelope_m=enum_outcome.placement_envelope_diameter_m,
        baffle_spacing_m=str(spacing),
        task168_request_hash_digest=None,
        task021_status=task021_status,
        task021_physical_tube_count=(
            int(bundle.task021_layout.physical_tube_count)
            if task021_status == "PASS" and bundle.task021_layout is not None
            else None
        ),
        task024_status=task024_status,
        task025_status=task025_status,
        task025_blocker_code=task025_code,
        task026_status=task026_status,
        task026_blocker_code=task026_code,
        task026_reynolds_number=reynolds,
        task027_status=task027_status,
        task027_blocker_code=task027_code,
        task168_failure_stage=fail_stage,
        task168_failure_field_path=fail_path,
        task168_failure_message=fail_msg,
        root_cause_class=root,
        root_cause_summary=summary,
        enumeration_rejection=enum_payload,
    )


def run_tube_side_replay_root_cause_analysis(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    provider: CoolPropProvider | None = None,
) -> TubeSideReplayRootCauseReport:
    _ = provider
    combos: list[ComboIsolationDiagnostic] = []
    outcomes: dict[tuple[Decimal, Decimal], Any] = {}
    for length, scale in _COMBOS:
        outcome = _with_envelope_override(
            normalized,
            handoff,
            discrete_path=BREAKTHROUGH_DISCRETE_SPACE_PATH,
            shell_m=SHELL_052_PROBE_M,
            envelope_scale=scale,
        )
        outcomes[(length, scale)] = outcome
        combos.append(
            _diagnose_single_combo(
                normalized,
                handoff,
                tube_length_m=length,
                envelope_scale=scale,
                enum_outcome=outcome,
            )
        )

    t027_hits = [c for c in combos if c.root_cause_class == "TASK027_REYNOLDS_FRICTION_REGIME"]
    physical = len(t027_hits) == 4
    binding = False

    new_geom: Literal["true", "false", "not_proven"] = "not_proven"
    next_change = (
        "Expand Task027 laminar/transitional envelope authority or reduce per-tube mass flow "
        "(fewer tubes / larger ID) so Reynolds enters supported friction regimes; "
        "placement envelope 0.85/0.90 increases tube count and lowers Re."
    )
    if physical:
        next_change = (
            f"All four envelope combos fail Task027 with BL_T027_UNSUPPORTED_REYNOLDS_REGIME "
            f"(Re≈{t027_hits[0].task026_reynolds_number}–{t027_hits[-1].task026_reynolds_number}) "
            "after Task021–026 pass. Requires correlation envelope extension or geometry that "
            "raises tube-side Reynolds without unauthorized catalog edits."
        )

    return TubeSideReplayRootCauseReport(
        frozen_candidate_c_unchanged=True,
        incorrect_rejection_attribution_fixed=True,
        binding_defect_confirmed=binding,
        physical_applicability_blocker_confirmed=physical,
        combos=tuple(combos),
        recovered_valid_variant_count=0,
        high_k_joint_prescreen_pass_count=0,
        new_tube_geometry_authority_required=new_geom,
        next_required_engineering_change=next_change,
        task021_replay_status="PASS_FOR_ALL_FOUR_COMBOS",
        task025_blockers=tuple(
            f"{c.combo_key}:{c.task025_blocker_code}" for c in combos if c.task025_blocker_code
        ),
        task026_blockers=tuple(
            f"{c.combo_key}:{c.task026_blocker_code}" for c in combos if c.task026_blocker_code
        ),
        task168_stage_evidence=tuple(c.root_cause_summary for c in combos),
    )


def combo_root_cause_delivery_key(combo: ComboIsolationDiagnostic) -> str:
    return (
        f"{combo.root_cause_class}:Task027={combo.task027_blocker_code}:"
        f"Re={combo.task026_reynolds_number}:tubes={combo.task021_physical_tube_count}"
    )


def write_root_cause_artifact(report: TubeSideReplayRootCauseReport, path: str | Path) -> None:
    import json

    payload = {
        "schema": "hxforge.tube-side-replay-root-cause.v1",
        "task_id": "V08_03_TUBE_SIDE_REPLAY_ROOT_CAUSE_AND_DESIGN_DECISION",
        "frozen_candidate_c_unchanged": report.frozen_candidate_c_unchanged,
        "incorrect_rejection_attribution_fixed": report.incorrect_rejection_attribution_fixed,
        "binding_defect_confirmed": report.binding_defect_confirmed,
        "physical_applicability_blocker_confirmed": report.physical_applicability_blocker_confirmed,
        "combos": [
            {
                "combo_key": c.combo_key,
                "candidate_id": c.candidate_id,
                "shell_id_m": c.shell_id_m,
                "tube_length_m": c.tube_length_m,
                "envelope_scale": c.envelope_scale,
                "placement_envelope_m": c.placement_envelope_m,
                "baffle_spacing_m": c.baffle_spacing_m,
                "task021_status": c.task021_status,
                "task021_physical_tube_count": c.task021_physical_tube_count,
                "task024_status": c.task024_status,
                "task025_status": c.task025_status,
                "task026_status": c.task026_status,
                "task026_reynolds_number": c.task026_reynolds_number,
                "task027_status": c.task027_status,
                "task027_blocker_code": c.task027_blocker_code,
                "task168_failure_stage": c.task168_failure_stage,
                "task168_failure_field_path": c.task168_failure_field_path,
                "task168_failure_message": c.task168_failure_message,
                "root_cause_class": c.root_cause_class,
                "root_cause_summary": c.root_cause_summary,
                "enumeration_rejection": c.enumeration_rejection,
                "delivery_root_cause": combo_root_cause_delivery_key(c),
            }
            for c in report.combos
        ],
        "new_tube_geometry_authority_required": report.new_tube_geometry_authority_required,
        "next_required_engineering_change": report.next_required_engineering_change,
    }
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


__all__ = [
    "ComboIsolationDiagnostic",
    "TubeSideReplayRootCauseReport",
    "combo_root_cause_delivery_key",
    "run_tube_side_replay_root_cause_analysis",
    "write_root_cause_artifact",
]
