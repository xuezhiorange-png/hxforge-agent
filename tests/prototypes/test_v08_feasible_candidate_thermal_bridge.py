"""Hydraulic-feasible candidates must be selected before thermal closeout."""

from __future__ import annotations

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CASE_330KW_ID,
    load_case_bindings,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.feasible_candidate_thermal_bridge_v08 import (
    _inventory_counts,
)
from prototypes.v08_thermal_rating.hydraulic_feasibility_v08 import screen_task174_hydraulic_row


def test_first_enumerated_differs_from_hydraulic_feasible_selection() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    assert normalized.engineering_case_id == CASE_330KW_ID
    inventory, bindings_by_id = _inventory_counts(
        normalized, handoff, provider=provider, max_candidates=64
    )
    assert inventory.manufacturable_valid_count >= 2
    ordered_ids = list(bindings_by_id.keys())
    first_row = screen_task174_hydraulic_row(bindings_by_id[ordered_ids[0]])
    assert first_row.shell_dp_pass is False
    feasible_ids = [
        cid for cid, b in bindings_by_id.items() if screen_task174_hydraulic_row(b).hydraulic_pass
    ]
    assert inventory.hydraulic_feasible_count == len(feasible_ids)
    assert len(feasible_ids) >= 1
    assert feasible_ids[0] != ordered_ids[0]
