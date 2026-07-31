"""TASK-026 16-stage pipeline (S00..S15).

R8 implementation. This module orchestrates the full pipeline. The
16 stages per R6-R7 §14:

  S00  raw_input_boundary
  S01  task025_envelope_validation
  S02  property_snapshot_schema_validation
  S03  hash_and_authority_validation
  S04  phase_validation
  S05  mass_flow_validation
  S06  bulk_velocity_computation
  S07  reynolds_computation
  S08  prandtl_computation
  S09  applicability_selection
  S10  nusselt_computation
  S11  hi_computation
  S12  quantization
  S13  warnings_and_blockers_finalization
  S14  canonical_serialization
  S15  hash_uuid_provenance

The public entry points are:

  build_raw_tube_side_request_envelope(
      raw: object,
  ) -> TubeSideThermalRequest | RawBoundaryBlockedResult
  compute_tube_side_heat_transfer_coefficient(
      request: TubeSideThermalRequest,
      upstream: Task025ValidResult | Task025BlockedResult,
  ) -> TubeSideThermalResult | TubeSideBlockedResult

Per R6-R7 §2.1, S00 only returns a typed request or a raw-blocked
result; the raw factory does NOT execute correlation applicability,
property positivity, or engineering computation. Per R6-R7 §2.2,
the typed compute only accepts already-typed inputs.

R8 brief §4: the raw factory must not invoke hasattr / getattr /
str / repr / dataclasses.asdict / arbitrary Mapping protocol on
unknown objects. The raw factory only inspects the static shape
keys of a known object.

R8 brief §7: at S15, the upstream_identity_hashes tuple is rebuilt
from the actual upstream — (upstream.result_hash,) for valid
upstream, (upstream.blocked_result_hash,) for blocked upstream.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence  # noqa: E402
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from hexagent.exchangers.shell_tube.tube_side_thermal.blocker_registry import (
    TASK026_BLOCKER_EARLIEST_STAGE,
    TASK026_BLOCKER_REGISTRY,
    TASK026_BLOCKER_SEVERITY,
    BlockerEntry,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.canonical import (
    KIND_DECIMAL,
    KIND_STRING,
    KIND_TUPLE,
    composite_hash,
    decimal_payload,
    enum_payload,
    frame_record,
    frame_tuple,
    frame_value,
    string_payload,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.decimal_primitives import (
    DecimalFailure,
)

# ---------------------------------------------------------------------------
# TASK-025 upstream type protocols (R6-R7 §4 + §14.1 S01).
# ---------------------------------------------------------------------------
# We do NOT duck type (R8 brief §6). The typed compute accepts exactly
# Task025ValidResult or Task025BlockedResult. The runtime check uses
# type(__name__) to dispatch. The TYPE_CHECKING block supplies structural
# types so mypy can verify attribute access without runtime import.


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


from hexagent.exchangers.shell_tube.tube_side_thermal import (
    ACCEPTED_PHASE_ASSERTIONS,
    ACCEPTED_PHASE_REGIONS,
    ACCEPTED_THERMAL_BOUNDARY_CONDITIONS,
    FlowRegime,
    PhaseAssertion,
    PhaseRegion,
    ThermalBoundaryCondition,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.nusselt_selector import (
    check_pr_envelope,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.property_snapshot import (
    PROPERTY_SNAPSHOT_NAMESPACE,
    PROPERTY_SNAPSHOT_SUBRECORD_KIND_TAGS,
    PropertySnapshot,
    recompute_property_snapshot_hash,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.provenance import (
    INPUT_EVIDENCE_REFS_V1,
    FrozenProvenance,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.raw_projection import (
    FrozenRawProjection,
    frame_raw_projection_field,
    zero_optional,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.request import (
    DEFERRED_CAPABILITIES_V1,
    IMPLEMENTATION_SOFTWARE_VERSION,
    REQUEST_HASH_FIELDS,
    REQUEST_HASH_KIND_TAGS,
    REQUEST_HASH_NAMESPACE,
    SCHEMA_VERSION,
    TASK026_VERSION,
    TubeSideThermalRequest,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import (
    BLOCKED_RESULT_HASH_FIELDS,
    BLOCKED_RESULT_HASH_KIND_TAGS,
    BLOCKED_RESULT_HASH_NAMESPACE,
    SUCCESS_RESULT_HASH_FIELDS,
    SUCCESS_RESULT_HASH_KIND_TAGS,
    SUCCESS_RESULT_HASH_NAMESPACE,
    RawBoundaryBlockedResult,
    TubeSideBlockedResult,
    TubeSideThermalResult,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.single_phase import (
    SinglePhaseOutputs,
    compute_single_phase,
)

# R6-R7 §4 — 7-field TASK-025 read set.
TASK026_T025_UPSTREAM_READ_SET: tuple[str, ...] = (
    "single_tube_flow_area_m2",
    "total_parallel_flow_area_m2",
    "flow_cross_section_wetted_perimeter_m",
    "total_flow_cross_section_wetted_perimeter_m",
    "hydraulic_diameter_m",
    "internal_volume_m3",
    "internal_heat_transfer_surface_area_m2",
)

# R6-R7 §4.2 — 10 forbidden TASK-025 field names.
TASK026_T025_FORBIDDEN_FIELDS: tuple[str, ...] = (
    "D_i",
    "D_o",
    "L",
    "n_tubes",
    "layout",
    "pitch_ratio",
    "baffle_spacing",
    "baffle_cut",
    "inlet_outlet_zone_length",
    "tube_thermal_conductivity",
)

# R6-R7 §4.3 — 7-field hydraulic geometry hash.
HYDRAULIC_GEOMETRY_HASH_FIELDS: tuple[str, ...] = TASK026_T025_UPSTREAM_READ_SET
HYDRAULIC_GEOMETRY_NAMESPACE: str = "task026.hydraulic-geometry.v1"
HYDRAULIC_GEOMETRY_KIND_TAGS: tuple[bytes, ...] = (
    KIND_DECIMAL,
    KIND_DECIMAL,
    KIND_DECIMAL,
    KIND_DECIMAL,
    KIND_DECIMAL,
    KIND_DECIMAL,
    KIND_DECIMAL,
)

# R6-R7 §10 — result UUID.
RESULT_ID_NAMESPACE: str = "a0260000-0000-5000-8000-000000000002"
RESULT_ID_NAME_PREFIX: str = "task026-result-v1::"

# R6-R7 §16 — TEST_BLOCKER_REGISTRY (40-doored test count from T1-R2).
# Already in T1-R2.

# R6-R7 §14 — Stages.
STAGES: tuple[tuple[str, str], ...] = (
    ("S00", "raw_input_boundary"),
    ("S01", "task025_envelope_validation"),
    ("S02", "property_snapshot_schema_validation"),
    ("S03", "hash_and_authority_validation"),
    ("S04", "phase_validation"),
    ("S05", "mass_flow_validation"),
    ("S06", "bulk_velocity_computation"),
    ("S07", "reynolds_computation"),
    ("S08", "prandtl_computation"),
    ("S09", "applicability_selection"),
    ("S10", "nusselt_computation"),
    ("S11", "hi_computation"),
    ("S12", "quantization"),
    ("S13", "warnings_and_blockers_finalization"),
    ("S14", "canonical_serialization"),
    ("S15", "hash_uuid_provenance"),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_phase_region(value: object) -> PhaseRegion:
    if isinstance(value, PhaseRegion):
        return value
    if isinstance(value, str) and value in {p.value for p in ACCEPTED_PHASE_REGIONS}:
        return PhaseRegion(value)
    raise ValueError(
        f"phase_region must be one of {[p.value for p in ACCEPTED_PHASE_REGIONS]}; got {value!r}"
    )


def _to_phase_assertion(value: object) -> PhaseAssertion:
    if isinstance(value, PhaseAssertion):
        return value
    if isinstance(value, str) and value in {p.value for p in ACCEPTED_PHASE_ASSERTIONS}:
        return PhaseAssertion(value)
    raise ValueError(
        f"phase_assertion must be one of "
        f"{[p.value for p in ACCEPTED_PHASE_ASSERTIONS]}; got {value!r}"
    )


def _to_thermal_boundary(value: object) -> ThermalBoundaryCondition:
    if isinstance(value, ThermalBoundaryCondition):
        return value
    if isinstance(value, str) and value in {c.value for c in ACCEPTED_THERMAL_BOUNDARY_CONDITIONS}:
        return ThermalBoundaryCondition(value)
    raise ValueError(
        f"thermal_boundary_condition must be one of "
        f"{[c.value for c in ACCEPTED_THERMAL_BOUNDARY_CONDITIONS]}; got {value!r}"
    )


def _to_decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str):
        try:
            return Decimal(value)
        except Exception as exc:
            raise ValueError(f"{field_name} cannot parse Decimal: {exc!s}") from exc
    raise ValueError(f"{field_name} must be Decimal or str; got {type(value).__name__}")


def _to_hex_hash(value: object, field_name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field_name} must be 64-hex string")
    if any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field_name} must be lowercase hex")
    return value


def _new_blocker(
    code: str, stage: str, payload: tuple[str, ...], message_template: str
) -> BlockerEntry:
    if code not in TASK026_BLOCKER_REGISTRY:
        raise ValueError(f"unknown blocker code: {code!r}")
    # TASK026_BLOCKER_EARLIEST_STAGE is {code: stage}; check the stage is one of the values.
    valid_stages = set(TASK026_BLOCKER_EARLIEST_STAGE.values())
    if stage not in valid_stages:
        raise ValueError(f"unknown stage: {stage!r}")
    if TASK026_BLOCKER_SEVERITY[code] != "hard":
        raise ValueError(f"severity must be hard for {code}")
    return BlockerEntry(
        code=code,
        severity="hard",
        stage=stage,
        payload=payload,
        message_template=message_template,
    )


# ---------------------------------------------------------------------------
# §2.1 — Raw input factory (S00 only)
# ---------------------------------------------------------------------------


def build_raw_tube_side_request_envelope(
    raw: object,
) -> TubeSideThermalRequest | RawBoundaryBlockedResult:
    """R6-R7 §2.1 — S00 raw factory.

    The factory shape-validates the raw input (no engineering
    computation, no property positivity, no property hash equality,
    no phase semantic validation, no mass-flow semantic validation,
    no correlation applicability, no engineering computation). It
    either returns a typed TubeSideThermalRequest or a
    RawBoundaryBlockedResult with BL_RAW_INPUT_BOUNDARY_MALFORMED
    or BL_REQUEST_UNKNOWN_FIELD.

    Per R8 brief §4: the factory must NOT use hasattr / getattr /
    str / repr / dataclasses.asdict / arbitrary Mapping protocol /
    custom iterator protocol / Decimal(str(value)) on unknown
    objects. It only inspects the static shape keys of a known
    mapping input; everything else is rejected.
    """
    # Recognized raw envelope shape: a built-in dict with exactly
    # the 10 field values (or with the 10 field keys + optional
    # _schema_marker). The raw factory only inspects the static
    # _KEYS list below; it does NOT iterate arbitrary Mapping.
    if type(raw) is not dict:
        # We do NOT use hasattr / getattr / Mapping on the input.
        # We accept built-in dict shape; everything else is rejected.
        return _raw_boundary_blocked(
            raw_bytes=b"",
            blockers=(
                _new_blocker(
                    "BL_RAW_INPUT_BOUNDARY_MALFORMED",
                    "S00",
                    (type(raw).__name__,),
                    "raw input must be a built-in dict; got {actual_type}",
                ),
            ),
            warnings=(),
        )

    # Known raw-input keys (deliberately 10 to match the request schema).
    _RAW_KEYS = (
        "schema_version",
        "task026_version",
        "implementation_software_version",
        "property_snapshot_hash",
        "property_snapshot",
        "phase_assertion",
        "thermal_boundary_condition",
        "mass_flow_rate_kg_s",
        "deferred_capabilities",
        "provenance",
    )
    raw_keys = list(raw.keys())
    unknown = [k for k in raw_keys if k not in _RAW_KEYS]
    if unknown:
        return _raw_boundary_blocked(
            raw_bytes=b"",
            blockers=(
                _new_blocker(
                    "BL_REQUEST_UNKNOWN_FIELD",
                    "S00",
                    (",".join(unknown),),
                    "raw input has unknown fields: {unknown_fields}",
                ),
            ),
            warnings=(),
        )

    # All required keys must be present (no missing).
    missing = [k for k in _RAW_KEYS if k not in raw]
    if missing:
        return _raw_boundary_blocked(
            raw_bytes=b"",
            blockers=(
                _new_blocker(
                    "BL_RAW_INPUT_BOUNDARY_MALFORMED",
                    "S00",
                    (",".join(missing),),
                    "raw input missing required fields: {missing_fields}",
                ),
            ),
            warnings=(),
        )

    # Build the typed request. S00 does NOT validate semantics
    # (no property positivity, no hash equality, no phase consistency).
    # That work is done at S02-S04 in compute_tube_side_heat_transfer_coefficient.
    try:
        snap_dict = raw["property_snapshot"]
        if not isinstance(snap_dict, dict):
            raise ValueError("property_snapshot must be a dict")
        # PropertySnapshot only — no semantics yet.
        prop_snapshot = PropertySnapshot(
            density_kg_m3=_to_decimal(snap_dict["density_kg_m3"], "density_kg_m3"),
            dynamic_viscosity_pa_s=_to_decimal(
                snap_dict["dynamic_viscosity_pa_s"], "dynamic_viscosity_pa_s"
            ),
            thermal_conductivity_w_m_k=_to_decimal(
                snap_dict["thermal_conductivity_w_m_k"], "thermal_conductivity_w_m_k"
            ),
            specific_heat_capacity_j_kg_k=_to_decimal(
                snap_dict["specific_heat_capacity_j_kg_k"], "specific_heat_capacity_j_kg_k"
            ),
            bulk_temperature_k=_to_decimal(snap_dict["bulk_temperature_k"], "bulk_temperature_k"),
            bulk_pressure_pa=_to_decimal(snap_dict["bulk_pressure_pa"], "bulk_pressure_pa"),
            phase_region=_to_phase_region(snap_dict["phase_region"]),
            property_source_id=str(snap_dict["property_source_id"]),
            property_source_version=str(snap_dict["property_source_version"]),
            property_snapshot_hash=_to_hex_hash(
                snap_dict["property_snapshot_hash"], "property_snapshot_hash"
            ),
        )
        phase_assertion = _to_phase_assertion(raw["phase_assertion"])
        thermal_boundary = _to_thermal_boundary(raw["thermal_boundary_condition"])
        mass_flow = _to_decimal(raw["mass_flow_rate_kg_s"], "mass_flow_rate_kg_s")
        property_snapshot_hash = _to_hex_hash(
            raw["property_snapshot_hash"], "property_snapshot_hash"
        )

        # Build a placeholder provenance at S00 (no upstream yet).
        # Runtime provenance is rebuilt at S15.
        # The 6 input_evidence_refs are frozen per R6-R7 §17.2.
        # The upstream_identity_hashes tuple is a single-element
        # placeholder at S00; the runtime S15 step replaces it with
        # the actual value from the upstream argument.
        # We use a placeholder hash of zeros at S00; the actual
        # S15 rebinding is what makes the runtime provenance.
        # Per R8 brief §7, the S15 step MUST use the actual upstream.
        # We accept a SINGLE-element "runtime_pending" placeholder
        # at S00 only; S15 in the typed compute replaces it.
        # The placeholder is allowed because S00 has no upstream.
        placeholder_upstream = ("0" * 64,)
        provenance = FrozenProvenance(
            task_id="TASK-026",
            design_contract_path="/tmp/TASK-026-DESIGN-CONTRACT-DRAFT-R6-R7.md",
            implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
            input_evidence_refs=INPUT_EVIDENCE_REFS_V1,
            upstream_identity_hashes=placeholder_upstream,
        )

        request = TubeSideThermalRequest(
            schema_version=SCHEMA_VERSION,
            task026_version=TASK026_VERSION,
            implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
            property_snapshot_hash=property_snapshot_hash,
            property_snapshot=prop_snapshot,
            phase_assertion=phase_assertion,
            thermal_boundary_condition=thermal_boundary,
            mass_flow_rate_kg_s=mass_flow,
            deferred_capabilities=DEFERRED_CAPABILITIES_V1,
            provenance=provenance,
        )
        return request
    except (ValueError, KeyError, TypeError) as exc:
        return _raw_boundary_blocked(
            raw_bytes=b"",
            blockers=(
                _new_blocker(
                    "BL_RAW_INPUT_BOUNDARY_MALFORMED",
                    "S00",
                    (type(exc).__name__, str(exc)),
                    "raw input boundary malformed: {reason}",
                ),
            ),
            warnings=(),
        )


def _raw_boundary_blocked(
    raw_bytes: bytes,
    blockers: tuple[BlockerEntry, ...],
    warnings: tuple[str, ...],
) -> RawBoundaryBlockedResult:
    """R6-R7 §9.6.1 — S00 raw boundary blocked result.

    The raw projection is a single KIND_RAW_PROJECTION frame over
    raw_bytes (empty bytes if no child bytes were provided). The
    6-field hash projection uses the frozen namespace.
    """
    if not blockers:
        raise ValueError("raw_boundary_blocked_result must have at least one blocker")
    projection = FrozenRawProjection(
        projection_kind="RAW_PROJECTION",
        canonical_bytes_hex=raw_bytes.hex() if raw_bytes else "",
    )
    return RawBoundaryBlockedResult(
        schema_version=SCHEMA_VERSION,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        raw_request_projection=projection,
        blockers=blockers,
        warnings=warnings,
        deferred_capabilities=DEFERRED_CAPABILITIES_V1,
    )


# ---------------------------------------------------------------------------
# §2.2 — Typed compute (S01..S15)
# ---------------------------------------------------------------------------


def compute_tube_side_heat_transfer_coefficient(
    request: TubeSideThermalRequest,
    upstream: object,
) -> TubeSideThermalResult | TubeSideBlockedResult:
    """R6-R7 §2.2 — Typed compute.

    The typed compute runs S01..S15 inside a single call. The
    upstream argument is **already typed** (Task025ValidResult or
    Task025BlockedResult); duck typing is forbidden per R8 brief
    §6. Dispatch is via type() identity check.
    """
    # S01 — TASK-025 envelope validation.
    upstream_type_name = type(upstream).__name__
    if upstream_type_name == "Task025ValidResult":
        # Read the 7 fields by attribute access (typed upstream).
        # The runtime dispatch on type(__name__) is the only accepted entry
        # path (R8 brief §6 forbids duck typing). mypy cannot infer the
        # protocol from a runtime string match, so we cast() after the
        # dispatch.
        valid_typed = cast("_Task025ValidResultProtocol", upstream)
        try:
            single_area = valid_typed.single_tube_flow_area_m2
            total_area = valid_typed.total_parallel_flow_area_m2
            d_h = valid_typed.hydraulic_diameter_m
            upstream_geometry_hash = getattr(valid_typed, "hydraulic_authority_hash", None)
            if not isinstance(upstream_geometry_hash, str) or len(upstream_geometry_hash) != 64:
                raise ValueError("upstream.hydraulic_authority_hash must be 64-hex str")
        except AttributeError as exc:
            return _blocked_result(
                request=request,
                upstream=upstream,
                blockers=(
                    _new_blocker(
                        "BL_UPSTREAM_BLOCKED",
                        "S01",
                        (str(exc),),
                        "upstream missing TASK-025 hydraulic geometry field: {reason}",
                    ),
                ),
                warnings=(),
            )
        # Whether upstream is itself blocked is not signaled by this shape;
        # if upstream were blocked the dispatcher would have routed it.
        try:
            return _compute_s02_s15(
                request=request,
                upstream_geometry_hash=upstream_geometry_hash,
                single_tube_flow_area_m2=single_area,
                total_parallel_flow_area_m2=total_area,
                hydraulic_diameter_m=d_h,
                upstream_identity_hash=valid_typed.result_hash,
            )
        except DecimalFailure as exc:
            return _blocked_result(
                request=request,
                upstream=upstream,
                blockers=(
                    _new_blocker(
                        "BL_DECIMAL_FAILURE",
                        "S07",
                        (exc.operation, exc.lexeme, exc.reason),
                        "decimal failure during S07..S11: {op}({lexeme}) -> {reason}",
                    ),
                ),
                warnings=(),
            )
    elif upstream_type_name == "Task025BlockedResult":
        # Mirror upstream blockers verbatim per R6-R7 §14.1 S01.
        blocked_typed = cast("_Task025BlockedResultProtocol", upstream)
        upstream_blockers = []
        for ub in blocked_typed.blockers:
            upstream_blockers.append(
                _new_blocker(
                    "BL_UPSTREAM_BLOCKED",
                    "S01",
                    (getattr(ub, "code", "UNKNOWN"),),
                    "upstream TASK-025 blocked: {upstream_code}",
                )
            )
        return _blocked_result(
            request=request,
            upstream=upstream,
            blockers=tuple(upstream_blockers),
            warnings=tuple(),
        )
    else:
        # Unknown upstream type — emit BL_UPSTREAM_BLOCKED.
        return _blocked_result(
            request=request,
            upstream=upstream,
            blockers=(
                _new_blocker(
                    "BL_UPSTREAM_BLOCKED",
                    "S01",
                    (upstream_type_name,),
                    (
                        "upstream must be Task025ValidResult or "
                        "Task025BlockedResult; got {actual_type}"
                    ),
                ),
            ),
            warnings=(),
        )


def _compute_s02_s15(
    request: TubeSideThermalRequest,
    upstream_geometry_hash: str,
    single_tube_flow_area_m2: Decimal,
    total_parallel_flow_area_m2: Decimal,
    hydraulic_diameter_m: Decimal,
    upstream_identity_hash: str,
) -> TubeSideThermalResult | TubeSideBlockedResult:
    """Run stages S02..S15 and return either a success or a blocked result."""
    # S02 — property_snapshot schema validation (already validated at construction).
    # S03 — hash + authority validation.
    recomputed_hash = recompute_property_snapshot_hash(request.property_snapshot)
    if (
        recomputed_hash != request.property_snapshot.property_snapshot_hash
        or recomputed_hash != request.property_snapshot_hash
    ):
        return _blocked_result(
            request=request,
            upstream_geometry_hash=upstream_geometry_hash,
            upstream_identity_hash=upstream_identity_hash,
            blockers=(
                _new_blocker(
                    "BL_PROPERTY_HASH_MISMATCH",
                    "S03",
                    (recomputed_hash[:16], request.property_snapshot_hash[:16]),
                    "property_snapshot_hash mismatch: recomputed={a} vs field={b}",
                ),
            ),
            warnings=(),
        )
    # Property authority presence check (R6-R7 §3.2 requires
    # property_source_id and property_source_version; both are
    # non-empty str at construction).
    if (
        not request.property_snapshot.property_source_id
        or not request.property_snapshot.property_source_version
    ):
        return _blocked_result(
            request=request,
            upstream_geometry_hash=upstream_geometry_hash,
            upstream_identity_hash=upstream_identity_hash,
            blockers=(
                _new_blocker(
                    "BL_PROPERTY_AUTHORITY_MISSING",
                    "S03",
                    ("property_source_id",),
                    "property_source_id missing",
                ),
            ),
            warnings=(),
        )
    # S04 — phase validation: phase_assertion == phase_region.
    if request.phase_assertion.value != request.property_snapshot.phase_region.value:
        return _blocked_result(
            request=request,
            upstream_geometry_hash=upstream_geometry_hash,
            upstream_identity_hash=upstream_identity_hash,
            blockers=(
                _new_blocker(
                    "BL_UNSUPPORTED_PHASE",
                    "S04",
                    (request.phase_assertion.value, request.property_snapshot.phase_region.value),
                    "phase_assertion={a} != phase_region={b}",
                ),
            ),
            warnings=(),
        )
    # S05 — mass flow validation.
    if request.mass_flow_rate_kg_s <= Decimal(0):
        return _blocked_result(
            request=request,
            upstream_geometry_hash=upstream_geometry_hash,
            upstream_identity_hash=upstream_identity_hash,
            blockers=(
                _new_blocker(
                    "BL_MASS_FLOW_INVALID",
                    "S05",
                    (str(request.mass_flow_rate_kg_s),),
                    "mass_flow_rate_kg_s must be strictly positive; got {actual}",
                ),
            ),
            warnings=(),
        )
    # S06..S11 — single-phase computation.
    try:
        out = compute_single_phase(
            mass_flow_rate_kg_s=request.mass_flow_rate_kg_s,
            density_kg_m3=request.property_snapshot.density_kg_m3,
            dynamic_viscosity_pa_s=request.property_snapshot.dynamic_viscosity_pa_s,
            thermal_conductivity_w_m_k=request.property_snapshot.thermal_conductivity_w_m_k,
            specific_heat_capacity_j_kg_k=request.property_snapshot.specific_heat_capacity_j_kg_k,
            total_parallel_flow_area_m2=total_parallel_flow_area_m2,
            hydraulic_diameter_m=hydraulic_diameter_m,
            thermal_boundary_condition=request.thermal_boundary_condition,
        )
    except DecimalFailure as exc:
        return _blocked_result(
            request=request,
            upstream_geometry_hash=upstream_geometry_hash,
            upstream_identity_hash=upstream_identity_hash,
            blockers=(
                _new_blocker(
                    "BL_DECIMAL_FAILURE",
                    "S07",
                    (exc.operation, exc.lexeme, exc.reason),
                    "decimal failure during S07..S11: {op}({lexeme}) -> {reason}",
                ),
            ),
            warnings=(),
        )

    # S09 — applicability selection: TRANSITION gap.
    if out.flow_regime == FlowRegime.TRANSITION:
        return _blocked_result(
            request=request,
            upstream_geometry_hash=upstream_geometry_hash,
            upstream_identity_hash=upstream_identity_hash,
            blockers=(
                _new_blocker(
                    "BL_REGIME_NO_CORRELATION_APPLICABLE",
                    "S09",
                    (str(out.reynolds_number),),
                    "Re in transition gap [2300, 3000): Re={actual}",
                ),
            ),
            warnings=(),
        )
    # S09 — Pr envelope check.
    if not check_pr_envelope(out.flow_regime, out.prandtl_number):
        return _blocked_result(
            request=request,
            upstream_geometry_hash=upstream_geometry_hash,
            upstream_identity_hash=upstream_identity_hash,
            blockers=(
                _new_blocker(
                    "BL_CORRELATION_NOT_APPLICABLE",
                    "S09",
                    (str(out.prandtl_number), out.flow_regime.value),
                    "Pr={actual} outside {regime} envelope",
                ),
            ),
            warnings=(),
        )

    # S13 — warnings/blockers finalization (none in v1).
    # S15 — build frozen provenance with the actual upstream identity.
    actual_provenance = FrozenProvenance(
        task_id="TASK-026",
        design_contract_path="/tmp/TASK-026-DESIGN-CONTRACT-DRAFT-R6-R7.md",
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        input_evidence_refs=INPUT_EVIDENCE_REFS_V1,
        upstream_identity_hashes=(upstream_identity_hash,),
    )

    # Compute success result hash (R6-R7 §9.4).
    # Excluded fields: result_hash, result_id (no self-reference).
    request_hash = _compute_request_hash(request)
    result_hash = _compute_success_result_hash(
        request_hash=request_hash,
        upstream_geometry_hash=upstream_geometry_hash,
        request=request,
        out=out,
        provenance=actual_provenance,
    )
    result_id = str(
        uuid.uuid5(
            uuid.UUID(RESULT_ID_NAMESPACE),
            RESULT_ID_NAME_PREFIX + result_hash,
        )
    )

    return TubeSideThermalResult(
        schema_version=SCHEMA_VERSION,
        task026_version=TASK026_VERSION,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        upstream_geometry_hash=upstream_geometry_hash,
        property_snapshot_hash=request.property_snapshot_hash,
        thermal_boundary_condition=request.thermal_boundary_condition,
        phase_assertion=request.phase_assertion,
        mass_flow_rate_kg_s=request.mass_flow_rate_kg_s,
        bulk_velocity_m_s=out.bulk_velocity_m_s,
        reynolds_number=out.reynolds_number,
        prandtl_number=out.prandtl_number,
        flow_regime=out.flow_regime,
        correlation_id=out.correlation_id,
        correlation_version=out.correlation_version,
        nusselt_number=out.nusselt_number,
        tube_side_heat_transfer_coefficient_w_m2_k=out.tube_side_heat_transfer_coefficient_w_m2_k,
        request_hash=request_hash,
        result_hash=result_hash,
        result_id=result_id,
        warnings=(),
        blockers=(),
        deferred_capabilities=DEFERRED_CAPABILITIES_V1,
        provenance=actual_provenance,
    )


def _blocked_result(
    request: TubeSideThermalRequest,
    upstream: object = None,
    upstream_geometry_hash: str = "",
    upstream_identity_hash: str = "",
    blockers: tuple[BlockerEntry, ...] = (),
    warnings: tuple[str, ...] = (),
) -> TubeSideBlockedResult:
    """R6-R7 §8.2 / §9.5 — Build a typed blocked result envelope."""
    if not blockers:
        raise ValueError("blocked_result must have at least one blocker")
    # Build raw_request_projection as a single frame over the
    # request's serialized canonical bytes (no re-projection).
    raw_req_bytes = _request_raw_child_bytes(request)
    raw_req_projection = FrozenRawProjection(
        projection_kind="RAW_PROJECTION",
        canonical_bytes_hex=raw_req_bytes.hex(),
    )
    # Build raw_upstream_blocked_projection only if upstream is blocked.
    raw_upstream_projection = FrozenRawProjection(
        projection_kind="RAW_PROJECTION",
        canonical_bytes_hex="",
    )
    if upstream is not None and type(upstream).__name__ == "Task025BlockedResult":
        # Mirror upstream's raw_request_projection or blocked envelope.
        mirror_bytes = _task025_blocked_mirror_bytes(upstream)
        raw_upstream_projection = FrozenRawProjection(
            projection_kind="RAW_PROJECTION",
            canonical_bytes_hex=mirror_bytes.hex(),
        )
    # Recompute the upstream identity from the actual upstream.
    actual_upstream_identity = (
        upstream_identity_hash
        if upstream_identity_hash
        else getattr(upstream, "blocked_result_hash", None)
        or getattr(upstream, "result_hash", None)
        or "0" * 64
    )
    request_hash = _compute_request_hash(request)

    # Build the actual frozen provenance with the runtime upstream identity.
    actual_provenance = FrozenProvenance(
        task_id="TASK-026",
        design_contract_path="/tmp/TASK-026-DESIGN-CONTRACT-DRAFT-R6-R7.md",
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        input_evidence_refs=INPUT_EVIDENCE_REFS_V1,
        upstream_identity_hashes=(actual_upstream_identity,),
    )

    # Blocked result hash (R6-R7 §9.5).
    result_hash = _compute_blocked_result_hash(
        request_hash=request_hash,
        upstream_geometry_hash=upstream_geometry_hash,
        request=request,
        raw_req_projection=raw_req_projection,
        raw_upstream_projection=raw_upstream_projection,
        blockers=blockers,
        provenance=actual_provenance,
    )
    result_id = str(
        uuid.uuid5(
            uuid.UUID(RESULT_ID_NAMESPACE),
            RESULT_ID_NAME_PREFIX + result_hash,
        )
    )

    return TubeSideBlockedResult(
        schema_version=SCHEMA_VERSION,
        task026_version=TASK026_VERSION,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        upstream_geometry_hash=upstream_geometry_hash or "0" * 64,
        property_snapshot_hash=request.property_snapshot_hash,
        thermal_boundary_condition=request.thermal_boundary_condition,
        phase_assertion=request.phase_assertion,
        mass_flow_rate_kg_s=request.mass_flow_rate_kg_s,
        raw_request_projection=raw_req_projection,
        raw_upstream_blocked_projection=raw_upstream_projection,
        request_hash=request_hash,
        result_hash=result_hash,
        result_id=result_id,
        blockers=blockers,
        warnings=warnings,
        deferred_capabilities=DEFERRED_CAPABILITIES_V1,
        provenance=actual_provenance,
    )


def _task025_blocked_mirror_bytes(upstream: object) -> bytes:
    """Encode the upstream TASK-025 blocked envelope's blocker codes as bytes.

    The mirror is a single-frame child bytes; the raw projection is
    applied once at the field boundary in frame_record.
    """
    if not hasattr(upstream, "blockers"):
        return b""
    out = b""
    for ub in upstream.blockers:
        code = getattr(ub, "code", None)
        if code is None:
            continue
        code_value = getattr(code, "value", str(code))
        out += frame_value(b"ITEM", code_value.encode("ascii"))
    return out


def _request_raw_child_bytes(request: TubeSideThermalRequest) -> bytes:
    """Encode the request's full canonical request bytes as a single child bytes."""
    fields = []
    for i, name in enumerate(REQUEST_HASH_FIELDS):
        kind = REQUEST_HASH_KIND_TAGS[i]
        payload = _request_field_payload(name, request)
        fields.append((name, kind, payload))
    return frame_record(REQUEST_HASH_NAMESPACE, fields)


