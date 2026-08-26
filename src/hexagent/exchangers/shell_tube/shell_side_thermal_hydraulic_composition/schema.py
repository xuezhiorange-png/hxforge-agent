"""Frozen structural contract for TASK-035.

This module contains only closed, ordered contract data.  The composition
implementation deliberately does not import any of the upstream producer
packages: producer evidence is validated structurally at the public mapping
boundary instead.
"""

# Contract paths and registry rows are intentionally kept as exact strings.
# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

TASK_ID: Final = "TASK035"
PUBLIC_OPERATION: Final = "validate_request"

REQUEST_SCHEMA_VERSION: Final = "task035.shell-side-thermal-hydraulic-composition-request.v1"
RESULT_SCHEMA_VERSION: Final = "task035.shell-side-thermal-hydraulic-composition.v1"
BLOCKED_RESULT_SCHEMA_VERSION: Final = "task035.shell-side-thermal-hydraulic-composition-blocked.v1"
RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION: Final = (
    "task035.shell-side-thermal-hydraulic-composition-raw-boundary-blocked.v1"
)
PROFILE_ID: Final = "hxforge.shell_tube.shell_side_thermal_hydraulic_composition.v1"
FIRST_SLICE_PROFILE_ID: Final = (
    "SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_KERN_THERMAL_HYDRAULIC_COMPOSITION_V1"
)
IMPLEMENTATION_SOFTWARE_VERSION: Final = "task035.shell-side-thermal-hydraulic-composition-impl-v1"

APPLICABILITY_PROFILE_ID: Final = (
    "hxforge.shell_tube.shell_side_thermal_hydraulic_composition.applicability.v1"
)
COMPLETENESS_PROFILE_ID: Final = (
    "hxforge.shell_tube.shell_side_thermal_hydraulic_composition.completeness.v1"
)

REQUEST_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "task031_result",
    "task032_result",
    "task033_result",
    "task034_result",
    "evidence_refs",
)

SUCCESS_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "first_slice_profile_id",
    "implementation_software_version",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task021_layout_id",
    "task021_layout_hash",
    "task024_geometry_id",
    "task024_geometry_hash",
    "task031_request_hash",
    "task031_geometry_id",
    "task031_geometry_hash",
    "task032_request_hash",
    "task032_result_hash",
    "task032_result_id",
    "task033_request_hash",
    "task033_result_hash",
    "task033_result_id",
    "task034_request_hash",
    "task034_result_hash",
    "task034_result_id",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "task033_correlation_id",
    "task034_correlation_id",
    "heat_transfer_surface",
    "modeled_shell_side_heat_transfer_coefficient_w_m2_k",
    "modeled_shell_side_pressure_drop_pa",
    "applicability_ledger",
    "completeness_ledger",
    "request_hash",
    "result_hash",
    "result_id",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "provenance",
)

TYPED_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "failure_stage",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "task031_geometry_id",
    "task031_geometry_hash",
    "task032_request_hash",
    "task032_result_hash",
    "task032_result_id",
    "task033_result_hash",
    "task033_result_id",
    "task034_result_hash",
    "task034_result_id",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "request_hash",
    "blocked_result_hash",
    "result_id",
    "blockers",
    "warnings",
    "deferred_capabilities",
    "provenance",
)

RAW_BOUNDARY_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "raw_request_projection",
    "blocked_result_hash",
    "blockers",
    "warnings",
    "deferred_capabilities",
)

TASK031_ENVELOPE_FIELDS: Final[tuple[str, ...]] = (
    "status",
    "geometry",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "blocked_result_hash",
)
TASK031_GEOMETRY_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "geometry_id",
    "geometry_hash",
    "request_hash",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task021_layout_id",
    "task021_layout_hash",
    "task022_geometry_id",
    "task022_geometry_hash",
    "task024_geometry_id",
    "task024_geometry_hash",
    "engineering_authority_id",
    "engineering_authority_hash",
    "formula_a_id",
    "formula_b_id",
    "pattern_family",
    "flow_region_identity",
    "central_inter_baffle_spacing_m",
    "central_crossflow_flow_area_m2",
    "shell_side_equivalent_hydraulic_diameter_m",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "provenance",
)

