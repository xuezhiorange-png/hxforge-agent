"""Strict raw-boundary value projection for TASK-038."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenRawProjection:
    """A producer-preserved canonical byte child.

    TASK-038 never interprets these bytes.  The owning producer decides the
    projection; this value object only enforces the frozen lowercase-hex
    transport representation.
    """

    projection_kind: str
    canonical_bytes_hex: str

    def __post_init__(self) -> None:
        if type(self.projection_kind) is not str or not self.projection_kind:
            raise ValueError("projection_kind must be a non-empty str")
        if type(self.canonical_bytes_hex) is not str:
            raise ValueError("canonical_bytes_hex must be str")
        if len(self.canonical_bytes_hex) % 2:
            raise ValueError("canonical_bytes_hex must have even length")
        if any(char not in "0123456789abcdef" for char in self.canonical_bytes_hex):
            raise ValueError("canonical_bytes_hex must be lowercase hex")

    @property
    def child_bytes(self) -> bytes:
        return bytes.fromhex(self.canonical_bytes_hex)


def project_raw_value(value: bytes) -> bytes:
    """Return already-canonical producer bytes without reinterpretation."""

    if type(value) is not bytes:
        raise ValueError("raw projection input must be bytes")
    return value


__all__ = ["FrozenRawProjection", "project_raw_value"]