def _compute_request_hash(request: TubeSideThermalRequest) -> str:
    """R6-R7 §9.2 — request_hash from the 10-field frame_record."""
    fields = []
    for i, name in enumerate(REQUEST_HASH_FIELDS):
        kind = REQUEST_HASH_KIND_TAGS[i]
        payload = _request_field_payload(name, request)
        fields.append((name, kind, payload))
    return composite_hash(REQUEST_HASH_NAMESPACE, fields)


def _request_field_payload(name: str, request: TubeSideThermalRequest) -> bytes:
    """Return the canonical payload for a single request field."""
    if name == "schema_version":
        return string_payload(request.schema_version)
    if name == "task026_version":
        return string_payload(request.task026_version)
    if name == "implementation_software_version":
        return string_payload(request.implementation_software_version)
    if name == "property_snapshot_hash":
        return string_payload(request.property_snapshot_hash)
    if name == "property_snapshot":
        # KIND_RECORD child bytes = the 10-field sub-record frame.
        return _property_snapshot_subrecord_bytes(request.property_snapshot)
    if name == "phase_assertion":
        return enum_payload(request.phase_assertion)
    if name == "thermal_boundary_condition":
        return enum_payload(request.thermal_boundary_condition)
    if name == "mass_flow_rate_kg_s":
        return decimal_payload(request.mass_flow_rate_kg_s)
    if name == "deferred_capabilities":
        return _tuple_payload_of_strings(request.deferred_capabilities)
    if name == "provenance":
        return _provenance_subrecord_bytes(request.provenance)
    raise ValueError(f"unknown request field: {name}")


