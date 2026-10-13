"""Programmatic n=32 bracket (delegates to mesh extrapolation helper)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from hexagent.properties.base import PropertyProvider
from prototypes.v07_fast_solver_outer_boundary_r3.outer_boundary import OuterTrialReceipt
from prototypes.v07_fast_solver_verified_bracket.mesh_extrapolation_bracket import (
    BracketEstablishmentFailed,
    establish_verified_bracket,
    propose_search_bounds as propose_n32_search_bounds,
)

MAX_BRACKET_EXPANSIONS = 12

__all__ = [
    "BracketEstablishmentFailed",
    "MAX_BRACKET_EXPANSIONS",
    "establish_n32_verified_bracket",
    "propose_n32_search_bounds",
]


def establish_n32_verified_bracket(
    subdivisions: int,
    provider: PropertyProvider,
    shell_authority: Any,
    *,
    h8_j_kg: str,
    h16_j_kg: str,
    authority_id: str,
    rating_request_hash: str = "",
    run_session_id: str | None = None,
    deadline_monotonic: float | None = None,
    on_trial_receipt: Callable[[OuterTrialReceipt], None] | None = None,
) -> tuple[str, str, dict[str, Any]]:
    endpoints, meta = establish_verified_bracket(
        subdivisions,
        provider,
        shell_authority,
        h_coarse_j_kg=h8_j_kg,
        h_fine_j_kg=h16_j_kg,
        authority_id=authority_id,
        rating_request_hash=rating_request_hash,
        run_session_id=run_session_id,
        deadline_monotonic=deadline_monotonic,
        on_trial_receipt=on_trial_receipt,
    )
    meta["reusable_endpoints"] = endpoints.to_audit_dict()
    return endpoints.h_low_j_kg, endpoints.h_high_j_kg, meta
