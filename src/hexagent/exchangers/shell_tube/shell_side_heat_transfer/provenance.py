"""Exact TASK-033 provenance construction."""

from __future__ import annotations

from typing import Any

from .canonical import PROVENANCE_FIELDS, provenance_hash
from .engineering_authority_snapshot import (
    ENGINEERING_SOURCE_AUTHORITY_RECORD_ID,
    FRACTIONAL_POWER_ALGORITHM,
    HEAT_TRANSFER_SURFACE,
    SOURCE_DOI,
    SOURCE_ID,
    SOURCE_LOCATION,
    VALUE_AUTHORITY_REPLAY_MODEL,
)
from .models import CORRELATION_ID, DEFERRED_CAPABILITIES, DESIGN_CONTRACT_PATH


def build_provenance_prehash(
    *,
    request_hash: str | None,
    flow: Any,
    request: Any,
    task032_request_hash: str | None,
    task032_result_hash: str | None,
    task032_result_id: str | None,
    warnings: Any,
) -> dict[str, Any]:
    flow_value = flow
    if request is None:
        evidence_refs: tuple[str, ...] = ()
    else:
        evidence = request.task032_request_evidence
        evidence_refs = tuple(request.evidence_refs) + tuple(evidence.evidence_refs)
    return {
        "task_id": "TASK033",
        "design_contract_path": DESIGN_CONTRACT_PATH,
        "implementation_software_version": "task033.shell-side-heat-transfer-impl-v1",
        "request_hash": request_hash,
        "shell_side_case_id": flow_value.shell_side_case_id if flow_value else None,
        "shell_side_stream_id": flow_value.shell_side_stream_id if flow_value else None,
        "shell_side_fluid_id": flow_value.shell_side_fluid_id if flow_value else None,
        "task020_configuration_id": flow_value.task020_configuration_id if flow_value else None,
        "task020_configuration_hash": flow_value.task020_configuration_hash if flow_value else None,
        "task031_geometry_id": flow_value.task031_geometry_id if flow_value else None,
        "task031_geometry_hash": flow_value.task031_geometry_hash if flow_value else None,
        "property_snapshot_hash": flow_value.property_snapshot_hash if flow_value else None,
        "mass_flow_authority_hash": flow_value.mass_flow_authority_hash if flow_value else None,
        "task032_request_hash": task032_request_hash,
        "task032_result_hash": task032_result_hash,
        "task032_result_id": task032_result_id,
        "correlation_id": CORRELATION_ID,
        "engineering_source_authority_record_id": ENGINEERING_SOURCE_AUTHORITY_RECORD_ID,
        "source_id": SOURCE_ID,
        "source_doi": SOURCE_DOI,
        "source_location": SOURCE_LOCATION,
        "heat_transfer_surface": HEAT_TRANSFER_SURFACE,
        "value_authority_replay_model": VALUE_AUTHORITY_REPLAY_MODEL,
        "fractional_power_algorithm": FRACTIONAL_POWER_ALGORITHM,
        "warnings": warnings,
        "deferred_capabilities": DEFERRED_CAPABILITIES,
        "evidence_refs": evidence_refs,
        "source_definition_issue": 196,
        "engineering_source_correlation_freeze_comment_id": 5387111841,
    }


def finalize_provenance(prehash: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    if set(prehash) != set(PROVENANCE_FIELDS) - {"provenance_hash"}:
        raise ValueError("provenance field set mismatch")
    complete = dict(prehash)
    complete["provenance_hash"] = provenance_hash(prehash)
    return tuple((field, complete[field]) for field in PROVENANCE_FIELDS)


__all__ = ["build_provenance_prehash", "finalize_provenance"]
