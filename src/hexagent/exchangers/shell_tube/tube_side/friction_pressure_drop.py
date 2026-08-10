"""TASK-027 Shell-and-Tube Tube-Side Single-Phase Straight-Tube Friction Pressure-Drop.

§16.1 — 26-code BlockerCode registry.
§9 — Laminar friction factor (f = 64/Re).
§9.2 — Turbulent friction factor (Colebrook-White implicit).
§9.1 — Darcy-Weisbach pressure drop.
§8 — Roughness authority handling.
§14 — Request and result schemas.
§15 — Hash and UUID contracts.
§13 — Decimal context and output quantization.
"""

from __future__ import annotations

import decimal
import enum
import hashlib
import uuid
from dataclasses import dataclass
from decimal import Context, Decimal, localcontext
from typing import Any, Final

_WORKING_PRECISION: Final[int] = 28


def _task027_decimal_context() -> Context:
    """Return a Decimal context with frozen TASK-027 parameters."""
    ctx = Context(
        prec=_WORKING_PRECISION,
        rounding=decimal.ROUND_HALF_EVEN,
    )
    return ctx


# ---------------------------------------------------------------------------
# §13.3 — Output quantization quanta
# ---------------------------------------------------------------------------
FRICTION_FACTOR_QUANTUM: Final[Decimal] = Decimal("0.00000001")
PRESSURE_DROP_QUANTUM: Final[Decimal] = Decimal("0.001")
LENGTH_QUANTUM_M: Final[Decimal] = Decimal("0.00000001")


# ---------------------------------------------------------------------------
# §9 — Reynolds number regime thresholds (frozen)
# ---------------------------------------------------------------------------
LAMINAR_UPPER_RE: Final[Decimal] = Decimal("2000")
TURBULENT_LOWER_RE: Final[Decimal] = Decimal("4000")
TURBULENT_UPPER_RE: Final[Decimal] = Decimal("100000000")


# ---------------------------------------------------------------------------
# §5 / §14.1 — Request schema
# ---------------------------------------------------------------------------
TASK027_REQUEST_SCHEMA_VERSION: Final[str] = "task027-r1.schema.v1"
TASK027_REQUEST_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "task025_valid_result",
    "task026_success_result",
    "property_snapshot",
    "property_snapshot_hash",
    "constant_density_path_assertion",
    "zero_net_elevation_change_assertion",
    "flow_direction_assertion",
    "roughness_authority",
    "request_hash",
)

REQUEST_HASH_NAMESPACE: Final[str] = "task027.request.v1"
SUCCESS_RESULT_HASH_NAMESPACE: Final[str] = "task027.success-result.v1"
BLOCKED_RESULT_HASH_NAMESPACE: Final[str] = "task027.blocked-result.v1"
RAW_BOUNDARY_BLOCKED_HASH_NAMESPACE: Final[str] = "task027.raw-boundary-blocked-result.v1"
RAW_PROJECTION_NAMESPACE: Final[str] = "task027.raw-projection.v1"
PROVENANCE_NAMESPACE: Final[str] = "task027.provenance.v1"
RESULT_ID_NAMESPACE: Final[str] = "a0270000-0000-5000-8000-000000000002"
RESULT_ID_NAME_PREFIX: Final[str] = "task027-result-v1::"

TASK027_SUCCESS_RESULT_SCHEMA_VERSION: Final[str] = "task027-r1.schema.v1"
TASK027_SUCCESS_RESULT_FIELD_COUNT: Final[int] = 18

TASK027_BLOCKED_RESULT_SCHEMA_VERSION: Final[str] = "task027-r1.schema.v1"
TASK027_BLOCKED_RESULT_FIELD_COUNT: Final[int] = 15

TASK027_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION: Final[str] = "task027-r1.schema.v1"
TASK027_RAW_BOUNDARY_BLOCKED_FIELD_COUNT: Final[int] = 6

IMPLEMENTATION_SOFTWARE_VERSION: Final[str] = "0.1.0"

SUPPORTED_PROFILE_IDS: Final[tuple[str, ...]] = ("profile-001",)

ROUGHNESS_SCHEMA_VERSION: Final[str] = "task027.roughness-authority.v1"
SELECTION_CONTRACT_VERSION: Final[str] = "task027.turbulent-selection.v1"


# ---------------------------------------------------------------------------
# §8 — Assertion enums
# ---------------------------------------------------------------------------
class AssertionState(enum.StrEnum):
    """§4 — Applicability assertion state."""

    TRUE = "TRUE"
    FALSE = "FALSE"


class FlowDirectionAssertion(enum.StrEnum):
    """§11 — Flow direction assertion."""

    START_TO_END = "START_TO_END"
    END_TO_START = "END_TO_START"


class RoughnessMode(enum.StrEnum):
    """§8 — Roughness semantic model."""

    EXPLICIT_ABSOLUTE_ROUGHNESS = "EXPLICIT_ABSOLUTE_ROUGHNESS"
    EXPLICIT_SMOOTH_PIPE_ASSERTION = "EXPLICIT_SMOOTH_PIPE_ASSERTION"


class FrictionFactorConvention(enum.StrEnum):
    """§5 — Friction factor convention."""

    DARCY = "DARCY"
    FANNING = "FANNING"


class PhaseType(enum.StrEnum):
    """§12 — Phase type."""

    LIQUID = "LIQUID"
    GAS = "GAS"


class RheologyType(enum.StrEnum):
    """§4.1 — Rheology type."""

    NEWTONIAN = "NEWTONIAN"
    NON_NEWTONIAN = "NON_NEWTONIAN"


# ---------------------------------------------------------------------------
# §16.1 — 26-code BlockerCode registry
# ---------------------------------------------------------------------------
class BlockerCode(enum.StrEnum):
    """§16.1 — Closed 26-code TASK-027 BlockerCode registry.

    Members are sorted alphabetically by lexical name; the textual
    ordering is part of the contract.
    """

    BL_T027_REQUEST_UNKNOWN_FIELD = "BL_T027_REQUEST_UNKNOWN_FIELD"
    BL_T027_RAW_INPUT_BOUNDARY_MALFORMED = "BL_T027_RAW_INPUT_BOUNDARY_MALFORMED"
    BL_T027_UPSTREAM_TASK025_BLOCKED = "BL_T027_UPSTREAM_TASK025_BLOCKED"
    BL_T027_UPSTREAM_TASK026_RAW_BLOCKED = "BL_T027_UPSTREAM_TASK026_RAW_BLOCKED"
    BL_T027_UPSTREAM_TASK026_TYPED_BLOCKED = "BL_T027_UPSTREAM_TASK026_TYPED_BLOCKED"
    BL_T027_UPSTREAM_IDENTITY_MISMATCH = "BL_T027_UPSTREAM_IDENTITY_MISMATCH"
    BL_T027_PROPERTY_SNAPSHOT_HASH_MISMATCH = "BL_T027_PROPERTY_SNAPSHOT_HASH_MISMATCH"
    BL_T027_UNSUPPORTED_REYNOLDS_REGIME = "BL_T027_UNSUPPORTED_REYNOLDS_REGIME"
    BL_T027_UNSUPPORTED_PHASE = "BL_T027_UNSUPPORTED_PHASE"
    BL_T027_UNSUPPORTED_RHEOLOGY = "BL_T027_UNSUPPORTED_RHEOLOGY"
    BL_T027_FRICTION_FACTOR_CONVENTION_UNSUPPORTED = (
        "BL_T027_FRICTION_FACTOR_CONVENTION_UNSUPPORTED"
    )
    BL_T027_APPLICABILITY_ASSERTION_MISSING = "BL_T027_APPLICABILITY_ASSERTION_MISSING"
    BL_T027_APPLICABILITY_ASSERTION_FALSE = "BL_T027_APPLICABILITY_ASSERTION_FALSE"
    BL_T027_FLOW_DIRECTION_UNSUPPORTED = "BL_T027_FLOW_DIRECTION_UNSUPPORTED"
    BL_T027_DARCY_WEISBACH_SOURCE_NOT_ADMITTED = "BL_T027_DARCY_WEISBACH_SOURCE_NOT_ADMITTED"
    BL_T027_PARTIAL_RESULT_FORBIDDEN = "BL_T027_PARTIAL_RESULT_FORBIDDEN"
    BL_T027_ROUGHNESS_AUTHORITY_MISSING = "BL_T027_ROUGHNESS_AUTHORITY_MISSING"
    BL_T027_ROUGHNESS_AUTHORITY_INVALID = "BL_T027_ROUGHNESS_AUTHORITY_INVALID"
    BL_T027_ROUGHNESS_AUTHORITY_HASH_MISMATCH = "BL_T027_ROUGHNESS_AUTHORITY_HASH_MISMATCH"
    BL_T027_ROUGHNESS_SOURCE_ID_MISSING = "BL_T027_ROUGHNESS_SOURCE_ID_MISSING"
    BL_T027_ROUGHNESS_SOURCE_LOCATION_MISSING = "BL_T027_ROUGHNESS_SOURCE_LOCATION_MISSING"
    BL_T027_ROUGHNESS_EVIDENCE_MISSING = "BL_T027_ROUGHNESS_EVIDENCE_MISSING"
    BL_T027_ROUGHNESS_VALUE_NONFINITE = "BL_T027_ROUGHNESS_VALUE_NONFINITE"
    BL_T027_ROUGHNESS_VALUE_NONPOSITIVE = "BL_T027_ROUGHNESS_VALUE_NONPOSITIVE"
    BL_T027_RELATIVE_ROUGHNESS_OUT_OF_ENVELOPE = "BL_T027_RELATIVE_ROUGHNESS_OUT_OF_ENVELOPE"
    BL_T027_TURBULENT_SOLVER_FAILURE = "BL_T027_TURBULENT_SOLVER_FAILURE"

    @property
    def canonical_utf8_bytes(self) -> bytes:
        return self.value.encode("ascii")


