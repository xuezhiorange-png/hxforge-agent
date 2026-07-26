"""TASK-025 hydraulic participation authority.

§5.4 — Task025HydraulicParticipationAuthority.
§9.4 — Ten participation invariants.
§10.5 — hydraulic_authority_hash node.
"""

from __future__ import annotations

from dataclasses import dataclass

from hexagent.exchangers.shell_tube.tube_side.owned_enums import HydraulicAuthorityMode

_HEX_DIGITS: frozenset[str] = frozenset("0123456789abcdef")


def _validate_hash_field(value: str, field_path: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field_path} must be a 64-character string")
    if any(c not in _HEX_DIGITS for c in value):
        raise ValueError(f"{field_path} must be lowercase hexadecimal")
    return value


def _validate_non_empty_string_tuple(
    value: tuple[str, ...] | list[str], field_path: str
) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{field_path} must be a tuple/list of str")
    items = tuple(value)
    for item in items:
        if not isinstance(item, str) or not item:
            raise ValueError(f"{field_path} entries must be non-empty str")
    return items


@dataclass(frozen=True)
class Task025HydraulicParticipationAuthority:
    """§5.4 — TASK-025 hydraulic participation authority."""

    all_layout_position_ids: tuple[str, ...]
    active_position_ids: tuple[str, ...]
    inactive_position_ids: tuple[str, ...]
    authority_mode: HydraulicAuthorityMode
    evidence_refs: tuple[str, ...]
    hydraulic_authority_hash: str

    def __post_init__(self) -> None:
        self._validate_all_layout_position_ids()
        self._validate_active_position_ids()
        self._validate_inactive_position_ids()
        if not isinstance(self.authority_mode, HydraulicAuthorityMode):
            raise ValueError(
                "hydraulic_participation_authority.authority_mode must be "
                f"HydraulicAuthorityMode; got {type(self.authority_mode).__name__}"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_non_empty_string_tuple(
                self.evidence_refs,
                "hydraulic_participation_authority.evidence_refs",
            ),
        )
        _validate_hash_field(
            self.hydraulic_authority_hash,
            "hydraulic_participation_authority.hydraulic_authority_hash",
        )

    def _validate_all_layout_position_ids(self) -> None:
        _validate_non_empty_string_tuple(
            self.all_layout_position_ids,
            "hydraulic_participation_authority.all_layout_position_ids",
        )

    def _validate_active_position_ids(self) -> None:
        _validate_non_empty_string_tuple(
            self.active_position_ids,
            "hydraulic_participation_authority.active_position_ids",
        )

    def _validate_inactive_position_ids(self) -> None:
        _validate_non_empty_string_tuple(
            self.inactive_position_ids,
            "hydraulic_participation_authority.inactive_position_ids",
        )


__all__ = ["Task025HydraulicParticipationAuthority"]
