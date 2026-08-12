"""TASK-029 frozen schema constants and field-order tuples.

I01 scope: namespaces, schema versions, field-order tuples, and frozen constants
only. Framing primitives and kind-tag maps are owned by later slices.
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# §2 — Frozen engineering constants
# ---------------------------------------------------------------------------

IMPLEMENTATION_SOFTWARE_VERSION: Final[str] = "0.2.0-dev"
TASK029_DECIMAL_PRECISION: Final[int] = 28
TASK029_ROUNDING_MODE: Final[str] = "ROUND_HALF_EVEN"
TASK029_PRESSURE_QUANTUM_PA: Final[str] = "0.001"
TASK029_PRESSURE_UNIT: Final[str] = "Pa"
TASK029_PUBLIC_TOTAL_FIELD: Final[str] = "modeled_total_tube_side_pressure_drop_pa"
TASK029_FORBIDDEN_UNCONDITIONAL_TOTAL_FIELD: Final[str] = "total_tube_side_pressure_drop_pa"
TASK027_COMPOSED_PRESSURE_FIELD: Final[str] = "straight_tube_friction_pressure_drop_pa"
TASK028_COMPOSED_PRESSURE_FIELD: Final[str] = "component_irreversible_pressure_loss_pa"
TASK029_TASK027_BRANCH_AUTHORITY_HASH_SENTINEL: Final[str] = ""

TASK029_DESIGN_CONTRACT_PATH: Final[str] = (
    "docs/tasks/TASK-029-shell-and-tube-tube-side-modeled-total-pressure-drop-composition.md"
)

SUPPORTED_PROFILE_IDS: Final[tuple[str, ...]] = ("profile-001",)

TASK027_ACCEPTED_SCHEMA_VERSION: Final[str] = "task027-r1.schema.v1"
TASK028_ACCEPTED_SCHEMA_VERSION: Final[str] = "task028.success-result.v1"

# ---------------------------------------------------------------------------
# §3 — Schema versions / record namespaces
# ---------------------------------------------------------------------------

MEMBER_AUTHORITY_SCHEMA_VERSION: Final[str] = "task029.pressure-path-member-authority.v1"
EXCLUSION_AUTHORITY_SCHEMA_VERSION: Final[str] = "task029.pressure-path-exclusion-authority.v1"
COMPOSITION_AUTHORITY_SCHEMA_VERSION: Final[str] = "task029.pressure-path-composition-authority.v1"
TASK029_REQUEST_SCHEMA_VERSION: Final[str] = "task029.request.v1"
LEDGER_MEMBER_EVIDENCE_SCHEMA_VERSION: Final[str] = "task029.ledger-member-evidence.v1"
LEDGER_EXCLUSION_EVIDENCE_SCHEMA_VERSION: Final[str] = "task029.ledger-exclusion-evidence.v1"
COMPLETENESS_LEDGER_SCHEMA_VERSION: Final[str] = "task029.completeness-ledger.v1"
TASK029_SUCCESS_RESULT_SCHEMA_VERSION: Final[str] = "task029.success-result.v1"
TASK029_BLOCKED_RESULT_SCHEMA_VERSION: Final[str] = "task029.blocked-result.v1"
TASK029_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION: Final[str] = "task029.raw-boundary-blocked-result.v1"
RAW_PROJECTION_SCHEMA_VERSION: Final[str] = "task029.raw-projection.v1"
BLOCKER_ENTRY_SCHEMA_VERSION: Final[str] = "task029.blocker-entry.v1"
PROVENANCE_SCHEMA_VERSION: Final[str] = "task029.provenance.v1"

# ---------------------------------------------------------------------------
# §11 — Hash / identity namespaces (constants only; framing in later slices)
# ---------------------------------------------------------------------------

MEMBER_AUTHORITY_HASH_NAMESPACE: Final[str] = MEMBER_AUTHORITY_SCHEMA_VERSION
EXCLUSION_AUTHORITY_HASH_NAMESPACE: Final[str] = EXCLUSION_AUTHORITY_SCHEMA_VERSION
COMPOSITION_AUTHORITY_HASH_NAMESPACE: Final[str] = COMPOSITION_AUTHORITY_SCHEMA_VERSION
REQUEST_HASH_NAMESPACE: Final[str] = TASK029_REQUEST_SCHEMA_VERSION
LEDGER_HASH_NAMESPACE: Final[str] = COMPLETENESS_LEDGER_SCHEMA_VERSION
SUCCESS_RESULT_HASH_NAMESPACE: Final[str] = TASK029_SUCCESS_RESULT_SCHEMA_VERSION
BLOCKED_RESULT_HASH_NAMESPACE: Final[str] = TASK029_BLOCKED_RESULT_SCHEMA_VERSION
RAW_BOUNDARY_BLOCKED_HASH_NAMESPACE: Final[str] = TASK029_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION
RAW_PROJECTION_NAMESPACE: Final[str] = RAW_PROJECTION_SCHEMA_VERSION
PROVENANCE_NAMESPACE: Final[str] = PROVENANCE_SCHEMA_VERSION
BLOCKER_ENTRY_NAMESPACE: Final[str] = BLOCKER_ENTRY_SCHEMA_VERSION

RESULT_ID_NAMESPACE: Final[str] = "a0290000-0000-5000-8000-000000000001"
RESULT_ID_NAME_PREFIX: Final[str] = "task029-result-v1::"

# ---------------------------------------------------------------------------
# §3.11 / §12 — Raw projection kinds
# ---------------------------------------------------------------------------

RAW_REQUEST_PROJECTION_KIND: Final[str] = "task029.raw-request"
UPSTREAM_BLOCKED_SET_PROJECTION_KIND: Final[str] = "task029.upstream-blocked-set"

# ---------------------------------------------------------------------------
# §3.14 — Deferred capabilities (frozen tuple)
# ---------------------------------------------------------------------------

TASK029_DEFERRED_CAPABILITIES_V1: Final[tuple[str, ...]] = (
    "STATIC_HEAD_NOT_MODELED",
    "ACCELERATION_PRESSURE_DROP_NOT_MODELED",
    "COMPRESSIBLE_PATH_INTEGRATION_NOT_MODELED",
    "SHELL_SIDE_PRESSURE_DROP_NOT_MODELED",
    "EXCLUDED_TASK028_COMPONENT_TYPES_NOT_MODELED",
    "FULL_PHYSICAL_PRESSURE_DROP_COMPLETENESS_NOT_CLAIMED",
)

# ---------------------------------------------------------------------------
# §3.2 — Completeness partition constants
# ---------------------------------------------------------------------------

V0_2_OUT_OF_SCOPE_REQUIRED_EXCLUSIONS: Final[tuple[str, ...]] = (
    "PASS_PARTITION",
    "RETURN_HEADER",
    "RETURN_BEND",
    "U_BEND",
)

TASK028_IN_SCOPE_COMPONENT_TYPES: Final[tuple[str, ...]] = (
    "ENTRANCE",
    "EXIT",
    "CHANNEL_HEAD",
    "NOZZLE",
    "CONTRACTION",
    "EXPANSION",
)

BLOCKER_REGISTRY_COUNT: Final[int] = 43

# ---------------------------------------------------------------------------
# §3 — Field-order tuples and counts
# ---------------------------------------------------------------------------

MEMBER_AUTHORITY_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "member_id",
    "global_path_sequence_index",
    "producer_task",
    "producer_member_kind",
    "producer_component_identity",
    "expected_producer_component_type",
    "expected_producer_authority_hash",
    "expected_upstream_reference_plane",
    "expected_downstream_reference_plane",
    "expected_multiplicity",
    "geometry_evidence_refs",
    "member_authority_hash",
)
MEMBER_AUTHORITY_FIELD_COUNT: Final[int] = 13

EXCLUSION_AUTHORITY_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "exclusion_id",
    "excluded_item_identity",
    "exclusion_reason",
    "evidence_refs",
    "exclusion_authority_hash",
)
EXCLUSION_AUTHORITY_FIELD_COUNT: Final[int] = 6

COMPOSITION_AUTHORITY_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "modeled_path_id",
    "flow_direction_assertion",
    "start_reference_plane",
    "end_reference_plane",
    "member_authorities",
    "exclusion_authorities",
    "geometry_evidence_refs",
    "composition_authority_hash",
)
COMPOSITION_AUTHORITY_FIELD_COUNT: Final[int] = 9

TASK029_REQUEST_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "task027_success_result",
    "task028_success_result",
    "composition_authority",
    "request_hash",
)
TASK029_REQUEST_FIELD_COUNT: Final[int] = 6

REQUEST_HASH_SEMANTIC_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "task027_result_hash",
    "task028_result_hash",
    "task025_hydraulic_authority_hash",
    "task025_result_hash",
    "task026_result_hash",
    "property_snapshot_hash",
    "composition_authority_hash",
)
REQUEST_HASH_SEMANTIC_FIELD_COUNT: Final[int] = 9

LEDGER_MEMBER_EVIDENCE_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "member_id",
    "global_path_sequence_index",
    "producer_task",
    "producer_result_hash",
    "producer_member_kind",
    "producer_component_identity",
    "producer_component_type",
    "producer_authority_hash",
    "upstream_reference_plane",
    "downstream_reference_plane",
    "expected_multiplicity",
    "observed_multiplicity",
    "pressure_contribution_pa",
    "composition_member_authority_hash",
    "member_status",
)
LEDGER_MEMBER_EVIDENCE_FIELD_COUNT: Final[int] = 16

LEDGER_EXCLUSION_EVIDENCE_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "exclusion_id",
    "excluded_item_identity",
    "exclusion_reason",
    "evidence_refs",
    "exclusion_authority_hash",
    "exclusion_status",
)
LEDGER_EXCLUSION_EVIDENCE_FIELD_COUNT: Final[int] = 7

COMPLETENESS_LEDGER_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "modeled_path_id",
    "modeled_start_reference_plane",
    "modeled_end_reference_plane",
    "expected_member_count",
    "observed_member_count",
    "ordered_member_evidence",
    "ordered_exclusion_evidence",
    "path_continuity_status",
    "identity_compatibility_status",
    "completeness_status",
    "ledger_hash",
)
COMPLETENESS_LEDGER_FIELD_COUNT: Final[int] = 12

TASK029_SUCCESS_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "request_hash",
    "result_hash",
    "result_id",
    "task027_result_hash",
    "task028_result_hash",
    "task025_hydraulic_authority_hash",
    "task025_result_hash",
    "task026_result_hash",
    "property_snapshot_hash",
    "composition_authority_hash",
    "completeness_ledger",
    "modeled_total_tube_side_pressure_drop_pa",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "provenance",
)
TASK029_SUCCESS_RESULT_FIELD_COUNT: Final[int] = 18

TASK029_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "request_hash",
    "result_hash",
    "result_id",
    "task027_result_hash",
    "task028_result_hash",
    "task025_hydraulic_authority_hash",
    "task025_result_hash",
    "task026_result_hash",
    "property_snapshot_hash",
    "composition_authority_hash",
    "raw_request_projection",
    "raw_upstream_blocked_projection",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "provenance",
)
TASK029_BLOCKED_RESULT_FIELD_COUNT: Final[int] = 18

TASK029_RAW_BOUNDARY_BLOCKED_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "implementation_software_version",
    "raw_request_projection",
    "blockers",
    "warnings",
    "deferred_capabilities",
)
TASK029_RAW_BOUNDARY_BLOCKED_FIELD_COUNT: Final[int] = 6

RAW_PROJECTION_FIELDS: Final[tuple[str, ...]] = (
    "projection_kind",
    "canonical_bytes_hex",
)
RAW_PROJECTION_FIELD_COUNT: Final[int] = 2

BLOCKER_ENTRY_FIELDS: Final[tuple[str, ...]] = (
    "code",
    "field_path",
    "message_key",
    "evidence_refs",
)
BLOCKER_ENTRY_FIELD_COUNT: Final[int] = 4

PROVENANCE_FIELDS: Final[tuple[str, ...]] = (
    "task_id",
    "design_contract_path",
    "implementation_software_version",
    "input_evidence_refs",
    "upstream_identity_hashes",
)
PROVENANCE_FIELD_COUNT: Final[int] = 5

SUCCESS_PROVENANCE_UPSTREAM_HASH_ORDER: Final[tuple[str, ...]] = (
    "task027_result_hash",
    "task028_result_hash",
    "task025_hydraulic_authority_hash",
    "task025_result_hash",
    "task026_result_hash",
    "property_snapshot_hash",
    "composition_authority_hash",
)

assert len(MEMBER_AUTHORITY_FIELDS) == MEMBER_AUTHORITY_FIELD_COUNT
assert len(EXCLUSION_AUTHORITY_FIELDS) == EXCLUSION_AUTHORITY_FIELD_COUNT
assert len(COMPOSITION_AUTHORITY_FIELDS) == COMPOSITION_AUTHORITY_FIELD_COUNT
assert len(TASK029_REQUEST_FIELDS) == TASK029_REQUEST_FIELD_COUNT
assert len(REQUEST_HASH_SEMANTIC_FIELDS) == REQUEST_HASH_SEMANTIC_FIELD_COUNT
assert len(LEDGER_MEMBER_EVIDENCE_FIELDS) == LEDGER_MEMBER_EVIDENCE_FIELD_COUNT
assert len(LEDGER_EXCLUSION_EVIDENCE_FIELDS) == LEDGER_EXCLUSION_EVIDENCE_FIELD_COUNT
assert len(COMPLETENESS_LEDGER_FIELDS) == COMPLETENESS_LEDGER_FIELD_COUNT
assert len(TASK029_SUCCESS_RESULT_FIELDS) == TASK029_SUCCESS_RESULT_FIELD_COUNT
assert len(TASK029_BLOCKED_RESULT_FIELDS) == TASK029_BLOCKED_RESULT_FIELD_COUNT
assert len(TASK029_RAW_BOUNDARY_BLOCKED_FIELDS) == TASK029_RAW_BOUNDARY_BLOCKED_FIELD_COUNT
assert len(RAW_PROJECTION_FIELDS) == RAW_PROJECTION_FIELD_COUNT
assert len(BLOCKER_ENTRY_FIELDS) == BLOCKER_ENTRY_FIELD_COUNT
assert len(PROVENANCE_FIELDS) == PROVENANCE_FIELD_COUNT

__all__ = [
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "TASK029_DECIMAL_PRECISION",
    "TASK029_ROUNDING_MODE",
    "TASK029_PRESSURE_QUANTUM_PA",
    "TASK029_PRESSURE_UNIT",
    "TASK029_PUBLIC_TOTAL_FIELD",
    "TASK029_FORBIDDEN_UNCONDITIONAL_TOTAL_FIELD",
    "TASK027_COMPOSED_PRESSURE_FIELD",
    "TASK028_COMPOSED_PRESSURE_FIELD",
    "TASK029_TASK027_BRANCH_AUTHORITY_HASH_SENTINEL",
    "TASK029_DESIGN_CONTRACT_PATH",
    "SUPPORTED_PROFILE_IDS",
    "TASK027_ACCEPTED_SCHEMA_VERSION",
    "TASK028_ACCEPTED_SCHEMA_VERSION",
    "MEMBER_AUTHORITY_SCHEMA_VERSION",
    "EXCLUSION_AUTHORITY_SCHEMA_VERSION",
    "COMPOSITION_AUTHORITY_SCHEMA_VERSION",
    "TASK029_REQUEST_SCHEMA_VERSION",
    "LEDGER_MEMBER_EVIDENCE_SCHEMA_VERSION",
    "LEDGER_EXCLUSION_EVIDENCE_SCHEMA_VERSION",
    "COMPLETENESS_LEDGER_SCHEMA_VERSION",
    "TASK029_SUCCESS_RESULT_SCHEMA_VERSION",
    "TASK029_BLOCKED_RESULT_SCHEMA_VERSION",
    "TASK029_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION",
    "RAW_PROJECTION_SCHEMA_VERSION",
    "BLOCKER_ENTRY_SCHEMA_VERSION",
    "PROVENANCE_SCHEMA_VERSION",
    "MEMBER_AUTHORITY_HASH_NAMESPACE",
    "EXCLUSION_AUTHORITY_HASH_NAMESPACE",
    "COMPOSITION_AUTHORITY_HASH_NAMESPACE",
    "REQUEST_HASH_NAMESPACE",
    "LEDGER_HASH_NAMESPACE",
    "SUCCESS_RESULT_HASH_NAMESPACE",
    "BLOCKED_RESULT_HASH_NAMESPACE",
    "RAW_BOUNDARY_BLOCKED_HASH_NAMESPACE",
    "RAW_PROJECTION_NAMESPACE",
    "PROVENANCE_NAMESPACE",
    "BLOCKER_ENTRY_NAMESPACE",
    "RESULT_ID_NAMESPACE",
    "RESULT_ID_NAME_PREFIX",
    "RAW_REQUEST_PROJECTION_KIND",
    "UPSTREAM_BLOCKED_SET_PROJECTION_KIND",
    "TASK029_DEFERRED_CAPABILITIES_V1",
    "V0_2_OUT_OF_SCOPE_REQUIRED_EXCLUSIONS",
    "TASK028_IN_SCOPE_COMPONENT_TYPES",
    "BLOCKER_REGISTRY_COUNT",
    "MEMBER_AUTHORITY_FIELDS",
    "MEMBER_AUTHORITY_FIELD_COUNT",
    "EXCLUSION_AUTHORITY_FIELDS",
    "EXCLUSION_AUTHORITY_FIELD_COUNT",
    "COMPOSITION_AUTHORITY_FIELDS",
    "COMPOSITION_AUTHORITY_FIELD_COUNT",
    "TASK029_REQUEST_FIELDS",
    "TASK029_REQUEST_FIELD_COUNT",
    "REQUEST_HASH_SEMANTIC_FIELDS",
    "REQUEST_HASH_SEMANTIC_FIELD_COUNT",
    "LEDGER_MEMBER_EVIDENCE_FIELDS",
    "LEDGER_MEMBER_EVIDENCE_FIELD_COUNT",
    "LEDGER_EXCLUSION_EVIDENCE_FIELDS",
    "LEDGER_EXCLUSION_EVIDENCE_FIELD_COUNT",
    "COMPLETENESS_LEDGER_FIELDS",
    "COMPLETENESS_LEDGER_FIELD_COUNT",
    "TASK029_SUCCESS_RESULT_FIELDS",
    "TASK029_SUCCESS_RESULT_FIELD_COUNT",
    "TASK029_BLOCKED_RESULT_FIELDS",
    "TASK029_BLOCKED_RESULT_FIELD_COUNT",
    "TASK029_RAW_BOUNDARY_BLOCKED_FIELDS",
    "TASK029_RAW_BOUNDARY_BLOCKED_FIELD_COUNT",
    "RAW_PROJECTION_FIELDS",
    "RAW_PROJECTION_FIELD_COUNT",
    "BLOCKER_ENTRY_FIELDS",
    "BLOCKER_ENTRY_FIELD_COUNT",
    "PROVENANCE_FIELDS",
    "PROVENANCE_FIELD_COUNT",
    "SUCCESS_PROVENANCE_UPSTREAM_HASH_ORDER",
]
