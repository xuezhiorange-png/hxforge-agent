"""Raw-boundary projection for TASK-032."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    canonical_json,
    canonical_raw_json_or_none,
)

RAW_PROJECTION_NAMESPACE = "task032.raw-projection.v1"


@dataclass(frozen=True)
class FrozenRawProjection:
    """Stable representation of the raw input available at S00/S01."""

    projection_kind: str
    canonical_bytes_hex: str

    def __post_init__(self) -> None:
        if type(self.projection_kind) is not str or not self.projection_kind:
            raise ValueError("projection_kind must be a non-empty string")
        if type(self.canonical_bytes_hex) is not str:
            raise ValueError("canonical_bytes_hex must be a string")
        if len(self.canonical_bytes_hex) % 2:
            raise ValueError("canonical_bytes_hex must have even length")
        if any(char not in "0123456789abcdef" for char in self.canonical_bytes_hex):
            raise ValueError("canonical_bytes_hex must be lowercase hexadecimal")


def project_raw_request(raw_request: Any) -> FrozenRawProjection:
    """Project canonicalizable raw input once, without coercion."""

    primitive = canonical_raw_json_or_none(raw_request)
    if primitive is None:
        return FrozenRawProjection("NONE", "")
    encoded = canonical_json(primitive).encode("utf-8")
    return FrozenRawProjection("RAW_REQUEST", encoded.hex())


def projection_primitive(projection: FrozenRawProjection) -> list[str]:
    return [projection.projection_kind, projection.canonical_bytes_hex]


__all__ = [
    "FrozenRawProjection",
    "RAW_PROJECTION_NAMESPACE",
    "project_raw_request",
    "projection_primitive",
]
