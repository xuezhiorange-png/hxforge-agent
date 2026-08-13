"""TASK-029 producer-member binding and path topology validation primitives.

I08 / T06: bind validated composition member authorities to trusted upstream replay
evidence.
I09 / T08: global index domain, producer-bound reference-plane compatibility, and
path topology predicates.
"""

from __future__ import annotations

from dataclasses import dataclass

from hexagent.exchangers.shell_tube.tube_side_local_loss.models import (
    TubeSideLocalLossComponentResult,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.blocker_registry import (
    collapse_blockers,
    emit_blocker,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    ProducerTask,
    Task029BlockerCode,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029BlockerEntry,
    TubeSidePressurePathCompositionAuthority,
    TubeSidePressurePathMemberAuthority,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.upstream_replay import (
    Task027ReplayEvidence,
    Task028ReplayEvidence,
)

_GLOBAL_INDEX_FIELD_PATH = "composition_authority.member_authorities[].global_path_sequence_index"
_MEMBER_AUTHORITIES_FIELD_PATH = "composition_authority.member_authorities"


@dataclass(frozen=True)
class BoundPressurePathMember:
    """Package-internal immutable producer-member binding evidence."""

    member_authority: TubeSidePressurePathMemberAuthority
    producer_task: ProducerTask
    producer_result_hash: str
    producer_component_identity: str
    producer_authority_hash: str
    expected_multiplicity: int
    observed_multiplicity: int
    upstream_reference_plane: str
    downstream_reference_plane: str
    task027_replay_evidence: Task027ReplayEvidence | None
    task028_component_result: TubeSideLocalLossComponentResult | None


@dataclass(frozen=True)
class BindingResult:
    """Deterministic ordered bound members and accumulated blockers."""

    bound_members: tuple[BoundPressurePathMember, ...]
    blockers: tuple[Task029BlockerEntry, ...]


@dataclass(frozen=True)
class PathTopologyResult:
    """Deterministic ordered bound members, plane sequence, and topology blockers."""

    ordered_bound_members: tuple[BoundPressurePathMember, ...]
    plane_sequence: tuple[str, ...]
    blockers: tuple[Task029BlockerEntry, ...]


def sort_members_by_global_index(
    members: tuple[TubeSidePressurePathMemberAuthority, ...],
) -> tuple[TubeSidePressurePathMemberAuthority, ...]:
    """Return members sorted by ``global_path_sequence_index`` ASC."""
    return tuple(sorted(members, key=lambda member: member.global_path_sequence_index))


def _sort_bound_members_by_global_index(
    bound_members: tuple[BoundPressurePathMember, ...],
) -> tuple[BoundPressurePathMember, ...]:
    return tuple(
        sorted(
            bound_members,
            key=lambda bound: bound.member_authority.global_path_sequence_index,
        )
    )


def validate_global_index_domain(
    members: tuple[TubeSidePressurePathMemberAuthority, ...],
) -> tuple[Task029BlockerEntry, ...]:
    """Require exact contiguous zero-based global index domain ``0..N-1``."""
    if not members:
        return ()

    ordered_members = sort_members_by_global_index(members)
    member_count = len(ordered_members)
    indices = [member.global_path_sequence_index for member in ordered_members]

    if len(set(indices)) != member_count:
        return collapse_blockers(
            [
                emit_blocker(
                    Task029BlockerCode.BL_T029_OUT_OF_ORDER_MEMBER,
                    _GLOBAL_INDEX_FIELD_PATH,
                )
            ]
        )

    expected_indices = list(range(member_count))
    if indices != expected_indices:
        return collapse_blockers(
            [
                emit_blocker(
                    Task029BlockerCode.BL_T029_OUT_OF_ORDER_MEMBER,
                    _GLOBAL_INDEX_FIELD_PATH,
                )
            ]
        )

    return ()


def _member_field_path(_member: TubeSidePressurePathMemberAuthority) -> str:
    return "composition_authority.member_authorities[].member_id"


def _member_index_field_path(index: int, field: str) -> str:
    return f"composition_authority.member_authorities[{index}].{field}"


def _collect_duplicate_member_id_blockers(
    members: tuple[TubeSidePressurePathMemberAuthority, ...],
) -> list[Task029BlockerEntry]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for member in members:
        if member.member_id in seen:
            duplicates.add(member.member_id)
        seen.add(member.member_id)
    if not duplicates:
        return []
    return [
        emit_blocker(
            Task029BlockerCode.BL_T029_DUPLICATE_MEMBER,
            _MEMBER_AUTHORITIES_FIELD_PATH,
        )
    ]


def _collect_duplicate_component_identity_blockers(
    members: tuple[TubeSidePressurePathMemberAuthority, ...],
) -> list[Task029BlockerEntry]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for member in members:
        if member.producer_task != ProducerTask.TASK_028:
            continue
        identity = member.producer_component_identity
        if identity in seen:
            duplicates.add(identity)
        seen.add(identity)
    if not duplicates:
        return []
    return [
        emit_blocker(
            Task029BlockerCode.BL_T029_DUPLICATE_MEMBER,
            _MEMBER_AUTHORITIES_FIELD_PATH,
        )
    ]


def _collect_task027_exactly_one_blockers(
    members: tuple[TubeSidePressurePathMemberAuthority, ...],
) -> list[Task029BlockerEntry]:
    task027_members = [
        member for member in members if member.producer_task == ProducerTask.TASK_027
    ]
    if len(task027_members) == 0:
        return [
            emit_blocker(
                Task029BlockerCode.BL_T029_EXPECTED_MEMBER_MISSING,
                _MEMBER_AUTHORITIES_FIELD_PATH,
            )
        ]
    if len(task027_members) > 1:
        return [
            emit_blocker(
                Task029BlockerCode.BL_T029_UNEXPECTED_EXTRA_MEMBER,
                "task028_success_result.component_results",
            )
        ]
    return []


def _is_duplicate_member_id(
    member: TubeSidePressurePathMemberAuthority,
    members: tuple[TubeSidePressurePathMemberAuthority, ...],
) -> bool:
    return sum(1 for other in members if other.member_id == member.member_id) > 1


def _is_duplicate_task028_component_identity(
    member: TubeSidePressurePathMemberAuthority,
    members: tuple[TubeSidePressurePathMemberAuthority, ...],
) -> bool:
    if member.producer_task != ProducerTask.TASK_028:
        return False
    identity = member.producer_component_identity
    return (
        sum(
            1
            for other in members
            if other.producer_task == ProducerTask.TASK_028
            and other.producer_component_identity == identity
        )
        > 1
    )


def _bind_task027_member(
    member: TubeSidePressurePathMemberAuthority,
    task027_evidence: Task027ReplayEvidence,
    *,
    producer_upstream_reference_plane: str | None,
    producer_downstream_reference_plane: str | None,
) -> BoundPressurePathMember:
    upstream_plane = (
        producer_upstream_reference_plane
        if producer_upstream_reference_plane is not None
        else member.expected_upstream_reference_plane
    )
    downstream_plane = (
        producer_downstream_reference_plane
        if producer_downstream_reference_plane is not None
        else member.expected_downstream_reference_plane
    )
    return BoundPressurePathMember(
        member_authority=member,
        producer_task=ProducerTask.TASK_027,
        producer_result_hash=task027_evidence.result_hash,
        producer_component_identity=member.producer_component_identity,
        producer_authority_hash=member.expected_producer_authority_hash,
        expected_multiplicity=member.expected_multiplicity,
        observed_multiplicity=1,
        upstream_reference_plane=upstream_plane,
        downstream_reference_plane=downstream_plane,
        task027_replay_evidence=task027_evidence,
        task028_component_result=None,
    )


def _bind_task028_member(
    member: TubeSidePressurePathMemberAuthority,
    component: TubeSideLocalLossComponentResult,
    task028_evidence: Task028ReplayEvidence,
) -> BoundPressurePathMember:
    return BoundPressurePathMember(
        member_authority=member,
        producer_task=ProducerTask.TASK_028,
        producer_result_hash=task028_evidence.result_hash,
        producer_component_identity=component.component_id,
        producer_authority_hash=component.authority_hash,
        expected_multiplicity=member.expected_multiplicity,
        observed_multiplicity=component.multiplicity,
        upstream_reference_plane=component.upstream_reference_plane,
        downstream_reference_plane=component.downstream_reference_plane,
        task027_replay_evidence=None,
        task028_component_result=component,
    )


def bind_members_to_producers(
    *,
    composition_authority: TubeSidePressurePathCompositionAuthority,
    task027_replay_evidence: Task027ReplayEvidence,
    task028_replay_evidence: Task028ReplayEvidence,
    task027_upstream_reference_plane: str | None = None,
    task027_downstream_reference_plane: str | None = None,
) -> BindingResult:
    """Bind composition member authorities to trusted TASK-027/TASK-028 replay evidence."""
    blockers: list[Task029BlockerEntry] = []
    ordered_members = sort_members_by_global_index(composition_authority.member_authorities)
    all_members = composition_authority.member_authorities

    blockers.extend(_collect_duplicate_member_id_blockers(all_members))
    blockers.extend(_collect_duplicate_component_identity_blockers(all_members))
    blockers.extend(_collect_task027_exactly_one_blockers(all_members))

    bound_component_ids: set[str] = set()
    bound_members: list[BoundPressurePathMember] = []

    for index, member in enumerate(ordered_members):
        if _is_duplicate_member_id(member, all_members):
            continue
        if _is_duplicate_task028_component_identity(member, all_members):
            continue

        if member.producer_task == ProducerTask.TASK_027:
            bound_members.append(
                _bind_task027_member(
                    member,
                    task027_replay_evidence,
                    producer_upstream_reference_plane=task027_upstream_reference_plane,
                    producer_downstream_reference_plane=task027_downstream_reference_plane,
                )
            )
            continue

        if member.producer_task != ProducerTask.TASK_028:
            continue

        component = task028_replay_evidence.components_by_id.get(member.producer_component_identity)
        if component is None:
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_EXPECTED_MEMBER_MISSING,
                    _member_field_path(member),
                )
            )
            continue

        if member.expected_producer_component_type != component.component_type.value:
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_EXPECTED_MEMBER_MISSING,
                    _member_field_path(member),
                )
            )
            continue

        if member.expected_producer_authority_hash != component.authority_hash:
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_COMPOSITION_MEMBER_AUTHORITY_HASH_MISMATCH,
                    _member_index_field_path(index, "expected_producer_authority_hash"),
                )
            )
            continue

        bound_component_ids.add(component.component_id)
        bound_members.append(_bind_task028_member(member, component, task028_replay_evidence))

    for component in task028_replay_evidence.component_results:
        if component.component_id not in bound_component_ids:
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_UNEXPECTED_EXTRA_MEMBER,
                    "task028_success_result.component_results",
                )
            )

    return BindingResult(
        bound_members=tuple(bound_members),
        blockers=collapse_blockers(blockers),
    )