TASK032_ENVELOPE_FIELDS: Final[tuple[str, ...]] = (
    "status",
    "flow_state",
    "blocked_result",
    "raw_boundary_blocked_result",
)
TASK032_SUCCESS_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "engineering_authority_id",
    "engineering_authority_hash",
    "flow_model",
    "phase_region",
    "rheology_model",
    "shell_side_mass_flow_rate_kg_s",
    "shell_side_mass_velocity_kg_m2_s",
    "shell_side_bulk_velocity_m_s",
    "shell_side_reynolds_number",
    "shell_side_prandtl_number",
    "request_hash",
    "result_hash",
    "result_id",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "provenance",
)
TASK032_TYPED_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "failure_stage",
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "request_hash",
    "result_hash",
    "result_id",
    "blockers",
    "warnings",
    "deferred_capabilities",
    "provenance",
)
TASK032_RAW_BOUNDARY_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "raw_request_projection",
    "blocked_result_hash",
    "blockers",
    "warnings",
    "deferred_capabilities",
)

TASK033_ENVELOPE_FIELDS: Final[tuple[str, ...]] = (
    "status",
    "heat_transfer",
    "blocked_result",
    "raw_boundary_blocked_result",
)
TASK033_SUCCESS_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "first_slice_profile_id",
    "implementation_software_version",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "task032_request_hash",
    "task032_result_hash",
    "task032_result_id",
    "correlation_id",
    "engineering_source_authority_record_id",
    "heat_transfer_surface",
    "modeled_shell_side_heat_transfer_coefficient_w_m2_k",
    "request_hash",
    "result_hash",
    "result_id",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "applicability_context",
    "provenance",
)
TASK033_TYPED_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "failure_stage",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "task032_request_hash",
    "task032_result_hash",
    "task032_result_id",
    "request_hash",
    "blocked_result_hash",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "provenance",
)
TASK033_RAW_BOUNDARY_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "request_hash",
    "blocked_result_hash",
    "blockers",
    "warnings",
    "deferred_capabilities",
    "raw_projection",
)

TASK034_ENVELOPE_FIELDS: Final[tuple[str, ...]] = (
    "status",
    "pressure_drop",
    "blocked_result",
    "raw_boundary_blocked_result",
)
TASK034_SUCCESS_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "first_slice_profile_id",
    "implementation_software_version",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task031_request_hash",
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "task032_request_hash",
    "task032_result_hash",
    "task032_result_id",
    "task033_request_hash",
    "task033_result_hash",
    "task033_result_id",
    "correlation_id",
    "engineering_source_authority_record_id",
    "source_id",
    "source_version",
    "source_location",
    "wall_property_schema_version",
    "wall_property_source_id",
    "wall_property_source_version",
    "wall_property_snapshot_hash",
    "wall_property_authority_hash",
    "modeled_shell_side_pressure_drop_pa",
    "request_hash",
    "result_hash",
    "result_id",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "applicability_context",
    "physical_boundary_context",
    "provenance",
)
TASK034_TYPED_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "failure_stage",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task031_request_hash",
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "task032_request_hash",
    "task032_result_hash",
    "task032_result_id",
    "task033_request_hash",
    "task033_result_hash",
    "task033_result_id",
    "wall_property_schema_version",
    "wall_property_source_id",
    "wall_property_source_version",
    "wall_property_snapshot_hash",
    "wall_property_authority_hash",
    "request_hash",
    "blocked_result_hash",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "provenance",
)
TASK034_RAW_BOUNDARY_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "request_hash",
    "blocked_result_hash",
    "blockers",
    "warnings",
    "deferred_capabilities",
    "raw_projection",
)

PRODUCER_ENVELOPE_FIELDS: Final[dict[str, tuple[str, ...]]] = {
    "TASK031": TASK031_ENVELOPE_FIELDS,
    "TASK032": TASK032_ENVELOPE_FIELDS,
    "TASK033": TASK033_ENVELOPE_FIELDS,
    "TASK034": TASK034_ENVELOPE_FIELDS,
}

