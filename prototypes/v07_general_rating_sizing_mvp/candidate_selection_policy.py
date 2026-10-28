"""Rating candidate selection policies (experimental, non-production)."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from math import pi
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
        CandidateSelectionRecord,
    )
    from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase

FIRST_N_POLICY = "FIRST_N_DISTINCT_GEOMETRY_TASK174_READY_UNDER_SOLVER_BUDGET"
MIN_AREA_POLICY = "MIN_NOMINAL_TUBE_AREA_SEARCH_EXCLUDING_BASELINE_GEOMETRIES"
VARIABLE_SHELL_POLICY = "VARIABLE_SHELL_BUNDLE_MIN_NOMINAL_AREA_R13"


def resolve_candidate_selection_mode(case: EngineeringCase) -> str:
    mode = getattr(case, "experimental_candidate_selection_mode", "FIRST_N_DISTINCT_GEOMETRY")
    return str(mode)


def baseline_geometry_pair_set(case: EngineeringCase) -> set[tuple[str, str]]:
    pairs = getattr(case, "r10_baseline_geometry_pairs", ()) or ()
    out: set[tuple[str, str]] = set()
    for pair in pairs:
        out.add((str(pair.tube_length_m), str(pair.baffle_spacing_m)))
    return out


def _matches_fingerprint(row: CandidateSelectionRecord, pair: Any) -> bool:
    if (row.tube_length_m, row.baffle_spacing_m) != (
        str(pair.tube_length_m),
        str(pair.baffle_spacing_m),
    ):
        return False
    shell = getattr(pair, "shell_inside_diameter_m", None)
    if shell is not None and row.shell_inside_diameter_m != str(shell):
        return False
    tube_count = getattr(pair, "physical_tube_count", None)
    return tube_count is None or row.physical_tube_count == tube_count


def _excluded_by_fingerprints(row: CandidateSelectionRecord, case: EngineeringCase) -> bool:
    for collection in (
        getattr(case, "r10_baseline_geometry_pairs", ()),
        getattr(case, "r12_baseline_geometry_fingerprints", ()),
    ):
        for pair in collection or ():
            if _matches_fingerprint(row, pair):
                return True
    return False


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


def _pinned_baseline_rows(
    case: EngineeringCase, ready: list[CandidateSelectionRecord]
) -> list[CandidateSelectionRecord]:
    pinned: list[CandidateSelectionRecord] = []
    for pair in getattr(case, "r10_baseline_geometry_pairs", ()) or ():
        for row in ready:
            if _matches_fingerprint(row, pair):
                pinned.append(row)
                break
    return pinned


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
    elif mode == "VARIABLE_SHELL_BUNDLE_MIN_NOMINAL_AREA_R13":
        pool = [row for row in ready if not _excluded_by_fingerprints(row, case)]
        pool_sorted = sorted(
            pool,
            key=lambda row: (
                Decimal(row.nominal_tube_outer_area_proxy_m2 or "Infinity"),
                row.physical_tube_count or 0,
            ),
        )
        reason = VARIABLE_SHELL_POLICY
    else:
        pool_sorted = ready
        reason = FIRST_N_POLICY

    selected_ids: list[str] = []
    selected_geometry: set[str] = set()
    selected_tube_counts: set[int] = set()

    def _try_pick(row: CandidateSelectionRecord) -> bool:
        if len(selected_ids) >= max_rate:
            return False
        if row.geometry_projection_hash in selected_geometry:
            return False
        if mode == "VARIABLE_SHELL_BUNDLE_MIN_NOMINAL_AREA_R13":
            count = row.physical_tube_count
            if (
                len(selected_ids) == 1
                and count is not None
                and count in selected_tube_counts
                and len(pool_sorted) > 2
            ):
                return False
        selected_ids.append(row.candidate_id)
        selected_geometry.add(row.geometry_projection_hash)
        if row.physical_tube_count is not None:
            selected_tube_counts.add(row.physical_tube_count)
        return True

    if mode not in {
        "MIN_NOMINAL_TUBE_AREA_SEARCH",
        "VARIABLE_SHELL_BUNDLE_MIN_NOMINAL_AREA_R13",
    }:
        for row in _pinned_baseline_rows(case, ready):
            _try_pick(row)

    for row in pool_sorted:
        _try_pick(row)
    if mode == "VARIABLE_SHELL_BUNDLE_MIN_NOMINAL_AREA_R13" and len(selected_ids) < max_rate:
        for row in pool_sorted:
            if row.candidate_id in selected_ids:
                continue
            if _try_pick(row) and len(selected_ids) >= max_rate:
                break

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
