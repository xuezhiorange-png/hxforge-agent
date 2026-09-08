"""Total, bounded raw ingress for TASK-167.

Only exact built-in containers, scalar values, and the explicitly registered
trusted producer/value objects are traversed.  Unsupported objects never
invoke ``repr``, ``str``, ``id``, ``hash`` or user code.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from decimal import Decimal
from enum import Enum
from typing import Any

from hexagent.exchangers.shell_tube.bell_delaware.models import (
    ApplicabilityStatus as Task166ApplicabilityStatus,
)
from hexagent.exchangers.shell_tube.bell_delaware.models import (
    Task166Result,
)
from hexagent.exchangers.shell_tube.models import (
    AuthorityMode,
    CaseRevisionStatus,
    ConstructionFamily,
    EquipmentFamily,
    EvaluatedRulePackAuthority,
    Orientation,
    SelectedRuleAuthority,
    ShellAndTubeConfiguration,
    StandardClaimStatus,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    FlowRegime,
    PhaseAssertion,
    ThermalBoundaryCondition,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import TubeSideThermalResult

from . import authority
from .canonical import sha256_domain_hex
from .errors import BlockerCode
from .models import (
    FoulingTendency,
    NozzleGeometryAuthority,
    ScreeningPropertySnapshot,
    ScreeningRequirements,
    Task167Request,
)


class RawProjectionFailure(ValueError):
    def __init__(self, code: BlockerCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class _Budget:
    def __init__(self) -> None:
        self.nodes = 0

    def consume(self) -> None:
        self.nodes += 1
        if self.nodes > authority.RAW_MAX_NODES:
            raise RawProjectionFailure(
                BlockerCode.RAW_NODE_LIMIT_EXCEEDED, "raw node budget exceeded"
            )


def _utf8(value: str) -> bytes:
    try:
        return value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise RawProjectionFailure(
            BlockerCode.RAW_UNICODE_ENCODING_FAILURE, "invalid UTF-8 scalar"
        ) from exc


def _string(value: str) -> dict[str, Any]:
    encoded = _utf8(value)
    if len(encoded) > authority.RAW_MAX_SCALAR_BYTES:
        raise RawProjectionFailure(
            BlockerCode.RAW_SCALAR_BYTE_LIMIT_EXCEEDED, "raw scalar budget exceeded"
        )
    return {"kind": "STRING", "value": value}


def _decimal(value: Decimal) -> dict[str, Any]:
    if not value.is_finite():
        raise RawProjectionFailure(BlockerCode.UNSUPPORTED_RAW_VALUE, "non-finite Decimal")
    try:
        encoded = str(value).encode("ascii", "strict")
    except UnicodeEncodeError as exc:  # pragma: no cover - Decimal is ASCII by definition
        raise RawProjectionFailure(BlockerCode.UNSUPPORTED_RAW_VALUE, "invalid Decimal") from exc
    if len(encoded) > authority.RAW_MAX_SCALAR_BYTES:
        raise RawProjectionFailure(
            BlockerCode.RAW_SCALAR_BYTE_LIMIT_EXCEEDED, "raw scalar budget exceeded"
        )
    return {"kind": "DECIMAL", "value": str(value)}


def _identity_fields(
    value: Any, names: tuple[str, ...], budget: _Budget, depth: int
) -> dict[str, Any]:
    return {
        "kind": type(value).__name__,
        "fields": {
            name: _walk(getattr(value, name), depth=depth + 1, budget=budget) for name in names
        },
    }


def _special(value: Any, *, depth: int, budget: _Budget) -> dict[str, Any] | None:
    if type(value) is Task166Result:
        return {
            "kind": "TASK166_RESULT",
            "fields": {
                "schema_version": _walk(value.schema_version, depth=depth + 1, budget=budget),
                "task166_version": _walk(value.task166_version, depth=depth + 1, budget=budget),
                "source_definition_id": _walk(
                    value.source_definition_id, depth=depth + 1, budget=budget
                ),
                "request_hash": _walk(value.request_hash, depth=depth + 1, budget=budget),
                "result_hash": _walk(value.result_hash, depth=depth + 1, budget=budget),
                "result_id": _walk(value.result_id, depth=depth + 1, budget=budget),
                "applicability_status": _walk(
                    None if value.applicability is None else value.applicability.status,
                    depth=depth + 1,
                    budget=budget,
                ),
                "completeness_status": _walk(
                    None if value.completeness is None else value.completeness.status,
                    depth=depth + 1,
                    budget=budget,
                ),
            },
        }
    if type(value) is TubeSideThermalResult:
        return _identity_fields(
            value,
            (
                "schema_version",
                "task026_version",
                "implementation_software_version",
                "upstream_geometry_hash",
                "property_snapshot_hash",
                "phase_assertion",
                "bulk_velocity_m_s",
                "reynolds_number",
                "prandtl_number",
                "request_hash",
                "result_hash",
                "result_id",
                "warnings",
                "deferred_capabilities",
            ),
            budget,
            depth,
        )
    if type(value) is ShellAndTubeConfiguration:
        return {
            "kind": "TASK020_CONFIGURATION",
            "fields": {
                name: _walk(getattr(value, name), depth=depth + 1, budget=budget)
                for name in (
                    "schema_version",
                    "configuration_id",
                    "configuration_hash",
                    "equipment_family",
                    "authority_mode",
                    "standard_claim_status",
                    "construction_family",
                    "orientation",
                    "shell_pass_count",
                    "tube_pass_count",
                )
            },
            "case_authority": {
                "revision_id": _walk(
                    value.case_authority.revision_id, depth=depth + 1, budget=budget
                ),
                "payload_hash": _walk(
                    value.case_authority.payload_hash, depth=depth + 1, budget=budget
                ),
                "domain_snapshot_hash": _walk(
                    value.case_authority.domain_snapshot_hash, depth=depth + 1, budget=budget
                ),
                "revision_status": _walk(
                    value.case_authority.revision_status, depth=depth + 1, budget=budget
                ),
            },
        }
    if type(value) is ScreeningRequirements:
        return _identity_fields(value, tuple(item.name for item in fields(value)), budget, depth)
    if type(value) is ScreeningPropertySnapshot:
        return _identity_fields(value, tuple(item.name for item in fields(value)), budget, depth)
    if type(value) is NozzleGeometryAuthority:
        return _identity_fields(value, tuple(item.name for item in fields(value)), budget, depth)
    if type(value) is Task167Request:
        names = tuple(item.name for item in fields(value) if item.name != "request_metadata")
        projected = {
            name: _walk(getattr(value, name), depth=depth + 1, budget=budget) for name in names
        }
        metadata = tuple(
            sorted(
                value.request_metadata,
                key=lambda item: (
                    _utf8(item[0]),
                    _utf8(item[1]),
                ),
            )
        )
        projected["request_metadata"] = _walk(
            metadata,
            depth=depth + 1,
            budget=budget,
        )
        return {"kind": "Task167Request", "fields": projected}
    if type(value) is EvaluatedRulePackAuthority:
        return _identity_fields(value, tuple(item.name for item in fields(value)), budget, depth)
    if type(value) is SelectedRuleAuthority:
        return _identity_fields(value, tuple(item.name for item in fields(value)), budget, depth)
    return None


def _walk(value: Any, *, depth: int, budget: _Budget) -> dict[str, Any]:
    if depth > authority.RAW_MAX_DEPTH:
        raise RawProjectionFailure(
            BlockerCode.RAW_DEPTH_LIMIT_EXCEEDED, "raw depth budget exceeded"
        )

    special = _special(value, depth=depth, budget=budget)
    if special is not None:
        budget.consume()
        return special
    if value is None:
        budget.consume()
        return {"kind": "NONE"}
    if type(value) is bool:
        budget.consume()
        return {"kind": "BOOL", "value": value}
    if type(value) is int:
        budget.consume()
        try:
            encoded = str(value).encode("ascii", "strict")
        except ValueError as exc:
            raise RawProjectionFailure(
                BlockerCode.RAW_SCALAR_BYTE_LIMIT_EXCEEDED, "integer too large"
            ) from exc
        if len(encoded) > authority.RAW_MAX_SCALAR_BYTES:
            raise RawProjectionFailure(
                BlockerCode.RAW_SCALAR_BYTE_LIMIT_EXCEEDED, "integer too large"
            )
        return {"kind": "INTEGER", "value": value}
    if type(value) is str:
        budget.consume()
        return _string(value)
    if type(value) is Decimal:
        budget.consume()
        return _decimal(value)
    if type(value) in {
        AuthorityMode,
        ConstructionFamily,
        EquipmentFamily,
        Orientation,
        StandardClaimStatus,
        CaseRevisionStatus,
        Task166ApplicabilityStatus,
        FlowRegime,
        PhaseAssertion,
        ThermalBoundaryCondition,
        FoulingTendency,
    }:
        budget.consume()
        return {"kind": "ENUM", "value": value.value}
    if isinstance(value, Enum):
        raise RawProjectionFailure(BlockerCode.UNSUPPORTED_RAW_VALUE, "custom Enum unsupported")
    if type(value) is float:
        raise RawProjectionFailure(BlockerCode.UNSUPPORTED_RAW_VALUE, "binary float unsupported")
    if type(value) in (tuple, list):
        budget.consume()
        return {
            "kind": "SEQUENCE",
            "items": [_walk(item, depth=depth + 1, budget=budget) for item in value],
        }
    if type(value) is dict:
        budget.consume()
        keys: list[tuple[bytes, str]] = []
        for key in value:
            if type(key) is not str:
                raise RawProjectionFailure(
                    BlockerCode.UNSUPPORTED_RAW_VALUE, "mapping key must be exact str"
                )
            keys.append((_utf8(key), key))

        def _metadata_value(item: Any) -> Any:
            if type(item) is tuple and all(
                type(pair) is tuple
                and len(pair) == 2
                and type(pair[0]) is str
                and type(pair[1]) is str
                for pair in item
            ):
                return tuple(
                    sorted(
                        item,
                        key=lambda pair: (
                            _utf8(pair[0]),
                            _utf8(pair[1]),
                        ),
                    )
                )
            return item

        return {
            "kind": "RECORD",
            "fields": [
                [
                    key,
                    _walk(
                        _metadata_value(value[key]) if key == "request_metadata" else value[key],
                        depth=depth + 1,
                        budget=budget,
                    ),
                ]
                for _encoded, key in sorted(keys, key=lambda item: item[0])
            ],
        }
    if isinstance(value, Mapping):
        raise RawProjectionFailure(BlockerCode.UNSUPPORTED_RAW_VALUE, "mapping must be exact dict")
    raise RawProjectionFailure(BlockerCode.UNSUPPORTED_RAW_VALUE, "unsupported raw value")


def project_raw(value: object) -> dict[str, Any]:
    return _walk(value, depth=0, budget=_Budget())


def raw_projection_hash(value: object) -> str:
    return sha256_domain_hex("task167.raw-request-projection.v1", project_raw(value))


__all__ = ["RawProjectionFailure", "project_raw", "raw_projection_hash"]