VALIDATION_STAGES: Final[tuple[tuple[str, str], ...]] = (
    ("S01", "RAW_BOUNDARY"),
    ("S02", "REQUEST_SCHEMA"),
    ("S03", "TASK031_PRODUCER_BOUNDARY"),
    ("S04", "TASK031_IDENTITY_REPLAY"),
    ("S05", "TASK032_PRODUCER_BOUNDARY"),
    ("S06", "TASK032_IDENTITY_REPLAY"),
    ("S07", "TASK033_PRODUCER_BOUNDARY"),
    ("S08", "TASK033_IDENTITY_REPLAY"),
    ("S09", "TASK034_PRODUCER_BOUNDARY"),
    ("S10", "TASK034_IDENTITY_REPLAY"),
    ("S11", "CROSS_PRODUCER_CONFIGURATION_AND_GEOMETRY_JOIN"),
    ("S12", "PROPERTY_AND_MASS_FLOW_IDENTITY_JOIN"),
    ("S13", "CASE_STREAM_FLUID_JOIN"),
    ("S14", "PROFILE_COMPATIBILITY"),
    ("S15", "APPLICABILITY_INTERSECTION"),
    ("S16", "COMPLETENESS_LEDGER"),
    ("S17", "SUCCESS_PAYLOAD_COMPOSITION"),
    ("S18", "PROVENANCE_CANONICALIZATION"),
    ("S19", "RESULT_IDENTITY_FINALIZATION"),
)

SAFE_EVIDENCE_CLASSES: Final[tuple[str, ...]] = (
    "NONE",
    "REQUEST_IDENTITY",
    "TASK031_IDENTITY",
    "TASK031_TASK032_IDENTITY",
    "TASK031_TASK032_TASK033_IDENTITY",
    "ALL_PRODUCER_IDENTITIES",
    "ALL_IDENTITIES_AND_COMPATIBILITY",
)

APPLICABILITY_LEDGER_FIELDS: Final[tuple[str, ...]] = (
    "task031_profile",
    "task032_profile",
    "task033_profile",
    "task034_profile",
    "shared_case_identity",
    "shared_configuration_identity",
    "shared_geometry_identity",
    "shared_property_identity",
    "shared_mass_flow_identity",
    "intersection_status",
)
COMPLETENESS_CLASSIFICATION_UNIVERSE: Final[tuple[str, ...]] = (
    "DELIVERED_AND_PRESENT",
    "DELIVERED_BUT_BLOCKED",
    "NOT_APPLICABLE",
    "DEFERRED_BY_V0_3_SCOPE",
    "OUT_OF_SCOPE",
)
DEFERRED_CAPABILITIES: Final[tuple[str, ...]] = (
    "VERSION_LEVEL_INTEGRATION_DEFERRED_TO_TASK036",
    "DEMONSTRATION_DEFERRED_TO_TASK036",
    "RELEASE_ACCEPTANCE_DEFERRED_TO_TASK036",
)
WARNING_REGISTRY: Final[tuple[str, ...]] = (
    "SSTHC_COMPOSITION_ONLY",
    "SSTHC_APPLICABILITY_INTERSECTION_ONLY",
    "SSTHC_NO_UPSTREAM_ENGINEERING_RECOMPUTATION",
    "SSTHC_NO_FULL_EXCHANGER_RATING_CLAIM",
    "SSTHC_TASK036_RELEASE_ACCEPTANCE_DEFERRED",
)

