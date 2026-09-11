"""Literal TASK-169 Golden fixture authority data.

These values are proposal authority data, not runtime geometry inference.  In
particular, the G02 U-tube pairing plan is intentionally a literal payload
whose hash is verified by TASK-021 at the public boundary.
"""

from typing import Final

G05_NEGATIVE_CLASS: Final[str] = "MISSING_REQUIRED_SOURCE_OR_LICENSE_AUTHORITY"
G05_EXPECTED_BLOCKER_CODE: Final[str] = "EVALUATION_AUTHORITY_REQUIRED"
G05_EXPECTED_BLOCKER_OWNER: Final[str] = "TASK166"
G05_EXPECTED_BLOCKER_FIELD: Final[str] = "evaluation_input_authority.task166_request_template"
G05_NO_RECOMMENDATION_REQUIRED: Final[bool] = True

G02_PAIRING_AUTHORITY_ID: Final[str] = "HXFORGE-V06-G02-UTUBE-PAIRING"
G02_PAIRING_AUTHORITY_VERSION: Final[str] = "v1"
G02_PAIRING_SOURCE_CLASS: Final[str] = "AUTHORIZED_PROJECT_DEFINED_PAIRING_PROPOSAL"
G02_PAIRING_SOURCE_ID: Final[str] = "TASK169-G02-PAIRING-PROPOSAL"
G02_PAIRING_SOURCE_REVISION: Final[str] = "v1"
G02_PAIRING_APPROVAL_STATUS: Final[str] = "PROPOSED"
G02_PAIRING_EVIDENCE_REF: Final[str] = "TASK169-V06-G02-PAIRING-REVIEW"
G02_PAIRING_SCHEMA_VERSION: Final[str] = "task021.u-tube-pairing.v1"
G02_RUNTIME_PAIR_INFERENCE: Final[bool] = False
G02_TASK021_ORIGIN_MODE: Final[str] = "CENTER_ON_PRIMITIVE_CELL"
G02_PAIRING_PROVENANCE_SOURCE_HASH: Final[str] = (
    "895bd8e1ee5fecccfccc29a422b17574dedf4c7140435b544e8c35a78dc0edba"
)

# Do not replace this literal list with accepted-coordinate pairing logic.
# The proposal is deliberately explicit so that any change is a reviewable
# authority change rather than an execution-time inference.
G02_UTUBE_PAIRING_PLAN_RAW: Final[dict[str, object]] = {
    "schema_version": G02_PAIRING_SCHEMA_VERSION,
    "pairs": [
        {
            "pair_id": "G02-UTUBE-PAIR-001",
            "leg_a": {"u": 0, "v": -2},
            "leg_b": {"u": 1, "v": -2},
            "evidence_refs": [G02_PAIRING_EVIDENCE_REF],
        },
        {
            "pair_id": "G02-UTUBE-PAIR-002",
            "leg_a": {"u": -1, "v": -1},
            "leg_b": {"u": 0, "v": -1},
            "evidence_refs": [G02_PAIRING_EVIDENCE_REF],
        },
        {
            "pair_id": "G02-UTUBE-PAIR-003",
            "leg_a": {"u": 1, "v": -1},
            "leg_b": {"u": -2, "v": 0},
            "evidence_refs": [G02_PAIRING_EVIDENCE_REF],
        },
        {
            "pair_id": "G02-UTUBE-PAIR-004",
            "leg_a": {"u": -1, "v": 0},
            "leg_b": {"u": 0, "v": 0},
            "evidence_refs": [G02_PAIRING_EVIDENCE_REF],
        },
        {
            "pair_id": "G02-UTUBE-PAIR-005",
            "leg_a": {"u": -2, "v": 1},
            "leg_b": {"u": -1, "v": 1},
            "evidence_refs": [G02_PAIRING_EVIDENCE_REF],
        },
    ],
    "evidence_refs": [G02_PAIRING_EVIDENCE_REF],
    "pairing_plan_hash": "e7fe05b5ebd5e55107545f9a8f9b32908301d3bd12d4602b0ca0b3b8598eb4b0",
}


__all__ = (
    "G05_EXPECTED_BLOCKER_CODE",
    "G05_EXPECTED_BLOCKER_FIELD",
    "G05_EXPECTED_BLOCKER_OWNER",
    "G05_NEGATIVE_CLASS",
    "G05_NO_RECOMMENDATION_REQUIRED",
    "G02_PAIRING_APPROVAL_STATUS",
    "G02_PAIRING_AUTHORITY_ID",
    "G02_PAIRING_AUTHORITY_VERSION",
    "G02_PAIRING_EVIDENCE_REF",
    "G02_PAIRING_SCHEMA_VERSION",
    "G02_PAIRING_SOURCE_CLASS",
    "G02_PAIRING_SOURCE_ID",
    "G02_PAIRING_SOURCE_REVISION",
    "G02_PAIRING_PROVENANCE_SOURCE_HASH",
    "G02_RUNTIME_PAIR_INFERENCE",
    "G02_TASK021_ORIGIN_MODE",
    "G02_UTUBE_PAIRING_PLAN_RAW",
)