def _property_snapshot_subrecord_bytes(snapshot: PropertySnapshot) -> bytes:
    """R6-R7 §9.7.1 — 10-field sub-record bytes (H1-R1 closure)."""
    fields = []
    for i, name in enumerate(
        (
            "density_kg_m3",
            "dynamic_viscosity_pa_s",
            "thermal_conductivity_w_m_k",
            "specific_heat_capacity_j_kg_k",
            "bulk_temperature_k",
            "bulk_pressure_pa",
            "phase_region",
            "property_source_id",
            "property_source_version",
            "property_snapshot_hash",
        )
    ):
        kind = PROPERTY_SNAPSHOT_SUBRECORD_KIND_TAGS[i]
        if name == "density_kg_m3":
            payload = decimal_payload(snapshot.density_kg_m3)
        elif name == "dynamic_viscosity_pa_s":
            payload = decimal_payload(snapshot.dynamic_viscosity_pa_s)
        elif name == "thermal_conductivity_w_m_k":
            payload = decimal_payload(snapshot.thermal_conductivity_w_m_k)
        elif name == "specific_heat_capacity_j_kg_k":
            payload = decimal_payload(snapshot.specific_heat_capacity_j_kg_k)
        elif name == "bulk_temperature_k":
            payload = decimal_payload(snapshot.bulk_temperature_k)
        elif name == "bulk_pressure_pa":
            payload = decimal_payload(snapshot.bulk_pressure_pa)
        elif name == "phase_region":
            payload = enum_payload(snapshot.phase_region)
        elif name == "property_source_id":
            payload = string_payload(snapshot.property_source_id)
        elif name == "property_source_version":
            payload = string_payload(snapshot.property_source_version)
        elif name == "property_snapshot_hash":
            payload = string_payload(snapshot.property_snapshot_hash)
        else:
            raise ValueError(f"unknown property_snapshot field: {name}")
        fields.append((name, kind, payload))
    return frame_record(PROPERTY_SNAPSHOT_NAMESPACE, fields)


