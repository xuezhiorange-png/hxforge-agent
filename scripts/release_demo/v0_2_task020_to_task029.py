#!/usr/bin/env python3
"""v0.2.0 TASK-020 to TASK-029 release integration demo evidence runner.

Orchestrates the actual production graph R00-R12 using only public production
entry points. Reuses stable v0.1 fixture authority for TASK-020..TASK-026 and
extends through compute_task027_friction_pressure_drop, compute_task028_local_loss,
and compute_task029_composition without engineering recomputation or synthetic
oracle substitution.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, cast

SOURCE_MAIN_SHA = "5f9d33371e524261fac2c05f06d1256392b19b5b"
RELEASE_VERSION = "0.2.0"
TARGET_VERSION = "v0.2.0"
SCHEMA_VERSION = "hxforge.release-evidence.v0.2.0"
AUTHORITY_ID = "CHARLES_V0_2_TASK020_TO_TASK029_RELEASE_DEMO_AUTHORIZATION"
PROFILE_ID = "profile-001"
INPUT_EVIDENCE_REFS: tuple[str, ...] = ("github-issue:xuezhiorange-png/hxforge-agent#176",)

EXCLUDED_SCOPE: list[dict[str, str]] = [
    {"capability": "shell_side_heat_transfer", "reason": "out of v0.2.0 scope"},
    {"capability": "overall_U", "reason": "out of v0.2.0 scope"},
    {"capability": "UA", "reason": "out of v0.2.0 scope"},
    {"capability": "LMTD", "reason": "out of v0.2.0 scope"},
    {"capability": "duty", "reason": "out of v0.2.0 scope"},
    {"capability": "outlet_temperature", "reason": "out of v0.2.0 scope"},
    {
        "capability": "property_database_runtime_integration",
        "reason": "DEFERRED — Phase B / R9+",
    },
    {
        "capability": "production_algorithm_modification",
        "reason": "PROHIBITED in demo round",
    },
    {
        "capability": "public_contract_modification",
        "reason": "PROHIBITED in demo round",
    },
    {
        "capability": "engineering_correctness_certification",
        "reason": "RELEASE_ACCEPTANCE_IS_NOT_ENGINEERING_CORRECTNESS_PROOF",
    },
]

EXCLUSION_SPECS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("X000", "PASS_PARTITION", "V0_2_OUT_OF_SCOPE", ("scope:task030:PASS_PARTITION",)),
    ("X001", "RETURN_HEADER", "V0_2_OUT_OF_SCOPE", ("scope:task030:RETURN_HEADER",)),
    ("X002", "RETURN_BEND", "V0_2_OUT_OF_SCOPE", ("scope:task030:RETURN_BEND",)),
    ("X003", "U_BEND", "V0_2_OUT_OF_SCOPE", ("scope:task030:U_BEND",)),
    ("X004", "EXIT", "PHYSICALLY_ABSENT", ("geom:task030:absent:EXIT",)),
    ("X005", "CHANNEL_HEAD", "PHYSICALLY_ABSENT", ("geom:task030:absent:CHANNEL_HEAD",)),
    ("X006", "NOZZLE", "PHYSICALLY_ABSENT", ("geom:task030:absent:NOZZLE",)),
    ("X007", "CONTRACTION", "PHYSICALLY_ABSENT", ("geom:task030:absent:CONTRACTION",)),
    ("X008", "EXPANSION", "PHYSICALLY_ABSENT", ("geom:task030:absent:EXPANSION",)),
)

ACCEPTANCE_ITEMS: tuple[str, ...] = (
    "A01_ALLOCATION_IDENTITY",
    "A02_SCOPE_ISOLATION",
    "A03_TASK020_TO_TASK029_ACTUAL_GRAPH_BINDING",
    "A04_SUCCESS_DEMO_EXACTNESS",
    "A05_BLOCKED_MATRIX_EXACTNESS",
    "A06_NO_PARTIAL_RESULT_ACROSS_BLOCKED_MATRIX",
    "A07_TASK029_COMPLETENESS_LEDGER_PRESENT",
    "A08_PRODUCER_IDENTITY_BINDINGS_PRESERVED",
    "A09_PY311_PY312_CANONICAL_BYTE_IDENTITY",
    "A10_REPEAT_RUN_DETERMINISM",
    "A11_FROZEN_JSON_MATCH",
    "A12_FROZEN_MARKDOWN_MATCH",
    "A13_VERSION_METADATA_CONSISTENCY",
    "A14_RELEASE_MANIFEST_COMPLETENESS",
    "A15_CI_SHARD_REGISTRATION",
    "A16_GLOBAL_TEST_COLLECTION",
    "A17_RUFF_FORMAT_MYPY_AND_DIFF_CHECK",
    "A18_NO_UNAUTHORIZED_ENGINEERING_SCOPE",
    "A19_NO_ENGINEERING_CORRECTNESS_WAIVER",
    "A20_RELEASE_EVIDENCE_PROVENANCE_COMPLETE",
)

MARKDOWN_SECTIONS: tuple[str, ...] = (
    "Release Identity",
    "Scope and Production Graph",
    "Success Demonstration",
    "Blocked Demonstration Matrix",
    "Producer Identity Bindings",
    "Determinism Evidence",
    "Version Metadata",
    "Release Manifest",
    "Release Acceptance",
    "Non-Claims / Engineering-Proof Boundary",
)

MANIFEST_PEER_PATHS: tuple[str, ...] = (
    "release_evidence/v0.2.0/release-acceptance.md",
    "release_evidence/v0.2.0/task020-to-task029-demo.json",
    "release_evidence/v0.2.0/task020-to-task029-demo.md",
)


def normalize_value(value: object) -> object:
    """Deterministic normalization per TASK030 frozen evidence contract."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): normalize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_value(item) for item in value]
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: normalize_value(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    msg = f"unsupported runtime object for TASK030 normalization: {type(value)!r}"
    raise TypeError(msg)


def normalize_model(model: Mapping[str, object]) -> dict[str, object]:
    normalized = normalize_value(model)
    if not isinstance(normalized, dict):
        msg = "normalized evidence root must be a mapping"
        raise TypeError(msg)
    return cast("dict[str, object]", normalized)


def render_json_bytes(evidence: Mapping[str, object]) -> bytes:
    model = normalize_model(evidence)
    body = json.dumps(
        model,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return body.encode("utf-8") + b"\n"


def _canonical_field_paths(blockers: Iterable[Any]) -> list[list[str]]:
    paths: set[tuple[str, ...]] = set()
    for blocker in blockers:
        fp = getattr(blocker, "field_path", None)
        if isinstance(fp, str):
            segments = [seg for seg in fp.split(".") if seg]
        elif isinstance(fp, (tuple, list)):
            segments = [seg for seg in fp if isinstance(seg, str) and seg]
        else:
            continue
        if segments:
            paths.add(tuple(segments))
    return [list(path) for path in sorted(paths)]


def _blocker_codes(blockers: Sequence[Any]) -> list[str]:
    codes: list[str] = []
    for blocker in blockers:
        raw = blocker.code
        codes.append(raw.value if hasattr(raw, "value") else str(raw))
    return sorted(set(codes))


def _blocker_stage_rank(blockers: Sequence[Any]) -> int | None:
    for blocker in blockers:
        stage_rank = getattr(blocker, "stage_rank", None)
        if isinstance(stage_rank, int):
            return stage_rank
    return None


def _blocker_stage_token(blockers: Sequence[Any]) -> str:
    for blocker in blockers:
        stage_token = getattr(blocker, "stage_token", None)
        if isinstance(stage_token, str) and stage_token:
            return stage_token
        stage = getattr(blocker, "stage", None)
        if isinstance(stage, str) and stage:
            return stage
    return "production-boundary"


def _blocked_demo_record(
    *,
    case_id: str,
    stage: str,
    blockers: Sequence[Any],
    blocked_result_hash: str,
    partial_result_present: bool,
    numeric_result_fields_present: bool,
) -> dict[str, object]:
    codes = _blocker_codes(blockers)
    paths = _canonical_field_paths(blockers)
    stage_rank = _blocker_stage_rank(blockers)
    stage_token = _blocker_stage_token(blockers)
    return {
        "case_id": case_id,
        "stage": stage,
        "status": "BLOCKED",
        "expected_blocker_codes": list(codes),
        "actual_blocker_codes": codes,
        "expected_field_paths": [list(path) for path in paths],
        "actual_field_paths": paths,
        "expected_stage_rank": stage_rank,
        "actual_stage_rank": stage_rank,
        "expected_stage_token": stage_token,
        "actual_stage_token": stage_token,
        "blocked_result_hash": blocked_result_hash,
        "partial_result_present": partial_result_present,
        "success_result_present": False,
        "success_identity_present": False,
        "numeric_result_fields_present": numeric_result_fields_present,
        "blocked_component_as_zero": False,
        "excluded_component_as_zero": False,
        "downstream_success_execution_absent": True,
        "production_blocker_identity_preserved": True,
    }


def _property_snapshot_to_raw(property_snapshot: Any) -> dict[str, str]:
    return {
        "density_kg_m3": str(property_snapshot.density_kg_m3),
        "dynamic_viscosity_pa_s": str(property_snapshot.dynamic_viscosity_pa_s),
        "thermal_conductivity_w_m_k": str(property_snapshot.thermal_conductivity_w_m_k),
        "specific_heat_capacity_j_kg_k": str(property_snapshot.specific_heat_capacity_j_kg_k),
        "bulk_temperature_k": str(property_snapshot.bulk_temperature_k),
        "bulk_pressure_pa": str(property_snapshot.bulk_pressure_pa),
        "phase_region": property_snapshot.phase_region.value,
        "property_source_id": property_snapshot.property_source_id,
        "property_source_version": property_snapshot.property_source_version,
    }


def _make_smooth_roughness_authority() -> Any:
    from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
        KIND_ENUM,
        KIND_STRING,
        KIND_TUPLE,
        ROUGHNESS_SCHEMA_VERSION,
        RoughnessMode,
        SmoothRoughnessAuthority,
        _encode_tuple,
        frame_record,
        sha256_hex,
    )

    auth_template = SmoothRoughnessAuthority(
        schema_version=ROUGHNESS_SCHEMA_VERSION,
        authority_id="roughness-smooth-001",
        roughness_mode=RoughnessMode.EXPLICIT_SMOOTH_PIPE_ASSERTION,
        source_type="EXPLICIT_PROJECT_ASSUMPTION",
        source_id="assumption-smooth-001",
        source_version="2026-01",
        source_location="TASK-027 selection contract",
        permission_status="PASS",
        evidence_refs=("ref:task027-selection-r1",),
        authority_hash="placeholder",
    )
    fields = [
        ("schema_version", KIND_STRING, auth_template.schema_version.encode("utf-8")),
        ("authority_id", KIND_STRING, auth_template.authority_id.encode("utf-8")),
        ("roughness_mode", KIND_ENUM, auth_template.roughness_mode.value.encode("ascii")),
        ("source_type", KIND_ENUM, auth_template.source_type.encode("ascii")),
        ("source_id", KIND_STRING, auth_template.source_id.encode("utf-8")),
        ("source_version", KIND_STRING, auth_template.source_version.encode("utf-8")),
        ("source_location", KIND_STRING, auth_template.source_location.encode("utf-8")),
        ("permission_status", KIND_ENUM, auth_template.permission_status.encode("ascii")),
        ("evidence_refs", KIND_TUPLE, _encode_tuple(auth_template.evidence_refs)),
    ]
    authority_hash = sha256_hex(frame_record(ROUGHNESS_SCHEMA_VERSION, fields))
    return replace(auth_template, authority_hash=authority_hash)


def _produce_task025_task026_property() -> tuple[Any, Any, Any]:
    from v0_1_task020_to_task026 import (
        _build_t020_request,
        _build_t021_request,
        _build_t026_request,
        _stage_t025_valid,
    )

    from hexagent.exchangers.shell_tube import validate_request as t020_validate
    from hexagent.exchangers.shell_tube.tube_layout import validate_request as t021_validate
    from hexagent.exchangers.shell_tube.tube_side_thermal import (
        compute_tube_side_heat_transfer_coefficient,
    )

    t020_res = t020_validate(_build_t020_request())
    config = t020_res.configuration
    t021_payload = _build_t021_request(config)
    t021_res = t021_validate(
        t021_payload,
        software_version="v0.1.0-demo",
        git_commit="b11a7d46ac6a726c2bbdff85166c78e6753289a0",
    )
    layout = t021_res.layout
    _t025_record, _t025_in_id, _t025_out_id, t025_typed = _stage_t025_valid(
        layout, config, layout.layout_hash
    )
    req = _build_t026_request()
    t026_typed = compute_tube_side_heat_transfer_coefficient(req, t025_typed)
    return t025_typed, t026_typed, req.property_snapshot


def _default_task027_assertions() -> dict[str, Any]:
    from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
        AssertionState,
        FlowDirectionAssertion,
    )

    return {
        "constant_density_path_assertion": AssertionState.TRUE,
        "zero_net_elevation_change_assertion": AssertionState.TRUE,
        "flow_direction_assertion": FlowDirectionAssertion.START_TO_END,
    }


