"""TASK-025 raw projection.

The public raw boundary is deliberately strict: only exact built-ins,
registered enum classes, and the frozen TASK-025 known-object table are
accepted.  Every recursive value is framed with an explicit kind tag and
length, so projection is injective for the supported domain.
"""

from __future__ import annotations

import enum as _enum
from decimal import Decimal
from typing import Any, Final

from hexagent.exchangers.shell_tube.models import (
    AuthorityMode,
    ConstructionFamily,
    Orientation,
    ShellAndTubeConfiguration,
)
from hexagent.exchangers.shell_tube.tube_layout.models import (
    ApprovedTubeGeometrySnapshot,
    TubeLayout,
    TubePosition,
)
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    FrozenJsonArray,
    FrozenJsonObject,
    PIWrapper,
    sha256_hex_from_framed_bytes,
)
from hexagent.exchangers.shell_tube.tube_side.hydraulic_participation_authority import (
    Task025HydraulicParticipationAuthority,
)
from hexagent.exchangers.shell_tube.tube_side.length_authorities import (
    HeatTransferLengthAuthority,
    InternalFlowLengthAuthority,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    HydraulicAuthorityMode,
    ReferencePlanePair,
    ReferencePlaneToken,
)

FlowPathMode = __import__(
    "hexagent.exchangers.shell_tube.tube_side.owned_enums", fromlist=["FlowPathMode"]
).FlowPathMode
BlockerCode = __import__(
    "hexagent.exchangers.shell_tube.tube_side.blocker_registry", fromlist=["BlockerCode"]
).BlockerCode

RECOGNIZED_ENUM_CLASSES: Final[tuple[type[_enum.Enum], ...]] = (
    FlowPathMode,
    HydraulicAuthorityMode,
    ReferencePlaneToken,
    BlockerCode,
    AuthorityMode,
    ConstructionFamily,
    Orientation,
)

# Exact concrete type table for TASK-025 known objects. Used by both the
# raw projection dispatch (project_raw_value) and the public
# unsafe_object_signal check. Identity comparison must use type(...) and
# never isinstance, class name, MRO, or duck typing.
KNOWN_TASK025_CONCRETE_TYPES: Final[frozenset[type[Any]]] = frozenset(
    {
        ShellAndTubeConfiguration,
        TubeLayout,
        InternalFlowLengthAuthority,
        HeatTransferLengthAuthority,
        Task025HydraulicParticipationAuthority,
        ReferencePlanePair,
    }
)

MAX_DEPTH: Final[int] = 64
_DEPTH_LIMIT: Final[int] = MAX_DEPTH

_SHELL_TUBE_CONFIGURATION_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "configuration_id",
    "configuration_hash",
    "authority_mode",
    "construction_family",
    "orientation",
    "shell_pass_count",
    "tube_pass_count",
)
_TUBE_LAYOUT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "layout_id",
    "layout_hash",
    "request_hash",
    "task020_configuration_id",
    "task020_configuration_hash",
    "construction_family",
    "equipment_orientation",
    "shell_pass_count",
    "tube_pass_count",
    "tube_hole_count",
    "physical_tube_count",
    "positions",
    "tube_geometry",
)
_NS_SHELL_TUBE_CONFIGURATION: Final[bytes] = b"hexagent.shell-tube.configuration.v1"
_NS_TUBE_LAYOUT: Final[bytes] = b"hexagent.tube-layout.layout.v1"
_NS_INTERNAL_FLOW_LENGTH: Final[bytes] = b"task025.internal-flow-length-authority.v1"
_NS_HEAT_TRANSFER_LENGTH: Final[bytes] = b"task025.heat-transfer-length-authority.v1"
_NS_HYDRAULIC_PARTICIPATION: Final[bytes] = b"task025.hydraulic-participation-authority.v1"
_NS_REFERENCE_PLANE_PAIR: Final[bytes] = b"task025.reference-plane-pair.v1"


class RawProjectionError(ValueError):
    """Controlled failure from the raw projection boundary."""


def _u32_be(n: int) -> bytes:
    if n < 0 or n > 0xFFFFFFFF:
        raise RawProjectionError("u32 framing range")
    return n.to_bytes(4, "big")


def _u64_be(n: int) -> bytes:
    if n < 0 or n > 0xFFFFFFFFFFFFFFFF:
        raise RawProjectionError("u64 framing range")
    return n.to_bytes(8, "big")