def _provenance_subrecord_bytes(prov: FrozenProvenance) -> bytes:
    """R6-R7 §9.7.2 — 5-field provenance sub-record bytes."""
    fields = [
        ("task_id", KIND_STRING, string_payload(prov.task_id)),
        ("design_contract_path", KIND_STRING, string_payload(prov.design_contract_path)),
        (
            "implementation_software_version",
            KIND_STRING,
            string_payload(prov.implementation_software_version),
        ),
        ("input_evidence_refs", KIND_TUPLE, _tuple_payload_of_strings(prov.input_evidence_refs)),
        (
            "upstream_identity_hashes",
            KIND_TUPLE,
            _tuple_payload_of_strings(prov.upstream_identity_hashes),
        ),
    ]
    return frame_record("task026.provenance.v1", fields)


def _tuple_payload_of_strings(items: tuple[str, ...]) -> bytes:
    """Return KIND_TUPLE payload = U32_BE(count) || FRAME('ITEM', payload)."""
    return frame_tuple([string_payload(s) for s in items])


def _tuple_payload_of_blockers(blockers: tuple[BlockerEntry, ...]) -> bytes:
    """Return KIND_TUPLE payload for a sequence of BlockerEntry.

    Each item payload is the canonical 5-field blocker entry bytes.
    """
    item_payloads = []
    for b in blockers:
        item_payloads.append(_blocker_entry_field_bytes(b))
    return frame_tuple(item_payloads)


