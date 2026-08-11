"""TASK-028 Tube-Side Local/Minor-Loss Component Pressure-Drop.

Package-local export surface only.
"""

from hexagent.exchangers.shell_tube.tube_side_local_loss.blocker_registry import (
    BLOCKER_REGISTRY_COUNT,
    Task028BlockerCode,
    Task028BlockerEntry,
    collapse_blockers,
    emit_blocker,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.canonical import (
    AUTHORITY_HASH_NAMESPACE,
    BLOCKED_RESULT_HASH_NAMESPACE,
    COMPONENT_RESULT_HASH_NAMESPACE,
    IMPLEMENTATION_SOFTWARE_VERSION,
    KIND_DECIMAL,
    KIND_ENUM,
    KIND_INTEGER,
    KIND_NONE,
    KIND_RAW_PROJECTION,
    KIND_RECORD,
    KIND_STRING,
    KIND_TUPLE,
    PROVENANCE_NAMESPACE,
    RAW_BOUNDARY_BLOCKED_HASH_NAMESPACE,
    RAW_PROJECTION_NAMESPACE,
    REQUEST_HASH_NAMESPACE,
    RESULT_ID_NAME_PREFIX,
    RESULT_ID_NAMESPACE,
    SUCCESS_RESULT_HASH_NAMESPACE,
    SUPPORTED_PROFILE_IDS,
    TASK028_BLOCKED_RESULT_SCHEMA_VERSION,
    TASK028_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION,
    TASK028_REQUEST_FIELDS,
    TASK028_REQUEST_SCHEMA_VERSION,
    TASK028_SUCCESS_RESULT_SCHEMA_VERSION,
    )
from hexagent.exchangers.shell_tube.tube_side_local_loss.computation import (
    compute_local_loss_component,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.decimal_identity import (
    LOSS_COEFFICIENT_QUANTUM,
    PRESSURE_LOSS_QUANTUM,
    REFERENCE_FLOW_AREA_QUANTUM,
    REFERENCE_VELOCITY_QUANTUM,
    TASK028_DECIMAL_PRECISION,
    normalize_negative_zero,
    quantize_task028_decimal,
    task028_decimal_context,
    task028_decimal_payload,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.enums import (
    KNOWN_UNSUPPORTED_RAW_COMPONENT_TOKENS,
    CoefficientPermissionStatus,
    LossCoefficientConvention,
    Task028ApplicabilityAssertion,
    Task028ComponentFlowDirectionAssertion,
    Task028ComponentType,
    Task028RequestFlowDirectionAssertion,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.identity import (
    compute_authority_hash,
    compute_blocked_result_hash,
    compute_raw_boundary_blocked_hash,
    compute_request_hash,
    compute_result_id,
    compute_success_result_hash,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.models import (
    AUTHORITY_FIELD_COUNT,
    COMPONENT_RESULT_FIELD_COUNT,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_COEFFICIENT_SEMANTICS,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELD_COUNT,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELDS,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FORMULA,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_ID,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_LOCATION,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_PERMISSION_STATUS,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_SCOPE,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_TITLE,
    TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_VERSION,
    TubeSideLocalLossComponentAuthority,
    TubeSideLocalLossComponentResult,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.pipeline import (
    compute_task028_local_loss,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.raw_boundary import (
    RawBoundaryResult,
    validate_raw_boundary,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.raw_projection import (
    Task028RawProjection,
    canonicalize_raw_value,
    encode_raw_projection,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.request import (
    Task028Request,
    build_task028_request,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
    BLOCKED_RESULT_FIELD_COUNT,
    BLOCKER_ENTRY_FIELD_COUNT,
    PROVENANCE_FIELD_COUNT,
    RAW_BOUNDARY_BLOCKED_FIELD_COUNT,
    SUCCESS_RESULT_FIELD_COUNT,
    Task028BlockedResult,
    Task028Provenance,
    Task028RawBoundaryBlockedResult,
    Task028SuccessResult,
    build_blocked_result,
    build_raw_boundary_blocked_result,
    build_success_result,
)

__all__ = [
    # Enums
    "Task028ComponentType",
    "Task028RequestFlowDirectionAssertion",
    "Task028ComponentFlowDirectionAssertion",
    "LossCoefficientConvention",
    "CoefficientPermissionStatus",
    "Task028ApplicabilityAssertion",
    "KNOWN_UNSUPPORTED_RAW_COMPONENT_TOKENS",
    # Models
    "TubeSideLocalLossComponentAuthority",
    "TubeSideLocalLossComponentResult",
    "AUTHORITY_FIELD_COUNT",
    "COMPONENT_RESULT_FIELD_COUNT",
    # Blocker
    "Task028BlockerCode",
    "Task028BlockerEntry",
    "emit_blocker",
    "collapse_blockers",
    "BLOCKER_REGISTRY_COUNT",
    # Decimal
    "TASK028_DECIMAL_PRECISION",
    "REFERENCE_VELOCITY_QUANTUM",
    "PRESSURE_LOSS_QUANTUM",
    "REFERENCE_FLOW_AREA_QUANTUM",
    "LOSS_COEFFICIENT_QUANTUM",
    "task028_decimal_context",
    "quantize_task028_decimal",
    "normalize_negative_zero",
    "task028_decimal_payload",
    # Canonical
    "KIND_NONE",
    "KIND_STRING",
    "KIND_DECIMAL",
    "KIND_ENUM",
    "KIND_INTEGER",
    "KIND_TUPLE",
    "KIND_RECORD",
    "KIND_RAW_PROJECTION",
    "task028_tuple_payload",
    # Raw projection
    "Task028RawProjection",
    "canonicalize_raw_value",
    "encode_raw_projection",
    # Raw boundary
    "RawBoundaryResult",
    "validate_raw_boundary",
    # Request
    "Task028Request",
    "build_task028_request",
    # Computation
    "compute_local_loss_component",
    # Identity
    "compute_authority_hash",
    "compute_request_hash",
    "compute_success_result_hash",
    "compute_blocked_result_hash",
    "compute_raw_boundary_blocked_hash",
    "compute_result_id",
    # Result
    "Task028Provenance",
    "Task028SuccessResult",
    "Task028BlockedResult",
    "Task028RawBoundaryBlockedResult",
    "SUCCESS_RESULT_FIELD_COUNT",
    "BLOCKED_RESULT_FIELD_COUNT",
    "RAW_BOUNDARY_BLOCKED_FIELD_COUNT",
    "PROVENANCE_FIELD_COUNT",
    "BLOCKER_ENTRY_FIELD_COUNT",
    "build_success_result",
    "build_blocked_result",
    "build_raw_boundary_blocked_result",
    # Pipeline
    "compute_task028_local_loss",
    # Constants
    "TASK028_REQUEST_SCHEMA_VERSION",
    "TASK028_REQUEST_FIELDS",
    "TASK028_SUCCESS_RESULT_SCHEMA_VERSION",
    "TASK028_BLOCKED_RESULT_SCHEMA_VERSION",
    "TASK028_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "SUPPORTED_PROFILE_IDS",
    "RESULT_ID_NAMESPACE",
    "RESULT_ID_NAME_PREFIX",
    "REQUEST_HASH_NAMESPACE",
    "SUCCESS_RESULT_HASH_NAMESPACE",
    "BLOCKED_RESULT_HASH_NAMESPACE",
    "RAW_BOUNDARY_BLOCKED_HASH_NAMESPACE",
    "RAW_PROJECTION_NAMESPACE",
    "PROVENANCE_NAMESPACE",
    "COMPONENT_RESULT_HASH_NAMESPACE",
    "AUTHORITY_HASH_NAMESPACE",
    # Source authority
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELDS",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FIELD_COUNT",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_ID",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_TITLE",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_VERSION",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_LOCATION",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_SCOPE",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_FORMULA",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_COEFFICIENT_SEMANTICS",
    "TASK028_LOCAL_LOSS_SOURCE_AUTHORITY_PERMISSION_STATUS",
]