PROVENANCE_FIELDS: Final[tuple[str, ...]] = (
    "task_id",
    "profile_id",
    "first_slice_profile_id",
    "implementation_software_version",
    "request_hash",
    "task031_request_hash",
    "task031_geometry_hash",
    "task031_geometry_id",
    "task021_layout_hash",
    "task021_layout_id",
    "task024_geometry_hash",
    "task024_geometry_id",
    "task032_request_hash",
    "task032_result_hash",
    "task032_result_id",
    "task033_request_hash",
    "task033_result_hash",
    "task033_result_id",
    "task033_correlation_id",
    "task034_request_hash",
    "task034_result_hash",
    "task034_result_id",
    "task034_correlation_id",
    "task020_configuration_hash",
    "task020_configuration_id",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "applicability_profile_id",
    "completeness_profile_id",
    "producer_edges",
    "warnings",
    "deferred_capabilities",
    "evidence_refs",
    "source_definition_issue",
    "source_definition_correction_chain",
    "provenance_hash",
)
PROVENANCE_PREHASH_FIELDS: Final[tuple[str, ...]] = tuple(
    field for field in PROVENANCE_FIELDS if field != "provenance_hash"
)
SOURCE_DEFINITION_ISSUE: Final[int] = 201
SOURCE_DEFINITION_CORRECTION_CHAIN: Final[tuple[int, ...]] = (
    5410149038,
    5410454707,
    5411050595,
    5411382945,
    5411743935,
    5418782032,
)


@dataclass(frozen=True)
class IdentityJoinRule:
    """One immutable identity relation in the frozen J01-J25 set."""

    rule_id: str
    left_paths: tuple[str, ...]
    right_paths: tuple[str, ...]
    owner_stage: str
    owner_blocker: str


IDENTITY_JOIN_RULES: Final[tuple[IdentityJoinRule, ...]] = (
    IdentityJoinRule(
        "J01",
        ("task034_result.pressure_drop.task033_request_hash",),
        ("task033_result.heat_transfer.request_hash",),
        "S10",
        "SSTHC_TASK034_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J02",
        ("task034_result.pressure_drop.task033_result_hash",),
        ("task033_result.heat_transfer.result_hash",),
        "S10",
        "SSTHC_TASK034_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J03",
        ("task034_result.pressure_drop.task033_result_id",),
        ("task033_result.heat_transfer.result_id",),
        "S10",
        "SSTHC_TASK034_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J04",
        ("task033_result.heat_transfer.task032_request_hash",),
        ("task032_result.flow_state.request_hash",),
        "S08",
        "SSTHC_TASK033_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J05",
        ("task033_result.heat_transfer.task032_result_hash",),
        ("task032_result.flow_state.result_hash",),
        "S08",
        "SSTHC_TASK033_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J06",
        ("task033_result.heat_transfer.task032_result_id",),
        ("task032_result.flow_state.result_id",),
        "S08",
        "SSTHC_TASK033_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J07",
        ("task034_result.pressure_drop.task032_request_hash",),
        ("task032_result.flow_state.request_hash",),
        "S10",
        "SSTHC_TASK034_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J08",
        ("task034_result.pressure_drop.task032_result_hash",),
        ("task032_result.flow_state.result_hash",),
        "S10",
        "SSTHC_TASK034_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J09",
        ("task034_result.pressure_drop.task032_result_id",),
        ("task032_result.flow_state.result_id",),
        "S10",
        "SSTHC_TASK034_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J10",
        ("task034_result.pressure_drop.task031_request_hash",),
        ("task031_result.geometry.request_hash",),
        "S10",
        "SSTHC_TASK034_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J11",
        ("task032_result.flow_state.task031_geometry_id",),
        ("task031_result.geometry.geometry_id",),
        "S06",
        "SSTHC_TASK032_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J12",
        ("task033_result.heat_transfer.task031_geometry_id",),
        ("task031_result.geometry.geometry_id",),
        "S08",
        "SSTHC_TASK033_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J13",
        ("task034_result.pressure_drop.task031_geometry_id",),
        ("task031_result.geometry.geometry_id",),
        "S10",
        "SSTHC_TASK034_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J14",
        ("task032_result.flow_state.task031_geometry_hash",),
        ("task031_result.geometry.geometry_hash",),
        "S06",
        "SSTHC_TASK032_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J15",
        ("task033_result.heat_transfer.task031_geometry_hash",),
        ("task031_result.geometry.geometry_hash",),
        "S08",
        "SSTHC_TASK033_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J16",
        ("task034_result.pressure_drop.task031_geometry_hash",),
        ("task031_result.geometry.geometry_hash",),
        "S10",
        "SSTHC_TASK034_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J17",
        ("all exposed task020_configuration_id values",),
        ("same accepted configuration",),
        "S11",
        "SSTHC_CONFIGURATION_MISMATCH",
    ),
    IdentityJoinRule(
        "J18",
        ("all exposed task020_configuration_hash values",),
        ("same accepted configuration",),
        "S11",
        "SSTHC_CONFIGURATION_MISMATCH",
    ),
    IdentityJoinRule(
        "J19",
        (
            "task032_result.flow_state.property_snapshot_hash",
            "task033_result.heat_transfer.property_snapshot_hash",
            "task034_result.pressure_drop.property_snapshot_hash",
        ),
        ("byte-identical values",),
        "S12",
        "SSTHC_PROPERTY_SNAPSHOT_MISMATCH",
    ),
    IdentityJoinRule(
        "J20",
        (
            "task032_result.flow_state.mass_flow_authority_hash",
            "task033_result.heat_transfer.mass_flow_authority_hash",
            "task034_result.pressure_drop.mass_flow_authority_hash",
        ),
        ("byte-identical values",),
        "S12",
        "SSTHC_MASS_FLOW_AUTHORITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J21",
        (
            "task032_result.flow_state.shell_side_case_id",
            "task033_result.heat_transfer.shell_side_case_id",
            "task034_result.pressure_drop.shell_side_case_id",
        ),
        ("byte-identical values",),
        "S13",
        "SSTHC_CASE_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J22",
        (
            "task032_result.flow_state.shell_side_stream_id",
            "task033_result.heat_transfer.shell_side_stream_id",
            "task034_result.pressure_drop.shell_side_stream_id",
        ),
        ("byte-identical values",),
        "S13",
        "SSTHC_STREAM_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J23",
        (
            "task032_result.flow_state.shell_side_fluid_id",
            "task033_result.heat_transfer.shell_side_fluid_id",
            "task034_result.pressure_drop.shell_side_fluid_id",
        ),
        ("byte-identical values",),
        "S13",
        "SSTHC_FLUID_IDENTITY_MISMATCH",
    ),
    IdentityJoinRule(
        "J24",
        (
            "task031_result.geometry.task021_layout_id",
            "task031_result.geometry.task021_layout_hash",
        ),
        ("accepted TASK031 ancestry",),
        "S11",
        "SSTHC_TASK021_LAYOUT_MISMATCH",
    ),
    IdentityJoinRule(
        "J25",
        (
            "task031_result.geometry.task024_geometry_id",
            "task031_result.geometry.task024_geometry_hash",
        ),
        ("accepted TASK031 ancestry",),
        "S11",
        "SSTHC_TASK024_GEOMETRY_MISMATCH",
    ),
)