# §16.1 — Exact member count must remain 26.
_BLOCKER_CODE_COUNT: Final[int] = 26
assert len(BlockerCode.__members__) == _BLOCKER_CODE_COUNT, (
    f"BlockerCode must have exactly {_BLOCKER_CODE_COUNT} members"
)


# ---------------------------------------------------------------------------
# §16.1 — Ordering key mapping (frozen)
# ---------------------------------------------------------------------------
_BLOCKER_ORDERING_KEYS: Final[dict[BlockerCode, str]] = {
    BlockerCode.BL_T027_REQUEST_UNKNOWN_FIELD: "00:BL_T027_REQUEST_UNKNOWN_FIELD",
    BlockerCode.BL_T027_RAW_INPUT_BOUNDARY_MALFORMED: "01:BL_T027_RAW_INPUT_BOUNDARY_MALFORMED",
    BlockerCode.BL_T027_UPSTREAM_TASK025_BLOCKED: "02:BL_T027_UPSTREAM_TASK025_BLOCKED",
    BlockerCode.BL_T027_UPSTREAM_TASK026_RAW_BLOCKED: "03:BL_T027_UPSTREAM_TASK026_RAW_BLOCKED",
    BlockerCode.BL_T027_UPSTREAM_TASK026_TYPED_BLOCKED: "04:BL_T027_UPSTREAM_TASK026_TYPED_BLOCKED",
    BlockerCode.BL_T027_UPSTREAM_IDENTITY_MISMATCH: "05:BL_T027_UPSTREAM_IDENTITY_MISMATCH",
    BlockerCode.BL_T027_PROPERTY_SNAPSHOT_HASH_MISMATCH: "06:BL_T027_PROPERTY_SNAPSHOT_HASH_MISMATCH",
    BlockerCode.BL_T027_UNSUPPORTED_REYNOLDS_REGIME: "07:BL_T027_UNSUPPORTED_REYNOLDS_REGIME",
    BlockerCode.BL_T027_UNSUPPORTED_PHASE: "08:BL_T027_UNSUPPORTED_PHASE",
    BlockerCode.BL_T027_UNSUPPORTED_RHEOLOGY: "09:BL_T027_UNSUPPORTED_RHEOLOGY",
    BlockerCode.BL_T027_FRICTION_FACTOR_CONVENTION_UNSUPPORTED: "10:BL_T027_FRICTION_FACTOR_CONVENTION_UNSUPPORTED",
    BlockerCode.BL_T027_APPLICABILITY_ASSERTION_MISSING: "11:BL_T027_APPLICABILITY_ASSERTION_MISSING",
    BlockerCode.BL_T027_APPLICABILITY_ASSERTION_FALSE: "12:BL_T027_APPLICABILITY_ASSERTION_FALSE",
    BlockerCode.BL_T027_FLOW_DIRECTION_UNSUPPORTED: "13:BL_T027_FLOW_DIRECTION_UNSUPPORTED",
    BlockerCode.BL_T027_DARCY_WEISBACH_SOURCE_NOT_ADMITTED: "14:BL_T027_DARCY_WEISBACH_SOURCE_NOT_ADMITTED",
    BlockerCode.BL_T027_PARTIAL_RESULT_FORBIDDEN: "15:BL_T027_PARTIAL_RESULT_FORBIDDEN",
    BlockerCode.BL_T027_ROUGHNESS_AUTHORITY_MISSING: "16:BL_T027_ROUGHNESS_AUTHORITY_MISSING",
    BlockerCode.BL_T027_ROUGHNESS_AUTHORITY_INVALID: "17:BL_T027_ROUGHNESS_AUTHORITY_INVALID",
    BlockerCode.BL_T027_ROUGHNESS_AUTHORITY_HASH_MISMATCH: "18:BL_T027_ROUGHNESS_AUTHORITY_HASH_MISMATCH",
    BlockerCode.BL_T027_ROUGHNESS_SOURCE_ID_MISSING: "19:BL_T027_ROUGHNESS_SOURCE_ID_MISSING",
    BlockerCode.BL_T027_ROUGHNESS_SOURCE_LOCATION_MISSING: "20:BL_T027_ROUGHNESS_SOURCE_LOCATION_MISSING",
    BlockerCode.BL_T027_ROUGHNESS_EVIDENCE_MISSING: "21:BL_T027_ROUGHNESS_EVIDENCE_MISSING",
    BlockerCode.BL_T027_ROUGHNESS_VALUE_NONFINITE: "22:BL_T027_ROUGHNESS_VALUE_NONFINITE",
    BlockerCode.BL_T027_ROUGHNESS_VALUE_NONPOSITIVE: "23:BL_T027_ROUGHNESS_VALUE_NONPOSITIVE",
    BlockerCode.BL_T027_RELATIVE_ROUGHNESS_OUT_OF_ENVELOPE: "24:BL_T027_RELATIVE_ROUGHNESS_OUT_OF_ENVELOPE",
    BlockerCode.BL_T027_TURBULENT_SOLVER_FAILURE: "25:BL_T027_TURBULENT_SOLVER_FAILURE",
}

