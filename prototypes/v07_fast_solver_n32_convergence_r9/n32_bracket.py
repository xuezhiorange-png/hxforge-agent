"""Programmatic n=32 bracket proposal and bounded establishment."""

from __future__ import annotations

import time
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    H_MAX_J_KG,
    H_MIN_J_KG,
)
from hexagent.properties.base import PropertyProvider
from prototypes.v07_fast_solver_outer_boundary_r3.outer_boundary import (
    FastOuterBoundaryStats,
    OuterTrialReceipt,
    _classify_fast_trial,
)

MAX_BRACKET_EXPANSIONS = 12


class BracketEstablishmentFailed(Exception):
    """Could not find LOW/VALID bracket within bounded expansions."""


def propose_n32_search_bounds(h8_j_kg: str, h16_j_kg: str) -> dict[str, str]:
    h8 = Decimal(h8_j_kg)
    h16 = Decimal(h16_j_kg)
    delta = h16 - h8
    h_center = h16 + delta
    span = abs(delta) * Decimal("4")
    if span < Decimal("1e-6"):
        span = Decimal("1e-4")
    h_low = max(H_MIN_J_KG, h_center - span)
    h_high = min(H_MAX_J_KG, h_center + span)
    if h_low >= h_high:
        raise ValueError("degenerate n=32 proposal")
    return {
        "h8_j_kg": h8_j_kg,
        "h16_j_kg": h16_j_kg,
        "mesh_delta_h16_minus_h8": str(delta),
        "extrapolated_h32_center": str(h_center),
        "initial_span": str(span),
        "proposed_low_j_kg": str(h_low),
        "proposed_high_j_kg": str(h_high),
    }


def establish_n32_verified_bracket(
    subdivisions: int,
    provider: PropertyProvider,
    shell_authority: Any,
    *,
    h8_j_kg: str,
    h16_j_kg: str,
    authority_id: str,
    deadline_monotonic: float | None = None,
    on_trial_receipt: Callable[[OuterTrialReceipt], None] | None = None,
) -> tuple[str, str, dict[str, Any]]:
    proposal = propose_n32_search_bounds(h8_j_kg, h16_j_kg)
    h_low = Decimal(proposal["proposed_low_j_kg"])
    h_high = Decimal(proposal["proposed_high_j_kg"])
    span = Decimal(proposal["initial_span"])
    stats = FastOuterBoundaryStats(authority_id=authority_id)
    expansions = 0
    probes: list[dict[str, Any]] = []

    def classify(enthalpy: Decimal) -> str:
        if deadline_monotonic is not None and time.perf_counter() >= deadline_monotonic:
            raise BracketEstablishmentFailed("deadline during bracket establishment")
        trial = _classify_fast_trial(
            subdivisions,
            enthalpy,
            provider,
            shell_authority,
            stats.bisection_iterations,
            stats,
            on_trial_receipt=on_trial_receipt,
        )
        return trial.classification

    while expansions <= MAX_BRACKET_EXPANSIONS:
        low_cls = classify(h_low)
        high_trial = _classify_fast_trial(
            subdivisions,
            h_high,
            provider,
            shell_authority,
            stats.bisection_iterations,
            stats,
            on_trial_receipt=on_trial_receipt,
        )
        high_cls = high_trial.classification
        probes.append(
            {
                "expansion": expansions,
                "h_low": str(h_low),
                "h_high": str(h_high),
                "low_classification": low_cls,
                "high_classification": high_cls,
            }
        )
        if high_cls == "HARD_BLOCKER":
            raise BracketEstablishmentFailed("HARD_BLOCKER at high probe")
        if low_cls == "HARD_BLOCKER":
            raise BracketEstablishmentFailed("HARD_BLOCKER at low probe")

        high_ok = False
        if high_cls == "VALID_TRAJECTORY" and high_trial.mesh_run is not None:
            obs = high_trial.mesh_run.observables
            high_ok = (
                obs.terminal_boundary_residual_j_kg >= 0 and obs.terminal_boundary_residual_k >= 0
            )
        if low_cls == "LOW_SIDE_DOMAIN_INFEASIBLE" and high_ok and h_low < h_high:
            meta = {
                **proposal,
                "establishment_probes": probes,
                "expansions_used": expansions,
                "outer_trials_for_establishment": stats.outer_trial_count,
            }
            return str(h_low), str(h_high), meta

        step = span * Decimal("0.5")
        if low_cls != "LOW_SIDE_DOMAIN_INFEASIBLE":
            h_low = max(H_MIN_J_KG, h_low - step)
        if not high_ok:
            h_high = min(H_MAX_J_KG, h_high + step)
        if h_low >= h_high:
            span = span * Decimal("1.5")
            h_center = Decimal(proposal["extrapolated_h32_center"])
            h_low = max(H_MIN_J_KG, h_center - span)
            h_high = min(H_MAX_J_KG, h_center + span)
        expansions += 1

    raise BracketEstablishmentFailed("max expansions exceeded without valid bracket")
