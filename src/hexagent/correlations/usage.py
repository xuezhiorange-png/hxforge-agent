"""CorrelationUsageRecord for provenance tracking."""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from hexagent.correlations.models import (
    ApplicabilityStatus,
    CorrelationKey,
    UncertaintySpec,
)
from hexagent.domain.provenance import ProvenanceNode, ProvenanceNodeType


class CorrelationUsageRecord(BaseModel):
    """Immutable record of correlation usage for provenance tracking.

    Captures which correlation was used, the input values, applicability
    status, and links to the source definition and assessment hashes.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    correlation_key: CorrelationKey
    definition_hash: str
    source_id: str
    applicability_status: ApplicabilityStatus
    input_values: tuple[tuple[str, float], ...]
    assessment_hash: str
    extrapolation_used: bool
    uncertainty: UncertaintySpec | None = None

    def to_provenance_node(self) -> ProvenanceNode:
        """Convert this usage record to a ProvenanceNode for graph insertion.

        The payload_hash is derived from the SHA-256 of this record's
        canonical JSON representation.
        """

        from hexagent.core.canonical import sha256_digest

        # Build a serialisable dict for hashing
        payload = {
            "correlation_key": {
                "correlation_id": self.correlation_key.correlation_id,
                "version": self.correlation_key.version,
            },
            "definition_hash": self.definition_hash,
            "source_id": self.source_id,
            "applicability_status": self.applicability_status.value,
            "input_values": dict(self.input_values),
            "assessment_hash": self.assessment_hash,
            "extrapolation_used": self.extrapolation_used,
        }
        payload_hash = sha256_digest(payload)

        metadata: list[tuple[str, Any]] = [
            ("correlation_id", self.correlation_key.correlation_id),
            ("correlation_version", self.correlation_key.version),
            ("source_id", self.source_id),
            ("applicability_status", self.applicability_status.value),
            ("extrapolation_used", self.extrapolation_used),
        ]
        if self.uncertainty is not None:
            metadata.append(("uncertainty_basis", self.uncertainty.basis))

        return ProvenanceNode(
            node_id=uuid4(),
            node_type=ProvenanceNodeType.CORRELATION,
            label=f"{self.correlation_key.correlation_id} v{self.correlation_key.version}",
            metadata=tuple(metadata),
            payload_hash=payload_hash,
        )


__all__ = ["CorrelationUsageRecord"]
