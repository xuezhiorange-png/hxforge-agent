"""TASK-026 14-code blocker registry and immutable BlockerEntry.

R8 implementation. The 14-code registry (R6-R7 §13.1) is the closed
set of error codes that the stage pipeline can emit. Reachability
(R6-R7 §13.2) is partitioned 13 reachable + 1 defensive:

  Reachable (earliest stage):
    BL_REQUEST_UNKNOWN_FIELD               S00
    BL_RAW_INPUT_BOUNDARY_MALFORMED        S00
    BL_UPSTREAM_BLOCKED                    S01
    BL_PROPERTY_FIELD_MISSING              S02
    BL_PROPERTY_FIELD_INVALID              S02
    BL_PROPERTY_FIELD_NON_POSITIVE         S02
    BL_PROPERTY_AUTHORITY_MISSING          S03
    BL_PROPERTY_HASH_MISMATCH              S03
    BL_UNSUPPORTED_PHASE                   S04
    BL_MASS_FLOW_INVALID                   S05
    BL_DECIMAL_FAILURE                     S07..S11
    BL_CORRELATION_NOT_APPLICABLE          S09
    BL_REGIME_NO_CORRELATION_APPLICABLE    S09
  Defensive (never emitted at runtime):
    BL_PARTIAL_RESULT_FORBIDDEN            S13

BL_NON_CONVERGENCE is reserved but NOT in the registry (R6-R7 §13.3).
All entries have severity "hard" (R6-R7 §13.4).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

# R6-R7 §13.1 — 14-code registry (exact tuple order).
TASK026_BLOCKER_REGISTRY: tuple[str, ...] = (
    "BL_REQUEST_UNKNOWN_FIELD",
    "BL_RAW_INPUT_BOUNDARY_MALFORMED",
    "BL_UPSTREAM_BLOCKED",
    "BL_PROPERTY_FIELD_MISSING",
    "BL_PROPERTY_FIELD_INVALID",
    "BL_PROPERTY_FIELD_NON_POSITIVE",
    "BL_PROPERTY_AUTHORITY_MISSING",
    "BL_PROPERTY_HASH_MISMATCH",
    "BL_UNSUPPORTED_PHASE",
    "BL_MASS_FLOW_INVALID",
    "BL_DECIMAL_FAILURE",
    "BL_CORRELATION_NOT_APPLICABLE",
    "BL_REGIME_NO_CORRELATION_APPLICABLE",
    "BL_PARTIAL_RESULT_FORBIDDEN",
)

TASK026_BLOCKER_CODE_COUNT: int = 14

# R6-R7 §13.2 — reachability disposition.
TASK026_REACHABLE_BLOCKERS: tuple[str, ...] = (
    "BL_REQUEST_UNKNOWN_FIELD",
    "BL_RAW_INPUT_BOUNDARY_MALFORMED",
    "BL_UPSTREAM_BLOCKED",
    "BL_PROPERTY_FIELD_MISSING",
    "BL_PROPERTY_FIELD_INVALID",
    "BL_PROPERTY_FIELD_NON_POSITIVE",
    "BL_PROPERTY_AUTHORITY_MISSING",
    "BL_PROPERTY_HASH_MISMATCH",
    "BL_UNSUPPORTED_PHASE",
    "BL_MASS_FLOW_INVALID",
    "BL_DECIMAL_FAILURE",
    "BL_CORRELATION_NOT_APPLICABLE",
    "BL_REGIME_NO_CORRELATION_APPLICABLE",
)

TASK026_DEFENSIVE_BLOCKERS: tuple[str, ...] = ("BL_PARTIAL_RESULT_FORBIDDEN",)

REACHABLE_COUNT: int = 13
DEFENSIVE_COUNT: int = 1
DEFENSIVE_UNREACHABLE_CODE: str = "BL_PARTIAL_RESULT_FORBIDDEN"

# R6-R7 §13.3 — reserved but not in registry.
RESERVED_NOT_EMITTED: str = "BL_NON_CONVERGENCE"

# R6-R7 §13.2 — earliest stage per blocker.
TASK026_BLOCKER_EARLIEST_STAGE: dict[str, str] = {
    "BL_REQUEST_UNKNOWN_FIELD": "S00",
    "BL_RAW_INPUT_BOUNDARY_MALFORMED": "S00",
    "BL_UPSTREAM_BLOCKED": "S01",
    "BL_PROPERTY_FIELD_MISSING": "S02",
    "BL_PROPERTY_FIELD_INVALID": "S02",
    "BL_PROPERTY_FIELD_NON_POSITIVE": "S02",
    "BL_PROPERTY_AUTHORITY_MISSING": "S03",
    "BL_PROPERTY_HASH_MISMATCH": "S03",
    "BL_UNSUPPORTED_PHASE": "S04",
    "BL_MASS_FLOW_INVALID": "S05",
    "BL_DECIMAL_FAILURE": "S07",
    "BL_CORRELATION_NOT_APPLICABLE": "S09",
    "BL_REGIME_NO_CORRELATION_APPLICABLE": "S09",
    "BL_PARTIAL_RESULT_FORBIDDEN": "S13",
}

# Dispatch severity (R6-R7 §13.4 — all hard).
TASK026_BLOCKER_SEVERITY: dict[str, str] = {code: "hard" for code in TASK026_BLOCKER_REGISTRY}


# ---------------------------------------------------------------------------
# Frozen hash field tuples (R6-R7 §11.5).
# These are the SHA-256 input fields for each record type.
# ---------------------------------------------------------------------------

BLOCKER_ENTRY_HASH_FIELDS: Final[tuple[str, ...]] = (
    "code",
    "severity",
    "stage",
    "payload",
    "message_template",
)


class BlockerCode(StrEnum):
    """String-valued enum for type safety on the 14 codes."""

    BL_REQUEST_UNKNOWN_FIELD = "BL_REQUEST_UNKNOWN_FIELD"
    BL_RAW_INPUT_BOUNDARY_MALFORMED = "BL_RAW_INPUT_BOUNDARY_MALFORMED"
    BL_UPSTREAM_BLOCKED = "BL_UPSTREAM_BLOCKED"
    BL_PROPERTY_FIELD_MISSING = "BL_PROPERTY_FIELD_MISSING"
    BL_PROPERTY_FIELD_INVALID = "BL_PROPERTY_FIELD_INVALID"
    BL_PROPERTY_FIELD_NON_POSITIVE = "BL_PROPERTY_FIELD_NON_POSITIVE"
    BL_PROPERTY_AUTHORITY_MISSING = "BL_PROPERTY_AUTHORITY_MISSING"
    BL_PROPERTY_HASH_MISMATCH = "BL_PROPERTY_HASH_MISMATCH"
    BL_UNSUPPORTED_PHASE = "BL_UNSUPPORTED_PHASE"
    BL_MASS_FLOW_INVALID = "BL_MASS_FLOW_INVALID"
    BL_DECIMAL_FAILURE = "BL_DECIMAL_FAILURE"
    BL_CORRELATION_NOT_APPLICABLE = "BL_CORRELATION_NOT_APPLICABLE"
    BL_REGIME_NO_CORRELATION_APPLICABLE = "BL_REGIME_NO_CORRELATION_APPLICABLE"
    BL_PARTIAL_RESULT_FORBIDDEN = "BL_PARTIAL_RESULT_FORBIDDEN"

    @property
    def canonical_utf8_bytes(self) -> bytes:
        return self.value.encode("ascii")


@dataclass(frozen=True)
class BlockerEntry:
    """R6-R7 §9.6.2 — Blocker entry (5 fields, KIND_TUPLE payload per §9.6.2)."""

    code: str
    severity: str
    stage: str
    payload: tuple[str, ...]
    message_template: str

    def __post_init__(self) -> None:
        if self.code not in TASK026_BLOCKER_REGISTRY:
            raise ValueError(f"code must be one of {TASK026_BLOCKER_REGISTRY!r}; got {self.code!r}")
        if self.severity != "hard":
            raise ValueError(f"severity must be 'hard'; got {self.severity!r}")
        if self.stage not in {
            s
            for s, _ in (
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
        }:
            raise ValueError(f"stage must be a valid S00..S15; got {self.stage!r}")
        if not isinstance(self.payload, tuple):
            raise ValueError("payload must be tuple")
        if not isinstance(self.message_template, str) or not self.message_template:
            raise ValueError("message_template must be non-empty str")


def blocker_entry_hash_fields() -> tuple[str, ...]:
    """R6-R7 §9.6.2 — exactly 5 fields for the blocker entry hash."""
    return ("code", "severity", "stage", "payload", "message_template")


__all__ = [
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
    "BlockerCode",
    "BlockerEntry",
    "blocker_entry_hash_fields",
]
