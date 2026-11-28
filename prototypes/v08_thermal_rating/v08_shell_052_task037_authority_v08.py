"""Isolated Task037 evaluation for the frozen 0.52 m recovered candidate."""

# ruff: noqa: E501

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
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import RecoveredShell052Bundle
from prototypes.v08_thermal_rating.v08_task037_experimental_authority_v08 import (
    FoulingScenario,
    build_v08_experimental_task037_request,
)

Task037AuthorityStatus = Literal[
    "SUCCESS",
    "BLOCKED",
    "MATERIAL_AUTHORITY_REQUIRED",
    "UPSTREAM_BLOCKED",
]


@dataclass(frozen=True)
class Shell052Task037Evaluation:
    status: Task037AuthorityStatus
    request_label: str
    material_grade: str
    material_authority_id: str
    conductivity_authority_id: str
    fouling_scenario: FoulingScenario
    wall_conductivity_w_m_k: str | None
    wall_resistance_outer_m2_k_w: str | None
    wall_bundle_resistance_k_w: str | None
    result_id: str | None
    result_hash: str | None
    identity_replay_ok: bool
    notes: tuple[str, ...]
    raw: Task037SuccessResult | None


def evaluate_shell_052_task037(
    recovered: RecoveredShell052Bundle,
    *,
    fouling_scenario: FoulingScenario = "T039_DEMO_FOULING",
) -> Shell052Task037Evaluation:
    layout = recovered.structural_bundle.bundle.task021_layout
    t025 = recovered.structural_bundle.bundle.task025_result
    notes: list[str] = [
        "task037_isolated_not_via_task168_legacy_chain",
        "v08_experimental_content_bound_authority",
        f"fouling_scenario={fouling_scenario}",
    ]
    if not isinstance(t025, Task025ValidResult):
        return Shell052Task037Evaluation(
            status="UPSTREAM_BLOCKED",
            request_label="V08-SHELL052-TASK037-R1",
            material_grade="316L",
            material_authority_id="",
            conductivity_authority_id="",
            fouling_scenario=fouling_scenario,
            wall_conductivity_w_m_k=None,
            wall_resistance_outer_m2_k_w=None,
            wall_bundle_resistance_k_w=None,
            result_id=None,
            result_hash=None,
            identity_replay_ok=False,
            notes=(*notes, "task025_not_valid"),
            raw=None,
        )
    request = build_v08_experimental_task037_request(fouling_scenario)
    outcome = evaluate_task037(request, layout, t025)
    if outcome.status != "VALID" or outcome.success_result is None:
        stage = outcome.failure_stage or "unknown"
        return Shell052Task037Evaluation(
            status="MATERIAL_AUTHORITY_REQUIRED"
            if "FOULING" in stage or "material" in stage.lower()
            else "BLOCKED",
            request_label="V08-SHELL052-TASK037-R1",
            material_grade="316L",
            material_authority_id=request.wall_material_authority.authority_hash,
            conductivity_authority_id=request.wall_thermal_conductivity_authority.authority_hash,
            fouling_scenario=fouling_scenario,
            wall_conductivity_w_m_k=str(
                request.wall_thermal_conductivity_authority.thermal_conductivity_w_m_k
            ),
            wall_resistance_outer_m2_k_w=None,
            wall_bundle_resistance_k_w=None,
            result_id=None,
            result_hash=None,
            identity_replay_ok=False,
            notes=(*notes, f"evaluate_task037_failed:{stage}"),
            raw=None,
        )
    result = outcome.success_result
    replay = verify_task037_success_identity(result)
    return Shell052Task037Evaluation(
        status="SUCCESS",
        request_label="V08-SHELL052-TASK037-R1",
        material_grade="316L",
        material_authority_id=result.wall_material_authority_hash,
        conductivity_authority_id=result.wall_conductivity_authority_hash,
        fouling_scenario=fouling_scenario,
        wall_conductivity_w_m_k=str(
            request.wall_thermal_conductivity_authority.thermal_conductivity_w_m_k
        ),
        wall_resistance_outer_m2_k_w=str(result.wall_resistance_outer_surface_m2_k_w),
        wall_bundle_resistance_k_w=str(result.wall_bundle_conduction_resistance_k_w),
        result_id=result.result_id,
        result_hash=result.result_hash,
        identity_replay_ok=replay,
        notes=notes,
        raw=result,
    )


__all__ = ["Shell052Task037Evaluation", "evaluate_shell_052_task037"]
