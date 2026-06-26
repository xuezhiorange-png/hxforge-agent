"""
TASK-009 Phase 2 tests — TASK-008 adapter mapping, verification state
machine, evidence records, provider identity checking.

Uses mock RatingResult objects to verify the verification pipeline
without calling the real TASK-008 kernel.
"""

from __future__ import annotations

from typing import Any

from hexagent.exchangers.double_pipe.result import RatingResult, RatingStatus
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.optimization.adapter import build_candidate_geometry
from hexagent.optimization.context import ExpectedProviderIdentity
from hexagent.optimization.evaluation import (
    CandidateEvaluationState,
    VerificationOutcome,
    VerifiedRatingEvidenceSnapshot,
    verify_and_evaluate_candidate,
)
from hexagent.optimization.identities import (
    ManufacturableCandidate,
    PhysicalCandidateIdentity,
    SourceQualifiedCandidateIdentity,
)
from hexagent.optimization.models import (
    CatalogSnapshotRef,
    CompleteDoublePipeAssemblyOption,
    LengthSource,
)

# ============================================================================
# Fixtures
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


def _make_candidate(eval_idx: int = 0, length: str = "1.0") -> ManufacturableCandidate:
    _make_opt("o1", lengths=(1.0,))
    phy = PhysicalCandidateIdentity(
        inner_tube_inner_diameter_m=0.05,
        inner_tube_outer_diameter_m=0.06,
        outer_pipe_inner_diameter_m=0.10,
        effective_length_m_canonical=length,
        wall_thermal_conductivity_w_m_k=50.0,
        inner_surface_roughness_m=1e-5,
        annulus_surface_roughness_m=1e-5,
        inner_fouling_resistance_m2k_w=0.0001,
        outer_fouling_resistance_m2k_w=0.0002,
    )
    sq = SourceQualifiedCandidateIdentity(
        physical_identity_digest=phy.physical_identity_digest,
        catalog_id="c1",
        catalog_version="v1",
        catalog_content_hash="sha256:" + "a" * 64,
        assembly_option_id="o1",
        manufacturing_option_identity="std",
    )
    return ManufacturableCandidate(
        physical_identity=phy,
        physical_identity_digest=phy.physical_identity_digest,
        source_qualified_identity=sq,
        source_qualified_candidate_id=sq.source_qualified_candidate_id,
        catalog_snapshot_ref=CatalogSnapshotRef(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash="sha256:" + "a" * 64,
            source_identity="test",
            schema_version="1.0",
        ),
        assembly_option_id="o1",
        manufacturing_option_identity="std",
        manufacturing_metadata=(),
        effective_length_m_canonical=length,
        evaluation_order_index=eval_idx,
    )


# ============================================================================
# Adapter geometry building
# ============================================================================


class TestAdapterGeometry:
    """``build_candidate_geometry`` maps fields exactly."""

    def test_geometry_fields_match(self) -> None:
        cand = _make_candidate(length="2.0")
        geom = build_candidate_geometry(cand)
        assert geom.inner_tube_inner_diameter_m == 0.05
        assert geom.inner_tube_outer_diameter_m == 0.06
        assert geom.outer_pipe_inner_diameter_m == 0.10
        assert geom.effective_length_m == 2.0
        assert geom.wall_thermal_conductivity_w_m_k == 50.0
        assert geom.inner_surface_roughness_m == 1e-5
        assert geom.annulus_surface_roughness_m == 1e-5
        assert geom.inner_fouling_resistance_m2k_w == 0.0001
        assert geom.outer_fouling_resistance_m2k_w == 0.0002


# ============================================================================
# Verification state machine tests
# ============================================================================


