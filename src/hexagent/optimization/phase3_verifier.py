"""
TASK-009 Phase 3 — Warning/blocker aggregation, external verifier,
provenance builder and verifier.

Sections 20-22 of the Phase 3 design contract.
"""

from __future__ import annotations

import dataclasses
import typing
import uuid
from decimal import Decimal

from hexagent.core.canonical import sha256_digest
from hexagent.domain.messages import EngineeringMessage, ErrorCode, RunFailure
from hexagent.domain.provenance import (
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
)
from hexagent.optimization.context import OptimizationObjective
from hexagent.optimization.evaluation import (
    CandidateEvaluationRecord,
    CandidateEvaluationState,
    _build_message_descriptor,
)
from hexagent.optimization.identities import ManufacturableCandidate
from hexagent.optimization.models import SizingRequest
from hexagent.optimization.phase3_core import (
    Phase2SourceRecordDescriptor,
    Phase2SourceRecordIdentitySnapshot,
    Phase2SourceRecordSnapshot,
    Phase3Disposition,
    Phase3MessageDescriptor,
    Phase3MessageDescriptorBinding,
    Phase3PreparationStatus,
    Phase3ProvenanceRelation,
    Phase3RunFailureDescriptorBinding,
    TerminationStatus,
    _find_stop_index,
    _verify_all_counts,
    canonical_decimal,
    derive_termination_status,
)
from hexagent.optimization.phase3_evaluation import (
    CandidateDispositionRecord,
    Phase3CandidateClassificationInput,
    Phase3CandidatePreparationResult,
    Phase3EvaluationInput,
    Phase3SourceRecordBinding,
    candidate_disposition_payload,
    disposition_from_preparation_failure,
    verify_phase3_index_artifact_matrix,
)

# Late imports from phase3_builder to avoid circular import.
# These are imported inside the functions that need them.
# Types used in annotations are imported under TYPE_CHECKING.

if typing.TYPE_CHECKING:
    from hexagent.optimization.phase3_builder import (
        OptimizationResult,
        OptimizationResultCoreValues,
        RankedCandidateRecord,
    )

# ── Shorthand aliases for enum members used verbatim in contract code ──────

# CandidateEvaluationState
VERIFIED = CandidateEvaluationState.VERIFIED

# Phase3Disposition
FEASIBLE = Phase3Disposition.FEASIBLE
INFEASIBLE = Phase3Disposition.INFEASIBLE

# TerminationStatus
COMPLETE = TerminationStatus.COMPLETE
PARTIAL = TerminationStatus.PARTIAL

# Phase3PreparationStatus
READY = Phase3PreparationStatus.READY
FAILED = Phase3PreparationStatus.FAILED

# OptimizationObjective
MINIMUM_OUTER_HEAT_TRANSFER_AREA = OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA
MINIMUM_EFFECTIVE_LENGTH = OptimizationObjective.MINIMUM_EFFECTIVE_LENGTH

# ProvenanceNodeType aliases
EXTERNAL = ProvenanceNodeType.EXTERNAL
INPUT_FILE = ProvenanceNodeType.INPUT_FILE
CALCULATION_RUN = ProvenanceNodeType.CALCULATION_RUN
INTERMEDIATE = ProvenanceNodeType.INTERMEDIATE
RESULT = ProvenanceNodeType.RESULT
OPTIMIZER = ProvenanceNodeType.OPTIMIZER

# Phase 3 result namespace UUID (matching phase3_builder)
PHASE3_RESULT_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# ── Forward reference for types defined in this module ─────────────────────
# Phase3AuthoritativeArtifacts is defined below; used via string annotation
# in verify_optimization_result_or_raise before definition.


# ═══════════════════════════════════════════════════════════════════════════
# Section 20 — Warning/blocker aggregation
# ═══════════════════════════════════════════════════════════════════════════


def build_engineering_message_descriptor(
    msg: EngineeringMessage,
) -> Phase3MessageDescriptor | RunFailure:
    """Build a Phase3MessageDescriptor from an EngineeringMessage.

    Uses the canonical Phase 2 _build_message_descriptor to extract
    owner_sort_key, original_code, and message_payload_digest.
    Returns RunFailure if canonicalization fails.
    """
    desc = _build_message_descriptor(msg)
    if desc.canonicalization_error is not None:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Cannot build message descriptor: {desc.canonicalization_error.failure_kind.value}"
            ),
            context=(
                ("original_code", desc.original_code),
                ("failure_kind", desc.canonicalization_error.failure_kind.value),
                ("context_key", desc.canonicalization_error.context_key),
            ),
        )
    return Phase3MessageDescriptor(
        owner_sort_key=desc.owner_sort_key,
        original_code=desc.original_code,
        message_payload_digest=desc.message_payload_digest,  # type: ignore[arg-type]
    )


def verify_phase3_message_descriptor_or_raise(d: Phase3MessageDescriptor) -> None:
    if not d.original_code:
        raise ValueError("descriptor original_code must be non-empty")
    if not d.DIGEST_PATTERN.match(d.message_payload_digest):
        raise ValueError("invalid message_payload_digest")
    if len(d.owner_sort_key) != 6:
        raise ValueError("owner_sort_key length != 6")
    if d.owner_sort_key[1] != d.original_code:
        raise ValueError("owner_sort_key[1] != original_code")


