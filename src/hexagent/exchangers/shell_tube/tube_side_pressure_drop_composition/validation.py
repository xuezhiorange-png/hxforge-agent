"""TASK-029 typed validation stage primitives and scheduler foundation.

T00-T04 / T06 / T08 / T09: validation stage wrappers and safe accumulation.
T05: composition authority tree and hash replay validation.
T07: direction, multiplicity, convention, and pressure contribution validation.
"""

from __future__ import annotations

from dataclasses import dataclass

from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    Task027BlockedResult,
    Task027RawBoundaryBlockedResult,
    Task027SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
    Task028BlockedResult,
    Task028RawBoundaryBlockedResult,
    Task028SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.blocker_registry import (
    collapse_blockers,
    emit_blocker,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
    COMPOSITION_AUTHORITY_SCHEMA_VERSION,
    EXCLUSION_AUTHORITY_SCHEMA_VERSION,
    MEMBER_AUTHORITY_SCHEMA_VERSION,
    TASK027_ACCEPTED_SCHEMA_VERSION,
    TASK028_ACCEPTED_SCHEMA_VERSION,
    sort_evidence_refs,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.completeness import (
    validate_exclusion_partition_and_completeness,
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
    BindingResult,
    BoundPressurePathMember,
    PathTopologyResult,
    bind_members_to_producers,
    evaluate_path_topology,
    validate_bound_members_multiplicity,
    validate_global_index_domain,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.upstream_replay import (
    Task027ReplayEvidence,
    Task028ReplayEvidence,
    replay_task027_success,
    replay_task028_success,
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


_COMMON_RUNTIME_IDENTITY_FIELDS: tuple[tuple[str, str], ...] = (
    ("task025_hydraulic_authority_hash", "task025_hydraulic_authority_hash"),
    ("task025_result_hash", "task025_result_hash"),
    ("task026_result_hash", "task026_result_hash"),
    ("property_snapshot_hash", "property_snapshot_hash"),
)


@dataclass(frozen=True)
class T01ThroughT09ValidationResult:
    """Package-internal T01-T09 foundation output."""

    blockers: tuple[Task029BlockerEntry, ...]
    bound_members: tuple[BoundPressurePathMember, ...] | None


def _is_task029_blocker_entry(value: object) -> bool:
    return type(value) is Task029BlockerEntry


def _composition_authority_safe_for_binding(
    composition_authority: TubeSidePressurePathCompositionAuthority | None,
) -> bool:
    if composition_authority is None:
        return False
    if type(composition_authority) is not TubeSidePressurePathCompositionAuthority:
        return False
    return _validate_composition_structure(composition_authority)


def T00_ROUTE_UPSTREAM_BLOCKED_AND_REQUIRE_EXACT_TYPES(
    *,
    task027_result: object,
    task028_result: object,
) -> tuple[Task029BlockerEntry, ...]:
    """Route raw/typed blocked upstream variants and require exact success types."""
    blockers: list[Task029BlockerEntry] = []

    if type(task027_result) is Task027RawBoundaryBlockedResult:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_UPSTREAM_TASK027_RAW_BLOCKED,
                "task027_success_result",
            )
        )
    elif type(task027_result) is Task027BlockedResult:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_UPSTREAM_TASK027_TYPED_BLOCKED,
                "task027_success_result",
            )
        )
    elif type(task027_result) is not Task027SuccessResult:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_UPSTREAM_TASK027_TYPE_INVALID,
                "task027_success_result",
            )
        )

    if type(task028_result) is Task028RawBoundaryBlockedResult:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_UPSTREAM_TASK028_RAW_BLOCKED,
                "task028_success_result",
            )
        )
    elif type(task028_result) is Task028BlockedResult:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_UPSTREAM_TASK028_TYPED_BLOCKED,
                "task028_success_result",
            )
        )
    elif type(task028_result) is not Task028SuccessResult:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_UPSTREAM_TASK028_TYPE_INVALID,
                "task028_success_result",
            )
        )

    return collapse_blockers(blockers)


