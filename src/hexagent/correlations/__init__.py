"""Correlation registry and applicability engine."""

from __future__ import annotations

from hexagent.correlations.applicability import assess_applicability
from hexagent.correlations.errors import (
    CorrelationDuplicateError,
    CorrelationError,
    CorrelationHashMismatchError,
    CorrelationNotFoundError,
    CorrelationVersionNotFoundError,
)
from hexagent.correlations.models import (
    ApplicabilityAssessment,
    ApplicabilityEnvelope,
    ApplicabilityStatus,
    ApplicabilityVariable,
    BibliographicSource,
    CorrelationApplicabilityInput,
    CorrelationDefinition,
    CorrelationImplementationStatus,
    CorrelationKey,
    CorrelationPurpose,
    FlowRegime,
    GeometryType,
    NumericBound,
    OutOfRangeAction,
    OutOfRangePolicy,
    PhaseRegime,
    SourceVerificationStatus,
    UncertaintySpec,
    VariableApplicabilityStatus,
    VariableAssessment,
    compute_assessment_hash,
    compute_definition_hash,
    parse_semver,
)
from hexagent.correlations.registry import (
    CorrelationRegistry,
    InMemoryCorrelationRegistry,
)
from hexagent.correlations.usage import CorrelationUsageRecord

__all__ = [
    "ApplicabilityAssessment",
    "ApplicabilityEnvelope",
    "ApplicabilityStatus",
    "ApplicabilityVariable",
    "BibliographicSource",
    "CorrelationApplicabilityInput",
    "CorrelationDefinition",
    "CorrelationDuplicateError",
    "CorrelationError",
    "CorrelationHashMismatchError",
    "CorrelationImplementationStatus",
    "CorrelationKey",
    "CorrelationNotFoundError",
    "CorrelationPurpose",
    "CorrelationRegistry",
    "CorrelationUsageRecord",
    "CorrelationVersionNotFoundError",
    "FlowRegime",
    "GeometryType",
    "InMemoryCorrelationRegistry",
    "NumericBound",
    "OutOfRangeAction",
    "OutOfRangePolicy",
    "PhaseRegime",
    "SourceVerificationStatus",
    "UncertaintySpec",
    "VariableApplicabilityStatus",
    "VariableAssessment",
    "assess_applicability",
    "compute_assessment_hash",
    "compute_definition_hash",
    "parse_semver",
]
