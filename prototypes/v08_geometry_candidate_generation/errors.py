"""Structured errors for V08-02 geometry generation."""

from __future__ import annotations


class V08GeometryGenerationBlocked(Exception):
    """Structured block; carries audit codes in evidence."""

    code: str
    message: str
    evidence: dict[str, str]

    def __init__(self, code: str, message: str, evidence: dict[str, str]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.evidence = evidence