def T01_VALIDATE_UPSTREAM_SCHEMA_VERSIONS(
    *,
    task027_success_result: Task027SuccessResult,
    task028_success_result: Task028SuccessResult,
) -> tuple[Task029BlockerEntry, ...]:
    """Validate accepted TASK-027/TASK-028 schema versions after exact type gating."""
    blockers: list[Task029BlockerEntry] = []

    if task027_success_result.schema_version != TASK027_ACCEPTED_SCHEMA_VERSION:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_UPSTREAM_SCHEMA_VERSION_UNSUPPORTED,
                "task027_success_result.schema_version",
            )
        )

    if task028_success_result.schema_version != TASK028_ACCEPTED_SCHEMA_VERSION:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_UPSTREAM_SCHEMA_VERSION_UNSUPPORTED,
                "task028_success_result.schema_version",
            )
        )

    return collapse_blockers(blockers)


def T02_REPLAY_UPSTREAM_RESULT_HASH_AND_UUID(
    *,
    task027_success_result: Task027SuccessResult,
    task028_success_result: Task028SuccessResult,
    task027_schema_supported: bool,
    task028_schema_supported: bool,
) -> tuple[Task029BlockerEntry, ...]:
    """Replay production upstream hash and UUID evidence for supported schemas."""
    blockers: list[Task029BlockerEntry] = []

    if task027_schema_supported:
        task027_replay = replay_task027_success(task027_success_result)
        if _is_task029_blocker_entry(task027_replay):
            blockers.append(task027_replay)

    if task028_schema_supported:
        task028_replay = replay_task028_success(task028_success_result)
        if _is_task029_blocker_entry(task028_replay):
            blockers.append(task028_replay)

    return collapse_blockers(blockers)


def _extract_task027_replay_evidence(
    replay_result: Task027ReplayEvidence | Task029BlockerEntry,
) -> Task027ReplayEvidence | None:
    if type(replay_result) is Task027ReplayEvidence:
        return replay_result
    return None


def _extract_task028_replay_evidence(
    replay_result: Task028ReplayEvidence | Task029BlockerEntry,
) -> Task028ReplayEvidence | None:
    if type(replay_result) is Task028ReplayEvidence:
        return replay_result
    return None


def T03_VALIDATE_UPSTREAM_SUCCESS_WARNINGS_BLOCKERS(
    *,
    task027_success_result: Task027SuccessResult,
    task028_success_result: Task028SuccessResult,
    task027_schema_supported: bool,
    task028_schema_supported: bool,
) -> tuple[Task029BlockerEntry, ...]:
    """Require empty upstream success warnings and blockers when schema is supported."""
    blockers: list[Task029BlockerEntry] = []

    if task027_schema_supported:
        if task027_success_result.warnings != ():
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_UPSTREAM_SUCCESS_DIAGNOSTICS_NONEMPTY,
                    "task027_success_result.warnings",
                )
            )
        if task027_success_result.blockers != ():
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_UPSTREAM_SUCCESS_DIAGNOSTICS_NONEMPTY,
                    "task027_success_result.blockers",
                )
            )

    if task028_schema_supported:
        if task028_success_result.warnings != ():
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_UPSTREAM_SUCCESS_DIAGNOSTICS_NONEMPTY,
                    "task028_success_result.warnings",
                )
            )
        if task028_success_result.blockers != ():
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_UPSTREAM_SUCCESS_DIAGNOSTICS_NONEMPTY,
                    "task028_success_result.blockers",
                )
            )

    return collapse_blockers(blockers)


def T04_COMPARE_PROFILE_AND_COMMON_IDENTITIES(
    *,
    request_profile_id: str,
    task027_success_result: Task027SuccessResult,
    task028_success_result: Task028SuccessResult,
) -> tuple[Task029BlockerEntry, ...]:
    """Compare request profile and common upstream runtime identity fields."""
    blockers: list[Task029BlockerEntry] = []

    if (
        request_profile_id != task027_success_result.profile_id
        or request_profile_id != task028_success_result.profile_id
    ):
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_PROFILE_MISMATCH,
                "profile_id",
            )
        )

    for attribute_name, field_suffix in _COMMON_RUNTIME_IDENTITY_FIELDS:
        task027_value = getattr(task027_success_result, attribute_name)
        task028_value = getattr(task028_success_result, attribute_name)
        if task027_value == task028_value:
            continue
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_UPSTREAM_IDENTITY_MISMATCH,
                f"task028_success_result.{field_suffix}",
                evidence_refs=sort_evidence_refs((task027_value, task028_value)),
            )
        )

    return collapse_blockers(blockers)


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