def _frame(kind: bytes, payload: bytes) -> bytes:
    return _u32_be(len(kind)) + kind + _u64_be(len(payload)) + payload


def _record(namespace: bytes, fields: tuple[tuple[str, bytes, bytes], ...]) -> bytes:
    out = _u32_be(len(namespace)) + namespace + _u32_be(len(fields))
    for name, kind, payload in fields:
        name_bytes = name.encode("utf-8")
        out += _u32_be(len(name_bytes)) + name_bytes + _frame(kind, payload)
    return out


def _atom(kind: bytes, payload: bytes) -> bytes:
    return _frame(kind, payload)


def _utf8(value: str) -> bytes:
    if type(value) is not str:
        raise RawProjectionError("invalid UTF-8 string type")
    try:
        return value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise RawProjectionError("invalid UTF-8 string") from exc


def _ascii_decimal(value: Decimal) -> bytes:
    try:
        return str(value).encode("ascii")
    except (UnicodeEncodeError, ValueError) as exc:
        raise RawProjectionError("decimal lexical encoding failed") from exc


def _enum_bytes(value: _enum.Enum) -> bytes:
    if type(value) not in RECOGNIZED_ENUM_CLASSES:
        raise RawProjectionError("unrecognized enum class")
    # Registered StrEnum classes expose an implementation-owned .value.
    raw_value = value.value
    if type(raw_value) is not str:
        raise RawProjectionError("enum value is not exact str")
    try:
        return raw_value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise RawProjectionError("enum value is not ASCII") from exc


def _project_atom(value: Any) -> bytes:
    value_type = type(value)
    if value is None:
        return _atom(b"NONE", b"")
    if value_type is bool:
        return _atom(b"BOOL_TRUE" if value else b"BOOL_FALSE", b"")
    if value_type is int:
        return _atom(b"INT", str(value).encode("ascii"))
    if value_type is str:
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise RawProjectionError("surrogate-containing string")
        return _atom(b"STRING", _utf8(value))
    if value_type is bytes:
        return _atom(b"BYTES", bytes(value))
    if value_type is Decimal:
        return _atom(b"DECIMAL", _ascii_decimal(value))
    if type(value) in RECOGNIZED_ENUM_CLASSES:
        return _atom(b"ENUM", _enum_bytes(value))
    if type(value) is PIWrapper:
        return _atom(b"KNOWN_PI", value.canonical_utf8_bytes)
    raise RawProjectionError("unsupported atom")


def _project(value: Any, depth: int, active_container_ids: frozenset[int]) -> bytes:
    if depth > MAX_DEPTH:
        raise RawProjectionError("raw projection depth limit")
    value_type = type(value)
    if (
        value is None
        or value_type in (bool, int, str, bytes, Decimal)
        or value_type in RECOGNIZED_ENUM_CLASSES
        or value_type is PIWrapper
    ):
        return _project_atom(value)

    if value_type is ShellAndTubeConfiguration:
        return _project_shell_tube_configuration(value, depth, active_container_ids)
    if value_type is TubeLayout:
        return _project_tube_layout(value, depth, active_container_ids)
    if value_type is InternalFlowLengthAuthority:
        return _project_length_authority(value, _NS_INTERNAL_FLOW_LENGTH)
    if value_type is HeatTransferLengthAuthority:
        return _project_length_authority(value, _NS_HEAT_TRANSFER_LENGTH)
    if value_type is Task025HydraulicParticipationAuthority:
        return _project_participation(value, depth, active_container_ids)
    if value_type is ReferencePlanePair:
        return _project_reference_plane_pair(value)
    if value_type is FrozenJsonArray:
        object_id = id(value)
        if object_id in active_container_ids:
            raise RawProjectionError("raw projection cycle")
        return _project_frozen_array(value, depth + 1, active_container_ids | {object_id})
    if value_type is FrozenJsonObject:
        object_id = id(value)
        if object_id in active_container_ids:
            raise RawProjectionError("raw projection cycle")
        return _project_frozen_object(value, depth + 1, active_container_ids | {object_id})

    if value_type in (dict, tuple, frozenset):
        object_id = id(value)
        if object_id in active_container_ids:
            raise RawProjectionError("raw projection cycle")
        next_active = active_container_ids | {object_id}
        if value_type is dict:
            return _project_dict(value, depth + 1, next_active)
        if value_type is tuple:
            return _project_tuple(value, depth + 1, next_active)
        return _project_frozenset(value, depth + 1, next_active)

    raise RawProjectionError("unsupported raw object")


