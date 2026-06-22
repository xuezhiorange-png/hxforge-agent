"""CorrelationUsageRecord for provenance tracking."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from hexagent.correlations.models import (
    ApplicabilityAssessment,
    ApplicabilityStatus,
    ApplicabilityVariable,
    CorrelationApplicabilityInput,
    CorrelationDefinition,
    CorrelationKey,
    UncertaintySpec,
    _validate_hash_format,
    _validate_no_nan_inf,
)
from hexagent.domain.provenance import ProvenanceNode, ProvenanceNodeType

# Stable HXForge namespace for deterministic UUIDs
HXFORGE_NAMESPACE = UUID("54767866-6f72-6765-2d61-67656e742d76")  # "hxforge-agent-v" in hex


class CorrelationUsageRecord(BaseModel):
    """Immutable record of correlation usage for provenance tracking.

    Captures which correlation was used, the input values, applicability
    status, and links to the source definition and assessment hashes.

    Item 8: source_id is the BibliographicSource.source_id (not a run ID).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    correlation_key: CorrelationKey
    definition_hash: str
    source_id: str
    applicability_status: ApplicabilityStatus
    input_values: tuple[tuple[ApplicabilityVariable, float], ...]
    assessment_hash: str
    extrapolation_used: bool
    uncertainty: UncertaintySpec | None = None

    @field_validator("definition_hash")
    @classmethod
    def _validate_definition_hash(cls, v: str) -> str:
        _validate_hash_format(v, "definition_hash")
        return v

    @field_validator("assessment_hash")
    @classmethod
    def _validate_assessment_hash(cls, v: str) -> str:
        _validate_hash_format(v, "assessment_hash")
        return v

    @field_validator("input_values", mode="before")
    @classmethod
    def _normalize_input_values(cls, v: Any) -> tuple[tuple[ApplicabilityVariable, float], ...]:
        """Accept dict, list-of-pairs, or tuple-of-pairs.
        Sort and deduplicate. Reject NaN/Inf.
        """
        pairs: list[tuple[ApplicabilityVariable, float]] = []
        if isinstance(v, dict):
            raw = list(v.items())
        elif isinstance(v, (list, tuple)):
            raw = list(v)
        else:
            raise ValueError(f"input_values must be dict or list-of-pairs, got {type(v).__name__}")

        seen: set[ApplicabilityVariable] = set()
        for item in raw:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise ValueError(f"Each input value pair must be (variable, float), got {item!r}")
            var, val = item
            if isinstance(var, str):
                var = ApplicabilityVariable(var)
            if not isinstance(val, (int, float)):
                raise ValueError(f"Value must be numeric, got {val!r}")
            _validate_no_nan_inf(float(val), f"input value for {var}")
            if var in seen:
                raise ValueError(f"Duplicate variable in input_values: {var!r}")
            seen.add(var)
            pairs.append((var, float(val)))
        return tuple(sorted(pairs, key=lambda p: p[0].value))

    @model_validator(mode="after")
    def _validate_consistency(self) -> CorrelationUsageRecord:
        """Item 8: If applicability_status is explicit_extrapolation then
        extrapolation_used must be True.  Bidirectional: extrapolation_used=True
        requires applicability_status='explicit_extrapolation'."""
        if (
            self.applicability_status == ApplicabilityStatus.explicit_extrapolation
            and not self.extrapolation_used
        ):
            raise ValueError(
                "extrapolation_used must be True when applicability_status "
                "is explicit_extrapolation"
            )
        if (
            self.extrapolation_used
            and self.applicability_status != ApplicabilityStatus.explicit_extrapolation
        ):
            raise ValueError(
                "extrapolation_used=True requires applicability_status='explicit_extrapolation'"
            )
        return self

    @classmethod
    def create(
        cls,
        definition: CorrelationDefinition,
        assessment: ApplicabilityAssessment,
        inputs: CorrelationApplicabilityInput,
        uncertainty: UncertaintySpec | None = None,
    ) -> CorrelationUsageRecord:
        """Factory that cross-validates definition, assessment, and inputs.

        Recomputes the expected assessment from definition+inputs and
        verifies the supplied assessment matches.  This prevents callers
        from injecting a forged or mismatched assessment.
        """
        from hexagent.correlations.applicability import assess_applicability

        # Recompute expected assessment from the authoritative sources
        expected = assess_applicability(definition, inputs)

        # Cross-validate supplied assessment against expected
        if assessment.correlation_key != expected.correlation_key:
            raise ValueError("assessment.correlation_key does not match expected")
        if assessment.assessment_hash != expected.assessment_hash:
            raise ValueError("assessment.assessment_hash does not match expected")
        if assessment.status != expected.status:
            raise ValueError("assessment.status does not match expected")
        if assessment.variable_results != expected.variable_results:
            raise ValueError("assessment.variable_results do not match expected")
        if assessment.warnings != expected.warnings:
            raise ValueError("assessment.warnings do not match expected")
        if assessment.blockers != expected.blockers:
            raise ValueError("assessment.blockers do not match expected")
        if assessment.allows_evaluation != expected.allows_evaluation:
            raise ValueError("assessment.allows_evaluation does not match expected")

        # Derive fields from verified assessment
        extrapolation_used = assessment.status == ApplicabilityStatus.explicit_extrapolation

        record = cls(
            correlation_key=definition.key,
            definition_hash=definition.definition_hash,
            source_id=definition.source.source_id,
            applicability_status=assessment.status,
            input_values=inputs.values,
            assessment_hash=assessment.assessment_hash,
            extrapolation_used=extrapolation_used,
            uncertainty=uncertainty,
        )
        return record

    @property
    def usage_hash(self) -> str:
        """Item 8: Stable hash of the complete record including uncertainty."""
        from hexagent.core.canonical import sha256_digest

        payload = {
            "correlation_key": {
                "correlation_id": self.correlation_key.correlation_id,
                "version": self.correlation_key.version,
            },
            "definition_hash": self.definition_hash,
            "source_id": self.source_id,
            "applicability_status": self.applicability_status.value,
            "input_values": [(var.value, val) for var, val in self.input_values],
            "assessment_hash": self.assessment_hash,
            "extrapolation_used": self.extrapolation_used,
            "uncertainty": (
                {
                    "relative_uncertainty_fraction": self.uncertainty.relative_uncertainty_fraction,
                    "confidence_level_fraction": self.uncertainty.confidence_level_fraction,
                    "basis": self.uncertainty.basis,
                    "source_id": self.uncertainty.source_id,
                }
                if self.uncertainty is not None
                else None
            ),
        }
        return sha256_digest(payload)

    def to_provenance_node(self) -> ProvenanceNode:
        """Item 8: Convert this usage record to a ProvenanceNode for graph insertion.

        node_id is deterministically derived from usage_hash using uuid5
        with the HXForge namespace. Does NOT call uuid4().
        """
        usage_hash = self.usage_hash
        # Domain-separated UUID5 from HXForge namespace + usage hash
        node_uuid = uuid5(HXFORGE_NAMESPACE, usage_hash)

        metadata: list[tuple[str, Any]] = [
            ("correlation_id", self.correlation_key.correlation_id),
            ("correlation_version", self.correlation_key.version),
            ("definition_hash", self.definition_hash),
            ("assessment_hash", self.assessment_hash),
            ("usage_hash", usage_hash),
            ("source_id", self.source_id),
            ("applicability_status", self.applicability_status.value),
            ("extrapolation_used", self.extrapolation_used),
        ]
        if self.uncertainty is not None:
            metadata.append(("uncertainty_basis", self.uncertainty.basis))
            if self.uncertainty.source_id:
                metadata.append(("uncertainty_source_id", self.uncertainty.source_id))

        return ProvenanceNode(
            node_id=node_uuid,
            node_type=ProvenanceNodeType.CORRELATION,
            label=f"{self.correlation_key.correlation_id} v{self.correlation_key.version}",
            metadata=tuple(metadata),
            payload_hash=usage_hash,
        )


__all__ = ["CorrelationUsageRecord", "HXFORGE_NAMESPACE"]
