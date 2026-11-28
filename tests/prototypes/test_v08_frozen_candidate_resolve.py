"""Frozen HXFORGE_330KW_STRICT_DP candidate identity."""

from __future__ import annotations

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CASE_330KW_ID,
    load_case_bindings,
    resolve_candidate_bindings_by_id,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330

FROZEN_ID = "9277ebb8-5b05-5130-8b90-92ee4768606b"
FROZEN_HASH = "1d5cfed590c20aacb2224df020fd7fc88866c551b9ac6d813812d40b9a0a874f"


def test_resolve_frozen_hydraulic_feasible_candidate() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    assert normalized.engineering_case_id == CASE_330KW_ID
    bindings = resolve_candidate_bindings_by_id(
        FROZEN_ID, normalized, handoff, provider, max_valid=64
    )
    assert bindings is not None
    assert bindings.rating_request.candidate_id == FROZEN_ID
    assert bindings.geometry_projection_hash == FROZEN_HASH