class TestVerificationHashFalse:
    """verify_hash() returns False → INTEGRITY_INVALID."""

    def test_state_is_integrity_invalid(self) -> None:
        result = _make_rating_result(result_hash="sha256:" + "0" * 64)
        record = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
        )
        assert record.candidate_evaluation_state == CandidateEvaluationState.INTEGRITY_INVALID.value
        assert record.hash_verification_outcome == VerificationOutcome.FAILED.value
        assert record.provenance_verification_outcome == VerificationOutcome.NOT_RUN.value
        assert not record.feasible

    def test_invalid_evidence_present(self) -> None:
        result = _make_rating_result(result_hash="sha256:" + "0" * 64)
        record = verify_and_evaluate_candidate(0, "sq_test", result)
        assert record.invalid_rating_evidence is not None
        assert record.verified_rating_evidence is None
        assert (
            record.invalid_rating_evidence.hash_verification_outcome
            == VerificationOutcome.FAILED.value
        )

    def test_no_thermal_metrics(self) -> None:
        result = _make_rating_result(result_hash="sha256:" + "0" * 64)
        record = verify_and_evaluate_candidate(0, "sq_test", result)
        # Must NOT contain trusted evidence with thermal metrics
        assert record.verified_rating_evidence is None
        # Even in audit, safe fields only
        audit = record.claimed_rating_result_audit
        assert "status" in audit


class TestVerificationHashException:
    """verify_hash() raises → RUNTIME_FAILED."""

    def test_state_is_runtime_failed(self) -> None:
        result = _make_broken_rating_result(hash_raises=True)
        record = verify_and_evaluate_candidate(0, "sq_test", result)
        assert record.candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED.value
        assert record.hash_verification_outcome == VerificationOutcome.ERROR.value
        assert record.provenance_verification_outcome == VerificationOutcome.NOT_RUN.value

    def test_failure_detail_present(self) -> None:
        result = _make_broken_rating_result(hash_raises=True)
        record = verify_and_evaluate_candidate(0, "sq_test", result)
        assert record.evaluation_failure is not None
        assert "verify_hash() raised" in record.evaluation_failure.message


class TestVerificationHashPassProvenanceFalse:
    """hash passes, provenance fails → INTEGRITY_INVALID."""

    def test_state_is_integrity_invalid(self) -> None:
        result = _make_rating_result(provenance_passes=False)
        record = verify_and_evaluate_candidate(0, "sq_test", result)
        assert record.candidate_evaluation_state == CandidateEvaluationState.INTEGRITY_INVALID.value
        assert record.hash_verification_outcome == VerificationOutcome.PASSED.value
        assert record.provenance_verification_outcome == VerificationOutcome.FAILED.value

    def test_invalid_evidence(self) -> None:
        result = _make_rating_result(provenance_passes=False)
        record = verify_and_evaluate_candidate(0, "sq_test", result)
        assert record.invalid_rating_evidence is not None
        assert (
            record.invalid_rating_evidence.provenance_verification_outcome
            == VerificationOutcome.FAILED.value
        )

    def test_no_trusted_evidence(self) -> None:
        result = _make_rating_result(provenance_passes=False)
        record = verify_and_evaluate_candidate(0, "sq_test", result)
        assert record.verified_rating_evidence is None


class TestVerificationProvenanceException:
    """provenance raises → RUNTIME_FAILED."""

    def test_state_runtime_failed(self) -> None:
        result = _make_broken_rating_result(provenance_raises=True)
        record = verify_and_evaluate_candidate(0, "sq_test", result)
        assert record.candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED.value
        assert record.hash_verification_outcome == VerificationOutcome.PASSED.value
        assert record.provenance_verification_outcome == VerificationOutcome.ERROR.value