def _collect_producer_plane_binding_blockers(
    ordered_bound_members: tuple[BoundPressurePathMember, ...],
    *,
    task027_upstream_reference_plane: str,
    task027_downstream_reference_plane: str,
) -> list[Task029BlockerEntry]:
    blockers: list[Task029BlockerEntry] = []
    for bound in ordered_bound_members:
        member = bound.member_authority
        if bound.producer_task == ProducerTask.TASK_027:
            if member.expected_upstream_reference_plane != task027_upstream_reference_plane:
                blockers.append(
                    emit_blocker(
                        Task029BlockerCode.BL_T029_REFERENCE_PLANE_DISCONTINUITY,
                        _MEMBER_AUTHORITIES_FIELD_PATH,
                    )
                )
            if member.expected_downstream_reference_plane != task027_downstream_reference_plane:
                blockers.append(
                    emit_blocker(
                        Task029BlockerCode.BL_T029_REFERENCE_PLANE_DISCONTINUITY,
                        _MEMBER_AUTHORITIES_FIELD_PATH,
                    )
                )
            continue

        component = bound.task028_component_result
        if component is None:
            continue
        if member.expected_upstream_reference_plane != component.upstream_reference_plane:
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_REFERENCE_PLANE_DISCONTINUITY,
                    _MEMBER_AUTHORITIES_FIELD_PATH,
                )
            )
        if member.expected_downstream_reference_plane != component.downstream_reference_plane:
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_REFERENCE_PLANE_DISCONTINUITY,
                    _MEMBER_AUTHORITIES_FIELD_PATH,
                )
            )
    return blockers


