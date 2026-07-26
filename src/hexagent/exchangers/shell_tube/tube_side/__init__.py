"""TASK-025 public re-export boundary.

§14 — Public TASK-025 types and A01 re-exports.
"""

from __future__ import annotations

from hexagent.exchangers.shell_tube.tube_side import (
    blocked_result as _blocked_result,
)
from hexagent.exchangers.shell_tube.tube_side import (
    blocker_registry as _blocker_registry,
)
from hexagent.exchangers.shell_tube.tube_side import (
    canonical as _canonical,
)
from hexagent.exchangers.shell_tube.tube_side import (
    decimal_identity as _decimal_identity,
)
from hexagent.exchangers.shell_tube.tube_side import (
    hash_dag as _hash_dag,
)
from hexagent.exchangers.shell_tube.tube_side import (
    hydraulic_geometry as _hydraulic_geometry,
)
from hexagent.exchangers.shell_tube.tube_side import (
    hydraulic_participation_authority as _hydraulic_participation_authority,
)
from hexagent.exchangers.shell_tube.tube_side import (
    length_authorities as _length_authorities,
)
from hexagent.exchangers.shell_tube.tube_side import (
    owned_enums as _owned_enums,
)
from hexagent.exchangers.shell_tube.tube_side import (
    provenance as _provenance,
)
from hexagent.exchangers.shell_tube.tube_side import (
    raw_projection as _raw_projection,
)
from hexagent.exchangers.shell_tube.tube_side import (
    request as _request,
)
from hexagent.exchangers.shell_tube.tube_side import (
    scheduler as _scheduler,
)
from hexagent.exchangers.shell_tube.tube_side import (
    valid_result as _valid_result,
)

# A01 — required exports
FrozenJsonArray = _canonical.FrozenJsonArray
FrozenJsonObject = _canonical.FrozenJsonObject
sha256_hex = _canonical.sha256_hex


# Canonical framing primitives
frame_value = _canonical.frame_value
frame_tuple = _canonical.frame_tuple
frame_record = _canonical.frame_record
PI_DECIMAL_LEXEME = _canonical.PI_DECIMAL_LEXEME
pi_decimal = _canonical.pi_decimal


# §2.2 — owned enums
FlowPathMode = _owned_enums.FlowPathMode
HydraulicAuthorityMode = _owned_enums.HydraulicAuthorityMode
ReferencePlaneToken = _owned_enums.ReferencePlaneToken
ReferencePlanePair = _owned_enums.ReferencePlanePair
canonical_internal_flow_pair = _owned_enums.canonical_internal_flow_pair
canonical_heat_transfer_pair = _owned_enums.canonical_heat_transfer_pair


# §13 — blocker registry
BlockerCode = _blocker_registry.BlockerCode
Task025BlockerEntry = _blocker_registry.Task025BlockerEntry
emit_blocker = _blocker_registry.emit_blocker
collapse_unregistered_codes = _blocker_registry.collapse_unregistered_codes


# §5.3 — length authorities
InternalFlowLengthAuthority = _length_authorities.InternalFlowLengthAuthority
HeatTransferLengthAuthority = _length_authorities.HeatTransferLengthAuthority


# §5.4 — participation authority
Task025HydraulicParticipationAuthority = (
    _hydraulic_participation_authority.Task025HydraulicParticipationAuthority
)


# §5 — request
Task025Request = _request.Task025Request
TASK025_REQUEST_FIELDS = _request.TASK025_REQUEST_FIELDS
SUPPORTED_PROFILE_IDS = _request.SUPPORTED_PROFILE_IDS
SUPPORTED_SOFTWARE_VERSION = _request.SUPPORTED_SOFTWARE_VERSION


# §6.2 / §6.3 — result schemas
Task025ValidResult = _valid_result.Task025ValidResult
TASK025_VALID_RESULT_FIELDS = _valid_result.TASK025_VALID_RESULT_FIELDS
DEFERRED_CAPABILITIES_V1 = _valid_result.DEFERRED_CAPABILITIES_V1
Task025BlockedResult = _blocked_result.Task025BlockedResult
TASK025_BLOCKED_RESULT_FIELDS = _blocked_result.TASK025_BLOCKED_RESULT_FIELDS
BLOCKED_RESULT_HASH_FIELDS = _blocked_result.BLOCKED_RESULT_HASH_FIELDS


# §6.1 — provenance
FrozenRawProjection = _provenance.FrozenRawProjection
FrozenIdentity = _provenance.FrozenIdentity
FrozenProvenance = _provenance.FrozenProvenance
DESIGN_CONTRACT_PATH = _provenance.DESIGN_CONTRACT_PATH
TASK_ID = _provenance.TASK_ID
IMPLEMENTATION_SOFTWARE_VERSION = _provenance.IMPLEMENTATION_SOFTWARE_VERSION