def build_result_message_digest_tuples(
    ei: Phase3EvaluationInput,
    dispositions: tuple[CandidateDispositionRecord, ...],
    stop_index: int | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    from hexagent.optimization.phase3_builder import _build_strict_stop_warning

    for dr in dispositions:
        for d in dr.warning_descriptors:
            verify_phase3_message_descriptor_or_raise(d)
        for d in dr.blocker_descriptors:
            verify_phase3_message_descriptor_or_raise(d)
    all_w = [d for dr in dispositions for d in dr.warning_descriptors]
    if stop_index is not None:
        ss = _build_strict_stop_warning(ei, stop_index)
        if ss is None:
            raise RuntimeError("strict-stop None for PARTIAL")
        ssd = build_engineering_message_descriptor(ss)
        if isinstance(ssd, RunFailure):
            raise RuntimeError("strict-stop descriptor failed")
        all_w.append(ssd)
    all_w.sort(key=lambda d: d.owner_sort_key)
    all_b = [d for dr in dispositions for d in dr.blocker_descriptors]
    all_b.sort(key=lambda d: d.owner_sort_key)
    return (
        tuple(d.message_payload_digest for d in all_w),
        tuple(d.message_payload_digest for d in all_b),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Section 21 — External verifier (P0-11)
# ═══════════════════════════════════════════════════════════════════════════


def _verify_external_authority_parity(
    *,
    evaluation_input: Phase3EvaluationInput,
    external_source_records: tuple[CandidateEvaluationRecord, ...],
    external_identity_snapshots: tuple[Phase2SourceRecordIdentitySnapshot, ...],
    external_complete_snapshots: tuple[Phase2SourceRecordSnapshot | None, ...],
) -> None:
    if external_source_records != evaluation_input.evaluation_records:
        raise ValueError("external source_records parity mismatch")
    if external_identity_snapshots != evaluation_input.identity_snapshots:
        raise ValueError("external identity_snapshots parity mismatch")
    if external_complete_snapshots != evaluation_input.complete_snapshots:
        raise ValueError("external complete_snapshots parity mismatch")


def verify_optimization_result_or_raise(
    result: OptimizationResult,
    *,
    ei: Phase3EvaluationInput,
    sizing_request: SizingRequest,
    candidates: tuple[ManufacturableCandidate, ...],
    source_records: tuple[CandidateEvaluationRecord, ...],
    identity_snapshots: tuple[Phase2SourceRecordIdentitySnapshot, ...],
    complete_snapshots: tuple[Phase2SourceRecordSnapshot | None, ...],
    phase2_source_record_descriptors: tuple[Phase2SourceRecordDescriptor | None, ...],
    source_bindings: tuple[Phase3SourceRecordBinding | None, ...],
    classification_inputs: tuple[Phase3CandidateClassificationInput | None, ...],
    preparation_results: tuple[Phase3CandidatePreparationResult | None, ...],
    warning_descriptor_tuples: tuple[tuple[Phase3MessageDescriptor, ...], ...],
    blocker_descriptor_tuples: tuple[tuple[Phase3MessageDescriptor, ...], ...],
    warning_binding_tuples: tuple[tuple[Phase3MessageDescriptorBinding, ...], ...],
    blocker_binding_tuples: tuple[tuple[Phase3MessageDescriptorBinding, ...], ...],
    evidence_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...],
    source_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...],
    phase3_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...],
    dispositions: tuple[CandidateDispositionRecord, ...],
    ranked: tuple[RankedCandidateRecord, ...],
    graph: ProvenanceGraph,
) -> None:
    """Delegate all semantic verification to the shared acceptance function."""
    _verify_external_authority_parity(
        evaluation_input=ei,
        external_source_records=source_records,
        external_identity_snapshots=identity_snapshots,
        external_complete_snapshots=complete_snapshots,
    )
    # Candidates are owned by EvaluationInput; verify external candidates match
    if candidates != ei.materialization_result.candidates:
        raise ValueError("external candidates parity mismatch")
    artifacts = Phase3AuthoritativeArtifacts(
        sizing_request=sizing_request,
        phase2_source_record_descriptors=phase2_source_record_descriptors,
        source_bindings=source_bindings,
        classification_inputs=classification_inputs,
        preparation_results=preparation_results,
        warning_descriptor_tuples=warning_descriptor_tuples,
        blocker_descriptor_tuples=blocker_descriptor_tuples,
        warning_binding_tuples=warning_binding_tuples,
        blocker_binding_tuples=blocker_binding_tuples,
        evidence_failure_bindings=evidence_failure_bindings,
        source_failure_bindings=source_failure_bindings,
        phase3_failure_bindings=phase3_failure_bindings,
    )
    verify_phase3_result_semantics_or_raise(
        result=result,
        graph=graph,
        evaluation_input=ei,
        artifacts=artifacts,
        dispositions=dispositions,
        ranked_records=ranked,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Section 21b — verify_phase3_result_semantics_or_raise (shared semantic acceptance)
# ═══════════════════════════════════════════════════════════════════════════


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Phase3AuthoritativeArtifacts:
    """Container for all independent authority artifact tuples required by the shared verifier.

    Note: EvaluationInput is the sole owner of source_records, identity_snapshots,
    complete_snapshots, and materialization_result.candidates. These are consumed
    directly from evaluation_input, not duplicated here.
    """

    sizing_request: SizingRequest
    phase2_source_record_descriptors: tuple[Phase2SourceRecordDescriptor | None, ...]
    source_bindings: tuple[Phase3SourceRecordBinding | None, ...]
    classification_inputs: tuple[Phase3CandidateClassificationInput | None, ...]
    preparation_results: tuple[Phase3CandidatePreparationResult | None, ...]
    warning_descriptor_tuples: tuple[tuple[Phase3MessageDescriptor, ...], ...]
    blocker_descriptor_tuples: tuple[tuple[Phase3MessageDescriptor, ...], ...]
    warning_binding_tuples: tuple[tuple[Phase3MessageDescriptorBinding, ...], ...]
    blocker_binding_tuples: tuple[tuple[Phase3MessageDescriptorBinding, ...], ...]
    evidence_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...]
    source_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...]
    phase3_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...]


