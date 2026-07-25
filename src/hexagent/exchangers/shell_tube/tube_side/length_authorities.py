"""TASK-025 dual length authorities.

§5.3 — InternalFlowLengthAuthority and HeatTransferLengthAuthority.
§10.3 / §10.4 — Each length authority has its own hash node.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side.decimal_identity import (
    validate_positive_finite_decimal,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    HydraulicAuthorityMode,
    ReferencePlanePair,
)

_HEX_DIGITS: frozenset[str] = frozenset("0123456789abcdef")


def _validate_hash_field(value: str, field_path: str) -> str:
    """Validate that ``value`` is a 64-lowercase-hex SHA-256 string."""
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field_path} must be a 64-character string")
    if any(c not in _HEX_DIGITS for c in value):
        raise ValueError(f"{field_path} must be lowercase hexadecimal")
    return value


def _validate_length_id(value: str, field_path: str) -> str:
    """Validate that ``value`` is a non-empty str."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_path} must be a non-empty str")
    return value


def _validate_reference_plane_pair_for_kind(
    pair: ReferencePlanePair, kind: str, field_path: str
) -> ReferencePlanePair:
    """Validate that ``pair.kind`` matches the expected length kind."""
    if pair.kind != kind:
        raise ValueError(
            f"{field_path} has ReferencePlanePair.kind={pair.kind!r}, "
            f"expected {kind!r}"
        )
    return pair


@dataclass(frozen=True)
class InternalFlowLengthAuthority:
    """§5.3 — Internal flow length authority.

    Fields:
      length_id (str): caller-supplied identity label.
      length_m (Decimal): finite, strictly positive metre value.
      start_plane / end_plane: exact internal-flow start/end pair.
      authority_mode (HydraulicAuthorityMode): v1 accepted mode.
      length_hash (str): 64-lowercase-hex SHA-256 from §10.3.
    """

    length_id: str
    length_m: Decimal
    start_plane: ReferencePlanePair
    end_plane: ReferencePlanePair
    authority_mode: HydraulicAuthorityMode
    length_hash: str

    def __post_init__(self) -> None:
        _validate_length_id(self.length_id, "internal_flow_authority.length_id")
        validate_positive_finite_decimal(self.length_m, "internal_flow_authority.length_m")
        _validate_reference_plane_pair_for_kind(
            self.start_plane, "internal_flow", "internal_flow_authority.start_plane"
        )
        _validate_reference_plane_pair_for_kind(
            self.end_plane, "internal_flow", "internal_flow_authority.end_plane"
        )
        if self.authority_mode is not HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH:
            raise ValueError(
                f"internal_flow_authority.authority_mode must be "
                f"INTERNAL_ARITHMETIC_FROM_LENGTH; got {self.authority_mode!r}"
            )
        _validate_hash_field(self.length_hash, "internal_flow_authority.length_hash")


@dataclass(frozen=True)
class HeatTransferLengthAuthority:
    """§5.3 — Heat-transfer length authority."""

    length_id: str
    length_m: Decimal
    start_plane: ReferencePlanePair
    end_plane: ReferencePlanePair
    authority_mode: HydraulicAuthorityMode
    length_hash: str

    def __post_init__(self) -> None:
        _validate_length_id(self.length_id, "heat_transfer_authority.length_id")
        validate_positive_finite_decimal(self.length_m, "heat_transfer_authority.length_m")
        _validate_reference_plane_pair_for_kind(
            self.start_plane, "heat_transfer", "heat_transfer_authority.start_plane"
        )
        _validate_reference_plane_pair_for_kind(
            self.end_plane, "heat_transfer", "heat_transfer_authority.end_plane"
        )
        if self.authority_mode is not HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH:
            raise ValueError(
                f"heat_transfer_authority.authority_mode must be "
                f"INTERNAL_ARITHMETIC_FROM_LENGTH; got {self.authority_mode!r}"
            )
        _validate_hash_field(self.length_hash, "heat_transfer_authority.length_hash")


__all__ = [
    "InternalFlowLengthAuthority",
    "HeatTransferLengthAuthority",
]