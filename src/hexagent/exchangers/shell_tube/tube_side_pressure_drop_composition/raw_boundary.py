"""TASK-029 raw input boundary validation and typed request transition.

I13H: RAW_S00-S03 structural boundary and RAW_S04 transition via ``build_task029_request``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    Task027SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
    Task028SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.blocker_registry import (
    collapse_blockers,
    emit_blocker,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    ExclusionReason,
    ProducerMemberKind,
    ProducerTask,
    Task029BlockerCode,
    Task029FlowDirectionAssertion,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    FrozenTask029RawProjection,
    Task029BlockerEntry,
    Task029RawBoundaryBlockedResult,
    Task029Request,
    TubeSidePressurePathCompositionAuthority,
    TubeSidePressurePathExclusionAuthority,
    TubeSidePressurePathMemberAuthority,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.raw_projection import (
    encode_raw_projection,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.request import (
    build_task029_request,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.result import (
    build_raw_boundary_blocked_result,
)

_RAW_REQUEST_PROJECTION_KIND: str = "task029.raw-request"

_TOP_LEVEL_FIELDS: frozenset[str] = frozenset(
    {
        "schema_version",
        "profile_id",
        "composition_authority",
        "request_hash",
    }
)

_COMPOSITION_AUTHORITY_FIELDS: frozenset[str] = frozenset(
    {
        "schema_version",
        "modeled_path_id",
        "flow_direction_assertion",
        "start_reference_plane",
        "end_reference_plane",
        "member_authorities",
        "exclusion_authorities",
        "geometry_evidence_refs",
        "composition_authority_hash",
    }
)

_MEMBER_AUTHORITY_FIELDS: frozenset[str] = frozenset(
    {
        "schema_version",
        "member_id",
        "global_path_sequence_index",
        "producer_task",
        "producer_member_kind",
        "producer_component_identity",
        "expected_producer_component_type",
        "expected_producer_authority_hash",
        "expected_upstream_reference_plane",
        "expected_downstream_reference_plane",
        "expected_multiplicity",
        "geometry_evidence_refs",
        "member_authority_hash",
    }
)

_EXCLUSION_AUTHORITY_FIELDS: frozenset[str] = frozenset(
    {
        "schema_version",
        "exclusion_id",
        "excluded_item_identity",
        "exclusion_reason",
        "evidence_refs",
        "exclusion_authority_hash",
    }
)


@dataclass(frozen=True)
class RawBoundaryResult:
    """RAW_S03 blocked path or RAW_S04 typed ``Task029Request`` path."""

    blocked: bool
    blocked_result: Task029RawBoundaryBlockedResult | None
    request: Task029Request | None
    raw_request_projection: FrozenTask029RawProjection


def validate_raw_boundary(
    raw_input: object,
    *,
    task027_success_result: Task027SuccessResult,
    task028_success_result: Task028SuccessResult,
) -> RawBoundaryResult:
    """Validate raw TASK-029 request input and return blocked or typed request."""
    raw_request_projection = encode_raw_projection(_RAW_REQUEST_PROJECTION_KIND, raw_input)
    blockers: list[Task029BlockerEntry] = []

    if type(raw_input) is not dict:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_RAW_INPUT_BOUNDARY_MALFORMED,
                "request",
            )
        )
        return _finalize_blocked(blockers, raw_request_projection)

    blockers.extend(_scan_unknown_fields(raw_input))

    for field_name in _TOP_LEVEL_FIELDS:
        if field_name not in raw_input:
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_REQUIRED_FIELD_MISSING,
                    "request",
                )
            )

    if blockers:
        return _finalize_blocked(blockers, raw_request_projection)

    composition_authority = _parse_composition_authority(raw_input.get("composition_authority"))
    if composition_authority is None:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_RAW_INPUT_BOUNDARY_MALFORMED,
                "request",
            )
        )
        return _finalize_blocked(blockers, raw_request_projection)

    profile_id = raw_input.get("profile_id")
    if type(profile_id) is not str or profile_id == "":
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_RAW_INPUT_BOUNDARY_MALFORMED,
                "request",
            )
        )
        return _finalize_blocked(blockers, raw_request_projection)

    request = build_task029_request(
        profile_id=profile_id,
        task027_success_result=task027_success_result,
        task028_success_result=task028_success_result,
        composition_authority=composition_authority,
    )
    return RawBoundaryResult(
        blocked=False,
        blocked_result=None,
        request=request,
        raw_request_projection=raw_request_projection,
    )


def _finalize_blocked(
    blockers: list[Task029BlockerEntry],
    raw_request_projection: FrozenTask029RawProjection,
) -> RawBoundaryResult:
    collapsed = collapse_blockers(blockers)
    blocked_result = build_raw_boundary_blocked_result(
        raw_request_projection=raw_request_projection,
        blockers=collapsed,
    )
    return RawBoundaryResult(
        blocked=True,
        blocked_result=blocked_result,
        request=None,
        raw_request_projection=raw_request_projection,
    )


def _scan_unknown_fields(raw_input: dict[str, Any]) -> list[Task029BlockerEntry]:
    blockers: list[Task029BlockerEntry] = []
    for key in raw_input:
        if key not in _TOP_LEVEL_FIELDS:
            blockers.append(_unknown_field_blocker(key))

    composition_raw = raw_input.get("composition_authority")
    if type(composition_raw) is dict:
        for key in composition_raw:
            if key not in _COMPOSITION_AUTHORITY_FIELDS:
                blockers.append(_unknown_field_blocker(key))

        members_raw = composition_raw.get("member_authorities")
        if type(members_raw) is tuple or type(members_raw) is list:
            for member_raw in members_raw:
                if type(member_raw) is dict:
                    for key in member_raw:
                        if key not in _MEMBER_AUTHORITY_FIELDS:
                            blockers.append(_unknown_field_blocker(key))

        exclusions_raw = composition_raw.get("exclusion_authorities")
        if type(exclusions_raw) is tuple or type(exclusions_raw) is list:
            for exclusion_raw in exclusions_raw:
                if type(exclusion_raw) is dict:
                    for key in exclusion_raw:
                        if key not in _EXCLUSION_AUTHORITY_FIELDS:
                            blockers.append(_unknown_field_blocker(key))

    return blockers


def _unknown_field_blocker(unknown_key: str) -> Task029BlockerEntry:
    return emit_blocker(
        Task029BlockerCode.BL_T029_REQUEST_UNKNOWN_FIELD,
        "unexpected",
        evidence_refs=(unknown_key,),
    )


def _parse_evidence_refs(value: object) -> tuple[str, ...] | None:
    if type(value) is tuple:
        if all(type(item) is str and item != "" for item in value):
            return value
        return None
    if type(value) is list and all(type(item) is str and item != "" for item in value):
        return tuple(value)
    return None


def _parse_exact_int(value: object) -> int | None:
    if type(value) is int:
        return value
    return None


def _parse_member_authority(value: object) -> TubeSidePressurePathMemberAuthority | None:
    if type(value) is not dict:
        return None
    try:
        global_index = _parse_exact_int(value["global_path_sequence_index"])
        expected_multiplicity = _parse_exact_int(value["expected_multiplicity"])
        geometry_evidence_refs = _parse_evidence_refs(value["geometry_evidence_refs"])
        if global_index is None or expected_multiplicity is None or geometry_evidence_refs is None:
            return None
        return TubeSidePressurePathMemberAuthority(
            schema_version=value["schema_version"],
            member_id=value["member_id"],
            global_path_sequence_index=global_index,
            producer_task=ProducerTask(value["producer_task"]),
            producer_member_kind=ProducerMemberKind(value["producer_member_kind"]),
            producer_component_identity=value["producer_component_identity"],
            expected_producer_component_type=value["expected_producer_component_type"],
            expected_producer_authority_hash=value["expected_producer_authority_hash"],
            expected_upstream_reference_plane=value["expected_upstream_reference_plane"],
            expected_downstream_reference_plane=value["expected_downstream_reference_plane"],
            expected_multiplicity=expected_multiplicity,
            geometry_evidence_refs=geometry_evidence_refs,
            member_authority_hash=value["member_authority_hash"],
        )
    except (KeyError, ValueError):
        return None


def _parse_exclusion_authority(value: object) -> TubeSidePressurePathExclusionAuthority | None:
    if type(value) is not dict:
        return None
    try:
        evidence_refs = _parse_evidence_refs(value["evidence_refs"])
        if evidence_refs is None:
            return None
        return TubeSidePressurePathExclusionAuthority(
            schema_version=value["schema_version"],
            exclusion_id=value["exclusion_id"],
            excluded_item_identity=value["excluded_item_identity"],
            exclusion_reason=ExclusionReason(value["exclusion_reason"]),
            evidence_refs=evidence_refs,
            exclusion_authority_hash=value["exclusion_authority_hash"],
        )
    except (KeyError, ValueError):
        return None


def _parse_member_authorities(
    value: object,
) -> tuple[TubeSidePressurePathMemberAuthority, ...] | None:
    if type(value) is not tuple and type(value) is not list:
        return None
    members: list[TubeSidePressurePathMemberAuthority] = []
    for item in value:
        parsed = _parse_member_authority(item)
        if parsed is None:
            return None
        members.append(parsed)
    return tuple(members)


def _parse_exclusion_authorities(
    value: object,
) -> tuple[TubeSidePressurePathExclusionAuthority, ...] | None:
    if type(value) is not tuple and type(value) is not list:
        return None
    exclusions: list[TubeSidePressurePathExclusionAuthority] = []
    for item in value:
        parsed = _parse_exclusion_authority(item)
        if parsed is None:
            return None
        exclusions.append(parsed)
    return tuple(exclusions)


def _parse_composition_authority(value: object) -> TubeSidePressurePathCompositionAuthority | None:
    if type(value) is not dict:
        return None
    try:
        geometry_evidence_refs = _parse_evidence_refs(value["geometry_evidence_refs"])
        member_authorities = _parse_member_authorities(value["member_authorities"])
        exclusion_authorities = _parse_exclusion_authorities(value["exclusion_authorities"])
        if (
            geometry_evidence_refs is None
            or member_authorities is None
            or exclusion_authorities is None
        ):
            return None
        return TubeSidePressurePathCompositionAuthority(
            schema_version=value["schema_version"],
            modeled_path_id=value["modeled_path_id"],
            flow_direction_assertion=Task029FlowDirectionAssertion(
                value["flow_direction_assertion"]
            ),
            start_reference_plane=value["start_reference_plane"],
            end_reference_plane=value["end_reference_plane"],
            member_authorities=member_authorities,
            exclusion_authorities=exclusion_authorities,
            geometry_evidence_refs=geometry_evidence_refs,
            composition_authority_hash=value["composition_authority_hash"],
        )
    except (KeyError, ValueError):
        return None


__all__ = [
    "RawBoundaryResult",
    "validate_raw_boundary",
]