def verify_phase3_result_semantics_or_raise(
    *,
    result: OptimizationResult,
    graph: ProvenanceGraph,
    evaluation_input: Phase3EvaluationInput,
    artifacts: Phase3AuthoritativeArtifacts,
    dispositions: tuple[CandidateDispositionRecord, ...],
    ranked_records: tuple[RankedCandidateRecord, ...],
) -> None:
    """Shared semantic acceptance function used by both builder and external verifier.

    Executes every semantic check exactly once. Builder calls this after constructing
    result + graph but before return. External verifier delegates to this instead of
    duplicating per-index rules.
    """
    from hexagent.optimization.phase3_builder import (
        _expected_ranked_values,
        classify_candidate,
        derive_optimization_result_core_values,
    )

    N = evaluation_input.evaluation_record_count

    # === 1) Tuple exact-length gates ===
    if len(dispositions) != N:
        raise ValueError("dispositions count != N")
    if len(artifacts.preparation_results) != N:
        raise ValueError("preparation_results count != N")
    if len(artifacts.phase2_source_record_descriptors) != N:
        raise ValueError("descriptors count != N")
    if len(evaluation_input.identity_snapshots) != N:
        raise ValueError("identity_snapshots count != N")
    if len(evaluation_input.complete_snapshots) != N:
        raise ValueError("complete_snapshots count != N")
    if len(artifacts.source_bindings) != N:
        raise ValueError("source_bindings count != N")
    if len(artifacts.classification_inputs) != N:
        raise ValueError("classification_inputs count != N")
    if len(artifacts.evidence_failure_bindings) != N:
        raise ValueError("evidence_failure_bindings count != N")
    if len(artifacts.source_failure_bindings) != N:
        raise ValueError("source_failure_bindings count != N")
    if len(artifacts.phase3_failure_bindings) != N:
        raise ValueError("phase3_failure_bindings count != N")
    if len(artifacts.warning_descriptor_tuples) != N:
        raise ValueError("warning_descriptor_tuples count != N")
    if len(artifacts.blocker_descriptor_tuples) != N:
        raise ValueError("blocker_descriptor_tuples count != N")
    if len(artifacts.warning_binding_tuples) != N:
        raise ValueError("warning_binding_tuples count != N")
    if len(artifacts.blocker_binding_tuples) != N:
        raise ValueError("blocker_binding_tuples count != N")
    F = sum(1 for d in dispositions if d.disposition is FEASIBLE)
    if len(ranked_records) != F:
        raise ValueError("ranked_records count != F")

    # === 2) Phase3EvaluationInput.verify_or_raise() ===
    evaluation_input.verify_or_raise(
        sizing_request=artifacts.sizing_request,
        candidates=evaluation_input.materialization_result.candidates,
        source_records=evaluation_input.evaluation_records,
        phase2_source_record_descriptors=artifacts.phase2_source_record_descriptors,
        warning_binding_tuples=artifacts.warning_binding_tuples,
        blocker_binding_tuples=artifacts.blocker_binding_tuples,
        source_failure_bindings=artifacts.source_failure_bindings,
        evidence_failure_bindings=artifacts.evidence_failure_bindings,
    )

    # === 3-5) Per-index artifact matrix, descriptor, identity, complete snapshot replay ===
    for i in range(N):
        rec_i = evaluation_input.evaluation_records[i]
        ids_i = evaluation_input.identity_snapshots[i]
        cs_i = evaluation_input.complete_snapshots[i]
        desc_i = artifacts.phase2_source_record_descriptors[i]
        sb_i = artifacts.source_bindings[i]
        cin_i = artifacts.classification_inputs[i]
        pr = artifacts.preparation_results[i]
        efb_i = artifacts.evidence_failure_bindings[i]
        sfb_i = artifacts.source_failure_bindings[i]
        p3fb_i = artifacts.phase3_failure_bindings[i]

        # 6) Shared per-index artifact matrix
        verify_phase3_index_artifact_matrix(
            source_record=rec_i,
            identity_snapshot=ids_i,
            complete_snapshot=cs_i,
            source_record_descriptor=desc_i,
            source_binding=sb_i,
            classification_input=cin_i,
            preparation_result=pr,
            evidence_failure_binding=efb_i,
            source_failure_binding=sfb_i,
            phase3_failure_binding=p3fb_i,
        )

        # Identity snapshot authoritative replay per-index
        ids_i.verify_or_raise(source_record=rec_i)

        # 7) Warning/blocker descriptor-binding cross-validation
        wdt = artifacts.warning_descriptor_tuples[i]
        bdt = artifacts.blocker_descriptor_tuples[i]
        wbt = artifacts.warning_binding_tuples[i]
        bbt = artifacts.blocker_binding_tuples[i]
        if len(wdt) != len(wbt):
            raise ValueError(f"[{i}] warning descriptor/binding count mismatch")
        for j, (wd, wb) in enumerate(zip(wdt, wbt, strict=False)):
            if wd.owner_sort_key != wb.owner_sort_key:
                raise ValueError(f"[{i}] warn[{j}] sort_key mismatch")
            if wd.original_code != wb.original_code:
                raise ValueError(f"[{i}] warn[{j}] code mismatch")
            if wd.message_payload_digest != wb.message_payload_digest:
                raise ValueError(f"[{i}] warn[{j}] digest mismatch")
        if len(bdt) != len(bbt):
            raise ValueError(f"[{i}] blocker descriptor/binding count mismatch")
        for j, (bd, bb) in enumerate(zip(bdt, bbt, strict=False)):
            if bd.owner_sort_key != bb.owner_sort_key:
                raise ValueError(f"[{i}] block[{j}] sort_key mismatch")
            if bd.original_code != bb.original_code:
                raise ValueError(f"[{i}] block[{j}] code mismatch")
            if bd.message_payload_digest != bb.message_payload_digest:
                raise ValueError(f"[{i}] block[{j}] digest mismatch")

        # Complete snapshot authoritative replay per-index
        if cs_i is not None and desc_i is not None:
            cs_i.verify_or_raise(
                source_record=rec_i,
                identity_snapshot=ids_i,
                source_record_descriptor=desc_i,
                verified_evidence=rec_i.verified_rating_evidence,
                warning_descriptor_bindings=wbt,
                blocker_descriptor_bindings=bbt,
                source_failure_binding=sfb_i,
                evidence_failure_binding=efb_i,
            )

        # Source descriptor authoritative replay per-index
        if desc_i is not None:
            desc_i.verify_or_raise(
                source_record=rec_i,
                identity_snapshot=ids_i,
                verified_evidence=rec_i.verified_rating_evidence,
                source_failure_binding=sfb_i,
            )

        # 8) Source binding authoritative replay per-index
        if sb_i is not None and cs_i is not None and desc_i is not None:
            sb_i.verify_or_raise(
                source_record=rec_i,
                identity_snapshot=ids_i,
                complete_snapshot=cs_i,
                source_record_descriptor=desc_i,
                verified_evidence=rec_i.verified_rating_evidence,
                warning_bindings=wbt,
                blocker_bindings=bbt,
                source_failure_binding=sfb_i,
                evidence_failure_binding=efb_i,
            )

        # 9) Preparation result authoritative replay per-index
        if pr is not None:
            pr.verify_or_raise(
                source_record=rec_i,
                identity_snapshot=ids_i,
                complete_snapshot=cs_i,
                source_binding=sb_i,
                classification_input=cin_i,
                evidence_failure_binding=efb_i,
                source_failure_binding=sfb_i,
                phase3_failure_binding=p3fb_i,
            )

        # 10) READY classification input validation + classify_candidate() replay
        if pr is not None and pr.status is READY:
            if cin_i is None:
                raise ValueError(f"[{i}] READY needs cin")
            if cs_i is None or desc_i is None or sb_i is None:
                raise ValueError(f"[{i}] READY needs complete snapshot, descriptor, binding")
            cin_i.verify_or_raise(
                source_record=rec_i,
                identity_snapshot=ids_i,
                complete_snapshot=cs_i,
                source_record_descriptor=desc_i,
                source_binding=sb_i,
                sizing_request=artifacts.sizing_request,
                candidate=evaluation_input.materialization_result.candidates[i],
            )
            expected_disp = classify_candidate(
                cin_i,
                warning_descriptors=wdt,
                blocker_descriptors=bdt,
                source_failure_binding=sfb_i,
                evidence_failure_binding=efb_i,
            )
            dr = dispositions[i]
            if candidate_disposition_payload(dr) != candidate_disposition_payload(expected_disp):
                raise ValueError(f"[{i}] classify_candidate replay mismatch")

        # 11) FAILED disposition_from_preparation_failure() replay
        if pr is not None and pr.status is FAILED:
            if p3fb_i is None:
                raise ValueError(f"[{i}] FAILED needs phase3_failure_binding")
            expected_disp = disposition_from_preparation_failure(
                source_record=rec_i,
                source_snapshot=cs_i,
                identity_snapshot_digest=ids_i.identity_snapshot_digest,
                candidate=evaluation_input.materialization_result.candidates[i],
                preparation_result=pr,
                phase3_failure_binding=p3fb_i,
                warning_descriptors=wdt,
                blocker_descriptors=bdt,
                source_failure_binding=sfb_i,
                evidence_failure_binding=efb_i,
            )
            dr = dispositions[i]
            if candidate_disposition_payload(dr) != candidate_disposition_payload(expected_disp):
                raise ValueError(f"[{i}] disposition_from_preparation_failure replay mismatch")

        # 12) CandidateDispositionRecord authoritative replay per-index
        dr = dispositions[i]
        dr.verify_or_raise(
            source_record=rec_i,
            source_failure_binding=sfb_i,
            phase3_failure_binding=p3fb_i,
        )

        # Descriptor tuple exact length and value check
        if len(dr.warning_descriptors) != len(wdt):
            raise ValueError(f"[{i}] warning count mismatch")
        for j, wd in enumerate(dr.warning_descriptors):
            b = wdt[j]
            if wd.owner_sort_key != b.owner_sort_key:
                raise ValueError(f"[{i}] warn[{j}] sort_key")
            if wd.original_code != b.original_code:
                raise ValueError(f"[{i}] warn[{j}] code")
            if wd.message_payload_digest != b.message_payload_digest:
                raise ValueError(f"[{i}] warn[{j}] digest")
        if len(dr.blocker_descriptors) != len(bdt):
            raise ValueError(f"[{i}] blocker count mismatch")
        for j, bd in enumerate(dr.blocker_descriptors):
            b = bdt[j]
            if bd.owner_sort_key != b.owner_sort_key:
                raise ValueError(f"[{i}] block[{j}] sort_key")
            if bd.original_code != b.original_code:
                raise ValueError(f"[{i}] block[{j}] code")
            if bd.message_payload_digest != b.message_payload_digest:
                raise ValueError(f"[{i}] block[{j}] digest")

    # === 13) Disposition count recomputation ===
    _verify_all_counts(result, evaluation_input, dispositions)

    # === 14) Strict-stop and termination status recomputation ===
    stop_index = _find_stop_index(evaluation_input)
    expected_ts = derive_termination_status(evaluation_input)
    if result.termination_status is not expected_ts:
        raise ValueError(
            f"termination_status {result.termination_status} != expected {expected_ts}"
        )

    # === 15) Warning/blocker aggregation recomputation ===
    expected_w, expected_b = build_result_message_digest_tuples(
        evaluation_input, dispositions, stop_index
    )
    if tuple(result.ordered_warning_digests) != expected_w:
        raise ValueError("warning digests mismatch")
    if tuple(result.ordered_blocker_digests) != expected_b:
        raise ValueError("blocker digests mismatch")

    # === 16) Frozen ranking-sort reconstruction ===
    feasible_disps = [d for d in dispositions if d.disposition is FEASIBLE]
    if len(feasible_disps) != F:
        raise ValueError("FEASIBLE count != F")
    ranked_keyed = []
    for d in feasible_disps:
        ci = d.evaluation_order_index
        cand = evaluation_input.materialization_result.candidates[ci]
        el = canonical_decimal(Decimal(cand.effective_length_m_canonical))
        pev = d.primary_engineering_value
        assert pev is not None, "primary_engineering_value must be non-None for FEASIBLE"
        a = canonical_decimal(Decimal(pev))
        if result.optimization_objective is MINIMUM_OUTER_HEAT_TRANSFER_AREA:
            key = (a, el, d.source_qualified_candidate_id)
        else:
            key = (el, a, d.source_qualified_candidate_id)
        ranked_keyed.append((key, d, ci))
    ranked_keyed.sort(key=lambda x: x[0])
    for ri, (_, disp, ci) in enumerate(ranked_keyed):
        rr = ranked_records[ri]
        cand = evaluation_input.materialization_result.candidates[ci]
        pv, pf, sv, sf = _expected_ranked_values(disp, cand, result.optimization_objective)
        if rr.rank != ri + 1:
            raise ValueError(f"ranked[{ri}]: rank mismatch")
        if rr.source_qualified_candidate_id != disp.source_qualified_candidate_id:
            raise ValueError(f"ranked[{ri}]: candidate_id")
        if rr.feasibility_digest != disp.feasibility_digest:
            raise ValueError(f"ranked[{ri}]: feasibility digest")
        if rr.primary_objective_value != pv or rr.primary_objective_field != pf:
            raise ValueError(f"ranked[{ri}]: primary")
        if rr.secondary_tie_break_value != sv or rr.secondary_tie_break_field != sf:
            raise ValueError(f"ranked[{ri}]: secondary")
        rr.verify_or_raise(disposition=disp)

    # === 17) Top-N prefix recomputation ===
    TN = min(result.requested_top_n, F)
    if result.ordered_top_n_record_digests != result.ordered_ranked_record_digests[:TN]:
        raise ValueError("Top-N not prefix of ranked")

    # === 18) OptimizationResult.verify_or_raise() ===
    result.verify_or_raise(
        dispositions=dispositions,
        ranked_records=ranked_records,
        source_records=evaluation_input.evaluation_records,
        preparation_results=artifacts.preparation_results,
        source_bindings=artifacts.source_bindings,
    )

    # === 19) Independent core_values derivation and core hash check ===
    derived_core_values = derive_optimization_result_core_values(
        evaluation_input=evaluation_input,
        dispositions=dispositions,
        ranked_records=ranked_records,
        source_bindings=artifacts.source_bindings,
        preparation_results=artifacts.preparation_results,
    )
    derived_core_hash = derived_core_values.compute_hash()
    if result.result_core_hash != derived_core_hash:
        raise ValueError("result_core_hash mismatch vs independently derived core values")

    # === 20) Provenance semantic verifier ===
    verify_phase3_provenance_graph_or_raise(
        graph,
        ei=evaluation_input,
        dispositions=dispositions,
        ranked=ranked_records,
        total_candidate_count=N,
        feasible_candidate_count=F,
        requested_top_n=result.requested_top_n,
        ordered_identity_snapshot_digests=derived_core_values.ordered_identity_snapshot_digests,
        ordered_phase2_source_snapshot_digests=derived_core_values.ordered_phase2_source_snapshot_digests,
        ordered_phase3_source_binding_digests=derived_core_values.ordered_phase3_source_binding_digests,
        ordered_phase3_preparation_result_digests=derived_core_values.ordered_phase3_preparation_result_digests,
        ordered_ranked_record_digests=derived_core_values.ordered_ranked_record_digests,
        ordered_top_n_record_digests=derived_core_values.ordered_top_n_record_digests,
        result_core_hash=result.result_core_hash,
        termination_status=result.termination_status,
        optimization_objective=result.optimization_objective,
        evaluation_input_digest=result.evaluation_input_digest,
        preparation_results=artifacts.preparation_results,
        source_bindings=artifacts.source_bindings,
        core_values=derived_core_values,
    )

    # === 20b) Bind result.provenance_digest to actual graph hash ===
    actual_provenance_digest = graph.compute_hash()
    if result.provenance_digest != actual_provenance_digest:
        raise ValueError("result.provenance_digest mismatch vs graph.compute_hash()")

    # === 21) Envelope hash and UUID recomputation ===
    expected_env = sha256_digest(
        {"result_core_hash": result.result_core_hash, "provenance_digest": result.provenance_digest}
    )
    if result.result_hash != expected_env:
        raise ValueError("envelope hash mismatch")
    expected_id = str(uuid.uuid5(PHASE3_RESULT_NS, result.result_hash))
    if result.optimization_result_id != expected_id:
        raise ValueError("UUID mismatch")