def _collect_self_loop_blockers(
    ordered_bound_members: tuple[BoundPressurePathMember, ...],
) -> list[Task029BlockerEntry]:
    blockers: list[Task029BlockerEntry] = []
    for bound in ordered_bound_members:
        if bound.upstream_reference_plane == bound.downstream_reference_plane:
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_REFERENCE_PLANE_SELF_LOOP,
                    _MEMBER_AUTHORITIES_FIELD_PATH,
                )
            )
    return blockers


def _collect_adjacent_continuity_blockers(
    ordered_bound_members: tuple[BoundPressurePathMember, ...],
) -> list[Task029BlockerEntry]:
    blockers: list[Task029BlockerEntry] = []
    for index in range(len(ordered_bound_members) - 1):
        current = ordered_bound_members[index]
        next_member = ordered_bound_members[index + 1]
        if current.downstream_reference_plane != next_member.upstream_reference_plane:
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_REFERENCE_PLANE_DISCONTINUITY,
                    _MEMBER_AUTHORITIES_FIELD_PATH,
                )
            )
    return blockers


def _collect_boundary_blockers(
    composition_authority: TubeSidePressurePathCompositionAuthority,
    ordered_bound_members: tuple[BoundPressurePathMember, ...],
) -> list[Task029BlockerEntry]:
    blockers: list[Task029BlockerEntry] = []
    first = ordered_bound_members[0]
    last = ordered_bound_members[-1]
    if first.upstream_reference_plane != composition_authority.start_reference_plane:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_MODELED_PATH_BOUNDARY_INVALID,
                "composition_authority.start_reference_plane",
            )
        )
    if last.downstream_reference_plane != composition_authority.end_reference_plane:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_MODELED_PATH_BOUNDARY_INVALID,
                "composition_authority.end_reference_plane",
            )
        )
    return blockers