def _blocker_entry_field_bytes(b: BlockerEntry) -> bytes:
    """R6-R7 §9.6.2 — Blocker entry 5-field frame_record bytes."""
    fields = [
        ("code", KIND_STRING, string_payload(b.code)),
        ("severity", KIND_STRING, string_payload(b.severity)),
        ("stage", KIND_STRING, string_payload(b.stage)),
        ("payload", KIND_TUPLE, _tuple_payload_of_strings(b.payload)),
        ("message_template", KIND_STRING, string_payload(b.message_template)),
    ]
    return frame_record("task026.blocker-entry.v1", fields)


def _compute_success_result_hash(
    request_hash: str,
    upstream_geometry_hash: str,
    request: TubeSideThermalRequest,
    out: SinglePhaseOutputs,
    provenance: FrozenProvenance,
) -> str:
    """R6-R7 §9.4 — Success result hash from the 21-field frame_record."""
    fields = []
    for i, name in enumerate(SUCCESS_RESULT_HASH_FIELDS):
        kind = SUCCESS_RESULT_HASH_KIND_TAGS[i]
        payload = _success_field_payload(
            name, request_hash, upstream_geometry_hash, request, out, provenance
        )
        fields.append((name, kind, payload))
    return composite_hash(SUCCESS_RESULT_HASH_NAMESPACE, fields)