def _project_dict(value: dict[Any, Any], depth: int, active: frozenset[int]) -> bytes:
    entries: list[tuple[bytes, bytes]] = []
    for key, child in value.items():
        key_bytes = _utf8(key)
        entries.append((key_bytes, _project(child, depth, active)))
    entries.sort(key=lambda pair: pair[0])
    payload = _u32_be(len(entries))
    for key_bytes, child_bytes in entries:
        payload += _u32_be(len(key_bytes)) + key_bytes + _u64_be(len(child_bytes)) + child_bytes
    return _atom(b"DICT", payload)


def _project_tuple(value: tuple[Any, ...], depth: int, active: frozenset[int]) -> bytes:
    payload = _u32_be(len(value))
    for child in value:
        child_bytes = _project(child, depth, active)
        payload += _u64_be(len(child_bytes)) + child_bytes
    return _atom(b"TUPLE", payload)


def _project_frozenset(value: frozenset[Any], depth: int, active: frozenset[int]) -> bytes:
    # Only exact supported atoms / frozen values are allowed; projection itself
    # never invokes member __hash__, __eq__, or ordering methods.
    projected = [_project(item, depth, active) for item in value]
    if len(set(projected)) != len(projected):
        raise RawProjectionError("frozenset projected duplicate")
    payload = _u32_be(len(projected))
    for child_bytes in sorted(projected):
        payload += _u64_be(len(child_bytes)) + child_bytes
    return _atom(b"FROZENSET", payload)


def _configuration_field(value: Any, field_name: str) -> Any:
    if field_name == "schema_version":
        return value.schema_version
    if field_name == "configuration_id":
        return value.configuration_id
    if field_name == "configuration_hash":
        return value.configuration_hash
    if field_name == "authority_mode":
        return value.authority_mode
    if field_name == "construction_family":
        return value.construction_family
    if field_name == "orientation":
        return value.orientation
    if field_name == "shell_pass_count":
        return value.shell_pass_count
    if field_name == "tube_pass_count":
        return value.tube_pass_count
    raise RawProjectionError("unknown configuration field")


def _layout_field(value: TubeLayout, field_name: str) -> Any:
    if field_name == "schema_version":
        return value.schema_version
    if field_name == "layout_id":
        return value.layout_id
    if field_name == "layout_hash":
        return value.layout_hash
    if field_name == "request_hash":
        return value.request_hash
    if field_name == "task020_configuration_id":
        return value.task020_configuration_id
    if field_name == "task020_configuration_hash":
        return value.task020_configuration_hash
    if field_name == "construction_family":
        return value.construction_family
    if field_name == "equipment_orientation":
        return value.equipment_orientation
    if field_name == "shell_pass_count":
        return value.shell_pass_count
    if field_name == "tube_pass_count":
        return value.tube_pass_count
    if field_name == "tube_hole_count":
        return value.tube_hole_count
    if field_name == "physical_tube_count":
        return value.physical_tube_count
    if field_name == "positions":
        return value.positions
    if field_name == "tube_geometry":
        return value.tube_geometry
    raise RawProjectionError("unknown layout field")


def _project_shell_tube_configuration(value: Any, depth: int, active: frozenset[int]) -> bytes:
    fields: list[tuple[str, bytes, bytes]] = []
    for field_name in _SHELL_TUBE_CONFIGURATION_FIELDS:
        try:
            field_value = _configuration_field(value, field_name)
        except (AttributeError, ValueError, TypeError) as exc:
            raise RawProjectionError(f"configuration field {field_name!r} inaccessible") from exc
        if field_name in ("authority_mode", "construction_family", "orientation"):
            if not isinstance(field_value, _enum.Enum):
                raise RawProjectionError("configuration enum field type")
            fields.append((field_name, b"ENUM", _enum_bytes(field_value)))
        elif type(field_value) is str:
            fields.append((field_name, b"STRING", field_value.encode("utf-8")))
        elif type(field_value) is int:
            fields.append((field_name, b"INT", str(field_value).encode("ascii")))
        else:
            raise RawProjectionError("configuration field type")
    return _atom(b"KNOWN_RECORD", _record(_NS_SHELL_TUBE_CONFIGURATION, tuple(fields)))


