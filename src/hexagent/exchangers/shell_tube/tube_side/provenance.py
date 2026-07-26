"""TASK-025 frozen provenance and identity value objects.

§6.1 — FrozenRawProjection, FrozenIdentity, FrozenProvenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from hexagent.exchangers.shell_tube.tube_side.canonical import sha256_hex_from_framed_bytes

_HEX_DIGITS: frozenset[str] = frozenset("0123456789abcdef")


def _validate_hash_field(value: str, field_path: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field_path} must be a 64-character string")
    if any(c not in _HEX_DIGITS for c in value):
        raise ValueError(f"{field_path} must be lowercase hexadecimal")
    return value


@dataclass(frozen=True)
class FrozenRawProjection:
    """§6.1 — FrozenRawProjection: projection_kind + canonical_bytes_hex.

    canonical_bytes_hex is the lowercase even-length hex encoding of
    the already framed projection bytes.
    """

    projection_kind: str
    canonical_bytes_hex: str

    def __post_init__(self) -> None:
        if not isinstance(self.projection_kind, str) or not self.projection_kind:
            raise ValueError("FrozenRawProjection.projection_kind must be non-empty str")
        if not isinstance(self.canonical_bytes_hex, str):
            raise ValueError("FrozenRawProjection.canonical_bytes_hex must be str")
        if len(self.canonical_bytes_hex) == 0 or len(self.canonical_bytes_hex) % 2 != 0:
            raise ValueError("FrozenRawProjection.canonical_bytes_hex must have even length")
        if any(c not in "0123456789abcdef" for c in self.canonical_bytes_hex):
            raise ValueError("FrozenRawProjection.canonical_bytes_hex must be lowercase hex")


@dataclass(frozen=True)
class FrozenIdentity:
    """§6.1 — FrozenIdentity: identity_type + identity_id + identity_hash."""

    identity_type: str
    identity_id: str
    identity_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.identity_type, str) or not self.identity_type:
            raise ValueError("FrozenIdentity.identity_type must be non-empty str")
        if not isinstance(self.identity_id, str) or not self.identity_id:
            raise ValueError("FrozenIdentity.identity_id must be non-empty str")
        _validate_hash_field(self.identity_hash, "FrozenIdentity.identity_hash")


@dataclass(frozen=True)
class FrozenProvenance:
    """§6.1 — FrozenProvenance value object."""

    task_id: str
    design_contract_path: str
    implementation_software_version: str
    input_evidence_refs: tuple[str, ...]
    upstream_identity_hashes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, str) or not self.task_id:
            raise ValueError("FrozenProvenance.task_id must be non-empty str")
        if not isinstance(self.design_contract_path, str) or not self.design_contract_path:
            raise ValueError("FrozenProvenance.design_contract_path must be non-empty str")
        if not isinstance(self.implementation_software_version, str):
            raise ValueError("FrozenProvenance.implementation_software_version must be str")
        if not isinstance(self.input_evidence_refs, (tuple, list)):
            raise ValueError("FrozenProvenance.input_evidence_refs must be a tuple/list of str")
        items: list[str] = []
        for item in self.input_evidence_refs:
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "FrozenProvenance.input_evidence_refs entries must be non-empty str"
                )
            items.append(item)
        object.__setattr__(self, "input_evidence_refs", tuple(items))
        if not isinstance(self.upstream_identity_hashes, (tuple, list)):
            raise ValueError(
                "FrozenProvenance.upstream_identity_hashes must be a tuple/list of str"
            )
        hashes: list[str] = []
        for item in self.upstream_identity_hashes:
            _validate_hash_field(item, "FrozenProvenance.upstream_identity_hashes entry")
            hashes.append(item)
        object.__setattr__(self, "upstream_identity_hashes", tuple(hashes))


DESIGN_CONTRACT_PATH: Final[str] = (
    "docs/tasks/TASK-025-shell-and-tube-tube-side-hydraulic-geometry.md"
)
TASK_ID: Final[str] = "TASK-025"
IMPLEMENTATION_SOFTWARE_VERSION: Final[str] = "0.1.0"


__all__ = [
    "FrozenRawProjection",
    "FrozenIdentity",
    "FrozenProvenance",
    "DESIGN_CONTRACT_PATH",
    "TASK_ID",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "sha256_hex_from_framed_bytes",
]

# ruff: noqa: E501