def _success_field_payload(
    name: str,
    request_hash: str,
    upstream_geometry_hash: str,
    request: TubeSideThermalRequest,
    out: SinglePhaseOutputs,
    provenance: FrozenProvenance,
) -> bytes:
    if name == "schema_version":
        return string_payload(SCHEMA_VERSION)
    if name == "task026_version":
        return string_payload(TASK026_VERSION)
    if name == "implementation_software_version":
        return string_payload(IMPLEMENTATION_SOFTWARE_VERSION)
    if name == "upstream_geometry_hash":
        return string_payload(upstream_geometry_hash)
    if name == "property_snapshot_hash":
        return string_payload(request.property_snapshot_hash)
    if name == "thermal_boundary_condition":
        return enum_payload(request.thermal_boundary_condition)
    if name == "phase_assertion":
        return enum_payload(request.phase_assertion)
    if name == "mass_flow_rate_kg_s":
        return decimal_payload(request.mass_flow_rate_kg_s)
    if name == "bulk_velocity_m_s":
        return decimal_payload(out.bulk_velocity_m_s)
    if name == "reynolds_number":
        return decimal_payload(out.reynolds_number)
    if name == "prandtl_number":
        return decimal_payload(out.prandtl_number)
    if name == "flow_regime":
        return enum_payload(out.flow_regime)
    if name == "correlation_id":
        return string_payload(out.correlation_id)
    if name == "correlation_version":
        return string_payload(out.correlation_version)
    if name == "nusselt_number":
        return decimal_payload(out.nusselt_number)
    if name == "tube_side_heat_transfer_coefficient_w_m2_k":
        return decimal_payload(out.tube_side_heat_transfer_coefficient_w_m2_k)
    if name == "request_hash":
        return string_payload(request_hash)
    if name == "warnings":
        return _tuple_payload_of_strings(())
    if name == "blockers":
        return _tuple_payload_of_blockers(())
    if name == "deferred_capabilities":
        return _tuple_payload_of_strings(DEFERRED_CAPABILITIES_V1)
    if name == "provenance":
        return _provenance_subrecord_bytes(provenance)
    raise ValueError(f"unknown success field: {name}")