def _build_plane_sequence(
    ordered_bound_members: tuple[BoundPressurePathMember, ...],
) -> tuple[str, ...]:
    if not ordered_bound_members:
        return ()
    planes = [ordered_bound_members[0].upstream_reference_plane]
    for bound in ordered_bound_members:
        planes.append(bound.downstream_reference_plane)
    return tuple(planes)


def _collect_cycle_blockers(plane_sequence: tuple[str, ...]) -> list[Task029BlockerEntry]:
    seen: set[str] = set()
    for plane in plane_sequence:
        if plane in seen:
            return [
                emit_blocker(
                    Task029BlockerCode.BL_T029_PATH_CYCLE,
                    _MEMBER_AUTHORITIES_FIELD_PATH,
                )
            ]
        seen.add(plane)
    return []


def _collect_fork_blockers(
    ordered_bound_members: tuple[BoundPressurePathMember, ...],
) -> list[Task029BlockerEntry]:
    upstream_to_member_ids: dict[str, list[str]] = {}
    for bound in ordered_bound_members:
        upstream = bound.upstream_reference_plane
        upstream_to_member_ids.setdefault(upstream, []).append(bound.member_authority.member_id)

    for member_ids in upstream_to_member_ids.values():
        if len(set(member_ids)) > 1:
            return [
                emit_blocker(
                    Task029BlockerCode.BL_T029_PATH_FORK,
                    _MEMBER_AUTHORITIES_FIELD_PATH,
                )
            ]
    return []


