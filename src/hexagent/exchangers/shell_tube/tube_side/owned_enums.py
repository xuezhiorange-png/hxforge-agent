"""TASK-025 owned enums and immutable ReferencePlanePair value object."""

from __future__ import annotations

import enum
from typing import Final


class FlowPathMode(enum.StrEnum):
    STRAIGHT_TUBE_PARALLEL_FLOW = "STRAIGHT_TUBE_PARALLEL_FLOW"
    STRAIGHT_TUBE_COUNTER_FLOW = "STRAIGHT_TUBE_COUNTER_FLOW"
    U_TUBE_PARALLEL_FLOW = "U_TUBE_PARALLEL_FLOW"
    U_TUBE_COUNTER_FLOW = "U_TUBE_COUNTER_FLOW"

    @property
    def canonical_utf8_bytes(self) -> bytes:
        return self.value.encode("ascii")


class HydraulicAuthorityMode(enum.StrEnum):
    INTERNAL_ARITHMETIC_FROM_LENGTH = "INTERNAL_ARITHMETIC_FROM_LENGTH"
    INTERNAL_ARITHMETIC_FROM_FROZEN_PAYLOAD = "INTERNAL_ARITHMETIC_FROM_FROZEN_PAYLOAD"
    APPROVED_RULE_PACK_FROZEN_PAYLOAD = "APPROVED_RULE_PACK_FROZEN_PAYLOAD"

    @property
    def canonical_utf8_bytes(self) -> bytes:
        return self.value.encode("ascii")


class ReferencePlaneToken(enum.StrEnum):
    TUBE_INTERNAL_FLOW_START_PLANE = "TUBE_INTERNAL_FLOW_START_PLANE"
    TUBE_INTERNAL_FLOW_END_PLANE = "TUBE_INTERNAL_FLOW_END_PLANE"
    TUBE_HEAT_TRANSFER_START_PLANE = "TUBE_HEAT_TRANSFER_START_PLANE"
    TUBE_HEAT_TRANSFER_END_PLANE = "TUBE_HEAT_TRANSFER_END_PLANE"

    @property
    def canonical_utf8_bytes(self) -> bytes:
        return self.value.encode("ascii")


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
    """Immutable value object with exactly one of two ordered token pairs."""

    _start: ReferencePlaneToken
    _end: ReferencePlaneToken
    __slots__ = ("_start", "_end")

    def __init__(self, start: ReferencePlaneToken, end: ReferencePlaneToken) -> None:
        if type(start) is not ReferencePlaneToken:
            raise ValueError(
                f"ReferencePlanePair.start must be ReferencePlaneToken, got {type(start).__name__}"
            )
        if type(end) is not ReferencePlaneToken:
            raise ValueError(
                f"ReferencePlanePair.end must be ReferencePlaneToken, got {type(end).__name__}"
            )
        pair = (start, end)
        if pair not in _ALLOWED_PAIRS:
            raise ValueError(f"ReferencePlanePair {pair!r} is not an allowed ordered pair")
        object.__setattr__(self, "_start", start)
        object.__setattr__(self, "_end", end)

    @property
    def start(self) -> ReferencePlaneToken:
        return self._start

    @property
    def end(self) -> ReferencePlaneToken:
        return self._end

    @property
    def kind(self) -> str:
        if (self._start, self._end) == _INTERNAL_FLOW_PAIR:
            return "internal_flow"
        return "heat_transfer"

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("ReferencePlanePair is immutable")

    def __eq__(self, other: object) -> bool:
        if type(other) is not ReferencePlanePair:
            return NotImplemented
        return self._start == other._start and self._end == other._end

    def __hash__(self) -> int:
        return hash((self._start, self._end))

    def __repr__(self) -> str:  # pragma: no cover
        return f"ReferencePlanePair(start={self._start.name}, end={self._end.name})"


def canonical_internal_flow_pair() -> ReferencePlanePair:
    return ReferencePlanePair(*_INTERNAL_FLOW_PAIR)


def canonical_heat_transfer_pair() -> ReferencePlanePair:
    return ReferencePlanePair(*_HEAT_TRANSFER_PAIR)


__all__ = [
    "FlowPathMode",
    "HydraulicAuthorityMode",
    "ReferencePlaneToken",
    "ReferencePlanePair",
    "canonical_internal_flow_pair",
    "canonical_heat_transfer_pair",
]
