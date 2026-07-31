"""TASK-026 public package surface.

R8 implementation. The public surface exposes the two frozen
signatures and the typed value objects. No private helpers are
re-exported here.

Public entry points (R6-R7 §2):

  build_raw_tube_side_request_envelope(raw: object)
    -> TubeSideThermalRequest | RawBoundaryBlockedResult

  compute_tube_side_heat_transfer_coefficient(
      request: TubeSideThermalRequest,
      upstream: Task025ValidResult | Task025BlockedResult,
  ) -> TubeSideThermalResult | TubeSideBlockedResult
"""

from __future__ import annotations

import enum as _enum
from typing import Final as _Final, TYPE_CHECKING, Sequence, cast


# ---------------------------------------------------------------------------
# Frozen enums (R6-R7 §3.5 + §6 + §8.1).
# Defined at module top AFTER `from __future__` so submodule imports from
# this package can reference these names without circular-import risk.
# ---------------------------------------------------------------------------


class PhaseRegion(_enum.StrEnum):
    """R6-R7 §3.5 — Phase regions accepted at S04."""

    SINGLE_PHASE_LIQUID = "SINGLE_PHASE_LIQUID"
    SINGLE_PHASE_GAS = "SINGLE_PHASE_GAS"

    @property
    def canonical_utf8_bytes(self) -> bytes:
        return self.value.encode("ascii")


ACCEPTED_PHASE_REGIONS: _Final[tuple[PhaseRegion, ...]] = (
    PhaseRegion.SINGLE_PHASE_LIQUID,
    PhaseRegion.SINGLE_PHASE_GAS,
)


class PhaseAssertion(_enum.StrEnum):
    """R6-R7 §3.5 — Phase assertion from the caller."""

    SINGLE_PHASE_LIQUID = "SINGLE_PHASE_LIQUID"
    SINGLE_PHASE_GAS = "SINGLE_PHASE_GAS"

    @property
    def canonical_utf8_bytes(self) -> bytes:
        return self.value.encode("ascii")


ACCEPTED_PHASE_ASSERTIONS: _Final[tuple[PhaseAssertion, ...]] = (
    PhaseAssertion.SINGLE_PHASE_LIQUID,
    PhaseAssertion.SINGLE_PHASE_GAS,
)


class FlowRegime(_enum.StrEnum):
    """R6-R7 §6 — Flow regimes."""

    LAMINAR = "LAMINAR"
    TRANSITION = "TRANSITION"
    TURBULENT = "TURBULENT"

    @property
    def canonical_utf8_bytes(self) -> bytes:
        return self.value.encode("ascii")


class ThermalBoundaryCondition(_enum.StrEnum):
    """R6-R7 §6.1 / §6.3 — Thermal boundary conditions."""

    CWT = "CWT"
    CHF = "CHF"

    @property
    def canonical_utf8_bytes(self) -> bytes:
        return self.value.encode("ascii")


ACCEPTED_THERMAL_BOUNDARY_CONDITIONS: _Final[tuple[ThermalBoundaryCondition, ...]] = (
    ThermalBoundaryCondition.CWT,
    ThermalBoundaryCondition.CHF,
)


# ---------------------------------------------------------------------------
# Type-check-only protocols for TASK-025 upstream (R8 brief §6 forbids duck typing).
# ---------------------------------------------------------------------------

if TYPE_CHECKING:
    from typing import Protocol


    class _Task025ValidResultProtocol(Protocol):
        schema_version: str
        implementation_software_version: str
        single_tube_flow_area_m2: Decimal
        total_parallel_flow_area_m2: Decimal
        flow_cross_section_wetted_perimeter_m: Decimal
        total_flow_cross_section_wetted_perimeter_m: Decimal
        hydraulic_diameter_m: Decimal
        internal_volume_m3: Decimal
        internal_heat_transfer_surface_area_m2: Decimal
        result_hash: str
        request_hash: str
        hydraulic_authority_hash: str

    class _Task025BlockedResultProtocol(Protocol):
        schema_version: str
        implementation_software_version: str
        blocked_result_hash: str
        blockers: Sequence[object]
        warnings: Sequence[str]
        deferred_capabilities: Sequence[str]
        stage_rank: int
        task020_identity: object | None
        task021_identity: object | None
        provenance: object | None


