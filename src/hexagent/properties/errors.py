from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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


# Item 4: strict versioned error model for API serialization
class PropertyServiceErrorModel(BaseModel):
    """Strict versioned Pydantic model for property service errors.

    ``extra="forbid"`` ensures no unknown fields leak through.
    ``code`` uses the stable ``PropertyErrorCode`` enum, not free text.
    ``schema_version`` is a ``Literal["1.0"]`` — any other value is
    rejected at validation time.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    code: PropertyErrorCode
    message: str
    context: dict[str, object] = Field(default_factory=dict)


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

    def to_model(self) -> PropertyServiceErrorModel:
        """Serialize to a strict Pydantic model."""
        return PropertyServiceErrorModel(
            code=self.code,
            message=str(self),
            context=self.context,
        )

    def to_json(self) -> str:
        """Serialize to deterministic JSON."""
        return self.to_model().model_dump_json()

    @classmethod
    def from_model(cls, model: PropertyServiceErrorModel) -> PropertyServiceError:
        """Reconstruct from a Pydantic model."""
        return cls(
            code=model.code,
            message=model.message,
            context=dict(model.context),
        )

    @classmethod
    def from_json(cls, raw: str) -> PropertyServiceError:
        """Reconstruct from JSON string."""
        model = PropertyServiceErrorModel.model_validate_json(raw)
        return cls.from_model(model)