BLOCKER_CODES: Final[tuple[str, ...]] = (
    "SSTHC_RAW_TYPE_INVALID",
    "SSTHC_UNKNOWN_FIELD",
    "SSTHC_EVIDENCE_REFS_INVALID",
    "SSTHC_SCHEMA_VERSION_UNSUPPORTED",
    "SSTHC_PROFILE_ID_UNSUPPORTED",
    "SSTHC_REQUIRED_FIELD_MISSING",
    "SSTHC_TASK031_RESULT_MISSING",
    "SSTHC_TASK031_RESULT_INVALID",
    "SSTHC_TASK031_RESULT_BLOCKED",
    "SSTHC_TASK031_IDENTITY_MISMATCH",
    "SSTHC_TASK032_RESULT_MISSING",
    "SSTHC_TASK032_RESULT_INVALID",
    "SSTHC_TASK032_RESULT_BLOCKED",
    "SSTHC_TASK032_IDENTITY_MISMATCH",
    "SSTHC_TASK033_RESULT_MISSING",
    "SSTHC_TASK033_RESULT_INVALID",
    "SSTHC_TASK033_RESULT_BLOCKED",
    "SSTHC_TASK033_IDENTITY_MISMATCH",
    "SSTHC_TASK034_RESULT_MISSING",
    "SSTHC_TASK034_RESULT_INVALID",
    "SSTHC_TASK034_RESULT_BLOCKED",
    "SSTHC_TASK034_IDENTITY_MISMATCH",
    "SSTHC_CONFIGURATION_MISMATCH",
    "SSTHC_TASK021_LAYOUT_MISMATCH",
    "SSTHC_TASK024_GEOMETRY_MISMATCH",
    "SSTHC_TASK031_GEOMETRY_MISMATCH",
    "SSTHC_PROPERTY_SNAPSHOT_MISMATCH",
    "SSTHC_MASS_FLOW_AUTHORITY_MISMATCH",
    "SSTHC_CASE_IDENTITY_MISMATCH",
    "SSTHC_STREAM_IDENTITY_MISMATCH",
    "SSTHC_FLUID_IDENTITY_MISMATCH",
    "SSTHC_PROFILE_COMPATIBILITY_MISMATCH",
    "SSTHC_HEAT_TRANSFER_SURFACE_MISMATCH",
    "SSTHC_CORRELATION_IDENTITY_MISMATCH",
    "SSTHC_APPLICABILITY_INCOMPATIBLE",
    "SSTHC_REQUIRED_CAPABILITY_MISSING",
    "SSTHC_REQUIRED_PRODUCER_NOT_DELIVERED",
    "SSTHC_SUCCESS_PAYLOAD_COMPOSITION_FAILED",
    "SSTHC_PARTIAL_SUCCESS_FORBIDDEN",
    "SSTHC_PROVENANCE_CANONICALIZATION_FAILED",
    "SSTHC_CANONICALIZATION_FAILED",
    "SSTHC_RESULT_IDENTITY_FINALIZATION_FAILED",
)