# ---------------------------------------------------------------------------
# Production module imports (all 14 in-scope paths).
# ---------------------------------------------------------------------------

from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side_thermal.blocker_registry import (
    DEFENSIVE_COUNT,
    DEFENSIVE_UNREACHABLE_CODE,
    REACHABLE_COUNT,
    RESERVED_NOT_EMITTED,
    TASK026_BLOCKER_CODE_COUNT,
    TASK026_BLOCKER_EARLIEST_STAGE,
    TASK026_BLOCKER_REGISTRY,
    TASK026_BLOCKER_SEVERITY,
    TASK026_DEFENSIVE_BLOCKERS,
    TASK026_REACHABLE_BLOCKERS,
    BlockerCode,
    BlockerEntry,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.canonical import (
    ABSENT_OPTIONAL_KIND,
    ABSENT_OPTIONAL_PAYLOAD,
    KIND_BYTES,
    KIND_DECIMAL,
    KIND_ENUM,
    KIND_INT,
    KIND_NONE,
    KIND_RAW_PROJECTION,
    KIND_RECORD,
    KIND_STRING,
    KIND_TUPLE,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.decimal_primitives import (
    GOLDEN_VECTORS,
    NOMINAL_DECIMAL_PRECISION,
    WORKING_DECIMAL_PRECISION,
    WORKING_GUARD_DIGITS,
    DecimalFailure,
    decimal_ln,
    decimal_pow_2_3,
    decimal_sqrt,
    task026_decimal_context_160,
    task026_decimal_context_200,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.decimal_quantization import (
    HI_QUANTUM_POLICY,
    QUANTIZATION_FIELD_COUNT,
    QUANTIZATION_MAP,
    QUANTIZATION_STAGE,
    ROUNDING_MODE,
    field_for,
    quantize_half_even,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.nusselt_selector import (
    GNIELINSKI_CONST_0790,
    GNIELINSKI_CONST_127,
    GNIELINSKI_CONST_1000,
    GNIELINSKI_CONST_164,
    GNIELINSKI_CONST_8,
    LAMINAR_CHF_NU,
    LAMINAR_CWT_NU,
    ApplicabilityResult,
    check_pr_envelope,
    compute_gnielinski_nusselt,
    compute_laminar_nusselt,
    select_laminar_correlation,
    select_regime,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.property_snapshot import (
    PROPERTY_SNAPSHOT_FIELDS,
    PROPERTY_SNAPSHOT_HASH_FIELDS,
    PROPERTY_SNAPSHOT_HASH_KIND_TAGS,
    PROPERTY_SNAPSHOT_NAMESPACE,
    PROPERTY_SNAPSHOT_SUBRECORD_KIND_TAGS,
    PropertySnapshot,
    recompute_property_snapshot_hash,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.provenance import (
    INPUT_EVIDENCE_REF_COUNT,
    INPUT_EVIDENCE_REFS_V1,
    PROVENANCE_FIELDS,
    PROVENANCE_KIND_TAGS,
    PROVENANCE_NAMESPACE,
    FrozenProvenance,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.raw_projection import (
    RAW_PROJECTION_NAMESPACE,
    FrozenRawProjection,
    frame_raw_projection_field,
    zero_optional,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.request import (
    DEFERRED_CAPABILITIES_V1,
    DEFERRED_CAPABILITY_COUNT,
    IMPLEMENTATION_SOFTWARE_VERSION,
    REQUEST_FIELDS,
    REQUEST_FIELD_COUNT,
    REQUEST_HASH_FIELDS,
    REQUEST_HASH_KIND_TAGS,
    REQUEST_HASH_NAMESPACE,
    SCHEMA_VERSION,
    TASK026_VERSION,
    TubeSideThermalRequest,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import (
    BLOCKED_FIELD_COUNT,
    BLOCKED_RESULT_FIELDS,
    BLOCKED_RESULT_HASH_FIELDS,
    BLOCKED_RESULT_HASH_KIND_TAGS,
    BLOCKED_RESULT_HASH_NAMESPACE,
    RAW_BOUNDARY_BLOCKED_RESULT_HASH_FIELDS,
    RAW_BOUNDARY_BLOCKED_RESULT_HASH_KIND_TAGS,
    RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE,
    RawBoundaryBlockedResult,
    SUCCESS_FIELD_COUNT,
    SUCCESS_RESULT_FIELDS,
    SUCCESS_RESULT_HASH_FIELDS,
    SUCCESS_RESULT_HASH_KIND_TAGS,
    SUCCESS_RESULT_HASH_NAMESPACE,
    TubeSideBlockedResult,
    TubeSideThermalResult,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.single_phase import (
    SinglePhaseOutputs,
    compute_single_phase,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.stage_pipeline import (
    HYDRAULIC_GEOMETRY_HASH_FIELDS,
    HYDRAULIC_GEOMETRY_KIND_TAGS,
    HYDRAULIC_GEOMETRY_NAMESPACE,
    RESULT_ID_NAMESPACE,
    RESULT_ID_NAME_PREFIX,
    STAGES,
    TASK026_T025_FORBIDDEN_FIELDS,
    TASK026_T025_UPSTREAM_READ_SET,
    build_raw_tube_side_request_envelope,
    compute_tube_side_heat_transfer_coefficient,
    rebuild_provenance_upstream,
    stage_count,
    stage_name,
    stage_names,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.warning_registry import (
    TASK026_WARNING_CODE_COUNT,
    TASK026_WARNING_REGISTRY,
    WARNING_ENTRY_HASH_FIELDS,
    WarningEntry,
)


__all__ = [
    # Public entry points
    "build_raw_tube_side_request_envelope",
    "compute_tube_side_heat_transfer_coefficient",
    # Enums
    "PhaseRegion",
    "PhaseAssertion",
    "FlowRegime",
    "ThermalBoundaryCondition",
    "ACCEPTED_PHASE_REGIONS",
    "ACCEPTED_PHASE_ASSERTIONS",
    "ACCEPTED_THERMAL_BOUNDARY_CONDITIONS",
    # Typed value objects
    "TubeSideThermalRequest",
    "TubeSideThermalResult",
    "TubeSideBlockedResult",
    "RawBoundaryBlockedResult",
    "PropertySnapshot",
    "FrozenProvenance",
    "FrozenRawProjection",
    "BlockerEntry",
    "BlockerCode",
    "WarningEntry",
    "SinglePhaseOutputs",
    "ApplicabilityResult",
    # Frozen constants
    "REQUEST_FIELDS",
    "REQUEST_FIELD_COUNT",
    "REQUEST_HASH_FIELDS",
    "REQUEST_HASH_KIND_TAGS",
    "REQUEST_HASH_NAMESPACE",
    "PROPERTY_SNAPSHOT_FIELDS",
    "PROPERTY_SNAPSHOT_HASH_FIELDS",
    "PROPERTY_SNAPSHOT_HASH_KIND_TAGS",
    "PROPERTY_SNAPSHOT_SUBRECORD_KIND_TAGS",
    "PROPERTY_SNAPSHOT_NAMESPACE",
    "PROVENANCE_FIELDS",
    "PROVENANCE_NAMESPACE",
    "PROVENANCE_KIND_TAGS",
    "INPUT_EVIDENCE_REFS_V1",
    "INPUT_EVIDENCE_REF_COUNT",
    "SUCCESS_RESULT_FIELDS",
    "SUCCESS_FIELD_COUNT",
    "BLOCKED_RESULT_FIELDS",
    "BLOCKED_FIELD_COUNT",
    "SUCCESS_RESULT_HASH_FIELDS",
    "SUCCESS_RESULT_HASH_KIND_TAGS",
    "SUCCESS_RESULT_HASH_NAMESPACE",
    "BLOCKED_RESULT_HASH_FIELDS",
    "BLOCKED_RESULT_HASH_KIND_TAGS",
    "BLOCKED_RESULT_HASH_NAMESPACE",
    "RAW_BOUNDARY_BLOCKED_RESULT_HASH_FIELDS",
    "RAW_BOUNDARY_BLOCKED_RESULT_HASH_KIND_TAGS",
    "RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE",
    "WARNING_ENTRY_HASH_FIELDS",
    "TASK026_BLOCKER_REGISTRY",
    "TASK026_BLOCKER_CODE_COUNT",
    "TASK026_REACHABLE_BLOCKERS",
    "TASK026_DEFENSIVE_BLOCKERS",
    "REACHABLE_COUNT",
    "DEFENSIVE_COUNT",
    "DEFENSIVE_UNREACHABLE_CODE",
    "RESERVED_NOT_EMITTED",
    "TASK026_BLOCKER_EARLIEST_STAGE",
    "TASK026_BLOCKER_SEVERITY",
    "TASK026_WARNING_CODE_COUNT",
    "TASK026_WARNING_REGISTRY",
    "QUANTIZATION_MAP",
    "QUANTIZATION_FIELD_COUNT",
    "QUANTIZATION_STAGE",
    "ROUNDING_MODE",
    "HI_QUANTUM_POLICY",
    "WORKING_DECIMAL_PRECISION",
    "NOMINAL_DECIMAL_PRECISION",
    "WORKING_GUARD_DIGITS",
    "GOLDEN_VECTORS",
    "LAMINAR_CWT_NU",
    "LAMINAR_CHF_NU",
    "GNIELINSKI_CONST_0790",
    "GNIELINSKI_CONST_164",
    "GNIELINSKI_CONST_127",
    "GNIELINSKI_CONST_1000",
    "GNIELINSKI_CONST_8",
    "DEFERRED_CAPABILITIES_V1",
    "DEFERRED_CAPABILITY_COUNT",
    "SCHEMA_VERSION",
    "TASK026_VERSION",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "KIND_NONE",
    "KIND_INT",
    "KIND_STRING",
    "KIND_BYTES",
    "KIND_DECIMAL",
    "KIND_ENUM",
    "KIND_TUPLE",
    "KIND_RECORD",
    "KIND_RAW_PROJECTION",
    "ABSENT_OPTIONAL_KIND",
    "ABSENT_OPTIONAL_PAYLOAD",
    "HYDRAULIC_GEOMETRY_HASH_FIELDS",
    "HYDRAULIC_GEOMETRY_NAMESPACE",
    "HYDRAULIC_GEOMETRY_KIND_TAGS",
    "TASK026_T025_UPSTREAM_READ_SET",
    "TASK026_T025_FORBIDDEN_FIELDS",
    "RESULT_ID_NAMESPACE",
    "RESULT_ID_NAME_PREFIX",
    "STAGES",
    "RAW_PROJECTION_NAMESPACE",
    # Helpers
    "decimal_ln",
    "decimal_sqrt",
    "decimal_pow_2_3",
    "DecimalFailure",
    "task026_decimal_context_200",
    "task026_decimal_context_160",
    "quantize_half_even",
    "field_for",
    "select_regime",
    "check_pr_envelope",
    "select_laminar_correlation",
    "compute_gnielinski_nusselt",
    "compute_laminar_nusselt",
    "compute_single_phase",
    "recompute_property_snapshot_hash",
    "frame_raw_projection_field",
    "zero_optional",
    "rebuild_provenance_upstream",
    "stage_count",
    "stage_names",
    "stage_name",
]
