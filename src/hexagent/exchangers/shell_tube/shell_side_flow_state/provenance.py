"""Deterministic TASK-032 provenance assembly."""

from __future__ import annotations

from typing import Any

from .canonical import final_provenance_tuple
from .engineering_authority_snapshot import (
    ENGINEERING_SOURCE_FORMULA_FREEZE_COMMENT_ID,
    SOURCE_DEFINITION_ISSUE,
)
from .models import (
    DEFERRED_CAPABILITIES,
    DESIGN_CONTRACT_PATH,
    FLOW_MODEL,
    FORMULA_IDS,
    IMPLEMENTATION_SOFTWARE_VERSION,
    RHEOLOGY_MODEL,
    SOURCE_IDS,
    ShellSideFlowStateRequest,
    WarningEntry,
)

PROVENANCE_NAMESPACE = "task032.provenance.v1"


def build_provenance_prehash(
    *,
    request: ShellSideFlowStateRequest | None,
    request_hash: str | None,
    task031_geometry_id: str | None,
    task031_geometry_hash: str | None,
    property_snapshot_hash: str | None,
    mass_flow_authority_hash: str | None,
    engineering_authority_id: str | None,
    engineering_authority_hash: str | None,
    phase_region: Any,
    shell_side_case_id: str | None,
    shell_side_stream_id: str | None,
    shell_side_fluid_id: str | None,
    warnings: tuple[WarningEntry, ...],
) -> dict[str, Any]:
    geometry = None if request is None else request.task031_result.geometry
    task020_id = None if geometry is None else geometry.task020_configuration_id
    task020_hash = None if geometry is None else geometry.task020_configuration_hash
    evidence_refs = () if request is None else request.evidence_refs
    phase = phase_region.value if hasattr(phase_region, "value") else phase_region
    return {
        "task_id": "TASK-032",
        "design_contract_path": DESIGN_CONTRACT_PATH,
        "implementation_software_version": IMPLEMENTATION_SOFTWARE_VERSION,
        "request_hash": request_hash,
        "task020_configuration_id": task020_id,
        "task020_configuration_hash": task020_hash,
        "task031_geometry_id": task031_geometry_id,
        "task031_geometry_hash": task031_geometry_hash,
        "property_snapshot_hash": property_snapshot_hash,
        "mass_flow_authority_hash": mass_flow_authority_hash,
        "engineering_authority_id": engineering_authority_id,
        "engineering_authority_hash": engineering_authority_hash,
        "formula_ids": FORMULA_IDS,
        "source_ids": SOURCE_IDS,
        "flow_model": FLOW_MODEL,
        "phase_region": phase,
        "rheology_model": RHEOLOGY_MODEL,
        "shell_side_case_id": shell_side_case_id,
        "shell_side_stream_id": shell_side_stream_id,
        "shell_side_fluid_id": shell_side_fluid_id,
        "warnings": tuple(
            (
                item.code,
                item.severity,
                item.prerequisite_stage,
                item.field_path,
                item.message_key,
                item.evidence_refs,
            )
            for item in warnings
        ),
        "deferred_capabilities": DEFERRED_CAPABILITIES,
        "evidence_refs": evidence_refs,
        "engineering_source_formula_freeze_comment_id": (
            ENGINEERING_SOURCE_FORMULA_FREEZE_COMMENT_ID
        ),
        "source_definition_issue": SOURCE_DEFINITION_ISSUE,
    }


def finalize_provenance(prehash: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return final_provenance_tuple(prehash)


__all__ = [
    "PROVENANCE_NAMESPACE",
    "build_provenance_prehash",
    "finalize_provenance",
]