def _project_tube_layout(value: TubeLayout, depth: int, active: frozenset[int]) -> bytes:
    fields: list[tuple[str, bytes, bytes]] = []
    for field_name in _TUBE_LAYOUT_FIELDS:
        try:
            field_value = _layout_field(value, field_name)
        except (AttributeError, ValueError, TypeError) as exc:
            raise RawProjectionError(f"layout field {field_name!r} inaccessible") from exc
        if field_name in ("construction_family", "equipment_orientation"):
            if field_name == "construction_family":
                if type(field_value) is not str:
                    raise RawProjectionError("layout construction family type")
                fields.append((field_name, b"STRING", field_value.encode("utf-8")))
            else:
                if type(field_value) is not Orientation:
                    raise RawProjectionError("layout orientation type")
                fields.append((field_name, b"ENUM", _enum_bytes(field_value)))
        elif field_name == "positions":
            if type(field_value) is not tuple:
                raise RawProjectionError("layout positions are not exact tuple")
            position_payload = _u32_be(len(field_value))
            for position in field_value:
                if type(position) is not TubePosition:
                    raise RawProjectionError("layout position not exact TubePosition")
                position_id: Any = None
                try:
                    position_id = position.position_id
                except (AttributeError, ValueError, TypeError) as exc:
                    raise RawProjectionError("layout position_id inaccessible") from exc
                if type(position_id) is not str:
                    raise RawProjectionError("layout position_id not exact str")
                child = _project_atom(position_id)
                position_payload += _u64_be(len(child)) + child
            fields.append((field_name, b"TUPLE", position_payload))
        elif field_name == "tube_geometry":
            if type(field_value) is not ApprovedTubeGeometrySnapshot:
                raise RawProjectionError(
                    "layout tube_geometry not exact ApprovedTubeGeometrySnapshot"
                )
            geometry: ApprovedTubeGeometrySnapshot = field_value
            geometry_id: Any = None
            record_hash: Any = None
            snapshot_hash: Any = None
            try:
                geometry_id = geometry.geometry_id
                record_hash = geometry.record_hash
                snapshot_hash = geometry.snapshot_hash
            except (AttributeError, ValueError, TypeError) as exc:
                raise RawProjectionError("layout geometry field inaccessible") from exc
            if type(geometry_id) is not str:
                raise RawProjectionError("layout geometry_id not exact str")
            if type(record_hash) is not str:
                raise RawProjectionError("layout record_hash not exact str")
            if type(snapshot_hash) is not str:
                raise RawProjectionError("layout snapshot_hash not exact str")
            subfields = (
                ("geometry_id", b"STRING", geometry_id.encode("utf-8")),
                ("record_hash", b"STRING", record_hash.encode("ascii")),
                ("snapshot_hash", b"STRING", snapshot_hash.encode("ascii")),
            )
            fields.append(
                (field_name, b"KNOWN_RECORD", _record(b"task025.tube-geometry.v1", subfields))
            )
        elif type(field_value) is str:
            fields.append((field_name, b"STRING", field_value.encode("utf-8")))
        elif type(field_value) is int:
            fields.append((field_name, b"INT", str(field_value).encode("ascii")))
        else:
            raise RawProjectionError("layout field type")
    return _atom(b"KNOWN_RECORD", _record(_NS_TUBE_LAYOUT, tuple(fields)))


def _project_length_authority(value: Any, namespace: bytes) -> bytes:
    try:
        length_id = value.length_id
        length_m = value.length_m
        start_plane = value.start_plane
        end_plane = value.end_plane
        authority_mode = value.authority_mode
        length_hash = value.length_hash
    except (AttributeError, ValueError, TypeError) as exc:
        raise RawProjectionError("length authority field inaccessible") from exc
    fields = (
        ("length_id", b"STRING", length_id.encode("utf-8")),
        ("length_m", b"DECIMAL", _ascii_decimal(length_m)),
        ("start_plane", b"KNOWN_RECORD", _project_reference_plane_pair(start_plane)),
        ("end_plane", b"KNOWN_RECORD", _project_reference_plane_pair(end_plane)),
        ("authority_mode", b"ENUM", _enum_bytes(authority_mode)),
        ("length_hash", b"STRING", length_hash.encode("ascii")),
    )
    return _atom(b"KNOWN_RECORD", _record(namespace, fields))


