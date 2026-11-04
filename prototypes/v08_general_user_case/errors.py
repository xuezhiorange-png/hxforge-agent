"""Structured validation errors for V08 user design cases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class V08ValidationCode(StrEnum):
    INVALID_INPUT = "INVALID_INPUT"
    OUT_OF_ENVELOPE = "OUT_OF_ENVELOPE"
    THERMODYNAMICALLY_INFEASIBLE = "THERMODYNAMICALLY_INFEASIBLE"
    PROPERTY_UNAVAILABLE = "PROPERTY_UNAVAILABLE"
    MODEL_BLOCKED = "MODEL_BLOCKED"
    AMBIGUOUS_INPUT = "AMBIGUOUS_INPUT"


@dataclass(frozen=True)
class V08ValidationIssue:
    code: V08ValidationCode
    field: str
    message: str
    context: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "field": self.field,
            "message": self.message,
            "context": self.context,
        }


class V08UserCaseValidationError(ValueError):
    """Fail-closed user-case validation with traceable issues."""

    def __init__(self, issues: tuple[V08ValidationIssue, ...]) -> None:
        self.issues = issues
        detail = "; ".join(f"{issue.code.value}: {issue.message}" for issue in issues)
        super().__init__(detail)

    def as_dict(self) -> dict[str, Any]:
        return {"issues": [issue.as_dict() for issue in self.issues]}
