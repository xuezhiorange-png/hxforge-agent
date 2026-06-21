from __future__ import annotations

from enum import StrEnum


class PropertyErrorCode(StrEnum):
    INVALID_FLUID = "property_invalid_fluid"
    UNVALIDATED_FLUID = "property_unvalidated_fluid"
    INVALID_INPUT = "property_invalid_input"
    STATE_OUT_OF_RANGE = "property_state_out_of_range"
    NEAR_SATURATION = "property_near_saturation"
    TWO_PHASE_STATE = "property_two_phase_state"
    SATURATION_UNAVAILABLE = "property_saturation_unavailable"
    UNSUPPORTED_BACKEND = "property_unsupported_backend"
    UNSUPPORTED_QUERY = "property_unsupported_query"
    BACKEND_FAILURE = "property_backend_failure"
    NON_FINITE_RESULT = "property_non_finite_result"
    CONFIGURATION_CHANGED = "property_configuration_changed"


class PropertyServiceError(ValueError):
    """Structured property-service failure suitable for API serialization."""

    def __init__(
        self,
        code: PropertyErrorCode,
        message: str,
        *,
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.context = context or {}

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code.value,
            "message": str(self),
            "context": self.context,
        }