def _project_participation(value: Any, depth: int, active: frozenset[int]) -> bytes:
    try:
        all_layout = value.all_layout_position_ids
        active_ids = value.active_position_ids
        inactive_ids = value.inactive_position_ids
        authority_mode = value.authority_mode
        evidence_refs = value.evidence_refs
        hydraulic_authority_hash = value.hydraulic_authority_hash
    except (AttributeError, ValueError, TypeError) as exc:
        raise RawProjectionError("participation authority field inaccessible") from exc
    fields = (
        (
            "all_layout_position_ids",
            b"TUPLE",
            _project_tuple(all_layout, depth, active),
        ),
        ("active_position_ids", b"TUPLE", _project_tuple(active_ids, depth, active)),
        (
            "inactive_position_ids",
            b"TUPLE",
            _project_tuple(inactive_ids, depth, active),
        ),
        ("authority_mode", b"ENUM", _enum_bytes(authority_mode)),
        ("evidence_refs", b"TUPLE", _project_tuple(evidence_refs, depth, active)),
        ("hydraulic_authority_hash", b"STRING", hydraulic_authority_hash.encode("ascii")),
    )
    return _atom(b"KNOWN_RECORD", _record(_NS_HYDRAULIC_PARTICIPATION, fields))


def _project_reference_plane_pair(value: ReferencePlanePair) -> bytes:
    start = value.start
    end = value.end
    fields = (
        ("start", b"ENUM", _enum_bytes(start)),
        ("end", b"ENUM", _enum_bytes(end)),
    )
    return _record(_NS_REFERENCE_PLANE_PAIR, fields)


def _project_frozen_array(value: FrozenJsonArray, depth: int, active: frozenset[int]) -> bytes:
    payload = _u32_be(len(value))
    for child in value:
        child_bytes = _project(child, depth, active)
        payload += _u64_be(len(child_bytes)) + child_bytes
    return _atom(b"FROZEN_JSON_ARRAY", payload)


def _project_frozen_object(value: FrozenJsonObject, depth: int, active: frozenset[int]) -> bytes:
    entries: list[tuple[bytes, bytes]] = []
    for key, child in value.items_mapping.items():
        key_bytes = _utf8(key)
        child_bytes = _project(child, depth, active)
        entries.append((key_bytes, child_bytes))
    entries.sort(key=lambda pair: pair[0])
    payload = _u32_be(len(entries))
    for key_bytes, child_bytes in entries:
        payload += _u32_be(len(key_bytes)) + key_bytes + _u64_be(len(child_bytes)) + child_bytes
    return _atom(b"KNOWN_RECORD", payload)


def project_raw_value(
    value: Any, *, depth: int = 0, active_container_ids: frozenset[int] = frozenset()
) -> bytes:
    """Project a supported value; raise only :class:`RawProjectionError`."""
    out = _project(value, depth, active_container_ids)
    return out


def project_raw_dict(value: dict[str, Any]) -> bytes:
    if type(value) is not dict:
        raise RawProjectionError("top-level is not exact dict")
    return project_raw_value(value)


def raw_projection_hex(framed_bytes: bytes) -> str:
    return sha256_hex_from_framed_bytes(framed_bytes)


def unsafe_object_signal(value: Any) -> bool:
    """Return True if ``value`` is not in the supported raw boundary.

    Uses an exact concrete-type table only — never class names, MRO,
    ``isinstance`` for known types, or duck typing.
    """
    value_type = type(value)
    if value is None or value_type in (bool, int, str, bytes, Decimal):
        return False
    if value_type in RECOGNIZED_ENUM_CLASSES or value_type is PIWrapper:
        return False
    if value_type in (dict, tuple, frozenset, FrozenJsonArray, FrozenJsonObject):
        return False
    return value_type not in KNOWN_TASK025_CONCRETE_TYPES


__all__ = [
    "RawProjectionError",
    "MAX_DEPTH",
    "RECOGNIZED_ENUM_CLASSES",
    "KNOWN_TASK025_CONCRETE_TYPES",
    "project_raw_value",
    "project_raw_dict",
    "raw_projection_hex",
    "unsafe_object_signal",
]
