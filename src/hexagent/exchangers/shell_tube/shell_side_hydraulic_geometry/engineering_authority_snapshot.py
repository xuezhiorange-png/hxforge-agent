"""Frozen TASK-031 engineering authority snapshot."""

from __future__ import annotations

from typing import Any

from hexagent.exchangers.shell_tube.tube_layout.canonical import sha256_hex

from .models import (
    AGGREGATE_AUTHORITY_PROFILE_ID,
    ENGINEERING_AUTHORITY_SCHEMA_VERSION,
    FORMULA_A_ID,
    FORMULA_B_ID,
)

ENGINEERING_AUTHORITY_HASH = "1cb5cf1ff9f28fb2dec074f6458473e60d0866c744fbd97501e41d68b5837989"
ENGINEERING_AUTHORITY_ID = (
    f"urn:hxforge:task031:engineering-authority:v1:{ENGINEERING_AUTHORITY_HASH}"
)
FREEZE_COMMENT_ID = "5311936966"
ISSUE_NUMBER = 181
PERMISSION_STATE = "LAWFUL_PUBLIC_ACCESS_REUSE_WITH_ATTRIBUTION"
SOURCE_LEDGER_VERSION = "TASK031_ENGINEERING_SOURCE_FORMULA_AUTHORITY_FREEZE_V1"
SOURCE_LEDGER_COUNT = 4
FORMULA_AUTHORITY_RECORD_MODEL = "PER_FORMULA_PLUS_AGGREGATE"
PRIMARY_SOURCE_ID = "SRC-INTECHOPEN-100450-KHARAJI-2021"

EXACT_SOURCE_LOCATIONS: tuple[str, ...] = (
    '§4.4 "Shell diameter", Eq. (55)-(56)',
    '§4.4 "Shell diameter", Eq. (51)-(53)',
)

CORROBORATING_SOURCE_IDS: tuple[str, ...] = (
    "SRC-NPTEL-103103027-MOD1",
    "SRC-NPTEL-103103032-LEC35",
    "SRC-OU-CHE-DESIGN-2018-KERN",
)

SOURCE_IDS: tuple[str, ...] = tuple(sorted((PRIMARY_SOURCE_ID, *CORROBORATING_SOURCE_IDS)))

SUPPORTED_PATTERN_FAMILIES: tuple[str, ...] = ("SQUARE", "TRIANGULAR")

APPLICABILITY_ENVELOPE: dict[str, Any] = {
    "construction_family": "FIXED_TUBESHEET",
    "shell_pass_count": 1,
    "baffle_type": "SINGLE_SEGMENTAL",
    "baffle_count_minimum": 2,
    "pattern_families": ["SQUARE", "TRIANGULAR"],
    "uniform_central_inter_baffle_spacing_required": True,
    "flow_region_identity": "CENTRAL_CROSSFLOW_SCREENING",
}


def authority_canonical_projection() -> dict[str, Any]:
    """Return the frozen §20.2 key-ordered mapping projection."""
    return {
        "schema_version": ENGINEERING_AUTHORITY_SCHEMA_VERSION,
        "aggregate_profile_id": AGGREGATE_AUTHORITY_PROFILE_ID,
        "formula_a_id": FORMULA_A_ID,
        "formula_b_id": FORMULA_B_ID,
        "primary_source_id": PRIMARY_SOURCE_ID,
        "exact_source_locations": list(EXACT_SOURCE_LOCATIONS),
        "corroborating_source_ids": list(CORROBORATING_SOURCE_IDS),
        "supported_pattern_families": list(SUPPORTED_PATTERN_FAMILIES),
        "applicability_envelope": APPLICABILITY_ENVELOPE,
        "permission_state": PERMISSION_STATE,
        "issue_number": ISSUE_NUMBER,
        "freeze_comment_id": FREEZE_COMMENT_ID,
        "source_ledger_version": SOURCE_LEDGER_VERSION,
        "source_ledger_count": SOURCE_LEDGER_COUNT,
        "formula_authority_record_model": FORMULA_AUTHORITY_RECORD_MODEL,
    }


def recompute_engineering_authority_hash() -> str:
    return sha256_hex(authority_canonical_projection())


__all__ = [
    "APPLICABILITY_ENVELOPE",
    "CORROBORATING_SOURCE_IDS",
    "ENGINEERING_AUTHORITY_HASH",
    "ENGINEERING_AUTHORITY_ID",
    "EXACT_SOURCE_LOCATIONS",
    "FORMULA_AUTHORITY_RECORD_MODEL",
    "FREEZE_COMMENT_ID",
    "ISSUE_NUMBER",
    "PERMISSION_STATE",
    "PRIMARY_SOURCE_ID",
    "SOURCE_IDS",
    "SOURCE_LEDGER_COUNT",
    "SOURCE_LEDGER_VERSION",
    "SUPPORTED_PATTERN_FAMILIES",
    "authority_canonical_projection",
    "recompute_engineering_authority_hash",
]