# ═══════════════════════════════════════════════════════════════════════════
# Section 22 — Provenance (P0-12)
# ═══════════════════════════════════════════════════════════════════════════

# === 22.1 Constants ===

PHASE3_PROVENANCE_NS = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


@dataclasses.dataclass(frozen=True, slots=True)
class ExpectedPhase3ProvenanceNode:
    role: str
    node_type: ProvenanceNodeType
    payload_hash: str


def expected_phase3_node_id(role: str, nt: ProvenanceNodeType, ph: str) -> uuid.UUID:
    return uuid.uuid5(PHASE3_PROVENANCE_NS, f"{role}:{nt.value}:{ph}")


# === 22.2 Expected nodes ===


def expected_phase3_provenance_nodes(
    *,
    ei: Phase3EvaluationInput,
    dispositions: tuple[CandidateDispositionRecord, ...],
    ranked: tuple[RankedCandidateRecord, ...],
    total_candidate_count: int,
    feasible_candidate_count: int,
    requested_top_n: int,
    ordered_identity_snapshot_digests: tuple[str, ...],
    ordered_phase2_source_snapshot_digests: tuple[str | None, ...],
    ordered_phase3_source_binding_digests: tuple[str | None, ...],
    ordered_phase3_preparation_result_digests: tuple[str | None, ...],
    ordered_ranked_record_digests: tuple[str, ...],
    ordered_top_n_record_digests: tuple[str, ...],
    result_core_hash: str,
    termination_status: TerminationStatus,
    optimization_objective: OptimizationObjective,
    evaluation_input_digest: str,
) -> tuple[ExpectedPhase3ProvenanceNode, ...]:
    nodes = []
    root_p = sha256_digest(
        {
            "artifact_kind": "phase3_evaluation_input",
            "evaluation_input_digest": ei.evaluation_input_digest,
        }
    )
    nodes.append(ExpectedPhase3ProvenanceNode("root", EXTERNAL, root_p))
    nodes.append(
        ExpectedPhase3ProvenanceNode(
            "sizing_request", INPUT_FILE, ei.sizing_request_identity_digest
        )
    )
    nodes.append(ExpectedPhase3ProvenanceNode("passed_gate", CALCULATION_RUN, ei.gate_digest))
    nodes.append(
        ExpectedPhase3ProvenanceNode("candidate_set", CALCULATION_RUN, ei.candidate_set_digest)
    )
    is_p = sha256_digest(
        {"ordered_identity_snapshot_digests": list(ordered_identity_snapshot_digests)}
    )
    nodes.append(ExpectedPhase3ProvenanceNode("identity_snapshot_set", INTERMEDIATE, is_p))
    css_p = sha256_digest(
        {"ordered_complete_snapshot_digests": list(ordered_phase2_source_snapshot_digests)}
    )
    nodes.append(ExpectedPhase3ProvenanceNode("complete_snapshot_set", INTERMEDIATE, css_p))
    nodes.append(
        ExpectedPhase3ProvenanceNode("evaluation_input", INTERMEDIATE, ei.evaluation_input_digest)
    )
    sb_p = sha256_digest({"ordered_binding_digests": list(ordered_phase3_source_binding_digests)})
    nodes.append(ExpectedPhase3ProvenanceNode("source_binding_set", INTERMEDIATE, sb_p))
    pr_p = sha256_digest(
        {"ordered_prep_result_digests": list(ordered_phase3_preparation_result_digests)}
    )
    nodes.append(ExpectedPhase3ProvenanceNode("preparation_result_set", INTERMEDIATE, pr_p))
    for i, d in enumerate(dispositions):
        nodes.append(
            ExpectedPhase3ProvenanceNode(f"disposition[{i}]", INTERMEDIATE, d.feasibility_digest)
        )
    for i, r in enumerate(ranked):
        nodes.append(
            ExpectedPhase3ProvenanceNode(f"ranked[{i}]", INTERMEDIATE, r.ranked_record_digest)
        )
    tn_p = sha256_digest({"ordered_top_n_record_digests": list(ordered_top_n_record_digests)})
    nodes.append(ExpectedPhase3ProvenanceNode("top_n_selection", INTERMEDIATE, tn_p))
    nodes.append(ExpectedPhase3ProvenanceNode("result_core", RESULT, result_core_hash))
    opt_p = sha256_digest(
        {
            "evaluation_input_digest": evaluation_input_digest,
            "optimization_objective": optimization_objective.value,
            "requested_top_n": requested_top_n,
            "termination_status": termination_status.value,
            "result_core_hash": result_core_hash,
            "phase3_algorithm_version": "task009-phase3-v1",
        }
    )
    nodes.append(ExpectedPhase3ProvenanceNode("optimizer", OPTIMIZER, opt_p))
    return tuple(nodes)


