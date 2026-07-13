from __future__ import annotations

from hexagent.exchangers.shell_tube.tube_layout.geometry import AcceptedCoordinate
from hexagent.exchangers.shell_tube.tube_layout.models import (
    LatticeIndex,
    UTubePair,
    UTubePairingPlan,
)
from hexagent.exchangers.shell_tube.tube_layout.pairing import (
    PairingFailure,
    compute_pairing_plan_hash,
    validate_pairing_plan,
)


def _accepted() -> tuple[AcceptedCoordinate, ...]:
    from decimal import Decimal

    return (
        AcceptedCoordinate(0, 0, Decimal(0), Decimal(0), "0", "0"),
        AcceptedCoordinate(1, 0, Decimal(1), Decimal(0), "1", "0"),
    )


def test_pairing_hash_is_input_order_independent() -> None:
    raw = UTubePairingPlan(
        schema_version="task021.u-tube-pairing.v1",
        pairs=(UTubePair("p", LatticeIndex(1, 0), LatticeIndex(0, 0), ("e",)),),
        evidence_refs=("plan",),
        pairing_plan_hash="0" * 64,
    )
    expected = compute_pairing_plan_hash(raw)
    plan = UTubePairingPlan(raw.schema_version, raw.pairs, raw.evidence_refs, expected)
    normalized, count = validate_pairing_plan(plan, _accepted())
    assert count == 1
    assert normalized.pairs[0].leg_a == LatticeIndex(0, 0)


def test_missing_and_reused_message_keys_are_disjoint() -> None:
    plan = UTubePairingPlan(
        schema_version="task021.u-tube-pairing.v1",
        pairs=(UTubePair("p", LatticeIndex(0, 0), LatticeIndex(0, 0), ()),),
        evidence_refs=("plan",),
        pairing_plan_hash="0" * 64,
    )
    try:
        validate_pairing_plan(plan, _accepted())
    except PairingFailure as exc:
        keys = {item.message_key for item in exc.blockers}
        assert "u_tube_pair_missing_coverage" in keys
        assert "u_tube_pair_leg_reused" in keys
        assert keys != {"u_tube_pair_missing_coverage"}
