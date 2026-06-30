"""Typed artifact bundles for rating and sizing runs (TASK-010 Phase 2).

Provides frozen Pydantic models that bind together all inputs, outputs,
provenance, and integrity hashes for a completed run.  Construction
auto-verifies all hash parities via ``model_validator(mode="after")``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import ConfigDict, model_validator

from hexagent.api.models import ResolvedProviderAuthority
from hexagent.core.canonical import sha256_digest
from hexagent.domain.models import StrictBaseModel
from hexagent.domain.provenance import ProvenanceGraph
from hexagent.exchangers.double_pipe.result import RatingResult

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Bundle hash helper
# ---------------------------------------------------------------------------


def compute_bundle_hash(artifacts_dict: dict[str, Any]) -> str:
    """Compute deterministic bundle hash excluding the ``bundle_hash`` field.

    Parameters
    ----------
    artifacts_dict:
        A dict of all bundle fields (typically from ``model_dump()``).

    Returns
    -------
    str
        A ``sha256:`` prefixed hex digest of the canonical JSON
        representation of all fields except ``bundle_hash``.
    """
    filtered = {k: v for k, v in artifacts_dict.items() if k != "bundle_hash"}
    return sha256_digest(filtered)


# ---------------------------------------------------------------------------
# Rating bundle
# ---------------------------------------------------------------------------


class RatingRunArtifacts(StrictBaseModel):
    """Typed artifact bundle for rating runs.

    Binds together the canonical request snapshot, resolved provider
    authority, geometry/solver artifacts, the domain result, and the
    full provenance graph.  All integrity hashes are verified on
    construction.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical_request_snapshot: dict[str, Any]
    resolved_provider: ResolvedProviderAuthority
    geometry_artifact: dict[str, Any]
    solver_artifact: dict[str, Any]
    rating_result: RatingResult
    result_hash: str
    provenance_graph: ProvenanceGraph
    provenance_digest: str
    bundle_hash: str

    # -- auto-verify on construction ----------------------------------------

    @model_validator(mode="after")
    def _verify_hashes(self) -> RatingRunArtifacts:
        verify_rating_bundle(self)
        return self


# ---------------------------------------------------------------------------
# Sizing bundle
# ---------------------------------------------------------------------------


class SizingRunArtifacts(StrictBaseModel):
    """Typed artifact bundle for sizing runs.

    Binds together the canonical request snapshot, sizing request and
    identity, resolved provider and catalogs, the optimization result,
    and the full provenance graph.  All integrity hashes are verified on
    construction.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical_request_snapshot: dict[str, Any]
    sizing_request: Any  # SizingRequest
    sizing_request_identity: Any  # SizingRequestIdentity
    resolved_provider: ResolvedProviderAuthority
    resolved_catalogs: tuple[Any, ...]  # tuple[CompleteDoublePipeCatalogSnapshot, ...]
    optimization_result: Any  # OptimizationResult
    result_hash: str
    provenance_graph: ProvenanceGraph
    provenance_digest: str
    bundle_hash: str

    # -- auto-verify on construction ----------------------------------------

    @model_validator(mode="after")
    def _verify_hashes(self) -> SizingRunArtifacts:
        verify_sizing_bundle(self)
        return self


# ---------------------------------------------------------------------------
# Verification functions
# ---------------------------------------------------------------------------


def verify_rating_bundle(artifacts: RatingRunArtifacts) -> None:
    """Verify all hash parities in a rating bundle.

    Raises
    ------
    ValueError
        If any hash does not match its expected value.
    """
    # 1. result_hash parity
    if artifacts.result_hash != artifacts.rating_result.result_hash:
        raise ValueError(
            f"result_hash mismatch: bundle has {artifacts.result_hash!r}, "
            f"rating_result has {artifacts.rating_result.result_hash!r}"
        )

    # 2. provenance_digest parity
    computed_prov = artifacts.provenance_graph.compute_hash()
    if artifacts.provenance_digest != computed_prov:
        raise ValueError(
            f"provenance_digest mismatch: bundle has {artifacts.provenance_digest!r}, "
            f"provenance_graph.compute_hash() returned {computed_prov!r}"
        )

    # 3. bundle_hash parity
    computed_bundle = compute_bundle_hash(artifacts.model_dump())
    if artifacts.bundle_hash != computed_bundle:
        raise ValueError(
            f"bundle_hash mismatch: bundle has {artifacts.bundle_hash!r}, "
            f"recomputed {computed_bundle!r}"
        )


def verify_sizing_bundle(artifacts: SizingRunArtifacts) -> None:
    """Verify all hash parities in a sizing bundle.

    Raises
    ------
    ValueError
        If any hash does not match its expected value.
    """
    # 1. result_hash parity
    if artifacts.result_hash != artifacts.optimization_result.result_hash:
        raise ValueError(
            f"result_hash mismatch: bundle has {artifacts.result_hash!r}, "
            f"optimization_result has {artifacts.optimization_result.result_hash!r}"
        )

    # 2. provenance_digest parity
    computed_prov = artifacts.provenance_graph.compute_hash()
    if artifacts.provenance_digest != computed_prov:
        raise ValueError(
            f"provenance_digest mismatch: bundle has {artifacts.provenance_digest!r}, "
            f"provenance_graph.compute_hash() returned {computed_prov!r}"
        )

    # 3. bundle_hash parity
    computed_bundle = compute_bundle_hash(artifacts.model_dump())
    if artifacts.bundle_hash != computed_bundle:
        raise ValueError(
            f"bundle_hash mismatch: bundle has {artifacts.bundle_hash!r}, "
            f"recomputed {computed_bundle!r}"
        )


__all__ = [
    "RatingRunArtifacts",
    "SizingRunArtifacts",
    "compute_bundle_hash",
    "verify_rating_bundle",
    "verify_sizing_bundle",
]