# Canonical message map
_BLOCKER_MESSAGES: Final[dict[BlockerCode, str]] = {
    BlockerCode.BL_T027_REQUEST_UNKNOWN_FIELD: "The TASK-027 raw request contains one or more unknown fields.",
    BlockerCode.BL_T027_RAW_INPUT_BOUNDARY_MALFORMED: "The TASK-027 raw input boundary is malformed.",
    BlockerCode.BL_T027_UPSTREAM_TASK025_BLOCKED: "TASK-025 upstream input is blocked.",
    BlockerCode.BL_T027_UPSTREAM_TASK026_RAW_BLOCKED: "TASK-026 raw upstream input is blocked.",
    BlockerCode.BL_T027_UPSTREAM_TASK026_TYPED_BLOCKED: "TASK-026 typed upstream result is blocked.",
    BlockerCode.BL_T027_UPSTREAM_IDENTITY_MISMATCH: "TASK-025 and TASK-026 upstream identities are inconsistent.",
    BlockerCode.BL_T027_PROPERTY_SNAPSHOT_HASH_MISMATCH: "The supplied property snapshot hash is inconsistent.",
    BlockerCode.BL_T027_UNSUPPORTED_REYNOLDS_REGIME: "The Reynolds number is outside the supported friction regimes.",
    BlockerCode.BL_T027_UNSUPPORTED_PHASE: "The supplied phase is not supported by TASK-027 V1.",
    BlockerCode.BL_T027_UNSUPPORTED_RHEOLOGY: "The supplied rheology is not supported by TASK-027 V1.",
    BlockerCode.BL_T027_FRICTION_FACTOR_CONVENTION_UNSUPPORTED: "The friction-factor convention is not Darcy.",
    BlockerCode.BL_T027_APPLICABILITY_ASSERTION_MISSING: "A required TASK-027 applicability assertion is missing.",
    BlockerCode.BL_T027_APPLICABILITY_ASSERTION_FALSE: "A required TASK-027 applicability assertion is false.",
    BlockerCode.BL_T027_FLOW_DIRECTION_UNSUPPORTED: "The supplied flow direction is not supported by TASK-027 V1.",
    BlockerCode.BL_T027_DARCY_WEISBACH_SOURCE_NOT_ADMITTED: "The Darcy-Weisbach pressure-drop relation has not been admitted.",
    BlockerCode.BL_T027_PARTIAL_RESULT_FORBIDDEN: "A blocked TASK-027 result must not contain partial engineering outputs.",
    BlockerCode.BL_T027_ROUGHNESS_AUTHORITY_MISSING: "No roughness authority record was provided.",
    BlockerCode.BL_T027_ROUGHNESS_AUTHORITY_INVALID: "The roughness authority record is invalid.",
    BlockerCode.BL_T027_ROUGHNESS_AUTHORITY_HASH_MISMATCH: "The roughness authority hash does not match.",
    BlockerCode.BL_T027_ROUGHNESS_SOURCE_ID_MISSING: "The roughness source identification is missing.",
    BlockerCode.BL_T027_ROUGHNESS_SOURCE_LOCATION_MISSING: "The roughness source location is missing.",
    BlockerCode.BL_T027_ROUGHNESS_EVIDENCE_MISSING: "The roughness evidence reference is missing.",
    BlockerCode.BL_T027_ROUGHNESS_VALUE_NONFINITE: "The roughness value is not finite.",
    BlockerCode.BL_T027_ROUGHNESS_VALUE_NONPOSITIVE: "The roughness value is not positive.",
    BlockerCode.BL_T027_RELATIVE_ROUGHNESS_OUT_OF_ENVELOPE: "The relative roughness is outside the Colebrook-White applicability envelope.",
    BlockerCode.BL_T027_TURBULENT_SOLVER_FAILURE: "The implicit Colebrook-White solver failed to establish convergence under the future solver contract.",
}


# ---------------------------------------------------------------------------
# §16.1 — Blocker entry record
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Task027BlockerEntry:
    """§16.1 — Task027BlockerEntry: code + field_path + message_key + evidence_refs."""

    code: BlockerCode
    field_path: tuple[str, ...]
    message_key: str
    evidence_refs: tuple[str, ...]


def emit_blocker(
    code: BlockerCode,
    field_path: tuple[str, ...] | list[str] | str,
    message_key: str,
    evidence_refs: tuple[str, ...] | list[str] = (),
) -> Task027BlockerEntry:
    """Emit one blocker entry; collapse unknown codes to unknown field."""
    if isinstance(field_path, str):
        field_path_tuple: tuple[str, ...] = (field_path,)
    else:
        field_path_tuple = tuple(field_path)
    if not all(isinstance(p, str) and p for p in field_path_tuple):
        raise ValueError(f"field_path entries must be non-empty str: {field_path_tuple!r}")
    if isinstance(evidence_refs, (list, tuple)):
        evidence_refs_tuple: tuple[str, ...] = tuple(evidence_refs)
    else:
        raise TypeError(f"evidence_refs must be tuple/list of str: {type(evidence_refs).__name__}")
    if not all(isinstance(r, str) and r for r in evidence_refs_tuple):
        raise ValueError(f"evidence_refs entries must be non-empty str: {evidence_refs_tuple!r}")
    if not isinstance(code, BlockerCode):
        code = BlockerCode.BL_T027_REQUEST_UNKNOWN_FIELD
    return Task027BlockerEntry(
        code=code,
        field_path=field_path_tuple,
        message_key=message_key,
        evidence_refs=evidence_refs_tuple,
    )


def collapse_blockers(
    entries: list[Task027BlockerEntry],
) -> tuple[Task027BlockerEntry, ...]:
    """Sort and deduplicate entries by ordering key; return tuple."""
    seen_codes: set[BlockerCode] = set()
    sorted_entries = sorted(entries, key=lambda e: _BLOCKER_ORDERING_KEYS[e.code])
    unique: list[Task027BlockerEntry] = []
    for entry in sorted_entries:
        if entry.code in seen_codes:
            continue
        seen_codes.add(entry.code)
        unique.append(entry)
    return tuple(unique)


# ---------------------------------------------------------------------------
# §16.1 — Blocker registry helper
# ---------------------------------------------------------------------------
BLOCKER_REGISTRY_COUNT: Final[int] = 26
UNIQUE_BLOCKER_CODE_COUNT: Final[int] = 26
UNIQUE_ORDERING_KEY_COUNT: Final[int] = 26


def get_blocker_ordering_key(code: BlockerCode) -> str:
    """Return the frozen ordering key for a blocker code."""
    return _BLOCKER_ORDERING_KEYS[code]


def get_blocker_message(code: BlockerCode) -> str:
    """Return the frozen canonical message for a blocker code."""
    return _BLOCKER_MESSAGES[code]


# ---------------------------------------------------------------------------
# §8 — Roughness authority records
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AbsoluteRoughnessAuthority:
    """§8.1.1 — Absolute roughness authority record (EXPLICIT_ABSOLUTE_ROUGHNESS)."""

    schema_version: str
    authority_id: str
    roughness_mode: RoughnessMode
    absolute_roughness_m: Decimal
    source_type: str
    source_id: str
    source_version: str
    source_location: str
    permission_status: str
    evidence_refs: tuple[str, ...]
    authority_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != ROUGHNESS_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be '{ROUGHNESS_SCHEMA_VERSION}'")
        if self.roughness_mode != RoughnessMode.EXPLICIT_ABSOLUTE_ROUGHNESS:
            raise ValueError("roughness_mode must be EXPLICIT_ABSOLUTE_ROUGHNESS")
        if not isinstance(self.absolute_roughness_m, Decimal):
            raise ValueError("absolute_roughness_m must be Decimal")
        if not self.absolute_roughness_m.is_finite():
            raise ValueError("absolute_roughness_m must be finite")
        if self.absolute_roughness_m <= Decimal(0):
            raise ValueError("absolute_roughness_m must be positive")
        if not isinstance(self.evidence_refs, tuple):
            raise ValueError("evidence_refs must be tuple")


@dataclass(frozen=True)
class SmoothRoughnessAuthority:
    """§8.1.2 — Smooth pipe assertion authority record (EXPLICIT_SMOOTH_PIPE_ASSERTION)."""

    schema_version: str
    authority_id: str
    roughness_mode: RoughnessMode
    source_type: str
    source_id: str
    source_version: str
    source_location: str
    permission_status: str
    evidence_refs: tuple[str, ...]
    authority_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != ROUGHNESS_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be '{ROUGHNESS_SCHEMA_VERSION}'")
        if self.roughness_mode != RoughnessMode.EXPLICIT_SMOOTH_PIPE_ASSERTION:
            raise ValueError("roughness_mode must be EXPLICIT_SMOOTH_PIPE_ASSERTION")