def T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS(
    *,
    composition_authority: TubeSidePressurePathCompositionAuthority,
    task027_replay_evidence: Task027ReplayEvidence,
    task028_replay_evidence: Task028ReplayEvidence,
    task027_upstream_reference_plane: str,
    task027_downstream_reference_plane: str,
) -> BindingResult:
    """Bind composition member authorities to trusted TASK-027/TASK-028 replay evidence."""
    blockers: list[Task029BlockerEntry] = []
    blockers.extend(validate_global_index_domain(composition_authority.member_authorities))

    binding_result = bind_members_to_producers(
        composition_authority=composition_authority,
        task027_replay_evidence=task027_replay_evidence,
        task028_replay_evidence=task028_replay_evidence,
        task027_upstream_reference_plane=task027_upstream_reference_plane,
        task027_downstream_reference_plane=task027_downstream_reference_plane,
    )
    blockers.extend(binding_result.blockers)
    return BindingResult(
        bound_members=binding_result.bound_members,
        blockers=collapse_blockers(blockers),
    )


def T08_VALIDATE_GLOBAL_ORDER_BOUNDARIES_AND_PATH_TOPOLOGY(
    *,
    composition_authority: TubeSidePressurePathCompositionAuthority,
    binding_result: BindingResult,
    task027_upstream_reference_plane: str,
    task027_downstream_reference_plane: str,
) -> PathTopologyResult:
    """Validate global order, modeled boundaries, and path topology predicates."""
    return evaluate_path_topology(
        composition_authority=composition_authority,
        binding_result=binding_result,
        task027_upstream_reference_plane=task027_upstream_reference_plane,
        task027_downstream_reference_plane=task027_downstream_reference_plane,
    )


def T09_VALIDATE_EXCLUSION_PARTITION_AND_COMPLETENESS(
    *,
    composition_authority: TubeSidePressurePathCompositionAuthority,
    binding_result: BindingResult,
) -> tuple[Task029BlockerEntry, ...]:
    """Validate exclusion partition and modeled-boundary completeness proof."""
    return validate_exclusion_partition_and_completeness(
        composition_authority=composition_authority,
        binding_result=binding_result,
    ).blockers


