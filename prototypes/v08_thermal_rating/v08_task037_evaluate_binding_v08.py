"""Evaluate Task037 on a rating binding for a V08 fouling scenario."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance import evaluate_task037
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.models import (
    Task037SuccessResult,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.validation import (
    verify_task037_success_identity,
)
from hexagent.exchangers.shell_tube.tube_side import Task025ValidResult
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import CandidateRatingBindings
from prototypes.v08_thermal_rating.v08_task037_experimental_authority_v08 import (
    FoulingScenario,
    build_v08_experimental_task037_request,
)

Task037EvalStatus = Literal["SUCCESS", "BLOCKED", "UPSTREAM_BLOCKED"]


@dataclass(frozen=True)
class BindingTask037Evaluation:
    status: Task037EvalStatus
    fouling_scenario: FoulingScenario
    material_grade: str
    wall_conductivity_w_m_k: str | None
    wall_resistance_outer_m2_k_w: str | None
    material_authority_hash: str | None
    conductivity_authority_hash: str | None
    inside_fouling_resistance_m2_k_w: str | None
    outside_fouling_resistance_m2_k_w: str | None
    result_hash: str | None
    identity_replay_ok: bool
    raw: Task037SuccessResult | None


def evaluate_binding_task037(
    bindings: CandidateRatingBindings,
    *,
    fouling_scenario: FoulingScenario,
) -> BindingTask037Evaluation:
    layout = bindings.bundle.bundle.task021_layout
    t025 = bindings.bundle.bundle.task025_result
    if not isinstance(t025, Task025ValidResult):
        return BindingTask037Evaluation(
            status="UPSTREAM_BLOCKED",
            fouling_scenario=fouling_scenario,
            material_grade="316L",
            wall_conductivity_w_m_k=None,
            wall_resistance_outer_m2_k_w=None,
            material_authority_hash=None,
            conductivity_authority_hash=None,
            inside_fouling_resistance_m2_k_w=None,
            outside_fouling_resistance_m2_k_w=None,
            result_hash=None,
            identity_replay_ok=False,
            raw=None,
        )
    request = build_v08_experimental_task037_request(fouling_scenario)
    outcome = evaluate_task037(request, layout, t025)
    if outcome.status != "VALID" or outcome.success_result is None:
        return BindingTask037Evaluation(
            status="BLOCKED",
            fouling_scenario=fouling_scenario,
            material_grade="316L",
            wall_conductivity_w_m_k=str(
                request.wall_thermal_conductivity_authority.thermal_conductivity_w_m_k
            ),
            wall_resistance_outer_m2_k_w=None,
            material_authority_hash=request.wall_material_authority.authority_hash,
            conductivity_authority_hash=request.wall_thermal_conductivity_authority.authority_hash,
            inside_fouling_resistance_m2_k_w=str(
                request.inside_fouling_authority.fouling_resistance_m2_k_w
            ),
            outside_fouling_resistance_m2_k_w=str(
                request.outside_fouling_authority.fouling_resistance_m2_k_w
            ),
            result_hash=None,
            identity_replay_ok=False,
            raw=None,
        )
    result = outcome.success_result
    replay = verify_task037_success_identity(result)
    return BindingTask037Evaluation(
        status="SUCCESS",
        fouling_scenario=fouling_scenario,
        material_grade="316L",
        wall_conductivity_w_m_k=str(
            request.wall_thermal_conductivity_authority.thermal_conductivity_w_m_k
        ),
        wall_resistance_outer_m2_k_w=str(result.wall_resistance_outer_surface_m2_k_w),
        material_authority_hash=result.wall_material_authority_hash,
        conductivity_authority_hash=result.wall_conductivity_authority_hash,
        inside_fouling_resistance_m2_k_w=str(
            request.inside_fouling_authority.fouling_resistance_m2_k_w
        ),
        outside_fouling_resistance_m2_k_w=str(
            request.outside_fouling_authority.fouling_resistance_m2_k_w
        ),
        result_hash=result.result_hash,
        identity_replay_ok=replay,
        raw=result,
    )


__all__ = ["BindingTask037Evaluation", "evaluate_binding_task037"]
