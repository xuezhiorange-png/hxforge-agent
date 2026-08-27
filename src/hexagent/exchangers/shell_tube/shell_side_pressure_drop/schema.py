"""Fail-closed public request parser for TASK-034 v2."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .blocker_registry import BlockerCode, make_blocker
from .models import PROFILE_ID, REQUEST_FIELDS, REQUEST_SCHEMA_VERSION, Task034Request


class SchemaFailure(ValueError):
    def __init__(self, stage: str, *blockers: Any) -> None:
        super().__init__(stage)
        self.stage = stage
        self.blockers = tuple(blockers)


def _decimal(value: Any) -> Decimal:
    if type(value) is not str:
        raise ValueError("engineering Decimal must be a string")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("engineering Decimal must be finite")
    return result


def _string_refs(value: Any) -> tuple[str, ...]:
    if type(value) not in (list, tuple):
        raise ValueError("evidence refs must be a sequence")
    refs = tuple(value)
    if any(type(item) is not str for item in refs):
        raise ValueError("evidence refs must be strings")
    return refs


def _missing_blockers(missing: set[str]) -> tuple[Any, ...]:
    """Return schema blockers without conflating the v2 shell authority key."""
    blockers: list[Any] = []
    if "shell_type_authority" in missing:
        blockers.append(
            make_blocker(
                BlockerCode.SSPD_SHELL_TYPE_AUTHORITY_REQUIRED_FIELD_MISSING,
                stage="S02",
                field_path="shell_type_authority",
            )
        )
    if missing - {"shell_type_authority"}:
        blockers.append(
            make_blocker(
                BlockerCode.SSPD_REQUEST_SCHEMA_MISMATCH,
                stage="S02",
                field_path="request",
            )
        )
    return tuple(blockers)


def parse_request(raw_request: Any) -> Task034Request:
    """Parse only the TASK034 top-level shape; upstream evidence is replayed later."""
    if type(raw_request) is not dict:
        raise SchemaFailure(
            "S01",
            make_blocker(
                BlockerCode.SSPD_RAW_REQUEST_TYPE_INVALID,
                stage="S01",
                field_path="raw_request",
            ),
        )

    keys = set(raw_request)
    unknown = keys - set(REQUEST_FIELDS)
    if unknown:
        raise SchemaFailure(
            "S02",
            make_blocker(
                BlockerCode.SSPD_UNKNOWN_REQUEST_FIELD,
                stage="S02",
                field_path="request.keys",
            ),
        )
    missing = set(REQUEST_FIELDS) - keys
    if missing:
        raise SchemaFailure("S02", *_missing_blockers(missing))
    if raw_request["schema_version"] != REQUEST_SCHEMA_VERSION:
        raise SchemaFailure(
            "S02",
            make_blocker(
                BlockerCode.SSPD_REQUEST_SCHEMA_MISMATCH,
                stage="S02",
                field_path="schema_version",
            ),
        )
    if raw_request["profile_id"] != PROFILE_ID:
        raise SchemaFailure(
            "S02",
            make_blocker(
                BlockerCode.SSPD_PROFILE_ID_MISMATCH,
                stage="S02",
                field_path="profile_id",
            ),
        )

    try:
        spacing_raw = raw_request["uniform_spacing_sequence_m"]
        if type(spacing_raw) not in (list, tuple):
            raise ValueError("spacing must be a sequence")
        spacing = tuple(_decimal(item) for item in spacing_raw)
        wall_refs = _string_refs(raw_request["wall_property_evidence_refs"])
        evidence_refs = _string_refs(raw_request["evidence_refs"])
        return Task034Request(
            schema_version=raw_request["schema_version"],
            profile_id=raw_request["profile_id"],
            task033_upstream_evidence=raw_request["task033_upstream_evidence"],
            task031_request_evidence=raw_request["task031_request_evidence"],
            shell_type_authority=raw_request["shell_type_authority"],
            task031_request_hash=raw_request["task031_request_hash"],
            shell_inside_diameter_m=_decimal(raw_request["shell_inside_diameter_m"]),
            baffle_count=raw_request["baffle_count"],
            uniform_spacing_sequence_m=spacing,
            tube_pitch_m=_decimal(raw_request["tube_pitch_m"]),
            tube_outer_diameter_m=_decimal(raw_request["tube_outer_diameter_m"]),
            pattern_family=raw_request["pattern_family"],
            shell_side_wall_dynamic_viscosity_pa_s=_decimal(
                raw_request["shell_side_wall_dynamic_viscosity_pa_s"]
            ),
            wall_property_schema_version=raw_request["wall_property_schema_version"],
            wall_property_source_id=raw_request["wall_property_source_id"],
            wall_property_source_version=raw_request["wall_property_source_version"],
            wall_property_evidence_refs=wall_refs,
            wall_property_snapshot_hash=raw_request["wall_property_snapshot_hash"],
            wall_property_authority_hash=raw_request["wall_property_authority_hash"],
            correlation_id=raw_request["correlation_id"],
            shell_side_case_id=raw_request["shell_side_case_id"],
            shell_side_stream_id=raw_request["shell_side_stream_id"],
            shell_side_fluid_id=raw_request["shell_side_fluid_id"],
            task020_configuration_id=raw_request["task020_configuration_id"],
            task020_configuration_hash=raw_request["task020_configuration_hash"],
            task031_geometry_id=raw_request["task031_geometry_id"],
            task031_geometry_hash=raw_request["task031_geometry_hash"],
            task032_request_hash=raw_request["task032_request_hash"],
            task032_result_id=raw_request["task032_result_id"],
            task032_result_hash=raw_request["task032_result_hash"],
            task033_request_hash=raw_request["task033_request_hash"],
            task033_result_id=raw_request["task033_result_id"],
            task033_result_hash=raw_request["task033_result_hash"],
            property_snapshot_hash=raw_request["property_snapshot_hash"],
            mass_flow_authority_hash=raw_request["mass_flow_authority_hash"],
            evidence_refs=evidence_refs,
        )
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise SchemaFailure(
            "S02",
            make_blocker(
                BlockerCode.SSPD_REQUEST_SCHEMA_MISMATCH,
                stage="S02",
                field_path="request",
            ),
        ) from exc


__all__ = ["SchemaFailure", "parse_request"]
