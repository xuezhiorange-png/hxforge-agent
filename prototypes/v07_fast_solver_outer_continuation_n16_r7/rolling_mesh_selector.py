"""Production-aligned rolling mesh convergence candidate selection (experimental)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    ConvergenceComparison,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    REQUIRED_CONSECUTIVE_PASSING_PAIRS,
    REQUIRED_LATER_HEADROOM_LEVELS,
)

HeadroomStatus = Literal["PASS", "FAIL", "NOT_EXECUTED"]


@dataclass(frozen=True)
class RollingMeshEvaluation:
    subdivisions_per_interval: tuple[int, ...]
    comparison_history: tuple[dict[str, Any], ...]
    candidate_subdivisions: int | None
    headroom_subdivisions: int | None
    mesh_candidate_identified: bool
    headroom_status: HeadroomStatus
    consecutive_passing_pair_indices: tuple[int, ...]


def _comparison_record(
    comparison: ConvergenceComparison,
    coarse_n: int,
    fine_n: int,
) -> dict[str, Any]:
    return {
        "coarse_subdivisions": coarse_n,
        "fine_subdivisions": fine_n,
        "duty_status": comparison.duty_status,
        "wall_status": comparison.wall_status,
        "overall_status": comparison.overall_status,
        "duty_metric": str(comparison.duty_metric),
        "duty_difference_w": str(comparison.duty_difference_w),
    }


def evaluate_rolling_mesh_convergence(
    subdivisions_sequence: list[int],
    comparisons: list[ConvergenceComparison],
) -> RollingMeshEvaluation:
    """Mirror TASK173 _run_mesh_sequence candidate/headroom rules on frozen comparisons."""
    if len(comparisons) != max(0, len(subdivisions_sequence) - 1):
        raise ValueError("comparisons must align with subdivisions_sequence length")

    history: list[dict[str, Any]] = []
    for index, comparison in enumerate(comparisons):
        history.append(
            _comparison_record(
                comparison,
                subdivisions_sequence[index],
                subdivisions_sequence[index + 1],
            )
        )

    candidate_index: int | None = None
    headroom_index: int | None = None
    headroom_status: HeadroomStatus = "NOT_EXECUTED"
    consecutive_passing: list[int] = []

    for pair_index, record in enumerate(history):
        if record["overall_status"] == "PASS":
            consecutive_passing.append(pair_index)

    run_count = len(subdivisions_sequence)
    for run_index in range(run_count):
        comp_count = run_index
        if comp_count < 1:
            continue
        if candidate_index is None and comp_count >= REQUIRED_CONSECUTIVE_PASSING_PAIRS:
            recent = comparisons[comp_count - REQUIRED_CONSECUTIVE_PASSING_PAIRS : comp_count]
            if all(item.overall_status == "PASS" for item in recent):
                candidate_index = run_index
                if candidate_index >= len(subdivisions_sequence) - 1:
                    headroom_status = "FAIL"
                    break
                continue
        elif (
            candidate_index is not None
            and run_index == candidate_index + REQUIRED_LATER_HEADROOM_LEVELS
        ):
            headroom_comparison = comparisons[run_index - 1]
            if headroom_comparison.overall_status == "PASS":
                headroom_index = run_index
                headroom_status = "PASS"
            else:
                headroom_status = "FAIL"
            break

    candidate_n = subdivisions_sequence[candidate_index] if candidate_index is not None else None
    headroom_n = subdivisions_sequence[headroom_index] if headroom_index is not None else None
    identified = candidate_index is not None and headroom_index is not None

    return RollingMeshEvaluation(
        subdivisions_per_interval=tuple(subdivisions_sequence),
        comparison_history=tuple(history),
        candidate_subdivisions=candidate_n,
        headroom_subdivisions=headroom_n,
        mesh_candidate_identified=identified,
        headroom_status=headroom_status,
        consecutive_passing_pair_indices=tuple(consecutive_passing),
    )
