"""Closed TASK-035 blocker registry and reachability matrix."""

# The matrix preserves exact public field-path and predicate strings.
# ruff: noqa: E501

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .models import BlockerEntry
from .schema import BLOCKER_CODES, VALIDATION_STAGES


@dataclass(frozen=True)
class BlockerRow:
    """The implementation-facing row of the frozen 42-blocker matrix."""

    row_number: int
    code: str
    earliest_stage: str
    within_stage_order: int
    trigger_predicate: str
    exact_field_path: str
    safe_evidence_exposed: str
    test_coverage: tuple[str, ...]

    @property
    def stage(self) -> str:
        return self.earliest_stage

    @property
    def field_path(self) -> str:
        return self.exact_field_path

    @property
    def safe_evidence(self) -> str:
        return self.safe_evidence_exposed


def _row(
    number: int,
    code: str,
    stage: str,
    order: int,
    predicate: str,
    path: str,
    safe: str,
    *tests: str,
) -> BlockerRow:
    return BlockerRow(number, code, stage, order, predicate, path, safe, tuple(tests))


BLOCKER_ROWS: tuple[BlockerRow, ...] = (
    _row(
        1,
        "SSTHC_RAW_TYPE_INVALID",
        "S01",
        1,
        "raw_request is not an exact built-in dict at the public raw boundary",
        "raw_request",
        "NONE",
        "T035-001",
    ),
    _row(
        2,
        "SSTHC_UNKNOWN_FIELD",
        "S01",
        2,
        "raw_request contains a top-level key outside the seven frozen request fields",
        "raw_request",
        "NONE",
        "T035-001",
    ),
    _row(
        3,
        "SSTHC_EVIDENCE_REFS_INVALID",
        "S01",
        3,
        "evidence_refs is not a finite ordered sequence of unique non-empty strings",
        "evidence_refs",
        "NONE",
        "T035-001",
    ),
    _row(
        4,
        "SSTHC_SCHEMA_VERSION_UNSUPPORTED",
        "S02",
        1,
        "request.schema_version is not the frozen TASK035 request schema version",
        "schema_version",
        "REQUEST_IDENTITY",
        "T035-002",
    ),
    _row(
        5,
        "SSTHC_PROFILE_ID_UNSUPPORTED",
        "S02",
        2,
        "request.profile_id is not the frozen TASK035 composition profile ID",
        "profile_id",
        "REQUEST_IDENTITY",
        "T035-002",
    ),
    _row(
        6,
        "SSTHC_REQUIRED_FIELD_MISSING",
        "S02",
        3,
        "at least one frozen top-level request field is absent after raw boundary acceptance",
        "request",
        "REQUEST_IDENTITY",
        "T035-002",
    ),
    _row(
        7,
        "SSTHC_TASK031_RESULT_MISSING",
        "S03",
        1,
        "task031_result is null or absent after request schema acceptance",
        "task031_result",
        "REQUEST_IDENTITY",
        "T035-003",
    ),
    _row(
        8,
        "SSTHC_TASK031_RESULT_INVALID",
        "S03",
        2,
        "TASK031 envelope cannot be structurally parsed into a valid VALID or BLOCKED branch",
        "task031_result.status; task031_result.geometry; task031_result.blockers; task031_result.blocked_result_hash",
        "REQUEST_IDENTITY",
        "T035-003",
    ),
    _row(
        9,
        "SSTHC_TASK031_RESULT_BLOCKED",
        "S03",
        3,
        "structurally valid TASK031 envelope selects status=BLOCKED with geometry=null and admitted blocked evidence",
        "task031_result.status; task031_result.geometry; task031_result.blockers; task031_result.blocked_result_hash",
        "REQUEST_IDENTITY",
        "T035-004",
    ),
    _row(
        10,
        "SSTHC_TASK031_IDENTITY_MISMATCH",
        "S04",
        1,
        "accepted TASK031 geometry request_hash, geometry_hash, or geometry_id fails its public identity replay",
        "task031_result.geometry.request_hash; task031_result.geometry.geometry_hash; task031_result.geometry.geometry_id",
        "REQUEST_IDENTITY",
        "T035-003",
    ),
    _row(
        11,
        "SSTHC_TASK032_RESULT_MISSING",
        "S05",
        1,
        "task032_result is null or absent after TASK031 success acceptance",
        "task032_result",
        "TASK031_IDENTITY",
        "T035-005",
    ),
    _row(
        12,
        "SSTHC_TASK032_RESULT_INVALID",
        "S05",
        2,
        "TASK032 envelope has an unsupported shape, status, payload branch, field set, or field type",
        "task032_result.status; task032_result.flow_state; task032_result.blocked_result; task032_result.raw_boundary_blocked_result",
        "TASK031_IDENTITY",
        "T035-005",
    ),
    _row(
        13,
        "SSTHC_TASK032_RESULT_BLOCKED",
        "S05",
        3,
        "structurally valid TASK032 envelope selects status=BLOCKED with exactly one admitted blocked branch",
        "task032_result.status; task032_result.blocked_result; task032_result.raw_boundary_blocked_result",
        "TASK031_IDENTITY",
        "T035-006",
    ),
    _row(
        14,
        "SSTHC_TASK032_IDENTITY_MISMATCH",
        "S06",
        1,
        "accepted TASK032 flow_state request_hash, result_hash, result_id, or TASK031 geometry id/hash fails TASK032-local replay against accepted evidence; TASK033/TASK034 evidence is not read",
        "task032_result.flow_state.request_hash; task032_result.flow_state.result_hash; task032_result.flow_state.result_id; task032_result.flow_state.task031_geometry_id; task032_result.flow_state.task031_geometry_hash",
        "TASK031_IDENTITY",
        "T035-005",
    ),
    _row(
        15,
        "SSTHC_TASK033_RESULT_MISSING",
        "S07",
        1,
        "task033_result is null or absent after TASK032 success acceptance",
        "task033_result",
        "TASK031_TASK032_IDENTITY",
        "T035-007",
    ),
    _row(
        16,
        "SSTHC_TASK033_RESULT_INVALID",
        "S07",
        2,
        "TASK033 envelope has an unsupported shape, status, payload branch, field set, or field type",
        "task033_result.status; task033_result.heat_transfer; task033_result.blocked_result; task033_result.raw_boundary_blocked_result",
        "TASK031_TASK032_IDENTITY",
        "T035-007",
    ),
    _row(
        17,
        "SSTHC_TASK033_RESULT_BLOCKED",
        "S07",
        3,
        "structurally valid TASK033 envelope selects status=BLOCKED with exactly one admitted blocked branch",
        "task033_result.status; task033_result.blocked_result; task033_result.raw_boundary_blocked_result",
        "TASK031_TASK032_IDENTITY",
        "T035-008",
    ),
    _row(
        18,
        "SSTHC_TASK033_IDENTITY_MISMATCH",
        "S08",
        1,
        "accepted TASK033 heat_transfer request/result/id, TASK032 replay, or TASK031 geometry id/hash fails its public identity replay",
        "task033_result.heat_transfer.request_hash; task033_result.heat_transfer.result_hash; task033_result.heat_transfer.result_id; task033_result.heat_transfer.task032_request_hash; task033_result.heat_transfer.task032_result_hash; task033_result.heat_transfer.task032_result_id; task033_result.heat_transfer.task031_geometry_id; task033_result.heat_transfer.task031_geometry_hash",
        "TASK031_TASK032_IDENTITY",
        "T035-007",
        "T035-012",
    ),
    _row(
        19,
        "SSTHC_TASK034_RESULT_MISSING",
        "S09",
        1,
        "task034_result is null or absent after TASK033 success acceptance",
        "task034_result",
        "TASK031_TASK032_TASK033_IDENTITY",
        "T035-009",
    ),
    _row(
        20,
        "SSTHC_TASK034_RESULT_INVALID",
        "S09",
        2,
        "TASK034 envelope has an unsupported shape, status, payload branch, field set, or field type",
        "task034_result.status; task034_result.pressure_drop; task034_result.blocked_result; task034_result.raw_boundary_blocked_result",
        "TASK031_TASK032_TASK033_IDENTITY",
        "T035-009",
    ),
    _row(
        21,
        "SSTHC_TASK034_RESULT_BLOCKED",
        "S09",
        3,
        "structurally valid TASK034 envelope selects status=BLOCKED with exactly one admitted blocked branch",
        "task034_result.status; task034_result.blocked_result; task034_result.raw_boundary_blocked_result",
        "TASK031_TASK032_TASK033_IDENTITY",
        "T035-010",
    ),
    _row(
        22,
        "SSTHC_TASK034_IDENTITY_MISMATCH",
        "S10",
        1,
        "accepted TASK034 pressure_drop request/result/id, TASK033 replay, TASK032 replay, or TASK031 request/geometry replay fails",
        "task034_result.pressure_drop.request_hash; task034_result.pressure_drop.result_hash; task034_result.pressure_drop.result_id; task034_result.pressure_drop.task033_request_hash; task034_result.pressure_drop.task033_result_hash; task034_result.pressure_drop.task033_result_id; task034_result.pressure_drop.task032_request_hash; task034_result.pressure_drop.task032_result_hash; task034_result.pressure_drop.task032_result_id; task034_result.pressure_drop.task031_request_hash; task034_result.pressure_drop.task031_geometry_id; task034_result.pressure_drop.task031_geometry_hash",
        "TASK031_TASK032_TASK033_IDENTITY",
        "T035-009",
        "T035-011",
        "T035-012",
    ),
    _row(
        23,
        "SSTHC_CONFIGURATION_MISMATCH",
        "S11",
        1,
        "at least two exposed task020_configuration_id or task020_configuration_hash values are not identical",
        "task031_result.geometry.task020_configuration_id/hash; task032_result.flow_state.task020_configuration_id/hash; task033_result.heat_transfer.task020_configuration_id/hash; task034_result.pressure_drop.task020_configuration_id/hash",
        "ALL_PRODUCER_IDENTITIES",
        "T035-013",
    ),
    _row(
        24,
        "SSTHC_TASK021_LAYOUT_MISMATCH",
        "S11",
        2,
        "accepted TASK031 task021_layout_id or task021_layout_hash is absent, malformed, or fails the frozen ancestry identity",
        "task031_result.geometry.task021_layout_id; task031_result.geometry.task021_layout_hash",
        "ALL_PRODUCER_IDENTITIES",
        "T035-013",
    ),
    _row(
        25,
        "SSTHC_TASK024_GEOMETRY_MISMATCH",
        "S11",
        3,
        "accepted TASK031 task024_geometry_id or task024_geometry_hash is absent, malformed, or fails the frozen ancestry identity",
        "task031_result.geometry.task024_geometry_id; task031_result.geometry.task024_geometry_hash",
        "ALL_PRODUCER_IDENTITIES",
        "T035-013",
    ),
    _row(
        26,
        "SSTHC_TASK031_GEOMETRY_MISMATCH",
        "S11",
        4,
        "any accepted producer task031_geometry_id or task031_geometry_hash differs from TASK031 geometry",
        "task032_result.flow_state.task031_geometry_id/hash; task033_result.heat_transfer.task031_geometry_id/hash; task034_result.pressure_drop.task031_geometry_id/hash; task031_result.geometry.geometry_id/hash",
        "ALL_PRODUCER_IDENTITIES",
        "T035-013",
    ),
    _row(
        27,
        "SSTHC_PROPERTY_SNAPSHOT_MISMATCH",
        "S12",
        1,
        "TASK032, TASK033, and TASK034 property_snapshot_hash values are not byte-identical",
        "task032_result.flow_state.property_snapshot_hash; task033_result.heat_transfer.property_snapshot_hash; task034_result.pressure_drop.property_snapshot_hash",
        "ALL_PRODUCER_IDENTITIES",
        "T035-014",
    ),
    _row(
        28,
        "SSTHC_MASS_FLOW_AUTHORITY_MISMATCH",
        "S12",
        2,
        "TASK032, TASK033, and TASK034 mass_flow_authority_hash values are not byte-identical",
        "task032_result.flow_state.mass_flow_authority_hash; task033_result.heat_transfer.mass_flow_authority_hash; task034_result.pressure_drop.mass_flow_authority_hash",
        "ALL_PRODUCER_IDENTITIES",
        "T035-014",
    ),
    _row(
        29,
        "SSTHC_CASE_IDENTITY_MISMATCH",
        "S13",
        1,
        "TASK032, TASK033, and TASK034 shell_side_case_id values are not byte-identical",
        "task032_result.flow_state.shell_side_case_id; task033_result.heat_transfer.shell_side_case_id; task034_result.pressure_drop.shell_side_case_id",
        "ALL_PRODUCER_IDENTITIES",
        "T035-015",
    ),
    _row(
        30,
        "SSTHC_STREAM_IDENTITY_MISMATCH",
        "S13",
        2,
        "TASK032, TASK033, and TASK034 shell_side_stream_id values are not byte-identical",
        "task032_result.flow_state.shell_side_stream_id; task033_result.heat_transfer.shell_side_stream_id; task034_result.pressure_drop.shell_side_stream_id",
        "ALL_PRODUCER_IDENTITIES",
        "T035-015",
    ),
    _row(
        31,
        "SSTHC_FLUID_IDENTITY_MISMATCH",
        "S13",
        3,
        "TASK032, TASK033, and TASK034 shell_side_fluid_id values are not byte-identical",
        "task032_result.flow_state.shell_side_fluid_id; task033_result.heat_transfer.shell_side_fluid_id; task034_result.pressure_drop.shell_side_fluid_id",
        "ALL_PRODUCER_IDENTITIES",
        "T035-015",
    ),
    _row(
        32,
        "SSTHC_PROFILE_COMPATIBILITY_MISMATCH",
        "S14",
        1,
        "a producer profile_id or required first_slice_profile_id is not one of its frozen producer-specific authority tokens",
        "task032_result.flow_state.profile_id; task033_result.heat_transfer.profile_id/first_slice_profile_id; task034_result.pressure_drop.profile_id/first_slice_profile_id",
        "ALL_PRODUCER_IDENTITIES",
        "T035-016",
    ),
    _row(
        33,
        "SSTHC_HEAT_TRANSFER_SURFACE_MISMATCH",
        "S14",
        2,
        "TASK033 heat_transfer_surface is not OUTER_TUBE_SURFACE",
        "task033_result.heat_transfer.heat_transfer_surface",
        "ALL_PRODUCER_IDENTITIES",
        "T035-016",
    ),
    _row(
        34,
        "SSTHC_CORRELATION_IDENTITY_MISMATCH",
        "S14",
        3,
        "TASK033 or TASK034 correlation_id is not its own frozen correlation authority token",
        "task033_result.heat_transfer.correlation_id; task034_result.pressure_drop.correlation_id",
        "ALL_PRODUCER_IDENTITIES",
        "T035-016",
    ),
    _row(
        35,
        "SSTHC_APPLICABILITY_INCOMPATIBLE",
        "S15",
        1,
        "producer-specific applicability projections have a shared key with unequal values or do not form the admitted intersection",
        "task033_result.heat_transfer.applicability_context; task034_result.pressure_drop.applicability_context; task035.applicability_ledger",
        "ALL_IDENTITIES_AND_COMPATIBILITY",
        "T035-017",
    ),
    _row(
        36,
        "SSTHC_REQUIRED_CAPABILITY_MISSING",
        "S16",
        1,
        "a required TASK031-TASK034 capability is absent from the success-admissible completeness ledger",
        "task035.completeness_ledger",
        "ALL_IDENTITIES_AND_COMPATIBILITY",
        "T035-018",
    ),
    _row(
        37,
        "SSTHC_REQUIRED_PRODUCER_NOT_DELIVERED",
        "S16",
        2,
        "a required producer is classified as DELIVERED_BUT_BLOCKED, NOT_APPLICABLE, or another non-delivered state",
        "task035.completeness_ledger.required_producers",
        "ALL_IDENTITIES_AND_COMPATIBILITY",
        "T035-019",
    ),
    _row(
        38,
        "SSTHC_SUCCESS_PAYLOAD_COMPOSITION_FAILED",
        "S17",
        1,
        "one of the 41 frozen success fields cannot be populated from accepted public evidence and frozen ledger projections",
        "task035.success_result",
        "ALL_IDENTITIES_AND_COMPATIBILITY",
        "T035-018",
    ),
    _row(
        39,
        "SSTHC_PARTIAL_SUCCESS_FORBIDDEN",
        "S17",
        2,
        "success construction observes a required producer or required HTC/pressure-drop value absent or blocked",
        "task035.success_result",
        "ALL_IDENTITIES_AND_COMPATIBILITY",
        "T035-019",
    ),
    _row(
        40,
        "SSTHC_PROVENANCE_CANONICALIZATION_FAILED",
        "S18",
        1,
        "the finalized provenance cannot be represented in the frozen ordered 36-field canonical projection",
        "task035.provenance",
        "ALL_IDENTITIES_AND_COMPATIBILITY",
        "T035-021",
    ),
    _row(
        41,
        "SSTHC_CANONICALIZATION_FAILED",
        "S18",
        2,
        "an accepted success or ledger projection contains a value outside the frozen canonical primitive domain",
        "task035.canonical_projection",
        "ALL_IDENTITIES_AND_COMPATIBILITY",
        "T035-020",
    ),
    _row(
        42,
        "SSTHC_RESULT_IDENTITY_FINALIZATION_FAILED",
        "S19",
        1,
        "the frozen success or blocked result hash cannot be finalized or its deterministic result_id cannot be derived",
        "task035.result_identity",
        "ALL_IDENTITIES_AND_COMPATIBILITY",
        "T035-020",
    ),
)

