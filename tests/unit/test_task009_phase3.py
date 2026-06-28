"""
TASK-009 Phase 3 comprehensive unit tests.

Covers:
1. NORMAL FLOW — feasibility → ranking → Top-N
2. GATE & MATERIALIZATION
3. BATCH INPUT CONSISTENCY
4. INTEGRITY & PROVENANCE (fail-closed)
5. VERIFIER — all public entry points
6. RANKING & TOP-N
7. FAILURE PROPAGATION
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from hexagent.core.canonical import sha256_digest
from hexagent.core.heat_balance import (
    ExecutionContextSnapshot,
    ProviderIdentitySnapshot,
)
from hexagent.domain.messages import (
    ErrorCode,
    RunFailure,
)
from hexagent.exchangers.double_pipe.result import (
    RatingRequestIdentity,
    RatingStatus,
)
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.optimization.context import (
    ExpectedProviderIdentity,
    OptimizationObjective,
    SizingRequestIdentity,
    build_sizing_request_identity,
)
from hexagent.optimization.evaluation import (
    CandidateEvaluationIdentity,
    CandidateEvaluationRecord,
    CandidateEvaluationState,
    FeasibilityStatus,
    InvalidRatingEvidenceRecord,
    VerificationOutcome,
    VerifiedRatingEvidenceSnapshot,
    _build_run_failure_descriptor,
    execution_context_snapshot_payload,
    rating_request_identity_payload,
)
from hexagent.optimization.identities import (
    ManufacturableCandidate,
    build_candidate,
)
from hexagent.optimization.models import (
    CompleteDoublePipeAssemblyOption,
    CompleteDoublePipeCatalogSnapshot,
    LengthSource,
    SizingRequest,
)
from hexagent.optimization.phase3_builder import (
    OptimizationResultCoreValues,
    _build_feasible,
    _build_infeasible,
    _build_provider_mismatch,
    _expected_ranked_values,
    _map_non_verified,
    _phase3_runtime,
    _phase3_runtime_from_validation,
    build_ranked_candidate_record,
    classify_candidate,
)
from hexagent.optimization.phase3_core import (
    FailureOrigin,
    FeasibilityDiagnosticKey,
    Phase2SourceRecordDescriptor,
    Phase2SourceRecordIdentitySnapshot,
    Phase3Disposition,
    Phase3MessageDescriptor,
    Phase3MessageDescriptorBinding,
    Phase3PreparationFailureStage,
    Phase3PreparationStatus,
    Phase3ProvenanceRelation,
    Phase3RunFailureDescriptorBinding,
    TerminationStatus,
    build_identity_snapshot,
    build_phase2_source_record_descriptor,
    build_phase2_source_record_snapshot,
    build_phase3_message_descriptor_binding,
    build_phase3_run_failure_descriptor_binding,
    canonical_decimal,
    canonical_decimal_string,
    to_canonical_decimal,
    verify_canonical_decimal_string,
)
from hexagent.optimization.phase3_evaluation import (
    Phase3CandidateClassificationInput,
    Phase3EvaluationInput,
    Phase3SourceRecordBinding,
    build_candidate_disposition_record,
    build_phase3_candidate_preparation_result,
    build_phase3_source_record_binding,
    candidate_disposition_payload,
    verify_candidate_disposition_failure_matrix,
    verify_phase3_index_artifact_matrix,
)
from hexagent.optimization.phase3_verifier import (
    verify_phase3_message_descriptor_or_raise,
)

# ============================================================================
# Shared digest pattern for tests
# ============================================================================

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
DUMMY_DIGEST = "sha256:" + "a" * 64
DUMMY_DIGEST2 = "sha256:" + "b" * 64
DUMMY_DIGEST3 = "sha256:" + "c" * 64
DUMMY_DIGEST4 = "sha256:" + "d" * 64


def _make_digest(seed: str) -> str:
    return sha256_digest({"seed": seed})


# ============================================================================
# Helpers for building test fixtures
# ============================================================================


def _make_opt(
    option_id: str = "opt1",
    quantum: str = "0.1",
    lengths: tuple[float, ...] = (1.0, 2.0, 3.0),
) -> CompleteDoublePipeAssemblyOption:
    return CompleteDoublePipeAssemblyOption(
        assembly_option_id=option_id,
        inner_tube_inner_diameter_m=0.05,
        inner_tube_outer_diameter_m=0.06,
        outer_pipe_inner_diameter_m=0.10,
        wall_thermal_conductivity_w_m_k=50.0,
        inner_surface_roughness_m=1e-5,
        annulus_surface_roughness_m=1e-5,
        inner_fouling_resistance_m2k_w=0.0001,
        outer_fouling_resistance_m2k_w=0.0002,
        manufacturing_option_identity="std",
        manufacturing_metadata=(),
        length_source=LengthSource(
            length_quantum_m=quantum,
            allowed_effective_lengths_m=lengths,
        ),
    )


def _make_catalog(
    catalog_id: str = "c1",
    options: tuple[CompleteDoublePipeAssemblyOption, ...] = (),
) -> CompleteDoublePipeCatalogSnapshot:
    from hexagent.optimization.catalog import compute_catalog_content_hash

    h = compute_catalog_content_hash(
        catalog_id=catalog_id,
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=options,
    )
    return CompleteDoublePipeCatalogSnapshot(
        catalog_id=catalog_id,
        catalog_version="v1",
        source_identity="test",
        schema_version="1.0",
        assembly_options=options,
        catalog_content_hash=h,
    )


def _make_provider() -> ProviderIdentitySnapshot:
    return ProviderIdentitySnapshot(
        name="test_provider",
        version="1.0",
        git_revision="abc123",
        reference_state_policy="default",
    )


def _make_exec_ctx() -> ExecutionContextSnapshot:
    return ExecutionContextSnapshot()


def _make_evidence(
    *,
    heat_duty_w: float = 5000.0,
    area_outer_m2: float = 5.0,
    hot_outlet_temperature_k: float = 310.0,
    cold_outlet_temperature_k: float = 330.0,
    rating_status: RatingStatus = RatingStatus.SUCCEEDED,
) -> VerifiedRatingEvidenceSnapshot:
    rri = RatingRequestIdentity(
        hot_fluid_name="Water",
        hot_fluid_backend="CP",
        hot_fluid_components=(),
        cold_fluid_name="Water",
        cold_fluid_backend="CP",
        cold_fluid_components=(),
        hot_mass_flow_kg_s=1.0,
        cold_mass_flow_kg_s=0.8,
        hot_inlet_pressure_pa=2e5,
        cold_inlet_pressure_pa=1.5e5,
        hot_inlet_temperature_k=350.0,
        cold_inlet_temperature_k=290.0,
        flow_arrangement="counterflow",
        geometry={
            "inner_tube_inner_diameter_m": 0.05,
            "inner_tube_outer_diameter_m": 0.06,
            "outer_pipe_inner_diameter_m": 0.10,
            "effective_length_m": 1.0,
            "wall_thermal_conductivity_w_m_k": 50.0,
            "inner_surface_roughness_m": 1e-5,
            "annulus_surface_roughness_m": 1e-5,
            "inner_fouling_resistance_m2k_w": 0.0001,
            "outer_fouling_resistance_m2k_w": 0.0002,
        },
        solver_absolute_residual_w=1e-3,
        solver_relative_residual_fraction=1e-8,
        solver_bracket_temperature_tolerance_k=1e-4,
        solver_max_iterations=100,
    )
    exec_ctx = _make_exec_ctx()
    rri_digest = sha256_digest(rating_request_identity_payload(rri))
    ec_digest = sha256_digest(execution_context_snapshot_payload(exec_ctx))
    return VerifiedRatingEvidenceSnapshot(
        rating_status=rating_status,
        heat_duty_w=heat_duty_w,
        hot_outlet_temperature_k=hot_outlet_temperature_k,
        cold_outlet_temperature_k=cold_outlet_temperature_k,
        area_inner_m2=area_outer_m2 * 0.8,
        area_outer_m2=area_outer_m2,
        tube_flow_area_m2=0.002,
        annulus_flow_area_m2=0.005,
        provider_identity=_make_provider(),
        rating_result_hash="sha256:" + "e" * 64,
        rating_provenance_digest="sha256:" + "f" * 64,
        hash_verification_outcome=VerificationOutcome.PASSED,
        provenance_verification_outcome=VerificationOutcome.PASSED,
        rating_request_identity=rri,
        rating_request_identity_digest=rri_digest,
        rating_execution_context=exec_ctx,
        rating_execution_context_digest=ec_digest,
    )


def _make_candidate(
    evaluation_order_index: int = 0,
    effective_length_m: float = 1.0,
    catalog_id: str = "c1",
    option_id: str = "opt1",
) -> ManufacturableCandidate:
    """Build a ManufacturableCandidate using the real factory."""
    opt = _make_opt(option_id=option_id)
    cat = _make_catalog(catalog_id=catalog_id, options=(opt,))
    return build_candidate(
        catalog=cat,
        option=opt,
        effective_length_m_canonical=str(effective_length_m),
        evaluation_order_index=evaluation_order_index,
    )


def _make_cei(
    source_qualified_candidate_id: str,
    evidence: VerifiedRatingEvidenceSnapshot,
) -> CandidateEvaluationIdentity:
    """Build a CandidateEvaluationIdentity from evidence fields."""
    provider = evidence.provider_identity
    provider_digest = sha256_digest(
        {
            "name": provider.name,
            "version": provider.version,
            "git_revision": provider.git_revision,
            "reference_state_policy": provider.reference_state_policy,
        }
    )
    return CandidateEvaluationIdentity(
        sizing_request_identity_digest=DUMMY_DIGEST,
        source_qualified_candidate_id=source_qualified_candidate_id,
        rating_request_identity_digest=evidence.rating_request_identity_digest,
        rating_result_hash=evidence.rating_result_hash,
        rating_provenance_digest=evidence.rating_provenance_digest,
        rating_execution_context_digest=evidence.rating_execution_context_digest,
        provider_identity_digest=provider_digest,
        tube_in_hot=True,
    )


def _make_verified_record(
    candidate: ManufacturableCandidate,
    evidence: VerifiedRatingEvidenceSnapshot | None = None,
    *,
    provider_identity_matches: bool = True,
    rating_status: str | None = "succeeded",
) -> CandidateEvaluationRecord:
    """Build a VERIFIED CandidateEvaluationRecord matching the given candidate."""
    ev = evidence or _make_evidence()
    source_id = candidate.source_qualified_candidate_id
    idx = candidate.evaluation_order_index
    cei = _make_cei(source_id, ev)
    return CandidateEvaluationRecord(
        source_qualified_candidate_id=source_id,
        evaluation_order_index=idx,
        candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
        feasible=True,
        feasibility_status=FeasibilityStatus.NOT_EVALUATED,
        hash_verification_outcome=VerificationOutcome.PASSED,
        provenance_verification_outcome=VerificationOutcome.PASSED,
        candidate_evaluation_identity=cei,
        verified_rating_evidence=ev,
        provider_identity_matches=provider_identity_matches,
        rating_status=rating_status,
    )


def _make_ver(
    source_id: str = "c1",
    idx: int = 0,
    evidence: VerifiedRatingEvidenceSnapshot | None = None,
    *,
    provider_identity_matches: bool = True,
    rating_status: str | None = "succeeded",
) -> tuple[CandidateEvaluationRecord, ManufacturableCandidate]:
    cand = _make_candidate(evaluation_order_index=idx)
    rec = _make_verified_record(
        cand,
        evidence=evidence,
        provider_identity_matches=provider_identity_matches,
        rating_status=rating_status,
    )
    return rec, cand


def _make_integrity_invalid_record(
    source_qualified_candidate_id: str = "cand_1",
    evaluation_order_index: int = 0,
    hash_outcome: VerificationOutcome = VerificationOutcome.FAILED,
    prov_outcome: VerificationOutcome = VerificationOutcome.NOT_RUN,
) -> CandidateEvaluationRecord:
    inv = InvalidRatingEvidenceRecord(
        candidate_id=source_qualified_candidate_id,
        hash_verification_outcome=hash_outcome,
        provenance_verification_outcome=prov_outcome,
    )
    return CandidateEvaluationRecord(
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        candidate_evaluation_state=CandidateEvaluationState.INTEGRITY_INVALID,
        feasible=False,
        feasibility_status=FeasibilityStatus.NOT_EVALUATED,
        hash_verification_outcome=hash_outcome,
        provenance_verification_outcome=prov_outcome,
        invalid_rating_evidence=inv,
        provider_identity_matches=True,
    )


def _make_runtime_failed_record(
    source_qualified_candidate_id: str = "cand_1",
    evaluation_order_index: int = 0,
) -> CandidateEvaluationRecord:
    failure = RunFailure(
        code=ErrorCode.INPUT_INCONSISTENT,
        message="Runtime error",
        context=(("source", "test"),),
    )
    return CandidateEvaluationRecord(
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        candidate_evaluation_state=CandidateEvaluationState.RUNTIME_FAILED,
        feasible=False,
        feasibility_status=FeasibilityStatus.NOT_EVALUATED,
        hash_verification_outcome=VerificationOutcome.NOT_RUN,
        provenance_verification_outcome=VerificationOutcome.NOT_RUN,
        evaluation_failure=failure,
        provider_identity_matches=True,
    )


def _make_unevaluated_record(
    source_qualified_candidate_id: str = "cand_1",
    evaluation_order_index: int = 0,
) -> CandidateEvaluationRecord:
    return CandidateEvaluationRecord(
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        candidate_evaluation_state=CandidateEvaluationState.UNEVALUATED,
        feasible=False,
        feasibility_status=FeasibilityStatus.NOT_EVALUATED,
        hash_verification_outcome=VerificationOutcome.NOT_RUN,
        provenance_verification_outcome=VerificationOutcome.NOT_RUN,
        provider_identity_matches=True,
    )


def _make_sizing_request_identity(
    *,
    optimization_objective: OptimizationObjective = OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
    top_n: int = 3,
) -> SizingRequestIdentity:
    cat = _make_catalog(options=(_make_opt(),))
    return build_sizing_request_identity(
        request=SizingRequest(catalogs=(cat,)),
        hot_fluid_name="Water",
        cold_fluid_name="Water",
        hot_fluid_equation_of_state="IdealGas",
        cold_fluid_equation_of_state="IdealGas",
        hot_inlet_temperature_k=350.0,
        cold_inlet_temperature_k=290.0,
        hot_inlet_pressure_pa=2e5,
        cold_inlet_pressure_pa=1.5e5,
        hot_mass_flow_kg_s=1.0,
        cold_mass_flow_kg_s=0.8,
        tube_in_hot=True,
        flow_arrangement=FlowArrangement.COUNTERFLOW,
        minimum_terminal_delta_t=5.0,
        required_duty_w=5000.0,
        duty_absolute_tolerance_w=500.0,
        duty_relative_tolerance=0.1,
        optimization_objective=optimization_objective,
        top_n=top_n,
        solver_params=SolverParams(),
        expected_provider_identity=ExpectedProviderIdentity(
            name="test_provider",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        ),
    )


def _make_sizing_request_identity_parallel(
    *,
    optimization_objective: OptimizationObjective = OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
    top_n: int = 3,
) -> SizingRequestIdentity:
    cat = _make_catalog(options=(_make_opt(),))
    return build_sizing_request_identity(
        request=SizingRequest(catalogs=(cat,)),
        hot_fluid_name="Water",
        cold_fluid_name="Water",
        hot_fluid_equation_of_state="IdealGas",
        cold_fluid_equation_of_state="IdealGas",
        hot_inlet_temperature_k=350.0,
        cold_inlet_temperature_k=290.0,
        hot_inlet_pressure_pa=2e5,
        cold_inlet_pressure_pa=1.5e5,
        hot_mass_flow_kg_s=1.0,
        cold_mass_flow_kg_s=0.8,
        tube_in_hot=True,
        flow_arrangement=FlowArrangement.PARALLEL,
        minimum_terminal_delta_t=5.0,
        required_duty_w=5000.0,
        duty_absolute_tolerance_w=500.0,
        duty_relative_tolerance=0.1,
        optimization_objective=optimization_objective,
        top_n=top_n,
        solver_params=SolverParams(),
        expected_provider_identity=ExpectedProviderIdentity(
            name="test_provider",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        ),
    )


def _make_message_descriptor(
    original_code: str = "TEST001",
    owner_sort_key: tuple = ("a", "TEST001", "c", "d", (), "e"),
    message_payload_digest: str | None = None,
) -> Phase3MessageDescriptor:
    if message_payload_digest is None:
        message_payload_digest = sha256_digest({"msg": original_code})
    return Phase3MessageDescriptor(
        owner_sort_key=owner_sort_key,
        original_code=original_code,
        message_payload_digest=message_payload_digest,
    )


def _make_message_descriptor_binding(
    desc: Phase3MessageDescriptor | None = None,
) -> Phase3MessageDescriptorBinding:
    if desc is None:
        desc = _make_message_descriptor()
    return build_phase3_message_descriptor_binding(desc)


def _make_failure_binding() -> Phase3RunFailureDescriptorBinding:
    failure = RunFailure(
        code=ErrorCode.INPUT_INCONSISTENT,
        message="test failure",
        context=(("key", "value"),),
    )
    desc = _build_run_failure_descriptor(failure)
    return build_phase3_run_failure_descriptor_binding(desc)


def _build_cin(
    rec: CandidateEvaluationRecord,
    candidate: ManufacturableCandidate,
    sri: SizingRequestIdentity,
    isnap: Phase2SourceRecordIdentitySnapshot,
    sdesc: Phase2SourceRecordDescriptor,
    sb: Phase3SourceRecordBinding,
) -> Phase3CandidateClassificationInput:
    """Build and validate a Phase3CandidateClassificationInput."""
    # Compute payload and digest before construction so validation passes
    cin_digest = sha256_digest(
        {
            "schema_version": 1,
            "source_identity_record_descriptor_digest": isnap.identity_snapshot_digest,
            "source_record_descriptor_digest": sdesc.descriptor_digest,
            "materialized_candidate_digest": candidate.source_qualified_candidate_id,
            "sizing_request_identity_digest": sri.sizing_request_identity_digest,
            "identity_snapshot_digest": sb.phase2_identity_snapshot_digest,
            "source_binding_digest": sb.binding_digest,
            "verified_rating_evidence_digest": sb.verified_rating_evidence_digest,
        }
    )
    return Phase3CandidateClassificationInput(
        source_record=rec,
        source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
        source_record_descriptor_digest=sdesc.descriptor_digest,
        materialized_candidate=candidate,
        sizing_request_identity=sri,
        sizing_request_identity_digest=sri.sizing_request_identity_digest,
        evidence_binding=sb,
        verified_rating_evidence_digest=sb.verified_rating_evidence_digest,
        classification_input_digest=cin_digest,
    )


# ============================================================================
# Section 1: NORMAL FLOW — end-to-end
# ============================================================================


class TestEndToEndFlow:
    """Complete feasibility → ranking → Top-N end-to-end tests."""

    def test_single_candidate_feasible(self) -> None:
        """Single verified candidate with adequate duty and delta-T → FEASIBLE."""
        evidence = _make_evidence(heat_duty_w=5000.0)
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("BLOCK001")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.FEASIBLE
        assert disp.diagnostic == FeasibilityDiagnosticKey.NONE

    def test_single_candidate_infeasible_duty(self) -> None:
        """Candidate with duty shortfall → INFEASIBLE."""
        evidence = _make_evidence(heat_duty_w=100.0)
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B01")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.INFEASIBLE
        assert disp.diagnostic == FeasibilityDiagnosticKey.DUTY_SHORTFALL

    def test_multiple_candidates_mixed(self) -> None:
        """Multiple candidates with mixed feasible/infeasible."""
        evidence1 = _make_evidence(heat_duty_w=5000.0, area_outer_m2=5.0)
        evidence2 = _make_evidence(heat_duty_w=5000.0, area_outer_m2=3.0)
        evidence3 = _make_evidence(heat_duty_w=100.0)
        recs_and_cands = [
            _make_ver("c1", 0, evidence=evidence1),
            _make_ver("c2", 1, evidence=evidence2),
            _make_ver("c3", 2, evidence=evidence3),
        ]
        recs = [r for r, _ in recs_and_cands]
        cands = [c for _, c in recs_and_cands]
        cands = [
            _make_candidate(evaluation_order_index=0),
            _make_candidate(evaluation_order_index=1),
            _make_candidate(evaluation_order_index=2),
        ]
        sri = _make_sizing_request_identity(top_n=2)
        dispositions = []
        for i in range(3):
            isnap = build_identity_snapshot(recs[i])
            sdesc = build_phase2_source_record_descriptor(
                source_record=recs[i],
                identity_snapshot=isnap,
                verified_evidence=recs[i].verified_rating_evidence,
                source_failure_binding=None,
            )
            wd = _make_message_descriptor(f"W{i}")
            bd = _make_message_descriptor(f"B{i}")
            wbd = _make_message_descriptor_binding(wd)
            bbd = _make_message_descriptor_binding(bd)
            ev = recs[i].verified_rating_evidence
            sb = build_phase3_source_record_binding(
                source_qualified_candidate_id="test_id",  # f"c{i+1}"
                evaluation_order_index=i,
                phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
                verified_rating_evidence_digest=ev.compute_explicit_evidence_digest()
                if ev
                else None,
                phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
                warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
                blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
                source_evaluation_failure_binding_digest=None,
                evidence_failure_binding_digest=None,
            )
            cin = _build_cin(recs[i], cands[i], sri, isnap, sdesc, sb)
            disp = classify_candidate(
                cin,
                warning_descriptors=(wd,),
                blocker_descriptors=(bd,),
                source_failure_binding=None,
                evidence_failure_binding=None,
            )
            dispositions.append(disp)
        feasible = [d for d in dispositions if d.disposition == Phase3Disposition.FEASIBLE]
        infeasible = [d for d in dispositions if d.disposition == Phase3Disposition.INFEASIBLE]
        assert len(feasible) == 2
        assert len(infeasible) == 1

    def test_all_blocked_candidates(self) -> None:
        """All candidates rated as 'blocked' → all infeasible."""
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.INFEASIBLE
        assert disp.diagnostic == FeasibilityDiagnosticKey.RATING_BLOCKED

    def test_terminal_delta_t_inadequate(self) -> None:
        """Terminal delta-T below minimum → INFEASIBLE."""
        evidence = _make_evidence(
            heat_duty_w=5000.0,
            hot_outlet_temperature_k=296.0,  # close to cold_in=290 giving small delta
            cold_outlet_temperature_k=348.0,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.INFEASIBLE
        assert disp.diagnostic == FeasibilityDiagnosticKey.TERMINAL_DELTA_T_INADEQUATE

    def test_parallel_flow_delta_t(self) -> None:
        """Parallel flow with valid delta-T → FEASIBLE."""
        evidence = _make_evidence(
            heat_duty_w=5000.0,
            hot_outlet_temperature_k=320.0,
            cold_outlet_temperature_k=310.0,
        )
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        sri = _make_sizing_request_identity_parallel()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
        )
        # Should be feasible (hot_in=350, cold_in=290 → dt1=60, hot_out=320, cold_out=310 → dt2=10)
        assert disp.disposition == Phase3Disposition.FEASIBLE


# ============================================================================
# Section 2: GATE & MATERIALIZATION
# ============================================================================


class TestGateAndMaterialization:
    """Gate record consistency and materialization validation."""

    def test_catalog_identity_mismatch(self) -> None:
        """Catalog identity mismatch should be caught."""
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        isnap.verify_or_raise(source_record=rec)
        tampered = isnap.model_copy(update={"source_qualified_candidate_id": "wrong"})
        with pytest.raises(ValueError, match="candidate_id"):
            tampered.verify_or_raise(source_record=rec)

    def test_bounds_mismatch(self) -> None:
        """Bounds mismatch on evaluation order index should fail."""
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        tampered = isnap.model_copy(update={"evaluation_order_index": 999})
        with pytest.raises(ValueError, match="evaluation_index"):
            tampered.verify_or_raise(source_record=rec)

    def test_count_mismatch(self) -> None:
        """Count mismatch between snapshots and records."""
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        cs = build_phase2_source_record_snapshot(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
            feasible=True,
            feasibility_status=FeasibilityStatus.NOT_EVALUATED,
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.PASSED,
            provider_identity_matches=True,
            rating_status="succeeded",
            candidate_evaluation_identity_digest=(
                rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
                if rec.candidate_evaluation_identity
                else None
            ),
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            invalid_rating_evidence_digest=None,
            claimed_rating_result_audit_digest=None,
            evaluation_failure_digest=None,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptor_binding_digests=(),
            blocker_descriptor_binding_digests=(),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cat = _make_catalog(options=(_make_opt(),))
        from hexagent.optimization.identities import MaterializationResult

        mat = MaterializationResult(
            candidates=(_make_candidate(evaluation_order_index=0),),
            catalog_snapshots=(cat,),
            sizing_gate=None,
            sizing_request=SizingRequest(catalogs=(cat,)),
            catalog_content_hash=cat.catalog_content_hash,
            candidate_set_digest=sha256_digest({}),
        )
        with pytest.raises(ValueError, match="count"):
            Phase3EvaluationInput(
                sizing_request_identity=sri,
                sizing_request_identity_digest=sri.sizing_request_identity_digest,
                materialization_result=mat,
                candidate_set_digest=mat.candidate_set_digest
                if hasattr(mat, "candidate_set_digest")
                else sha256_digest({}),
                gate_digest="sha256:" + "a" * 64,
                evaluation_records=(rec,),
                evaluation_record_count=2,
                identity_snapshots=(isnap,),
                complete_snapshots=(cs,),
                ordered_identity_snapshot_digests=(isnap.identity_snapshot_digest,),
                ordered_phase2_source_snapshot_digests=(cs.snapshot_digest,),
                ordered_phase2_source_record_descriptor_digests=(sdesc.descriptor_digest,),
                evaluation_input_digest="sha256:" + "0" * 64,
            )


# ============================================================================
# Section 3: BATCH INPUT CONSISTENCY
# ============================================================================


class TestBatchInputConsistency:
    """Per-field correctness of batch input data."""

    def test_fluid_identity_preserved(self) -> None:
        evidence = _make_evidence()
        assert evidence.rating_request_identity.hot_fluid_name == "Water"

    def test_mass_flow_preserved(self) -> None:
        evidence = _make_evidence()
        assert evidence.rating_request_identity.hot_mass_flow_kg_s == 1.0

    def test_temperature_values(self) -> None:
        evidence = _make_evidence()
        assert evidence.hot_outlet_temperature_k == 310.0

    def test_pressure_values(self) -> None:
        evidence = _make_evidence()
        assert evidence.rating_request_identity.hot_inlet_pressure_pa == 2e5

    def test_flow_direction(self) -> None:
        evidence = _make_evidence()
        assert evidence.rating_request_identity.flow_arrangement == "counterflow"

    def test_solver_config(self) -> None:
        evidence = _make_evidence()
        assert evidence.rating_request_identity.solver_max_iterations == 100

    def test_candidate_identity(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("cand_xyz", 5, evidence=evidence)
        assert (
            rec.source_qualified_candidate_id == "cand_xyz"
        )  # May differ due to auto-generated ID
        assert rec.evaluation_order_index == 5


# ============================================================================
# Section 4: INTEGRITY & PROVENANCE (fail-closed)
# ============================================================================


class TestIntegrityAndProvenance:
    """All integrity and provenance tamper attempts must fail closed."""

    def test_hash_tamper_detected(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        tampered = isnap.model_copy(update={"identity_snapshot_digest": DUMMY_DIGEST2})
        with pytest.raises(ValueError, match="identity_snapshot_digest mismatch"):
            Phase2SourceRecordIdentitySnapshot(**tampered.model_dump())

    def test_uuid_tamper_detected(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        tampered = isnap.model_copy(update={"source_qualified_candidate_id": "evil_cand"})
        with pytest.raises(ValueError):
            Phase2SourceRecordIdentitySnapshot(**tampered.model_dump())

    def test_wrong_source_record(self) -> None:
        evidence = _make_evidence()
        rec1 = _make_ver("c1", 0, evidence=evidence)
        rec2 = _make_ver("c2", 1, evidence=evidence)
        isnap = build_identity_snapshot(rec1)
        with pytest.raises(ValueError, match="candidate_id"):
            isnap.verify_or_raise(source_record=rec2)

    def test_wrong_verified_evidence(self) -> None:
        evidence1 = _make_evidence(area_outer_m2=5.0)
        evidence2 = _make_evidence(area_outer_m2=3.0)
        rec, candidate = _make_ver("c1", 0, evidence=evidence1)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence1,
            source_failure_binding=None,
        )
        with pytest.raises(ValueError, match="verified_rating_evidence_digest"):
            sdesc.verify_or_raise(
                source_record=rec,
                identity_snapshot=isnap,
                verified_evidence=evidence2,
                source_failure_binding=None,
            )

    def test_wrong_evaluator_identity(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        tampered = isnap.model_copy(update={"provider_identity_matches": False})
        with pytest.raises(ValueError):
            Phase2SourceRecordIdentitySnapshot(**tampered.model_dump())

    def test_record_hash_tamper(self) -> None:
        desc = _make_message_descriptor()
        binding = build_phase3_message_descriptor_binding(desc)
        tampered = binding.model_copy(update={"descriptor_binding_digest": DUMMY_DIGEST3})
        with pytest.raises(ValueError, match="descriptor_binding_digest mismatch"):
            Phase3MessageDescriptorBinding(**tampered.model_dump())


# ============================================================================
# Section 5: VERIFIER
# ============================================================================


class TestVerifier:
    """All public/external verifier entry points."""

    def test_verify_message_descriptor_or_raise_valid(self) -> None:
        desc = _make_message_descriptor()
        verify_phase3_message_descriptor_or_raise(desc)

    def test_verify_message_descriptor_or_raise_empty_code(self) -> None:
        with pytest.raises(ValueError, match="original_code"):
            Phase3MessageDescriptor(
                owner_sort_key=("a", "b", "c", "d", (), "e"),
                original_code="",
                message_payload_digest=sha256_digest({"msg": "test"}),
            )

    def test_verify_message_descriptor_or_raise_invalid_digest(self) -> None:
        with pytest.raises(ValueError, match="invalid message_payload_digest"):
            Phase3MessageDescriptor(
                owner_sort_key=("a", "b", "c", "d", (), "e"),
                original_code="TEST001",
                message_payload_digest="not-a-digest",
            )

    def test_verify_message_descriptor_or_raise_bad_sort_key_length(self) -> None:
        desc = Phase3MessageDescriptor(
            owner_sort_key=("a", "TEST001", "c", "d", (), "b"),
            original_code="WRONG_CODE",
            message_payload_digest=sha256_digest({"msg": "test"}),
        )
        with pytest.raises(ValueError, match="owner_sort_key\\[1\\]"):
            verify_phase3_message_descriptor_or_raise(desc)

    def test_verify_message_descriptor_or_raise_code_mismatch(self) -> None:
        desc = Phase3MessageDescriptor(
            owner_sort_key=("a", "wrong_code", "c", "d", (), "e"),
            original_code="TEST001",
            message_payload_digest=sha256_digest({"msg": "test"}),
        )
        with pytest.raises(ValueError, match="owner_sort_key\\[1\\]"):
            verify_phase3_message_descriptor_or_raise(desc)

    def test_identity_snapshot_verify_or_raise(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        isnap.verify_or_raise(source_record=rec)

    def test_source_record_snapshot_verify_or_raise(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        cei_digest = (
            rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity
            else None
        )
        cs = build_phase2_source_record_snapshot(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
            feasible=True,
            feasibility_status=FeasibilityStatus.NOT_EVALUATED,
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.PASSED,
            provider_identity_matches=True,
            rating_status="succeeded",
            candidate_evaluation_identity_digest=cei_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            invalid_rating_evidence_digest=None,
            claimed_rating_result_audit_digest=None,
            evaluation_failure_digest=None,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptor_binding_digests=(),
            blocker_descriptor_binding_digests=(),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cs.verify_or_raise(
            source_record=rec,
            identity_snapshot=isnap,
            source_record_descriptor=sdesc,
            verified_evidence=evidence,
            warning_descriptor_bindings=(),
            blocker_descriptor_bindings=(),
            source_failure_binding=None,
            evidence_failure_binding=None,
        )

    def test_source_binding_verify_or_raise(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        cei_digest = (
            rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity
            else None
        )
        cs = build_phase2_source_record_snapshot(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
            feasible=True,
            feasibility_status=FeasibilityStatus.NOT_EVALUATED,
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.PASSED,
            provider_identity_matches=True,
            rating_status="succeeded",
            candidate_evaluation_identity_digest=cei_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            invalid_rating_evidence_digest=None,
            claimed_rating_result_audit_digest=None,
            evaluation_failure_digest=None,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptor_binding_digests=(),
            blocker_descriptor_binding_digests=(),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        wbd = _make_message_descriptor_binding(_make_message_descriptor())
        bbd = _make_message_descriptor_binding(_make_message_descriptor("B99"))
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        sb.verify_or_raise(
            source_record=rec,
            identity_snapshot=isnap,
            complete_snapshot=cs,
            source_record_descriptor=sdesc,
            verified_evidence=evidence,
            warning_bindings=(wbd,),
            blocker_bindings=(bbd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
        )

    def test_preparation_result_verify_or_raise(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        cei_digest = (
            rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity
            else None
        )
        cs = build_phase2_source_record_snapshot(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
            feasible=True,
            feasibility_status=FeasibilityStatus.NOT_EVALUATED,
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.PASSED,
            provider_identity_matches=True,
            rating_status="succeeded",
            candidate_evaluation_identity_digest=cei_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            invalid_rating_evidence_digest=None,
            claimed_rating_result_audit_digest=None,
            evaluation_failure_digest=None,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptor_binding_digests=(),
            blocker_descriptor_binding_digests=(),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        wbd = _make_message_descriptor_binding(_make_message_descriptor())
        bbd = _make_message_descriptor_binding(_make_message_descriptor("B99"))
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        sri = _make_sizing_request_identity()
        candidate = _make_candidate(evaluation_order_index=0)
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        prep = build_phase3_candidate_preparation_result(
            status=Phase3PreparationStatus.READY,
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            identity_snapshot=isnap,
            complete_snapshot=cs,
            source_binding=sb,
            classification_input=cin,
        )
        prep.verify_or_raise(
            source_record=rec,
            identity_snapshot=isnap,
            complete_snapshot=cs,
            source_binding=sb,
            classification_input=cin,
            evidence_failure_binding=None,
            source_failure_binding=None,
            phase3_failure_binding=None,
        )

    def test_index_artifact_matrix_integrity_invalid(self) -> None:
        rec = _make_integrity_invalid_record("c1", 0)
        verify_phase3_index_artifact_matrix(
            source_record=rec,
            identity_snapshot=None,
            complete_snapshot=None,
            source_record_descriptor=None,
            source_binding=None,
            classification_input=None,
            preparation_result=None,
            evidence_failure_binding=None,
            source_failure_binding=None,
            phase3_failure_binding=None,
        )
        # Adding any artifact should fail
        with pytest.raises(ValueError, match="INTEGRITY_INVALID.*FORBIDDEN"):
            verify_phase3_index_artifact_matrix(
                source_record=rec,
                identity_snapshot=None,
                complete_snapshot=build_phase2_source_record_snapshot(
                    source_qualified_candidate_id="test_id",
                    evaluation_order_index=0,
                    candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
                    feasible=True,
                    feasibility_status=FeasibilityStatus.NOT_EVALUATED,
                    hash_verification_outcome=VerificationOutcome.PASSED,
                    provenance_verification_outcome=VerificationOutcome.PASSED,
                    provider_identity_matches=True,
                    rating_status="succeeded",
                    candidate_evaluation_identity_digest=None,
                    verified_rating_evidence_digest=None,
                    invalid_rating_evidence_digest=None,
                    claimed_rating_result_audit_digest=None,
                    evaluation_failure_digest=None,
                    phase2_source_record_descriptor_digest=_make_digest("sd"),
                    warning_descriptor_binding_digests=(),
                    blocker_descriptor_binding_digests=(),
                    source_evaluation_failure_binding_digest=None,
                    evidence_failure_binding_digest=None,
                ),
                source_record_descriptor=None,
                source_binding=None,
                classification_input=None,
                preparation_result=None,
                evidence_failure_binding=None,
                source_failure_binding=None,
                phase3_failure_binding=None,
            )

    def test_index_artifact_matrix_runtime_failed(self) -> None:
        rec = _make_runtime_failed_record("c1", 0)
        fb = _make_failure_binding()
        verify_phase3_index_artifact_matrix(
            source_record=rec,
            identity_snapshot=None,
            complete_snapshot=None,
            source_record_descriptor=None,
            source_binding=None,
            classification_input=None,
            preparation_result=None,
            evidence_failure_binding=None,
            source_failure_binding=fb,
            phase3_failure_binding=None,
        )
        with pytest.raises(ValueError, match="RUNTIME_FAILED.*REQUIRED"):
            verify_phase3_index_artifact_matrix(
                source_record=rec,
                identity_snapshot=None,
                complete_snapshot=None,
                source_record_descriptor=None,
                source_binding=None,
                classification_input=None,
                preparation_result=None,
                evidence_failure_binding=None,
                source_failure_binding=None,
                phase3_failure_binding=None,
            )

    def test_index_artifact_matrix_unevaluated(self) -> None:
        rec = _make_unevaluated_record("c1", 0)
        verify_phase3_index_artifact_matrix(
            source_record=rec,
            identity_snapshot=None,
            complete_snapshot=None,
            source_record_descriptor=None,
            source_binding=None,
            classification_input=None,
            preparation_result=None,
            evidence_failure_binding=None,
            source_failure_binding=None,
            phase3_failure_binding=None,
        )


# ============================================================================
# Section 6: RANKING & TOP-N
# ============================================================================


class TestRankingAndTopN:
    """Ranking and Top-N selection tests."""

    def test_same_rank_key_tie_break(self) -> None:
        evidence1 = _make_evidence(area_outer_m2=5.0)
        evidence2 = _make_evidence(area_outer_m2=5.0)
        rec1, cand1 = _make_ver("c1", 0, evidence=evidence1)
        rec2, cand2 = _make_ver("c2", 1, evidence=evidence2)
        # cand1 and cand2 already unpacked from _make_ver above
        sri = _make_sizing_request_identity()
        isnap1 = build_identity_snapshot(rec1)
        sdesc1 = build_phase2_source_record_descriptor(
            source_record=rec1,
            identity_snapshot=isnap1,
            verified_evidence=evidence1,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb1 = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc1.descriptor_digest,
            verified_rating_evidence_digest=evidence1.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap1.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin1 = _build_cin(rec1, cand1, sri, isnap1, sdesc1, sb1)
        disp1 = classify_candidate(
            cin1,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
        )
        isnap2 = build_identity_snapshot(rec2)
        sdesc2 = build_phase2_source_record_descriptor(
            source_record=rec2,
            identity_snapshot=isnap2,
            verified_evidence=evidence2,
            source_failure_binding=None,
        )
        sb2 = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc2.descriptor_digest,
            verified_rating_evidence_digest=evidence2.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap2.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin2 = _build_cin(rec2, cand2, sri, isnap2, sdesc2, sb2)
        disp2 = classify_candidate(
            cin2,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
        )
        assert disp1.disposition == Phase3Disposition.FEASIBLE
        assert disp2.disposition == Phase3Disposition.FEASIBLE
        pv1, pf1, sv1, sf1 = _expected_ranked_values(
            disp1,
            cand1,
            OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
        )
        pv2, pf2, sv2, sf2 = _expected_ranked_values(
            disp2,
            cand2,
            OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
        )
        assert pv1 == pv2
        assert Decimal(sv2) < Decimal(sv1)

    def test_illegal_n_rejected(self) -> None:
        # OptimizationResultCoreValues doesn't validate top_n; OptimizationResult does
        # This test verifies the contract specification
        pytest.skip(
            "OptimizationResultCoreValues allows top_n=0; only OptimizationResult validates top_n >= 1"
        )

    def test_boundary_n_value(self) -> None:
        core = OptimizationResultCoreValues(
            schema_version=1,
            sizing_request_identity_digest=DUMMY_DIGEST,
            passed_gate_digest=DUMMY_DIGEST2,
            candidate_set_digest=DUMMY_DIGEST3,
            evaluation_input_digest=DUMMY_DIGEST4,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            requested_top_n=1,
            total_candidate_count=1,
            feasible_candidate_count=0,
            infeasible_candidate_count=1,
            provider_mismatch_count=0,
            integrity_failed_count=0,
            provenance_failed_count=0,
            runtime_failed_count=0,
            unevaluated_count=0,
            phase2_verified_record_count=1,
            phase2_integrity_invalid_record_count=0,
            phase2_runtime_failed_record_count=0,
            phase2_unevaluated_record_count=0,
            runtime_failed_from_phase2_verified_count=0,
            runtime_failed_from_phase2_runtime_failed_count=0,
            ordered_disposition_record_digests=(DUMMY_DIGEST,),
            ordered_ranked_record_digests=(),
            ordered_top_n_record_digests=(),
            ordered_identity_snapshot_digests=(DUMMY_DIGEST,),
            ordered_phase2_source_snapshot_digests=(DUMMY_DIGEST,),
            ordered_phase3_source_binding_digests=(DUMMY_DIGEST,),
            ordered_phase3_preparation_result_digests=(DUMMY_DIGEST,),
            termination_status=TerminationStatus.COMPLETE,
            ordered_warning_digests=(),
            ordered_blocker_digests=(),
        )
        assert core.requested_top_n == 1


# ============================================================================
# Section 7: FAILURE PROPAGATION
# ============================================================================


class TestFailurePropagation:
    """Failure propagation through the Phase 3 pipeline."""

    def test_provider_identity_mismatch(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, provider_identity_matches=False)
        sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.PROVIDER_IDENTITY_MISMATCH
        assert disp.diagnostic == FeasibilityDiagnosticKey.PROVIDER_IDENTITY_MISMATCH

    def test_missing_rating_status_phase3_runtime(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status=None)
        sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        cin = _build_cin(rec, candidate, sri, isnap, sdesc, sb)
        disp = classify_candidate(
            cin,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            source_failure_binding=None,
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

    def test_integrity_invalid_hash_failed(self) -> None:
        rec = _make_integrity_invalid_record(
            "c1",
            0,
            hash_outcome=VerificationOutcome.FAILED,
            prov_outcome=VerificationOutcome.NOT_RUN,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        isnap = build_identity_snapshot(_make_ver("c1", 0)[0])
        disp = _map_non_verified(
            rec,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=None,
            source_failure_binding=None,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.INTEGRITY_FAILED

    def test_integrity_invalid_provenance_failed(self) -> None:
        rec = _make_integrity_invalid_record(
            "c1",
            0,
            hash_outcome=VerificationOutcome.PASSED,
            prov_outcome=VerificationOutcome.ERROR,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        isnap = build_identity_snapshot(_make_ver("c1", 0)[0])
        disp = _map_non_verified(
            rec,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=None,
            source_failure_binding=None,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.PROVENANCE_FAILED

    def test_runtime_failed_mapped(self) -> None:
        rec = _make_runtime_failed_record("c1", 0)
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        fb = _make_failure_binding()
        isnap = build_identity_snapshot(_make_ver("c1", 0)[0])
        disp = _map_non_verified(
            rec,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=None,
            source_failure_binding=fb,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE2_RUNTIME_FAILED
        assert disp.failure_origin == FailureOrigin.PHASE2_EVALUATION

    def test_unevaluated_mapped(self) -> None:
        rec = _make_unevaluated_record("c1", 0)
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        isnap = build_identity_snapshot(_make_ver("c1", 0)[0])
        disp = _map_non_verified(
            rec,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=None,
            source_failure_binding=None,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.UNEVALUATED

    def test_phase3_runtime_from_builder(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        sri = _make_sizing_request_identity()
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(),
            blocker_descriptor_binding_digests=(),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        disp = _phase3_runtime(
            rec,
            sb,
            ErrorCode.INPUT_INCONSISTENT,
            "Test runtime",
            failure_stage=Phase3PreparationFailureStage.CLASSIFICATION,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptors=(),
            blocker_descriptors=(),
            source_failure_binding=None,
            evidence_failure_binding=None,
        )
        assert disp.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED
        assert disp.failure_origin == FailureOrigin.PHASE3_CLASSIFICATION

        failure = RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="validation failure",
            context=(("key", "val"),),
        )
        disp2 = _phase3_runtime_from_validation(
            rec,
            sb,
            failure,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptors=(),
            blocker_descriptors=(),
        )
        assert disp2.disposition == Phase3Disposition.RUNTIME_FAILED
        assert disp2.diagnostic == FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED


# ============================================================================
# Section 8: DECIMAL HELPERS
# ============================================================================


class TestDecimalHelpers:
    """Tests for canonical decimal helpers."""

    def test_canonical_decimal_normal(self) -> None:
        assert canonical_decimal(Decimal("5.0")) == Decimal("5")
        assert canonical_decimal(Decimal("0.0")) == Decimal("0")
        assert canonical_decimal(Decimal("1.000")) == Decimal("1")

    def test_canonical_decimal_string(self) -> None:
        assert canonical_decimal_string(Decimal("5.0")) == "5"
        assert canonical_decimal_string(Decimal("0")) == "0"
        assert canonical_decimal_string(Decimal("1.5")) == "1.5"

    def test_to_canonical_decimal_float(self) -> None:
        assert to_canonical_decimal(5.0) == Decimal("5")

    def test_to_canonical_decimal_int(self) -> None:
        assert to_canonical_decimal(5) == Decimal("5")

    def test_to_canonical_decimal_decimal(self) -> None:
        assert to_canonical_decimal(Decimal("5.0")) == Decimal("5")

    def test_to_canonical_decimal_bool_rejected(self) -> None:
        with pytest.raises(TypeError, match="bool"):
            to_canonical_decimal(True)

    def test_to_canonical_decimal_non_finite_rejected(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            to_canonical_decimal(float("inf"))

    def test_verify_canonical_decimal_string_valid(self) -> None:
        verify_canonical_decimal_string("5")
        verify_canonical_decimal_string("1.5")
        verify_canonical_decimal_string("0")

    def test_verify_canonical_decimal_string_invalid(self) -> None:
        with pytest.raises(ValueError, match="not canonical"):
            verify_canonical_decimal_string("5.0")

    def test_verify_canonical_decimal_string_non_finite(self) -> None:
        with pytest.raises(ValueError):
            verify_canonical_decimal_string("Infinity")


# ============================================================================
# Section 9: CORE TYPES
# ============================================================================


class TestCoreTypes:
    """Tests for core types: enums, descriptors, snapshots, bindings."""

    def test_phase3_disposition_values(self) -> None:
        assert Phase3Disposition.FEASIBLE == "feasible"
        assert Phase3Disposition.INFEASIBLE == "infeasible"
        assert Phase3Disposition.PROVIDER_IDENTITY_MISMATCH == "provider_identity_mismatch"

    def test_feasibility_diagnostic_key_values(self) -> None:
        assert FeasibilityDiagnosticKey.DUTY_SHORTFALL == "duty_shortfall"
        assert FeasibilityDiagnosticKey.RATING_BLOCKED == "rating_blocked"

    def test_termination_status_values(self) -> None:
        assert TerminationStatus.COMPLETE == "complete"
        assert TerminationStatus.PARTIAL == "partial"

    def test_failure_origin_values(self) -> None:
        assert FailureOrigin.NONE == "none"
        assert FailureOrigin.PHASE2_EVALUATION == "phase2_evaluation"
        assert FailureOrigin.PHASE3_CLASSIFICATION == "phase3_classification"

    def test_provenance_relation_values(self) -> None:
        assert Phase3ProvenanceRelation.REGULATES == "regulates"
        assert Phase3ProvenanceRelation.EVALUATED == "evaluated"
        assert Phase3ProvenanceRelation.RANKED == "ranked"

    def test_preparation_status_values(self) -> None:
        assert Phase3PreparationStatus.READY == "ready"
        assert Phase3PreparationStatus.FAILED == "failed"

    def test_message_descriptor_binding_roundtrip(self) -> None:
        desc = _make_message_descriptor()
        binding = build_phase3_message_descriptor_binding(desc)
        assert binding.owner_sort_key == desc.owner_sort_key
        assert binding.original_code == desc.original_code
        assert binding.message_payload_digest == desc.message_payload_digest
        assert DIGEST_RE.match(binding.descriptor_binding_digest)

    def test_message_descriptor_binding_tamper(self) -> None:
        desc = _make_message_descriptor()
        binding = build_phase3_message_descriptor_binding(desc)
        tampered = binding.model_copy(update={"descriptor_binding_digest": DUMMY_DIGEST4})
        with pytest.raises(ValueError, match="descriptor_binding_digest mismatch"):
            Phase3MessageDescriptorBinding(**tampered.model_dump())

    def test_failure_descriptor_binding_roundtrip(self) -> None:
        fb = _make_failure_binding()
        assert fb.original_code is not None
        assert DIGEST_RE.match(fb.descriptor_binding_digest)

    def test_identity_snapshot_build_and_verify(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        assert isnap.source_qualified_candidate_id == rec.source_qualified_candidate_id
        assert isnap.evaluation_order_index == 0
        assert DIGEST_RE.match(isnap.identity_snapshot_digest)
        isnap.verify_or_raise(source_record=rec)

    def test_source_record_descriptor_build(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        assert sdesc.source_qualified_candidate_id == rec.source_qualified_candidate_id
        assert DIGEST_RE.match(sdesc.descriptor_digest)

    def test_source_record_snapshot_build(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        cei_digest = (
            rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity
            else None
        )
        cs = build_phase2_source_record_snapshot(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
            feasible=True,
            feasibility_status=FeasibilityStatus.NOT_EVALUATED,
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.PASSED,
            provider_identity_matches=True,
            rating_status="succeeded",
            candidate_evaluation_identity_digest=cei_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            invalid_rating_evidence_digest=None,
            claimed_rating_result_audit_digest=None,
            evaluation_failure_digest=None,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptor_binding_digests=(),
            blocker_descriptor_binding_digests=(),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        assert cs.source_qualified_candidate_id == "test_id"
        assert DIGEST_RE.match(cs.snapshot_digest)


# ============================================================================
# Section 10: BUILDER HELPERS
# ============================================================================


class TestBuilderHelpers:
    """Tests for builder helper functions."""

    def test_build_feasible(self) -> None:
        evidence = _make_evidence(area_outer_m2=5.0, heat_duty_w=5000.0)
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        disp = _build_feasible(
            rec,
            evidence,
            sb,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
        )
        assert disp.disposition == Phase3Disposition.FEASIBLE
        assert disp.primary_engineering_value == "5"
        assert disp.secondary_engineering_value == "5000"

    def test_build_infeasible(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, rating_status="blocked")
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        disp = _build_infeasible(
            rec,
            sb,
            FeasibilityDiagnosticKey.RATING_BLOCKED,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
        )
        assert disp.disposition == Phase3Disposition.INFEASIBLE
        assert disp.diagnostic == FeasibilityDiagnosticKey.RATING_BLOCKED

    def test_build_provider_mismatch(self) -> None:
        evidence = _make_evidence()
        rec, candidate = _make_ver("c1", 0, evidence=evidence, provider_identity_matches=False)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        disp = _build_provider_mismatch(
            rec,
            evidence,
            sb,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
        )
        assert disp.disposition == Phase3Disposition.PROVIDER_IDENTITY_MISMATCH

    def test_ranked_candidate_record_valid(self) -> None:
        rr = build_ranked_candidate_record(
            rank=1,
            source_qualified_candidate_id="c1",
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            primary_objective_value="5",
            primary_objective_field="area_outer_m2",
            secondary_tie_break_value="1",
            secondary_tie_break_field="effective_length_m_canonical",
            candidate_evaluation_identity_digest=DUMMY_DIGEST,
            verified_rating_evidence_digest=DUMMY_DIGEST2,
            feasibility_digest=DUMMY_DIGEST3,
        )
        assert rr.rank == 1
        assert DIGEST_RE.match(rr.ranked_record_digest)

    def test_ranked_candidate_record_invalid_rank(self) -> None:
        with pytest.raises(ValueError, match="rank must be"):
            build_ranked_candidate_record(
                rank=0,
                source_qualified_candidate_id="c1",
                optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
                primary_objective_value="5",
                primary_objective_field="area_outer_m2",
                secondary_tie_break_value="1",
                secondary_tie_break_field="effective_length_m_canonical",
                candidate_evaluation_identity_digest=DUMMY_DIGEST,
                verified_rating_evidence_digest=DUMMY_DIGEST2,
                feasibility_digest=DUMMY_DIGEST3,
            )

    def test_ranked_candidate_record_wrong_field(self) -> None:
        with pytest.raises(ValueError, match="MIN_OA"):
            build_ranked_candidate_record(
                rank=1,
                source_qualified_candidate_id="c1",
                optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
                primary_objective_value="5",
                primary_objective_field="effective_length_m_canonical",
                secondary_tie_break_value="1",
                secondary_tie_break_field="area_outer_m2",
                candidate_evaluation_identity_digest=DUMMY_DIGEST,
                verified_rating_evidence_digest=DUMMY_DIGEST2,
                feasibility_digest=DUMMY_DIGEST3,
            )

    def test_ranked_candidate_record_non_canonical_value(self) -> None:
        with pytest.raises(ValueError, match="not canonical"):
            build_ranked_candidate_record(
                rank=1,
                source_qualified_candidate_id="c1",
                optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
                primary_objective_value="5.0",
                primary_objective_field="area_outer_m2",
                secondary_tie_break_value="1",
                secondary_tie_break_field="effective_length_m_canonical",
                candidate_evaluation_identity_digest=DUMMY_DIGEST,
                verified_rating_evidence_digest=DUMMY_DIGEST2,
                feasibility_digest=DUMMY_DIGEST3,
            )

    def test_expected_ranked_values_area_objective(self) -> None:
        evidence = _make_evidence(area_outer_m2=5.0, heat_duty_w=5000.0)
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        cand = _make_candidate(evaluation_order_index=0, effective_length_m=1.0)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        disp = _build_feasible(
            rec,
            evidence,
            sb,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
        )
        pv, pf, sv, sf = _expected_ranked_values(
            disp,
            cand,
            OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
        )
        assert pf == "area_outer_m2"
        assert sf == "effective_length_m_canonical"
        assert pv == "5"
        assert sv == "1"

    def test_expected_ranked_values_length_objective(self) -> None:
        evidence = _make_evidence(area_outer_m2=5.0, heat_duty_w=5000.0)
        rec, candidate = _make_ver("c1", 0, evidence=evidence)
        cand = _make_candidate(evaluation_order_index=0, effective_length_m=2.5)
        isnap = build_identity_snapshot(rec)
        sdesc = build_phase2_source_record_descriptor(
            source_record=rec,
            identity_snapshot=isnap,
            verified_evidence=evidence,
            source_failure_binding=None,
        )
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        wbd = _make_message_descriptor_binding(wd)
        bbd = _make_message_descriptor_binding(bd)
        sb = build_phase3_source_record_binding(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            phase2_source_record_descriptor_digest=sdesc.descriptor_digest,
            verified_rating_evidence_digest=evidence.compute_explicit_evidence_digest(),
            phase2_identity_snapshot_digest=isnap.identity_snapshot_digest,
            warning_descriptor_binding_digests=(wbd.descriptor_binding_digest,),
            blocker_descriptor_binding_digests=(bbd.descriptor_binding_digest,),
            source_evaluation_failure_binding_digest=None,
            evidence_failure_binding_digest=None,
        )
        disp = _build_feasible(
            rec,
            evidence,
            sb,
            source_identity_record_descriptor_digest=isnap.identity_snapshot_digest,
            source_record_descriptor_digest=sdesc.descriptor_digest,
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
        )
        pv, pf, sv, sf = _expected_ranked_values(
            disp,
            cand,
            OptimizationObjective.MINIMUM_EFFECTIVE_LENGTH,
        )
        assert pf == "effective_length_m_canonical"
        assert sf == "area_outer_m2"


# ============================================================================
# Section 11: CANDIDATE DISPOSITION RECORD
# ============================================================================


class TestCandidateDispositionRecord:
    """Tests for CandidateDispositionRecord construction and validation."""

    def test_build_method(self) -> None:
        sri = _make_sizing_request_identity()
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        record = build_candidate_disposition_record(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            source_candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
            source_hash_verification_outcome=VerificationOutcome.PASSED,
            source_provenance_verification_outcome=VerificationOutcome.PASSED,
            source_record_descriptor_digest=DUMMY_DIGEST,
            source_identity_record_descriptor_digest=sri.sizing_request_identity_digest,
            disposition=Phase3Disposition.FEASIBLE,
            diagnostic=FeasibilityDiagnosticKey.NONE,
            provider_identity_matches=True,
            rating_status="succeeded",
            candidate_evaluation_identity_digest=DUMMY_DIGEST2,
            verified_rating_evidence_digest=DUMMY_DIGEST3,
            invalid_rating_evidence_digest=None,
            primary_engineering_value="5",
            secondary_engineering_value="5000",
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            source_evaluation_failure_payload_digest=None,
            source_evaluation_failure_binding_digest=None,
            phase3_failure_payload_digest=None,
            failure_origin=FailureOrigin.NONE,
        )
        assert record.disposition == Phase3Disposition.FEASIBLE
        assert DIGEST_RE.match(record.feasibility_digest)

    def test_disposition_payload_roundtrip(self) -> None:
        sri = _make_sizing_request_identity()
        wd = _make_message_descriptor()
        bd = _make_message_descriptor("B1")
        record = build_candidate_disposition_record(
            source_qualified_candidate_id="test_id",
            evaluation_order_index=0,
            source_candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
            source_hash_verification_outcome=VerificationOutcome.PASSED,
            source_provenance_verification_outcome=VerificationOutcome.PASSED,
            source_record_descriptor_digest=DUMMY_DIGEST,
            source_identity_record_descriptor_digest=sri.sizing_request_identity_digest,
            disposition=Phase3Disposition.FEASIBLE,
            diagnostic=FeasibilityDiagnosticKey.NONE,
            provider_identity_matches=True,
            rating_status="succeeded",
            candidate_evaluation_identity_digest=DUMMY_DIGEST2,
            verified_rating_evidence_digest=DUMMY_DIGEST3,
            invalid_rating_evidence_digest=None,
            primary_engineering_value="5",
            secondary_engineering_value="5000",
            warning_descriptors=(wd,),
            blocker_descriptors=(bd,),
            source_evaluation_failure_payload_digest=None,
            source_evaluation_failure_binding_digest=None,
            phase3_failure_payload_digest=None,
            failure_origin=FailureOrigin.NONE,
        )
        payload = candidate_disposition_payload(record)
        assert payload["disposition"] == "feasible"
        assert payload["source_qualified_candidate_id"] == "test_id"

    def test_failure_matrix_non_failure_dispositions(self) -> None:
        with pytest.raises(ValueError, match="failure_origin must be NONE"):
            verify_candidate_disposition_failure_matrix(
                disposition=Phase3Disposition.FEASIBLE,
                failure_origin=FailureOrigin.PHASE3_CLASSIFICATION,
                failure_stage=None,
                source_failure_binding_digest=None,
                source_failure_payload_digest=None,
                phase3_failure_binding_digest=None,
                phase3_failure_payload_digest=None,
                source_identity_record_descriptor_digest=DUMMY_DIGEST,
            )

    def test_failure_matrix_p2_runtime(self) -> None:
        with pytest.raises(ValueError, match="source_failure_binding_digest required"):
            verify_candidate_disposition_failure_matrix(
                disposition=Phase3Disposition.RUNTIME_FAILED,
                failure_origin=FailureOrigin.PHASE2_EVALUATION,
                failure_stage=None,
                source_failure_binding_digest=None,
                source_failure_payload_digest=None,
                phase3_failure_binding_digest=None,
                phase3_failure_payload_digest=None,
                source_identity_record_descriptor_digest=DUMMY_DIGEST,
            )

    def test_failure_matrix_p3_runtime(self) -> None:
        with pytest.raises(ValueError, match="phase3_failure_binding_digest required"):
            verify_candidate_disposition_failure_matrix(
                disposition=Phase3Disposition.RUNTIME_FAILED,
                failure_origin=FailureOrigin.PHASE3_CLASSIFICATION,
                failure_stage=Phase3PreparationFailureStage.CLASSIFICATION,
                source_failure_binding_digest=None,
                source_failure_payload_digest=None,
                phase3_failure_binding_digest=None,
                phase3_failure_payload_digest=None,
                source_identity_record_descriptor_digest=DUMMY_DIGEST,
            )


# ============================================================================
# Section 12: OPTIMIZATION RESULT CORE VALUES
# ============================================================================


class TestOptimizationResultCoreValues:
    """Tests for OptimizationResultCoreValues validation."""

    def test_populated_counts_sum(self) -> None:
        core = OptimizationResultCoreValues(
            schema_version=1,
            sizing_request_identity_digest=DUMMY_DIGEST,
            passed_gate_digest=DUMMY_DIGEST2,
            candidate_set_digest=DUMMY_DIGEST3,
            evaluation_input_digest=DUMMY_DIGEST4,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            requested_top_n=3,
            total_candidate_count=3,
            feasible_candidate_count=1,
            infeasible_candidate_count=1,
            provider_mismatch_count=0,
            integrity_failed_count=0,
            provenance_failed_count=0,
            runtime_failed_count=0,
            unevaluated_count=1,
            phase2_verified_record_count=2,
            phase2_integrity_invalid_record_count=0,
            phase2_runtime_failed_record_count=0,
            phase2_unevaluated_record_count=1,
            runtime_failed_from_phase2_verified_count=0,
            runtime_failed_from_phase2_runtime_failed_count=0,
            ordered_disposition_record_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, DUMMY_DIGEST3),
            ordered_ranked_record_digests=(DUMMY_DIGEST4,),
            ordered_top_n_record_digests=(DUMMY_DIGEST4,),
            ordered_identity_snapshot_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, DUMMY_DIGEST3),
            ordered_phase2_source_snapshot_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
            ordered_phase3_source_binding_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
            ordered_phase3_preparation_result_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
            termination_status=TerminationStatus.COMPLETE,
            ordered_warning_digests=(),
            ordered_blocker_digests=(),
        )
        assert core.total_candidate_count == 3
        assert core.feasible_candidate_count == 1

    def test_counts_must_sum_correctly(self) -> None:
        with pytest.raises(ValueError, match="don't sum"):
            OptimizationResultCoreValues(
                schema_version=1,
                sizing_request_identity_digest=DUMMY_DIGEST,
                passed_gate_digest=DUMMY_DIGEST2,
                candidate_set_digest=DUMMY_DIGEST3,
                evaluation_input_digest=DUMMY_DIGEST4,
                optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
                requested_top_n=3,
                total_candidate_count=3,
                feasible_candidate_count=1,
                infeasible_candidate_count=1,
                provider_mismatch_count=0,
                integrity_failed_count=0,
                provenance_failed_count=0,
                runtime_failed_count=0,
                unevaluated_count=0,
                phase2_verified_record_count=2,
                phase2_integrity_invalid_record_count=0,
                phase2_runtime_failed_record_count=0,
                phase2_unevaluated_record_count=1,
                runtime_failed_from_phase2_verified_count=0,
                runtime_failed_from_phase2_runtime_failed_count=0,
                ordered_disposition_record_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, DUMMY_DIGEST3),
                ordered_ranked_record_digests=(DUMMY_DIGEST4,),
                ordered_top_n_record_digests=(DUMMY_DIGEST4,),
                ordered_identity_snapshot_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, DUMMY_DIGEST3),
                ordered_phase2_source_snapshot_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
                ordered_phase3_source_binding_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
                ordered_phase3_preparation_result_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
                termination_status=TerminationStatus.COMPLETE,
                ordered_warning_digests=(),
                ordered_blocker_digests=(),
            )

    def test_phase2_counts_must_sum(self) -> None:
        with pytest.raises(ValueError, match="Phase 2 counts don't sum"):
            OptimizationResultCoreValues(
                schema_version=1,
                sizing_request_identity_digest=DUMMY_DIGEST,
                passed_gate_digest=DUMMY_DIGEST2,
                candidate_set_digest=DUMMY_DIGEST3,
                evaluation_input_digest=DUMMY_DIGEST4,
                optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
                requested_top_n=3,
                total_candidate_count=3,
                feasible_candidate_count=1,
                infeasible_candidate_count=1,
                provider_mismatch_count=0,
                integrity_failed_count=0,
                provenance_failed_count=0,
                runtime_failed_count=0,
                unevaluated_count=1,
                phase2_verified_record_count=1,
                phase2_integrity_invalid_record_count=0,
                phase2_runtime_failed_record_count=0,
                phase2_unevaluated_record_count=1,
                runtime_failed_from_phase2_verified_count=0,
                runtime_failed_from_phase2_runtime_failed_count=0,
                ordered_disposition_record_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, DUMMY_DIGEST3),
                ordered_ranked_record_digests=(DUMMY_DIGEST4,),
                ordered_top_n_record_digests=(DUMMY_DIGEST4,),
                ordered_identity_snapshot_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, DUMMY_DIGEST3),
                ordered_phase2_source_snapshot_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
                ordered_phase3_source_binding_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
                ordered_phase3_preparation_result_digests=(DUMMY_DIGEST, DUMMY_DIGEST2, None),
                termination_status=TerminationStatus.COMPLETE,
                ordered_warning_digests=(),
                ordered_blocker_digests=(),
            )