def _collect_join_blockers(
    ordered_bound_members: tuple[BoundPressurePathMember, ...],
) -> list[Task029BlockerEntry]:
    downstream_to_member_ids: dict[str, list[str]] = {}
    for bound in ordered_bound_members:
        downstream = bound.downstream_reference_plane
        downstream_to_member_ids.setdefault(downstream, []).append(bound.member_authority.member_id)

    for member_ids in downstream_to_member_ids.values():
        if len(set(member_ids)) > 1:
            return [
                emit_blocker(
                    Task029BlockerCode.BL_T029_PATH_JOIN,
                    _MEMBER_AUTHORITIES_FIELD_PATH,
                )
            ]
    return []


def _collect_overlapping_segment_blockers(
    ordered_bound_members: tuple[BoundPressurePathMember, ...],
) -> list[Task029BlockerEntry]:
    segment_to_member_ids: dict[tuple[str, str], list[str]] = {}
    for bound in ordered_bound_members:
        segment = (bound.upstream_reference_plane, bound.downstream_reference_plane)
        segment_to_member_ids.setdefault(segment, []).append(bound.member_authority.member_id)

    for member_ids in segment_to_member_ids.values():
        if len(set(member_ids)) > 1:
            return [
                emit_blocker(
                    Task029BlockerCode.BL_T029_OVERLAPPING_PATH_SEGMENT,
                    _MEMBER_AUTHORITIES_FIELD_PATH,
                )
            ]
    return []


def evaluate_path_topology(
    *,
    composition_authority: TubeSidePressurePathCompositionAuthority,
    binding_result: BindingResult,
    task027_upstream_reference_plane: str,
    task027_downstream_reference_plane: str,
) -> PathTopologyResult:
    """Evaluate global order, producer plane compatibility, and path topology predicates."""
    blockers: list[Task029BlockerEntry] = []

    if not composition_authority.member_authorities:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_EMPTY_MODELED_PATH,
                _MEMBER_AUTHORITIES_FIELD_PATH,
            )
        )
        return PathTopologyResult(
            ordered_bound_members=(),
            plane_sequence=(),
            blockers=collapse_blockers(blockers),
        )

    blockers.extend(validate_global_index_domain(composition_authority.member_authorities))

    if not binding_result.bound_members:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_EMPTY_MODELED_PATH,
                _MEMBER_AUTHORITIES_FIELD_PATH,
            )
        )
        return PathTopologyResult(
            ordered_bound_members=(),
            plane_sequence=(),
            blockers=collapse_blockers(blockers),
        )

    ordered_bound_members = _sort_bound_members_by_global_index(binding_result.bound_members)

    blockers.extend(
        _collect_producer_plane_binding_blockers(
            ordered_bound_members,
            task027_upstream_reference_plane=task027_upstream_reference_plane,
            task027_downstream_reference_plane=task027_downstream_reference_plane,
        )
    )
    blockers.extend(_collect_self_loop_blockers(ordered_bound_members))
    blockers.extend(_collect_adjacent_continuity_blockers(ordered_bound_members))
    blockers.extend(_collect_boundary_blockers(composition_authority, ordered_bound_members))
    blockers.extend(_collect_fork_blockers(ordered_bound_members))
    blockers.extend(_collect_join_blockers(ordered_bound_members))
    blockers.extend(_collect_overlapping_segment_blockers(ordered_bound_members))

    plane_sequence = _build_plane_sequence(ordered_bound_members)
    blockers.extend(_collect_cycle_blockers(plane_sequence))

    return PathTopologyResult(
        ordered_bound_members=ordered_bound_members,
        plane_sequence=plane_sequence,
        blockers=collapse_blockers(blockers),
    )


__all__ = [
    "BoundPressurePathMember",
    "BindingResult",
    "PathTopologyResult",
    "bind_members_to_producers",
    "evaluate_path_topology",
    "sort_members_by_global_index",
    "validate_global_index_domain",
]
