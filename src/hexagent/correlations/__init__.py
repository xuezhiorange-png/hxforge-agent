"""Correlation registry and applicability engine."""

from __future__ import annotations

from hexagent.correlations.applicability import assess_applicability
from hexagent.correlations.errors import (
    CorrelationDuplicateError,
    CorrelationError,
    CorrelationErrorCode,
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
    "CorrelationErrorCode",
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
]
