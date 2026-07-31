"""TASK-026 raw projection.

R8 implementation. The raw projection is the byte form of the raw
input to S00. It is decoded from the snapshot_to_raw round-trip after
S00 has identified the input as a known shape. The raw projection
package is a KIND_RAW_PROJECTION-framed value (R6-R7 §9.5.1).

Per R6-R7 §9.5.1 the byte closure is:

  raw_projection_child_bytes = project_raw_value(value)
  record_field_payload      = raw_projection_child_bytes
  record_field_bytes        = frame_value(KIND_RAW_PROJECTION, record_field_payload)

The projection is called exactly once per field; frame_record applies
exactly one field-level KIND_RAW_PROJECTION frame. There is no
projection re-entry and no second frame.

For absent optional projections (R6-R7 §9.5 / H1-R1 addendum):
  kind    = KIND_NONE
  payload = b""

This module is a pure value-object holder plus the closure rule above;
the projection of a concrete raw value is encoded by project_raw_value,
which is a simple identifier-based passthrough for the R8 raw envelope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from hexagent.exchangers.shell_tube.tube_side_thermal.canonical import (
    ABSENT_OPTIONAL_KIND,
    ABSENT_OPTIONAL_PAYLOAD,
    KIND_RAW_PROJECTION,
    frame_value,
)

RAW_PROJECTION_NAMESPACE: Final[str] = "task026.raw-projection.v1"


@dataclass(frozen=True)
class FrozenRawProjection:
    """R6-R7 §9.5.1 — Frozen raw projection.

    The canonical_bytes_hex is the lowercase even-length hex encoding
    of the projected bytes (already framed once at the field boundary).
    """

    projection_kind: str
    canonical_bytes_hex: str

    def __post_init__(self) -> None:
        if not isinstance(self.projection_kind, str) or not self.projection_kind:
            raise ValueError("projection_kind must be non-empty str")
        if not isinstance(self.canonical_bytes_hex, str):
            raise ValueError("canonical_bytes_hex must be str")
        # Empty hex string represents absent optional projection (R6-R7 §9.5).
        if len(self.canonical_bytes_hex) % 2 != 0:
            raise ValueError("canonical_bytes_hex must have even length")
        if any(c not in "0123456789abcdef" for c in self.canonical_bytes_hex):
            raise ValueError("canonical_bytes_hex must be lowercase hex")


def project_raw_value(value: bytes) -> bytes:
    """R6-R7 §9.5.1 — Single-call projection.

    The raw value is already the canonical child bytes (passed in
    as bytes). No re-projection is performed.
    """
    if not isinstance(value, bytes):
        raise ValueError("project_raw_value input must be bytes")
    return value


def frame_raw_projection_field(child_bytes: bytes) -> bytes:
    """R6-R7 §9.5.1 — frame_value at the field boundary.

    Applies KIND_RAW_PROJECTION exactly once. The child_bytes are
    already internally framed.
    """
    return frame_value(KIND_RAW_PROJECTION, child_bytes)


def zero_optional() -> bytes:
    """R6-R7 §9.5 — absent optional projection: KIND_NONE + empty payload."""
    return frame_value(ABSENT_OPTIONAL_KIND, ABSENT_OPTIONAL_PAYLOAD)


__all__ = [
    "RAW_PROJECTION_NAMESPACE",
    "FrozenRawProjection",
    "project_raw_value",
    "frame_raw_projection_field",
    "zero_optional",
]