BLOCKER_REGISTRY = BLOCKER_ROWS
BLOCKER_REACHABILITY_MATRIX = BLOCKER_ROWS
BLOCKER_COUNT = len(BLOCKER_ROWS)
BLOCKER_REACHABILITY_ROW_COUNT = len(BLOCKER_ROWS)
BLOCKER_CODES_UNIQUE = len({row.code for row in BLOCKER_ROWS})
BLOCKER_REACHABILITY_AUDIT = "CROSS_CUTTING_ASSERTION_OVER_T035_001_TO_T035_021"
BLOCKER_REACHABILITY_AUDIT_HAS_NEW_TEST_ID = False

_STAGE_ORDER = {stage: index for index, (stage, _name) in enumerate(VALIDATION_STAGES)}
_BY_CODE = {row.code: row for row in BLOCKER_ROWS}


def row_for_code(code: Any) -> BlockerRow:
    code_value = getattr(code, "value", code)
    return _BY_CODE[str(code_value)]


def make_blocker(
    code: Any,
    *,
    stage: str | None = None,
    field_path: str | None = None,
    details: tuple[tuple[str, str], ...] = (),
) -> BlockerEntry:
    """Create a public blocker using the row's frozen defaults."""

    row = row_for_code(code)
    code_value = row.code
    selected_stage = row.earliest_stage if stage is None else stage
    selected_path = row.exact_field_path if field_path is None else field_path
    return BlockerEntry(
        code=code_value,
        stage=selected_stage,
        field_path=selected_path,
        message_key=code_value.lower(),
        details=tuple(details),
    )


