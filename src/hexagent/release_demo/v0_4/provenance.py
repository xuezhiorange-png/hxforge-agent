"""TASK039 provenance graph and self-edge-free identity construction."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .canonical import (
    provenance_full_bytes,
    provenance_hash,
    provenance_prehash_bytes,
    sha256_bytes,
)
from .schema import (
    PROVENANCE_EDGES,
    PROVENANCE_FULL_FIELDS,
    PROVENANCE_HASH,
    PROVENANCE_PREHASH_FIELDS,
    SELF_EDGE_COUNT,
)

PRODUCER_EDGE_COUNT = len(PROVENANCE_EDGES)
PROVENANCE_PREHASH_FIELD_COUNT = len(PROVENANCE_PREHASH_FIELDS)
PROVENANCE_FIELD_COUNT = len(PROVENANCE_FULL_FIELDS)


def producer_edges() -> tuple[str, ...]:
    return tuple(f"{source}->{target}:{field}" for source, target, field in PROVENANCE_EDGES)


def build_provenance(values: Mapping[str, Any]) -> dict[str, Any]:
    """Build the complete 23-field record from the 22 parent fields.

    The returned ``provenance_hash`` is appended once and is never included
    in its own prehash.  This makes the provenance node acyclic and permits
    exact replay by ``verify_provenance``.
    """

    record = {field: values[field] for field in PROVENANCE_PREHASH_FIELDS}
    record["provenance_hash"] = provenance_hash(record)
    return record


def build_provenance_prehash(values: Mapping[str, Any]) -> dict[str, Any]:
    return {field: values[field] for field in PROVENANCE_PREHASH_FIELDS}


def provenance_to_fields(record: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple((field, record[field]) for field in PROVENANCE_FULL_FIELDS)


def verify_provenance(record: Any) -> bool:
    if not isinstance(record, Mapping):
        return False
    if tuple(record.keys()) != PROVENANCE_FULL_FIELDS:
        return False
    try:
        return (
            provenance_hash(record) == record["provenance_hash"]
            and len(producer_edges()) == 13
            and SELF_EDGE_COUNT == 0
            and all(source != target for source, target, _ in PROVENANCE_EDGES)
        )
    except Exception:
        return False


def provenance_oracle_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    prehash = build_provenance_prehash(record)
    full = dict(record)
    return {
        "prehash_bytes": len(provenance_prehash_bytes(prehash)),
        "prehash_hash": provenance_hash(prehash),
        "full_bytes": len(provenance_full_bytes(full)),
        "full_sha256": sha256_bytes(provenance_full_bytes(full)),
        "design_prehash_bytes": 2459,
        "design_prehash_hash": PROVENANCE_HASH,
    }


__all__ = [
    "PRODUCER_EDGE_COUNT",
    "PROVENANCE_FIELD_COUNT",
    "PROVENANCE_PREHASH_FIELD_COUNT",
    "SELF_EDGE_COUNT",
    "build_provenance",
    "build_provenance_prehash",
    "producer_edges",
    "provenance_oracle_summary",
    "provenance_to_fields",
    "verify_provenance",
]
