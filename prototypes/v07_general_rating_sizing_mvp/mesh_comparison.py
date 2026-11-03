"""Compare frozen R4 n=1 mesh metrics to a fresh n=2 native mesh run."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import MeshObservables
from prototypes.v07_general_rating_sizing_mvp.frozen_r4_n1 import FrozenR4N1Mesh


def compare_frozen_n1_to_n2_mesh(
    frozen: FrozenR4N1Mesh,
    fine_obs: MeshObservables,
    *,
    fine_mesh_hash: str,
    fine_subdivisions: int,
    candidate_id: str,
    rating_request_hash: str,
) -> dict[str, Any]:
    duty_difference = abs(fine_obs.total_duty_w - frozen.total_duty_w)
    denominator = max(abs(frozen.total_duty_w), abs(fine_obs.total_duty_w))
    if denominator <= t173.MESH_DUTY_ABSOLUTE_THRESHOLD_W:
        duty_metric = duty_difference
        duty_metric_units = "W"
        duty_metric_threshold = t173.MESH_DUTY_ABSOLUTE_THRESHOLD_W
        duty_precision_floor_metric = fine_obs.duty_roundoff_floor_w
    else:
        duty_metric = duty_difference / denominator
        duty_metric_units = "RELATIVE_FRACTION"
        duty_metric_threshold = t173.MESH_DUTY_RELATIVE_THRESHOLD
        duty_precision_floor_metric = fine_obs.duty_roundoff_floor_w / denominator
    duty_status = t173._classify_difference(
        duty_metric,
        duty_precision_floor_metric,
        duty_metric_threshold,
    )
    terminal_delta = abs(
        fine_obs.terminal_boundary_residual_k - frozen.terminal_boundary_residual_k
    )
    duty_delta_percent = (
        (duty_difference / denominator * Decimal("100")) if denominator > 0 else Decimal("0")
    )
    identity_ok = candidate_id == frozen.candidate_id
    comparable = identity_ok and fine_subdivisions == 2 and frozen.mesh_level == 1
    wall_extrema_note = "WALL_EXTREMA_NOT_COMPARED_WITHOUT_ARCHIVED_R4_N1_OBSERVABLES"
    duty_comparison = duty_status if comparable else "NOT_COMPARABLE"
    return {
        "schema_version": "hxforge.mesh-n1-n2-comparison.v1",
        "comparable": comparable,
        "frozen_n1_source": frozen.source_path,
        "frozen_n1_mesh_hash": frozen.mesh_result_hash,
        "fine_n2_mesh_hash": fine_mesh_hash,
        "candidate_id": candidate_id,
        "rating_request_hash": rating_request_hash,
        "duty_delta_w": str(duty_difference),
        "duty_delta_percent": str(duty_delta_percent),
        "terminal_boundary_residual_delta_k": str(terminal_delta),
        "duty_metric": str(duty_metric),
        "duty_metric_units": duty_metric_units,
        "duty_metric_threshold": str(duty_metric_threshold),
        "duty_status": duty_status,
        "duty_comparison_status": duty_comparison,
        "wall_comparison": wall_extrema_note,
        "full_mesh_comparison_status": "NOT_AVAILABLE_WALL_EXTREMA_NOT_ARCHIVED",
        "mesh_comparison_status": duty_comparison,
    }


def compare_mesh_observables_duty(
    coarse_duty: Decimal,
    coarse_terminal_k: Decimal,
    fine_obs: MeshObservables,
    *,
    coarse_mesh_hash: str,
    fine_mesh_hash: str,
    coarse_level: int,
    fine_level: int,
    comparable: bool,
) -> dict[str, Any]:
    duty_difference = abs(fine_obs.total_duty_w - coarse_duty)
    denominator = max(abs(coarse_duty), abs(fine_obs.total_duty_w))
    if denominator <= t173.MESH_DUTY_ABSOLUTE_THRESHOLD_W:
        duty_metric = duty_difference
        duty_metric_units = "W"
        duty_metric_threshold = t173.MESH_DUTY_ABSOLUTE_THRESHOLD_W
        duty_precision_floor_metric = fine_obs.duty_roundoff_floor_w
    else:
        duty_metric = duty_difference / denominator
        duty_metric_units = "RELATIVE_FRACTION"
        duty_metric_threshold = t173.MESH_DUTY_RELATIVE_THRESHOLD
        duty_precision_floor_metric = fine_obs.duty_roundoff_floor_w / denominator
    duty_status = t173._classify_difference(
        duty_metric,
        duty_precision_floor_metric,
        duty_metric_threshold,
    )
    terminal_delta = abs(fine_obs.terminal_boundary_residual_k - coarse_terminal_k)
    duty_delta_percent = (
        (duty_difference / denominator * Decimal("100")) if denominator > 0 else Decimal("0")
    )
    duty_comparison = duty_status if comparable else "NOT_COMPARABLE"
    wall_note = "WALL_EXTREMA_NOT_COMPARED_WITHOUT_COARSE_ARCHIVED_OBSERVABLES"
    return {
        "schema_version": "hxforge.mesh-duty-comparison.v1",
        "comparable": comparable,
        "coarse_mesh_level": coarse_level,
        "fine_mesh_level": fine_level,
        "coarse_mesh_hash": coarse_mesh_hash,
        "fine_mesh_hash": fine_mesh_hash,
        "duty_delta_w": str(duty_difference),
        "duty_delta_percent": str(duty_delta_percent),
        "duty_metric": str(duty_metric),
        "duty_metric_units": duty_metric_units,
        "terminal_boundary_residual_delta_k": str(terminal_delta),
        "duty_comparison_status": duty_comparison,
        "full_mesh_comparison_status": "NOT_AVAILABLE_WALL_EXTREMA_NOT_ARCHIVED",
        "wall_comparison": wall_note,
    }
