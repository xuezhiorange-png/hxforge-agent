"""TASK-010 frozen run envelopes with typed artifact bundles.

Implements contract §6 (envelopes) and §9 (artifact bundles).

Envelopes:
  - ValidationRunEnvelope (operation = "validateCase")
  - RatingRunEnvelope     (operation = "rateDoublePipe")
  - SizingRunEnvelope      (operation = "sizeDoublePipe")
  - AnyRunEnvelope         (discriminated union by result_kind)

All envelope fields are typed — no Any for result, warnings, blockers,
failure, provenance, or artifact_bundle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from hexagent.api.artifacts import (
    RatingRunArtifacts,
    SizingRunArtifacts,
    compute_rating_artifact_bundle_digest,
    compute_sizing_artifact_bundle_digest,
    verify_rating_artifact_bundle,
)
from hexagent.domain.messages import EngineeringMessage, RunFailure
from hexagent.domain.models import StrictBaseModel
from hexagent.domain.provenance import ProvenanceGraph
from hexagent.exchangers.double_pipe.result import RatingResult

if TYPE_CHECKING:
    from hexagent.optimization.phase3_builder import OptimizationResult


# ---------------------------------------------------------------------------
# Report links
# ---------------------------------------------------------------------------


class ReportLinks(StrictBaseModel):
    """Links to generated reports for a completed run."""

    html: str | None = None
    pdf: str | None = None


# ---------------------------------------------------------------------------
# Validation envelope (no idempotency, no artifact bundle)
# ---------------------------------------------------------------------------


class ValidationRunEnvelope(StrictBaseModel):
    """Validation run response per contract §6.1."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    api_schema_version: Literal["1"]
    operation: Literal["validateCase"]
    run_id: UUID
    request_digest: str
    result_kind: Literal["validation"]
    result: None
    validation_receipt_hash: str
    report_links: None


# ---------------------------------------------------------------------------
# Rating envelope
# ---------------------------------------------------------------------------


class RatingRunEnvelope(StrictBaseModel):
    """Rating run response per contract §6.2.

    All fields are typed — no Any. Cross-field hash parity verified
    on construction.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    api_schema_version: Literal["1"]
    operation: Literal["rateDoublePipe"]
    run_id: UUID
    idempotency_key_digest: str
    request_digest: str
    result_kind: Literal["rating"]
    result: RatingResult
    result_hash: str
    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]
    failure: RunFailure | None
    provenance: ProvenanceGraph
    provenance_digest: str
    artifact_bundle: RatingRunArtifacts
    artifact_bundle_digest: str
    report_links: ReportLinks | None

    @model_validator(mode="after")
    def _verify_hashes(self) -> RatingRunEnvelope:
        """Complete cross-field hash parity per contract §6.2 (P0-4)."""
        # result_hash parity
        if self.result_hash != self.result.result_hash:
            raise ValueError("result_hash mismatch")

        # warnings parity
        if self.warnings != self.result.warnings:
            raise ValueError("warnings mismatch")

        # blockers parity
        if self.blockers != self.result.blockers:
            raise ValueError("blockers mismatch")

        # failure parity
        if self.failure != self.result.failure:
            raise ValueError("failure mismatch")

        # provenance object parity
        if self.provenance != self.result.provenance_graph:
            raise ValueError("provenance mismatch")

        # provenance digest parity (C2: single authority)
        if self.provenance_digest != self.result.provenance_digest:
            raise ValueError("provenance_digest != result.provenance_digest")

        # bundle parity
        verify_rating_artifact_bundle(self.artifact_bundle)
        if self.artifact_bundle.result != self.result:
            raise ValueError("bundle result mismatch")
        if self.artifact_bundle.request_identity != self.result.request_identity:
            raise ValueError("bundle request_identity mismatch")
        if self.artifact_bundle.provider_identity != self.result.provider_identity:
            raise ValueError("bundle provider_identity mismatch")
        if self.artifact_bundle.provenance_graph != self.result.provenance_graph:
            raise ValueError("bundle provenance_graph mismatch")

        # bundle digest parity
        expected_digest = compute_rating_artifact_bundle_digest(self.artifact_bundle)
        if self.artifact_bundle_digest != expected_digest:
            raise ValueError("artifact_bundle_digest mismatch")

        return self


# ---------------------------------------------------------------------------
# Sizing envelope (A1 — typed result, A5 — full verifier)
# ---------------------------------------------------------------------------


class SizingRunEnvelope(StrictBaseModel):
    """Sizing run response per contract §6.3.

    All fields are typed — no Any. Cross-field hash parity verified
    on construction.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    api_schema_version: Literal["1"]
    operation: Literal["sizeDoublePipe"]
    run_id: UUID
    idempotency_key_digest: str
    request_digest: str
    result_kind: Literal["sizing"]
    result: OptimizationResult  # A1: typed, not Any
    result_hash: str
    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]
    failure: None  # sizing never has failure
    provenance: ProvenanceGraph
    provenance_digest: str
    artifact_bundle: SizingRunArtifacts
    artifact_bundle_digest: str
    report_links: ReportLinks | None

    @model_validator(mode="after")
    def _verify_hashes(self) -> SizingRunEnvelope:
        """Cross-field hash parity per contract §6.3 (A5)."""
        # sizing failure must be None
        if self.failure is not None:
            raise ValueError("sizing failure must be None")

        # result_hash == result.result_hash
        if self.result_hash != self.result.result_hash:
            raise ValueError(
                f"result_hash mismatch: envelope has {self.result_hash!r}, "
                f"result has {self.result.result_hash!r}"
            )

        # artifact_bundle.optimization_result == result (A5)
        if (
            self.artifact_bundle.optimization_result is not self.result
            and self.artifact_bundle.optimization_result != self.result
        ):
            raise ValueError("bundle optimization_result != envelope result")

        # artifact_bundle_digest recomputation (A5)
        expected_digest = compute_sizing_artifact_bundle_digest(self.artifact_bundle)
        if self.artifact_bundle_digest != expected_digest:
            raise ValueError(
                f"artifact_bundle_digest mismatch: envelope has "
                f"{self.artifact_bundle_digest!r}, recomputed {expected_digest!r}"
            )

        # provenance object parity (A5)
        if self.provenance != self.artifact_bundle.provenance_graph:
            raise ValueError("provenance object mismatch")

        # provenance digest parity (C2: single authority)
        if self.provenance_digest != self.result.provenance_digest:
            raise ValueError(
                f"provenance_digest mismatch: envelope has {self.provenance_digest!r}, "
                f"result has {self.result.provenance_digest!r}"
            )

        return self


# ---------------------------------------------------------------------------
# Rebuild SizingRunEnvelope to resolve OptimizationResult forward ref
# ---------------------------------------------------------------------------


def _rebuild_sizing_envelope() -> None:
    """Resolve OptimizationResult forward reference."""
    try:
        from hexagent.optimization.phase3_builder import OptimizationResult as _OR

        SizingRunEnvelope.model_rebuild(
            _types_namespace={"OptimizationResult": _OR},
        )
    except ImportError:
        pass


_rebuild_sizing_envelope()


# ---------------------------------------------------------------------------
# Discriminated union by result_kind
# ---------------------------------------------------------------------------

AnyRunEnvelope = Annotated[
    ValidationRunEnvelope | RatingRunEnvelope | SizingRunEnvelope,
    Field(discriminator="result_kind"),
]
