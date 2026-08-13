"""TASK-029 ledger evidence projection and success result builder.

I11 / T10: pure projection of validated bound members and exclusion authorities
into frozen ledger evidence records.

I13B: success result builder using I13A identity primitives.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
    LEDGER_EXCLUSION_EVIDENCE_SCHEMA_VERSION,
    LEDGER_MEMBER_EVIDENCE_SCHEMA_VERSION,
    TASK029_DEFERRED_CAPABILITIES_V1,
    TASK029_SUCCESS_RESULT_SCHEMA_VERSION,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    ExclusionStatus,
    MemberStatus,
    ProducerTask,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.identity import (
    compute_ledger_hash,
    compute_success_result_hash,
    derive_result_id,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029Provenance,
    Task029SuccessResult,
    TubeSidePressurePathCompletenessLedger,
    TubeSidePressurePathExclusionAuthority,
    TubeSidePressurePathLedgerExclusionEvidence,
    TubeSidePressurePathLedgerMemberEvidence,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.path_binding import (
    BoundPressurePathMember,
)


def build_member_evidence(
    bound_member: BoundPressurePathMember,
    *,
    observed_multiplicity: int,
    pressure_contribution_pa: Decimal,
) -> TubeSidePressurePathLedgerMemberEvidence:
    """Project a T06-bound member into frozen 16-field ledger member evidence."""
    member_authority = bound_member.member_authority
    if bound_member.producer_task == ProducerTask.TASK_028:
        component_result = bound_member.task028_component_result
        producer_component_type = component_result.component_type.value
    else:
        producer_component_type = member_authority.expected_producer_component_type

    return TubeSidePressurePathLedgerMemberEvidence(
        schema_version=LEDGER_MEMBER_EVIDENCE_SCHEMA_VERSION,
        member_id=member_authority.member_id,
        global_path_sequence_index=member_authority.global_path_sequence_index,
        producer_task=bound_member.producer_task,
        producer_result_hash=bound_member.producer_result_hash,
        producer_member_kind=member_authority.producer_member_kind,
        producer_component_identity=bound_member.producer_component_identity,
        producer_component_type=producer_component_type,
        producer_authority_hash=bound_member.producer_authority_hash,
        upstream_reference_plane=bound_member.upstream_reference_plane,
        downstream_reference_plane=bound_member.downstream_reference_plane,
        expected_multiplicity=bound_member.expected_multiplicity,
        observed_multiplicity=observed_multiplicity,
        pressure_contribution_pa=pressure_contribution_pa,
        composition_member_authority_hash=member_authority.member_authority_hash,
        member_status=MemberStatus.VERIFIED,
    )


def build_exclusion_evidence(
    exclusion_authority: TubeSidePressurePathExclusionAuthority,
) -> TubeSidePressurePathLedgerExclusionEvidence:
    """Project a T09-validated exclusion authority into frozen 7-field ledger exclusion evidence."""
    return TubeSidePressurePathLedgerExclusionEvidence(
        schema_version=LEDGER_EXCLUSION_EVIDENCE_SCHEMA_VERSION,
        exclusion_id=exclusion_authority.exclusion_id,
        excluded_item_identity=exclusion_authority.excluded_item_identity,
        exclusion_reason=exclusion_authority.exclusion_reason,
        evidence_refs=exclusion_authority.evidence_refs,
        exclusion_authority_hash=exclusion_authority.exclusion_authority_hash,
        exclusion_status=ExclusionStatus.VERIFIED_EXCLUSION,
    )


def build_success_result(
    *,
    profile_id: str,
    request_hash: str,
    task027_result_hash: str,
    task028_result_hash: str,
    task025_hydraulic_authority_hash: str,
    task025_result_hash: str,
    task026_result_hash: str,
    property_snapshot_hash: str,
    composition_authority_hash: str,
    completeness_ledger: TubeSidePressurePathCompletenessLedger,
    modeled_total_tube_side_pressure_drop_pa: Decimal,
    provenance: Task029Provenance,
) -> Task029SuccessResult:
    """Build a frozen Task029SuccessResult with computed hash and ID."""
    if modeled_total_tube_side_pressure_drop_pa <= Decimal("0"):
        msg = "modeled_total_tube_side_pressure_drop_pa must be positive"
        raise ValueError(msg)

    replayed_ledger_hash = compute_ledger_hash(completeness_ledger)
    if replayed_ledger_hash != completeness_ledger.ledger_hash:
        msg = "completeness_ledger.ledger_hash does not match replay"
        raise ValueError(msg)

    semantic_result = Task029SuccessResult(
        schema_version=TASK029_SUCCESS_RESULT_SCHEMA_VERSION,
        profile_id=profile_id,
        request_hash=request_hash,
        result_hash="",
        result_id="",
        task027_result_hash=task027_result_hash,
        task028_result_hash=task028_result_hash,
        task025_hydraulic_authority_hash=task025_hydraulic_authority_hash,
        task025_result_hash=task025_result_hash,
        task026_result_hash=task026_result_hash,
        property_snapshot_hash=property_snapshot_hash,
        composition_authority_hash=composition_authority_hash,
        completeness_ledger=completeness_ledger,
        modeled_total_tube_side_pressure_drop_pa=modeled_total_tube_side_pressure_drop_pa,
        warnings=(),
        blockers=(),
        deferred_capabilities=TASK029_DEFERRED_CAPABILITIES_V1,
        provenance=provenance,
    )
    result_hash = compute_success_result_hash(semantic_result)
    result_id = derive_result_id(result_hash)
    return replace(
        semantic_result,
        result_hash=result_hash,
        result_id=result_id,
    )


__all__ = [
    "build_exclusion_evidence",
    "build_member_evidence",
    "build_success_result",
]
