"""Strict public models for the TASK173 fixed-geometry rating runtime."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TASK173_REQUEST_SCHEMA: Final = "task173.fixed-geometry-rating-request.v1"
TASK173_RESULT_SCHEMA: Final = "task173.fixed-geometry-rating-result.v1"
TASK173_BLOCKED_SCHEMA: Final = "task173.fixed-geometry-rating-blocked.v1"
OUTER_BOUNDARY_SOLVER_AUTHORITY_ID: Final = "V07-T173-OUTER-BOUNDARY-FEASIBILITY-BISECTION-R1"
LOCAL_STATE_RECONSTRUCTION_AUTHORITY_ID: Final = "V07-T173-ENTHALPY-MIDPOINT-LOCAL-STATE-R1"
CELL_ROOT_SOLVER_AUTHORITY_ID: Final = "V07-T173-VALID-POINT-CELL-ROOT-BRACKETING-R3"
ENDPOINT_HOLE_LOW_SIDE_CLASSIFICATION_AUTHORITY_ID: Final = (
    "V07-T173-SHELL-CAPACITY-ENDPOINT-HOLE-LOW-SIDE-CLASSIFICATION-R1"
)
PRODUCTION_MESH_PROFILE_AUTHORITY_ID: Final = "V07-T172-REAL-CASE-PRODUCTION-MESH-PROFILE-R1"
REVIEWED_MESH_SEQUENCE = (1, 2, 4, 8, 16, 32, 64)
H_MIN_J_KG = Decimal("104920.11980926784")
H_MAX_J_KG = Decimal("112654.89965462626")
T_MIN_K = Decimal("298.15")
T_MAX_K = Decimal("300")
REFERENCE_PRESSURE_PA = Decimal("101325")
TERMINAL_TOLERANCE_K: Final = Decimal("1e-8")
MAX_OUTER_BISECTION_ITERATIONS: Final = 128


class StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class Task173Request(StrictModel):
    schema_version: Literal["task173.fixed-geometry-rating-request.v1"] = TASK173_REQUEST_SCHEMA
    case_revision_id: Literal["V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-R2"]
    case_mode: Literal["RATING_FIXED_GEOMETRY"]
    shell_flow_replay_bundle: dict[str, Any]
    task174_result: dict[str, Any]
    mesh_sequence: tuple[int, ...] = REVIEWED_MESH_SEQUENCE

    @model_validator(mode="after")
    def reviewed_mesh_sequence(self) -> Task173Request:
        if self.mesh_sequence != REVIEWED_MESH_SEQUENCE:
            raise ValueError("TASK173 requires the complete reviewed production mesh sequence")
        return self


class PropertySnapshot(StrictModel):
    temperature_k: str
    pressure_pa: str
    enthalpy_j_kg: str
    density_kg_m3: str
    cp_j_kg_k: str
    viscosity_pa_s: str
    conductivity_w_m_k: str
    entropy_j_kg_k: str
    phase: Literal["liquid"]
    backend: Literal["HEOS::Water"]
    provider: Literal["CoolProp"]
    provider_version: Literal["8.0.0"]
    provider_git_revision: Literal["ae81610e7d23efc57f9d051c8e70a4d66e87537f"]
    reference_state: Literal["DEF"]
    query_type: Literal["TP", "PH"]
    inputs: dict[str, str]
    configuration_fingerprint: str


class FaceState(StrictModel):
    face_id: str
    face_hash: str
    case_revision_id: str
    topology_id: str
    flow_path_id: str
    side: Literal["TUBE", "SHELL"]
    face_index: int = Field(ge=0)
    physical_coordinate_m: Decimal
    travel_role: Literal["INLET", "OUTLET", "INTERIOR"]
    temperature_k: Decimal
    pressure_pa: Decimal
    enthalpy_j_kg: Decimal
    property_profile_id: Literal["V07-T172-WATER-PROPERTY-PROFILE-R2"]
    property_snapshot_hash: str
    property_snapshot: PropertySnapshot
    producer_authority_id: str
    provenance: dict[str, str]


class LocalStateReceipt(StrictModel):
    receipt_id: str
    receipt_hash: str
    side: Literal["TUBE", "SHELL"]
    physical_support_id: str
    physical_segment_id: str
    numerical_cell_id: str
    upstream_face_state_id: str
    upstream_face_state_hash: str
    downstream_face_state_id: str
    downstream_face_state_hash: str
    constitutive_evaluation_state_id: str
    constitutive_evaluation_state_hash: str
    constitutive_evaluation_temperature_k: Decimal
    constitutive_evaluation_enthalpy_j_kg: Decimal
    constitutive_evaluation_property_snapshot_hash: str
    constitutive_evaluation_property_snapshot: PropertySnapshot
    reconstruction_authority_id: Literal["V07-T173-ENTHALPY-MIDPOINT-LOCAL-STATE-R1"]
    reconstruction_authority_hash: str
    property_profile_id: Literal["V07-T172-WATER-PROPERTY-PROFILE-R2"]
    topology_id: str
    flow_path_id: str


class RatedCell(StrictModel):
    physical_support_id: str
    physical_segment_id: str
    support_start_m: Decimal
    support_end_m: Decimal
    tube_cell_id: str
    shell_cell_id: str
    wall_interface_id: str
    tube_upstream_face_id: str
    tube_downstream_face_id: str
    shell_upstream_face_id: str
    shell_downstream_face_id: str
    tube_state_receipt: LocalStateReceipt
    shell_state_receipt: LocalStateReceipt
    task172_request_hash: str
    task172_result_id: str
    task172_result_hash: str
    task172_result_projection: dict[str, Any]
    signed_q_hot_to_cold_w: Decimal
    wall_temperature_inner_k: Decimal
    wall_temperature_outer_k: Decimal
    shell_j_mu: Decimal
    local_duty_roundoff_bound_w: Decimal
    local_wall_temperature_roundoff_bound_k: Decimal


class MeshObservables(StrictModel):
    subdivisions_per_interval: int
    mesh_level_identity: str
    tube_cell_count: int
    shell_cell_count: int
    total_numerical_cell_count: int
    wall_interface_count: int
    total_duty_w: Decimal
    interval_duty_w: tuple[Decimal, ...]
    tube_outlet_temperature_k: Decimal
    shell_outlet_temperature_k: Decimal
    wall_inner_min_k: Decimal
    wall_inner_max_k: Decimal
    wall_outer_min_k: Decimal
    wall_outer_max_k: Decimal
    minimum_approach_temperature_k: Decimal
    hot_energy_loss_w: Decimal
    cold_energy_gain_w: Decimal
    wall_duty_sum_w: Decimal
    energy_balance_residual_w: Decimal
    terminal_boundary_residual_k: Decimal
    terminal_boundary_residual_j_kg: Decimal
    duty_roundoff_floor_w: Decimal
    wall_temperature_roundoff_floor_k: Decimal
    task172_local_evaluation_count: int
    task172_numerical_hole_count: int
    task172_numerical_hole_counts_by_code: dict[str, int]
    task172_numerical_hole_neighborhoods: tuple[dict[str, Any], ...]
    rating_result_hash: str
    local_task172_result_hashes: tuple[str, ...]


class ConvergenceComparison(StrictModel):
    coarse_subdivisions: int
    fine_subdivisions: int
    interval_duty_differences_w: tuple[Decimal, ...]
    duty_difference_w: Decimal
    duty_metric: Decimal
    duty_metric_units: Literal["W", "RELATIVE_FRACTION"]
    duty_metric_threshold: Decimal
    duty_precision_floor_metric: Decimal
    duty_precision_floor_w: Decimal
    duty_status: Literal["PASS", "FAIL", "PRECISION_FLOOR_UNRESOLVED"]
    wall_extrema_differences_k: dict[str, Decimal]
    wall_precision_floor_k: Decimal
    wall_status: Literal["PASS", "FAIL", "PRECISION_FLOOR_UNRESOLVED"]
    overall_status: Literal["PASS", "FAIL", "PRECISION_FLOOR_UNRESOLVED"]


class Task173SuccessResult(StrictModel):
    schema_version: Literal["task173.fixed-geometry-rating-result.v1"]
    status: Literal["VALIDATED"]
    case_revision_id: str
    case_mode: Literal["RATING_FIXED_GEOMETRY"]
    task171_topology_id: str
    task171_result_hash: str
    task171_mesh_identity: str
    physical_ownership_hash: str
    task031_geometry_id: str
    task031_geometry_hash: str
    task031_request_hash: str
    task032_result_id: str
    task032_result_hash: str
    task032_request_hash: str
    task166_result_id: str
    task166_result_hash: str
    task166_request_hash: str
    task172_implementation_version: str
    task174_result_id: str
    task174_result_hash: str
    property_profile_id: str
    reconstruction_authority_id: str
    reconstruction_authority_hash: str
    cell_root_solver_authority_id: str
    cell_root_solver_authority_hash: str
    outer_solver_authority_id: str
    outer_solver_authority_hash: str
    outer_low_endpoint_class: Literal["LOW_SIDE_DOMAIN_INFEASIBLE"]
    outer_high_endpoint_class: Literal["VALID_TRAJECTORY"]
    invalid_low_endpoint_used_as_physical_result: Literal[False]
    production_mesh_profile_authority_id: str
    production_mesh_identity: str
    accepted_subdivisions_per_interval: int
    accepted_tube_cell_count: int
    accepted_shell_cell_count: int
    accepted_total_numerical_cell_count: int
    accepted_wall_interface_count: int
    headroom_subdivisions_per_interval: int
    total_duty_w: Decimal
    tube_outlet_temperature_k: Decimal
    shell_outlet_temperature_k: Decimal
    tube_outlet_pressure_pa: Decimal
    shell_outlet_pressure_pa: Decimal
    hot_energy_loss_w: Decimal
    cold_energy_gain_w: Decimal
    wall_duty_sum_w: Decimal
    energy_balance_residual_w: Decimal
    energy_balance_pass: Literal[True]
    terminal_boundary_residual_k: Decimal
    terminal_boundary_residual_j_kg: Decimal
    shell_outlet_shooting_enthalpy_j_kg: Decimal
    outer_bisection_iterations: int
    minimum_approach_temperature_k: Decimal
    wall_inner_min_k: Decimal
    wall_inner_max_k: Decimal
    wall_outer_min_k: Decimal
    wall_outer_max_k: Decimal
    inlet_and_outlet_face_states: tuple[FaceState, ...]
    accepted_mesh_face_states: tuple[FaceState, ...]
    accepted_mesh_cells: tuple[RatedCell, ...]
    mesh_levels: tuple[MeshObservables, ...]
    convergence_comparisons: tuple[ConvergenceComparison, ...]
    duty_convergence_pass: Literal[True]
    wall_extrema_convergence_pass: Literal[True]
    consecutive_pair_rule_pass: Literal[True]
    headroom_rule_pass: Literal[True]
    precision_floor_status: Literal["RESOLVED_PASS"]
    real_case_mesh_admissible: Literal[True]
    sizing_execution_status: Literal["NOT_APPLICABLE_CURRENT_REFERENCE_CASE"]
    legacy_task163_diagnostic_status: Literal[
        "NOT_APPLICABLE_TO_V07_VARIABLE_LOCAL_CONSTITUTIVE_MODEL"
    ]
    request_hash: str
    result_hash: str
    result_id: str
    provenance: dict[str, str]
    warnings: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()


class Task173BlockedResult(StrictModel):
    schema_version: Literal["task173.fixed-geometry-rating-blocked.v1"]
    status: Literal["BLOCKED"]
    failure_code: str
    failed_mesh_subdivisions: int | None
    request_hash: str | None
    diagnostics: tuple[str, ...]
    result_hash: str
    result_id: str


Task173Outcome = Task173SuccessResult | Task173BlockedResult


__all__ = [
    "ConvergenceComparison",
    "CELL_ROOT_SOLVER_AUTHORITY_ID",
    "ENDPOINT_HOLE_LOW_SIDE_CLASSIFICATION_AUTHORITY_ID",
    "FaceState",
    "H_MAX_J_KG",
    "H_MIN_J_KG",
    "LOCAL_STATE_RECONSTRUCTION_AUTHORITY_ID",
    "MAX_OUTER_BISECTION_ITERATIONS",
    "MeshObservables",
    "OUTER_BOUNDARY_SOLVER_AUTHORITY_ID",
    "PRODUCTION_MESH_PROFILE_AUTHORITY_ID",
    "PropertySnapshot",
    "REVIEWED_MESH_SEQUENCE",
    "RatedCell",
    "REFERENCE_PRESSURE_PA",
    "T_MAX_K",
    "T_MIN_K",
    "Task173BlockedResult",
    "Task173Outcome",
    "Task173Request",
    "Task173SuccessResult",
]
