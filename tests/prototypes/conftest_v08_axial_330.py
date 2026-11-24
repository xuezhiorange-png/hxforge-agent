"""Session-scoped FIXTURE_330 structural prep for axial / 330 kW engine tests."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CandidateRatingBindings,
    build_candidate_rating_bindings,
    enumerate_structural_bundles,
    load_case_bindings,
    solve_isolated_outer_boundary,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.outer_shooting_isolated_v1 import IsolatedOuterBoundaryResult


@dataclass(frozen=True, slots=True)
class Fixture330EngineContext:
    normalized: NormalizedUserDesignCase
    handoff: V08SolverHandoffV1
    provider: CoolPropProvider
    space_hash: str
    t168_digest: str
    bindings: CandidateRatingBindings
    n1: IsolatedOuterBoundaryResult


@pytest.fixture(scope="session")
def fixture_330_engine_context() -> Fixture330EngineContext:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    space_hash, t168_digest, bundles, geom = enumerate_structural_bundles(
        normalized, handoff, max_valid=1
    )
    bindings = build_candidate_rating_bindings(
        bundles[0],
        space_hash=space_hash,
        t168_digest=t168_digest,
        normalized=normalized,
        handoff=handoff,
        provider=provider,
        geometry_projection_hash=geom[bundles[0].candidate.candidate_id],
    )
    assert bindings is not None
    n1 = solve_isolated_outer_boundary(bindings, provider, subdivisions=1)
    return Fixture330EngineContext(
        normalized=normalized,
        handoff=handoff,
        provider=provider,
        space_hash=space_hash,
        t168_digest=t168_digest,
        bindings=bindings,
        n1=n1,
    )
