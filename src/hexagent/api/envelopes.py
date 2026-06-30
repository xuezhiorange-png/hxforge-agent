"""TASK-010 frozen run envelopes and artifact bundles.

Implements contract §6 (envelopes) and §9 (artifact bundles).

Envelopes:
  - ValidationRunEnvelope (operation = "validateCase")
  - RatingRunEnvelope     (operation = "rateDoublePipe")
  - SizingRunEnvelope      (operation = "sizeDoublePipe")
  - AnyRunEnvelope         (discriminated union by result_kind)

Artifact bundles are opaque Any-typed at this layer; the contract
requires cross-field verification in envelope model_validators.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import model_validator

from hexagent.domain.models import StrictBaseModel

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

    artifact_bundle is opaque at the API layer; cross-field
    verification is performed in the model_validator.
    """

    api_schema_version: Literal["1"]
    operation: Literal["rateDoublePipe"]
    run_id: UUID
    idempotency_key_digest: str
    request_digest: str
    result_kind: Literal["rating"]
    result: Any  # RatingResult
    result_hash: str
    warnings: tuple[Any, ...]
    blockers: tuple[Any, ...]
    failure: Any | None
    provenance: Any  # ProvenanceGraph
    provenance_digest: str
    artifact_bundle: Any  # RatingRunArtifacts
    artifact_bundle_digest: str
    report_links: ReportLinks | None

    @model_validator(mode="after")
    def _verify_hashes(self) -> RatingRunEnvelope:
        """Cross-field hash parity per contract §6.2."""
        result = self.result
        if hasattr(result, "result_hash") and self.result_hash != result.result_hash:
            raise ValueError("result_hash mismatch: envelope != result.result_hash")
        if (
            hasattr(result, "provenance_digest")
            and self.provenance_digest != result.provenance_digest
        ):  # noqa: E501  # noqa: E501
            raise ValueError("provenance_digest != result.provenance_digest")
        return self


# ---------------------------------------------------------------------------
# Sizing envelope
# ---------------------------------------------------------------------------


class SizingRunEnvelope(StrictBaseModel):
    """Sizing run response per contract §6.3.

    artifact_bundle is opaque at the API layer; cross-field
    verification is performed in the model_validator.
    """

    api_schema_version: Literal["1"]
    operation: Literal["sizeDoublePipe"]
    run_id: UUID
    idempotency_key_digest: str
    request_digest: str
    result_kind: Literal["sizing"]
    result: Any  # OptimizationResult
    result_hash: str
    warnings: tuple[Any, ...]
    blockers: tuple[Any, ...]
    failure: Any | None
    provenance: Any  # ProvenanceGraph
    provenance_digest: str
    artifact_bundle: Any  # SizingRunArtifacts
    artifact_bundle_digest: str
    report_links: ReportLinks | None

    @model_validator(mode="after")
    def _verify_hashes(self) -> SizingRunEnvelope:
        """Cross-field hash parity per contract §6.3."""
        result = self.result
        if hasattr(result, "result_hash") and self.result_hash != result.result_hash:
            raise ValueError("result_hash mismatch: envelope != result.result_hash")
        if (
            hasattr(result, "provenance_digest")
            and self.provenance_digest != result.provenance_digest
        ):  # noqa: E501
            raise ValueError("provenance_digest != result.provenance_digest")
        if self.failure is not None:
            raise ValueError("sizing failure must be None")
        return self


# ---------------------------------------------------------------------------
# Discriminated union
# ---------------------------------------------------------------------------

AnyRunEnvelope = ValidationRunEnvelope | RatingRunEnvelope | SizingRunEnvelope