def _run_t01_through_t09_validation(
    request: Task029Request,
) -> T01ThroughT09ValidationResult:
    """Accumulate safely applicable T01-T09 blockers for a typed TASK-029 request."""
    blockers: list[Task029BlockerEntry] = []
    bound_members: tuple[BoundPressurePathMember, ...] | None = None

    task027_success_result = request.task027_success_result
    task028_success_result = request.task028_success_result

    blockers.extend(
        T01_VALIDATE_UPSTREAM_SCHEMA_VERSIONS(
            task027_success_result=task027_success_result,
            task028_success_result=task028_success_result,
        )
    )

    task027_schema_supported = (
        task027_success_result.schema_version == TASK027_ACCEPTED_SCHEMA_VERSION
    )
    task028_schema_supported = (
        task028_success_result.schema_version == TASK028_ACCEPTED_SCHEMA_VERSION
    )

    blockers.extend(
        T02_REPLAY_UPSTREAM_RESULT_HASH_AND_UUID(
            task027_success_result=task027_success_result,
            task028_success_result=task028_success_result,
            task027_schema_supported=task027_schema_supported,
            task028_schema_supported=task028_schema_supported,
        )
    )

    blockers.extend(
        T03_VALIDATE_UPSTREAM_SUCCESS_WARNINGS_BLOCKERS(
            task027_success_result=task027_success_result,
            task028_success_result=task028_success_result,
            task027_schema_supported=task027_schema_supported,
            task028_schema_supported=task028_schema_supported,
        )
    )

    if task027_schema_supported and task028_schema_supported:
        blockers.extend(
            T04_COMPARE_PROFILE_AND_COMMON_IDENTITIES(
                request_profile_id=request.profile_id,
                task027_success_result=task027_success_result,
                task028_success_result=task028_success_result,
            )
        )

    blockers.extend(
        T05_VALIDATE_COMPOSITION_AUTHORITY_TREE_AND_HASHES(
            schema_version=request.schema_version,
            profile_id=request.profile_id,
            request_hash=request.request_hash,
            composition_authority=request.composition_authority,
            task027_result_hash=task027_success_result.result_hash,
            task028_result_hash=task028_success_result.result_hash,
            task025_hydraulic_authority_hash=task027_success_result.task025_hydraulic_authority_hash,
            task025_result_hash=task027_success_result.task025_result_hash,
            task026_result_hash=task027_success_result.task026_result_hash,
            property_snapshot_hash=task027_success_result.property_snapshot_hash,
        )
    )

    composition_authority = request.composition_authority
    composition_safe = _composition_authority_safe_for_binding(composition_authority)

    task027_replay_evidence: Task027ReplayEvidence | None = None
    task028_replay_evidence: Task028ReplayEvidence | None = None
    if task027_schema_supported:
        task027_replay_evidence = _extract_task027_replay_evidence(
            replay_task027_success(task027_success_result)
        )
    if task028_schema_supported:
        task028_replay_evidence = _extract_task028_replay_evidence(
            replay_task028_success(task028_success_result)
        )

    if (
        composition_safe
        and task027_replay_evidence is not None
        and task028_replay_evidence is not None
        and type(composition_authority) is TubeSidePressurePathCompositionAuthority
    ):
        binding_result = T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS(
            composition_authority=composition_authority,
            task027_replay_evidence=task027_replay_evidence,
            task028_replay_evidence=task028_replay_evidence,
            task027_upstream_reference_plane=task027_success_result.upstream_reference_plane,
            task027_downstream_reference_plane=task027_success_result.downstream_reference_plane,
        )
        blockers.extend(binding_result.blockers)

        if binding_result.bound_members:
            blockers.extend(
                T07_VALIDATE_DIRECTION_MULTIPLICITY_CONVENTION_PRESSURE(
                    composition_authority=composition_authority,
                    bound_members=binding_result.bound_members,
                )
            )

            topology_result = T08_VALIDATE_GLOBAL_ORDER_BOUNDARIES_AND_PATH_TOPOLOGY(
                composition_authority=composition_authority,
                binding_result=binding_result,
                task027_upstream_reference_plane=task027_success_result.upstream_reference_plane,
                task027_downstream_reference_plane=task027_success_result.downstream_reference_plane,
            )
            blockers.extend(topology_result.blockers)
            if topology_result.ordered_bound_members:
                bound_members = topology_result.ordered_bound_members

            blockers.extend(
                T09_VALIDATE_EXCLUSION_PARTITION_AND_COMPLETENESS(
                    composition_authority=composition_authority,
                    binding_result=binding_result,
                )
            )

    return T01ThroughT09ValidationResult(
        blockers=collapse_blockers(blockers),
        bound_members=bound_members,
    )


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
    "T00_ROUTE_UPSTREAM_BLOCKED_AND_REQUIRE_EXACT_TYPES",
    "T01ThroughT09ValidationResult",
    "T01_VALIDATE_UPSTREAM_SCHEMA_VERSIONS",
    "T02_REPLAY_UPSTREAM_RESULT_HASH_AND_UUID",
    "T03_VALIDATE_UPSTREAM_SUCCESS_WARNINGS_BLOCKERS",
    "T04_COMPARE_PROFILE_AND_COMMON_IDENTITIES",
    "T05_VALIDATE_COMPOSITION_AUTHORITY_TREE_AND_HASHES",
    "T06_BIND_EXPECTED_MEMBERS_TO_PRODUCER_RESULTS",
    "T07_VALIDATE_DIRECTION_MULTIPLICITY_CONVENTION_PRESSURE",
    "T08_VALIDATE_GLOBAL_ORDER_BOUNDARIES_AND_PATH_TOPOLOGY",
    "T09_VALIDATE_EXCLUSION_PARTITION_AND_COMPLETENESS",
    "_run_t01_through_t09_validation",
    "validate_composition_authority_tree_and_hashes",
]