RoughnessAuthority = AbsoluteRoughnessAuthority | SmoothRoughnessAuthority


# ---------------------------------------------------------------------------
# §8.3 — Turbulent selection contract
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TurbulentSelectionContract:
    """§8.3 — Turbulent selection contract record."""

    selection_contract_version: str
    selected_correlation_id: str
    selected_correlation_source_refs: tuple[str, ...]
    friction_factor_convention: FrictionFactorConvention
    re_min: Decimal
    re_max: Decimal
    relative_roughness_variable: str
    relative_roughness_min: Decimal
    relative_roughness_max: Decimal
    unsupported_gap_policy: str
    out_of_envelope_policy: str
    roughness_authority_contract_version: str


# ---------------------------------------------------------------------------
# §8.2 — Decimal identity pipeline for absolute roughness
# ---------------------------------------------------------------------------
def quantize_roughness(value: Decimal) -> Decimal:
    """Quantize roughness to LENGTH_QUANTUM_M using ROUND_HALF_EVEN."""
    ctx = _task027_decimal_context()
    with localcontext(ctx):
        quantized = value.quantize(LENGTH_QUANTUM_M)
    if not quantized.is_finite():
        raise ValueError("Quantized roughness is not finite")
    if quantized <= Decimal(0):
        raise ValueError("Quantized roughness must be positive")
    return quantized


def validate_roughness_authority(
    roughness_authority: RoughnessAuthority | None,
    roughness_authority_hash: str,
) -> tuple[RoughnessAuthority | None, list[Task027BlockerEntry]]:
    """Validate roughness authority and return (authority, blockers)."""
    blockers: list[Task027BlockerEntry] = []

    if roughness_authority is None:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_ROUGHNESS_AUTHORITY_MISSING,
                "roughness_authority",
                get_blocker_message(BlockerCode.BL_T027_ROUGHNESS_AUTHORITY_MISSING),
            )
        )
        return None, blockers

    # Validate schema version
    if roughness_authority.schema_version != ROUGHNESS_SCHEMA_VERSION:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_ROUGHNESS_AUTHORITY_INVALID,
                "roughness_authority.schema_version",
                get_blocker_message(BlockerCode.BL_T027_ROUGHNESS_AUTHORITY_INVALID),
            )
        )
        return roughness_authority, blockers

    # Validate source_id
    if not roughness_authority.source_id:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_ROUGHNESS_SOURCE_ID_MISSING,
                "roughness_authority.source_id",
                get_blocker_message(BlockerCode.BL_T027_ROUGHNESS_SOURCE_ID_MISSING),
            )
        )

    # Validate source_location
    if not roughness_authority.source_location:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_ROUGHNESS_SOURCE_LOCATION_MISSING,
                "roughness_authority.source_location",
                get_blocker_message(BlockerCode.BL_T027_ROUGHNESS_SOURCE_LOCATION_MISSING),
            )
        )

    # Validate evidence_refs
    if not roughness_authority.evidence_refs:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_ROUGHNESS_EVIDENCE_MISSING,
                "roughness_authority.evidence_refs",
                get_blocker_message(BlockerCode.BL_T027_ROUGHNESS_EVIDENCE_MISSING),
            )
        )

    # Validate authority hash (recompute and compare)
    computed_hash = _compute_roughness_authority_hash(roughness_authority)
    if computed_hash != roughness_authority_hash:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_ROUGHNESS_AUTHORITY_HASH_MISMATCH,
                "roughness_authority.authority_hash",
                get_blocker_message(BlockerCode.BL_T027_ROUGHNESS_AUTHORITY_HASH_MISMATCH),
            )
        )

    # Validate absolute roughness if applicable
    if isinstance(roughness_authority, AbsoluteRoughnessAuthority):
        if not roughness_authority.absolute_roughness_m.is_finite():
            blockers.append(
                emit_blocker(
                    BlockerCode.BL_T027_ROUGHNESS_VALUE_NONFINITE,
                    "roughness_authority.absolute_roughness_m",
                    get_blocker_message(BlockerCode.BL_T027_ROUGHNESS_VALUE_NONFINITE),
                )
            )
        elif roughness_authority.absolute_roughness_m <= Decimal(0):
            blockers.append(
                emit_blocker(
                    BlockerCode.BL_T027_ROUGHNESS_VALUE_NONPOSITIVE,
                    "roughness_authority.absolute_roughness_m",
                    get_blocker_message(BlockerCode.BL_T027_ROUGHNESS_VALUE_NONPOSITIVE),
                )
            )

    return roughness_authority, blockers


def _compute_roughness_authority_hash(authority: RoughnessAuthority) -> str:
    """Compute the roughness authority hash using TASK025_TASK026_TYPED_FRAMED_BYTES."""
    if isinstance(authority, AbsoluteRoughnessAuthority):
        fields = [
            ("schema_version", KIND_STRING, authority.schema_version.encode("utf-8")),
            ("authority_id", KIND_STRING, authority.authority_id.encode("utf-8")),
            ("roughness_mode", KIND_ENUM, authority.roughness_mode.value.encode("ascii")),
            (
                "absolute_roughness_m",
                KIND_DECIMAL,
                str(authority.absolute_roughness_m).encode("utf-8"),
            ),
            ("source_type", KIND_ENUM, authority.source_type.encode("ascii")),
            ("source_id", KIND_STRING, authority.source_id.encode("utf-8")),
            ("source_version", KIND_STRING, authority.source_version.encode("utf-8")),
            ("source_location", KIND_STRING, authority.source_location.encode("utf-8")),
            ("permission_status", KIND_ENUM, authority.permission_status.encode("ascii")),
            ("evidence_refs", KIND_TUPLE, _encode_tuple(authority.evidence_refs)),
        ]
    else:
        fields = [
            ("schema_version", KIND_STRING, authority.schema_version.encode("utf-8")),
            ("authority_id", KIND_STRING, authority.authority_id.encode("utf-8")),
            ("roughness_mode", KIND_ENUM, authority.roughness_mode.value.encode("ascii")),
            ("source_type", KIND_ENUM, authority.source_type.encode("ascii")),
            ("source_id", KIND_STRING, authority.source_id.encode("utf-8")),
            ("source_version", KIND_STRING, authority.source_version.encode("utf-8")),
            ("source_location", KIND_STRING, authority.source_location.encode("utf-8")),
            ("permission_status", KIND_ENUM, authority.permission_status.encode("ascii")),
            ("evidence_refs", KIND_TUPLE, _encode_tuple(authority.evidence_refs)),
        ]

    framed = frame_record(ROUGHNESS_SCHEMA_VERSION, fields)
    return hashlib.sha256(framed).hexdigest()


# ---------------------------------------------------------------------------
# Canonical framing primitives (shared from canonical.py)
# ---------------------------------------------------------------------------
KIND_NONE: Final[bytes] = b"NONE"
KIND_STRING: Final[bytes] = b"STRING"
KIND_DECIMAL: Final[bytes] = b"DECIMAL"
KIND_ENUM: Final[bytes] = b"ENUM"
KIND_TUPLE: Final[bytes] = b"TUPLE"
KIND_RECORD: Final[bytes] = b"RECORD"
KIND_RAW_PROJECTION: Final[bytes] = b"RAW_PROJECTION"


def _u32_be(n: int) -> bytes:
    """Encode integer as big-endian u32."""
    import struct

    return struct.pack(">I", n)


def _u64_be(n: int) -> bytes:
    """Encode integer as big-endian u64."""
    import struct

    return struct.pack(">Q", n)


def frame_value(kind_tag_ascii: bytes, payload_bytes: bytes) -> bytes:
    """Universal labeled-record framing for a single value."""
    kind_tag = (
        kind_tag_ascii if isinstance(kind_tag_ascii, bytes) else kind_tag_ascii.encode("ascii")
    )
    payload = payload_bytes if isinstance(payload_bytes, bytes) else payload_bytes.encode("ascii")
    return _u32_be(len(kind_tag)) + kind_tag + _u64_be(len(payload)) + payload


