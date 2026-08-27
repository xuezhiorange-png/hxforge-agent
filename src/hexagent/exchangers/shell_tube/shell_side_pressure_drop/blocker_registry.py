"""Closed TASK-034 blocker registry."""

from __future__ import annotations

from .models import BlockerEntry

BLOCKER_CODES: tuple[str, ...] = (
    "SSPD_RAW_REQUEST_TYPE_INVALID",
    "SSPD_RAW_BINARY_FLOAT_FORBIDDEN",
    "SSPD_RAW_UNSUPPORTED_PRIMITIVE",
    "SSPD_RAW_CANONICALIZATION_FAILURE",
    "SSPD_UNKNOWN_REQUEST_FIELD",
    "SSPD_REQUEST_SCHEMA_MISMATCH",
    "SSPD_PROFILE_ID_MISMATCH",
    "SSPD_SOURCE_AUTHORITY_MISMATCH",
    "SSPD_TASK033_UPSTREAM_MISSING",
    "SSPD_TASK033_UPSTREAM_INVALID",
    "SSPD_TASK033_REQUEST_HASH_MISMATCH",
    "SSPD_TASK033_RESULT_ID_MISMATCH",
    "SSPD_TASK033_RESULT_HASH_MISMATCH",
    "SSPD_TASK031_REQUEST_EVIDENCE_MISSING",
    "SSPD_TASK031_REQUEST_HASH_MISMATCH",
    "SSPD_TASK031_GEOMETRY_ID_MISMATCH",
    "SSPD_TASK031_GEOMETRY_HASH_MISMATCH",
    "SSPD_TASK032_RESULT_ID_MISMATCH",
    "SSPD_TASK032_RESULT_HASH_MISMATCH",
    "SSPD_CASE_ID_MISMATCH",
    "SSPD_STREAM_ID_MISMATCH",
    "SSPD_FLUID_ID_MISMATCH",
    "SSPD_CONFIGURATION_ID_MISMATCH",
    "SSPD_PROPERTY_SNAPSHOT_HASH_MISMATCH",
    "SSPD_MASS_FLOW_AUTHORITY_HASH_MISMATCH",
    "SSPD_WALL_PROPERTY_AUTHORITY_MISSING",
    "SSPD_WALL_PROPERTY_AUTHORITY_MISMATCH",
    "SSPD_WALL_VISCOSITY_INVALID",
    "SSPD_UNSUPPORTED_PHASE",
    "SSPD_UNSUPPORTED_RHEOLOGY",
    "SSPD_UNSUPPORTED_SHELL_TYPE",
    "SSPD_UNSUPPORTED_SHELL_PASS_COUNT",
    "SSPD_UNSUPPORTED_BAFFLE_TYPE",
    "SSPD_UNSUPPORTED_TUBE_LAYOUT",
    "SSPD_UNSUPPORTED_BAFFLE_CUT",
    "SSPD_UNSUPPORTED_BAFFLE_SPACING",
    "SSPD_REYNOLDS_OUTSIDE_DOMAIN",
    "SSPD_FORMULA_INPUT_INVALID",
    "SSPD_DECIMAL_LN_FAILURE",
    "SSPD_DECIMAL_EXP_FAILURE",
    "SSPD_DECIMAL_POWER_FAILURE",
    "SSPD_PRESSURE_DROP_CALCULATION_FAILURE",
    "SSPD_PUBLIC_QUANTIZATION_FAILURE",
    "SSPD_PROVENANCE_CANONICALIZATION_FAILURE",
    "SSPD_RESULT_ID_FINALIZATION_FAILURE",
    "SSPD_PARTIAL_RESULT_FORBIDDEN",
    "SSPD_DEFERRED_CAPABILITY_TOKEN_INVALID",
    "SSPD_SHELL_INSIDE_DIAMETER_MISMATCH",
    "SSPD_BAFFLE_COUNT_MISMATCH",
    "SSPD_SPACING_SEQUENCE_MISMATCH",
    "SSPD_TUBE_PITCH_MISMATCH",
    "SSPD_TUBE_OUTER_DIAMETER_MISMATCH",
    "SSPD_PATTERN_FAMILY_MISMATCH",
    "SSPD_SHELL_TYPE_AUTHORITY_MISSING",
    "SSPD_SHELL_TYPE_AUTHORITY_INVALID",
    "SSPD_SHELL_TYPE_AUTHORITY_REPLAY_MISMATCH",
    "SSPD_SHELL_TYPE_AUTHORITY_CONFIGURATION_MISMATCH",
    "SSPD_SHELL_TYPE_AUTHORITY_REQUIRED_FIELD_MISSING",
)


class _BlockerCodeMeta(type):
    def __getattr__(cls, name: str) -> str:
        if name in BLOCKER_CODES:
            return name
        raise AttributeError(name)


class BlockerCode(metaclass=_BlockerCodeMeta):
    """Attribute access without permitting runtime registry mutation."""


for _code in BLOCKER_CODES:
    setattr(BlockerCode, _code, _code)


# The validation pipeline supplies the exact earliest stage for each emitted
# blocker.  The registry itself remains closed and deterministic.
BLOCKER_STAGE: dict[str, str] = {
    code: stage
    for stage, codes in (
        ("S01", BLOCKER_CODES[:4]),
        ("S02", BLOCKER_CODES[4:7] + (BLOCKER_CODES[-1],)),
        ("S03", BLOCKER_CODES[7:10]),
        ("S05", (BLOCKER_CODES[10],)),
        ("S04", BLOCKER_CODES[11:13] + BLOCKER_CODES[17:19]),
        ("S06", BLOCKER_CODES[13:15]),
        ("S07", BLOCKER_CODES[15:17]),
        ("S10", BLOCKER_CODES[19:23]),
        ("S09", BLOCKER_CODES[25:28]),
        ("S11", BLOCKER_CODES[28:37] + BLOCKER_CODES[-5:-1]),
        ("S12", (BLOCKER_CODES[37],)),
        ("S13", BLOCKER_CODES[38:41]),
        ("S14", (BLOCKER_CODES[41],)),
        ("S15", (BLOCKER_CODES[42],)),
        ("S16", (BLOCKER_CODES[43],)),
        ("S17", BLOCKER_CODES[44:47]),
        ("S08", BLOCKER_CODES[23:25] + BLOCKER_CODES[47:53]),
    )
    for code in codes
}


def validate_blocker_token(token: str) -> str:
    if type(token) is not str or token not in BLOCKER_CODES:
        raise ValueError("unknown TASK034 blocker token")
    return token


def make_blocker(
    code: str, *, stage: str | None = None, field_path: str | None = None
) -> BlockerEntry:
    validate_blocker_token(code)
    return BlockerEntry(code=code, stage=stage or BLOCKER_STAGE[code], field_path=field_path)


def sort_blockers(
    blockers: tuple[BlockerEntry, ...] | list[BlockerEntry],
) -> tuple[BlockerEntry, ...]:
    if any(item.code not in BLOCKER_CODES for item in blockers):
        raise ValueError("unknown TASK034 blocker token")
    return tuple(
        sorted(blockers, key=lambda item: (BLOCKER_CODES.index(item.code), item.field_path or ""))
    )


def all_blockers() -> tuple[str, ...]:
    return BLOCKER_CODES


__all__ = [
    "BLOCKER_CODES",
    "BlockerCode",
    "BLOCKER_STAGE",
    "all_blockers",
    "make_blocker",
    "sort_blockers",
    "validate_blocker_token",
]
