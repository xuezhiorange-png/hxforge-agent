"""Immutable TASK-032 engineering formula authority snapshot."""

from __future__ import annotations

from typing import Any

from hexagent.exchangers.shell_tube.tube_layout.canonical import sha256_hex

from .models import (
    FIRST_SLICE_PROFILE_ID,
    FLOW_MODEL,
    FORMULA_IDS,
    RHEOLOGY_MODEL,
)

ENGINEERING_AUTHORITY_SCHEMA_VERSION = "task032.engineering-authority.v1"
ENGINEERING_AUTHORITY_HASH_NAMESPACE = "task032.engineering-authority.v1"
ENGINEERING_AUTHORITY_PROFILE_ID = (
    "TASK032_SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_BULK_FLOW_STATE_SCREENING_V1_FORMULA_AUTHORITY"
)
ENGINEERING_SOURCE_FORMULA_FREEZE_COMMENT_ID = "5317260370"
SOURCE_DEFINITION_ISSUE = 185
PHASE_REGIONS: tuple[str, ...] = ("SINGLE_PHASE_LIQUID", "SINGLE_PHASE_GAS")
SOURCE_IDS: tuple[str, ...] = (
    "SRC-INTECHOPEN-100450-KHARAJI-2021",
    "SRC-NASA-GRC-MASS-FLOW-RATE-EQUATIONS",
)
EVIDENCE_REFS: tuple[str, ...] = (
    "5317111718",
    "5317255912",
    "5317260370",
    "docs/tasks/TASK-032-shell-and-tube-shell-side-single-phase-flow-state.md",
)


def authority_canonical_projection() -> dict[str, Any]:
    """Return the 12-field self-excluding authority projection."""

    return {
        "schema_version": ENGINEERING_AUTHORITY_SCHEMA_VERSION,
        "authority_profile_id": ENGINEERING_AUTHORITY_PROFILE_ID,
        "first_slice_profile_id": FIRST_SLICE_PROFILE_ID,
        "flow_model": FLOW_MODEL,
        "formula_ids": list(FORMULA_IDS),
        "source_ids": list(SOURCE_IDS),
        "phase_regions": list(PHASE_REGIONS),
        "rheology_model": RHEOLOGY_MODEL,
        "flow_regime_classification": "DEFERRED",
        "engineering_source_formula_freeze_comment_id": (
            ENGINEERING_SOURCE_FORMULA_FREEZE_COMMENT_ID
        ),
        "source_definition_issue": SOURCE_DEFINITION_ISSUE,
        "evidence_refs": list(EVIDENCE_REFS),
    }


def recompute_engineering_authority_hash() -> str:
    return sha256_hex([ENGINEERING_AUTHORITY_HASH_NAMESPACE, authority_canonical_projection()])


ENGINEERING_AUTHORITY_HASH = recompute_engineering_authority_hash()
ENGINEERING_AUTHORITY_ID = (
    f"urn:hxforge:task032:engineering-authority:v1:{ENGINEERING_AUTHORITY_HASH}"
)


__all__ = [
    "ENGINEERING_AUTHORITY_HASH",
    "ENGINEERING_AUTHORITY_HASH_NAMESPACE",
    "ENGINEERING_AUTHORITY_ID",
    "ENGINEERING_AUTHORITY_PROFILE_ID",
    "ENGINEERING_AUTHORITY_SCHEMA_VERSION",
    "ENGINEERING_SOURCE_FORMULA_FREEZE_COMMENT_ID",
    "EVIDENCE_REFS",
    "PHASE_REGIONS",
    "SOURCE_DEFINITION_ISSUE",
    "SOURCE_IDS",
    "authority_canonical_projection",
    "recompute_engineering_authority_hash",
]