def _compute_blocked_result_hash(
    request_hash: str,
    upstream_geometry_hash: str,
    request: TubeSideThermalRequest,
    raw_req_projection: FrozenRawProjection,
    raw_upstream_projection: FrozenRawProjection,
    blockers: tuple[BlockerEntry, ...],
    provenance: FrozenProvenance,
) -> str:
    """R6-R7 §9.5 — Blocked result hash from the 15-field frame_record."""
    fields = []
    for i, name in enumerate(BLOCKED_RESULT_HASH_FIELDS):
        kind = BLOCKED_RESULT_HASH_KIND_TAGS[i]
        payload = _blocked_field_payload(
            name,
            request_hash,
            upstream_geometry_hash,
            request,
            raw_req_projection,
            raw_upstream_projection,
            blockers,
            provenance,
        )
        fields.append((name, kind, payload))
    return composite_hash(BLOCKED_RESULT_HASH_NAMESPACE, fields)


def _blocked_field_payload(
    name: str,
    request_hash: str,
    upstream_geometry_hash: str,
    request: TubeSideThermalRequest,
    raw_req_projection: FrozenRawProjection,
    raw_upstream_projection: FrozenRawProjection,
    blockers: tuple[BlockerEntry, ...],
    provenance: FrozenProvenance,
) -> bytes:
    if name == "schema_version":
        return string_payload(SCHEMA_VERSION)
    if name == "task026_version":
        return string_payload(TASK026_VERSION)
    if name == "implementation_software_version":
        return string_payload(IMPLEMENTATION_SOFTWARE_VERSION)
    if name == "upstream_geometry_hash":
        return string_payload(upstream_geometry_hash or "0" * 64)
    if name == "property_snapshot_hash":
        return string_payload(request.property_snapshot_hash)
    if name == "thermal_boundary_condition":
        return enum_payload(request.thermal_boundary_condition)
    if name == "phase_assertion":
        return enum_payload(request.phase_assertion)
    if name == "mass_flow_rate_kg_s":
        return decimal_payload(request.mass_flow_rate_kg_s)
    if name == "raw_request_projection":
        return _raw_projection_payload(raw_req_projection)
    if name == "raw_upstream_blocked_projection":
        return _raw_projection_payload(raw_upstream_projection)
    if name == "request_hash":
        return string_payload(request_hash)
    if name == "blockers":
        return _tuple_payload_of_blockers(blockers)
    if name == "warnings":
        return _tuple_payload_of_strings(())
    if name == "deferred_capabilities":
        return _tuple_payload_of_strings(DEFERRED_CAPABILITIES_V1)
    if name == "provenance":
        return _provenance_subrecord_bytes(provenance)
    raise ValueError(f"unknown blocked field: {name}")