REQUEST_FIELD_COUNT: Final = len(REQUEST_FIELDS)
SUCCESS_FIELD_COUNT: Final = len(SUCCESS_RESULT_FIELDS)
TYPED_BLOCKED_FIELD_COUNT: Final = len(TYPED_BLOCKED_RESULT_FIELDS)
RAW_BOUNDARY_BLOCKED_FIELD_COUNT: Final = len(RAW_BOUNDARY_BLOCKED_RESULT_FIELDS)
IDENTITY_JOIN_RULE_COUNT: Final = len(IDENTITY_JOIN_RULES)
VALIDATION_STAGE_COUNT: Final = len(VALIDATION_STAGES)
BLOCKER_COUNT: Final = len(BLOCKER_CODES)
BLOCKER_REACHABILITY_ROW_COUNT: Final = BLOCKER_COUNT
PRIMARY_TEST_ID_COUNT: Final = 22
PROVENANCE_FIELD_COUNT: Final = len(PROVENANCE_FIELDS)
PROVENANCE_PREHASH_FIELD_COUNT: Final = len(PROVENANCE_PREHASH_FIELDS)
PRODUCER_ENVELOPE_COUNT: Final = len(PRODUCER_ENVELOPE_FIELDS)
PROVENANCE_PRODUCER_EDGE_COUNT: Final = 4
SELF_EDGE_COUNT: Final = 0
WARNING_COUNT: Final = len(WARNING_REGISTRY)
DEFERRED_CAPABILITY_COUNT: Final = len(DEFERRED_CAPABILITIES)
COMPLETENESS_CLASSIFICATION_COUNT: Final = len(COMPLETENESS_CLASSIFICATION_UNIVERSE)

assert REQUEST_FIELD_COUNT == 7
assert SUCCESS_FIELD_COUNT == 41
assert TYPED_BLOCKED_FIELD_COUNT == 25
assert RAW_BOUNDARY_BLOCKED_FIELD_COUNT == 8
assert IDENTITY_JOIN_RULE_COUNT == 25
assert VALIDATION_STAGE_COUNT == 19
assert BLOCKER_COUNT == 42
assert PROVENANCE_FIELD_COUNT == 36
assert PROVENANCE_PREHASH_FIELD_COUNT == 35
assert PRODUCER_ENVELOPE_COUNT == 4
assert PROVENANCE_PRODUCER_EDGE_COUNT == 4
assert SELF_EDGE_COUNT == 0
assert WARNING_COUNT == 5
assert DEFERRED_CAPABILITY_COUNT == 3
assert COMPLETENESS_CLASSIFICATION_COUNT == 5