def frame_record(node_namespace: str, fields: list[tuple[str, bytes, bytes]]) -> bytes:
    """HASH_RECORD canonical framing."""
    ns = node_namespace.encode("utf-8")
    out = _u32_be(len(ns)) + ns + _u32_be(len(fields))
    for field_name, field_kind_tag, field_payload in fields:
        out += (
            _u32_be(len(field_name))
            + field_name.encode("utf-8")
            + frame_value(field_kind_tag, field_payload)
        )
    return out


def _encode_tuple(items: tuple[str, ...]) -> bytes:
    """Encode a tuple of strings using frozen TUPLE framing.

    Frozen encoding: _u32_be(count) + for each item: _u32_be(len) + item_bytes.
    No per-item kind tags, u32 length prefix.
    """
    out = _u32_be(len(items))
    for item in items:
        out += _u32_be(len(item)) + item.encode("utf-8")
    return out


def sha256_hex(framed_bytes: bytes) -> str:
    """Return the 64-lowercase-hex SHA-256 of the framed bytes."""
    return hashlib.sha256(framed_bytes).hexdigest()


# ---------------------------------------------------------------------------
# §9 — Friction factor computations
# ---------------------------------------------------------------------------
def compute_laminar_friction_factor(reynolds: Decimal) -> Decimal:
    """§9 — Laminar friction factor: f_D = 64 / Re.

    Applicability: 0 < Re <= 2000.
    """
    if reynolds <= Decimal(0):
        raise ValueError("Reynolds must be positive for laminar friction factor")
    if reynolds > LAMINAR_UPPER_RE:
        raise ValueError("Reynolds exceeds laminar upper bound")

    ctx = _task027_decimal_context()
    with localcontext(ctx):
        f_d = Decimal(64) / reynolds
    return f_d


class ColebrookWhiteConvergenceError(Exception):
    """Raised when the Colebrook-White solver fails to converge.

    This is an internal deterministic failure signal. Callers must convert
    this into BL_T027_TURBULENT_SOLVER_FAILURE and return a blocked result.
    """


def compute_colebrook_white(
    reynolds: Decimal,
    relative_roughness: Decimal,
    tolerance: Decimal = Decimal("1e-12"),
    max_iterations: int = 100,
) -> Decimal:
    """§9.2 — Colebrook-White implicit friction factor solver.

    The Colebrook-White equation:
        1/sqrt(f) = -2*log10(epsilon/(3.7*D) + 2.51/(Re*sqrt(f)))

    We solve for f in the domain [0.004, 0.100].
    Uses fixed-point iteration with Swamee-Jain initial guess.

    Raises ColebrookWhiteConvergenceError on non-convergence (fail-closed).
    No partial result is ever returned.
    """
    if reynolds < TURBULENT_LOWER_RE or reynolds > TURBULENT_UPPER_RE:
        raise ValueError(
            f"Reynolds must be in [{TURBULENT_LOWER_RE}, {TURBULENT_UPPER_RE}] for Colebrook-White"
        )
    if relative_roughness < Decimal(0) or relative_roughness > Decimal("0.05"):
        raise ValueError("Relative roughness must be in [0, 0.05]")

    import math

    # Swamee-Jain initial guess (explicit approximation)
    re_f = float(reynolds)
    eps_d = float(relative_roughness)
    f_guess = 0.25 / (math.log10(eps_d / 3.7 + 5.74 / re_f**0.9)) ** 2
    f_val = float(max(0.004, min(0.100, f_guess)))

    converged = False
    # Fixed-point iteration: f = (1 / (-2*log10(eps_D/3.7 + 2.51/(Re*sqrt(f)))))^2
    for _ in range(max_iterations):
        sqrt_f = math.sqrt(f_val)
        term = eps_d / 3.7 + 2.51 / (re_f * sqrt_f)
        if term <= 0 or not math.isfinite(term):
            break
        f_new = 1.0 / (2.0 * math.log10(term)) ** 2
        if not math.isfinite(f_new):
            break
        if abs(f_new - f_val) < float(tolerance):
            f_val = f_new
            converged = True
            break
        f_val = f_new

    if not converged:
        raise ColebrookWhiteConvergenceError(
            f"Colebrook-White solver did not converge within {max_iterations} iterations "
            f"for Re={reynolds}, epsilon/D={relative_roughness}"
        )

    result = Decimal(str(f_val))
    # Clamp to domain
    if result < Decimal("0.004"):
        result = Decimal("0.004")
    elif result > Decimal("0.100"):
        result = Decimal("0.100")
    return result


def compute_turbulent_friction_factor_safe(
    reynolds: Decimal,
    relative_roughness: Decimal,
    tolerance: Decimal = Decimal("1e-12"),
    max_iterations: int = 100,
) -> tuple[Decimal | None, list[Task027BlockerEntry]]:
    """§9.2 safe wrapper — Colebrook-White with fail-closed propagation.

    Returns (friction_factor, blockers). On convergence, friction_factor is
    set and blockers is empty. On non-convergence, friction_factor is None
    and blockers contains BL_T027_TURBULENT_SOLVER_FAILURE.

    This is the frozen-authorized propagation boundary for solver failure.
    """
    try:
        f = compute_colebrook_white(reynolds, relative_roughness, tolerance, max_iterations)
        return f, []
    except ColebrookWhiteConvergenceError:
        blocker = emit_blocker(
            BlockerCode.BL_T027_TURBULENT_SOLVER_FAILURE,
            "compute_colebrook_white",
            get_blocker_message(BlockerCode.BL_T027_TURBULENT_SOLVER_FAILURE),
        )
        return None, [blocker]


# ---------------------------------------------------------------------------
# §9.1 — Darcy-Weisbach pressure drop
# ---------------------------------------------------------------------------
def compute_pressure_drop(
    darcy_friction_factor: Decimal,
    friction_length_m: Decimal,
    hydraulic_diameter_m: Decimal,
    density_kg_m3: Decimal,
    bulk_velocity_m_s: Decimal,
) -> Decimal:
    """§9.1 — Darcy-Weisbach straight-tube distributed-friction pressure drop.

    Delta_P = f_D * (L / D) * (rho * V^2 / 2)
    """
    if darcy_friction_factor <= Decimal(0):
        raise ValueError("darcy_friction_factor must be positive")
    if friction_length_m <= Decimal(0):
        raise ValueError("friction_length_m must be positive")
    if hydraulic_diameter_m <= Decimal(0):
        raise ValueError("hydraulic_diameter_m must be positive")
    if density_kg_m3 <= Decimal(0):
        raise ValueError("density_kg_m3 must be positive")
    if bulk_velocity_m_s <= Decimal(0):
        raise ValueError("bulk_velocity_m_s must be positive")

    ctx = _task027_decimal_context()
    with localcontext(ctx):
        delta_p = (
            darcy_friction_factor
            * (friction_length_m / hydraulic_diameter_m)
            * (density_kg_m3 * bulk_velocity_m_s ** Decimal(2) / Decimal(2))
        )
    return delta_p


# ---------------------------------------------------------------------------
# §8 — Relative roughness computation
# ---------------------------------------------------------------------------
def compute_relative_roughness(
    absolute_roughness_m: Decimal,
    hydraulic_diameter_m: Decimal,
) -> Decimal:
    """§8 — Compute relative roughness: epsilon/D."""
    if hydraulic_diameter_m <= Decimal(0):
        raise ValueError("hydraulic_diameter_m must be positive")
    if absolute_roughness_m < Decimal(0):
        raise ValueError("absolute_roughness_m must be non-negative")

    ctx = _task027_decimal_context()
    with localcontext(ctx):
        epsilon_d = absolute_roughness_m / hydraulic_diameter_m
    return epsilon_d