# §9 — geometry
HydraulicGeometryOutputs = _hydraulic_geometry.HydraulicGeometryOutputs
compute_hydraulic_geometry = _hydraulic_geometry.compute_hydraulic_geometry


# §8 — Decimal context
local_decimal_context = _decimal_identity.local_decimal_context
validate_positive_finite_decimal = _decimal_identity.validate_positive_finite_decimal
validate_finite_decimal = _decimal_identity.validate_finite_decimal
quantize_half_even = _decimal_identity.quantize_half_even
canonical_decimal_lexeme = _decimal_identity.canonical_decimal_lexeme


# §7 — raw projection
project_raw_value = _raw_projection.project_raw_value
project_raw_dict = _raw_projection.project_raw_dict
raw_projection_hex = _raw_projection.raw_projection_hex
unsafe_object_signal = _raw_projection.unsafe_object_signal
RECOGNIZED_ENUM_CLASSES = _raw_projection.RECOGNIZED_ENUM_CLASSES


# §10 — hash DAG
internal_flow_authority_length_hash = _hash_dag.internal_flow_authority_length_hash
heat_transfer_authority_length_hash = _hash_dag.heat_transfer_authority_length_hash
layout_hash_passthrough = _hash_dag.layout_hash_passthrough
hydraulic_authority_hash = _hash_dag.hydraulic_authority_hash
request_hash = _hash_dag.request_hash
result_hash = _hash_dag.result_hash
result_id = _hash_dag.result_id
blocked_result_hash = _hash_dag.blocked_result_hash


# §12 — scheduler
schedule = _scheduler.schedule
finalize_blocked = _scheduler.finalize_blocked
evaluate_task025 = _scheduler.evaluate_task025
STAGE_RANKS = _scheduler.STAGE_RANKS
TOP_LEVEL_NOT_EXACT_DICT_TOKEN = _scheduler.TOP_LEVEL_NOT_EXACT_DICT_TOKEN
RAW_PROFILE_ID_MISSING_TOKEN = _scheduler.RAW_PROFILE_ID_MISSING_TOKEN
RAW_PROFILE_ID_INVALID_TYPE_TOKEN = _scheduler.RAW_PROFILE_ID_INVALID_TYPE_TOKEN


__all__ = [
    # A01
    "FrozenJsonArray",
    "FrozenJsonObject",
    "sha256_hex",
    "frame_value",
    "frame_tuple",
    "frame_record",
    "PI_DECIMAL_LEXEME",
    "pi_decimal",
    # enums
    "FlowPathMode",
    "HydraulicAuthorityMode",
    "ReferencePlaneToken",
    "ReferencePlanePair",
    "canonical_internal_flow_pair",
    "canonical_heat_transfer_pair",
    # blockers
    "BlockerCode",
    "Task025BlockerEntry",
    "emit_blocker",
    "collapse_unregistered_codes",
    # length authorities
    "InternalFlowLengthAuthority",
    "HeatTransferLengthAuthority",
    # participation
    "Task025HydraulicParticipationAuthority",
    # request
    "Task025Request",
    "TASK025_REQUEST_FIELDS",
    "SUPPORTED_PROFILE_IDS",
    "SUPPORTED_SOFTWARE_VERSION",
    # result schemas
    "Task025ValidResult",
    "TASK025_VALID_RESULT_FIELDS",
    "DEFERRED_CAPABILITIES_V1",
    "Task025BlockedResult",
    "TASK025_BLOCKED_RESULT_FIELDS",
    "BLOCKED_RESULT_HASH_FIELDS",
    # provenance
    "FrozenRawProjection",
    "FrozenIdentity",
    "FrozenProvenance",
    "DESIGN_CONTRACT_PATH",
    "TASK_ID",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    # geometry
    "HydraulicGeometryOutputs",
    "compute_hydraulic_geometry",
    # decimal
    "local_decimal_context",
    "validate_positive_finite_decimal",
    "validate_finite_decimal",
    "quantize_half_even",
    "canonical_decimal_lexeme",
    # raw projection
    "project_raw_value",
    "project_raw_dict",
    "raw_projection_hex",
    "unsafe_object_signal",
    "RECOGNIZED_ENUM_CLASSES",
    # hash DAG
    "internal_flow_authority_length_hash",
    "heat_transfer_authority_length_hash",
    "layout_hash_passthrough",
    "hydraulic_authority_hash",
    "request_hash",
    "result_hash",
    "result_id",
    "blocked_result_hash",
    # scheduler
    "schedule",
    "finalize_blocked",
    "evaluate_task025",
    "STAGE_RANKS",
    "TOP_LEVEL_NOT_EXACT_DICT_TOKEN",
    "RAW_PROFILE_ID_MISSING_TOKEN",
    "RAW_PROFILE_ID_INVALID_TYPE_TOKEN",
]
