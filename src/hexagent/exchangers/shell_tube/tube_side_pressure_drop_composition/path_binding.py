"""TASK-029 producer-member identity binding primitives.

I08 / T06: bind validated composition member authorities to trusted upstream replay
evidence. Path topology, multiplicity, and exclusion partition are deferred.
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


def sort_members_by_global_index(
    members: tuple[TubeSidePressurePathMemberAuthority, ...],
) -> tuple[TubeSidePressurePathMemberAuthority, ...]:
    """Return members sorted by ``global_path_sequence_index`` ASC."""
    return tuple(sorted(members, key=lambda member: member.global_path_sequence_index))


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
            "composition_authority.member_authorities",
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
            "composition_authority.member_authorities",
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
                "composition_authority.member_authorities",
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
) -> BoundPressurePathMember:
    return BoundPressurePathMember(
        member_authority=member,
        producer_task=ProducerTask.TASK_027,
        producer_result_hash=task027_evidence.result_hash,
        producer_component_identity=member.producer_component_identity,
        producer_authority_hash=member.expected_producer_authority_hash,
        expected_multiplicity=member.expected_multiplicity,
        observed_multiplicity=1,
        upstream_reference_plane=member.expected_upstream_reference_plane,
        downstream_reference_plane=member.expected_downstream_reference_plane,
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
            bound_members.append(_bind_task027_member(member, task027_replay_evidence))
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


__all__ = [
    "BoundPressurePathMember",
    "BindingResult",
    "bind_members_to_producers",
    "sort_members_by_global_index",
]