def validate_relative_roughness(
    relative_roughness: Decimal,
) -> list[Task027BlockerEntry]:
    """Validate relative roughness is within Colebrook-White envelope [0, 0.05]."""
    blockers: list[Task027BlockerEntry] = []
    if relative_roughness > Decimal("0.05"):
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_RELATIVE_ROUGHNESS_OUT_OF_ENVELOPE,
                "relative_roughness",
                get_blocker_message(BlockerCode.BL_T027_RELATIVE_ROUGHNESS_OUT_OF_ENVELOPE),
            )
        )
    return blockers


# ---------------------------------------------------------------------------
# §2 — Reynolds number regime classification
# ---------------------------------------------------------------------------
def classify_reynolds(reynolds: Decimal) -> str:
    """Classify Reynolds number into regime.

    Returns: 'laminar', 'gap', 'turbulent', or 'outside_authority'.
    """
    if reynolds <= Decimal(0):
        return "outside_authority"
    if reynolds <= LAMINAR_UPPER_RE:
        return "laminar"
    if reynolds < TURBULENT_LOWER_RE:
        return "gap"
    if reynolds <= TURBULENT_UPPER_RE:
        return "turbulent"
    return "outside_authority"


def validate_reynolds(reynolds: Decimal) -> list[Task027BlockerEntry]:
    """Validate Reynolds number and return blockers if unsupported."""
    blockers: list[Task027BlockerEntry] = []
    regime = classify_reynolds(reynolds)

    if regime in ("outside_authority", "gap"):
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_UNSUPPORTED_REYNOLDS_REGIME,
                "reynolds_number",
                get_blocker_message(BlockerCode.BL_T027_UNSUPPORTED_REYNOLDS_REGIME),
            )
        )
    return blockers


# ---------------------------------------------------------------------------
# §4 — Applicability validation
# ---------------------------------------------------------------------------
def validate_applicability(
    phase: PhaseType | str | None,
    rheology: RheologyType | str | None,
    constant_density_assertion: AssertionState | str | None,
    zero_elevation_assertion: AssertionState | str | None,
    flow_direction: FlowDirectionAssertion | str | None,
) -> list[Task027BlockerEntry]:
    """Validate all applicability conditions and return blockers."""
    blockers: list[Task027BlockerEntry] = []

    # Phase validation
    if phase is None or (isinstance(phase, str) and phase != PhaseType.LIQUID.value):
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_UNSUPPORTED_PHASE,
                "phase",
                get_blocker_message(BlockerCode.BL_T027_UNSUPPORTED_PHASE),
            )
        )

    # Rheology validation
    if rheology is None or (isinstance(rheology, str) and rheology != RheologyType.NEWTONIAN.value):
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_UNSUPPORTED_RHEOLOGY,
                "rheology",
                get_blocker_message(BlockerCode.BL_T027_UNSUPPORTED_RHEOLOGY),
            )
        )

    # Friction factor convention (always Darcy for V1)
    # This is checked implicitly — if we get here, we're using Darcy

    # Constant density assertion
    if constant_density_assertion is None:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_APPLICABILITY_ASSERTION_MISSING,
                "constant_density_path_assertion",
                get_blocker_message(BlockerCode.BL_T027_APPLICABILITY_ASSERTION_MISSING),
            )
        )
    elif (
        isinstance(constant_density_assertion, str)
        and constant_density_assertion == AssertionState.FALSE.value
    ):
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_APPLICABILITY_ASSERTION_FALSE,
                "constant_density_path_assertion",
                get_blocker_message(BlockerCode.BL_T027_APPLICABILITY_ASSERTION_FALSE),
            )
        )

    # Zero elevation assertion
    if zero_elevation_assertion is None:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_APPLICABILITY_ASSERTION_MISSING,
                "zero_net_elevation_change_assertion",
                get_blocker_message(BlockerCode.BL_T027_APPLICABILITY_ASSERTION_MISSING),
            )
        )
    elif (
        isinstance(zero_elevation_assertion, str)
        and zero_elevation_assertion == AssertionState.FALSE.value
    ):
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_APPLICABILITY_ASSERTION_FALSE,
                "zero_net_elevation_change_assertion",
                get_blocker_message(BlockerCode.BL_T027_APPLICABILITY_ASSERTION_FALSE),
            )
        )

    # Flow direction
    if flow_direction is None or (
        isinstance(flow_direction, str)
        and flow_direction != FlowDirectionAssertion.START_TO_END.value
    ):
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_FLOW_DIRECTION_UNSUPPORTED,
                "flow_direction_assertion",
                get_blocker_message(BlockerCode.BL_T027_FLOW_DIRECTION_UNSUPPORTED),
            )
        )

    return blockers


# ---------------------------------------------------------------------------
# §15.7 — Result ID derivation
# ---------------------------------------------------------------------------
def derive_result_id(result_hash: str) -> str:
    """§15.7 — Derive canonical UUID from result hash."""
    ns = uuid.UUID(RESULT_ID_NAMESPACE)
    name = RESULT_ID_NAME_PREFIX + result_hash
    return str(uuid.uuid5(ns, name))