# === 22.3 Expected edges ===


def expected_phase3_provenance_edge_keys(
    *,
    expected_nodes: tuple[ExpectedPhase3ProvenanceNode, ...],
    dispositions: tuple[CandidateDispositionRecord, ...],
    ranked: tuple[RankedCandidateRecord, ...],
    requested_top_n: int,
) -> tuple[tuple[str, str, str], ...]:
    edges: list[tuple[str, str, str]] = []
    uid_map = {
        n.role: str(expected_phase3_node_id(n.role, n.node_type, n.payload_hash))
        for n in expected_nodes
    }

    def uid(r: str) -> str:
        return uid_map[r]

    edges.append((uid("root"), uid("sizing_request"), Phase3ProvenanceRelation.REGULATES.value))
    edges.append(
        (uid("sizing_request"), uid("passed_gate"), Phase3ProvenanceRelation.CONSUMED_BY.value)
    )
    edges.append(
        (uid("passed_gate"), uid("candidate_set"), Phase3ProvenanceRelation.PRODUCED.value)
    )
    edges.append(
        (
            uid("candidate_set"),
            uid("identity_snapshot_set"),
            Phase3ProvenanceRelation.PRODUCED.value,
        )
    )
    edges.append(
        (
            uid("identity_snapshot_set"),
            uid("complete_snapshot_set"),
            Phase3ProvenanceRelation.PRODUCED.value,
        )
    )
    edges.append(
        (
            uid("complete_snapshot_set"),
            uid("evaluation_input"),
            Phase3ProvenanceRelation.CONSUMED_BY.value,
        )
    )
    edges.append(
        (
            uid("evaluation_input"),
            uid("source_binding_set"),
            Phase3ProvenanceRelation.PRODUCED.value,
        )
    )
    edges.append(
        (
            uid("source_binding_set"),
            uid("preparation_result_set"),
            Phase3ProvenanceRelation.PRODUCED.value,
        )
    )
    for i, _ in enumerate(dispositions):
        edges.append(
            (
                uid("evaluation_input"),
                uid(f"disposition[{i}]"),
                Phase3ProvenanceRelation.EVALUATED.value,
            )
        )
    feasible_mask = {
        (d.source_qualified_candidate_id, d.feasibility_digest): i
        for i, d in enumerate(dispositions)
        if d.disposition is FEASIBLE
    }
    for ri, r in enumerate(ranked):
        key = (r.source_qualified_candidate_id, r.feasibility_digest)
        di = feasible_mask.get(key)
        if di is None:
            raise ValueError(f"ranked[{ri}]: no matching FEASIBLE disposition")
        edges.append(
            (
                uid(f"disposition[{di}]"),
                uid(f"ranked[{ri}]"),
                Phase3ProvenanceRelation.RANKED.value,
            )
        )
    edges.append(
        (
            uid("evaluation_input"),
            uid("top_n_selection"),
            Phase3ProvenanceRelation.SELECTED_BY.value,
        )
    )
    for ri in range(min(requested_top_n, len(ranked))):
        edges.append(
            (
                uid(f"ranked[{ri}]"),
                uid("top_n_selection"),
                Phase3ProvenanceRelation.SELECTED.value,
            )
        )
    edges.append(
        (
            uid("top_n_selection"),
            uid("result_core"),
            Phase3ProvenanceRelation.PRODUCED.value,
        )
    )
    edges.append(
        (
            uid("result_core"),
            uid("optimizer"),
            Phase3ProvenanceRelation.EXECUTED_BY.value,
        )
    )
    return tuple(sorted(edges))


# === 22.5 Real builders ===


