"""Typed errors for rule-pack validation.

All rule-pack validation failures raise ``RulePackValidationError`` so callers
can branch on a single exception type. Generic failures (IO, JSON decode) are
wrapped with ``RulePackError``.
"""

from __future__ import annotations


class RulePackError(Exception):
    """Base class for rule-pack runtime errors."""


class RulePackValidationError(RulePackError):
    """Raised when a rule-pack artifact, manifest, or provenance graph fails
    validation against the TASK-012 frozen design contract.

    The ``path`` attribute identifies the artifact or field path that failed,
    enabling machine-readable error reports.
    """

    def __init__(self, message: str, *, path: str = "") -> None:
        super().__init__(message)
        self.path = path
