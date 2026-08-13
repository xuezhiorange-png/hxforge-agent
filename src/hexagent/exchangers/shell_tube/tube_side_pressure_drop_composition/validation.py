"""TASK-029 typed validation stage primitives.

I07 / T05: composition authority tree and hash replay validation.
I12 / T07: direction, multiplicity, convention, and pressure contribution validation.
"""

from __future__ import annotations

from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.blocker_registry import (
    collapse_blockers,
    emit_blocker,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
    COMPOSITION_AUTHORITY_SCHEMA_VERSION,
    EXCLUSION_AUTHORITY_SCHEMA_VERSION,
    MEMBER_AUTHORITY_SCHEMA_VERSION,
    sort_evidence_refs,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.composition import (
    extract_pressure_contribution,
    pressure_contribution_field_path,
    validate_bound_member_producer_convention,
    validate_bound_member_task028_component_direction,
    validate_contribution,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    ExclusionReason,
    ProducerComponentIdentity,
    ProducerMemberKind,
    ProducerTask,
    Task029BlockerCode,
    Task029FlowDirectionAssertion,
    Task029InScopeComponentType,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
    compute_composition_authority_hash,
    compute_member_authority_hash,
    compute_request_hash,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029BlockerEntry,
    Task029Request,
    TubeSidePressurePathCompositionAuthority,
    TubeSidePressurePathExclusionAuthority,
    TubeSidePressurePathMemberAuthority,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.path_binding import (
    BoundPressurePathMember,
    validate_bound_members_multiplicity,
)

_TASK029_IN_SCOPE_COMPONENT_TYPES: frozenset[str] = frozenset(
    component_type.value for component_type in Task029InScopeComponentType
)


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and value != ""


def _is_hash_string(value: object) -> bool:
    return isinstance(value, str) and value != ""


def _is_exact_int(value: object) -> bool:
    return type(value) is int


def _is_exact_tuple(value: object) -> bool:
    return type(value) is tuple


def _refs_are_canonical_sorted(refs: tuple[str, ...]) -> bool:
    return refs == sort_evidence_refs(refs)


def _refs_are_non_empty_unique_sorted(refs: tuple[str, ...]) -> bool:
    if not refs:
        return False
    if len(set(refs)) != len(refs):
        return False
    return _refs_are_canonical_sorted(refs)


def _validate_exclusion_structure(exclusion: object) -> bool:
    if type(exclusion) is not TubeSidePressurePathExclusionAuthority:
        return False
    if exclusion.schema_version != EXCLUSION_AUTHORITY_SCHEMA_VERSION:
        return False
    if not _is_non_empty_string(exclusion.exclusion_id):
        return False
    if not _is_non_empty_string(exclusion.excluded_item_identity):
        return False
    if type(exclusion.exclusion_reason) is not ExclusionReason:
        return False
    if not _is_exact_tuple(exclusion.evidence_refs):
        return False
    if not all(_is_non_empty_string(ref) for ref in exclusion.evidence_refs):
        return False
    return _is_hash_string(exclusion.exclusion_authority_hash)


def _validate_member_branch_rules(member: TubeSidePressurePathMemberAuthority) -> bool:
    if member.producer_task == ProducerTask.TASK_027:
        return (
            member.producer_member_kind == ProducerMemberKind.DISTRIBUTED_FRICTION
            and member.producer_component_identity
            == ProducerComponentIdentity.STRAIGHT_TUBE_FRICTION.value
            and member.expected_producer_component_type
            == ProducerComponentIdentity.STRAIGHT_TUBE_FRICTION.value
            and member.expected_producer_authority_hash == ""
            and member.expected_multiplicity == 1
        )
    if member.producer_task == ProducerTask.TASK_028:
        return member.producer_member_kind == ProducerMemberKind.LOCAL_MINOR_LOSS
    return False


def _validate_member_structure(member: object) -> bool:
    if type(member) is not TubeSidePressurePathMemberAuthority:
        return False
    if member.schema_version != MEMBER_AUTHORITY_SCHEMA_VERSION:
        return False
    if not _is_non_empty_string(member.member_id):
        return False
    if not _is_exact_int(member.global_path_sequence_index):
        return False
    if member.global_path_sequence_index < 0:
        return False
    if type(member.producer_task) is not ProducerTask:
        return False
    if type(member.producer_member_kind) is not ProducerMemberKind:
        return False
    if not _is_non_empty_string(member.producer_component_identity):
        return False
    if not _is_non_empty_string(member.expected_producer_component_type):
        return False
    if member.producer_task == ProducerTask.TASK_027:
        if (
            member.expected_producer_component_type
            != ProducerComponentIdentity.STRAIGHT_TUBE_FRICTION.value
        ):
            return False
    elif member.producer_task == ProducerTask.TASK_028:
        if member.expected_producer_component_type not in _TASK029_IN_SCOPE_COMPONENT_TYPES:
            return False
    else:
        return False
    if not isinstance(member.expected_producer_authority_hash, str):
        return False
    if not _is_non_empty_string(member.expected_upstream_reference_plane):
        return False
    if not _is_non_empty_string(member.expected_downstream_reference_plane):
        return False
    if member.expected_upstream_reference_plane == member.expected_downstream_reference_plane:
        return False
    if not _is_exact_int(member.expected_multiplicity):
        return False
    if member.expected_multiplicity < 1:
        return False
    if not _is_exact_tuple(member.geometry_evidence_refs):
        return False
    if not _refs_are_non_empty_unique_sorted(member.geometry_evidence_refs):
        return False
    if not _is_hash_string(member.member_authority_hash):
        return False
    return _validate_member_branch_rules(member)


def _validate_composition_structure(
    authority: TubeSidePressurePathCompositionAuthority,
) -> bool:
    if authority.schema_version != COMPOSITION_AUTHORITY_SCHEMA_VERSION:
        return False
    if not _is_non_empty_string(authority.modeled_path_id):
        return False
    if type(authority.flow_direction_assertion) is not Task029FlowDirectionAssertion:
        return False
    if not _is_non_empty_string(authority.start_reference_plane):
        return False
    if not _is_non_empty_string(authority.end_reference_plane):
        return False
    if authority.start_reference_plane == authority.end_reference_plane:
        return False
    if not _is_exact_tuple(authority.member_authorities):
        return False
    if not _is_exact_tuple(authority.exclusion_authorities):
        return False
    if not _is_exact_tuple(authority.geometry_evidence_refs):
        return False
    if not _refs_are_non_empty_unique_sorted(authority.geometry_evidence_refs):
        return False
    if not _is_hash_string(authority.composition_authority_hash):
        return False
    for member in authority.member_authorities:
        if not _validate_member_structure(member):
            return False
    for exclusion in authority.exclusion_authorities:
        if not _validate_exclusion_structure(exclusion):
            return False
    return True


def T05_VALIDATE_COMPOSITION_AUTHORITY_TREE_AND_HASHES(
    *,
    schema_version: str,
    profile_id: str,
    request_hash: str,
    composition_authority: object | None,
    task027_result_hash: str,
    task028_result_hash: str,
    task025_hydraulic_authority_hash: str,
    task025_result_hash: str,
    task026_result_hash: str,
    property_snapshot_hash: str,
) -> tuple[Task029BlockerEntry, ...]:
    """Validate composition authority tree structure and replay authority hashes."""
    blockers: list[Task029BlockerEntry] = []

    if composition_authority is None:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_COMPOSITION_AUTHORITY_MISSING,
                "composition_authority",
            )
        )
        return collapse_blockers(blockers)

    if type(composition_authority) is not TubeSidePressurePathCompositionAuthority:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_COMPOSITION_AUTHORITY_MALFORMED,
                "composition_authority",
            )
        )
        return collapse_blockers(blockers)

    authority = composition_authority

    structure_safe = _validate_composition_structure(authority)
    if not structure_safe:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_COMPOSITION_AUTHORITY_MALFORMED,
                "composition_authority",
            )
        )
        return collapse_blockers(blockers)

    for index, member in enumerate(authority.member_authorities):
        replayed_member_hash = compute_member_authority_hash(member)
        if replayed_member_hash != member.member_authority_hash:
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_COMPOSITION_MEMBER_AUTHORITY_HASH_MISMATCH,
                    f"composition_authority.member_authorities[{index}].member_authority_hash",
                )
            )

    replayed_composition_hash = compute_composition_authority_hash(authority)
    if replayed_composition_hash != authority.composition_authority_hash:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_COMPOSITION_AUTHORITY_HASH_MISMATCH,
                "composition_authority.composition_authority_hash",
            )
        )

    replayed_request_hash = compute_request_hash(
        schema_version=schema_version,
        profile_id=profile_id,
        task027_result_hash=task027_result_hash,
        task028_result_hash=task028_result_hash,
        task025_hydraulic_authority_hash=task025_hydraulic_authority_hash,
        task025_result_hash=task025_result_hash,
        task026_result_hash=task026_result_hash,
        property_snapshot_hash=property_snapshot_hash,
        composition_authority_hash=authority.composition_authority_hash,
    )
    if replayed_request_hash != request_hash:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_REQUEST_HASH_MISMATCH,
                "request_hash",
            )
        )

    return collapse_blockers(blockers)


