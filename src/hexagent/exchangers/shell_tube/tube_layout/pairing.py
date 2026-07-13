"""Canonical U-tube pairing validation and hashing."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from .canonical import sha256_hex
from .geometry import AcceptedCoordinate
from .models import (
    PAIRING_SCHEMA_VERSION,
    BlockerCode,
    LatticeIndex,
    MessageEntry,
    UTubePair,
    UTubePairingPlan,
)


class PairingFailure(ValueError):
    def __init__(self, *blockers: MessageEntry) -> None:
        super().__init__(blockers[0].message_key if blockers else "pairing_failure")
        self.blockers = blockers


def _block(
    message_key: str, *, field_path: str = "u_tube_pairing_plan"
) -> MessageEntry:
    return MessageEntry(
        code=BlockerCode.STL_UTUBE_PAIRING_INVALID.value,
        field_path=field_path,
        message_key=message_key,
    )


def canonical_pair(pair: UTubePair) -> UTubePair:
    first, second = sorted((pair.leg_a, pair.leg_b))
    return UTubePair(
        pair_id=pair.pair_id,
        leg_a=first,
        leg_b=second,
        evidence_refs=tuple(sorted(pair.evidence_refs)),
    )


def canonical_pairs(plan: UTubePairingPlan) -> tuple[UTubePair, ...]:
    normalized = [canonical_pair(pair) for pair in plan.pairs]
    normalized.sort(
        key=lambda pair: (
            pair.leg_a.u,
            pair.leg_a.v,
            pair.leg_b.u,
            pair.leg_b.v,
            pair.pair_id,
        )
    )
    return tuple(normalized)


def pairing_plan_payload(plan: UTubePairingPlan) -> Mapping[str, Any]:
    return {
        "schema_version": PAIRING_SCHEMA_VERSION,
        "pairs": [
            {
                "pair_id": pair.pair_id,
                "leg_a": {"u": pair.leg_a.u, "v": pair.leg_a.v},
                "leg_b": {"u": pair.leg_b.u, "v": pair.leg_b.v},
                "evidence_refs": list(pair.evidence_refs),
            }
            for pair in canonical_pairs(plan)
        ],
        "plan_evidence_refs": list(sorted(plan.evidence_refs)),
    }


def compute_pairing_plan_hash(plan: UTubePairingPlan) -> str:
    return sha256_hex(pairing_plan_payload(plan))


def validate_pairing_plan(
    plan: UTubePairingPlan,
    accepted: tuple[AcceptedCoordinate, ...],
) -> tuple[UTubePairingPlan, int]:
    blockers: list[MessageEntry] = []
    pair_ids = [pair.pair_id for pair in plan.pairs]
    if len(set(pair_ids)) != len(pair_ids):
        blockers.append(
            _block("u_tube_pair_duplicate_id", field_path="u_tube_pairing_plan.pairs")
        )
    normalized = canonical_pairs(plan)
    for pair in normalized:
        if pair.leg_a == pair.leg_b:
            blockers.append(
                _block(
                    "u_tube_pair_self",
                    field_path=f"u_tube_pairing_plan.pairs.{pair.pair_id}",
                )
            )
    accepted_indices = {LatticeIndex(item.u, item.v) for item in accepted}
    referenced: list[LatticeIndex] = []
    for pair in normalized:
        for leg in (pair.leg_a, pair.leg_b):
            if leg not in accepted_indices:
                blockers.append(
                    _block(
                        "u_tube_pair_unknown_leg",
                        field_path=f"u_tube_pairing_plan.pairs.{pair.pair_id}",
                    )
                )
            referenced.append(leg)
    counts = Counter(referenced)
    for leg in sorted(accepted_indices):
        count = counts[leg]
        if count > 1:
            blockers.append(
                _block(
                    "u_tube_pair_leg_reused",
                    field_path=f"u_tube_pairing_plan.leg[{leg.u},{leg.v}]",
                )
            )
        elif count == 0:
            blockers.append(
                _block(
                    "u_tube_pair_missing_coverage",
                    field_path=f"u_tube_pairing_plan.leg[{leg.u},{leg.v}]",
                )
            )
    if blockers:
        raise PairingFailure(*blockers)
    normalized_plan = UTubePairingPlan(
        schema_version=PAIRING_SCHEMA_VERSION,
        pairs=normalized,
        evidence_refs=tuple(sorted(plan.evidence_refs)),
        pairing_plan_hash=plan.pairing_plan_hash,
    )
    expected_hash = compute_pairing_plan_hash(normalized_plan)
    if expected_hash != plan.pairing_plan_hash:
        raise PairingFailure(
            MessageEntry(
                code=BlockerCode.STL_UTUBE_PAIRING_HASH_MISMATCH.value,
                field_path="u_tube_pairing_plan.pairing_plan_hash",
                message_key="u_tube_pairing_hash_mismatch",
                evidence_refs=normalized_plan.evidence_refs,
                details={"expected_hash": expected_hash},
            )
        )
    return normalized_plan, len(normalized)


__all__ = [
    "PairingFailure",
    "canonical_pair",
    "canonical_pairs",
    "compute_pairing_plan_hash",
    "pairing_plan_payload",
    "validate_pairing_plan",
]
