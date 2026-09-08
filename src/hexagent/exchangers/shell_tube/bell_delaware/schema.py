"""Strict typed ingress for the TASK-166 request."""

from __future__ import annotations

from dataclasses import fields
from decimal import Decimal, InvalidOperation
from typing import Any

from .authority import REQUEST_SCHEMA_VERSION, SOURCE_DEFINITION_ID
from .errors import BlockerCode
from .models import REQUEST_FIELDS, Task166Request
from .raw_projection import register_dataclass_type

TASK166_VERSION = "1.0"


class SchemaFailure(ValueError):
    def __init__(self, code: BlockerCode, field_path: str | None, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.field_path = field_path


def _exact_str(value: Any, path: str) -> str:
    if type(value) is not str:
        raise SchemaFailure(BlockerCode.INVALID_REQUEST_SCHEMA, path, "expected exact str")
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise SchemaFailure(
            BlockerCode.INVALID_REQUEST_SCHEMA, path, "invalid UTF-8 string"
        ) from exc
    return value


def decimal_value(value: Any, path: str) -> Decimal:
    if type(value) is Decimal:
        result = value
    elif type(value) is int:
        result = Decimal(value)
    elif type(value) is str:
        try:
            result = Decimal(value)
        except InvalidOperation as exc:
            raise SchemaFailure(
                BlockerCode.INVALID_REQUEST_SCHEMA, path, "invalid Decimal lexical value"
            ) from exc
    else:
        raise SchemaFailure(
            BlockerCode.INVALID_REQUEST_SCHEMA, path, "Decimal must be exact Decimal or string"
        )
    if not result.is_finite():
        raise SchemaFailure(BlockerCode.INVALID_REQUEST_SCHEMA, path, "Decimal must be finite")
    return result


def _exact_record(value: Any, path: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise SchemaFailure(BlockerCode.INVALID_REQUEST_SCHEMA, path, "expected exact dict")
    for key in value:
        if type(key) is not str:
            raise SchemaFailure(
                BlockerCode.INVALID_REQUEST_SCHEMA, path, "record keys must be exact strings"
            )
    return dict(value)


def _metadata(value: Any) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, (tuple, list)):
        raise SchemaFailure(
            BlockerCode.INVALID_REQUEST_SCHEMA, "request_metadata", "metadata must be a sequence"
        )
    pairs: list[tuple[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise SchemaFailure(
                BlockerCode.INVALID_REQUEST_SCHEMA,
                f"request_metadata[{index}]",
                "metadata pair required",
            )
        key = _exact_str(item[0], f"request_metadata[{index}][0]")
        val = _exact_str(item[1], f"request_metadata[{index}][1]")
        pairs.append((key, val))
    if len({key for key, _ in pairs}) != len(pairs):
        raise SchemaFailure(
            BlockerCode.INVALID_REQUEST_SCHEMA, "request_metadata", "duplicate metadata key"
        )
    return tuple(sorted(pairs, key=lambda pair: (pair[0].encode("utf-8"), pair[1].encode("utf-8"))))


def parse_request(raw: Any) -> Task166Request:
    if type(raw) is Task166Request:
        schema_version = _exact_str(raw.schema_version, "schema_version")
        task166_version = _exact_str(raw.task166_version, "task166_version")
        source_definition_id = _exact_str(raw.source_definition_id, "source_definition_id")
        if schema_version != REQUEST_SCHEMA_VERSION:
            raise SchemaFailure(
                BlockerCode.INVALID_REQUEST_SCHEMA, "schema_version", "unsupported schema"
            )
        if task166_version != TASK166_VERSION:
            raise SchemaFailure(
                BlockerCode.UNSUPPORTED_TASK166_VERSION, "task166_version", "unsupported version"
            )
        if source_definition_id != SOURCE_DEFINITION_ID:
            raise SchemaFailure(
                BlockerCode.SOURCE_DEFINITION_MISMATCH,
                "source_definition_id",
                "source mismatch",
            )
        return Task166Request(
            schema_version=schema_version,
            task166_version=task166_version,
            source_definition_id=source_definition_id,
            task020_configuration=_exact_record(raw.task020_configuration, "task020_configuration"),
            tube_layout=_exact_record(raw.tube_layout, "tube_layout"),
            shell_bundle_geometry=_exact_record(raw.shell_bundle_geometry, "shell_bundle_geometry"),
            baffle_geometry=_exact_record(raw.baffle_geometry, "baffle_geometry"),
            shell_side_hydraulic_geometry=_exact_record(
                raw.shell_side_hydraulic_geometry, "shell_side_hydraulic_geometry"
            ),
            shell_side_flow_state=_exact_record(raw.shell_side_flow_state, "shell_side_flow_state"),
            shell_side_flow_state_request=_exact_record(
                raw.shell_side_flow_state_request, "shell_side_flow_state_request"
            ),
            request_metadata=_metadata(raw.request_metadata),
        )
    if type(raw) is not dict:
        raise SchemaFailure(
            BlockerCode.INVALID_REQUEST_SCHEMA, None, "request must be an exact dict"
        )
    unknown = [key for key in raw if type(key) is not str or key not in REQUEST_FIELDS]
    if unknown:
        raise SchemaFailure(BlockerCode.INVALID_REQUEST_SCHEMA, None, "unknown request field")
    missing = [key for key in REQUEST_FIELDS if key not in raw]
    if missing:
        raise SchemaFailure(BlockerCode.INVALID_REQUEST_SCHEMA, missing[0], "missing request field")
    schema_version = _exact_str(raw["schema_version"], "schema_version")
    task166_version = _exact_str(raw["task166_version"], "task166_version")
    source_definition_id = _exact_str(raw["source_definition_id"], "source_definition_id")
    if schema_version != REQUEST_SCHEMA_VERSION:
        raise SchemaFailure(
            BlockerCode.INVALID_REQUEST_SCHEMA, "schema_version", "unsupported schema"
        )
    if task166_version != TASK166_VERSION:
        raise SchemaFailure(
            BlockerCode.UNSUPPORTED_TASK166_VERSION, "task166_version", "unsupported version"
        )
    if source_definition_id != SOURCE_DEFINITION_ID:
        raise SchemaFailure(
            BlockerCode.SOURCE_DEFINITION_MISMATCH, "source_definition_id", "source mismatch"
        )
    return Task166Request(
        schema_version=schema_version,
        task166_version=task166_version,
        source_definition_id=source_definition_id,
        task020_configuration=_exact_record(raw["task020_configuration"], "task020_configuration"),
        tube_layout=_exact_record(raw["tube_layout"], "tube_layout"),
        shell_bundle_geometry=_exact_record(raw["shell_bundle_geometry"], "shell_bundle_geometry"),
        baffle_geometry=_exact_record(raw["baffle_geometry"], "baffle_geometry"),
        shell_side_hydraulic_geometry=_exact_record(
            raw["shell_side_hydraulic_geometry"], "shell_side_hydraulic_geometry"
        ),
        shell_side_flow_state=_exact_record(raw["shell_side_flow_state"], "shell_side_flow_state"),
        shell_side_flow_state_request=_exact_record(
            raw["shell_side_flow_state_request"], "shell_side_flow_state_request"
        ),
        request_metadata=_metadata(raw["request_metadata"]),
    )


register_dataclass_type(Task166Request, tuple(field.name for field in fields(Task166Request)))


__all__ = ["SchemaFailure", "TASK166_VERSION", "decimal_value", "parse_request"]
