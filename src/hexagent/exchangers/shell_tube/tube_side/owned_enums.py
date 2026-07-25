"""TASK-025 owned enums and ReferencePlanePair value object.

§2.2 — TASK-025-owned enum classes:
    FlowPathMode, HydraulicAuthorityMode, ReferencePlaneToken.
§2.2.1 — Canonical UTF-8 byte encoding for every member.
§2.6 — ReferencePlaneToken closed set; ReferencePlanePair is a frozen
       value object with the exact two ordered pairs.
"""

from __future__ import annotations

import enum
from typing import Final

# §2.2.1 — Exact owned-enum public surface.


class FlowPathMode(enum.StrEnum):
    """§2.2.1 — FlowPathMode canonical set.

    Canonical UTF-8 lexeme bytes are deterministic. The two U-tube
    members exist for membership testing but are blocked by §5 / §13.
    """

    STRAIGHT_TUBE_PARALLEL_FLOW = "STRAIGHT_TUBE_PARALLEL_FLOW"
    STRAIGHT_TUBE_COUNTER_FLOW = "STRAIGHT_TUBE_COUNTER_FLOW"
    U_TUBE_PARALLEL_FLOW = "U_TUBE_PARALLEL_FLOW"
    U_TUBE_COUNTER_FLOW = "U_TUBE_COUNTER_FLOW"

    @property
    def canonical_utf8_bytes(self) -> bytes:
        return self.value.encode("ascii")


class HydraulicAuthorityMode(enum.StrEnum):
    """§2.2.1 — HydraulicAuthorityMode canonical set.

    Only ``INTERNAL_ARITHMETIC_FROM_LENGTH`` is accepted by v1.
    """

    INTERNAL_ARITHMETIC_FROM_LENGTH = "INTERNAL_ARITHMETIC_FROM_LENGTH"
    INTERNAL_ARITHMETIC_FROM_FROZEN_PAYLOAD = "INTERNAL_ARITHMETIC_FROM_FROZEN_PAYLOAD"
    APPROVED_RULE_PACK_FROZEN_PAYLOAD = "APPROVED_RULE_PACK_FROZEN_PAYLOAD"

    @property
    def canonical_utf8_bytes(self) -> bytes:
        return self.value.encode("ascii")


class ReferencePlaneToken(enum.StrEnum):
    """§2.2.1 / §2.6 — ReferencePlaneToken canonical set."""

    TUBE_INTERNAL_FLOW_START_PLANE = "TUBE_INTERNAL_FLOW_START_PLANE"
    TUBE_INTERNAL_FLOW_END_PLANE = "TUBE_INTERNAL_FLOW_END_PLANE"
    TUBE_HEAT_TRANSFER_START_PLANE = "TUBE_HEAT_TRANSFER_START_PLANE"
    TUBE_HEAT_TRANSFER_END_PLANE = "TUBE_HEAT_TRANSFER_END_PLANE"

    @property
    def canonical_utf8_bytes(self) -> bytes:
        return self.value.encode("ascii")


# §2.2 — ReferencePlanePair is a frozen value object, not an enum.
# §2.6 — Allowed ordered pairs are exactly two.

_INTERNAL_FLOW_PAIR: Final[tuple[ReferencePlaneToken, ReferencePlaneToken]] = (
    ReferencePlaneToken.TUBE_INTERNAL_FLOW_START_PLANE,
    ReferencePlaneToken.TUBE_INTERNAL_FLOW_END_PLANE,
)
_HEAT_TRANSFER_PAIR: Final[tuple[ReferencePlaneToken, ReferencePlaneToken]] = (
    ReferencePlaneToken.TUBE_HEAT_TRANSFER_START_PLANE,
    ReferencePlaneToken.TUBE_HEAT_TRANSFER_END_PLANE,
)
_ALLOWED_PAIRS: Final[frozenset[tuple[ReferencePlaneToken, ReferencePlaneToken]]] = frozenset(
    {_INTERNAL_FLOW_PAIR, _HEAT_TRANSFER_PAIR}
)


class ReferencePlanePair:
    """§2.2 — Frozen value object with exact fields ``(start, end)``.

    Allowed ordered pairs are exactly the internal-flow start/end and the
    heat-transfer start/end. Cross-pair, swapped, alias, case-variant,
    whitespace-variant, and unrecognized token inputs are rejected.
    """

    __slots__ = ("start", "end")

    def __init__(self, start: ReferencePlaneToken, end: ReferencePlaneToken) -> None:
        if not isinstance(start, ReferencePlaneToken):
            raise ValueError(
                f"ReferencePlanePair.start must be ReferencePlaneToken, got {type(start).__name__}"
            )
        if not isinstance(end, ReferencePlaneToken):
            raise ValueError(
                f"ReferencePlanePair.end must be ReferencePlaneToken, got {type(end).__name__}"
            )
        pair = (start, end)
        if pair not in _ALLOWED_PAIRS:
            raise ValueError(
                f"ReferencePlanePair {pair!r} is not one of the two "
                f"allowed ordered pairs (internal-flow / heat-transfer)"
            )
        self.start = start
        self.end = end

    @property
    def kind(self) -> str:
        if (self.start, self.end) == _INTERNAL_FLOW_PAIR:
            return "internal_flow"
        return "heat_transfer"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ReferencePlanePair):
            return NotImplemented
        return self.start == other.start and self.end == other.end

    def __hash__(self) -> int:
        return hash((self.start, self.end))

    def __repr__(self) -> str:  # pragma: no cover
        return f"ReferencePlanePair(start={self.start.name}, end={self.end.name})"


def canonical_internal_flow_pair() -> ReferencePlanePair:
    """§10.3 / §10.4 — Return the internal-flow start/end pair."""
    return ReferencePlanePair(*_INTERNAL_FLOW_PAIR)


def canonical_heat_transfer_pair() -> ReferencePlanePair:
    """§10.3 / §10.4 — Return the heat-transfer start/end pair."""
    return ReferencePlanePair(*_HEAT_TRANSFER_PAIR)


__all__ = [
    "FlowPathMode",
    "HydraulicAuthorityMode",
    "ReferencePlaneToken",
    "ReferencePlanePair",
    "canonical_internal_flow_pair",
    "canonical_heat_transfer_pair",
]