def sort_blockers(
    blockers: tuple[BlockerEntry, ...] | list[BlockerEntry],
) -> tuple[BlockerEntry, ...]:
    """Order blockers by frozen stage and within-stage precedence."""

    def key(item: BlockerEntry) -> tuple[int, int, str]:
        row = _BY_CODE.get(item.code)
        if row is None:
            return (len(_STAGE_ORDER), 10**9, item.code)
        return (_STAGE_ORDER[row.earliest_stage], row.within_stage_order, row.code)

    return tuple(sorted(blockers, key=key))


def audit_blocker_reachability(
    observations: Iterable[tuple[BlockerEntry, ...] | list[BlockerEntry]],
) -> bool:
    """Verify runtime blocker observations against every frozen matrix row.

    The caller supplies blockers returned by real validation executions.  This
    intentionally does not treat registry membership alone as reachability:
    each row must be observed with its frozen stage/path, and every observed
    multi-fault result must already be in precedence order.
    """

    observed_codes: set[str] = set()
    for observed in observations:
        ordered = tuple(observed)
        if ordered != sort_blockers(ordered):
            return False
        for blocker in ordered:
            row = _BY_CODE.get(blocker.code)
            if row is None:
                return False
            if blocker.stage != row.earliest_stage or blocker.field_path != row.exact_field_path:
                return False
            observed_codes.add(blocker.code)
    return observed_codes == set(BLOCKER_CODES)


def blocker_codes() -> tuple[str, ...]:
    return tuple(row.code for row in BLOCKER_ROWS)


assert blocker_codes() == BLOCKER_CODES
assert BLOCKER_COUNT == 42
assert BLOCKER_CODES_UNIQUE == 42
assert BLOCKER_REACHABILITY_ROW_COUNT == 42
assert BLOCKER_REACHABILITY_AUDIT_HAS_NEW_TEST_ID is False


__all__ = [
    "BLOCKER_CODES_UNIQUE",
    "BLOCKER_COUNT",
    "BLOCKER_REACHABILITY_MATRIX",
    "BLOCKER_REACHABILITY_AUDIT",
    "BLOCKER_REACHABILITY_AUDIT_HAS_NEW_TEST_ID",
    "BLOCKER_REACHABILITY_ROW_COUNT",
    "BLOCKER_REGISTRY",
    "BLOCKER_ROWS",
    "BlockerRow",
    "blocker_codes",
    "audit_blocker_reachability",
    "make_blocker",
    "row_for_code",
    "sort_blockers",
]