def T07_VALIDATE_DIRECTION_MULTIPLICITY_CONVENTION_PRESSURE(
    *,
    composition_authority: TubeSidePressurePathCompositionAuthority,
    bound_members: tuple[BoundPressurePathMember, ...],
) -> tuple[Task029BlockerEntry, ...]:
    """Validate direction, multiplicity, K convention, and pressure contributions."""
    blockers: list[Task029BlockerEntry] = []

    if composition_authority.flow_direction_assertion != Task029FlowDirectionAssertion.START_TO_END:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_FLOW_DIRECTION_MISMATCH,
                "composition_authority.flow_direction_assertion",
            )
        )

    for bound_member in bound_members:
        blockers.extend(validate_bound_member_task028_component_direction(bound_member))

    blockers.extend(validate_bound_members_multiplicity(bound_members))

    for bound_member in bound_members:
        blockers.extend(validate_bound_member_producer_convention(bound_member))

        if bound_member.producer_task == ProducerTask.TASK_027:
            if bound_member.task027_replay_evidence is None:
                continue
        elif bound_member.producer_task == ProducerTask.TASK_028:
            if bound_member.task028_component_result is None:
                continue
        else:
            continue

        try:
            contribution = extract_pressure_contribution(bound_member)
        except ValueError:
            continue

        blockers.extend(
            validate_contribution(
                contribution,
                field_path=pressure_contribution_field_path(bound_member),
            )
        )

    return collapse_blockers(blockers)


def validate_composition_authority_tree_and_hashes(
    request: Task029Request,
) -> tuple[Task029BlockerEntry, ...]:
    """T05 stage entry using a typed TASK-029 request."""
    return T05_VALIDATE_COMPOSITION_AUTHORITY_TREE_AND_HASHES(
        schema_version=request.schema_version,
        profile_id=request.profile_id,
        request_hash=request.request_hash,
        composition_authority=request.composition_authority,
        task027_result_hash=request.task027_success_result.result_hash,
        task028_result_hash=request.task028_success_result.result_hash,
        task025_hydraulic_authority_hash=request.task027_success_result.task025_hydraulic_authority_hash,
        task025_result_hash=request.task027_success_result.task025_result_hash,
        task026_result_hash=request.task027_success_result.task026_result_hash,
        property_snapshot_hash=request.task027_success_result.property_snapshot_hash,
    )


__all__ = [
    "T05_VALIDATE_COMPOSITION_AUTHORITY_TREE_AND_HASHES",
    "T07_VALIDATE_DIRECTION_MULTIPLICITY_CONVENTION_PRESSURE",
    "validate_composition_authority_tree_and_hashes",
]
