"""Structured errors for V08-02 geometry generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class V08GeometryGenerationBlocked:
    code: str
    message: str
    evidence: dict[str, str]
