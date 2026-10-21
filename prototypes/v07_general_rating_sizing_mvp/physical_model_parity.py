"""Deterministic physical-model fingerprint for R4/R5/R6 comparability."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    PROFILE_ID,
    SHELL_INLET_T_K,
    SHELL_MASS_FLOW_KG_S,
    TUBE_INLET_T_K,
    TUBE_MASS_FLOW_KG_S,
)
from prototypes.v07_general_rating_sizing_mvp.case_streams import (
    shell_stream_spec,
    tube_stream_spec,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import NativeCellContext
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task173_sizing_request,
    sizing_request_identity,
)


def _physical_projection(case: EngineeringCase, native: NativeCellContext) -> dict[str, Any]:
    tube = tube_stream_spec(case)
    shell = shell_stream_spec(case)
    request = native.context.request
    return {
        "candidate_id": native.candidate_id,
        "candidate_hash": native.candidate_hash,
        "task171_result_hash": native.task171_result_hash,
        "task174_result_hash": native.task174_result_hash,
        "task025_parallel_area_m2": native.task025_parallel_area_m2,
        "physical_tube_count": native.physical_tube_count,
        "task031_geometry_hash": request.task031_geometry.geometry_hash,
        "task166_result_hash": request.task166_result.result_hash,
        "property_profile_id": PROFILE_ID,
        "kernel_tube_inlet_temperature_k": str(TUBE_INLET_T_K),
        "kernel_shell_inlet_temperature_k": str(SHELL_INLET_T_K),
        "kernel_tube_mass_flow_kg_s": str(TUBE_MASS_FLOW_KG_S),
        "kernel_shell_mass_flow_kg_s": str(SHELL_MASS_FLOW_KG_S),
        "user_tube_inlet_temperature_k": str(tube.inlet_temperature_k),
        "user_shell_inlet_temperature_k": str(shell.inlet_temperature_k),
        "user_tube_inlet_pressure_pa": str(tube.inlet_pressure_pa),
        "user_shell_inlet_pressure_pa": str(shell.inlet_pressure_pa),
        "target_duty_w": str(case.target_duty_w),
        "bind_task172_c3_reference_geometry": case.bind_task172_c3_reference_geometry,
        "candidate_constraints": case.candidate_constraints.model_dump(mode="json"),
    }


def build_physical_model_fingerprint(
    case: EngineeringCase,
    native: NativeCellContext,
) -> dict[str, Any]:
    physical = _physical_projection(case, native)
    sizing = build_task173_sizing_request(case)
    metadata_only = {
        "engineering_case_id": case.engineering_case_id,
        "engineering_case_schema": case.schema_version,
        "full_sizing_request_hash": sizing_request_identity(sizing),
        "candidate_rating_request_hash": native.rating_request_hash,
    }
    fingerprint_hash = canonical_sha256(physical)
    return {
        "schema_version": "hxforge.physical-model-fingerprint.v1",
        "physical_model_fingerprint_sha256": fingerprint_hash,
        "physical_projection": physical,
        "metadata_only_projection": metadata_only,
    }


def compare_physical_fingerprints(
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, Any]:
    same_physical = left["physical_model_fingerprint_sha256"] == right["physical_model_fingerprint_sha256"]
    meta_left = left["metadata_only_projection"]
    meta_right = right["metadata_only_projection"]
    metadata_differences = {
        key: {"left": meta_left[key], "right": meta_right[key]}
        for key in meta_left
        if meta_left[key] != meta_right[key]
    }
    return {
        "schema_version": "hxforge.physical-model-parity.v1",
        "r4_r5_physical_parity": same_physical,
        "physical_model_fingerprint_match": same_physical,
        "metadata_only_differences": metadata_differences,
        "interpretation": (
            "Matching physical_model_fingerprint_sha256 implies comparable thermal/geometry "
            "solver inputs; differing full_sizing_request_hash alone is metadata-only when parity is true."
            if same_physical
            else "Physical projections differ — mesh ladder comparisons are not strictly comparable."
        ),
    }