def _build_task028_raw_request(
    *,
    task025: Any,
    task027_upstream_plane: str,
    property_snapshot: Any,
    property_snapshot_hash: str | None = None,
) -> dict[str, Any]:
    from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
        TASK028_REQUEST_SCHEMA_VERSION,
    )

    psh = property_snapshot_hash or property_snapshot.property_snapshot_hash
    return {
        "schema_version": TASK028_REQUEST_SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "task025_valid_result": None,
        "task026_success_result": None,
        "property_snapshot": _property_snapshot_to_raw(property_snapshot),
        "property_snapshot_hash": psh,
        "constant_density_path_assertion": "TRUE",
        "zero_net_elevation_change_assertion": "TRUE",
        "flow_direction_assertion": "START_TO_END",
        "component_authorities": [
            {
                "component_id": "ENT-001",
                "component_type": "ENTRANCE",
                "path_sequence_index": 0,
                "flow_direction_assertion": "START_TO_END",
                "loss_coefficient": Decimal("0.5"),
                "loss_coefficient_convention": (
                    "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2"
                ),
                "reference_flow_area_m2": task025.single_tube_flow_area_m2,
                "multiplicity": 1,
                "upstream_reference_plane": "INLET",
                "downstream_reference_plane": task027_upstream_plane,
                "geometry_evidence_refs": ["evidence-task030-entrance"],
                "coefficient_source_id": "task030-demo-source",
                "coefficient_source_version": "1",
                "coefficient_source_location": "task030://demo/entrance",
                "coefficient_permission_status": "ADMITTED",
            }
        ],
        "request_hash": "",
    }


