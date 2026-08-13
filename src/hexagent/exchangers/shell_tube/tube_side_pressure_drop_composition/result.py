"""TASK-029 ledger member and exclusion evidence projection builders.

I11 / T10: pure projection of validated bound members and exclusion authorities
into frozen ledger evidence records.
"""

from __future__ import annotations

from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
    LEDGER_EXCLUSION_EVIDENCE_SCHEMA_VERSION,
    LEDGER_MEMBER_EVIDENCE_SCHEMA_VERSION,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    ExclusionStatus,
    MemberStatus,
    ProducerTask,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
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


__all__ = [
    "build_exclusion_evidence",
    "build_member_evidence",
]