def build_phase3_provenance_nodes(
    *,
    ei: Phase3EvaluationInput,
    dispositions: tuple[CandidateDispositionRecord, ...],
    ranked: tuple[RankedCandidateRecord, ...],
    total_candidate_count: int,
    feasible_candidate_count: int,
    requested_top_n: int,
    ordered_identity_snapshot_digests: tuple[str, ...],
    ordered_phase2_source_snapshot_digests: tuple[str | None, ...],
    ordered_phase3_source_binding_digests: tuple[str | None, ...],
    ordered_phase3_preparation_result_digests: tuple[str | None, ...],
    ordered_ranked_record_digests: tuple[str, ...],
    ordered_top_n_record_digests: tuple[str, ...],
    result_core_hash: str,
    termination_status: TerminationStatus,
    optimization_objective: OptimizationObjective,
    evaluation_input_digest: str,
) -> tuple[ProvenanceNode, ...]:
    """Build provenance nodes from pre-result values — no dependency on final OptimizationResult."""
    root_p = sha256_digest(
        {
            "artifact_kind": "phase3_evaluation_input",
            "evaluation_input_digest": ei.evaluation_input_digest,
        }
    )
    nodes = [
        ProvenanceNode(
            node_id=expected_phase3_node_id("root", EXTERNAL, root_p),
            node_type=EXTERNAL,
            payload_hash=root_p,
            label="",
            metadata=(),
        ),
        ProvenanceNode(
            node_id=expected_phase3_node_id(
                "sizing_request", INPUT_FILE, ei.sizing_request_identity_digest
            ),
            node_type=INPUT_FILE,
            payload_hash=ei.sizing_request_identity_digest,
            label="",
            metadata=(),
        ),
        ProvenanceNode(
            node_id=expected_phase3_node_id("passed_gate", CALCULATION_RUN, ei.gate_digest),
            node_type=CALCULATION_RUN,
            payload_hash=ei.gate_digest,
            label="",
            metadata=(),
        ),
        ProvenanceNode(
            node_id=expected_phase3_node_id(
                "candidate_set", CALCULATION_RUN, ei.candidate_set_digest
            ),
            node_type=CALCULATION_RUN,
            payload_hash=ei.candidate_set_digest,
            label="",
            metadata=(),
        ),
    ]
    is_p = sha256_digest(
        {"ordered_identity_snapshot_digests": list(ordered_identity_snapshot_digests)}
    )
    nodes.append(
        ProvenanceNode(
            node_id=expected_phase3_node_id("identity_snapshot_set", INTERMEDIATE, is_p),
            node_type=INTERMEDIATE,
            payload_hash=is_p,
            label="",
            metadata=(),
        )
    )
    css_p = sha256_digest(
        {"ordered_complete_snapshot_digests": list(ordered_phase2_source_snapshot_digests)}
    )
    nodes.append(
        ProvenanceNode(
            node_id=expected_phase3_node_id("complete_snapshot_set", INTERMEDIATE, css_p),
            node_type=INTERMEDIATE,
            payload_hash=css_p,
            label="",
            metadata=(),
        )
    )
    nodes.append(
        ProvenanceNode(
            node_id=expected_phase3_node_id(
                "evaluation_input", INTERMEDIATE, ei.evaluation_input_digest
            ),
            node_type=INTERMEDIATE,
            payload_hash=ei.evaluation_input_digest,
            label="",
            metadata=(),
        )
    )
    sb_p = sha256_digest({"ordered_binding_digests": list(ordered_phase3_source_binding_digests)})
    nodes.append(
        ProvenanceNode(
            node_id=expected_phase3_node_id("source_binding_set", INTERMEDIATE, sb_p),
            node_type=INTERMEDIATE,
            payload_hash=sb_p,
            label="",
            metadata=(),
        )
    )
    pr_p = sha256_digest(
        {"ordered_prep_result_digests": list(ordered_phase3_preparation_result_digests)}
    )
    nodes.append(
        ProvenanceNode(
            node_id=expected_phase3_node_id("preparation_result_set", INTERMEDIATE, pr_p),
            node_type=INTERMEDIATE,
            payload_hash=pr_p,
            label="",
            metadata=(),
        )
    )
    for i, d in enumerate(dispositions):
        nid = expected_phase3_node_id(f"disposition[{i}]", INTERMEDIATE, d.feasibility_digest)
        nodes.append(
            ProvenanceNode(
                node_id=nid,
                node_type=INTERMEDIATE,
                payload_hash=d.feasibility_digest,
                label="",
                metadata=(),
            )
        )
    for i, r in enumerate(ranked):
        nid = expected_phase3_node_id(f"ranked[{i}]", INTERMEDIATE, r.ranked_record_digest)
        nodes.append(
            ProvenanceNode(
                node_id=nid,
                node_type=INTERMEDIATE,
                payload_hash=r.ranked_record_digest,
                label="",
                metadata=(),
            )
        )
    tn_p = sha256_digest({"ordered_top_n_record_digests": list(ordered_top_n_record_digests)})
    nodes.append(
        ProvenanceNode(
            node_id=expected_phase3_node_id("top_n_selection", INTERMEDIATE, tn_p),
            node_type=INTERMEDIATE,
            payload_hash=tn_p,
            label="",
            metadata=(),
        )
    )
    nodes.append(
        ProvenanceNode(
            node_id=expected_phase3_node_id("result_core", RESULT, result_core_hash),
            node_type=RESULT,
            payload_hash=result_core_hash,
            label="",
            metadata=(),
        )
    )
    opt_p = sha256_digest(
        {
            "evaluation_input_digest": evaluation_input_digest,
            "optimization_objective": optimization_objective.value,
            "requested_top_n": requested_top_n,
            "termination_status": termination_status.value,
            "result_core_hash": result_core_hash,
            "phase3_algorithm_version": "task009-phase3-v1",
        }
    )
    nodes.append(
        ProvenanceNode(
            node_id=expected_phase3_node_id("optimizer", OPTIMIZER, opt_p),
            node_type=OPTIMIZER,
            payload_hash=opt_p,
            label="",
            metadata=(),
        )
    )
    return tuple(nodes)


def build_phase3_provenance_edges(
    *,
    ei: Phase3EvaluationInput,
    dispositions: tuple[CandidateDispositionRecord, ...],
    ranked: tuple[RankedCandidateRecord, ...],
    requested_top_n: int,
    exp_nodes: tuple[ExpectedPhase3ProvenanceNode, ...],
) -> tuple[ProvenanceEdge, ...]:
    uid_map = {}
    for n in exp_nodes:
        nid = expected_phase3_node_id(n.role, n.node_type, n.payload_hash)
        uid_map[n.role] = str(nid)

    def uid(r: str) -> str:
        return uid_map[r]

    edges: list[ProvenanceEdge] = []
    edges.append(
        ProvenanceEdge(
            source_id=uuid.UUID(uid("root")),
            target_id=uuid.UUID(uid("sizing_request")),
            relation=Phase3ProvenanceRelation.REGULATES.value,
            metadata=(),
        )
    )
    edges.append(
        ProvenanceEdge(
            source_id=uuid.UUID(uid("sizing_request")),
            target_id=uuid.UUID(uid("passed_gate")),
            relation=Phase3ProvenanceRelation.CONSUMED_BY.value,
            metadata=(),
        )
    )
    edges.append(
        ProvenanceEdge(
            source_id=uuid.UUID(uid("passed_gate")),
            target_id=uuid.UUID(uid("candidate_set")),
            relation=Phase3ProvenanceRelation.PRODUCED.value,
            metadata=(),
        )
    )
    edges.append(
        ProvenanceEdge(
            source_id=uuid.UUID(uid("candidate_set")),
            target_id=uuid.UUID(uid("identity_snapshot_set")),
            relation=Phase3ProvenanceRelation.PRODUCED.value,
            metadata=(),
        )
    )
    edges.append(
        ProvenanceEdge(
            source_id=uuid.UUID(uid("identity_snapshot_set")),
            target_id=uuid.UUID(uid("complete_snapshot_set")),
            relation=Phase3ProvenanceRelation.PRODUCED.value,
            metadata=(),
        )
    )
    edges.append(
        ProvenanceEdge(
            source_id=uuid.UUID(uid("complete_snapshot_set")),
            target_id=uuid.UUID(uid("evaluation_input")),
            relation=Phase3ProvenanceRelation.CONSUMED_BY.value,
            metadata=(),
        )
    )
    edges.append(
        ProvenanceEdge(
            source_id=uuid.UUID(uid("evaluation_input")),
            target_id=uuid.UUID(uid("source_binding_set")),
            relation=Phase3ProvenanceRelation.PRODUCED.value,
            metadata=(),
        )
    )
    edges.append(
        ProvenanceEdge(
            source_id=uuid.UUID(uid("source_binding_set")),
            target_id=uuid.UUID(uid("preparation_result_set")),
            relation=Phase3ProvenanceRelation.PRODUCED.value,
            metadata=(),
        )
    )
    for i, _ in enumerate(dispositions):
        edges.append(
            ProvenanceEdge(
                source_id=uuid.UUID(uid("evaluation_input")),
                target_id=uuid.UUID(uid(f"disposition[{i}]")),
                relation=Phase3ProvenanceRelation.EVALUATED.value,
                metadata=(),
            )
        )
    feasible_mask = {
        (d.source_qualified_candidate_id, d.feasibility_digest): i
        for i, d in enumerate(dispositions)
        if d.disposition is FEASIBLE
    }
    for ri, r in enumerate(ranked):
        key = (r.source_qualified_candidate_id, r.feasibility_digest)
        di = feasible_mask.get(key)
        if di is None:
            raise ValueError(f"ranked[{ri}]: no matching FEASIBLE disposition")
        edges.append(
            ProvenanceEdge(
                source_id=uuid.UUID(uid(f"disposition[{di}]")),
                target_id=uuid.UUID(uid(f"ranked[{ri}]")),
                relation=Phase3ProvenanceRelation.RANKED.value,
                metadata=(),
            )
        )
    edges.append(
        ProvenanceEdge(
            source_id=uuid.UUID(uid("evaluation_input")),
            target_id=uuid.UUID(uid("top_n_selection")),
            relation=Phase3ProvenanceRelation.SELECTED_BY.value,
            metadata=(),
        )
    )
    for ri in range(min(requested_top_n, len(ranked))):
        edges.append(
            ProvenanceEdge(
                source_id=uuid.UUID(uid(f"ranked[{ri}]")),
                target_id=uuid.UUID(uid("top_n_selection")),
                relation=Phase3ProvenanceRelation.SELECTED.value,
                metadata=(),
            )
        )
    edges.append(
        ProvenanceEdge(
            source_id=uuid.UUID(uid("top_n_selection")),
            target_id=uuid.UUID(uid("result_core")),
            relation=Phase3ProvenanceRelation.PRODUCED.value,
            metadata=(),
        )
    )
    edges.append(
        ProvenanceEdge(
            source_id=uuid.UUID(uid("result_core")),
            target_id=uuid.UUID(uid("optimizer")),
            relation=Phase3ProvenanceRelation.EXECUTED_BY.value,
            metadata=(),
        )
    )
    return tuple(sorted(edges, key=lambda e: (str(e.source_id), str(e.target_id), e.relation)))


