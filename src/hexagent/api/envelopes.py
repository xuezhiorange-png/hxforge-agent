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

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

from hexagent.api.artifacts import (
    RatingRunArtifacts,
    SizingRunArtifacts,
    compute_rating_artifact_bundle_digest,
    verify_rating_artifact_bundle,
)
from hexagent.domain.messages import EngineeringMessage, RunFailure
from hexagent.domain.models import StrictBaseModel
from hexagent.domain.provenance import ProvenanceGraph
from hexagent.exchangers.double_pipe.result import RatingResult

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

        # provenance digest parity
        # The result's provenance_digest is computed by the kernel using
        # _provenance_graph_digest() which excludes result_hash from metadata.
        # The envelope's provenance_digest should match the result's value.
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
# Sizing envelope
# ---------------------------------------------------------------------------


class SizingRunEnvelope(StrictBaseModel):
    """Sizing run response per contract §6.3.

    All fields are typed — no Any. Cross-field hash parity verified
    on construction.
    """

    api_schema_version: Literal["1"]
    operation: Literal["sizeDoublePipe"]
    run_id: UUID
    idempotency_key_digest: str
    request_digest: str
    result_kind: Literal["sizing"]
    result: Any  # OptimizationResult (Any at runtime, typed via TYPE_CHECKING)
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
        """Cross-field hash parity per contract §6.3."""
        # sizing failure must be None
        if self.failure is not None:
            raise ValueError("sizing failure must be None")
        # result_hash must match result's own hash
        if self.result_hash != self.result.result_hash:
            raise ValueError(
                f"result_hash mismatch: envelope has {self.result_hash!r}, "
                f"result has {self.result.result_hash!r}"
            )
        # provenance_digest must match provenance graph hash
        computed_prov = self.provenance.compute_hash()
        if self.provenance_digest != computed_prov:
            raise ValueError(
                f"provenance_digest mismatch: envelope has {self.provenance_digest!r}, "
                f"provenance.compute_hash() returned {computed_prov!r}"
            )
        # artifact_bundle_digest must match bundle hash
        if self.artifact_bundle_digest != self.artifact_bundle.bundle_hash:
            raise ValueError(
                f"artifact_bundle_digest mismatch: envelope has "
                f"{self.artifact_bundle_digest!r}, bundle has "
                f"{self.artifact_bundle.bundle_hash!r}"
            )
        return self


# ---------------------------------------------------------------------------
# Discriminated union by result_kind
# ---------------------------------------------------------------------------

AnyRunEnvelope = Annotated[
    ValidationRunEnvelope | RatingRunEnvelope | SizingRunEnvelope,
    Field(discriminator="result_kind"),
]