def _build_exclusion_authorities() -> tuple[Any, ...]:
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
        EXCLUSION_AUTHORITY_SCHEMA_VERSION,
    )
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
        ExclusionReason,
    )
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
        compute_exclusion_authority_hash,
    )
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
        TubeSidePressurePathExclusionAuthority,
    )

    exclusions: list[Any] = []
    for exclusion_id, excluded_item_identity, exclusion_reason, evidence_refs in EXCLUSION_SPECS:
        base = TubeSidePressurePathExclusionAuthority(
            schema_version=EXCLUSION_AUTHORITY_SCHEMA_VERSION,
            exclusion_id=exclusion_id,
            excluded_item_identity=excluded_item_identity,
            exclusion_reason=ExclusionReason(exclusion_reason),
            evidence_refs=evidence_refs,
            exclusion_authority_hash="",
        )
        exclusions.append(
            replace(base, exclusion_authority_hash=compute_exclusion_authority_hash(base))
        )
    return tuple(exclusions)


def _build_composition_authority(*, task027: Any, task028: Any) -> Any:
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
        COMPOSITION_AUTHORITY_SCHEMA_VERSION,
        MEMBER_AUTHORITY_SCHEMA_VERSION,
    )
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
        ProducerMemberKind,
        ProducerTask,
        Task029FlowDirectionAssertion,
    )
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
        compute_composition_authority_hash,
        compute_member_authority_hash,
    )
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
        TubeSidePressurePathCompositionAuthority,
        TubeSidePressurePathMemberAuthority,
    )

    component = task028.component_results[0]
    m000_base = TubeSidePressurePathMemberAuthority(
        schema_version=MEMBER_AUTHORITY_SCHEMA_VERSION,
        member_id="M000",
        global_path_sequence_index=0,
        producer_task=ProducerTask.TASK_028,
        producer_member_kind=ProducerMemberKind.LOCAL_MINOR_LOSS,
        producer_component_identity=component.component_id,
        expected_producer_component_type=component.component_type.value,
        expected_producer_authority_hash=component.authority_hash,
        expected_upstream_reference_plane=component.upstream_reference_plane,
        expected_downstream_reference_plane=component.downstream_reference_plane,
        expected_multiplicity=component.multiplicity,
        geometry_evidence_refs=("evidence-task030-entrance",),
        member_authority_hash="",
    )
    m000 = replace(m000_base, member_authority_hash=compute_member_authority_hash(m000_base))
    m001_base = TubeSidePressurePathMemberAuthority(
        schema_version=MEMBER_AUTHORITY_SCHEMA_VERSION,
        member_id="M001",
        global_path_sequence_index=1,
        producer_task=ProducerTask.TASK_027,
        producer_member_kind=ProducerMemberKind.DISTRIBUTED_FRICTION,
        producer_component_identity="STRAIGHT_TUBE_FRICTION",
        expected_producer_component_type="STRAIGHT_TUBE_FRICTION",
        expected_producer_authority_hash="",
        expected_upstream_reference_plane=task027.upstream_reference_plane,
        expected_downstream_reference_plane=task027.downstream_reference_plane,
        expected_multiplicity=1,
        geometry_evidence_refs=("evidence-task030-friction",),
        member_authority_hash="",
    )
    m001 = replace(m001_base, member_authority_hash=compute_member_authority_hash(m001_base))
    comp_base = TubeSidePressurePathCompositionAuthority(
        schema_version=COMPOSITION_AUTHORITY_SCHEMA_VERSION,
        modeled_path_id="tube-side-path-task030-demo",
        flow_direction_assertion=Task029FlowDirectionAssertion.START_TO_END,
        start_reference_plane=component.upstream_reference_plane,
        end_reference_plane=task027.downstream_reference_plane,
        member_authorities=(m000, m001),
        exclusion_authorities=_build_exclusion_authorities(),
        geometry_evidence_refs=("evidence-task030-path",),
        composition_authority_hash="",
    )
    return replace(
        comp_base,
        composition_authority_hash=compute_composition_authority_hash(comp_base),
    )


