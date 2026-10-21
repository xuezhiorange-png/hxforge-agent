"""Rating candidate selection policies (experimental, non-production)."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from math import pi
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
        CandidateSelectionRecord,
    )
    from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase

FIRST_N_POLICY = "FIRST_N_DISTINCT_GEOMETRY_TASK174_READY_UNDER_SOLVER_BUDGET"
MIN_AREA_POLICY = "MIN_NOMINAL_TUBE_AREA_SEARCH_EXCLUDING_BASELINE_GEOMETRIES"


def resolve_candidate_selection_mode(case: EngineeringCase) -> str:
    mode = getattr(case, "experimental_candidate_selection_mode", "FIRST_N_DISTINCT_GEOMETRY")
    return str(mode)


def baseline_geometry_pair_set(case: EngineeringCase) -> set[tuple[str, str]]:
    pairs = getattr(case, "r10_baseline_geometry_pairs", ()) or ()
    out: set[tuple[str, str]] = set()
    for pair in pairs:
        out.add((str(pair.tube_length_m), str(pair.baffle_spacing_m)))
    return out


def nominal_area_proxy_m2(
    case: EngineeringCase,
    *,
    tube_length_m: str,
    physical_tube_count: int,
) -> str:
    tube_od = case.candidate_constraints.tube_outer_diameter_m
    if case.bind_task172_c3_reference_geometry:
        tube_od = Decimal("0.01905")
    area = Decimal(str(pi)) * tube_od * Decimal(tube_length_m) * Decimal(physical_tube_count)
    return str(area)


def apply_rating_selection_policy(
    case: EngineeringCase,
    records: list[CandidateSelectionRecord],
) -> tuple[tuple[str, ...], str]:
    """Choose candidate IDs to mesh-rate after full-space enumeration."""
    mode = resolve_candidate_selection_mode(case)
    max_rate = case.solver_budget.max_candidates_to_rate
    baseline = baseline_geometry_pair_set(case)

    ready = [row for row in records if row.rating_request_ready]
    if mode == "MIN_NOMINAL_TUBE_AREA_SEARCH":
        pool = [row for row in ready if (row.tube_length_m, row.baffle_spacing_m) not in baseline]
        pool_sorted = sorted(
            pool,
            key=lambda row: Decimal(row.nominal_tube_outer_area_proxy_m2 or "Infinity"),
        )
        reason = MIN_AREA_POLICY
    else:
        pool_sorted = ready
        reason = FIRST_N_POLICY

    selected_ids: list[str] = []
    selected_geometry: set[str] = set()
    for row in pool_sorted:
        if len(selected_ids) >= max_rate:
            break
        if row.geometry_projection_hash in selected_geometry:
            continue
        selected_ids.append(row.candidate_id)
        selected_geometry.add(row.geometry_projection_hash)

    selected_set = set(selected_ids)
    for index, row in enumerate(records):
        if row.candidate_id in selected_set:
            records[index] = replace(
                row, selected_for_rating=True, task173_rating_status="SELECTED"
            )
        elif row.rating_request_ready:
            records[index] = replace(
                row, selected_for_rating=False, task173_rating_status="NOT_SELECTED"
            )

    return tuple(selected_ids), reason
