"""Exact TASK-034 v2 provenance construction."""

from __future__ import annotations

from typing import Any

from .canonical import PROVENANCE_FIELDS, provenance_hash
from .models import (
    DESIGN_CONTRACT_PATH,
    IMPLEMENTATION_SOFTWARE_VERSION,
    PROFILE_ID,
    SOURCE_DEFINITION_ISSUE,
)


def _read_field(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _task033_result(task033: Any) -> dict[str, Any]:
    if not isinstance(task033, dict):
        return {}
    validation_result = task033.get("task033_validation_result")
    if not isinstance(validation_result, dict):
        return {}
    result = validation_result.get("heat_transfer")
    return result if isinstance(result, dict) else {}


def _authority_field(request: Any, field: str) -> Any:
    authority = _read_field(request, "shell_type_authority")
    return authority.get(field) if isinstance(authority, dict) else None


def build_provenance_prehash(
    *,
    request: Any,
    request_hash: str | None,
    flow: Any,
    task033: Any,
    task031_request_hash: str | None,
    task031_geometry_id: str | None,
    task031_geometry_hash: str | None,
    warnings: Any,
    deferred_capabilities: Any,
) -> dict[str, Any]:
    task033_result = _task033_result(task033)
    return {
        "task_id": "TASK034",
        "profile_id": PROFILE_ID,
        "design_contract_path": DESIGN_CONTRACT_PATH,
        "implementation_software_version": IMPLEMENTATION_SOFTWARE_VERSION,
        "request_hash": request_hash,
        "shell_side_case_id": _read_field(flow, "shell_side_case_id"),
        "shell_side_stream_id": _read_field(flow, "shell_side_stream_id"),
        "shell_side_fluid_id": _read_field(flow, "shell_side_fluid_id"),
        "task020_configuration_id": _read_field(flow, "task020_configuration_id"),
        "task020_configuration_hash": _read_field(flow, "task020_configuration_hash"),
        "shell_type": _authority_field(request, "shell_type"),
        "shell_type_authority_hash": _authority_field(request, "authority_hash"),
        "shell_type_authority_record_id": _authority_field(request, "authority_record_id"),
        "shell_type_authority_source_id": _authority_field(request, "authority_source_id"),
        "shell_type_authority_source_version": _authority_field(
            request, "authority_source_version"
        ),
        "task031_request_hash": task031_request_hash,
        "task031_geometry_id": task031_geometry_id,
        "task031_geometry_hash": task031_geometry_hash,
        "task032_request_hash": _read_field(flow, "request_hash"),
        "task032_result_hash": _read_field(flow, "result_hash"),
        "task032_result_id": _read_field(flow, "result_id"),
        "task033_request_hash": task033_result.get("request_hash"),
        "task033_result_hash": task033_result.get("result_hash"),
        "task033_result_id": task033_result.get("result_id"),
        "property_snapshot_hash": _read_field(flow, "property_snapshot_hash"),
        "mass_flow_authority_hash": _read_field(flow, "mass_flow_authority_hash"),
        "wall_property_schema_version": _read_field(request, "wall_property_schema_version"),
        "wall_property_source_id": _read_field(request, "wall_property_source_id"),
        "wall_property_source_version": _read_field(request, "wall_property_source_version"),
        "wall_property_snapshot_hash": _read_field(request, "wall_property_snapshot_hash"),
        "wall_property_authority_hash": _read_field(request, "wall_property_authority_hash"),
        "correlation_id": (
            "TASK034_KERN_BAYRAM_SEVILGEN_2017_EQ15_EQ16_EQ17_WALL_VISCOSITY_CORRECTION_V1"
        ),
        "engineering_source_authority_record_id": "5387111841",
        "source_id": "SRC-MDPI-ENERGIES-2017-1156-BAYRAM-SEVILGEN",
        "source_version": "2018-01-10_UPDATED_VERSION_OF_RECORD",
        "source_location": "Section_2.1.1_Equations_15_16_17_pages_3_4",
        "frozen_source_artifact": "DOI:10.3390/en1101156",
        "applicability_profile": (
            "400 < Re_s < 1000000; SINGLE_PHASE_LIQUID; NEWTONIAN; E_SHELL; ONE_SHELL_PASS"
        ),
        "physical_boundary": (
            "IDEALIZED_SHELL_SIDE_BUNDLE_CROSSFLOW_FRICTIONAL_PRESSURE_DROP_SCREENING_AGGREGATE"
        ),
        "excluded_phenomena": (
            "NOZZLE",
            "STATIC_HEAD",
            "ACCELERATION",
            "LEAKAGE",
            "BYPASS",
            "BELL_DELAWARE",
            "UNEQUAL_SPACING",
        ),
        "modeled_quantity": "modeled_shell_side_pressure_drop_pa",
        "formula_identity": "Eq15|Eq16|Eq17|phi_s=(mu_b/mu_w)^(7/50)",
        "deterministic_algorithm_ids": (
            "EXPLICIT_CONTEXT_V1",
            "DECIMAL_LN_EXP_RATIONAL_EXPONENT_V1",
            "ROUND_HALF_EVEN",
        ),
        "warnings": warnings,
        "deferred_capabilities": deferred_capabilities,
        "evidence_refs": _read_field(request, "evidence_refs"),
        "source_definition_issue": SOURCE_DEFINITION_ISSUE,
        "source_definition_freeze_comment_id": "5403427791",
    }


def finalize_provenance(prehash: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    complete = {**prehash, "provenance_hash": provenance_hash(prehash)}
    return tuple((field, complete.get(field)) for field in PROVENANCE_FIELDS)


__all__ = ["build_provenance_prehash", "finalize_provenance"]