class TestVerificationBothPass:
    """Both hash and provenance pass → VERIFIED state."""

    def test_state_verified(self) -> None:
        result = _make_rating_result(status=RatingStatus.SUCCEEDED)
        record = verify_and_evaluate_candidate(0, "sq_test", result)
        assert record.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value

    def test_trusted_evidence_present(self) -> None:
        result = _make_rating_result(status=RatingStatus.SUCCEEDED)
        record = verify_and_evaluate_candidate(0, "sq_test", result)
        assert record.verified_rating_evidence is not None
        assert record.invalid_rating_evidence is None

    def test_succeeded_status(self) -> None:
        result = _make_rating_result(status=RatingStatus.SUCCEEDED)
        record = verify_and_evaluate_candidate(0, "sq_test", result)
        ev = record.verified_rating_evidence
        assert ev is not None
        assert ev.rating_status == RatingStatus.SUCCEEDED.value
        assert ev.heat_duty_w is not None

    def test_blocked_status(self) -> None:
        result = _make_rating_result(status=RatingStatus.BLOCKED)
        record = verify_and_evaluate_candidate(0, "sq_test", result)
        assert record.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value
        ev = record.verified_rating_evidence
        assert ev is not None
        assert ev.rating_status == RatingStatus.BLOCKED.value
        assert not record.feasible

    def test_failed_status(self) -> None:
        result = _make_rating_result(status=RatingStatus.FAILED)
        record = verify_and_evaluate_candidate(0, "sq_test", result)
        assert record.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value
        ev = record.verified_rating_evidence
        assert ev is not None
        assert ev.rating_status == RatingStatus.FAILED.value
        assert not record.feasible

    def test_provider_mismatch(self) -> None:
        result = _make_rating_result(status=RatingStatus.SUCCEEDED)
        expected = ExpectedProviderIdentity(
            name="expected_provider",
            version="1.0",
            git_revision="abc",
            reference_state_policy="default",
        )
        actual = type(
            "PI",
            (),
            {
                "name": "actual_provider",
                "version": "1.0",
                "git_revision": "abc",
                "reference_state_policy": "default",
                "configuration_fingerprint": "",
                "cache_policy_version": "",
            },
        )()
        record = verify_and_evaluate_candidate(
            0,
            "sq_test",
            result,
            expected_provider=expected,
            actual_provider_identity=actual,
        )
        assert record.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value
        assert not record.provider_identity_matches

    def test_provider_consistency(self) -> None:
        """Both candidates get same provider identity."""
        result1 = _make_rating_result(status=RatingStatus.SUCCEEDED)
        result2 = _make_rating_result(status=RatingStatus.SUCCEEDED)
        expected = ExpectedProviderIdentity(
            name="p",
            version="1",
            git_revision="g",
            reference_state_policy="d",
        )
        actual = type(
            "PI",
            (),
            {
                "name": "p",
                "version": "1",
                "git_revision": "g",
                "reference_state_policy": "d",
                "configuration_fingerprint": "",
                "cache_policy_version": "",
            },
        )()
        r1 = verify_and_evaluate_candidate(0, "a", result1, expected, actual)
        r2 = verify_and_evaluate_candidate(1, "b", result2, expected, actual)
        assert r1.provider_identity_matches
        assert r2.provider_identity_matches


class TestVerificationNonRatingResult:
    """Non-RatingResult object → RUNTIME_FAILED."""

    def test_non_rating_result(self) -> None:
        record = verify_and_evaluate_candidate(0, "sq_bad", {"not_a": "result"})
        assert record.candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED.value
        assert record.evaluation_failure is not None
        assert "Expected RatingResult" in record.evaluation_failure.message

    def test_integrity_failure_claimed_fields(self) -> None:
        """Claimed provider identity must NOT be used for feasibility decisions."""
        result = _make_rating_result(result_hash="sha256:" + "0" * 64)
        record = verify_and_evaluate_candidate(0, "sq_test", result)
        assert not record.feasible
        # Provider should not be used for decisions from integrity-invalid results
        assert not record.provider_identity_matches


class TestVerificationEvidenceDigest:
    """Evidence digests are deterministic."""

    def test_evidence_digest_stable(self) -> None:
        ev1 = VerifiedRatingEvidenceSnapshot(rating_status="succeeded", heat_duty_w=100.0)
        ev2 = VerifiedRatingEvidenceSnapshot(rating_status="succeeded", heat_duty_w=100.0)
        assert ev1.evidence_digest == ev2.evidence_digest

    def test_different_evidence_different_digest(self) -> None:
        ev1 = VerifiedRatingEvidenceSnapshot(rating_status="succeeded", heat_duty_w=100.0)
        ev2 = VerifiedRatingEvidenceSnapshot(rating_status="succeeded", heat_duty_w=200.0)
        assert ev1.evidence_digest != ev2.evidence_digest


class TestAdapterMapping:
    """Verification that unverified results don't leak thermal metrics."""

    def test_unverified_no_leak(self) -> None:
        """Hash false result must NOT populate verified_rating_evidence."""
        result = _make_rating_result(
            result_hash="sha256:" + "0" * 64,
            heat_duty_w=999.0,  # would be in unverified result
        )
        record = verify_and_evaluate_candidate(0, "sq_test", result)
        assert record.verified_rating_evidence is None
        # The invalid evidence must NOT carry thermal metrics
        ie = record.invalid_rating_evidence
        if ie is not None:
            # InvalidRatingEvidenceRecord has no thermal fields
            assert not hasattr(ie, "heat_duty_w")