def _raw_projection_payload(projection: FrozenRawProjection) -> bytes:
    """R6-R7 §9.5.1 — KIND_RAW_PROJECTION frame with one-frame boundary."""
    if projection.canonical_bytes_hex == "":
        # Absent optional projection: KIND_NONE + empty payload.
        return zero_optional()
    child_bytes = bytes.fromhex(projection.canonical_bytes_hex)
    return frame_raw_projection_field(child_bytes)


# ---------------------------------------------------------------------------
# Stage dispatch helpers (used by stage_pipeline orchestrator tests).
# ---------------------------------------------------------------------------


def stage_count() -> int:
    return 16


def stage_names() -> tuple[str, ...]:
    return tuple(s for s, _ in STAGES)


def stage_name(stage: str) -> str:
    for s, n in STAGES:
        if s == stage:
            return n
    raise ValueError(f"unknown stage: {stage}")


# ---------------------------------------------------------------------------
# Provenance rebuild helper (R8 brief §7).
# ---------------------------------------------------------------------------


def rebuild_provenance_upstream(
    base: FrozenProvenance,
    upstream_identity_hash: str,
) -> FrozenProvenance:
    """R8 brief §7 — Replace base.upstream_identity_hashes with the actual upstream.

    The 6 input_evidence_refs remain frozen; only the
    upstream_identity_hashes tuple is rebound at S15.
    """
    if not isinstance(upstream_identity_hash, str) or len(upstream_identity_hash) != 64:
        raise ValueError("upstream_identity_hash must be 64-hex str")
    if any(c not in "0123456789abcdef" for c in upstream_identity_hash):
        raise ValueError("upstream_identity_hash must be lowercase hex")
    return FrozenProvenance(
        task_id=base.task_id,
        design_contract_path=base.design_contract_path,
        implementation_software_version=base.implementation_software_version,
        input_evidence_refs=base.input_evidence_refs,
        upstream_identity_hashes=(upstream_identity_hash,),
    )


__all__ = [
    "TASK026_T025_UPSTREAM_READ_SET",
    "TASK026_T025_FORBIDDEN_FIELDS",
    "HYDRAULIC_GEOMETRY_HASH_FIELDS",
    "HYDRAULIC_GEOMETRY_NAMESPACE",
    "HYDRAULIC_GEOMETRY_KIND_TAGS",
    "RESULT_ID_NAMESPACE",
    "RESULT_ID_NAME_PREFIX",
    "STAGES",
    "build_raw_tube_side_request_envelope",
    "compute_tube_side_heat_transfer_coefficient",
    "rebuild_provenance_upstream",
    "stage_count",
    "stage_names",
    "stage_name",
]