def build_phase3_provenance_graph(
    *,
    ei: Phase3EvaluationInput,
    dispositions: tuple[CandidateDispositionRecord, ...],
    ranked: tuple[RankedCandidateRecord, ...],
    total_candidate_count: int,
    feasible_candidate_count: int,
    requested_top_n: int,
    ordered_identity_snapshot_digests: tuple[str, ...],
    ordered_phase2_source_snapshot_digests: tuple[str | None, ...],
    ordered_phase3_source_binding_digests: tuple[str | None, ...],
    ordered_phase3_preparation_result_digests: tuple[str | None, ...],
    ordered_ranked_record_digests: tuple[str, ...],
    ordered_top_n_record_digests: tuple[str, ...],
    result_core_hash: str,
    termination_status: TerminationStatus,
    optimization_objective: OptimizationObjective,
    evaluation_input_digest: str,
) -> ProvenanceGraph:
    exp_nodes = expected_phase3_provenance_nodes(
        ei=ei,
        dispositions=dispositions,
        ranked=ranked,
        total_candidate_count=total_candidate_count,
        feasible_candidate_count=feasible_candidate_count,
        requested_top_n=requested_top_n,
        ordered_identity_snapshot_digests=ordered_identity_snapshot_digests,
        ordered_phase2_source_snapshot_digests=ordered_phase2_source_snapshot_digests,
        ordered_phase3_source_binding_digests=ordered_phase3_source_binding_digests,
        ordered_phase3_preparation_result_digests=ordered_phase3_preparation_result_digests,
        ordered_ranked_record_digests=ordered_ranked_record_digests,
        ordered_top_n_record_digests=ordered_top_n_record_digests,
        result_core_hash=result_core_hash,
        termination_status=termination_status,
        optimization_objective=optimization_objective,
        evaluation_input_digest=evaluation_input_digest,
    )
    nodes = build_phase3_provenance_nodes(
        ei=ei,
        dispositions=dispositions,
        ranked=ranked,
        total_candidate_count=total_candidate_count,
        feasible_candidate_count=feasible_candidate_count,
        requested_top_n=requested_top_n,
        ordered_identity_snapshot_digests=ordered_identity_snapshot_digests,
        ordered_phase2_source_snapshot_digests=ordered_phase2_source_snapshot_digests,
        ordered_phase3_source_binding_digests=ordered_phase3_source_binding_digests,
        ordered_phase3_preparation_result_digests=ordered_phase3_preparation_result_digests,
        ordered_ranked_record_digests=ordered_ranked_record_digests,
        ordered_top_n_record_digests=ordered_top_n_record_digests,
        result_core_hash=result_core_hash,
        termination_status=termination_status,
        optimization_objective=optimization_objective,
        evaluation_input_digest=evaluation_input_digest,
    )
    edges = build_phase3_provenance_edges(
        ei=ei,
        dispositions=dispositions,
        ranked=ranked,
        requested_top_n=requested_top_n,
        exp_nodes=exp_nodes,
    )
    return ProvenanceGraph(nodes=nodes, edges=edges)


# === 22.6 Semantic verifier ===