# ============================================================================
# Helpers: mock RatingResult objects
# ============================================================================


def _make_rating_result(
    status: RatingStatus = RatingStatus.SUCCEEDED,
    result_hash: str | None = None,
    provenance_passes: bool = True,
    heat_duty_w: float = 1000.0,
) -> Any:
    """Build a simple duck-typed mock rating result that bypasses the
    real ``RatingResult`` model_post_init complexity.

    Implements enough of ``RatingResult``'s interface for
    ``verify_and_evaluate_candidate`` to work.
    """
    h = result_hash or "sha256:" + "e" * 64

    # Create a simple type that passes isinstance(RatingResult) for the
    # verification check, but bypasses all Pydantic validation complexity.
    # We create a minimal proxy that inherits from RatingResult but
    # skips its __init__.
    class _MinimalRatingResult(RatingResult):
        """Minimal subclass that bypasses Pydantic frozen restrictions."""

        def __init__(self) -> None:
            # Use object.__setattr__ to bypass Pydantic frozen check
            object.__setattr__(self, "status", status)
            object.__setattr__(self, "flow_arrangement", FlowArrangement.COUNTERFLOW)
            object.__setattr__(self, "result_hash", h)
            object.__setattr__(self, "heat_duty_w", heat_duty_w)
            object.__setattr__(self, "hot_outlet_temperature_k", 350.0)
            object.__setattr__(self, "cold_outlet_temperature_k", 310.0)
            object.__setattr__(self, "area_inner_m2", 1.5)
            object.__setattr__(self, "area_outer_m2", 2.0)
            object.__setattr__(self, "UA_w_k", 500.0)
            object.__setattr__(self, "LMTD_k", 40.0)
            object.__setattr__(self, "energy_residual_w", 0.001)
            object.__setattr__(self, "ua_lmtd_residual_w", 0.002)
            object.__setattr__(self, "tube_selected_correlation_id", "tube_corr_1")
            object.__setattr__(self, "tube_selected_correlation_version", "1.0")
            object.__setattr__(self, "annulus_selected_correlation_id", "ann_corr_1")
            object.__setattr__(self, "annulus_selected_correlation_version", "1.0")
            object.__setattr__(self, "warnings", ())
            object.__setattr__(self, "blockers", ())
            object.__setattr__(self, "failure", None)
            object.__setattr__(self, "provenance_digest", "mock_prov_digest")
            object.__setattr__(self, "request_identity", None)
            object.__setattr__(self, "execution_context", None)
            object.__setattr__(self, "provider_identity", None)
            # Set patched methods
            object.__setattr__(self, "verify_hash", self._verify_hash)
            object.__setattr__(self, "verify_provenance", self._verify_provenance)

        @staticmethod
        def _verify_hash() -> bool:
            return not (
                result_hash is not None and not result_hash.startswith("sha256:" + "e" * 64)
            )

        @staticmethod
        def _verify_provenance() -> bool:
            return provenance_passes

    return _MinimalRatingResult()


def _make_broken_rating_result(
    hash_raises: bool = False,
    provenance_raises: bool = False,
) -> Any:
    """Build a RatingResult whose verify methods raise exceptions."""
    # Use _make_rating_result and then override the methods
    result = _make_rating_result(status=RatingStatus.SUCCEEDED)

    if hash_raises:

        def _raise_hash() -> bool:
            raise RuntimeError("Hash verification crashed")

        object.__setattr__(result, "verify_hash", _raise_hash)

    if provenance_raises:

        def _raise_prov() -> bool:
            raise RuntimeError("Provenance verification crashed")

        object.__setattr__(result, "verify_provenance", _raise_prov)

    return result


# ============================================================================
# Safe audit extraction tests
# ============================================================================


class TestSafeAudit:
    """Safe extraction only reads allowed fields."""

    def test_safe_fields_extracted(self) -> None:
        from hexagent.optimization.evaluation import safe_extract_claimed_audit

        result = _make_rating_result()
        audit = safe_extract_claimed_audit(result)
        assert "status" in audit
        assert "result_hash" in audit

    def test_non_rating_object(self) -> None:
        from hexagent.optimization.evaluation import safe_extract_claimed_audit

        audit = safe_extract_claimed_audit(42)
        # Should not raise
        assert isinstance(audit, dict)
