"""Typed artifact bundles for rating and sizing runs (TASK-010 Phase 2).

Provides frozen Pydantic models that bind together all inputs, outputs,
provenance, and integrity hashes for a completed run.  Construction
auto-verifies all hash parities via ``model_validator(mode="after")``.

A1: All fields are runtime-typed — no Any in public models.
A4: Sizing artifact bundle verifier with full parity checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ConfigDict, model_validator

from hexagent.core.canonical import sha256_digest
from hexagent.core.heat_balance import ProviderIdentitySnapshot
from hexagent.domain.models import StrictBaseModel
from hexagent.domain.provenance import ProvenanceGraph
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.result import (
    RatingRequestIdentity,
    RatingResult,
)
from hexagent.exchangers.double_pipe.solver import SolverParams

if TYPE_CHECKING:
    from hexagent.optimization.models import SizingRequest
    from hexagent.optimization.phase3_builder import (
        OptimizationResult,
        RankedCandidateRecord,
    )
    from hexagent.optimization.phase3_evaluation import (
        CandidateDispositionRecord,
        Phase3EvaluationInput,
    )
    from hexagent.optimization.phase3_verifier import Phase3AuthoritativeArtifacts


# ---------------------------------------------------------------------------
# Rating bundle digest (P0-3)
# ---------------------------------------------------------------------------


def compute_rating_artifact_bundle_digest(bundle: RatingRunArtifacts) -> str:
    """Compute deterministic bundle digest excluding the digest field itself."""
    payload = bundle.model_dump(mode="python")
    # Remove the digest field from the payload
    payload.pop("artifact_bundle_digest", None)
    return sha256_digest(payload)


# ---------------------------------------------------------------------------
# Rating bundle verifier (P0-3)
# ---------------------------------------------------------------------------


def verify_rating_artifact_bundle(bundle: RatingRunArtifacts) -> None:
    """Verify all parities in a rating bundle."""
    # 1. bundle digest recompute
    expected_digest = compute_rating_artifact_bundle_digest(bundle)
    if bundle.artifact_bundle_digest != expected_digest:
        raise ValueError("artifact_bundle_digest mismatch")

    # 5. result request identity parity
    if bundle.result.request_identity != bundle.request_identity:
        raise ValueError("result request_identity mismatch")

    # 6. result provider identity parity
    if bundle.result.provider_identity != bundle.provider_identity:
        raise ValueError("result provider_identity mismatch")

    # 7. provenance object parity
    if bundle.result.provenance_graph != bundle.provenance_graph:
        raise ValueError("result provenance_graph mismatch")


# ---------------------------------------------------------------------------
# Rating bundle (P0-3 — precise frozen contract)
# ---------------------------------------------------------------------------


class RatingRunArtifacts(StrictBaseModel):
    """Frozen contract RatingRunArtifacts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical_request_snapshot: dict[str, object]
    request_identity: RatingRequestIdentity
    geometry_snapshot: DoublePipeGeometry
    solver_settings: SolverParams
    provider_identity: ProviderIdentitySnapshot
    result: RatingResult
    provenance_graph: ProvenanceGraph
    artifact_bundle_digest: str

    # -- auto-verify on construction ----------------------------------------

    @model_validator(mode="after")
    def _verify_bundle(self) -> RatingRunArtifacts:
        verify_rating_artifact_bundle(self)
        return self


# ---------------------------------------------------------------------------
# Sizing bundle hash helper
# ---------------------------------------------------------------------------


def compute_sizing_artifact_bundle_digest(
    bundle: SizingRunArtifacts,
) -> str:
    """Compute deterministic bundle digest excluding the digest field itself.

    Serializes all fields except ``artifact_bundle_digest`` to a canonical
    Python representation and computes sha256.
    """
    payload = bundle.model_dump(mode="python")
    payload.pop("artifact_bundle_digest", None)
    return sha256_digest(payload)


# ---------------------------------------------------------------------------
# Sizing bundle verifier (A4)
# ---------------------------------------------------------------------------


