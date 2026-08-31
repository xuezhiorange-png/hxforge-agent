"""Frozen TASK-038 blocker vocabulary and precedence."""

from __future__ import annotations

from .models import BlockerEntry

BLOCKER_CODES: tuple[str, ...] = (
    "BL_RAW_INPUT_BOUNDARY_MALFORMED",
    "BL_REQUEST_SCHEMA_INVALID",
    "BL_TASK025_RESULT_INVALID",
    "BL_TASK026_RESULT_INVALID",
    "BL_TASK035_RESULT_INVALID",
    "BL_TASK037_RESULT_INVALID",
    "BL_HYDRAULIC_AUTHORITY_MISMATCH",
    "BL_TASK021_TASK020_ANCESTRY_MISMATCH",
    "BL_REFERENCE_SURFACE_MISMATCH",
    "BL_SERVICE_BINDING_INVALID",
    "BL_FOULING_SERVICE_MISMATCH",
    "BL_OVERALL_U_NOT_APPLICABLE",
    "BL_RESISTANCE_COMPOSITION_INVALID",
    "BL_OVERALL_U_QUANTIZATION_INVALID",
    "BL_OUTER_AREA_AUTHORITY_INVALID",
    "BL_OUTER_AREA_QUANTIZATION_INVALID",
    "BL_UA_COMPOSITION_INVALID",
    "BL_APPLICABILITY_INCOMPLETE",
    "BL_PROVENANCE_INVALID",
    "BL_RESULT_IDENTITY_INVALID",
)


def blocker(
    code: str,
    stage: str,
    *,
    field_path: str | None = None,
    message_key: str = "",
    details: tuple[tuple[str, str], ...] = (),
) -> BlockerEntry:
    return BlockerEntry(code, stage, field_path, message_key, details)


__all__ = ["BLOCKER_CODES", "blocker"]
