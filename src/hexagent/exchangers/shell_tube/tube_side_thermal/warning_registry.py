"""TASK-026 warning registry.

R8 implementation. The warning registry is empty in v1 per R6-R7
§13.4: TASK026_WARNING_CODE_COUNT = 0. The 4-field Kind tag tuple
(R6-R7 §9.6.3) is presented for completeness but no warning code is
defined.
"""

from __future__ import annotations

from dataclasses import dataclass

TASK026_WARNING_CODE_COUNT: int = 0

TASK026_WARNING_REGISTRY: tuple[str, ...] = ()

# R6-R7 §9.6.3 — exactly 4 fields for the warning entry hash.
WARNING_ENTRY_HASH_FIELDS: tuple[str, ...] = (
    "code",
    "severity",
    "stage",
    "message",
)


@dataclass(frozen=True)
class WarningEntry:
    """R6-R7 §9.6.3 — Warning entry (not used in v1)."""

    code: str
    severity: str
    stage: str
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code:
            raise ValueError("code must be non-empty str")
        if not isinstance(self.severity, str) or not self.severity:
            raise ValueError("severity must be non-empty str")
        if not isinstance(self.stage, str) or not self.stage:
            raise ValueError("stage must be non-empty str")
        if not isinstance(self.message, str) or not self.message:
            raise ValueError("message must be non-empty str")


__all__ = [
    "TASK026_WARNING_CODE_COUNT",
    "TASK026_WARNING_REGISTRY",
    "WARNING_ENTRY_HASH_FIELDS",
    "WarningEntry",
]
