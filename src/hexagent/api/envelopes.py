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
        """Cross-field hash parity per contract §6.2."""
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
        # result must be the same object as bundle's result
        if self.result.result_hash != self.artifact_bundle.rating_result.result_hash:
            raise ValueError("result_hash parity: envelope result != bundle result")
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