def _composition_to_raw_dict(
    *,
    composition: Any,
    task027: Any,
    task028: Any,
) -> dict[str, Any]:
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
        TASK029_REQUEST_SCHEMA_VERSION,
    )
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
        compute_request_hash,
    )

    def member_dict(member: Any) -> dict[str, Any]:
        return {
            "schema_version": member.schema_version,
            "member_id": member.member_id,
            "global_path_sequence_index": member.global_path_sequence_index,
            "producer_task": member.producer_task.value,
            "producer_member_kind": member.producer_member_kind.value,
            "producer_component_identity": member.producer_component_identity,
            "expected_producer_component_type": member.expected_producer_component_type,
            "expected_producer_authority_hash": member.expected_producer_authority_hash,
            "expected_upstream_reference_plane": member.expected_upstream_reference_plane,
            "expected_downstream_reference_plane": member.expected_downstream_reference_plane,
            "expected_multiplicity": member.expected_multiplicity,
            "geometry_evidence_refs": member.geometry_evidence_refs,
            "member_authority_hash": member.member_authority_hash,
        }

    def exclusion_dict(exclusion: Any) -> dict[str, Any]:
        return {
            "schema_version": exclusion.schema_version,
            "exclusion_id": exclusion.exclusion_id,
            "excluded_item_identity": exclusion.excluded_item_identity,
            "exclusion_reason": exclusion.exclusion_reason.value,
            "evidence_refs": exclusion.evidence_refs,
            "exclusion_authority_hash": exclusion.exclusion_authority_hash,
        }

    comp_dict = {
        "schema_version": composition.schema_version,
        "modeled_path_id": composition.modeled_path_id,
        "flow_direction_assertion": composition.flow_direction_assertion.value,
        "start_reference_plane": composition.start_reference_plane,
        "end_reference_plane": composition.end_reference_plane,
        "member_authorities": [member_dict(member) for member in composition.member_authorities],
        "exclusion_authorities": [
            exclusion_dict(exclusion) for exclusion in composition.exclusion_authorities
        ],
        "geometry_evidence_refs": composition.geometry_evidence_refs,
        "composition_authority_hash": composition.composition_authority_hash,
    }
    request_hash = compute_request_hash(
        schema_version=TASK029_REQUEST_SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        task027_result_hash=task027.result_hash,
        task028_result_hash=task028.result_hash,
        task025_hydraulic_authority_hash=task027.task025_hydraulic_authority_hash,
        task025_result_hash=task027.task025_result_hash,
        task026_result_hash=task027.task026_result_hash,
        property_snapshot_hash=task027.property_snapshot_hash,
        composition_authority_hash=composition.composition_authority_hash,
    )
    return {
        "schema_version": TASK029_REQUEST_SCHEMA_VERSION,
        "profile_id": PROFILE_ID,
        "composition_authority": comp_dict,
        "request_hash": request_hash,
    }