# Compatibility aliases used by tests and downstream design tooling.
TASK035_REQUEST_FIELDS = REQUEST_FIELDS
TASK035_SUCCESS_FIELDS = SUCCESS_RESULT_FIELDS
TASK035_TYPED_BLOCKED_FIELDS = TYPED_BLOCKED_RESULT_FIELDS
TASK035_RAW_BOUNDARY_BLOCKED_FIELDS = RAW_BOUNDARY_BLOCKED_RESULT_FIELDS
J_RULES = IDENTITY_JOIN_RULES


__all__ = [
    "APPLICABILITY_LEDGER_FIELDS",
    "APPLICABILITY_PROFILE_ID",
    "BLOCKED_RESULT_SCHEMA_VERSION",
    "BLOCKER_CODES",
    "BLOCKER_COUNT",
    "BLOCKER_REACHABILITY_ROW_COUNT",
    "COMPLETENESS_CLASSIFICATION_COUNT",
    "COMPLETENESS_CLASSIFICATION_UNIVERSE",
    "COMPLETENESS_PROFILE_ID",
    "DEFERRED_CAPABILITIES",
    "DEFERRED_CAPABILITY_COUNT",
    "FIRST_SLICE_PROFILE_ID",
    "IDENTITY_JOIN_RULES",
    "IDENTITY_JOIN_RULE_COUNT",
    "IdentityJoinRule",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "J_RULES",
    "PRIMARY_TEST_ID_COUNT",
    "PRODUCER_ENVELOPE_COUNT",
    "PRODUCER_ENVELOPE_FIELDS",
    "PROVENANCE_FIELDS",
    "PROVENANCE_FIELD_COUNT",
    "PROVENANCE_PREHASH_FIELDS",
    "PROVENANCE_PREHASH_FIELD_COUNT",
    "PROVENANCE_PRODUCER_EDGE_COUNT",
    "PUBLIC_OPERATION",
    "PROFILE_ID",
    "RAW_BOUNDARY_BLOCKED_RESULT_FIELDS",
    "RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION",
    "RAW_BOUNDARY_BLOCKED_FIELD_COUNT",
    "REQUEST_FIELDS",
    "REQUEST_FIELD_COUNT",
    "REQUEST_SCHEMA_VERSION",
    "RESULT_SCHEMA_VERSION",
    "SAFE_EVIDENCE_CLASSES",
    "SELF_EDGE_COUNT",
    "SUCCESS_RESULT_FIELDS",
    "SUCCESS_FIELD_COUNT",
    "TASK031_ENVELOPE_FIELDS",
    "TASK031_GEOMETRY_FIELDS",
    "TASK032_ENVELOPE_FIELDS",
    "TASK032_RAW_BOUNDARY_BLOCKED_RESULT_FIELDS",
    "TASK032_SUCCESS_RESULT_FIELDS",
    "TASK032_TYPED_BLOCKED_RESULT_FIELDS",
    "TASK033_ENVELOPE_FIELDS",
    "TASK033_RAW_BOUNDARY_BLOCKED_RESULT_FIELDS",
    "TASK033_SUCCESS_RESULT_FIELDS",
    "TASK033_TYPED_BLOCKED_RESULT_FIELDS",
    "TASK034_ENVELOPE_FIELDS",
    "TASK034_RAW_BOUNDARY_BLOCKED_RESULT_FIELDS",
    "TASK034_SUCCESS_RESULT_FIELDS",
    "TASK034_TYPED_BLOCKED_RESULT_FIELDS",
    "TASK035_RAW_BOUNDARY_BLOCKED_FIELDS",
    "TASK035_REQUEST_FIELDS",
    "TASK035_SUCCESS_FIELDS",
    "TASK035_TYPED_BLOCKED_FIELDS",
    "TASK_ID",
    "TYPED_BLOCKED_RESULT_FIELDS",
    "TYPED_BLOCKED_FIELD_COUNT",
    "VALIDATION_STAGES",
    "VALIDATION_STAGE_COUNT",
    "WARNING_COUNT",
    "WARNING_REGISTRY",
]