def verify_sizing_artifact_bundle(artifacts: SizingRunArtifacts) -> None:
    """Verify all parities in a sizing artifact bundle (A4).

    Checks:
    1. artifact_bundle_digest recompute
    2. provenance_digest == optimization_result.provenance_digest
    3. Top-N is prefix of ranked records
    4. disposition count == optimization_result.total_candidate_count
    5. ranked count == optimization_result.feasible_candidate_count
    """
    # 1. Bundle digest recompute
    expected_digest = compute_sizing_artifact_bundle_digest(artifacts)
    if artifacts.artifact_bundle_digest != expected_digest:
        raise ValueError(
            f"artifact_bundle_digest mismatch: bundle has "
            f"{artifacts.artifact_bundle_digest!r}, recomputed {expected_digest!r}"
        )

    opt = artifacts.optimization_result

    # 2. provenance_digest parity (C2: single provenance digest authority)
    computed_prov = artifacts.provenance_graph.compute_hash()
    if opt.provenance_digest != computed_prov:
        raise ValueError(
            f"provenance_digest mismatch: result has {opt.provenance_digest!r}, "
            f"provenance_graph.compute_hash() returned {computed_prov!r}"
        )

    # 3. Top-N is prefix of ranked records
    if artifacts.top_n_records != artifacts.ranked_records[: len(artifacts.top_n_records)]:
        raise ValueError("top_n_records is not a prefix of ranked_records")

    # 4. Disposition count matches total
    if len(artifacts.dispositions) != opt.total_candidate_count:
        raise ValueError(
            f"dispositions count {len(artifacts.dispositions)} != "
            f"total_candidate_count {opt.total_candidate_count}"
        )

    # 5. Ranked count matches feasible
    if len(artifacts.ranked_records) != opt.feasible_candidate_count:
        raise ValueError(
            f"ranked_records count {len(artifacts.ranked_records)} != "
            f"feasible_candidate_count {opt.feasible_candidate_count}"
        )

    # 6. Top-N count matches min(requested, feasible)
    expected_top_n = min(opt.requested_top_n, opt.feasible_candidate_count)
    if len(artifacts.top_n_records) != expected_top_n:
        raise ValueError(
            f"top_n_records count {len(artifacts.top_n_records)} != expected {expected_top_n}"
        )


# ---------------------------------------------------------------------------
# Sizing bundle (A1 — fully typed, no Any at runtime after model_rebuild)
# ---------------------------------------------------------------------------


class SizingRunArtifacts(StrictBaseModel):
    """Typed artifact bundle for sizing runs (A1).

    All fields use forward references resolved at import time via
    model_rebuild.  ``from __future__ import annotations`` turns all
    annotations into strings so Python never tries to resolve them
    eagerly; Pydantic resolves them when the model is first used.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    canonical_request_snapshot: dict[str, object]
    sizing_request: SizingRequest
    evaluation_input: Phase3EvaluationInput
    phase3_authoritative_artifacts: Phase3AuthoritativeArtifacts
    dispositions: tuple[CandidateDispositionRecord, ...]
    ranked_records: tuple[RankedCandidateRecord, ...]
    top_n_records: tuple[RankedCandidateRecord, ...]
    optimization_result: OptimizationResult
    provenance_graph: ProvenanceGraph
    artifact_bundle_digest: str

    # -- auto-verify on construction ----------------------------------------

    @model_validator(mode="after")
    def _verify_bundle(self) -> SizingRunArtifacts:
        verify_sizing_artifact_bundle(self)
        return self


# ---------------------------------------------------------------------------
# Rebuild models to resolve forward references at runtime
# ---------------------------------------------------------------------------


def _rebuild_sizing_models() -> None:
    """Resolve forward references in SizingRunArtifacts."""
    try:
        from hexagent.optimization.models import SizingRequest as _SR
        from hexagent.optimization.phase3_builder import (
            OptimizationResult as _OR,
        )
        from hexagent.optimization.phase3_builder import (
            RankedCandidateRecord as _RCR,
        )
        from hexagent.optimization.phase3_evaluation import (
            CandidateDispositionRecord as _CDR,
        )
        from hexagent.optimization.phase3_evaluation import (
            Phase3EvaluationInput as _PEI,
        )
        from hexagent.optimization.phase3_verifier import (
            Phase3AuthoritativeArtifacts as _PAA,
        )

        SizingRunArtifacts.model_rebuild(
            _types_namespace={
                "SizingRequest": _SR,
                "Phase3EvaluationInput": _PEI,
                "Phase3AuthoritativeArtifacts": _PAA,
                "CandidateDispositionRecord": _CDR,
                "RankedCandidateRecord": _RCR,
                "OptimizationResult": _OR,
            },
        )
    except ImportError:
        pass  # optimization module not available during minimal imports


_rebuild_sizing_models()


__all__ = [
    "RatingRunArtifacts",
    "SizingRunArtifacts",
    "compute_rating_artifact_bundle_digest",
    "compute_sizing_artifact_bundle_digest",
    "verify_rating_artifact_bundle",
    "verify_sizing_artifact_bundle",
]