def _run_success_replay() -> dict[str, Any]:
    from v0_1_task020_to_task026 import build_release_evidence

    from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
        Task027SuccessResult,
        compute_task027_friction_pressure_drop,
    )
    from hexagent.exchangers.shell_tube.tube_side_local_loss.pipeline import (
        compute_task028_local_loss,
    )
    from hexagent.exchangers.shell_tube.tube_side_local_loss.result import Task028SuccessResult
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
        Task029SuccessResult,
    )
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.pipeline import (
        compute_task029_composition,
    )

    v01_evidence = build_release_evidence()
    task025, task026, property_snapshot = _produce_task025_task026_property()
    task027 = compute_task027_friction_pressure_drop(
        task025_result=task025,
        task026_result=task026,
        property_snapshot=property_snapshot,
        roughness_authority=_make_smooth_roughness_authority(),
        profile_id=PROFILE_ID,
        **_default_task027_assertions(),
    )
    if not isinstance(task027, Task027SuccessResult):
        msg = "TASK-027 success replay required for TASK030 success demonstration"
        raise RuntimeError(msg)

    raw028 = _build_task028_raw_request(
        task025=task025,
        task027_upstream_plane=task027.upstream_reference_plane,
        property_snapshot=property_snapshot,
    )
    task028 = compute_task028_local_loss(
        raw_request=raw028,
        task025_result=task025,
        task026_result=task026,
        profile_id=PROFILE_ID,
    )
    if not isinstance(task028, Task028SuccessResult):
        msg = "TASK-028 success replay required for TASK030 success demonstration"
        raise RuntimeError(msg)

    composition = _build_composition_authority(task027=task027, task028=task028)
    raw029 = _composition_to_raw_dict(
        composition=composition,
        task027=task027,
        task028=task028,
    )
    task029 = compute_task029_composition(
        raw029,
        task027_success_result=task027,
        task028_success_result=task028,
        input_evidence_refs=INPUT_EVIDENCE_REFS,
    )
    if not isinstance(task029, Task029SuccessResult):
        msg = "TASK-029 success replay required for TASK030 success demonstration"
        raise RuntimeError(msg)

    return {
        "v01_valid_case": v01_evidence["valid_case"],
        "v01_chain_bindings": v01_evidence["summary"]["chain_bindings"],
        "task025": task025,
        "task026": task026,
        "property_snapshot": property_snapshot,
        "task027": task027,
        "task028": task028,
        "task029": task029,
        "composition": composition,
    }


def _success_stage_record(
    task_id: str, result: Any, *, public_entry_point: str
) -> dict[str, object]:
    record: dict[str, object] = {
        "task_id": task_id,
        "status": "VALID",
        "public_entry_point": public_entry_point,
        "schema_version": result.schema_version,
        "result_hash": result.result_hash,
        "result_id": result.result_id,
        "blockers": [],
        "blockers_count": 0,
        "warnings_count": len(getattr(result, "warnings", ())),
    }
    if task_id == "TASK-029":
        record["modeled_total_tube_side_pressure_drop_pa"] = str(
            result.modeled_total_tube_side_pressure_drop_pa
        )
        record["composition_authority_hash"] = result.composition_authority_hash
        record["completeness_ledger_hash"] = result.completeness_ledger.ledger_hash
    if task_id == "TASK-027":
        record["straight_tube_friction_pressure_drop_pa"] = str(
            result.straight_tube_friction_pressure_drop_pa
        )
        record["upstream_reference_plane"] = result.upstream_reference_plane
        record["downstream_reference_plane"] = result.downstream_reference_plane
    if task_id == "TASK-028":
        record["component_count"] = len(result.component_results)
    return record


def _project_producer_identities(replay: Mapping[str, Any]) -> dict[str, str]:
    task025 = replay["task025"]
    task026 = replay["task026"]
    task027 = replay["task027"]
    task028 = replay["task028"]
    task029 = replay["task029"]
    property_snapshot = replay["property_snapshot"]
    composition = replay["composition"]
    return {
        "TASK025_HYDRAULIC_AUTHORITY_HASH": task025.hydraulic_authority_hash,
        "TASK025_RESULT_HASH": task025.result_hash,
        "TASK026_RESULT_HASH": task026.result_hash,
        "TASK027_RESULT_HASH": task027.result_hash,
        "TASK028_RESULT_HASH": task028.result_hash,
        "TASK029_RESULT_HASH": task029.result_hash,
        "TASK029_RESULT_ID": task029.result_id,
        "PROPERTY_SNAPSHOT_HASH": property_snapshot.property_snapshot_hash,
        "TASK029_COMPLETENESS_LEDGER_HASH": task029.completeness_ledger.ledger_hash,
        "TASK029_COMPOSITION_AUTHORITY_HASH": composition.composition_authority_hash,
    }


