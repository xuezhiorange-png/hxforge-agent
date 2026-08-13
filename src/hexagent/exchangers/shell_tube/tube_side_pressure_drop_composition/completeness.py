"""TASK-029 exclusion authority validation and modeled-boundary partition completeness.

I10 / T09: exclusion structural validation, hash replay, explicit partition proof,
and completeness blockers. Ledger construction and pressure composition are deferred.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.blocker_registry import (
    collapse_blockers,
    emit_blocker,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
    COMPLETENESS_LEDGER_SCHEMA_VERSION,
    EXCLUSION_AUTHORITY_SCHEMA_VERSION,
    sort_evidence_refs,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    CompletenessStatus,
    ExclusionReason,
    IdentityCompatibilityStatus,
    PathContinuityStatus,
    ProducerTask,
    Task029BlockerCode,
    Task029InScopeComponentType,
    V02OutOfScopeItemIdentity,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
    compute_exclusion_authority_hash,
    compute_ledger_hash,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029BlockerEntry,
    TubeSidePressurePathCompletenessLedger,
    TubeSidePressurePathCompositionAuthority,
    TubeSidePressurePathExclusionAuthority,
    TubeSidePressurePathLedgerExclusionEvidence,
    TubeSidePressurePathLedgerMemberEvidence,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.path_binding import (
    BindingResult,
)

_EXCLUSION_AUTHORITIES_FIELD_PATH = "composition_authority.exclusion_authorities"

_REQUIRED_V02_IDENTITIES: frozenset[str] = frozenset(
    identity.value for identity in V02OutOfScopeItemIdentity
)
_IN_SCOPE_COMPONENT_TYPES: frozenset[str] = frozenset(
    component_type.value for component_type in Task029InScopeComponentType
)


@dataclass(frozen=True)
class ExclusionPartitionResult:
    """Package-internal immutable exclusion partition and completeness proof."""

    ordered_valid_exclusions: tuple[TubeSidePressurePathExclusionAuthority, ...]
    observed_in_scope_counts: tuple[tuple[str, int], ...]
    blockers: tuple[Task029BlockerEntry, ...]
    complete_within_modeled_boundary: bool


def sort_exclusion_authorities(
    exclusions: tuple[TubeSidePressurePathExclusionAuthority, ...],
) -> tuple[TubeSidePressurePathExclusionAuthority, ...]:
    """Return exclusions sorted by ``exclusion_id`` UTF-8 ASC."""
    return tuple(sorted(exclusions, key=lambda exclusion: exclusion.exclusion_id))


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and value != ""


def _is_hash_string(value: object) -> bool:
    return isinstance(value, str) and value != ""


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


def _is_allowed_exclusion_semantics(exclusion: TubeSidePressurePathExclusionAuthority) -> bool:
    identity = exclusion.excluded_item_identity
    if exclusion.exclusion_reason == ExclusionReason.V0_2_OUT_OF_SCOPE:
        return identity in _REQUIRED_V02_IDENTITIES
    if exclusion.exclusion_reason == ExclusionReason.PHYSICALLY_ABSENT:
        return identity in _IN_SCOPE_COMPONENT_TYPES
    return False


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
    if not _refs_are_non_empty_unique_sorted(exclusion.evidence_refs):
        return False
    if not _is_hash_string(exclusion.exclusion_authority_hash):
        return False
    return _is_allowed_exclusion_semantics(exclusion)


def _binding_evidence_is_safe_for_observed_partition(binding_result: BindingResult) -> bool:
    return len(binding_result.blockers) == 0 and len(binding_result.bound_members) > 0


def _observed_in_scope_counts(binding_result: BindingResult) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for bound in binding_result.bound_members:
        if bound.producer_task != ProducerTask.TASK_028:
            continue
        component = bound.task028_component_result
        if component is None:
            continue
        counts[component.component_type.value] += 1
    return dict(counts)


def _collect_exclusion_authority_blockers(
    exclusions: tuple[TubeSidePressurePathExclusionAuthority, ...],
) -> tuple[list[Task029BlockerEntry], dict[str, list[TubeSidePressurePathExclusionAuthority]]]:
    blockers: list[Task029BlockerEntry] = []
    valid_exclusions: list[TubeSidePressurePathExclusionAuthority] = []
    exclusions_by_id: dict[str, list[TubeSidePressurePathExclusionAuthority]] = {}

    for exclusion in exclusions:
        exclusions_by_id.setdefault(exclusion.exclusion_id, []).append(exclusion)
        if not _validate_exclusion_structure(exclusion):
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_EXCLUSION_AUTHORITY_INVALID,
                    _EXCLUSION_AUTHORITIES_FIELD_PATH,
                )
            )
            continue

        replayed_hash = compute_exclusion_authority_hash(exclusion)
        if replayed_hash != exclusion.exclusion_authority_hash:
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_EXCLUSION_AUTHORITY_INVALID,
                    _EXCLUSION_AUTHORITIES_FIELD_PATH,
                )
            )
            continue

        valid_exclusions.append(exclusion)

    for _exclusion_id, entries in exclusions_by_id.items():
        if len(entries) > 1:
            blockers.append(
                emit_blocker(
                    Task029BlockerCode.BL_T029_EXCLUSION_AUTHORITY_INVALID,
                    _EXCLUSION_AUTHORITIES_FIELD_PATH,
                )
            )

    return blockers, exclusions_by_id


def _index_valid_exclusions_by_semantic_key(
    valid_exclusions: tuple[TubeSidePressurePathExclusionAuthority, ...],
) -> dict[tuple[ExclusionReason, str], list[TubeSidePressurePathExclusionAuthority]]:
    indexed: dict[tuple[ExclusionReason, str], list[TubeSidePressurePathExclusionAuthority]] = {}
    for exclusion in valid_exclusions:
        key = (exclusion.exclusion_reason, exclusion.excluded_item_identity)
        indexed.setdefault(key, []).append(exclusion)
    return indexed


def _collect_required_v02_blockers(
    semantic_index: dict[tuple[ExclusionReason, str], list[TubeSidePressurePathExclusionAuthority]],
) -> list[Task029BlockerEntry]:
    blockers: list[Task029BlockerEntry] = []
    partition_incomplete = False

    for identity in sorted(_REQUIRED_V02_IDENTITIES):
        key = (ExclusionReason.V0_2_OUT_OF_SCOPE, identity)
        matches = semantic_index.get(key, [])
        if len(matches) != 1:
            partition_incomplete = True
            if len(matches) == 0:
                blockers.append(
                    emit_blocker(
                        Task029BlockerCode.BL_T029_EXCLUSION_EVIDENCE_MISSING,
                        _EXCLUSION_AUTHORITIES_FIELD_PATH,
                    )
                )
            else:
                blockers.append(
                    emit_blocker(
                        Task029BlockerCode.BL_T029_EXCLUSION_AUTHORITY_INVALID,
                        _EXCLUSION_AUTHORITIES_FIELD_PATH,
                    )
                )

    if partition_incomplete:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_COMPLETENESS_LEDGER_INCOMPLETE,
                _EXCLUSION_AUTHORITIES_FIELD_PATH,
            )
        )

    return blockers


def _collect_in_scope_partition_blockers(
    *,
    semantic_index: dict[tuple[ExclusionReason, str], list[TubeSidePressurePathExclusionAuthority]],
    observed_counts: dict[str, int],
) -> list[Task029BlockerEntry]:
    blockers: list[Task029BlockerEntry] = []
    partition_incomplete = False

    for component_type in sorted(_IN_SCOPE_COMPONENT_TYPES):
        observed_count = observed_counts.get(component_type, 0)
        absent_key = (ExclusionReason.PHYSICALLY_ABSENT, component_type)
        absent_matches = semantic_index.get(absent_key, [])

        if observed_count > 0:
            if absent_matches:
                blockers.append(
                    emit_blocker(
                        Task029BlockerCode.BL_T029_EXCLUSION_AUTHORITY_INVALID,
                        _EXCLUSION_AUTHORITIES_FIELD_PATH,
                    )
                )
                partition_incomplete = True
            continue

        if len(absent_matches) != 1:
            partition_incomplete = True
            if len(absent_matches) == 0:
                blockers.append(
                    emit_blocker(
                        Task029BlockerCode.BL_T029_EXCLUSION_EVIDENCE_MISSING,
                        _EXCLUSION_AUTHORITIES_FIELD_PATH,
                    )
                )
            else:
                blockers.append(
                    emit_blocker(
                        Task029BlockerCode.BL_T029_EXCLUSION_AUTHORITY_INVALID,
                        _EXCLUSION_AUTHORITIES_FIELD_PATH,
                    )
                )

    if partition_incomplete:
        blockers.append(
            emit_blocker(
                Task029BlockerCode.BL_T029_COMPLETENESS_LEDGER_INCOMPLETE,
                _EXCLUSION_AUTHORITIES_FIELD_PATH,
            )
        )

    return blockers


def validate_exclusion_partition_and_completeness(
    *,
    composition_authority: TubeSidePressurePathCompositionAuthority,
    binding_result: BindingResult,
) -> ExclusionPartitionResult:
    """Validate exclusion authorities and prove modeled-boundary partition completeness."""
    blockers: list[Task029BlockerEntry] = []
    exclusions = composition_authority.exclusion_authorities

    authority_blockers, _exclusions_by_id = _collect_exclusion_authority_blockers(exclusions)
    blockers.extend(authority_blockers)

    valid_exclusions = tuple(
        exclusion
        for exclusion in exclusions
        if _validate_exclusion_structure(exclusion)
        and compute_exclusion_authority_hash(exclusion) == exclusion.exclusion_authority_hash
        and len(_exclusions_by_id.get(exclusion.exclusion_id, ())) == 1
    )
    ordered_valid_exclusions = sort_exclusion_authorities(valid_exclusions)
    semantic_index = _index_valid_exclusions_by_semantic_key(ordered_valid_exclusions)

    blockers.extend(_collect_required_v02_blockers(semantic_index))

    observed_counts: dict[str, int] = {}
    if _binding_evidence_is_safe_for_observed_partition(binding_result):
        observed_counts = _observed_in_scope_counts(binding_result)
        blockers.extend(
            _collect_in_scope_partition_blockers(
                semantic_index=semantic_index,
                observed_counts=observed_counts,
            )
        )

    collapsed_blockers = collapse_blockers(blockers)
    complete_within_modeled_boundary = len(collapsed_blockers) == 0

    observed_count_items = tuple(
        sorted(
            (component_type, observed_counts.get(component_type, 0))
            for component_type in _IN_SCOPE_COMPONENT_TYPES
        )
    )

    return ExclusionPartitionResult(
        ordered_valid_exclusions=ordered_valid_exclusions,
        observed_in_scope_counts=observed_count_items,
        blockers=collapsed_blockers,
        complete_within_modeled_boundary=complete_within_modeled_boundary,
    )


def _sort_member_evidence(
    member_evidence: tuple[TubeSidePressurePathLedgerMemberEvidence, ...],
) -> tuple[TubeSidePressurePathLedgerMemberEvidence, ...]:
    return tuple(sorted(member_evidence, key=lambda evidence: evidence.global_path_sequence_index))


def build_completeness_ledger(
    *,
    composition_authority: TubeSidePressurePathCompositionAuthority,
    member_evidence: tuple[TubeSidePressurePathLedgerMemberEvidence, ...],
    exclusion_evidence: tuple[TubeSidePressurePathLedgerExclusionEvidence, ...],
) -> TubeSidePressurePathCompletenessLedger:
    """Assemble verified 12-field completeness ledger with deterministic evidence ordering."""
    ordered_member_evidence = _sort_member_evidence(member_evidence)
    ordered_exclusion_evidence = sort_exclusion_authorities(exclusion_evidence)

    expected_member_count = len(composition_authority.member_authorities)
    observed_member_count = len(ordered_member_evidence)
    if expected_member_count != observed_member_count:
        msg = (
            "member evidence count must match composition authority modeled member plan: "
            f"expected={expected_member_count}, observed={observed_member_count}"
        )
        raise ValueError(msg)

    ledger_without_hash = TubeSidePressurePathCompletenessLedger(
        schema_version=COMPLETENESS_LEDGER_SCHEMA_VERSION,
        modeled_path_id=composition_authority.modeled_path_id,
        modeled_start_reference_plane=composition_authority.start_reference_plane,
        modeled_end_reference_plane=composition_authority.end_reference_plane,
        expected_member_count=expected_member_count,
        observed_member_count=observed_member_count,
        ordered_member_evidence=ordered_member_evidence,
        ordered_exclusion_evidence=ordered_exclusion_evidence,
        path_continuity_status=PathContinuityStatus.CONTIGUOUS_EXACT_REFERENCE_PLANE_CHAIN,
        identity_compatibility_status=IdentityCompatibilityStatus.MATCHED,
        completeness_status=CompletenessStatus.COMPLETE_WITHIN_EXPLICIT_MODELED_BOUNDARY,
        ledger_hash="",
    )
    ledger_hash = compute_ledger_hash(ledger_without_hash)
    return TubeSidePressurePathCompletenessLedger(
        schema_version=ledger_without_hash.schema_version,
        modeled_path_id=ledger_without_hash.modeled_path_id,
        modeled_start_reference_plane=ledger_without_hash.modeled_start_reference_plane,
        modeled_end_reference_plane=ledger_without_hash.modeled_end_reference_plane,
        expected_member_count=ledger_without_hash.expected_member_count,
        observed_member_count=ledger_without_hash.observed_member_count,
        ordered_member_evidence=ledger_without_hash.ordered_member_evidence,
        ordered_exclusion_evidence=ledger_without_hash.ordered_exclusion_evidence,
        path_continuity_status=ledger_without_hash.path_continuity_status,
        identity_compatibility_status=ledger_without_hash.identity_compatibility_status,
        completeness_status=ledger_without_hash.completeness_status,
        ledger_hash=ledger_hash,
    )


__all__ = [
    "ExclusionPartitionResult",
    "build_completeness_ledger",
    "sort_exclusion_authorities",
    "validate_exclusion_partition_and_completeness",
]