def verify_phase3_provenance_graph_or_raise(
    graph: ProvenanceGraph,
    *,
    ei: Phase3EvaluationInput,
    dispositions: tuple[CandidateDispositionRecord, ...],
    ranked: tuple[RankedCandidateRecord, ...],
    total_candidate_count: int,
    feasible_candidate_count: int,
    requested_top_n: int,
    ordered_identity_snapshot_digests: tuple[str, ...],
    ordered_phase2_source_snapshot_digests: tuple[str | None, ...],
    ordered_phase3_source_binding_digests: tuple[str | None, ...],
    ordered_phase3_preparation_result_digests: tuple[str | None, ...],
    ordered_ranked_record_digests: tuple[str, ...],
    ordered_top_n_record_digests: tuple[str, ...],
    result_core_hash: str,
    termination_status: TerminationStatus,
    optimization_objective: OptimizationObjective,
    evaluation_input_digest: str,
    preparation_results: tuple[Phase3CandidatePreparationResult | None, ...],
    source_bindings: tuple[Phase3SourceRecordBinding | None, ...],
    # Accept core_values to independently compute result_core_hash
    core_values: OptimizationResultCoreValues,
) -> None:
    from hexagent.optimization.phase3_builder import derive_optimization_result_core_values

    N = total_candidate_count
    F = feasible_candidate_count
    # 0) Independent authority cardinality gates — mandatory, never bypassed
    if len(dispositions) != N:
        raise ValueError(f"provenance: dispositions length {len(dispositions)} != N {N}")
    if len(ranked) != F:
        raise ValueError(f"provenance: ranked length {len(ranked)} != F {F}")
    if len(preparation_results) != N:
        raise ValueError(
            f"provenance: preparation_results length {len(preparation_results)} != N {N}"
        )
    if len(source_bindings) != N:
        raise ValueError(f"provenance: source_bindings length {len(source_bindings)} != N {N}")
    if len(ordered_identity_snapshot_digests) != N:
        raise ValueError(
            f"provenance: identity_snapshot_digests length "
            f"{len(ordered_identity_snapshot_digests)} != N {N}"
        )
    if len(ordered_phase2_source_snapshot_digests) != N:
        raise ValueError(
            f"provenance: source_snapshot_digests length "
            f"{len(ordered_phase2_source_snapshot_digests)} != N {N}"
        )
    if len(ordered_phase3_preparation_result_digests) != N:
        raise ValueError(
            f"provenance: prep tuple length "
            f"{len(ordered_phase3_preparation_result_digests)} != N {N}"
        )
    if len(ordered_phase3_source_binding_digests) != N:
        raise ValueError(
            f"provenance: sb tuple length {len(ordered_phase3_source_binding_digests)} != N {N}"
        )
    if len(ordered_ranked_record_digests) != F:
        raise ValueError(
            f"provenance: ranked_record_digests length "
            f"{len(ordered_ranked_record_digests)} != F {F}"
        )
    if len(ordered_top_n_record_digests) != min(requested_top_n, F):
        raise ValueError(
            f"provenance: top_n_record_digests length "
            f"{len(ordered_top_n_record_digests)} != min(N,F) "
            f"{min(requested_top_n, F)}"
        )
    # 0a) Independent tuple derivation — derive every tuple from authority artifacts, then compare
    derived_identity_digests = tuple(s.identity_snapshot_digest for s in ei.identity_snapshots)
    if ordered_identity_snapshot_digests != derived_identity_digests:
        raise ValueError("provenance: identity_snapshot_digests mismatch vs independent derivation")
    derived_source_snapshot_digests = tuple(
        cs.snapshot_digest if cs is not None else None for cs in ei.complete_snapshots
    )
    if ordered_phase2_source_snapshot_digests != derived_source_snapshot_digests:
        raise ValueError("provenance: source_snapshot_digests mismatch vs independent derivation")
    derived_sb_digests = tuple(
        sb.binding_digest if sb is not None else None for sb in source_bindings
    )
    if ordered_phase3_source_binding_digests != derived_sb_digests:
        raise ValueError("provenance: source_binding_digests mismatch vs independent derivation")
    derived_prep_digests = tuple(
        pr.preparation_result_digest if pr is not None else None for pr in preparation_results
    )
    if ordered_phase3_preparation_result_digests != derived_prep_digests:
        raise ValueError("provenance: prep_result_digests mismatch vs independent derivation")
    derived_ranked_digests = tuple(r.ranked_record_digest for r in ranked)
    if ordered_ranked_record_digests != derived_ranked_digests:
        raise ValueError("provenance: ranked_record_digests mismatch vs independent derivation")
    derived_top_n = derived_ranked_digests[: min(requested_top_n, F)]
    if ordered_top_n_record_digests != derived_top_n:
        raise ValueError("provenance: top_n_record_digests mismatch vs independent derivation")
    # 0b) Independent scalar derivation
    derived_total = ei.evaluation_record_count
    if total_candidate_count != derived_total:
        raise ValueError(
            f"provenance: total_candidate_count {total_candidate_count} != derived {derived_total}"
        )
    derived_feasible = sum(1 for d in dispositions if d.disposition is FEASIBLE)
    if feasible_candidate_count != derived_feasible:
        raise ValueError(
            f"provenance: feasible_candidate_count "
            f"{feasible_candidate_count} != derived {derived_feasible}"
        )
    derived_requested_top_n = ei.sizing_request_identity.top_n
    if requested_top_n != derived_requested_top_n:
        raise ValueError(
            f"provenance: requested_top_n {requested_top_n} != derived {derived_requested_top_n}"
        )
    derived_objective = ei.sizing_request_identity.optimization_objective
    if optimization_objective != derived_objective:
        raise ValueError("provenance: optimization_objective mismatch vs independent derivation")
    derived_termination = derive_termination_status(ei)
    if termination_status != derived_termination:
        raise ValueError("provenance: termination_status mismatch vs independent derivation")
    derived_ei_digest = ei.evaluation_input_digest
    if evaluation_input_digest != derived_ei_digest:
        raise ValueError("provenance: evaluation_input_digest mismatch vs independent derivation")
    # 0c) Independent core_values derivation — validate ALL fields field-by-field
    expected_core_values = derive_optimization_result_core_values(
        evaluation_input=ei,
        dispositions=dispositions,
        ranked_records=ranked,
        source_bindings=source_bindings,
        preparation_results=preparation_results,
    )
    if core_values != expected_core_values:
        raise ValueError("provenance: core_values mismatch vs independent derivation")
    derived_core_hash = expected_core_values.compute_hash()
    if result_core_hash != derived_core_hash:
        raise ValueError("provenance: result_core_hash mismatch vs core_values.compute_hash()")
    # Source-state positional nullability
    # (prep/sb digests already validated via independent derivation above)
    for i in range(N):
        rec = ei.evaluation_records[i]
        pr = preparation_results[i]
        prep_d = ordered_phase3_preparation_result_digests[i]
        sb_d = ordered_phase3_source_binding_digests[i]
        if rec.candidate_evaluation_state == VERIFIED:
            if prep_d is None:
                raise ValueError(f"provenance[{i}]: VERIFIED must have non-None prep digest")
            if pr is None:
                raise ValueError(f"provenance[{i}]: VERIFIED must have preparation_result")
            if ei.complete_snapshots[i] is None:
                raise ValueError(f"provenance[{i}]: VERIFIED must have complete_snapshot")
        else:
            if prep_d is not None:
                raise ValueError(f"provenance[{i}]: non-VERIFIED must have None prep digest")
            if pr is not None:
                raise ValueError(f"provenance[{i}]: non-VERIFIED must have None preparation_result")
            if sb_d is not None:
                raise ValueError(f"provenance[{i}]: non-VERIFIED must have None sb digest")
    # 1) Build expected nodes from validated tuples
    expected_nodes = expected_phase3_provenance_nodes(
        ei=ei,
        dispositions=dispositions,
        ranked=ranked,
        total_candidate_count=total_candidate_count,
        feasible_candidate_count=feasible_candidate_count,
        requested_top_n=requested_top_n,
        ordered_identity_snapshot_digests=ordered_identity_snapshot_digests,
        ordered_phase2_source_snapshot_digests=ordered_phase2_source_snapshot_digests,
        ordered_phase3_source_binding_digests=ordered_phase3_source_binding_digests,
        ordered_phase3_preparation_result_digests=ordered_phase3_preparation_result_digests,
        ordered_ranked_record_digests=ordered_ranked_record_digests,
        ordered_top_n_record_digests=ordered_top_n_record_digests,
        result_core_hash=result_core_hash,
        termination_status=termination_status,
        optimization_objective=optimization_objective,
        evaluation_input_digest=evaluation_input_digest,
    )
    expected_count = 12 + len(dispositions) + len(ranked)
    if len(expected_nodes) != expected_count:
        raise ValueError(f"expected node count {len(expected_nodes)} != {expected_count}")
    if len(graph.nodes) != expected_count:
        raise ValueError(f"graph node count {len(graph.nodes)} != {expected_count}")
    expected_ids = {}
    for n in expected_nodes:
        eid = expected_phase3_node_id(n.role, n.node_type, n.payload_hash)
        if eid in expected_ids:
            raise ValueError(f"duplicate expected ID for role {n.role}")
        expected_ids[eid] = n
    actual_by_id: dict[uuid.UUID, ProvenanceNode] = {}
    for anode in graph.nodes:
        aid = anode.node_id
        if aid in actual_by_id:
            raise ValueError("duplicate actual node ID")
        actual_by_id[aid] = anode
    for eid, exp in expected_ids.items():
        actual = actual_by_id.get(eid)
        if actual is None:
            raise ValueError(f"missing node: {exp.role}")
        if actual.node_type != exp.node_type:
            raise ValueError(f"{exp.role}: type mismatch")
        if actual.payload_hash != exp.payload_hash:
            raise ValueError(f"{exp.role}: payload hash mismatch")
        if actual.label != "":
            raise ValueError(f"{exp.role}: label not empty")
        if actual.metadata != ():
            raise ValueError(f"{exp.role}: metadata not empty")
    extra = set(actual_by_id) - set(expected_ids)
    if extra:
        raise ValueError(f"extra nodes: {len(extra)}")
    expected_edges = expected_phase3_provenance_edge_keys(
        expected_nodes=expected_nodes,
        dispositions=dispositions,
        ranked=ranked,
        requested_top_n=requested_top_n,
    )
    actual_edges = tuple(
        sorted((str(e.source_id), str(e.target_id), e.relation) for e in graph.edges)
    )
    if len(actual_edges) != len(set(actual_edges)):
        raise ValueError("duplicate edges")
    if actual_edges != expected_edges:
        raise ValueError("edge set mismatch")
    for e in graph.edges:
        if e.metadata != ():
            raise ValueError("edge metadata not empty")
    root_id = expected_phase3_node_id(
        expected_nodes[0].role,
        expected_nodes[0].node_type,
        expected_nodes[0].payload_hash,
    )
    children: dict[uuid.UUID, list[uuid.UUID]] = {n.node_id: [] for n in graph.nodes}
    for e in graph.edges:
        children[e.source_id].append(e.target_id)
    visited: set[uuid.UUID] = set()
    queue: list[uuid.UUID] = [root_id]
    while queue:
        nid = queue.pop(0)
        if nid in visited:
            continue
        visited.add(nid)
        queue.extend(children.get(nid, []))
    if len(visited) != len(graph.nodes):
        raise ValueError("unreachable nodes")
    # Cycle detection: DFS coloring
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n.node_id: WHITE for n in graph.nodes}

    def dfs(u: uuid.UUID) -> bool:
        color[u] = GRAY
        for v in children.get(u, []):
            if color.get(v) == GRAY:
                return True
            if color.get(v) == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False

    for nid in list(color):
        if color[nid] == WHITE and dfs(nid):
            raise ValueError("cycle detected")