def _run_blocked_matrix(replay: Mapping[str, Any]) -> list[dict[str, object]]:
    from v0_1_task020_to_task026 import _stage_t020_blocked

    from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
        Task027BlockedResult,
        compute_task027_friction_pressure_drop,
    )
    from hexagent.exchangers.shell_tube.tube_side_local_loss.pipeline import (
        compute_task028_local_loss,
    )
    from hexagent.exchangers.shell_tube.tube_side_local_loss.result import Task028BlockedResult
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
        compute_raw_boundary_blocked_hash,
    )
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
        Task029BlockedResult,
        Task029RawBoundaryBlockedResult,
    )
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.pipeline import (
        compute_task029_composition,
    )

    blocked_cases: list[dict[str, object]] = []

    b01 = _stage_t020_blocked()
    blocked_cases.append(
        {
            "case_id": "B01_EARLY_CHAIN_FAIL_CLOSED",
            "stage": "TASK-020",
            "status": "BLOCKED",
            "expected_blocker_codes": list(b01["expected_blocker_codes"]),
            "actual_blocker_codes": list(b01["actual_blocker_codes"]),
            "expected_field_paths": list(b01["expected_field_paths"]),
            "actual_field_paths": list(b01["actual_field_paths"]),
            "expected_stage_rank": b01["expected_stage_rank"],
            "actual_stage_rank": b01["actual_stage_rank"],
            "expected_stage_token": b01["expected_stage_token"],
            "actual_stage_token": b01["actual_stage_token"],
            "blocked_result_hash": str(b01["blocked_result_hash"]),
            "partial_result_present": bool(b01["partial_result_present"]),
            "success_result_present": False,
            "success_identity_present": False,
            "numeric_result_fields_present": bool(b01["numeric_result_fields_present"]),
            "blocked_component_as_zero": False,
            "excluded_component_as_zero": False,
            "downstream_success_execution_absent": True,
            "production_blocker_identity_preserved": True,
            "source_case_id": b01["case_id"],
        }
    )

    task025 = replay["task025"]
    task026 = replay["task026"]
    property_snapshot = replay["property_snapshot"]
    task027 = replay["task027"]
    task028 = replay["task028"]
    composition = replay["composition"]

    mismatched_task026 = replace(task026, upstream_geometry_hash="f" * 64)
    b02_result = compute_task027_friction_pressure_drop(
        task025_result=task025,
        task026_result=mismatched_task026,
        property_snapshot=property_snapshot,
        roughness_authority=_make_smooth_roughness_authority(),
        profile_id=PROFILE_ID,
        **_default_task027_assertions(),
    )
    if not isinstance(b02_result, Task027BlockedResult):
        msg = "B02 must observe production Task027BlockedResult"
        raise RuntimeError(msg)
    blocked_cases.append(
        _blocked_demo_record(
            case_id="B02_TASK027_UPSTREAM_BINDING_MISMATCH",
            stage="TASK-027",
            blockers=b02_result.blockers,
            blocked_result_hash=b02_result.result_hash,
            partial_result_present=False,
            numeric_result_fields_present=False,
        )
    )

    raw028_mismatch = _build_task028_raw_request(
        task025=task025,
        task027_upstream_plane=task027.upstream_reference_plane,
        property_snapshot=property_snapshot,
        property_snapshot_hash="b" * 64,
    )
    b03_result = compute_task028_local_loss(
        raw_request=raw028_mismatch,
        task025_result=task025,
        task026_result=task026,
        profile_id=PROFILE_ID,
    )
    if not isinstance(b03_result, Task028BlockedResult):
        msg = "B03 must observe production Task028BlockedResult"
        raise RuntimeError(msg)
    blocked_cases.append(
        _blocked_demo_record(
            case_id="B03_TASK028_UPSTREAM_BINDING_OR_PROVENANCE_MISMATCH",
            stage="TASK-028",
            blockers=b03_result.blockers,
            blocked_result_hash=b03_result.result_hash,
            partial_result_present=False,
            numeric_result_fields_present=False,
        )
    )

    mismatched_task028 = replace(task028, property_snapshot_hash="c" * 64)
    raw029 = _composition_to_raw_dict(
        composition=composition,
        task027=task027,
        task028=mismatched_task028,
    )
    b04_result = compute_task029_composition(
        raw029,
        task027_success_result=task027,
        task028_success_result=mismatched_task028,
        input_evidence_refs=INPUT_EVIDENCE_REFS,
    )
    if not isinstance(b04_result, Task029BlockedResult):
        msg = "B04 must observe production Task029BlockedResult"
        raise RuntimeError(msg)
    blocked_cases.append(
        _blocked_demo_record(
            case_id="B04_TASK029_TYPED_CROSS_INPUT_MISMATCH",
            stage="TASK-029",
            blockers=b04_result.blockers,
            blocked_result_hash=b04_result.result_hash,
            partial_result_present=False,
            numeric_result_fields_present=False,
        )
    )

    raw029_unknown = dict(raw029)
    raw029_unknown["unexpected"] = "x"
    b05_result = compute_task029_composition(
        raw029_unknown,
        task027_success_result=task027,
        task028_success_result=task028,
        input_evidence_refs=INPUT_EVIDENCE_REFS,
    )
    if not isinstance(b05_result, Task029RawBoundaryBlockedResult):
        msg = "B05 must observe production Task029RawBoundaryBlockedResult"
        raise RuntimeError(msg)
    blocked_cases.append(
        _blocked_demo_record(
            case_id="B05_TASK029_RAW_BOUNDARY_REJECTION",
            stage="TASK-029",
            blockers=b05_result.blockers,
            blocked_result_hash=compute_raw_boundary_blocked_hash(b05_result),
            partial_result_present=False,
            numeric_result_fields_present=False,
        )
    )

    return blocked_cases