# ---------------------------------------------------------------------------
# §15 — Hash computation helpers
# ---------------------------------------------------------------------------
def compute_request_hash(
    schema_version: str,
    profile_id: str,
    task025_result_hash: str,
    task026_result_hash: str,
    property_snapshot_hash: str,
    constant_density_assertion: str,
    zero_elevation_assertion: str,
    flow_direction_assertion: str,
    roughness_authority_hash: str,
) -> str:
    """§15.2 — Compute request hash from the 10 semantic fields."""
    fields = [
        ("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        ("profile_id", KIND_STRING, profile_id.encode("utf-8")),
        ("task025_result_hash", KIND_STRING, task025_result_hash.encode("utf-8")),
        ("task026_result_hash", KIND_STRING, task026_result_hash.encode("utf-8")),
        ("property_snapshot_hash", KIND_STRING, property_snapshot_hash.encode("utf-8")),
        ("constant_density_path_assertion", KIND_ENUM, constant_density_assertion.encode("ascii")),
        (
            "zero_net_elevation_change_assertion",
            KIND_ENUM,
            zero_elevation_assertion.encode("ascii"),
        ),
        ("flow_direction_assertion", KIND_ENUM, flow_direction_assertion.encode("ascii")),
        ("roughness_authority_hash", KIND_STRING, roughness_authority_hash.encode("utf-8")),
    ]
    framed = frame_record(REQUEST_HASH_NAMESPACE, fields)
    return sha256_hex(framed)


def compute_result_hash(
    schema_version: str,
    profile_id: str,
    request_hash: str,
    darcy_friction_factor: str,
    friction_length_m: str,
    upstream_reference_plane: str,
    downstream_reference_plane: str,
    straight_tube_friction_pressure_drop_pa: str,
    task025_hydraulic_authority_hash: str,
    task025_result_hash: str,
    task026_result_hash: str,
    property_snapshot_hash: str,
) -> str:
    """§15.3 — Compute success result hash from the 16 semantic fields."""
    fields = [
        ("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        ("profile_id", KIND_STRING, profile_id.encode("utf-8")),
        ("request_hash", KIND_STRING, request_hash.encode("utf-8")),
        (
            "task025_hydraulic_authority_hash",
            KIND_STRING,
            task025_hydraulic_authority_hash.encode("utf-8"),
        ),
        ("task025_result_hash", KIND_STRING, task025_result_hash.encode("utf-8")),
        ("task026_result_hash", KIND_STRING, task026_result_hash.encode("utf-8")),
        ("property_snapshot_hash", KIND_STRING, property_snapshot_hash.encode("utf-8")),
        ("darcy_friction_factor", KIND_DECIMAL, darcy_friction_factor.encode("utf-8")),
        ("friction_length_m", KIND_DECIMAL, friction_length_m.encode("utf-8")),
        ("upstream_reference_plane", KIND_STRING, upstream_reference_plane.encode("utf-8")),
        ("downstream_reference_plane", KIND_STRING, downstream_reference_plane.encode("utf-8")),
        (
            "straight_tube_friction_pressure_drop_pa",
            KIND_DECIMAL,
            straight_tube_friction_pressure_drop_pa.encode("utf-8"),
        ),
    ]
    framed = frame_record(SUCCESS_RESULT_HASH_NAMESPACE, fields)
    return sha256_hex(framed)


def compute_blocked_result_hash(
    schema_version: str,
    profile_id: str,
    request_hash: str | None,
    task025_hydraulic_authority_hash: str | None,
    task025_result_hash: str | None,
    task026_result_hash: str | None,
    property_snapshot_hash: str | None,
    raw_request_projection: str | None,
    raw_upstream_blocked_projection: str | None,
    warnings: str,
    blockers: str,
    deferred_capabilities: str,
    provenance: str,
) -> str:
    """§15.4 — Compute blocked result hash from the 13 semantic fields.

    Self-excludes result_hash and result_id (derived from this hash).
    Uses BLOCKED_RESULT_HASH_NAMESPACE.
    """
    fields = [
        ("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        ("profile_id", KIND_STRING, profile_id.encode("utf-8")),
        ("request_hash", KIND_STRING, (request_hash or "").encode("utf-8")),
        (
            "task025_hydraulic_authority_hash",
            KIND_STRING,
            (task025_hydraulic_authority_hash or "").encode("utf-8"),
        ),
        ("task025_result_hash", KIND_STRING, (task025_result_hash or "").encode("utf-8")),
        ("task026_result_hash", KIND_STRING, (task026_result_hash or "").encode("utf-8")),
        ("property_snapshot_hash", KIND_STRING, (property_snapshot_hash or "").encode("utf-8")),
        (
            "raw_request_projection",
            KIND_STRING,
            (raw_request_projection or "").encode("utf-8"),
        ),
        (
            "raw_upstream_blocked_projection",
            KIND_STRING,
            (raw_upstream_blocked_projection or "").encode("utf-8"),
        ),
        ("warnings", KIND_STRING, warnings.encode("utf-8")),
        ("blockers", KIND_STRING, blockers.encode("utf-8")),
        ("deferred_capabilities", KIND_STRING, deferred_capabilities.encode("utf-8")),
        ("provenance", KIND_STRING, provenance.encode("utf-8")),
    ]
    framed = frame_record(BLOCKED_RESULT_HASH_NAMESPACE, fields)
    return sha256_hex(framed)


# ---------------------------------------------------------------------------
# §14.2 — Success result schema
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Task027SuccessResult:
    """§14.2 — TASK-027 success result (18 fields)."""

    schema_version: str
    profile_id: str
    request_hash: str
    result_hash: str
    result_id: str
    task025_hydraulic_authority_hash: str
    task025_result_hash: str
    task026_result_hash: str
    property_snapshot_hash: str
    darcy_friction_factor: Decimal
    friction_length_m: Decimal
    upstream_reference_plane: str
    downstream_reference_plane: str
    straight_tube_friction_pressure_drop_pa: Decimal
    warnings: tuple[str, ...]
    blockers: tuple[Task027BlockerEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: Any  # FrozenProvenance

    def __post_init__(self) -> None:
        if self.schema_version != TASK027_SUCCESS_RESULT_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be '{TASK027_SUCCESS_RESULT_SCHEMA_VERSION}'")
        if self.blockers != ():
            raise ValueError("success result blockers must be empty")


# ---------------------------------------------------------------------------
# §14.3 — Blocked result schema
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Task027BlockedResult:
    """§14.3 — TASK-027 blocked result (15 fields)."""

    schema_version: str
    profile_id: str
    request_hash: str | None
    result_hash: str
    result_id: str
    task025_hydraulic_authority_hash: str | None
    task025_result_hash: str | None
    task026_result_hash: str | None
    property_snapshot_hash: str | None
    raw_request_projection: Any  # FrozenRawProjection | None
    raw_upstream_blocked_projection: Any  # FrozenRawProjection | None
    warnings: tuple[str, ...]
    blockers: tuple[Task027BlockerEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: Any  # FrozenProvenance | None

    def __post_init__(self) -> None:
        if self.schema_version != TASK027_BLOCKED_RESULT_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be '{TASK027_BLOCKED_RESULT_SCHEMA_VERSION}'")
        if len(self.blockers) == 0:
            raise ValueError("blocked result must have non-empty blockers")


# ---------------------------------------------------------------------------
# §14.4 — Raw boundary blocked result schema
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Task027RawBoundaryBlockedResult:
    """§14.4 — TASK-027 raw boundary blocked result (6 fields)."""

    schema_version: str
    implementation_software_version: str
    raw_request_projection: Any  # FrozenRawProjection
    blockers: tuple[Task027BlockerEntry, ...]
    warnings: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version != TASK027_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be '{TASK027_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION}'"
            )
        if len(self.blockers) == 0:
            raise ValueError("raw boundary blocked result must have non-empty blockers")


# ---------------------------------------------------------------------------
# §14.1 — TASK-027 typed request
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Task027Request:
    """§14.1 — TASK-027 typed request (11 fields)."""

    schema_version: str
    profile_id: str
    task025_valid_result: Any  # Task025ValidResult
    task026_success_result: Any  # Task026SuccessResult
    property_snapshot: Any  # PropertySnapshot
    property_snapshot_hash: str
    constant_density_path_assertion: AssertionState
    zero_net_elevation_change_assertion: AssertionState
    flow_direction_assertion: FlowDirectionAssertion
    roughness_authority: RoughnessAuthority
    request_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != TASK027_REQUEST_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be '{TASK027_REQUEST_SCHEMA_VERSION}'")
        if self.profile_id not in SUPPORTED_PROFILE_IDS:
            raise ValueError(f"profile_id must be one of {SUPPORTED_PROFILE_IDS}")


# ---------------------------------------------------------------------------
# §16.5 — Raw boundary validation pipeline
# ---------------------------------------------------------------------------
def validate_raw_boundary(
    raw_request: Any,
) -> Task027RawBoundaryBlockedResult | None:
    """§16.5 — Validate raw request boundary (R00-R09).

    Returns None if validation passes, otherwise returns a
    RawBoundaryBlockedResult with appropriate blockers.
    """
    blockers: list[Task027BlockerEntry] = []

    # R00: Capture raw projection (done externally)

    # R01: Validate top-level mapping
    if not isinstance(raw_request, dict):
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_RAW_INPUT_BOUNDARY_MALFORMED,
                "raw_request",
                get_blocker_message(BlockerCode.BL_T027_RAW_INPUT_BOUNDARY_MALFORMED),
            )
        )
        return _make_raw_boundary_blocked(blockers)

    # R02: Scan unknown fields
    known_fields = set(TASK027_REQUEST_FIELDS)
    unknown_fields = [k for k in raw_request if k not in known_fields]
    if unknown_fields:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_T027_REQUEST_UNKNOWN_FIELD,
                "raw_request",
                get_blocker_message(BlockerCode.BL_T027_REQUEST_UNKNOWN_FIELD),
            )
        )

    # R03: Scan required field presence
    for field_name in TASK027_REQUEST_FIELDS:
        if field_name not in raw_request:
            if field_name == "roughness_authority":
                blockers.append(
                    emit_blocker(
                        BlockerCode.BL_T027_ROUGHNESS_AUTHORITY_MISSING,
                        f"raw_request.{field_name}",
                        get_blocker_message(BlockerCode.BL_T027_ROUGHNESS_AUTHORITY_MISSING),
                    )
                )
            else:
                blockers.append(
                    emit_blocker(
                        BlockerCode.BL_T027_RAW_INPUT_BOUNDARY_MALFORMED,
                        f"raw_request.{field_name}",
                        get_blocker_message(BlockerCode.BL_T027_RAW_INPUT_BOUNDARY_MALFORMED),
                    )
                )

    # R06: Validate assertion field presence
    assertion_fields = [
        "constant_density_path_assertion",
        "zero_net_elevation_change_assertion",
        "flow_direction_assertion",
    ]
    for af in assertion_fields:
        if af not in raw_request:
            blockers.append(
                emit_blocker(
                    BlockerCode.BL_T027_APPLICABILITY_ASSERTION_MISSING,
                    f"raw_request.{af}",
                    get_blocker_message(BlockerCode.BL_T027_APPLICABILITY_ASSERTION_MISSING),
                )
            )

    if blockers:
        return _make_raw_boundary_blocked(blockers)
    return None


