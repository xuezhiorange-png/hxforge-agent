from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from hexagent.exchangers.shell_tube.shell_bundle_geometry import (
    DEFERRED_CAPABILITIES,
    BlockerCode,
    RuleAuthorityMode,
    ShellInsideDiameterAuthorityMode,
    WarningCode,
)

from ._builders import parsed_rule_snapshot, rule_payload


def test_closed_sets_have_frozen_sizes() -> None:
    assert len(BlockerCode) == 42
    assert len(WarningCode) == 10
    assert len(DEFERRED_CAPABILITIES) == 19
    assert tuple(RuleAuthorityMode) == (
        RuleAuthorityMode.INTERNAL_GENERIC,
        RuleAuthorityMode.APPROVED_RULE_PACK,
    )
    assert tuple(ShellInsideDiameterAuthorityMode) == (
        ShellInsideDiameterAuthorityMode.CALLER_SUPPLIED_EXPLICIT,
        ShellInsideDiameterAuthorityMode.APPROVED_CATALOG_SNAPSHOT,
    )


def test_rule_snapshot_is_immutable_and_detached() -> None:
    raw = rule_payload()
    license_evidence = raw["license_evidence"]
    snapshot = parsed_rule_snapshot(raw)
    license_evidence["standard_claim_status"] = "MUTATED"
    assert "MUTATED" not in repr(snapshot.license_evidence)
    with pytest.raises(FrozenInstanceError):
        snapshot.rule_id = "changed"  # type: ignore[misc]
