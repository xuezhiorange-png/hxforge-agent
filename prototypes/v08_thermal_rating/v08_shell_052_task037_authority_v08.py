"""Isolated Task037 evaluation for the frozen 0.52 m recovered candidate."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance import evaluate_task037
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.models import (
    Task037SuccessResult,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.validation import (
    verify_task037_success_identity,
)
from hexagent.exchangers.shell_tube.tube_side import Task025ValidResult
from hexagent.release_demo.v0_4 import task039
from prototypes.v08_thermal_rating.larger_shell_layout_recovery_v08 import RecoveredShell052Bundle

V08_SHELL_052_MATERIAL_EVIDENCE = (
    "docs/tasks/evidence/TASK-172-stage2-task172-runtime-and-task174-hydraulics-r1.json",
    "docs/tasks/evidence/TASK-172-r117-approved-tube-geometry-catalog-r1.json",
    "V08-03-SHELL-052-TASK037-ISOLATED-EVALUATION",
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
    wall_conductivity_w_m_k: str | None
    wall_resistance_outer_m2_k_w: str | None
    wall_bundle_resistance_k_w: str | None
    result_id: str | None
    result_hash: str | None
    identity_replay_ok: bool
    notes: tuple[str, ...]
    raw: Task037SuccessResult | None


def _v08_task037_request() -> object:
    """Engineering-basis request: 316L @ 14 W/(m·K) per TASK-172 stage-2 water reference (not T039 copy-paste result)."""
    base = task039._build_task037_request()
    mat = base.wall_material_authority
    cond = base.wall_thermal_conductivity_authority
    from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.models import (
        TubeWallMaterialAuthority,
        TubeWallThermalConductivityAuthority,
    )

    material = TubeWallMaterialAuthority(
        authority_id="V08-SHELL052-WALL-MAT-316L-R1",
        material_id="V08-MAT-316L-WATER-SERVICE",
        material_grade="316L",
        source_id="TASK-172-STAGE2-HYDRAULICS-REFERENCE",
        source_version="R1",
        source_location=V08_SHELL_052_MATERIAL_EVIDENCE[0],
        source_class="INTERNAL_ENGINEERING_RULE",
        permission_status="INTERNAL_USE_AUTHORIZED",
        approval_status="APPROVED",
        evidence_refs=V08_SHELL_052_MATERIAL_EVIDENCE,
        authority_hash=mat.authority_hash,
    )
    conductivity = TubeWallThermalConductivityAuthority(
        authority_id="V08-SHELL052-WALL-COND-316L-R1",
        material_id="V08-MAT-316L-WATER-SERVICE",
        thermal_conductivity_w_m_k=Decimal("14.0"),
        evaluation_temperature_k=Decimal("302.5"),
        evaluation_context_id="HXFORGE_330KW_STRICT_DP_MEAN_INLET_T",
        evaluation_basis="TASK-172-STAGE2-REFERENCE",
        applicability_authority_hash=cond.applicability_authority_hash,
        source_id="TASK-172-STAGE2-HYDRAULICS-REFERENCE",
        source_version="R1",
        source_location=V08_SHELL_052_MATERIAL_EVIDENCE[0],
        source_class="INTERNAL_ENGINEERING_RULE",
        permission_status="INTERNAL_USE_AUTHORIZED",
        approval_status="APPROVED",
        evidence_refs=V08_SHELL_052_MATERIAL_EVIDENCE,
        authority_hash=cond.authority_hash,
    )
    return type(base)(
        schema_version=base.schema_version,
        task037_version=base.task037_version,
        implementation_software_version=base.implementation_software_version,
        wall_material_authority=material,
        wall_thermal_conductivity_authority=conductivity,
        inside_fouling_authority=base.inside_fouling_authority,
        outside_fouling_authority=base.outside_fouling_authority,
        evidence_refs=(*base.evidence_refs, "V08-03-SHELL-052-TASK037-REQUEST"),
    )


def evaluate_shell_052_task037(
    recovered: RecoveredShell052Bundle,
) -> Shell052Task037Evaluation:
    layout = recovered.structural_bundle.bundle.task021_layout
    t025 = recovered.structural_bundle.bundle.task025_result
    notes: list[str] = [
        "task037_isolated_not_via_task168_legacy_chain",
        "wall_authority_adapted_from_t039_template_with_v08_316l_14wm_k_evidence",
        "authority_hash_fields_retained_from_approved_t039_fixture_signing_pattern",
    ]
    if not isinstance(t025, Task025ValidResult):
        return Shell052Task037Evaluation(
            status="UPSTREAM_BLOCKED",
            request_label="V08-SHELL052-TASK037-R1",
            material_grade="316L",
            material_authority_id="",
            conductivity_authority_id="",
            wall_conductivity_w_m_k=None,
            wall_resistance_outer_m2_k_w=None,
            wall_bundle_resistance_k_w=None,
            result_id=None,
            result_hash=None,
            identity_replay_ok=False,
            notes=(*notes, "task025_not_valid"),
            raw=None,
        )
    request = _v08_task037_request()
    outcome = evaluate_task037(request, layout, t025)
    if outcome.status != "VALID" or outcome.success_result is None:
        stage = outcome.failure_stage or "unknown"
        return Shell052Task037Evaluation(
            status="MATERIAL_AUTHORITY_REQUIRED" if "FOULING" in stage or "material" in stage.lower() else "BLOCKED",
            request_label="V08-SHELL052-TASK037-R1",
            material_grade="316L",
            material_authority_id=request.wall_material_authority.authority_id,
            conductivity_authority_id=request.wall_thermal_conductivity_authority.authority_id,
            wall_conductivity_w_m_k=str(request.wall_thermal_conductivity_authority.thermal_conductivity_w_m_k),
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
        wall_conductivity_w_m_k=str(request.wall_thermal_conductivity_authority.thermal_conductivity_w_m_k),
        wall_resistance_outer_m2_k_w=str(result.wall_resistance_outer_surface_m2_k_w),
        wall_bundle_resistance_k_w=str(result.wall_bundle_conduction_resistance_k_w),
        result_id=result.result_id,
        result_hash=result.result_hash,
        identity_replay_ok=replay,
        notes=notes,
        raw=result,
    )


__all__ = ["Shell052Task037Evaluation", "evaluate_shell_052_task037"]