def _make_raw_boundary_blocked(
    blockers: list[Task027BlockerEntry],
) -> Task027RawBoundaryBlockedResult:
    """Create a raw boundary blocked result from accumulated blockers."""
    deduplicated = collapse_blockers(blockers)
    return Task027RawBoundaryBlockedResult(
        schema_version=TASK027_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        raw_request_projection=None,  # Would be set by caller
        blockers=deduplicated,
        warnings=(),
        deferred_capabilities=(),
    )


# ---------------------------------------------------------------------------
# §8.3 — Selection contract computation
# ---------------------------------------------------------------------------
def compute_selection_contract_hash(contract: TurbulentSelectionContract) -> str:
    """§8.3 — Compute selection contract hash."""
    fields = [
        (
            "selection_contract_version",
            KIND_STRING,
            contract.selection_contract_version.encode("utf-8"),
        ),
        ("selected_correlation_id", KIND_ENUM, contract.selected_correlation_id.encode("ascii")),
        (
            "selected_correlation_source_refs",
            KIND_TUPLE,
            _encode_tuple(contract.selected_correlation_source_refs),
        ),
        (
            "friction_factor_convention",
            KIND_ENUM,
            contract.friction_factor_convention.value.encode("ascii"),
        ),
        ("re_min", KIND_DECIMAL, str(contract.re_min).encode("utf-8")),
        ("re_max", KIND_DECIMAL, str(contract.re_max).encode("utf-8")),
        (
            "relative_roughness_variable",
            KIND_STRING,
            contract.relative_roughness_variable.encode("utf-8"),
        ),
        (
            "relative_roughness_min",
            KIND_DECIMAL,
            str(contract.relative_roughness_min).encode("utf-8"),
        ),
        (
            "relative_roughness_max",
            KIND_DECIMAL,
            str(contract.relative_roughness_max).encode("utf-8"),
        ),
        ("unsupported_gap_policy", KIND_ENUM, contract.unsupported_gap_policy.encode("ascii")),
        ("out_of_envelope_policy", KIND_ENUM, contract.out_of_envelope_policy.encode("ascii")),
        (
            "roughness_authority_contract_version",
            KIND_STRING,
            contract.roughness_authority_contract_version.encode("utf-8"),
        ),
    ]
    framed = frame_record(SELECTION_CONTRACT_VERSION, fields)
    return sha256_hex(framed)


# Default selection contract
DEFAULT_SELECTION_CONTRACT: Final[TurbulentSelectionContract] = TurbulentSelectionContract(
    selection_contract_version=SELECTION_CONTRACT_VERSION,
    selected_correlation_id="COLEBROOK_WHITE_1939",
    selected_correlation_source_refs=(
        "IAEA_SODIUM_COOLANT_HANDBOOK_2024",
        "NETL_CO2_TRANSPORT_2022",
    ),
    friction_factor_convention=FrictionFactorConvention.DARCY,
    re_min=Decimal("4000"),
    re_max=Decimal("100000000"),
    relative_roughness_variable="epsilon/D",
    relative_roughness_min=Decimal("0"),
    relative_roughness_max=Decimal("0.05"),
    unsupported_gap_policy="FAIL_CLOSED",
    out_of_envelope_policy="FAIL_CLOSED",
    roughness_authority_contract_version=ROUGHNESS_SCHEMA_VERSION,
)


# ---------------------------------------------------------------------------
# §14.1 — TASK-027 request fields count assertion
# ---------------------------------------------------------------------------
REQUEST_FIELD_COUNT: Final[int] = 11
assert len(TASK027_REQUEST_FIELDS) == REQUEST_FIELD_COUNT, (
    f"TASK027_REQUEST_FIELDS must have exactly {REQUEST_FIELD_COUNT} members"
)


# ---------------------------------------------------------------------------
# §15.7 — Result ID constants
# ---------------------------------------------------------------------------
RESULT_ID_NAMESPACE_UUID: Final[uuid.UUID] = uuid.UUID(RESULT_ID_NAMESPACE)


__all__ = [
    # Enums
    "AssertionState",
    "FlowDirectionAssertion",
    "RoughnessMode",
    "FrictionFactorConvention",
    "PhaseType",
    "RheologyType",
    "BlockerCode",
    # Blocker registry
    "UNIQUE_BLOCKER_CODE_COUNT",
    "UNIQUE_ORDERING_KEY_COUNT",
    "BLOCKER_REGISTRY_COUNT",
    "emit_blocker",
    "collapse_blockers",
    "get_blocker_ordering_key",
    "get_blocker_message",
    "Task027BlockerEntry",
    # Roughness
    "AbsoluteRoughnessAuthority",
    "SmoothRoughnessAuthority",
    "RoughnessAuthority",
    "quantize_roughness",
    "validate_roughness_authority",
    "compute_relative_roughness",
    "validate_relative_roughness",
    # Friction factor
    "ColebrookWhiteConvergenceError",
    "compute_laminar_friction_factor",
    "compute_colebrook_white",
    "compute_turbulent_friction_factor_safe",
    "compute_pressure_drop",
    "classify_reynolds",
    "validate_reynolds",
    # Applicability
    "validate_applicability",
    # Selection contract
    "TurbulentSelectionContract",
    "compute_selection_contract_hash",
    "DEFAULT_SELECTION_CONTRACT",
    # Schemas
    "Task027Request",
    "Task027SuccessResult",
    "Task027BlockedResult",
    "Task027RawBoundaryBlockedResult",
    # Raw boundary
    "validate_raw_boundary",
    # Hash
    "compute_request_hash",
    "compute_result_hash",
    "compute_blocked_result_hash",
    "derive_result_id",
    # Constants
    "TASK027_REQUEST_SCHEMA_VERSION",
    "TASK027_REQUEST_FIELDS",
    "TASK027_SUCCESS_RESULT_SCHEMA_VERSION",
    "TASK027_BLOCKED_RESULT_SCHEMA_VERSION",
    "TASK027_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "SUPPORTED_PROFILE_IDS",
    "ROUGHNESS_SCHEMA_VERSION",
    "SELECTION_CONTRACT_VERSION",
    "LAMINAR_UPPER_RE",
    "TURBULENT_LOWER_RE",
    "TURBULENT_UPPER_RE",
    "FRICTION_FACTOR_QUANTUM",
    "PRESSURE_DROP_QUANTUM",
    "LENGTH_QUANTUM_M",
    "REQUEST_HASH_NAMESPACE",
    "SUCCESS_RESULT_HASH_NAMESPACE",
    "BLOCKED_RESULT_HASH_NAMESPACE",
    "RAW_BOUNDARY_BLOCKED_HASH_NAMESPACE",
    "RAW_PROJECTION_NAMESPACE",
    "PROVENANCE_NAMESPACE",
    "RESULT_ID_NAMESPACE",
    "RESULT_ID_NAME_PREFIX",
    "RESULT_ID_NAMESPACE_UUID",
    "REQUEST_FIELD_COUNT",
    "TASK027_SUCCESS_RESULT_FIELD_COUNT",
    "TASK027_BLOCKED_RESULT_FIELD_COUNT",
    "TASK027_RAW_BOUNDARY_BLOCKED_FIELD_COUNT",
    # Framing
    "KIND_NONE",
    "KIND_STRING",
    "KIND_DECIMAL",
    "KIND_ENUM",
    "KIND_TUPLE",
    "KIND_RECORD",
    "KIND_RAW_PROJECTION",
    "frame_value",
    "frame_record",
    "sha256_hex",
]


# ruff: noqa: E501