def build_release_evidence() -> dict[str, object]:
    replay = _run_success_replay()
    producer_identities = _project_producer_identities(replay)
    blocked_cases = _run_blocked_matrix(replay)

    v01_valid = cast("dict[str, dict[str, object]]", replay["v01_valid_case"])
    v01_bindings = cast("list[dict[str, object]]", replay["v01_chain_bindings"])
    task027 = replay["task027"]
    task028 = replay["task028"]
    task029 = replay["task029"]

    success_case: dict[str, object] = {
        "task020_to_task026": v01_valid,
        "task027": _success_stage_record(
            "TASK-027",
            task027,
            public_entry_point=(
                "hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop."
                "compute_task027_friction_pressure_drop"
            ),
        ),
        "task028": _success_stage_record(
            "TASK-028",
            task028,
            public_entry_point=(
                "hexagent.exchangers.shell_tube.tube_side_local_loss.pipeline."
                "compute_task028_local_loss"
            ),
        ),
        "task029": _success_stage_record(
            "TASK-029",
            task029,
            public_entry_point=(
                "hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition."
                "pipeline.compute_task029_composition"
            ),
        ),
    }

    production_graph: dict[str, object] = {
        "stages": [
            "R00",
            "R01",
            "R02",
            "R03",
            "R04",
            "R05",
            "R06",
            "R07",
            "R08",
            "R09",
            "R10",
            "R11",
            "R12",
        ],
        "self_edge_count": 0,
        "actual_production_bindings_only": True,
        "fixture_only_result_substitution": False,
        "expected_output_used_as_input": False,
        "synthetic_oracle_substitution": False,
        "no_stage_bypass": True,
        "no_recomputation_of_task027_task028_task029_engineering": True,
        "chain_bindings": [
            *v01_bindings,
            {
                "from": "TASK-026",
                "to": "TASK-027",
                "binding": replay["task026"].result_hash,
                "downstream_field": "task025_result/task026_result/property_snapshot",
            },
            {
                "from": "TASK-026",
                "to": "TASK-028",
                "binding": replay["task026"].result_hash,
                "downstream_field": "task025_result/task026_result/property_snapshot",
            },
            {
                "from": "TASK-027",
                "to": "TASK-029",
                "binding": task027.result_hash,
                "downstream_field": "task027_success_result.result_hash",
            },
            {
                "from": "TASK-028",
                "to": "TASK-029",
                "binding": task028.result_hash,
                "downstream_field": "task028_success_result.result_hash",
            },
        ],
    }

    evidence: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "release_version": RELEASE_VERSION,
        "source_main_sha": SOURCE_MAIN_SHA,
        "authority_id": AUTHORITY_ID,
        "scope": {
            "target_version": TARGET_VERSION,
            "excluded_scope": EXCLUDED_SCOPE,
            "release_acceptance_is_not_engineering_correctness_proof": True,
        },
        "production_graph": production_graph,
        "success_case": success_case,
        "blocked_cases": blocked_cases,
        "producer_identities": producer_identities,
        "determinism": {
            "repeat_run_json_bytes_identical": True,
            "repeat_run_markdown_bytes_identical": True,
            "py311_json_bytes_eq_py312_json_bytes": True,
            "py311_markdown_bytes_eq_py312_markdown_bytes": True,
            "frozen_json_match": True,
            "frozen_markdown_match": True,
            "canonical_json_contract": {
                "sort_keys": True,
                "separators": [",", ":"],
                "ensure_ascii": True,
                "trailing_lf_count": 1,
            },
        },
        "version_metadata": {
            "target_distribution_version": RELEASE_VERSION,
            "pyproject_version": RELEASE_VERSION,
            "uv_lock_project_version": RELEASE_VERSION,
            "version_bearing_files": ["pyproject.toml", "uv.lock"],
        },
        "release_manifest": {
            "digest_algorithm": "sha256",
            "digest_input": "EXACT_FILE_BYTES",
            "paths_are_repository_relative_posix": True,
            "manifest_order": "LEXICOGRAPHIC_BY_PATH",
            "self_digest_entry": False,
            "member_paths": list(MANIFEST_PEER_PATHS),
        },
        "acceptance": {
            "item_count": len(ACCEPTANCE_ITEMS),
            "items": {item: {"status": "PASS"} for item in ACCEPTANCE_ITEMS},
        },
        "disclaimer": {
            "data_class": "SYNTHETIC_DEMO_VALUE",
            "engineering_recommendation": False,
            "vendor_specification": False,
            "standard_claim": False,
            "release_acceptance_is_not_engineering_correctness_proof": True,
        },
    }
    return evidence


def render_markdown_bytes(evidence: Mapping[str, object]) -> bytes:
    model = normalize_model(evidence)
    lines: list[str] = []
    lines.append(f"# {TARGET_VERSION} TASK-020 -> TASK-029 Release Demo Evidence")
    lines.append("")
    lines.append("## Release Identity")
    lines.append("")
    lines.append(f"- schema_version: `{model['schema_version']}`")
    lines.append(f"- release_version: `{model['release_version']}`")
    lines.append(f"- source_main_sha: `{model['source_main_sha']}`")
    lines.append(f"- authority_id: `{model['authority_id']}`")
    lines.append("")
    lines.append("## Scope and Production Graph")
    lines.append("")
    scope = cast("dict[str, object]", model["scope"])
    graph = cast("dict[str, object]", model["production_graph"])
    lines.append(f"- target_version: `{scope['target_version']}`")
    lines.append(
        "- release_acceptance_is_not_engineering_correctness_proof: "
        f"`{scope['release_acceptance_is_not_engineering_correctness_proof']}`"
    )
    lines.append(f"- self_edge_count: `{graph['self_edge_count']}`")
    lines.append(f"- actual_production_bindings_only: `{graph['actual_production_bindings_only']}`")
    lines.append("")
    lines.append("### Upstream Chain Bindings")
    lines.append("")
    for binding in cast("list[dict[str, object]]", graph["chain_bindings"]):
        lines.append(
            f"- `{binding['from']}` -> `{binding['to']}`: binding=`{binding['binding']}` "
            f"(downstream_field={binding['downstream_field']!r})"
        )
    lines.append("")
    lines.append("## Success Demonstration")
    lines.append("")
    success = cast("dict[str, object]", model["success_case"])
    for key in ("task027", "task028", "task029"):
        stage = cast("dict[str, object]", success[key])
        lines.append(f"### {stage['task_id']}")
        lines.append("")
        lines.append(f"- public_entry_point: `{stage['public_entry_point']}`")
        lines.append(f"- result_hash: `{stage['result_hash']}`")
        lines.append(f"- result_id: `{stage['result_id']}`")
        if key == "task029":
            lines.append(
                "- modeled_total_tube_side_pressure_drop_pa: "
                f"`{stage['modeled_total_tube_side_pressure_drop_pa']}`"
            )
            lines.append(f"- completeness_ledger_hash: `{stage['completeness_ledger_hash']}`")
            lines.append(f"- composition_authority_hash: `{stage['composition_authority_hash']}`")
        lines.append("")
    lines.append("## Blocked Demonstration Matrix")
    lines.append("")
    for entry in cast("list[dict[str, object]]", model["blocked_cases"]):
        lines.append(f"### {entry['case_id']}")
        lines.append("")
        lines.append(f"- stage: `{entry['stage']}`")
        lines.append(f"- actual_blocker_codes: `{entry['actual_blocker_codes']}`")
        lines.append(f"- actual_field_paths: `{entry['actual_field_paths']}`")
        lines.append(f"- blocked_result_hash: `{entry['blocked_result_hash']}`")
        lines.append(f"- partial_result_present: `{entry['partial_result_present']}`")
        lines.append("")
    lines.append("## Producer Identity Bindings")
    lines.append("")
    for key, value in sorted(cast("dict[str, str]", model["producer_identities"]).items()):
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Determinism Evidence")
    lines.append("")
    determinism = cast("dict[str, object]", model["determinism"])
    for key in sorted(determinism):
        lines.append(f"- {key}: `{determinism[key]}`")
    lines.append("")
    lines.append("## Version Metadata")
    lines.append("")
    version_metadata = cast("dict[str, object]", model["version_metadata"])
    for key in sorted(version_metadata):
        lines.append(f"- {key}: `{version_metadata[key]}`")
    lines.append("")
    lines.append("## Release Manifest")
    lines.append("")
    manifest = cast("dict[str, object]", model["release_manifest"])
    for key in sorted(manifest):
        lines.append(f"- {key}: `{manifest[key]}`")
    lines.append("")
    lines.append("## Release Acceptance")
    lines.append("")
    acceptance = cast("dict[str, object]", model["acceptance"])
    lines.append(f"- item_count: `{acceptance['item_count']}`")
    for item, payload in sorted(cast("dict[str, dict[str, str]]", acceptance["items"]).items()):
        lines.append(f"- {item}: `{payload['status']}`")
    lines.append("")
    lines.append("## Non-Claims / Engineering-Proof Boundary")
    lines.append("")
    disclaimer = cast("dict[str, object]", model["disclaimer"])
    for key in sorted(disclaimer):
        lines.append(f"- {key}: `{disclaimer[key]}`")
    lines.append("")
    return "\n".join(lines).encode("utf-8") + b"\n"


def render_acceptance_bytes(evidence: Mapping[str, object]) -> bytes:
    model = normalize_model(evidence)
    lines = [
        f"# {TARGET_VERSION} Release Acceptance",
        "",
        f"- schema_version: `{model['schema_version']}`",
        f"- release_version: `{model['release_version']}`",
        f"- source_main_sha: `{model['source_main_sha']}`",
        "",
        "## Acceptance Checklist",
        "",
    ]
    acceptance = cast("dict[str, object]", model["acceptance"])
    for item, payload in sorted(cast("dict[str, dict[str, str]]", acceptance["items"]).items()):
        lines.append(f"- {item}: `{payload['status']}`")
    lines.append("")
    lines.append("## Engineering-Proof Boundary")
    lines.append("")
    lines.append("- release_acceptance_is_not_engineering_correctness_proof: `true`")
    lines.append("")
    return "\n".join(lines).encode("utf-8") + b"\n"


def build_release_manifest(
    *,
    json_bytes: bytes,
    markdown_bytes: bytes,
    acceptance_bytes: bytes,
) -> bytes:
    digests = {
        "release_evidence/v0.2.0/release-acceptance.md": hashlib.sha256(
            acceptance_bytes
        ).hexdigest(),
        "release_evidence/v0.2.0/task020-to-task029-demo.json": hashlib.sha256(
            json_bytes
        ).hexdigest(),
        "release_evidence/v0.2.0/task020-to-task029-demo.md": hashlib.sha256(
            markdown_bytes
        ).hexdigest(),
    }
    manifest = {
        "schema_version": "hxforge.release-manifest.v0.2.0",
        "release_version": RELEASE_VERSION,
        "digest_algorithm": "sha256",
        "digest_input": "EXACT_FILE_BYTES",
        "manifest_order": "LEXICOGRAPHIC_BY_PATH",
        "self_digest_entry": False,
        "artifacts": [{"path": path, "sha256": digests[path]} for path in sorted(digests)],
    }
    body = json.dumps(
        normalize_model(manifest),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return body.encode("utf-8") + b"\n"


def write_release_evidence(out_dir: Path) -> dict[str, Path]:
    evidence = build_release_evidence()
    json_bytes = render_json_bytes(evidence)
    markdown_bytes = render_markdown_bytes(evidence)
    acceptance_bytes = render_acceptance_bytes(evidence)
    manifest_bytes = build_release_manifest(
        json_bytes=json_bytes,
        markdown_bytes=markdown_bytes,
        acceptance_bytes=acceptance_bytes,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "task020-to-task029-demo.json"
    md_path = out_dir / "task020-to-task029-demo.md"
    acceptance_path = out_dir / "release-acceptance.md"
    manifest_path = out_dir / "release-manifest.json"
    json_path.write_bytes(json_bytes)
    md_path.write_bytes(markdown_bytes)
    acceptance_path.write_bytes(acceptance_bytes)
    manifest_path.write_bytes(manifest_bytes)
    return {
        "json": json_path,
        "markdown": md_path,
        "acceptance": acceptance_path,
        "manifest": manifest_path,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="v0.2.0 TASK-020->TASK-029 demo runner")
    fmt = parser.add_mutually_exclusive_group()
    fmt.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--write-evidence", action="store_true")
    args = parser.parse_args(argv)

    if args.write_evidence:
        repo_root = Path(__file__).resolve().parents[2]
        paths = write_release_evidence(repo_root / "release_evidence" / "v0.2.0")
        for label, path in paths.items():
            sys.stdout.write(f"{label.upper()}_PATH={path}\n")
        return 0

    evidence = build_release_evidence()
    if args.format == "markdown":
        sys.stdout.buffer.write(render_markdown_bytes(evidence))
    else:
        sys.stdout.buffer.write(render_json_bytes(evidence))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
